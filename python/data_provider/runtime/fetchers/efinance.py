# -*- coding: utf-8 -*-
"""
===================================
EfinanceFetcher - 优先数据源 (Priority 0)
===================================

数据来源：东方财富爬虫（通过 efinance 库）
特点：免费、无需 Token、数据全面、API 简洁
仓库：https://github.com/Micro-sheep/efinance

与 AkshareFetcher 类似，但 efinance 库：
1. API 更简洁易用
2. 支持批量获取数据
3. 更稳定的接口封装

防封禁策略：
1. 每次请求前随机休眠 1.5-3.0 秒
2. 随机轮换 User-Agent
3. 使用 tenacity 实现指数退避重试
4. 熔断器机制：连续失败后自动冷却
"""

import logging
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
import requests  # 引入 requests 以捕获异常
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

# Timeout (seconds) for efinance library calls that go through eastmoney APIs
# with no built-in timeout.  Prevents indefinite hangs when hosts are unreachable.
try:
    _EF_CALL_TIMEOUT = int(os.environ.get("EFINANCE_CALL_TIMEOUT", "30"))
except (ValueError, TypeError):
    import logging as _logging
    _logging.getLogger("data_provider.efinance_fetcher").warning(
        "EFINANCE_CALL_TIMEOUT is not a valid integer, using default 30s"
    )
    _EF_CALL_TIMEOUT = 30

from src.patches.eastmoney_patch import eastmoney_patch
from src.config import get_config
from data_provider.common.fetcher_contract import BaseFetcher, STANDARD_COLUMNS
from data_provider.common.errors import DataFetchError, RateLimitError
from src.domain.market.stock_codes import is_bse_code, is_st_stock, is_kc_cy_stock, normalize_stock_code, is_a_share_etf_code as _is_a_share_etf_code
from data_provider.common.symbols import _is_hk_market
from data_provider.realtime.types import UnifiedRealtimeQuote, RealtimeSource, safe_float, safe_int
from data_provider.common.health import get_realtime_circuit_breaker
from data_provider.clients.efinance import call_with_timeout, _classify_eastmoney_error, _is_us_code
from data_provider.kline.daily_efinance_source import build_eastmoney_etf_secid, build_history_failure_message


# 保留旧的类型别名，用于向后兼容
from data_provider.realtime.efinance_source import EfinanceRealtimeQuote


logger = logging.getLogger("data_provider.efinance_fetcher")

# 兼容导出同一协议常量；错误格式化和其他能力继续使用原名称。
from data_provider.kline.daily_efinance_source import (
    EASTMONEY_HISTORY_ENDPOINT,
    EfinanceDailySource,
)


# User-Agent 池，用于随机轮换
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]


# 缓存实时行情数据（避免重复请求）
# TTL 设为 10 分钟 (600秒)：批量分析场景下避免重复拉取
_realtime_cache: Dict[str, Any] = {
    'data': None,
    'timestamp': 0,
    'ttl': 600  # 10分钟缓存有效期
}

# ETF 实时行情缓存（与股票分开缓存）
_etf_realtime_cache: Dict[str, Any] = {
    'data': None,
    'timestamp': 0,
    'ttl': 600  # 10分钟缓存有效期
}



def _is_etf_code(stock_code: str) -> bool:
    """
    判断代码是否为 ETF 基金
    
    ETF 代码规则：
    - 上交所 ETF: 51xxxx, 52xxxx, 56xxxx, 58xxxx
    - 深交所 ETF: 15xxxx, 16xxxx, 18xxxx
    
    Args:
        stock_code: 股票/基金代码
        
    Returns:
        True 表示是 ETF 代码，False 表示是普通股票代码
    """
    return _is_a_share_etf_code(stock_code)


def _build_eastmoney_etf_secid(stock_code: str) -> str:
    return build_eastmoney_etf_secid(stock_code, is_etf=_is_etf_code)




def _ef_call_with_timeout(func, *args, timeout=None, **kwargs):
    """保留原配置读取时机，线程执行由共享协议辅助承担。"""
    return call_with_timeout(func, *args, default_timeout=_EF_CALL_TIMEOUT, timeout=timeout, **kwargs)




