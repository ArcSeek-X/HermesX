# -*- coding: utf-8 -*-
"""DataFetcherManager 适配器：实现 DailyBarFetcherPort。"""

from __future__ import annotations

from typing import Any


class DataProviderAlertDailyBarFetcher:
    """通过 DataFetcherManager 多源 fallback 获取日线数据。"""

    def get_daily_data(self, stock_code: str, days: int) -> Any:
        from data_provider import DataFetcherManager

        return DataFetcherManager().get_daily_data(stock_code, days=days)
