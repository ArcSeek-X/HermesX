# -*- coding: utf-8 -*-
"""自选股仓储：``stock_watchlist_group`` / ``stock_watchlist_item`` 的读写实现。

本实现向 :class:`~src.application.watchlist.ports.WatchlistRepositoryPort` 提供能力；
连接、会话与锁重试仍由 :class:`~src.storage.DatabaseManager`（底层
:class:`~src.infrastructure.persistence.session.DatabaseSession`）负责。

约定：

- 写入统一走 ``self._db._run_write_transaction``：它在任何读取之前先取
  ``BEGIN IMMEDIATE``，因此「存在性检查 + 写入」处于同一个一致窗口内，仓储不
  自行提交，方法返回即已提交。
- 重名、同分类重复股票这类由唯一性约束推导出的冲突，由本层抛
  :class:`~src.application.watchlist.errors.WatchlistConflictError`；消息与
  ``error_code`` 属于业务语义，不含 HTTP 状态码。
- 过滤条件保持原端点语义：列表查询只取 ``delete_flag == 0``，而 ``session.get``
  按主键定位时不过滤逻辑删除（既有行为，重复删除/编辑保持幂等）。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.application.watchlist.errors import (
    WatchlistConflictError,
    WatchlistNotFoundError,
)
from src.infrastructure.persistence.models.watchlist import WatchlistGroup, WatchlistItem

if TYPE_CHECKING:
    from src.storage import DatabaseManager

# 分组编码企业 ID（企业体系未实现前默认 01）
ENTERPRISE_ID = "01"


def _now() -> datetime:
    return datetime.now()


def _next_group_code(session: Session, enterprise_id: str = ENTERPRISE_ID) -> str:
    """生成分组编码：WG-{enterpriseId}-{yyyyMMdd}-{6位流水号}。

    流水号为当日该企业内已存在同类编码的数量 + 1，格式化为 6 位（000001 起）。
    编码生成依赖存量数据，因此留在仓储侧，用例层不感知编码规则。
    """
    date_str = _now().strftime("%Y%m%d")
    prefix = f"WG-{enterprise_id}-{date_str}-"
    count = session.execute(
        select(func.count(WatchlistGroup.id)).where(WatchlistGroup.group_code.like(f"{prefix}%"))
    ).scalar() or 0
    return f"{prefix}{count + 1:06d}"


class SqlAlchemyWatchlistRepository:
    """基于 SQLAlchemy 的自选股仓储实现。"""

    def __init__(self, db_manager: "DatabaseManager") -> None:
        self._db = db_manager

    # === 分类 ===

    def list_groups(self) -> List[Dict[str, Any]]:
        with self._db.get_session() as session:
            rows = session.execute(
                select(WatchlistGroup)
                .where(WatchlistGroup.delete_flag == 0)
                .order_by(WatchlistGroup.sort_order.asc(), WatchlistGroup.id.asc())
            ).scalars().all()
            counts = dict(
                session.execute(
                    select(WatchlistItem.group_id, func.count(WatchlistItem.id))
                    .where(WatchlistItem.delete_flag == 0)
                    .group_by(WatchlistItem.group_id)
                ).all()
            )
            result: List[Dict[str, Any]] = []
            for group in rows:
                data = group.to_dict()
                data["item_count"] = int(counts.get(group.id, 0))
                result.append(data)
            return result

    def create_group(
        self,
        *,
        name: str,
        sort_order: Optional[int],
        description: Optional[str],
    ) -> Dict[str, Any]:
        def _write(session: Session) -> Dict[str, Any]:
            existing = session.execute(
                select(WatchlistGroup.id).where(WatchlistGroup.name == name)
            ).first()
            if existing is not None:
                raise WatchlistConflictError(
                    f"分类「{name}」已存在",
                    error_code="duplicate_name",
                )

            if sort_order is None:
                max_order = session.execute(
                    select(func.max(WatchlistGroup.sort_order))
                ).scalar()
                next_order = (max_order + 1) if max_order is not None else 0
            else:
                next_order = sort_order

            now = _now()
            group = WatchlistGroup(
                name=name,
                sort_order=next_order,
                group_code=_next_group_code(session),
                description=description or '',
                delete_flag=0,
                create_date_time=now,
                update_date_time=now,
            )
            session.add(group)
            session.flush()
            result = group.to_dict()
            result["item_count"] = 0
            return result

        return self._db._run_write_transaction("watchlist.create_group", _write)

    def update_group(
        self,
        *,
        group_code: str,
        name: Optional[str],
        description: Optional[str],
        sort_order: Optional[int],
    ) -> Dict[str, Any]:
        def _write(session: Session) -> Dict[str, Any]:
            group = session.execute(
                select(WatchlistGroup).where(
                    WatchlistGroup.group_code == group_code,
                    WatchlistGroup.delete_flag == 0,
                )
            ).scalars().first()
            if group is None:
                raise WatchlistNotFoundError("分类不存在", error_code="not_found")

            if name is not None and name != group.name:
                duplicate = session.execute(
                    select(WatchlistGroup.id).where(
                        WatchlistGroup.name == name,
                        WatchlistGroup.group_code != group_code,
                    )
                ).first()
                if duplicate is not None:
                    raise WatchlistConflictError(
                        f"分类「{name}」已存在",
                        error_code="duplicate_name",
                    )
                group.name = name

            if description is not None:
                group.description = description
            if sort_order is not None:
                group.sort_order = sort_order

            group.update_date_time = _now()
            return group.to_dict()

        return self._db._run_write_transaction("watchlist.update_group", _write)

    def delete_group(self, group_code: str) -> None:
        def _write(session: Session) -> None:
            group = session.execute(
                select(WatchlistGroup).where(
                    WatchlistGroup.group_code == group_code,
                    WatchlistGroup.delete_flag == 0,
                )
            ).scalars().first()
            if group is None:
                raise WatchlistNotFoundError("分类不存在", error_code="not_found")

            # 逻辑删除：分类及其下自选股置 delete_flag=1，同事务完成
            now = _now()
            session.execute(
                WatchlistItem.__table__.update()
                .where(WatchlistItem.group_id == group.id)
                .values(delete_flag=1, update_date_time=now)
            )
            group.delete_flag = 1
            group.update_date_time = now

        self._db._run_write_transaction("watchlist.delete_group", _write)

    # === 自选股 ===

    def list_items(
        self,
        group_id: int,
        *,
        offset: int,
        limit: int,
    ) -> Tuple[List[Dict[str, Any]], int]:
        with self._db.get_session() as session:
            group = session.get(WatchlistGroup, group_id)
            if group is None:
                raise WatchlistNotFoundError("分类不存在", error_code="not_found")

            total = session.execute(
                select(func.count(WatchlistItem.id)).where(
                    WatchlistItem.group_id == group_id,
                    WatchlistItem.delete_flag == 0,
                )
            ).scalar() or 0

            rows = session.execute(
                select(WatchlistItem)
                .where(
                    WatchlistItem.group_id == group_id,
                    WatchlistItem.delete_flag == 0,
                )
                .order_by(WatchlistItem.sort_order.asc(), WatchlistItem.id.asc())
                .offset(offset)
                .limit(limit)
            ).scalars().all()

            return [row.to_dict() for row in rows], int(total)

    def create_item(
        self,
        *,
        group_id: int,
        stock_code: str,
        stock_name: Optional[str],
        description: Optional[str],
    ) -> Dict[str, Any]:
        def _write(session: Session) -> Dict[str, Any]:
            group = session.get(WatchlistGroup, group_id)
            if group is None:
                raise WatchlistNotFoundError("分类不存在", error_code="not_found")

            duplicate = session.execute(
                select(WatchlistItem.id).where(
                    WatchlistItem.group_id == group_id,
                    WatchlistItem.stock_code == stock_code,
                )
            ).first()
            if duplicate is not None:
                raise WatchlistConflictError(
                    f"分类下已存在股票 {stock_code}",
                    error_code="duplicate_item",
                )

            now = _now()
            item = WatchlistItem(
                group_id=group_id,
                stock_code=stock_code,
                stock_name=stock_name,
                description=description,
                sort_order=0,
                delete_flag=0,
                create_date_time=now,
                update_date_time=now,
            )
            session.add(item)
            session.flush()
            return item.to_dict()

        return self._db._run_write_transaction("watchlist.create_item", _write)

    def update_item(
        self,
        *,
        item_id: int,
        stock_name: Optional[str],
        description: Optional[str],
    ) -> Dict[str, Any]:
        def _write(session: Session) -> Dict[str, Any]:
            item = session.get(WatchlistItem, item_id)
            if item is None:
                raise WatchlistNotFoundError("自选股不存在", error_code="not_found")

            if description is not None:
                item.description = description
            if stock_name is not None:
                item.stock_name = stock_name

            item.update_date_time = _now()
            return item.to_dict()

        return self._db._run_write_transaction("watchlist.update_item", _write)

    def delete_item(self, item_id: int) -> None:
        def _write(session: Session) -> None:
            item = session.get(WatchlistItem, item_id)
            if item is None:
                raise WatchlistNotFoundError("自选股不存在", error_code="not_found")
            item.delete_flag = 1
            item.update_date_time = _now()

        self._db._run_write_transaction("watchlist.delete_item", _write)

    def move_item(
        self,
        *,
        item_id: int,
        target_group_id: int,
    ) -> Dict[str, Any]:
        def _write(session: Session) -> Dict[str, Any]:
            item = session.get(WatchlistItem, item_id)
            if item is None:
                raise WatchlistNotFoundError("自选股不存在", error_code="not_found")

            target = session.get(WatchlistGroup, target_group_id)
            if target is None:
                raise WatchlistNotFoundError("目标分类不存在", error_code="not_found")

            if item.group_id != target_group_id:
                duplicate = session.execute(
                    select(WatchlistItem.id).where(
                        WatchlistItem.group_id == target_group_id,
                        WatchlistItem.stock_code == item.stock_code,
                    )
                ).first()
                if duplicate is not None:
                    raise WatchlistConflictError(
                        "目标分类下已存在该股票",
                        error_code="duplicate_item",
                    )
                item.group_id = target_group_id
                item.update_date_time = _now()

            return item.to_dict()

        return self._db._run_write_transaction("watchlist.move_item", _write)
