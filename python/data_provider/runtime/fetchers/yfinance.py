# -*- coding: utf-8 -*-
"""
===================================
YfinanceFetcher - 兜底数据源 (Priority 4)
===================================

数据来源：Yahoo Finance（通过 yfinance 库）
特点：国际数据源、可能有延迟或缺失
定位：当所有国内数据源都失败时的最后保障

关键策略：
1. 自动将 A 股代码转换为 yfinance 格式（.SS / .SZ）
2. 处理 Yahoo Finance 的数据格式差异
3. 失败后指数退避重试
"""

import csv
import logging
from datetime import datetime
from io import StringIO
from typing import Optional, List, Dict, Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
from src.domain.market.stock_codes import is_bse_code
from data_provider.realtime.types import UnifiedRealtimeQuote, RealtimeSource
from data_provider.common.symbols import get_us_index_yf_symbol, convert_yfinance_symbol
from src.domain.market.us_index_symbols import is_us_stock_code
from data_provider.fundamentals.yfinance_source import _safe_float
from src.domain.market.market_symbol_utils import get_suffix_market, is_suffix_market_symbol

# 可选导入本地股票映射补丁，若缺失则使用空字典兜底
try:
    from src.data.stock_mapping import STOCK_NAME_MAP, is_meaningful_stock_name
except (ImportError, ModuleNotFoundError):
    STOCK_NAME_MAP = {}

    def is_meaningful_stock_name(name: str | None, stock_code: str) -> bool:
        """简单的名称有效性校验兜底"""
        if not name:
            return False
        n = str(name).strip()
        return bool(n and n.upper() != str(stock_code).strip().upper())

import os

from data_provider.kline.daily_yfinance_source import YfinanceDailySource

logger = logging.getLogger("data_provider.yfinance_fetcher")


