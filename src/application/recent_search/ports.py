# -*- coding: utf-8 -*-
"""个股最近搜索用例依赖的仓储端口。

应用层只依赖此协议，不感知 SQLAlchemy 或具体仓储实现。
"""

from __future__ import annotations

from typing import Any, Dict, List, Protocol


class RecentSearchRepositoryPort(Protocol):
    """最近搜索记录持久化能力。"""

    def record_upsert(
        self,
        *,
        user_id: str,
        stock_code: str,
        stock_name: str | None,
        market: str | None,
        max_records: int,
    ) -> Dict[str, Any]:
        """记录一次搜索并返回被写入的条目。"""
        ...

    def list_recent(self, *, user_id: str, limit: int) -> List[Dict[str, Any]]:
        """按最近搜索时间倒序列出记录。"""
        ...

    def clear_all(self, *, user_id: str) -> None:
        """清空该用户全部记录。"""
        ...
