# -*- coding: utf-8 -*-
"""个股最近搜索仓储：``stock_recent_search`` 的读写实现。

约定：

- 写入统一走 ``self._db._run_write_transaction``：在任何读取之前先取
  ``BEGIN IMMEDIATE``，因此「查重 + upsert + 裁剪」处于同一个一致窗口内，
  并发重复搜索由 ``(user_id, stock_code)`` 唯一约束兜底。
- 列表与裁剪都按 ``update_date_time DESC, id DESC`` 排序，同秒写入时以主键
  决定先后，避免顺序抖动。
- 仓储只返回 ``to_dict()`` 字典，不把 ORM 对象交回用例层。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.infrastructure.persistence.base import utc_naive_now
from src.infrastructure.persistence.models.recent_search import StockRecentSearch

if TYPE_CHECKING:
    from src.storage import DatabaseManager


class SqlAlchemyRecentSearchRepository:
    """基于 SQLAlchemy 的个股最近搜索仓储实现。"""

    def __init__(self, db_manager: "DatabaseManager") -> None:
        """构造最近搜索仓储并保存数据库管理器。"""
        self._db = db_manager

    @staticmethod
    def _newest_first(user_id: str):
        """构造按最近搜索时间倒序的查询（含主键兜底排序）。"""
        return (
            select(StockRecentSearch)
            .where(StockRecentSearch.user_id == user_id)
            .order_by(StockRecentSearch.update_date_time.desc(), StockRecentSearch.id.desc())
        )

    def record_upsert(
        self,
        *,
        user_id: str,
        stock_code: str,
        stock_name: str | None,
        market: str | None,
        max_records: int,
    ) -> Dict[str, Any]:
        """记录一次搜索：同代码刷新并顶置，写入后把队列裁剪到 ``max_records`` 条。"""
        def _write(session: Session) -> Dict[str, Any]:
            """在同一个写事务内完成查重、upsert 与裁剪。"""
            now = utc_naive_now()
            record = session.execute(
                select(StockRecentSearch).where(
                    StockRecentSearch.user_id == user_id,
                    StockRecentSearch.stock_code == stock_code,
                )
            ).scalars().first()

            if record is None:
                record = StockRecentSearch(
                    user_id=user_id,
                    stock_code=stock_code,
                    stock_name=stock_name,
                    market=market,
                    create_date_time=now,
                    update_date_time=now,
                )
                session.add(record)
            else:
                record.stock_name = stock_name
                record.market = market
                record.update_date_time = now

            session.flush()
            result = record.to_dict()

            stale_ids = session.execute(
                self._newest_first(user_id).with_only_columns(StockRecentSearch.id).offset(max_records)
            ).scalars().all()
            if stale_ids:
                session.execute(delete(StockRecentSearch).where(StockRecentSearch.id.in_(stale_ids)))

            return result

        return self._db._run_write_transaction("recent_search.record_upsert", _write)

    def list_recent(self, *, user_id: str, limit: int) -> List[Dict[str, Any]]:
        """列出该用户最近搜索记录（倒序，最多 ``limit`` 条）。"""
        with self._db.get_session() as session:
            rows = session.execute(self._newest_first(user_id).limit(limit)).scalars().all()
            return [row.to_dict() for row in rows]

    def clear_all(self, *, user_id: str) -> None:
        """清空该用户的全部最近搜索记录。"""
        def _write(session: Session) -> None:
            """在同一个写事务内删除该用户所有记录。"""
            session.execute(delete(StockRecentSearch).where(StockRecentSearch.user_id == user_id))

        self._db._run_write_transaction("recent_search.clear_all", _write)
