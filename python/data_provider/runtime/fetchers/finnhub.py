# -*- coding: utf-8 -*-
"""
FinnhubFetcher — US market data source (Priority 2)

Data source: Finnhub.io REST API
Rate limit: 60 calls/min (free tier)
Markets: US only

美股行情数据源（优先级 2）。通过 Finnhub REST API 获取美股历史日线与实时报价，
免费档限制每分钟 60 次调用；仅处理美股代码，其余市场直接返回空结果。
"""

import logging
import os
from datetime import datetime
from typing import Optional

import pandas as pd
import requests

from data_provider.common.fetcher_contract import BaseFetcher, STANDARD_COLUMNS
from data_provider.common.errors import DataFetchError
from data_provider.realtime.types import UnifiedRealtimeQuote, RealtimeSource
from src.domain.market.us_index_symbols import is_us_stock_code

from data_provider.kline.daily_finnhub_source import FinnhubDailySource

logger = logging.getLogger("data_provider.finnhub_fetcher")

_FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


class FinnhubFetcher(BaseFetcher):
    """Finnhub 美股数据抓取器：实现历史日线、实时报价与股票名称查询。"""

    name = "FinnhubFetcher"
    priority = 2

    def __init__(self):
        """构造抓取器：从配置或环境变量读取 Finnhub API key。"""
        from src.config import get_config
        config = get_config()
        self._api_key = getattr(config, 'finnhub_api_key', None) or os.getenv('FINNHUB_API_KEY')
        if not self._api_key:
            logger.debug("[Finnhub] API key not configured, fetcher disabled")

    def _is_us_stock(self, stock_code: str) -> bool:
        """判断股票代码是否属于美股（本数据源仅支持美股）。"""
        return is_us_stock_code(stock_code)

    def _daily_history_source(self) -> FinnhubDailySource:
        """复用原有连接、凭证、缓存与错误处理入口。"""
        return FinnhubDailySource(
            api_key=lambda: self._api_key, is_us=self._is_us_stock, sleep=self.random_sleep,
            http_get=lambda *args, **kwargs: requests.get(*args, **kwargs),
            base_url=lambda: _FINNHUB_BASE_URL
        )

    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._daily_history_source().fetch_raw_data(stock_code, start_date, end_date)

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        return self._daily_history_source().normalize_data(df, stock_code)

    def _realtime_source(self):
        """复用原实例及模块的实时资源、旧替换入口和降级路径。"""
        from data_provider.realtime.finnhub_source import FinnhubRealtimeOperations

        return FinnhubRealtimeOperations(
            use_is_us_stock=self._is_us_stock,
            use_random_sleep=self.random_sleep,
            current_api_key=lambda: self._api_key,
            read_requests=lambda: requests,
            read_finnhub_base_url=lambda: _FINNHUB_BASE_URL,
        )

    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        return self._realtime_source().get_realtime_quote(stock_code)

    def _stock_names(self):
        """按需加载名称/清单实现，复用原状态及旧替换入口。"""
        from data_provider.stock_info.name_lookup import FinnhubNameLookup

        return FinnhubNameLookup(
            use_is_us_stock=lambda *args, **kwargs: self._is_us_stock(*args, **kwargs),
            read_api_key=lambda: self._api_key,
            current_requests=lambda: requests,
            current_finnhub_base_url=lambda: _FINNHUB_BASE_URL,
            log=lambda: logger,
        )

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        return self._stock_names().get_stock_name(stock_code)
