# -*- coding: utf-8 -*-
"""
===================================
TushareFetcher - 备用数据源 1 (Priority 2)
===================================

数据来源：Tushare Pro API（挖地兔）
特点：需要 Token、有请求配额限制
优点：数据质量高、接口稳定

流控策略：
1. 实现"每分钟调用计数器"
2. 超过免费配额（80次/分）时，强制休眠到下一分钟
3. 使用 tenacity 实现指数退避重试
"""

from data_provider.kline.daily_tushare_source import TushareDailySource

import json as _json
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any

import pandas as pd
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from data_provider.common.fetcher_contract import BaseFetcher, STANDARD_COLUMNS
from data_provider.common.errors import DataFetchError, RateLimitError
from src.domain.market.stock_codes import is_bse_code, is_st_stock, is_kc_cy_stock, normalize_stock_code
from data_provider.common.symbols import _is_hk_market
from data_provider.realtime.types import UnifiedRealtimeQuote, ChipDistribution
from src.config import get_config
import os
from zoneinfo import ZoneInfo

logger = logging.getLogger("data_provider.tushare_fetcher")


# ETF code prefixes by exchange
# Shanghai: 51xxxx, 52xxxx, 56xxxx, 58xxxx
# Shenzhen: 15xxxx, 16xxxx, 18xxxx








from data_provider.clients.tushare.http import _TushareHttpClient, _resolve_tushare_http_url
from data_provider.clients.tushare.client import (
    _ETF_SH_PREFIXES, _ETF_SZ_PREFIXES, _ETF_ALL_PREFIXES, _is_etf_code, _is_us_code,
    pick_trade_date, detect_exchange_hint, get_legacy_realtime_symbol,
    convert_stock_code, convert_hk_stock_code,
)


