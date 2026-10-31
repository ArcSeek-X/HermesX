# -*- coding: utf-8 -*-
"""回测服务的装配。

回测用例 ``BacktestService``（位于 ``src/application/backtest``）只依赖端口，不自行装配
具体适配器；本装配口把仓储 ``BacktestRepository`` / ``StockRepository`` 与日线补数适配器
一并注入；``api`` 只通过依赖注入拿到实例，不再直接依赖 ``src.storage``。
"""

from __future__ import annotations

from src.application.backtest.service import BacktestService
from src.infrastructure.persistence.repositories.backtest_repository import BacktestRepository
from src.infrastructure.persistence.repositories.stock_repository import StockRepository
from src.storage import DatabaseManager


def build_backtest_service() -> BacktestService:
    """按当前进程的数据库单例装配回测服务。

    每次调用返回新实例而不缓存：``DatabaseManager.reset_instance()`` 之后新建的
    服务会绑定到新的管理器，不会残留已释放的引擎引用。

    回测/日线仓储与日线补数端口在此显式装配注入，使 application 层与 ``src.repositories`` /
    ``src.storage`` / ``data_provider`` / ``src.infrastructure`` 解耦；``BacktestService``
    不再自带缺省装配，所有生产构造点均应经由本装配口获取实例。
    """
    db = DatabaseManager.get_instance()
    from src.infrastructure.providers.backtest_daily_refill import (
        DataProviderDailyBarRefill,
    )

    return BacktestService(
        backtest_repository=BacktestRepository(db),
        stock_repository=StockRepository(db),
        daily_refill=DataProviderDailyBarRefill(db),
    )
