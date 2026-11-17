# -*- coding: utf-8 -*-
"""个股最近搜索用例的装配。

``api`` 只通过依赖注入拿到装配好的
:class:`~src.application.recent_search.service.RecentSearchService`，不接触仓储
实现或 ORM 模型。
"""

from __future__ import annotations

from src.application.recent_search import RecentSearchService
from src.infrastructure.persistence.repositories.recent_search_repo import (
    SqlAlchemyRecentSearchRepository,
)
from src.storage import DatabaseManager


def build_recent_search_service() -> RecentSearchService:
    """按当前进程的数据库单例装配最近搜索用例。

    每次调用返回无状态用例对象而不缓存：``DatabaseManager.reset_instance()`` 之后
    新建的用例会绑定到新的管理器，不会残留已释放的引擎引用。
    """
    return RecentSearchService(
        repository=SqlAlchemyRecentSearchRepository(DatabaseManager.get_instance()),
    )
