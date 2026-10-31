# -*- coding: utf-8 -*-
"""回测"日线补数"端口的数据源适配器。

把原先内联在 :class:`~src.application.backtest.service.BacktestService` 里的
``DataFetcherManager().get_daily_data(...)`` 取数 + ``DatabaseManager.save_daily_data(...)``
落库两步编排收敛到 ``src/infrastructure``，使应用层不再直接依赖 ``data_provider``。

- 选源、回退、熔断、字段标准化仍完全复用 ``DataFetcherManager``，这里不重写；
- 空数据直接返回（非异常），落库失败向上抛出，由用例层统一降级为告警日志，
  与原实现行为逐字一致；
- ``DataFetcherManager`` 采用**调用期惰性导入**，保持与原内联实现相同的导入时机，
  因此测试仍可 patch ``data_provider.base.DataFetcherManager``。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.storage import DatabaseManager


class DataProviderDailyBarRefill:
    """:class:`~src.application.backtest.ports.DailyBarRefillPort` 的数据源实现。"""

    def __init__(self, db_manager: "DatabaseManager"):
        self._db = db_manager

    def refill(
        self,
        *,
        code: str,
        start_date: str,
        end_date: str,
        days: int,
    ) -> None:
        from data_provider.base import DataFetcherManager

        df, source = DataFetcherManager().get_daily_data(
            stock_code=code,
            start_date=start_date,
            end_date=end_date,
            days=days,
        )
        if df is None or df.empty:
            return
        self._db.save_daily_data(df, code=code, data_source=source)
