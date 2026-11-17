# -*- coding: utf-8 -*-
"""搜索领域包。

对外暴露检索用例与各搜索引擎适配器共享的返回记录（领域 DTO）；本包不含任何
框架 / ORM / 网络 / 存储依赖，供 application、infrastructure、仓储层共同依赖，
避免分层为共享契约互相 import。
"""

from __future__ import annotations

from src.domain.search.records import (
    SearchResponse,
    SearchResult,
)

__all__ = [
    "SearchResult",
    "SearchResponse",
]
