# -*- coding: utf-8 -*-
"""
===================================
自选股管理 API
===================================

路由前缀：/api/v1/watchlist

提供自选股分类（group）与自选股（item）的增删改查，以及移动归类能力。
排序与搜索由前端完成，本模块仅负责结构化数据的 CRUD。
"""

import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from src.storage import (
    DatabaseManager,
    WatchlistGroup,
    WatchlistItem,
)

# 数据库访问入口（与 api/deps.py、history.py 等保持一致）
db = DatabaseManager.get_instance()
from api.v1.schemas.watchlist import (
    WatchlistGroupCreate,
    WatchlistGroupUpdate,
    WatchlistGroupOut,
    WatchlistItemCreate,
    WatchlistItemUpdate,
    WatchlistItemMove,
    WatchlistItemOut,
    SimpleSuccess,
)

logger = logging.getLogger(__name__)

# 路由前缀统一在 api/v1/router.py 的 include_router(prefix="/watchlist") 处添加，
# 此处不再重复加前缀，避免形成 /api/v1/watchlist/watchlist/... 的双重前缀。
router = APIRouter(tags=["watchlist"])


def _now() -> datetime:
    return datetime.now()


# === 分类 CRUD ===

@router.get(
    "/groups",
    response_model=List[WatchlistGroupOut],
    summary="列出所有自选股分类",
    description="按 sort_order 升序返回所有分类",
)
def list_groups() -> List[dict]:
    with db.get_session() as session:
        rows = session.execute(
            select(WatchlistGroup).order_by(WatchlistGroup.sort_order.asc(), WatchlistGroup.id.asc())
        ).scalars().all()
        return [r.to_dict() for r in rows]


@router.post(
    "/groups",
    response_model=WatchlistGroupOut,
    summary="新增自选股分类",
    responses={409: {"description": "分类名称已存在"}},
)
def create_group(payload: WatchlistGroupCreate) -> dict:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail={"error": "invalid_name", "message": "分类名称不能为空"})

    with db.get_session() as session:
        existing = session.execute(
            select(WatchlistGroup).where(WatchlistGroup.name == name)
        ).scalars().first()
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail={"error": "duplicate_name", "message": f"分类「{name}」已存在"},
            )

        max_order = session.execute(
            select(WatchlistGroup.sort_order)
        ).scalars().all()
        next_order = (max(max_order) + 1) if max_order else 0

        group = WatchlistGroup(name=name, sort_order=next_order, created_at=_now(), updated_at=_now())
        session.add(group)
        session.flush()
        result = group.to_dict()
        session.commit()
        return result


@router.put(
    "/groups/{group_id}",
    response_model=WatchlistGroupOut,
    summary="编辑自选股分类",
    responses={404: {"description": "分类不存在"}, 409: {"description": "分类名称已存在"}},
)
def update_group(group_id: int, payload: WatchlistGroupUpdate) -> dict:
    with db.get_session() as session:
        group = session.get(WatchlistGroup, group_id)
        if group is None:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "分类不存在"})

        if payload.name is not None:
            new_name = payload.name.strip()
            if not new_name:
                raise HTTPException(status_code=422, detail={"error": "invalid_name", "message": "分类名称不能为空"})
            if new_name != group.name:
                dup = session.execute(
                    select(WatchlistGroup).where(WatchlistGroup.name == new_name)
                ).scalars().first()
                if dup is not None:
                    raise HTTPException(
                        status_code=409,
                        detail={"error": "duplicate_name", "message": f"分类「{new_name}」已存在"},
                    )
                group.name = new_name

        if payload.sort_order is not None:
            group.sort_order = payload.sort_order

        group.updated_at = _now()
        result = group.to_dict()
        session.commit()
        return result


@router.delete(
    "/groups/{group_id}",
    response_model=SimpleSuccess,
    summary="删除自选股分类",
    responses={404: {"description": "分类不存在"}},
)
def delete_group(group_id: int) -> dict:
    with db.get_session() as session:
        group = session.get(WatchlistGroup, group_id)
        if group is None:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "分类不存在"})
        session.delete(group)  # 级联删除其下股票（依赖外键 ON DELETE CASCADE）
        session.commit()
        return {"success": True}


