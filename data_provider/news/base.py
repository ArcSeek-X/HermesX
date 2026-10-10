# -*- coding: utf-8 -*-
"""
@file: base.py
@description: 资讯能力抽象，统一快讯 / 财经日历结果契约。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from data_provider.common.base import DataSource, DataSourceManager


@dataclass
class NewsRequest:
    """资讯请求。"""

    mode: str = "live"
    channel_id: str = "global-channel"
    limit: int = 30
    cursor: Optional[str] = None
    start_ts: Optional[int] = None
    end_ts: Optional[int] = None


@dataclass
class NewsResult:
    """资讯结果。"""

    items: List[Any]
    source: str = ""
    next_cursor: Optional[str] = None
    polling_cursor: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class NewsDataSource(DataSource[NewsRequest, NewsResult]):
    """资讯能力 source 公共抽象。"""


class NewsDataSourceManager(DataSourceManager[NewsRequest, NewsResult]):
    """资讯能力 Manager。"""

    def get_news(self, request: NewsRequest) -> NewsResult:
        """获取首个有效的资讯结果。"""
        return self.fetch_first(request)

    def build_cache_key(self, request: NewsRequest) -> Optional[str]:
        """按模式与查询条件构造缓存键。"""
        return (
            "news:"
            f"{request.mode}:{request.channel_id}:{request.limit}:"
            f"{request.cursor or ''}:{request.start_ts or ''}:{request.end_ts or ''}"
        )

    def is_valid_result(self, result: Optional[NewsResult]) -> bool:
        """资讯结果至少要有条目。"""
        return result is not None and bool(result.items)