class EfinanceFetcher(BaseFetcher):
    """
    Efinance 数据源实现
    
    优先级：0（最高，优先于 AkshareFetcher）
    数据来源：东方财富网（通过 efinance 库封装）
    仓库：https://github.com/Micro-sheep/efinance
    
    主要 API：
    - ef.stock.get_quote_history(): 获取历史 K 线数据
    - ef.stock.get_base_info(): 获取股票基本信息
    - ef.stock.get_realtime_quotes(): 获取实时行情
    
    关键策略：
    - 每次请求前随机休眠 1.5-3.0 秒
    - 随机 User-Agent 轮换
    - 失败后指数退避重试（最多3次）
    """
    
    name = "EfinanceFetcher"
    priority = int(os.getenv("EFINANCE_PRIORITY", "0"))  # 最高优先级，排在 AkshareFetcher 之前
    
    def __init__(self, sleep_min: float = 1.5, sleep_max: float = 3.0):
        """
        初始化 EfinanceFetcher
        
        Args:
            sleep_min: 最小休眠时间（秒）
            sleep_max: 最大休眠时间（秒）
        """
        self.sleep_min = sleep_min
        self.sleep_max = sleep_max
        self._last_request_time: Optional[float] = None
        # 东财补丁开启才执行打补丁操作
        if get_config().enable_eastmoney_patch:
            eastmoney_patch()

    @staticmethod
    def _build_history_failure_message(
        stock_code: str,
        beg_date: str,
        end_date: str,
        exc: Exception,
        elapsed: float,
        is_etf: bool = False,
    ) -> Tuple[str, str]:
        return build_history_failure_message(stock_code, beg_date, end_date, exc, elapsed, is_etf)

    def _set_random_user_agent(self) -> None:
        return self._shared_client_access()._set_random_user_agent()
    
    def _enforce_rate_limit(self) -> None:
        return self._shared_client_access()._enforce_rate_limit()
    
    @retry(
        stop=stop_after_attempt(1),  # 减少到1次，避免触发限流
        wait=wait_exponential(multiplier=1, min=4, max=60),  # 保持等待时间设置
        retry=retry_if_exception_type((
            ConnectionError,
            TimeoutError,
            requests.exceptions.RequestException,
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_raw_data(
        self, stock_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        return self._daily_routing()._fetch_raw_data(stock_code, start_date, end_date)
    
    def _prepare_history_request(self) -> None:
        return self._shared_client_access()._prepare_history_request()

    def _daily_history_source(self) -> EfinanceDailySource:
        """与旧历史方法一致，先导入 SDK，再执行请求准备；不持有第二份源状态。"""
        import efinance as ef

        return EfinanceDailySource(
            history_call=lambda **kwargs: _ef_call_with_timeout(
                ef.stock.get_quote_history, **kwargs
            ),
            prepare_request=self._prepare_history_request,
            history_failure=self._build_history_failure_message,
            etf_secid=_build_eastmoney_etf_secid,
        )

    def _fetch_stock_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """旧调用入口，委托同一日线协议实现并保留当前实例的节流。"""
        return self._daily_history_source().fetch_stock(stock_code, start_date, end_date)

    def _fetch_etf_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """ETF 继续使用 stock 历史接口及原显式市场参数。"""
        return self._daily_history_source().fetch_etf(stock_code, start_date, end_date)
    
    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """保留旧标准化入口，纯本地转换不触发 SDK 导入。"""
        return EfinanceDailySource.normalize_data(df, stock_code)
    
    def _realtime_source(self):
        """复用原实例及模块的实时资源、旧替换入口和降级路径。"""
        from data_provider.realtime.efinance_source import EfinanceRealtimeOperations

        return EfinanceRealtimeOperations(
            use_get_etf_realtime_quote=self._get_etf_realtime_quote,
            use_enforce_rate_limit=self._enforce_rate_limit,
            use_set_random_user_agent=self._set_random_user_agent,
            call_is_etf_code=lambda *args, **kwargs: _is_etf_code(*args, **kwargs),
            call_get_realtime_circuit_breaker=lambda *args, **kwargs: get_realtime_circuit_breaker(
                *args, **kwargs
            ),
            call_ef_call_with_timeout=lambda *args, **kwargs: _ef_call_with_timeout(
                *args, **kwargs
            ),
            read_ef_call_timeout=lambda: _EF_CALL_TIMEOUT,
            read_realtime_cache=lambda: _realtime_cache,
            read_etf_realtime_cache=lambda: _etf_realtime_cache,
            read_time=lambda: time,
        )

    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        return self._realtime_source().get_realtime_quote(stock_code)

    def _get_etf_realtime_quote(
        self, stock_code: str
    ) -> Optional[UnifiedRealtimeQuote]:
        return self._realtime_source().get_etf_realtime_quote(stock_code)

    def _market_index_source(self):
        """按需接线市场原始数据实现，保持原状态和旧替换入口。"""
        from data_provider.market.indices import EfinanceIndices

        return EfinanceIndices(
            use_enforce_rate_limit=lambda *args, **kwargs: self._enforce_rate_limit(
                *args, **kwargs
            ),
            use_set_random_user_agent=lambda *args, **kwargs: self._set_random_user_agent(
                *args, **kwargs
            ),
            call_ef_call_with_timeout=lambda *args, **kwargs: _ef_call_with_timeout(
                *args, **kwargs
            ),
            call_safe_float=lambda *args, **kwargs: safe_float(*args, **kwargs),
            read_logger=lambda: logger,
        )

    def get_main_indices(self, region: str = "cn") -> Optional[List[Dict[str, Any]]]:
        return self._market_index_source().get_main_indices(region)

    def _market_statistics_source(self):
        """按需接线市场原始数据实现，保持原状态和旧替换入口。"""
        from data_provider.market.statistics import EfinanceStatistics

        return EfinanceStatistics(
            use_calc_market_stats=lambda *args, **kwargs: self._calc_market_stats(
                *args, **kwargs
            ),
            use_enforce_rate_limit=lambda *args, **kwargs: self._enforce_rate_limit(
                *args, **kwargs
            ),
            use_set_random_user_agent=lambda *args, **kwargs: self._set_random_user_agent(
                *args, **kwargs
            ),
            call_ef_call_with_timeout=lambda *args, **kwargs: _ef_call_with_timeout(
                *args, **kwargs
            ),
            read_logger=lambda: logger,
            read_time=lambda: time,
            read_realtime_cache=lambda: _realtime_cache,
        )

    def get_market_stats(self) -> Optional[Dict[str, Any]]:
        return self._market_statistics_source().get_market_stats()
        
    def _calc_market_stats(
        self,
        df: pd.DataFrame,
    ) -> Optional[Dict[str, Any]]:
        from data_provider.market.statistics import calculate_market_stats

        return calculate_market_stats(
            df,
            normalize=normalize_stock_code,
            is_bse=is_bse_code,
            is_kc_cy=is_kc_cy_stock,
            is_st=is_st_stock,
        )

    def _sector_source(self):
        """按需加载能力实现，保留原缓存/SDK/诊断与动态替换入口。"""
        from data_provider.sector.efinance_source import EfinanceSectorOperations

        return EfinanceSectorOperations(
            use_enforce_rate_limit=lambda *args, **kwargs: self._enforce_rate_limit(
                *args, **kwargs
            ),
            use_set_random_user_agent=lambda *args, **kwargs: self._set_random_user_agent(
                *args, **kwargs
            ),
            call_ef_call_with_timeout=lambda *args, **kwargs: _ef_call_with_timeout(
                *args, **kwargs
            ),
            read_logger=lambda: logger,
            read_ef_call_timeout=lambda: _EF_CALL_TIMEOUT,
        )

    def get_sector_rankings(
        self, n: int = 5
    ) -> Optional[Tuple[List[Dict], List[Dict]]]:
        return self._sector_source().get_sector_rankings(n)
    
    def get_base_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        return self._base_info_source().get_base_info(stock_code)
    
    def get_belong_board(self, stock_code: str) -> Optional[pd.DataFrame]:
        return self._sector_source().get_belong_board(stock_code)
    
    def get_enhanced_data(self, stock_code: str, days: int = 60) -> Dict[str, Any]:
        return self._enhanced_data_source().get_enhanced_data(stock_code, days)

    def _daily_routing(self):
        """接线唯一能力实现，沿用原资源和方法扩展点。"""
        from data_provider.kline.daily_efinance_source import EfinanceDailyRouting

        return EfinanceDailyRouting(
            use_fetch_etf_data=lambda *args, **kwargs: self._fetch_etf_data(
                *args, **kwargs
            ),
            use_fetch_stock_data=lambda *args, **kwargs: self._fetch_stock_data(
                *args, **kwargs
            ),
            read_global_is_us_code=lambda: _is_us_code,
            read_global_is_hk_market=lambda: _is_hk_market,
            read_global_is_etf_code=lambda: _is_etf_code,
        )


    def _base_info_source(self):
        """接线唯一能力实现，沿用原资源和方法扩展点。"""
        from data_provider.stock_info.catalog import EfinanceBaseInfo

        return EfinanceBaseInfo(
            use_enforce_rate_limit=lambda *args, **kwargs: self._enforce_rate_limit(
                *args, **kwargs
            ),
            use_set_random_user_agent=lambda *args, **kwargs: self._set_random_user_agent(
                *args, **kwargs
            ),
            read_global_logger=lambda: logger,
            read_global_ef_call_with_timeout=lambda: _ef_call_with_timeout,
        )


    def _enhanced_data_source(self):
        """接线唯一能力实现，沿用原资源和方法扩展点。"""
        from data_provider.realtime.enrichment import EfinanceEnhancedData

        return EfinanceEnhancedData(
            use_get_base_info=lambda *args, **kwargs: self.get_base_info(*args, **kwargs),
            use_get_belong_board=lambda *args, **kwargs: self.get_belong_board(
                *args, **kwargs
            ),
            use_get_daily_data=lambda *args, **kwargs: self.get_daily_data(*args, **kwargs),
            use_get_realtime_quote=lambda *args, **kwargs: self.get_realtime_quote(
                *args, **kwargs
            ),
            read_global_logger=lambda: logger,
        )

    def _shared_client_access(self):
        """接线共享协议；显式复用原资源，不传递整个宿主。"""
        from data_provider.clients.efinance import EfinanceClientAccess

        return EfinanceClientAccess(
            use_enforce_rate_limit=lambda *args, **kwargs: self._enforce_rate_limit(
                *args, **kwargs
            ),
            use_set_random_user_agent=lambda *args, **kwargs: self._set_random_user_agent(
                *args, **kwargs
            ),
            use_random_sleep=lambda *args, **kwargs: self.random_sleep(*args, **kwargs),
            read_last_request_time=lambda: self._last_request_time,
            read_sleep_max=lambda: self.sleep_max,
            read_sleep_min=lambda: self.sleep_min,
            write_last_request_time=lambda value: setattr(
                self, "_last_request_time", value
            ),
            read_global_USER_AGENTS=lambda: USER_AGENTS,
            read_global_logger=lambda: logger,
            read_global_random=lambda: random,
            read_global_time=lambda: time,
        )


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    fetcher = EfinanceFetcher()
    
    # 测试普通股票
    print("=" * 50)
    print("测试普通股票数据获取 (efinance)")
    print("=" * 50)
    try:
        df = fetcher.get_daily_data('600519')  # 茅台
        print(f"[股票] 获取成功，共 {len(df)} 条数据")
        print(df.tail())
    except Exception as e:
        print(f"[股票] 获取失败: {e}")
    
    # 测试 ETF 基金
    print("\n" + "=" * 50)
    print("测试 ETF 基金数据获取 (efinance)")
    print("=" * 50)
    try:
        df = fetcher.get_daily_data('512400')  # 有色龙头ETF
        print(f"[ETF] 获取成功，共 {len(df)} 条数据")
        print(df.tail())
    except Exception as e:
        print(f"[ETF] 获取失败: {e}")
    
    # 测试实时行情
    print("\n" + "=" * 50)
    print("测试实时行情获取 (efinance)")
    print("=" * 50)
    try:
        quote = fetcher.get_realtime_quote('600519')
        if quote:
            print(f"[实时行情] {quote.name}: 价格={quote.price}, 涨跌幅={quote.change_pct}%")
        else:
            print("[实时行情] 未获取到数据")
    except Exception as e:
        print(f"[实时行情] 获取失败: {e}")
    
    # 测试基本信息
    print("\n" + "=" * 50)
    print("测试基本信息获取 (efinance)")
    print("=" * 50)
    try:
        info = fetcher.get_base_info('600519')
        if info:
            print(f"[基本信息] 市盈率={info.get('市盈率(动)', 'N/A')}, 市净率={info.get('市净率', 'N/A')}")
        else:
            print("[基本信息] 未获取到数据")
    except Exception as e:
        print(f"[基本信息] 获取失败: {e}")

    # 测试市场统计 
    print("\n" + "=" * 50)
    print("Testing get_market_stats (efinance)")
    print("=" * 50)
    try:
        stats = fetcher.get_market_stats()
        if stats:
            print(f"Market Stats successfully computed:")
            print(f"Up: {stats['up_count']} (Limit Up: {stats['limit_up_count']})")
            print(f"Down: {stats['down_count']} (Limit Down: {stats['limit_down_count']})")
            print(f"Flat: {stats['flat_count']}")
            print(f"Total Amount: {stats['total_amount']:.2f} 亿 (Yi)")
        else:
            print("Failed to compute market stats.")
    except Exception as e:
        print(f"Failed to compute market stats: {e}")
