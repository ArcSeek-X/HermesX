# -*- coding: utf-8 -*-
"""个股最近搜索用例。

对外只暴露 :class:`RecentSearchService`、参数归一工具与业务错误类型；仓储端口
在 ``ports``，具体实现在
``src.infrastructure.persistence.repositories.recent_search_repo``。
"""

from src.application.recent_search.errors import RecentSearchValidationError
from src.application.recent_search.ports import RecentSearchRepositoryPort
from src.application.recent_search.service import (
    DEFAULT_USER_ID,
    MAX_RECENT_SEARCH_RECORDS,
    RecentSearchService,
    infer_recent_search_market,
    normalize_recent_search_code,
    normalize_recent_search_user_id,
)

__all__ = [
    "DEFAULT_USER_ID",
    "MAX_RECENT_SEARCH_RECORDS",
    "RecentSearchRepositoryPort",
    "RecentSearchService",
    "RecentSearchValidationError",
    "infer_recent_search_market",
    "normalize_recent_search_code",
    "normalize_recent_search_user_id",
]