class TushareFetcher(BaseFetcher):
    """
    Tushare Pro 数据源实现
    
    优先级：2
    数据来源：Tushare Pro API
    
    关键策略：
    - 每分钟调用计数器，防止超出配额
    - 超过 80 次/分钟时强制等待
    - 失败后指数退避重试
    
    配额说明（Tushare 免费用户）：
    - 每分钟最多 80 次请求
    - 每天最多 500 次请求
    """
    
    name = "TushareFetcher"
    priority = int(os.getenv("TUSHARE_PRIORITY", "2"))  # 默认优先级，会在 __init__ 中根据配置动态调整

    def __init__(self, rate_limit_per_minute: int = 80):
        """
        初始化 TushareFetcher

        Args:
            rate_limit_per_minute: 每分钟最大请求数（默认80，Tushare免费配额）
        """
        self.rate_limit_per_minute = rate_limit_per_minute
        self._call_count = 0  # 当前分钟内的调用次数
        self._minute_start: Optional[float] = None  # 当前计数周期开始时间
        self._api: Optional[object] = None  # Tushare API 实例
        self.date_list: Optional[List[str]] = None  # 交易日列表缓存（倒序，最新日期在前）
        self._date_list_end: Optional[str] = None  # 缓存对应的截止日期，用于跨日刷新

        # 尝试初始化 API
        self._init_api()

        # 根据 API 初始化结果动态调整优先级
        self.priority = self._determine_priority()
    
    def _init_api(self) -> None:
        return self._shared_client_access()._init_api()

    def _build_api_client(self, token: str) -> _TushareHttpClient:
        return self._shared_client_access()._build_api_client(token)

    def _determine_priority(self) -> int:
        """
        根据 Token 配置和 API 初始化状态确定优先级

        策略：
        - Token 配置且 API 初始化成功：优先级 -1（绝对最高，优于 efinance）
        - 其他情况：优先级 2（默认）

        Returns:
            优先级数字（0=最高，数字越大优先级越低）
        """
        config = get_config()

        if config.tushare_token and self._api is not None:
            # Token 配置且 API 初始化成功，提升为最高优先级
            logger.info("✅ 检测到 TUSHARE_TOKEN 且 API 初始化成功，Tushare 数据源优先级提升为最高 (Priority -1)")
            return -1

        # Token 未配置或 API 初始化失败，保持默认优先级
        return 2

    def is_available(self) -> bool:
        """
        检查数据源是否可用

        Returns:
            True 表示可用，False 表示不可用
        """
        return self._api is not None

    def _check_rate_limit(self) -> None:
        return self._shared_client_access()._check_rate_limit()

    def _call_api_with_rate_limit(self, method_name: str, **kwargs) -> pd.DataFrame:
        return self._shared_client_access()._call_api_with_rate_limit(method_name, **kwargs)

    def _get_china_now(self) -> datetime:
        return self._shared_client_access()._get_china_now()

    def _get_trade_dates(self, end_date: Optional[str] = None) -> List[str]:
        return self._shared_client_access()._get_trade_dates(end_date)

    @staticmethod
    def _pick_trade_date(trade_dates: List[str], use_today: bool) -> Optional[str]:
        """委托 Tushare 协议辅助，保留原覆盖点。"""
        return pick_trade_date(trade_dates, use_today)

    @staticmethod
    def _detect_exchange_hint(stock_code: str) -> Optional[str]:
        """委托 Tushare 协议辅助，保留原覆盖点。"""
        return detect_exchange_hint(stock_code)

    @classmethod
    def _get_legacy_realtime_symbol(cls, stock_code: str) -> str:
        """委托 Tushare 协议辅助，保留原覆盖点。"""
        return get_legacy_realtime_symbol(stock_code, detect_exchange_hint=cls._detect_exchange_hint)
    
    def _convert_stock_code(self, stock_code: str) -> str:
        """委托 Tushare 协议辅助，保留原覆盖点。"""
        return convert_stock_code(stock_code, detect_exchange_hint=self._detect_exchange_hint, is_hk=_is_hk_market, logger=logger)

    def _convert_hk_stock_code_for_tushare(self, stock_code: str) -> str:
        """委托 Tushare 协议辅助，保留原覆盖点。"""
        return convert_hk_stock_code(stock_code, is_hk=_is_hk_market, convert_stock_code=self._convert_stock_code)

    def _daily_history_source(self) -> TushareDailySource:
        """API 在原访问时机读取，保留跨能力共享的限额与 SDK 模式。"""
        return TushareDailySource(
            get_api=lambda: self._api,
            rate_limit=self._check_rate_limit,
            convert_hk=self._convert_hk_stock_code_for_tushare,
            convert_code=self._convert_stock_code,
            is_us=_is_us_code,
            is_hk=_is_hk_market,
            is_etf=_is_etf_code,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """旧入口保留原重试/覆盖点；协议与单位转换委托同一实现。"""
        return self._daily_history_source().fetch_raw_data(stock_code, start_date, end_date)
    
    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """旧入口保留原重试/覆盖点；协议与单位转换委托同一实现。"""
        return self._daily_history_source().normalize_data(df, stock_code)

    def _stock_names(self):
        """按需加载名称/清单实现，复用原状态及旧替换入口。"""
        from data_provider.stock_info.name_lookup import TushareNameLookup

        return TushareNameLookup(
            use_check_rate_limit=lambda *args, **kwargs: self._check_rate_limit(
                *args, **kwargs
            ),
            use_convert_hk_stock_code_for_tushare=lambda *args, **kwargs: self._convert_hk_stock_code_for_tushare(
                *args, **kwargs
            ),
            use_convert_stock_code=lambda *args, **kwargs: self._convert_stock_code(
                *args, **kwargs
            ),
            read_api=lambda: self._api,
            read_stock_name_cache=lambda: self._stock_name_cache,
            write_stock_name_cache=lambda value: setattr(
                self, "_stock_name_cache", value
            ),
            has_stock_name_cache=lambda: hasattr(self, "_stock_name_cache"),
            call_is_etf_code=lambda *args, **kwargs: _is_etf_code(*args, **kwargs),
            call_is_hk_market=lambda *args, **kwargs: _is_hk_market(*args, **kwargs),
            log=lambda: logger,
        )

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        return self._stock_names().get_stock_name(stock_code)
    
    def _stock_catalog(self):
        """按需加载名称/清单实现，复用原状态及旧替换入口。"""
        from data_provider.stock_info.catalog import TushareCatalog

        return TushareCatalog(
            use_check_rate_limit=lambda *args, **kwargs: self._check_rate_limit(
                *args, **kwargs
            ),
            read_api=lambda: self._api,
            read_stock_name_cache=lambda: self._stock_name_cache,
            write_stock_name_cache=lambda value: setattr(
                self, "_stock_name_cache", value
            ),
            has_stock_name_cache=lambda: hasattr(self, "_stock_name_cache"),
            log=lambda: logger,
        )

    def get_stock_list(self) -> Optional[pd.DataFrame]:
        return self._stock_catalog().get_stock_list()
    
    def _realtime_source(self):
        """复用原实例及模块的实时资源、旧替换入口和降级路径。"""
        from data_provider.realtime.tushare_source import TushareRealtimeOperations

        return TushareRealtimeOperations(
            use_check_rate_limit=self._check_rate_limit,
            use_convert_stock_code=self._convert_stock_code,
            use_get_legacy_realtime_symbol=self._get_legacy_realtime_symbol,
            current_api=lambda: self._api,
            call_is_hk_market=lambda *args, **kwargs: _is_hk_market(*args, **kwargs),
        )

    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        return self._realtime_source().get_realtime_quote(stock_code)

    def _market_index_source(self):
        """按需接线市场原始数据实现，保持原状态和旧替换入口。"""
        from data_provider.market.indices import TushareIndices

        return TushareIndices(
            use_check_rate_limit=lambda *args, **kwargs: self._check_rate_limit(
                *args, **kwargs
            ),
            current_api=lambda: self._api,
            read_logger=lambda: logger,
            read_datetime=lambda: datetime,
        )

    def get_main_indices(self, region: str = "cn") -> Optional[List[dict]]:
        return self._market_index_source().get_main_indices(region)

    def _market_statistics_source(self):
        """按需接线市场原始数据实现，保持原状态和旧替换入口。"""
        from data_provider.market.statistics import TushareStatistics

        return TushareStatistics(
            use_calc_market_stats=lambda *args, **kwargs: self._calc_market_stats(
                *args, **kwargs
            ),
            use_call_api_with_rate_limit=lambda *args, **kwargs: self._call_api_with_rate_limit(
                *args, **kwargs
            ),
            use_get_china_now=lambda *args, **kwargs: self._get_china_now(
                *args, **kwargs
            ),
            use_get_trade_dates=lambda *args, **kwargs: self._get_trade_dates(
                *args, **kwargs
            ),
            use_pick_trade_date=lambda *args, **kwargs: self._pick_trade_date(
                *args, **kwargs
            ),
            current_api=lambda: self._api,
            read_logger=lambda: logger,
        )

    def get_market_stats(self) -> Optional[dict]:
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

    def get_trade_time(self, early_time="09:30", late_time="16:30") -> Optional[str]:
        return self._shared_client_access().get_trade_time(early_time, late_time)
    
    def _sector_source(self):
        """按需加载能力实现，保留原缓存/SDK/诊断与动态替换入口。"""
        from data_provider.sector.tushare_source import TushareSectorOperations

        return TushareSectorOperations(
            use_call_api_with_rate_limit=lambda *args, **kwargs: self._call_api_with_rate_limit(
                *args, **kwargs
            ),
            use_get_trade_time=lambda *args, **kwargs: self.get_trade_time(
                *args, **kwargs
            ),
            read_logger=lambda: logger,
        )

    def get_sector_rankings(self, n: int = 5) -> Optional[Tuple[list, list]]:
        return self._sector_source().get_sector_rankings(n)
    
    

    
    def _chip_source(self):
        """按需接线筹码实现，使用原资源及 domain 规则。"""
        from data_provider.chip.tushare_source import TushareChipSource

        return TushareChipSource(
            use_call_api_with_rate_limit=lambda *args, **kwargs: self._call_api_with_rate_limit(
                *args, **kwargs
            ),
            use_convert_stock_code=lambda *args, **kwargs: self._convert_stock_code(
                *args, **kwargs
            ),
            use_compute_cyq_metrics=lambda *args, **kwargs: self.compute_cyq_metrics(
                *args, **kwargs
            ),
            use_get_trade_time=lambda *args, **kwargs: self.get_trade_time(
                *args, **kwargs
            ),
            call_is_us_code=lambda *args, **kwargs: _is_us_code(*args, **kwargs),
            call_is_etf_code=lambda *args, **kwargs: _is_etf_code(*args, **kwargs),
            call_is_hk_market=lambda *args, **kwargs: _is_hk_market(*args, **kwargs),
            read_logger=lambda: logger,
            read_datetime=lambda: datetime,
        )

    def get_chip_distribution(self, stock_code: str) -> Optional[ChipDistribution]:
        return self._chip_source().get_chip_distribution(stock_code)

    def compute_cyq_metrics(self, df: pd.DataFrame, current_price: float) -> dict:
        from src.domain.analysis.chip_rules import compute_cyq_metrics

        return compute_cyq_metrics(df, current_price)

    def _shared_client_access(self):
        """接线共享协议；显式复用原资源，不传递整个宿主。"""
        from data_provider.clients.tushare.client import TushareClientAccess

        return TushareClientAccess(
            use_build_api_client=lambda *args, **kwargs: self._build_api_client(
                *args, **kwargs
            ),
            use_call_api_with_rate_limit=lambda *args, **kwargs: self._call_api_with_rate_limit(
                *args, **kwargs
            ),
            use_check_rate_limit=lambda *args, **kwargs: self._check_rate_limit(
                *args, **kwargs
            ),
            use_get_china_now=lambda *args, **kwargs: self._get_china_now(*args, **kwargs),
            use_get_trade_dates=lambda *args, **kwargs: self._get_trade_dates(
                *args, **kwargs
            ),
            use_pick_trade_date=lambda *args, **kwargs: self._pick_trade_date(
                *args, **kwargs
            ),
            read_api=lambda: self._api,
            read_call_count=lambda: self._call_count,
            read_date_list_end=lambda: self._date_list_end,
            read_minute_start=lambda: self._minute_start,
            read_date_list=lambda: self.date_list,
            read_rate_limit_per_minute=lambda: self.rate_limit_per_minute,
            write_api=lambda value: setattr(self, "_api", value),
            write_call_count=lambda value: setattr(self, "_call_count", value),
            write_date_list_end=lambda value: setattr(self, "_date_list_end", value),
            write_minute_start=lambda value: setattr(self, "_minute_start", value),
            write_date_list=lambda value: setattr(self, "date_list", value),
            read_global_DataFetchError=lambda: DataFetchError,
            read_global_ZoneInfo=lambda: ZoneInfo,
            read_global_TushareHttpClient=lambda: _TushareHttpClient,
            read_global_resolve_tushare_http_url=lambda: _resolve_tushare_http_url,
            read_global_datetime=lambda: datetime,
            read_global_get_config=lambda: get_config,
            read_global_logger=lambda: logger,
            read_global_time=lambda: time,
            read_global_timedelta=lambda: timedelta,
        )



if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    fetcher = TushareFetcher()
    
    try:
        # 测试历史数据
        df = fetcher.get_daily_data('600519')  # 茅台
        print(f"获取成功，共 {len(df)} 条数据")
        print(df.tail())
        
        # 测试股票名称
        name = fetcher.get_stock_name('600519')
        print(f"股票名称: {name}")
        
    except Exception as e:
        print(f"获取失败: {e}")

    # 测试市场统计
    print("\n" + "=" * 50)
    print("Testing get_market_stats (tushare)")
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
