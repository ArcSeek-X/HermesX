# -*- coding: utf-8 -*-
"""
===================================
AkshareFetcher - 主数据源 (Priority 1)
===================================

数据来源：
1. 东方财富爬虫（通过 akshare 库） - 默认数据源
2. 新浪财经接口 - 备选数据源
3. 腾讯财经接口 - 备选数据源

特点：免费、无需 Token、数据全面
风险：爬虫机制易被反爬封禁

防封禁策略：
1. 每次请求前随机休眠 2-5 秒
2. 随机轮换 User-Agent
3. 使用 tenacity 实现指数退避重试
4. 熔断器机制：连续失败后自动冷却

增强数据：
- 实时行情：量比、换手率、市盈率、市净率、总市值、流通市值
- 筹码分布：获利比例、平均成本、筹码集中度
"""

import logging
import multiprocessing
import os
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from src.patches.eastmoney_patch import eastmoney_patch
from src.config import get_config
# 港股判定规则已下沉 domain（R3-S14）；保留模块级别名，兼容既有
# `from data_provider.runtime.fetchers.akshare import _is_hk_code` 调用面。
from src.domain.market.stock_codes import is_hk_stock_code as _is_hk_code  # noqa: F401
from data_provider.common.fetcher_contract import BaseFetcher, STANDARD_COLUMNS
from data_provider.common.errors import DataFetchError, RateLimitError
from src.domain.market.stock_codes import is_bse_code, is_st_stock, is_kc_cy_stock, normalize_stock_code
from data_provider.realtime.types import UnifiedRealtimeQuote, ChipDistribution, RealtimeSource, safe_float, safe_int
from data_provider.common.health import get_realtime_circuit_breaker, get_chip_circuit_breaker
from src.domain.market.us_index_symbols import is_us_index_code, is_us_stock_code
from data_provider.kline.daily_akshare_source import AkshareDailySource
from data_provider.clients.akshare.client import (
    _AKSHARE_HISTORY_CALL_TIMEOUT,
    _AKSHARE_TIMEOUT_PROCESS_JOIN_GRACE,
    _AKSHARE_TIMEOUT_PROCESS_START_METHOD,
    _is_etf_code,
    _to_sina_tx_symbol,
    _akshare_call_with_timeout,
    _akshare_timeout_worker,
    _terminate_akshare_process,
    safe_float as parse_akshare_float,
    safe_int as parse_akshare_int,
    find_first_column,
    find_column_containing,
)
from data_provider.realtime.akshare_source import (
    _normalize_tencent_volume,
    _parse_tencent_amount,
    _classify_realtime_http_error,
    _build_realtime_failure_message,
)
from data_provider.limit_pool.akshare_source import (
    normalize_limit_time_value,
)


# 保留旧的 RealtimeQuote 别名，用于向后兼容
RealtimeQuote = UnifiedRealtimeQuote


logger = logging.getLogger("data_provider.akshare_fetcher")

SINA_REALTIME_ENDPOINT = "hq.sinajs.cn/list"
TENCENT_REALTIME_ENDPOINT = "qt.gtimg.cn/q"


# User-Agent 池，用于随机轮换
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]


# 缓存实时行情数据（避免重复请求）
# TTL 设为 20 分钟 (1200秒)：
# - 批量分析场景：通常 30 只股票在 5 分钟内分析完，20 分钟足够覆盖
# - 实时性要求：股票分析不需要秒级实时数据，20 分钟延迟可接受
# - 防封禁：减少 API 调用频率
_realtime_cache: Dict[str, Any] = {
    'data': None,
    'timestamp': 0,
    'ttl': 1200  # 20分钟缓存有效期
}

# ETF 实时行情缓存
_etf_realtime_cache: Dict[str, Any] = {
    'data': None,
    'timestamp': 0,
    'ttl': 1200  # 20分钟缓存有效期
}

# 港股实时行情缓存。stock_hk_spot_em() 返回全市场数据，单次调用成本较高。
_hk_realtime_cache: Dict[str, Any] = {
    'data': None,
    'timestamp': 0,
    'ttl': 1200,  # 20分钟缓存有效期
    'failure_ttl': 30,
    'last_result': None,
}
_hk_realtime_cache_lock = threading.Lock()








