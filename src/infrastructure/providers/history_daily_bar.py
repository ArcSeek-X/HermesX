# -*- coding: utf-8 -*-
"""DataFetcherManager 适配器：实现 HistoryDailyBarFetcherPort。

``history_loader`` 的 DB-first 取数在网络回退时需要一个日线获取器。具体
``data_provider`` 依赖收敛在本适配器，由 ``src.bootstrap.history`` 在进程启动时
注入，使 loader 侧（以及后续搬入 ``src/application/history/`` 后）不直接 import
数据源包。返回 ``(pd.DataFrame, source_name)`` 元组，与旧 ``DataFetcherManager``
契约逐字一致。
"""

from __future__ import annotations

from typing import Any


class DataProviderHistoryDailyBarFetcher:
    """通过 DataFetcherManager 多源 fallback 获取日线数据，返回 ``(df, source)``。"""

    def get_daily_data(self, stock_code: str, days: int) -> Any:
        from data_provider import DataFetcherManager

        return DataFetcherManager().get_daily_data(stock_code, days=days)
