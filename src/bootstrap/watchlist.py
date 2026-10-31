# -*- coding: utf-8 -*-
"""自选股用例的装配。

用例需要「持久化」与「股票主数据核验」两个能力，具体实现在此绑定；``api`` 只通过
依赖注入拿到装配好的 :class:`~src.application.watchlist.service.WatchlistService`，
不接触仓储实现或 ORM 模型。
"""

from __future__ import annotations

from src.application.watchlist import WatchlistService
from src.infrastructure.indexing.stock_code_validator import StockIndexCodeValidator
from src.infrastructure.persistence.repositories.watchlist_repo import (
    SqlAlchemyWatchlistRepository,
)
from src.storage import DatabaseManager


def build_watchlist_service() -> WatchlistService:
    """按当前进程的数据库单例装配自选股用例。

    每次调用返回无状态用例对象而不缓存：``DatabaseManager.reset_instance()`` 之后
    新建的用例会绑定到新的管理器，不会残留已释放的引擎引用。
    """
    return WatchlistService(
        repository=SqlAlchemyWatchlistRepository(DatabaseManager.get_instance()),
        stock_code_validator=StockIndexCodeValidator(),
    )
