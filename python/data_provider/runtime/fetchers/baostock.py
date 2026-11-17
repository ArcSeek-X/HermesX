# -*- coding: utf-8 -*-
"""
===================================
BaostockFetcher - 备用数据源 2 (Priority 3)
===================================

数据来源：证券宝（Baostock）
特点：免费、无需 Token、需要登录管理
优点：稳定、无配额限制

关键策略：
1. 管理 bs.login() 和 bs.logout() 生命周期
2. 使用上下文管理器防止连接泄露
3. 失败后指数退避重试
"""

import logging
import re
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Generator

import pandas as pd
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from data_provider.common.fetcher_contract import BaseFetcher, STANDARD_COLUMNS
from data_provider.common.errors import DataFetchError
from src.domain.market.stock_codes import is_bse_code, normalize_stock_code
from data_provider.common.symbols import _is_hk_market
import os

from data_provider.kline.daily_baostock_source import BaostockDailySource

logger = logging.getLogger("data_provider.baostock_fetcher")


from data_provider.clients.baostock import _is_us_code, convert_stock_code


class BaostockFetcher(BaseFetcher):
    """
    Baostock 数据源实现
    
    优先级：3
    数据来源：证券宝 Baostock API
    
    关键策略：
    - 使用上下文管理器管理连接生命周期
    - 每次请求都重新登录/登出，防止连接泄露
    - 失败后指数退避重试
    
    Baostock 特点：
    - 免费、无需注册
    - 需要显式登录/登出
    - 数据更新略有延迟（T+1）
    """
    
    name = "BaostockFetcher"
    priority = int(os.getenv("BAOSTOCK_PRIORITY", "3"))
    
    def __init__(self):
        """初始化 BaostockFetcher"""
        self._bs_module = None
    
    def _get_baostock(self):
        return self._shared_client_access()._get_baostock()
    
    @contextmanager
    def _baostock_session(self) -> Generator:
        return self._shared_client_access()._baostock_session()
    
    def _convert_stock_code(self, stock_code: str) -> str:
        """委托唯一协议转换，保留原能力覆盖点。"""
        return convert_stock_code(stock_code, is_hk=_is_hk_market, logger=logger)
    
    def _daily_history_source(self) -> BaostockDailySource:
        """复用原宿主的代码转换、会话及市场判断。"""
        return BaostockDailySource(
            convert_code=self._convert_stock_code, session=self._baostock_session,
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
        from data_provider.stock_info.name_lookup import BaostockNameLookup

        return BaostockNameLookup(
            use_baostock_session=lambda *args, **kwargs: self._baostock_session(
                *args, **kwargs
            ),
            use_convert_stock_code=lambda *args, **kwargs: self._convert_stock_code(
                *args, **kwargs
            ),
            read_stock_name_cache=lambda: self._stock_name_cache,
            write_stock_name_cache=lambda value: setattr(
                self, "_stock_name_cache", value
            ),
            has_stock_name_cache=lambda: hasattr(self, "_stock_name_cache"),
            log=lambda: logger,
        )

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        return self._stock_names().get_stock_name(stock_code)
    
    def _stock_catalog(self):
        """按需加载名称/清单实现，复用原状态及旧替换入口。"""
        from data_provider.stock_info.catalog import BaostockCatalog

        return BaostockCatalog(
            use_baostock_session=lambda *args, **kwargs: self._baostock_session(
                *args, **kwargs
            ),
            read_stock_name_cache=lambda: self._stock_name_cache,
            write_stock_name_cache=lambda value: setattr(
                self, "_stock_name_cache", value
            ),
            has_stock_name_cache=lambda: hasattr(self, "_stock_name_cache"),
            log=lambda: logger,
        )

    def get_stock_list(self) -> Optional[pd.DataFrame]:
        return self._stock_catalog().get_stock_list()

    def _shared_client_access(self):
        """接线共享协议；显式复用原资源，不传递整个宿主。"""
        from data_provider.clients.baostock import BaostockClientAccess

        return BaostockClientAccess(
            use_get_baostock=lambda *args, **kwargs: self._get_baostock(*args, **kwargs),
            read_bs_module=lambda: self._bs_module,
            write_bs_module=lambda value: setattr(self, "_bs_module", value),
            read_global_DataFetchError=lambda: DataFetchError,
            read_global_logger=lambda: logger,
        )


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    fetcher = BaostockFetcher()
    
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