# === 自选股 CRUD ===

@router.get(
    "/groups/{group_id}/items",
    response_model=List[WatchlistItemOut],
    summary="获取某分类下的自选股",
    responses={404: {"description": "分类不存在"}},
)
def list_items(group_id: int) -> List[dict]:
    with db.get_session() as session:
        group = session.get(WatchlistGroup, group_id)
        if group is None:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "分类不存在"})

        rows = session.execute(
            select(WatchlistItem)
            .where(WatchlistItem.group_id == group_id)
            .order_by(WatchlistItem.sort_order.asc(), WatchlistItem.id.asc())
        ).scalars().all()
        return [r.to_dict() for r in rows]


@router.post(
    "/groups/{group_id}/items",
    response_model=WatchlistItemOut,
    summary="新增自选股到分类",
    responses={
        404: {"description": "分类不存在"},
        409: {"description": "该分类下股票已存在"},
    },
)
def create_item(group_id: int, payload: WatchlistItemCreate) -> dict:
    stock_code = payload.stock_code.strip()
    if not stock_code:
        raise HTTPException(status_code=422, detail={"error": "invalid_code", "message": "股票代码不能为空"})

    with db.get_session() as session:
        group = session.get(WatchlistGroup, group_id)
        if group is None:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "分类不存在"})

        dup = session.execute(
            select(WatchlistItem).where(
                WatchlistItem.group_id == group_id,
                WatchlistItem.stock_code == stock_code,
            )
        ).scalars().first()
        if dup is not None:
            raise HTTPException(
                status_code=409,
                detail={"error": "duplicate_item", "message": f"分类下已存在股票 {stock_code}"},
            )

        item = WatchlistItem(
            group_id=group_id,
            stock_code=stock_code,
            stock_name=payload.stock_name,
            note=payload.note,
            sort_order=0,
            created_at=_now(),
            updated_at=_now(),
        )
        session.add(item)
        session.flush()
        result = item.to_dict()
        session.commit()
        return result


@router.put(
    "/items/{item_id}",
    response_model=WatchlistItemOut,
    summary="编辑自选股（备注/名称）",
    responses={404: {"description": "自选股不存在"}},
)
def update_item(item_id: int, payload: WatchlistItemUpdate) -> dict:
    with db.get_session() as session:
        item = session.get(WatchlistItem, item_id)
        if item is None:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "自选股不存在"})

        if payload.note is not None:
            item.note = payload.note
        if payload.stock_name is not None:
            item.stock_name = payload.stock_name

        item.updated_at = _now()
        result = item.to_dict()
        session.commit()
        return result


@router.delete(
    "/items/{item_id}",
    response_model=SimpleSuccess,
    summary="删除自选股",
    responses={404: {"description": "自选股不存在"}},
)
def delete_item(item_id: int) -> dict:
    with db.get_session() as session:
        item = session.get(WatchlistItem, item_id)
        if item is None:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "自选股不存在"})
        session.delete(item)
        session.commit()
        return {"success": True}


@router.put(
    "/items/{item_id}/move",
    response_model=WatchlistItemOut,
    summary="移动自选股到其他分类",
    responses={
        404: {"description": "自选股或目标分类不存在"},
        409: {"description": "目标分类下已存在该股票"},
    },
)
def move_item(item_id: int, payload: WatchlistItemMove) -> dict:
    with db.get_session() as session:
        item = session.get(WatchlistItem, item_id)
        if item is None:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "自选股不存在"})

        target = session.get(WatchlistGroup, payload.target_group_id)
        if target is None:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "目标分类不存在"})

        if item.group_id != payload.target_group_id:
            dup = session.execute(
                select(WatchlistItem).where(
                    WatchlistItem.group_id == payload.target_group_id,
                    WatchlistItem.stock_code == item.stock_code,
                )
            ).scalars().first()
            if dup is not None:
                raise HTTPException(
                    status_code=409,
                    detail={"error": "duplicate_item", "message": "目标分类下已存在该股票"},
                )
            item.group_id = payload.target_group_id
            item.updated_at = _now()

        result = item.to_dict()
        session.commit()
        return result