class YfinanceFetcher(BaseFetcher):
    """
    Yahoo Finance 数据源实现

    优先级：4（最低，作为兜底）
    数据来源：Yahoo Finance

    关键策略：
    - 自动转换股票代码格式
    - 处理时区和数据格式差异
    - 失败后指数退避重试

    注意事项：
    - A 股数据可能有延迟
    - 某些股票可能无数据
    - 数据精度可能与国内源略有差异
    """

    name = "YfinanceFetcher"
    priority = int(os.getenv("YFINANCE_PRIORITY", "4"))

    def __init__(self):
        """初始化 YfinanceFetcher"""
        pass

    @staticmethod
    def _is_jp_kr_suffix_stock(stock_code: str) -> bool:
        """Return True for supported JP/KR suffix-only Yahoo symbols."""
        return is_suffix_market_symbol(stock_code, "jp") or is_suffix_market_symbol(stock_code, "kr")

    @staticmethod
    def _is_tw_suffix_stock(stock_code: str) -> bool:
        """Return True for supported Taiwan suffix-only Yahoo symbols (TWSE `.TW` / TPEx `.TWO`).

        Taiwan base codes are 4-6 digits (common stocks 4, ETFs/others up to 6,
        e.g. 00878 / 006208), wider than the JP `.T` range.
        """
        return is_suffix_market_symbol(stock_code, "tw")

    def _convert_stock_code(self, stock_code: str) -> str:
        """委托唯一协议转换，保留原能力覆盖点。"""
        return convert_yfinance_symbol(
            stock_code, is_jp_kr=self._is_jp_kr_suffix_stock,
            is_tw=self._is_tw_suffix_stock, is_bse=is_bse_code, logger=logger,
        )

    def _daily_history_source(self) -> YfinanceDailySource:
        """复用原宿主的代码转换、会话及市场判断。"""
        return YfinanceDailySource(
            convert_code=self._convert_stock_code
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

    def _market_index_source(self):
        """按需接线市场原始数据实现，保持原状态和旧替换入口。"""
        from data_provider.market.indices import YfinanceIndices

        return YfinanceIndices(
            use_fetch_yf_ticker_data=lambda *args, **kwargs: self._fetch_yf_ticker_data(
                *args, **kwargs
            ),
            use_get_hk_main_indices=lambda *args, **kwargs: self._get_hk_main_indices(
                *args, **kwargs
            ),
            use_get_jp_main_indices=lambda *args, **kwargs: self._get_jp_main_indices(
                *args, **kwargs
            ),
            use_get_kr_main_indices=lambda *args, **kwargs: self._get_kr_main_indices(
                *args, **kwargs
            ),
            use_get_tw_main_indices=lambda *args, **kwargs: self._get_tw_main_indices(
                *args, **kwargs
            ),
            use_get_us_main_indices=lambda *args, **kwargs: self._get_us_main_indices(
                *args, **kwargs
            ),
            call_get_us_index_yf_symbol=lambda *args, **kwargs: get_us_index_yf_symbol(
                *args, **kwargs
            ),
            read_logger=lambda: logger,
        )

    def _fetch_yf_ticker_data(
        self, yf, yf_code: str, name: str, return_code: str
    ) -> Optional[Dict[str, Any]]:
        return self._market_index_source().fetch_yf_ticker_data(
            yf, yf_code, name, return_code
        )

    def get_main_indices(self, region: str = "cn") -> Optional[List[Dict[str, Any]]]:
        return self._market_index_source().get_main_indices(region)

    def _get_us_main_indices(self, yf) -> Optional[List[Dict[str, Any]]]:
        return self._market_index_source().get_us_main_indices(yf)

    def _get_hk_main_indices(self, yf) -> Optional[List[Dict[str, Any]]]:
        return self._market_index_source().get_hk_main_indices(yf)

    def _get_jp_main_indices(self, yf) -> Optional[List[Dict[str, Any]]]:
        return self._market_index_source().get_jp_main_indices(yf)

    def _get_kr_main_indices(self, yf) -> Optional[List[Dict[str, Any]]]:
        return self._market_index_source().get_kr_main_indices(yf)

    def _get_tw_main_indices(self, yf) -> Optional[List[Dict[str, Any]]]:
        return self._market_index_source().get_tw_main_indices(yf)

    def _is_us_stock(self, stock_code: str) -> bool:
        """
        判断代码是否为美股股票（排除美股指数）。

        委托给 us_index_mapping 模块的 is_us_stock_code()。
        """
        return is_us_stock_code(stock_code)

    def _realtime_source(self):
        """复用原实例及模块的实时资源、旧替换入口和降级路径。"""
        from data_provider.realtime.yfinance_source import YfinanceRealtimeOperations

        return YfinanceRealtimeOperations(
            use_convert_stock_code=self._convert_stock_code,
            use_get_us_index_realtime_quote=self._get_us_index_realtime_quote,
            use_get_us_stock_quote_from_stooq=self._get_us_stock_quote_from_stooq,
            use_is_jp_kr_suffix_stock=self._is_jp_kr_suffix_stock,
            use_is_tw_suffix_stock=self._is_tw_suffix_stock,
            use_is_us_stock=self._is_us_stock,
            call_safe_float=lambda *args, **kwargs: _safe_float(*args, **kwargs),
            call_get_suffix_market=lambda *args, **kwargs: get_suffix_market(
                *args, **kwargs
            ),
            call_get_us_index_yf_symbol=lambda *args, **kwargs: get_us_index_yf_symbol(
                *args, **kwargs
            ),
            call_is_meaningful_stock_name=lambda *args, **kwargs: is_meaningful_stock_name(
                *args, **kwargs
            ),
            call_urlopen=lambda *args, **kwargs: urlopen(*args, **kwargs),
            read_stock_name_map=lambda: STOCK_NAME_MAP,
        )

    def _get_us_stock_quote_from_stooq(
        self, stock_code: str
    ) -> Optional[UnifiedRealtimeQuote]:
        return self._realtime_source().get_us_stock_quote_from_stooq(stock_code)

    def _get_us_index_realtime_quote(
        self,
        user_code: str,
        yf_symbol: str,
        index_name: str,
    ) -> Optional[UnifiedRealtimeQuote]:
        return self._realtime_source().get_us_index_realtime_quote(
            user_code, yf_symbol, index_name
        )

    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        return self._realtime_source().get_realtime_quote(stock_code)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)

    fetcher = YfinanceFetcher()

    try:
        df = fetcher.get_daily_data('600519')  # 茅台
        print(f"获取成功，共 {len(df)} 条数据")
        print(df.tail())
    except Exception as e:
        print(f"获取失败: {e}")