def is_hk_stock_code(stock_code: str) -> bool:
    """
    Public API: determine if a stock code is a Hong Kong stock.

    Delegates to _is_hk_code for internal compatibility.

    Args:
        stock_code: Stock code (e.g. '00700', 'hk00700')

    Returns:
        True if HK stock, False otherwise
    """
    return _is_hk_code(stock_code)


def _is_us_code(stock_code: str) -> bool:
    """
    判断代码是否为美股股票（不包括美股指数）。

    委托给 us_index_mapping 模块的 is_us_stock_code()。

    Args:
        stock_code: 股票代码

    Returns:
        True 表示是美股代码，False 表示不是美股代码

    Examples:
        >>> _is_us_code('AAPL')
        True
        >>> _is_us_code('TSLA')
        True
        >>> _is_us_code('SPX')
        False
        >>> _is_us_code('600519')
        False
    """
    return is_us_stock_code(stock_code)














class AkshareFetcher(BaseFetcher):
    """
    Akshare 数据源实现

    优先级：1（最高）
    数据来源：东方财富网爬虫

    关键策略：
    - 每次请求前随机休眠 2.0-5.0 秒
    - 随机 User-Agent 轮换
    - 失败后指数退避重试（最多3次）
    """

    name = "AkshareFetcher"
    priority = int(os.getenv("AKSHARE_PRIORITY", "1"))

    def __init__(self, sleep_min: float = 2.0, sleep_max: float = 5.0,
                 realtime_sleep_min: float = 0.0, realtime_sleep_max: float = 0.3):
        """
        初始化 AkshareFetcher

        Args:
            sleep_min: 最小休眠时间（秒，用于 K 线等全量爬取防封）
            sleep_max: 最大休眠时间（秒，用于 K 线等全量爬取防封）
            realtime_sleep_min: 实时行情（单股直连）最小休眠时间（秒），默认近乎 0
            realtime_sleep_max: 实时行情（单股直连）最大休眠时间（秒），默认 0.3
        """
        self.sleep_min = sleep_min
        self.sleep_max = sleep_max
        self.realtime_sleep_min = realtime_sleep_min
        self.realtime_sleep_max = realtime_sleep_max
        self._last_request_time: Optional[float] = None
        self._history_call_timeout = _AKSHARE_HISTORY_CALL_TIMEOUT
        # 东财补丁开启才执行打补丁操作
        if get_config().enable_eastmoney_patch:
            eastmoney_patch()

    def _set_random_user_agent(self) -> None:
        return self._shared_client_access()._set_random_user_agent()

    def _enforce_rate_limit(self) -> None:
        return self._shared_client_access()._enforce_rate_limit()

    def _enforce_realtime_rate_limit(self) -> None:
        return self._shared_client_access()._enforce_realtime_rate_limit()

    @retry(
        stop=stop_after_attempt(3),  # 最多重试3次
        wait=wait_exponential(multiplier=1, min=2, max=30),  # 指数退避：2, 4, 8... 最大30秒
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_raw_data(
        self, stock_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        return self._daily_routing()._fetch_raw_data(stock_code, start_date, end_date)

    def _daily_history_source(self) -> AkshareDailySource:
        """不初始化新 SDK 或状态；超时值与调用函数在实际请求时从旧宿主读取。"""
        return AkshareDailySource(
            set_user_agent=self._set_random_user_agent,
            rate_limit=self._enforce_rate_limit,
            call_with_timeout=lambda *args, **kwargs: _akshare_call_with_timeout(*args, **kwargs),
            history_timeout=lambda: self._history_call_timeout,
            to_symbol=_to_sina_tx_symbol,
        )

    def _fetch_stock_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """兼容入口；委托日线组件，保留当前实例的限流与原渠道覆盖点。"""
        return self._daily_history_source().fetch_stock_data(
            stock_code, start_date, end_date,
            channels=[
                (self._fetch_stock_data_em, "东方财富"),
                (self._fetch_stock_data_sina, "新浪财经"),
                (self._fetch_stock_data_tx, "腾讯财经"),
            ],
        )

    def _fetch_stock_data_em(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """兼容入口；委托日线组件，保留当前实例的限流与原渠道覆盖点。"""
        return self._daily_history_source().fetch_stock_data_em(stock_code, start_date, end_date)

    def _fetch_stock_data_sina(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """兼容入口；委托日线组件，保留当前实例的限流与原渠道覆盖点。"""
        return self._daily_history_source().fetch_stock_data_sina(stock_code, start_date, end_date)

    def _fetch_stock_data_tx(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """兼容入口；委托日线组件，保留当前实例的限流与原渠道覆盖点。"""
        return self._daily_history_source().fetch_stock_data_tx(stock_code, start_date, end_date)

    def _fetch_etf_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """兼容入口；委托日线组件，保留当前实例的限流与原渠道覆盖点。"""
        return self._daily_history_source().fetch_etf_data(stock_code, start_date, end_date)

    def _fetch_us_data(
        self, stock_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        return self._daily_routing()._fetch_us_data(stock_code, start_date, end_date)

    def _fetch_hk_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """兼容入口；委托日线组件，保留当前实例的限流与原渠道覆盖点。"""
        return self._daily_history_source().fetch_hk_data(stock_code, start_date, end_date)

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """兼容入口；委托日线组件，保留当前实例的限流与原渠道覆盖点。"""
        return AkshareDailySource.normalize_data(df, stock_code)

    def _realtime_source(self):
        """读取原模块缓存/熔断/传输及原实例节流，保持旧替换入口。"""
        from data_provider.realtime.akshare_source import AkshareRealtimeOperations

        return AkshareRealtimeOperations(
            hk_quote=self._get_hk_realtime_quote,
            etf_quote=self._get_etf_realtime_quote,
            sina_quote=self._get_stock_realtime_quote_sina,
            tencent_quote=self._get_stock_realtime_quote_tencent,
            em_quote=self._get_stock_realtime_quote_em,
            set_random_user_agent=self._set_random_user_agent,
            enforce_rate_limit=self._enforce_rate_limit,
            enforce_realtime_rate_limit=self._enforce_realtime_rate_limit,
            get_realtime_circuit_breaker=lambda *args, **kwargs: get_realtime_circuit_breaker(
                *args, **kwargs
            ),
            is_us_code=lambda *args, **kwargs: _is_us_code(*args, **kwargs),
            is_hk_code=lambda *args, **kwargs: _is_hk_code(*args, **kwargs),
            is_etf_code=lambda *args, **kwargs: _is_etf_code(*args, **kwargs),
            build_realtime_failure_message=lambda *args, **kwargs: _build_realtime_failure_message(
                *args, **kwargs
            ),
            classify_realtime_http_error=lambda *args, **kwargs: _classify_realtime_http_error(
                *args, **kwargs
            ),
            to_sina_tx_symbol=lambda *args, **kwargs: _to_sina_tx_symbol(
                *args, **kwargs
            ),
            normalize_tencent_volume=lambda *args, **kwargs: _normalize_tencent_volume(
                *args, **kwargs
            ),
            parse_tencent_amount=lambda *args, **kwargs: _parse_tencent_amount(
                *args, **kwargs
            ),
            stock_cache=lambda: _realtime_cache,
            etf_cache=lambda: _etf_realtime_cache,
            hk_cache=lambda: _hk_realtime_cache,
            hk_cache_lock=lambda: _hk_realtime_cache_lock,
            sina_endpoint=lambda: SINA_REALTIME_ENDPOINT,
            tencent_endpoint=lambda: TENCENT_REALTIME_ENDPOINT,
            user_agents=lambda: USER_AGENTS,
            clock=lambda: time,
            transport=lambda: requests,
            randomizer=lambda: random,
        )

    def get_realtime_quote(
        self, stock_code: str, source: str = "em"
    ) -> Optional[UnifiedRealtimeQuote]:
        return self._realtime_source().get_realtime_quote(stock_code, source=source)

    def _get_stock_realtime_quote_em(
        self, stock_code: str
    ) -> Optional[UnifiedRealtimeQuote]:
        return self._realtime_source().get_stock_realtime_quote_em(stock_code)

    def get_realtime_quote_snapshot(self) -> Optional["pd.DataFrame"]:
        return self._realtime_source().get_realtime_quote_snapshot()

    def _get_stock_realtime_quote_sina(
        self, stock_code: str
    ) -> Optional[UnifiedRealtimeQuote]:
        return self._realtime_source().get_stock_realtime_quote_sina(stock_code)

    def _get_stock_realtime_quote_tencent(
        self, stock_code: str
    ) -> Optional[UnifiedRealtimeQuote]:
        return self._realtime_source().get_stock_realtime_quote_tencent(stock_code)

    def _get_etf_realtime_quote(
        self, stock_code: str
    ) -> Optional[UnifiedRealtimeQuote]:
        return self._realtime_source().get_etf_realtime_quote(stock_code)

    def _get_hk_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        return self._realtime_source().get_hk_realtime_quote(stock_code)

    def _chip_source(self):
        """按需接线筹码实现，使用原资源及 domain 规则。"""
        from data_provider.chip.akshare_source import AkshareChipSource

        return AkshareChipSource(
            use_enforce_rate_limit=lambda *args, **kwargs: self._enforce_rate_limit(
                *args, **kwargs
            ),
            use_set_random_user_agent=lambda *args, **kwargs: self._set_random_user_agent(
                *args, **kwargs
            ),
            call_is_us_code=lambda *args, **kwargs: _is_us_code(*args, **kwargs),
            call_is_hk_code=lambda *args, **kwargs: _is_hk_code(*args, **kwargs),
            call_is_etf_code=lambda *args, **kwargs: _is_etf_code(*args, **kwargs),
            call_safe_float=lambda *args, **kwargs: safe_float(*args, **kwargs),
            read_logger=lambda: logger,
        )

    def get_chip_distribution(self, stock_code: str) -> Optional[ChipDistribution]:
        return self._chip_source().get_chip_distribution(stock_code)

    def get_enhanced_data(self, stock_code: str, days: int = 60) -> Dict[str, Any]:
        return self._enhanced_data_source().get_enhanced_data(stock_code, days)

    def _market_index_source(self):
        """按需接线市场原始数据实现，保持原状态和旧替换入口。"""
        from data_provider.market.indices import AkshareIndices

        return AkshareIndices(
            use_enforce_rate_limit=lambda *args, **kwargs: self._enforce_rate_limit(
                *args, **kwargs
            ),
            use_set_random_user_agent=lambda *args, **kwargs: self._set_random_user_agent(
                *args, **kwargs
            ),
            call_safe_float=lambda *args, **kwargs: safe_float(*args, **kwargs),
            read_logger=lambda: logger,
        )

    def get_main_indices(self, region: str = "cn") -> Optional[List[Dict[str, Any]]]:
        return self._market_index_source().get_main_indices(region)

    def _market_statistics_source(self):
        """按需接线市场原始数据实现，保持原状态和旧替换入口。"""
        from data_provider.market.statistics import AkshareStatistics

        return AkshareStatistics(
            use_calc_market_stats=lambda *args, **kwargs: self._calc_market_stats(
                *args, **kwargs
            ),
            use_enforce_rate_limit=lambda *args, **kwargs: self._enforce_rate_limit(
                *args, **kwargs
            ),
            use_set_random_user_agent=lambda *args, **kwargs: self._set_random_user_agent(
                *args, **kwargs
            ),
            read_logger=lambda: logger,
            read_time=lambda: time,
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
        from data_provider.sector.akshare_source import AkshareSectorOperations

        return AkshareSectorOperations(
            use_enforce_rate_limit=lambda *args, **kwargs: self._enforce_rate_limit(
                *args, **kwargs
            ),
            use_find_column_containing=lambda *args, **kwargs: self._find_column_containing(
                *args, **kwargs
            ),
            use_find_first_column=lambda *args, **kwargs: self._find_first_column(
                *args, **kwargs
            ),
            use_get_eastmoney_hot_stocks=lambda *args, **kwargs: self._get_eastmoney_hot_stocks(
                *args, **kwargs
            ),
            use_get_eastmoney_hot_up_stocks=lambda *args, **kwargs: self._get_eastmoney_hot_up_stocks(
                *args, **kwargs
            ),
            use_get_xueqiu_hot_stocks=lambda *args, **kwargs: self._get_xueqiu_hot_stocks(
                *args, **kwargs
            ),
            use_safe_float=lambda *args, **kwargs: self._safe_float(*args, **kwargs),
            use_safe_int=lambda *args, **kwargs: self._safe_int(*args, **kwargs),
            use_set_random_user_agent=lambda *args, **kwargs: self._set_random_user_agent(
                *args, **kwargs
            ),
            read_logger=lambda: logger,
        )

    def get_sector_rankings(
        self, n: int = 5
    ) -> Optional[Tuple[List[Dict], List[Dict]]]:
        return self._sector_source().get_sector_rankings(n)

    def get_concept_rankings(
        self, n: int = 5
    ) -> Optional[Tuple[List[Dict], List[Dict]]]:
        return self._sector_source().get_concept_rankings(n)

    def get_hot_stocks(self, n: int = 10) -> Optional[List[Dict[str, Any]]]:
        return self._sector_source().get_hot_stocks(n)

    def _get_eastmoney_hot_stocks(
        self, ak: Any, n: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        return self._sector_source().get_eastmoney_hot_stocks(ak, n)

    def _get_eastmoney_hot_up_stocks(
        self, ak: Any, n: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        return self._sector_source().get_eastmoney_hot_up_stocks(ak, n)

    def _get_xueqiu_hot_stocks(
        self, ak: Any, n: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        return self._sector_source().get_xueqiu_hot_stocks(ak, n)

    def _limit_pool_source(self):
        """按需加载能力实现，保留原缓存/SDK/诊断与动态替换入口。"""
        from data_provider.limit_pool.akshare_source import AkshareLimitPoolOperations

        return AkshareLimitPoolOperations(
            use_enforce_realtime_rate_limit=lambda *args, **kwargs: self._enforce_realtime_rate_limit(
                *args, **kwargs
            ),
            use_normalize_limit_time_value=lambda *args, **kwargs: self._normalize_limit_time_value(
                *args, **kwargs
            ),
            use_safe_float=lambda *args, **kwargs: self._safe_float(*args, **kwargs),
            use_safe_int=lambda *args, **kwargs: self._safe_int(*args, **kwargs),
            use_set_random_user_agent=lambda *args, **kwargs: self._set_random_user_agent(
                *args, **kwargs
            ),
            read_logger=lambda: logger,
            read_datetime=lambda: datetime,
        )

    def get_limit_up_pool(
        self,
        date: Optional[str] = None,
        n: int = 20,
    ) -> Optional[List[Dict[str, Any]]]:
        return self._limit_pool_source().get_limit_up_pool(date, n)

    def get_limit_down_pool(
        self,
        date: Optional[str] = None,
        n: int = 20,
    ) -> Optional[List[Dict[str, Any]]]:
        return self._limit_pool_source().get_limit_down_pool(date, n)

    @staticmethod
    def _normalize_limit_time_value(value: Any) -> str:
        """委托协议解析，保留原静态覆盖入口。"""
        return normalize_limit_time_value(value)

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """委托协议解析，保留原静态覆盖入口。"""
        return parse_akshare_float(value)

    @staticmethod
    def _safe_int(value: Any) -> int:
        """委托协议解析，保留原静态覆盖入口。"""
        return parse_akshare_int(value)

    @staticmethod
    def _find_first_column(df: pd.DataFrame, candidates: Tuple[str, ...]) -> Optional[str]:
        """委托协议解析，保留原静态覆盖入口。"""
        return find_first_column(df, candidates)

    @staticmethod
    def _find_column_containing(df: pd.DataFrame, keywords: Tuple[str, ...]) -> Optional[str]:
        """委托协议解析，保留原静态覆盖入口。"""
        return find_column_containing(df, keywords)

    def _daily_routing(self):
        """接线唯一能力实现，沿用原资源和方法扩展点。"""
        from data_provider.kline.daily_akshare_source import AkshareDailyRouting

        return AkshareDailyRouting(
            use_enforce_rate_limit=lambda *args, **kwargs: self._enforce_rate_limit(
                *args, **kwargs
            ),
            use_fetch_etf_data=lambda *args, **kwargs: self._fetch_etf_data(
                *args, **kwargs
            ),
            use_fetch_hk_data=lambda *args, **kwargs: self._fetch_hk_data(*args, **kwargs),
            use_fetch_stock_data=lambda *args, **kwargs: self._fetch_stock_data(
                *args, **kwargs
            ),
            use_set_random_user_agent=lambda *args, **kwargs: self._set_random_user_agent(
                *args, **kwargs
            ),
            read_global_logger=lambda: logger,
            read_global_is_us_code=lambda: _is_us_code,
            read_global_is_hk_code=lambda: _is_hk_code,
            read_global_is_etf_code=lambda: _is_etf_code,
        )


    def _enhanced_data_source(self):
        """接线唯一能力实现，沿用原资源和方法扩展点。"""
        from data_provider.realtime.enrichment import AkshareEnhancedData

        return AkshareEnhancedData(
            use_get_chip_distribution=lambda *args, **kwargs: self.get_chip_distribution(
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
        from data_provider.clients.akshare.client import AkshareClientAccess

        return AkshareClientAccess(
            use_random_sleep=lambda *args, **kwargs: self.random_sleep(*args, **kwargs),
            read_last_request_time=lambda: self._last_request_time,
            read_realtime_sleep_max=lambda: self.realtime_sleep_max,
            read_realtime_sleep_min=lambda: self.realtime_sleep_min,
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

    fetcher = AkshareFetcher()

    # 测试普通股票
    print("=" * 50)
    print("测试普通股票数据获取")
    print("=" * 50)
    try:
        df = fetcher.get_daily_data('600519')  # 茅台
        print(f"[股票] 获取成功，共 {len(df)} 条数据")
        print(df.tail())
    except Exception as e:
        print(f"[股票] 获取失败: {e}")

    # 测试 ETF 基金
    print("\n" + "=" * 50)
    print("测试 ETF 基金数据获取")
    print("=" * 50)
    try:
        df = fetcher.get_daily_data('512400')  # 有色龙头ETF
        print(f"[ETF] 获取成功，共 {len(df)} 条数据")
        print(df.tail())
    except Exception as e:
        print(f"[ETF] 获取失败: {e}")

    # 测试 ETF 实时行情
    print("\n" + "=" * 50)
    print("测试 ETF 实时行情获取")
    print("=" * 50)
    try:
        quote = fetcher.get_realtime_quote('512880')  # 证券ETF
        if quote:
            print(f"[ETF实时] {quote.name}: 价格={quote.price}, 涨跌幅={quote.change_pct}%")
        else:
            print("[ETF实时] 未获取到数据")
    except Exception as e:
        print(f"[ETF实时] 获取失败: {e}")

    # 测试港股历史数据
    print("\n" + "=" * 50)
    print("测试港股历史数据获取")
    print("=" * 50)
    try:
        df = fetcher.get_daily_data('00700')  # 腾讯控股
        print(f"[港股] 获取成功，共 {len(df)} 条数据")
        print(df.tail())
    except Exception as e:
        print(f"[港股] 获取失败: {e}")

    # 测试港股实时行情
    print("\n" + "=" * 50)
    print("测试港股实时行情获取")
    print("=" * 50)
    try:
        quote = fetcher.get_realtime_quote('00700')  # 腾讯控股
        if quote:
            print(f"[港股实时] {quote.name}: 价格={quote.price}, 涨跌幅={quote.change_pct}%")
        else:
            print("[港股实时] 未获取到数据")
    except Exception as e:
        print(f"[港股实时] 获取失败: {e}")

    # 测试市场统计
    print("\n" + "=" * 50)
    print("Testing get_market_stats (akshare)")
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

    # 测试筹码分布数据
    print("\n" + "=" * 50)
    print("测试筹码分布数据获取")
    print("=" * 50)
    try:
        chip = fetcher.get_chip_distribution('600519')  # 茅台
    except Exception as e:
        print(f"[筹码分布] 获取失败: {e}")

    # 测试行业板块排名
    print("\n" + "=" * 50)
    print("测试行业板块排名获取")
    print("=" * 50)
    try:
        rankings = fetcher.get_sector_rankings(n=5)
        if rankings:
            top, bottom = rankings
            print("涨幅榜 Top 5:")
            for sector in top:
                print(f"{sector['name']}: {sector['change_pct']}%")
            print("\n跌幅榜 Top 5:")
            for sector in bottom:
                print(f"{sector['name']}: {sector['change_pct']}%")
        else:
            print("未获取到行业板块排名数据")
    except Exception as e:
        print(f"[行业板块排名] 获取失败: {e}")
