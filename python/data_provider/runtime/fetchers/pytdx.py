# -*- coding: utf-8 -*-
"""
===================================
PytdxFetcher - 通达信数据源 (Priority 2)
===================================

数据来源：通达信行情服务器（pytdx 库）
特点：免费、无需 Token、直连行情服务器
优点：实时数据、稳定、无配额限制

关键策略：
1. 多服务器自动切换
2. 连接超时自动重连
3. 失败后指数退避重试
"""

import logging
import re
import time
from contextlib import contextmanager
from typing import Optional, Generator, List, Tuple

import pandas as pd
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from data_provider.common.fetcher_contract import BaseFetcher, STANDARD_COLUMNS
from data_provider.common.errors import DataFetchError, DataSourceUnavailableError
from src.domain.market.stock_codes import is_bse_code, normalize_stock_code
from data_provider.common.symbols import _is_hk_market
import os

from data_provider.kline.daily_pytdx_source import PytdxDailySource
from data_provider.clients.pytdx import _parse_hosts_from_env, _is_us_code, get_market_code

logger = logging.getLogger("data_provider.pytdx_fetcher")

_PYTDX_CONNECTION_COOLDOWN_SECONDS = 15.0






class PytdxFetcher(BaseFetcher):
    """
    通达信数据源实现
    
    优先级：2（与 Tushare 同级）
    数据来源：通达信行情服务器
    
    关键策略：
    - 自动选择最优服务器
    - 连接失败自动切换服务器
    - 失败后指数退避重试
    
    Pytdx 特点：
    - 免费、无需注册
    - 直连行情服务器
    - 支持实时行情和历史数据
    - 支持股票名称查询
    """
    
    name = "PytdxFetcher"
    priority = int(os.getenv("PYTDX_PRIORITY", "2"))
    
    # 默认通达信行情服务器列表
    DEFAULT_HOSTS = [
        ("119.147.212.81", 7709),  # 深圳
        ("112.74.214.43", 7727),   # 深圳
        ("221.231.141.60", 7709),  # 上海
        ("101.227.73.20", 7709),   # 上海
        ("101.227.77.254", 7709),  # 上海
        ("14.215.128.18", 7709),   # 广州
        ("59.173.18.140", 7709),   # 武汉
        ("180.153.39.51", 7709),   # 杭州
    ]
    # Pytdx get_security_list returns at most 1000 items per page
    SECURITY_LIST_PAGE_SIZE = 1000
    
    def __init__(self, hosts: Optional[List[Tuple[str, int]]] = None):
        """
        初始化 PytdxFetcher

        Args:
            hosts: 服务器列表 [(host, port), ...]。若未传入，优先使用环境变量
                   PYTDX_SERVERS（ip:port,ip:port）或 PYTDX_HOST+PYTDX_PORT，
                   否则使用内置 DEFAULT_HOSTS。
        """
        if hosts is not None:
            self._hosts = hosts
        else:
            env_hosts = _parse_hosts_from_env()
            self._hosts = env_hosts if env_hosts else self.DEFAULT_HOSTS
        self._api = None
        self._connected = False
        self._current_host_idx = 0
        self._stock_list_cache = None  # 股票列表缓存
        self._stock_name_cache = {}    # 股票名称缓存 {code: name}
        self._unavailable_until = 0.0
        self._last_unavailable_reason = ""

    def _is_in_connection_cooldown(self) -> bool:
        return self._shared_client_access()._is_in_connection_cooldown()

    def _mark_connection_cooldown(self, reason: str) -> None:
        return self._shared_client_access()._mark_connection_cooldown(reason)

    def is_available_for_request(self, capability: str = "") -> bool:
        return self._shared_client_access().is_available_for_request(capability)
    
    def _get_pytdx(self):
        return self._shared_client_access()._get_pytdx()
    
    @contextmanager
    def _pytdx_session(self) -> Generator:
        return self._shared_client_access()._pytdx_session()
    
    def _get_market_code(self, stock_code: str) -> Tuple[int, str]:
        """委托 Pytdx 协议转换，不持有新资源。"""
        return get_market_code(stock_code)

    def _stock_catalog(self):
        """按需加载名称/清单实现，复用原状态及旧替换入口。"""
        from data_provider.stock_info.catalog import PytdxCatalog

        return PytdxCatalog(
            read_security_list_page_size=lambda: self.SECURITY_LIST_PAGE_SIZE,
            read_stock_list_cache=lambda: self._stock_list_cache,
            write_stock_list_cache=lambda value: setattr(
                self, "_stock_list_cache", value
            ),
            log=lambda: logger,
        )

    def _build_stock_list_cache(self, api) -> None:
        return self._stock_catalog().build_stock_list_cache(api)
    
    def _daily_history_source(self) -> PytdxDailySource:
        """复用原宿主的代码转换、会话及市场判断。"""
        return PytdxDailySource(
            market_code=self._get_market_code, session=self._pytdx_session,
            is_us=_is_us_code, is_hk=_is_hk_market, is_bse=is_bse_code
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._daily_history_source().fetch_raw_data(stock_code, start_date, end_date)
    
    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        return self._daily_history_source().normalize_data(df, stock_code)
    
    def _stock_names(self):
        """按需加载名称/清单实现，复用原状态及旧替换入口。"""
        from data_provider.stock_info.name_lookup import PytdxNameLookup

        return PytdxNameLookup(
            use_build_stock_list_cache=lambda *args, **kwargs: self._build_stock_list_cache(
                *args, **kwargs
            ),
            use_get_market_code=lambda *args, **kwargs: self._get_market_code(
                *args, **kwargs
            ),
            use_pytdx_session=lambda *args, **kwargs: self._pytdx_session(
                *args, **kwargs
            ),
            read_stock_list_cache=lambda: self._stock_list_cache,
            read_stock_name_cache=lambda: self._stock_name_cache,
            call_is_hk_market=lambda *args, **kwargs: _is_hk_market(*args, **kwargs),
            log=lambda: logger,
        )

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        return self._stock_names().get_stock_name(stock_code)
    
    def _realtime_source(self):
        """复用原实例及模块的实时资源、旧替换入口和降级路径。"""
        from data_provider.realtime.pytdx_source import PytdxRealtimeOperations

        return PytdxRealtimeOperations(
            use_get_market_code=self._get_market_code,
            use_pytdx_session=self._pytdx_session,
            call_is_bse_code=lambda *args, **kwargs: is_bse_code(*args, **kwargs),
        )

    def get_realtime_quote(self, stock_code: str) -> Optional[dict]:
        return self._realtime_source().get_realtime_quote(stock_code)

    def _shared_client_access(self):
        """接线共享协议；显式复用原资源，不传递整个宿主。"""
        from data_provider.clients.pytdx import PytdxClientAccess

        return PytdxClientAccess(
            use_get_pytdx=lambda *args, **kwargs: self._get_pytdx(*args, **kwargs),
            use_is_in_connection_cooldown=lambda *args, **kwargs: self._is_in_connection_cooldown(
                *args, **kwargs
            ),
            use_mark_connection_cooldown=lambda *args, **kwargs: self._mark_connection_cooldown(
                *args, **kwargs
            ),
            read_current_host_idx=lambda: self._current_host_idx,
            read_hosts=lambda: self._hosts,
            read_last_unavailable_reason=lambda: self._last_unavailable_reason,
            read_unavailable_until=lambda: self._unavailable_until,
            write_current_host_idx=lambda value: setattr(self, "_current_host_idx", value),
            write_last_unavailable_reason=lambda value: setattr(
                self, "_last_unavailable_reason", value
            ),
            write_unavailable_until=lambda value: setattr(
                self, "_unavailable_until", value
            ),
            read_global_DataFetchError=lambda: DataFetchError,
            read_global_DataSourceUnavailableError=lambda: DataSourceUnavailableError,
            read_global_PYTDX_CONNECTION_COOLDOWN_SECONDS=lambda: _PYTDX_CONNECTION_COOLDOWN_SECONDS,
            read_global_logger=lambda: logger,
            read_global_time=lambda: time,
        )


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    fetcher = PytdxFetcher()
    
    try:
        # 测试历史数据
        df = fetcher.get_daily_data('600519')  # 茅台
        print(f"获取成功，共 {len(df)} 条数据")
        print(df.tail())
        
        # 测试股票名称
        name = fetcher.get_stock_name('600519')
        print(f"股票名称: {name}")
        
        # 测试实时行情
        quote = fetcher.get_realtime_quote('600519')
        print(f"实时行情: {quote}")
        
    except Exception as e:
        print(f"获取失败: {e}")
