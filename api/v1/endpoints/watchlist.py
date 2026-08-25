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
from sqlalchemy import select, func

from src.storage import (
    DatabaseManager,
    WatchlistGroup,
    WatchlistItem,
)
from src.data.stock_index_loader import get_stock_name_index_map
from src.utils.pagination import PaginationParams, compute_pages, paginate_response

# 数据库访问入口（与 api/deps.py、history.py 等保持一致）
db = DatabaseManager.get_instance()
from api.v1.schemas.watchlist import (
    WatchlistGroupCreate,
    WatchlistGroupUpdate,
    WatchlistGroupList,
    WatchlistItemCreate,
    WatchlistItemUpdate,
    WatchlistItemMove,
    WatchlistItemOut,
    WatchlistItemsQueryRequest,
    WatchlistItemsPaginatedResponse,
    SimpleSuccess,
)

logger = logging.getLogger(__name__)

# 路由前缀统一在 api/v1/router.py 的 include_router(prefix="/watchlist") 处添加，
# 此处不再重复加前缀，避免形成 /api/v1/watchlist/watchlist/... 的双重前缀。
router = APIRouter(tags=["watchlist"])


def _now() -> datetime:
    return datetime.now()


# 分组编码企业 ID（企业体系未实现前默认 01）
ENTERPRISE_ID = "01"


def _gen_group_code(session, enterprise_id: str = ENTERPRISE_ID) -> str:
    """生成分组编码：WG-{enterpriseId}-{yyyyMMdd}-{6位流水号}。

    流水号为当日该企业内已存在同类编码的数量 + 1，格式化为 6 位（000001 起）。
    """
    date_str = _now().strftime("%Y%m%d")
    prefix = f"WG-{enterprise_id}-{date_str}-"
    count = session.execute(
        select(func.count(WatchlistGroup.id)).where(WatchlistGroup.group_code.like(f"{prefix}%"))
    ).scalar() or 0
    return f"{prefix}{count + 1:06d}"


# === 分类 CRUD ===

@router.get(
    "/get_group_list",
    response_model=List[WatchlistGroupList],
    summary="列出所有自选股分类",
    description="按 sort_order 升序返回所有未删除分类，并实时统计每个分类下的个股数量",
)
def get_watchlist_groups() -> List[dict]:
    with db.get_session() as session:
        rows = session.execute(
            select(WatchlistGroup)
            .where(WatchlistGroup.delete_flag == 0)
            .order_by(WatchlistGroup.sort_order.asc(), WatchlistGroup.id.asc())
        ).scalars().all()
        result = []
        for group in rows:
            d = group.to_dict()
            count = session.execute(
                select(func.count(WatchlistItem.id)).where(
                    WatchlistItem.group_id == group.id,
                    WatchlistItem.delete_flag == 0,
                )
            ).scalar() or 0
            d["item_count"] = count
            result.append(d)
        return result


@router.post(
    "/create_group",
    response_model=WatchlistGroupList,
    summary="新增自选股分类",
    responses={409: {"description": "分类名称已存在"}},
)
def create_watchlist_group(payload: WatchlistGroupCreate) -> dict:
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

        group = WatchlistGroup(
            name=name,
            sort_order=payload.sort_order if payload.sort_order is not None else next_order,
            group_code=_gen_group_code(session),
            description=payload.description or '',
            delete_flag=0,
            create_date_time=_now(),
            update_date_time=_now(),
        )
        session.add(group)
        session.flush()
        result = group.to_dict()
        result["item_count"] = 0
        session.commit()
        return result


@router.post(
    "/update_group",
    response_model=WatchlistGroupList,
    summary="编辑自选股分类（按 group_code 定位）",
    responses={404: {"description": "分类不存在"}, 409: {"description": "分类名称已存在"}},
)
def update_watchlist_group(payload: WatchlistGroupUpdate) -> dict:
    with db.get_session() as session:
        group = session.execute(
            select(WatchlistGroup).where(
                WatchlistGroup.group_code == payload.group_code,
                WatchlistGroup.delete_flag == 0,
            )
        ).scalars().first()
        if group is None:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "分类不存在"})

        if payload.name is not None:
            new_name = payload.name.strip()
            if not new_name:
                raise HTTPException(status_code=422, detail={"error": "invalid_name", "message": "分类名称不能为空"})
            if new_name != group.name:
                dup = session.execute(
                    select(WatchlistGroup).where(
                        WatchlistGroup.name == new_name,
                        WatchlistGroup.group_code != payload.group_code,
                    )
                ).scalars().first()
                if dup is not None:
                    raise HTTPException(
                        status_code=409,
                        detail={"error": "duplicate_name", "message": f"分类「{new_name}」已存在"},
                    )
                group.name = new_name

        if payload.description is not None:
            group.description = payload.description
        if payload.sort_order is not None:
            group.sort_order = payload.sort_order

        group.update_date_time = _now()
        result = group.to_dict()
        session.commit()
        return result


@router.delete(
    "/delete_group/{group_code}",
    response_model=SimpleSuccess,
    summary="删除自选股分类（逻辑删除）",
    responses={404: {"description": "分类不存在"}},
)
def delete_watchlist_group(group_code: str) -> dict:
    with db.get_session() as session:
        group = session.execute(
            select(WatchlistGroup).where(
                WatchlistGroup.group_code == group_code,
                WatchlistGroup.delete_flag == 0,
            )
        ).scalars().first()
        if group is None:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "分类不存在"})
        # 逻辑删除：分类及其下自选股置 delete_flag=1
        session.execute(
            WatchlistItem.__table__.update()
            .where(WatchlistItem.group_id == group.id)
            .values(delete_flag=1, update_date_time=_now())
        )
        group.delete_flag = 1
        group.update_date_time = _now()
        session.commit()
        return {"success": True}


# === 自选股 CRUD ===

@router.post(
    "/get_items_list",
    response_model=WatchlistItemsPaginatedResponse,
    summary="分页查询自选股",
    responses={404: {"description": "分类不存在"}},
)
def get_watchlist_items(payload: WatchlistItemsQueryRequest) -> dict:
    """分页查询某分类下的自选股。

    入参（body）：group_id, pageSize, pageNum
    出参：list, total, pageSize, pages, pageNum
    """
    paging = PaginationParams(page_num=payload.pageNum, page_size=payload.pageSize)

    with db.get_session() as session:
        group = session.get(WatchlistGroup, payload.group_id)
        if group is None:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "分类不存在"})

        # 查询总数（仅未逻辑删除）
        total = session.execute(
            select(func.count(WatchlistItem.id))
            .where(WatchlistItem.group_id == payload.group_id, WatchlistItem.delete_flag == 0)
        ).scalar() or 0

        # 分页查询（仅未逻辑删除）
        rows = session.execute(
            select(WatchlistItem)
            .where(WatchlistItem.group_id == payload.group_id, WatchlistItem.delete_flag == 0)
            .order_by(WatchlistItem.sort_order.asc(), WatchlistItem.id.asc())
            .offset(paging.offset)
            .limit(paging.limit)
        ).scalars().all()

        items = [r.to_dict() for r in rows]
        return paginate_response(items, total, payload.pageNum, payload.pageSize)


def _is_valid_stock_code(code: str) -> bool:
    """核验股票编号是否在股票主数据（stocks.index.json）中存在。

    使用 ``get_stock_name_index_map`` 的键（canonicalCode，如 ``603019.SH``、
    ``00700.HK``、``AAPL``）直接匹配，覆盖 A 股/港股/美股等全市场。
    若索引加载失败（异常），采取宽松放行，避免主数据缺失拖垮新增功能。
    """
    if not code:
        return False
    try:
        name_map = get_stock_name_index_map()
        return code in name_map
    except Exception as exc:  # pragma: no cover - 索引加载异常时降级
        logging.getLogger(__name__).warning("[自选股] 股票索引核验失败，降级放行：%s", exc)
        return True


@router.post(
    "/create_item/{id}",
    response_model=WatchlistItemOut,
    summary="新增自选股到分类",
    responses={
        400: {"description": "股票代码无效或未收录"},
        404: {"description": "分类不存在"},
        409: {"description": "该分类下股票已存在"},
    },
)
def create_watchlist_item(id: int, payload: WatchlistItemCreate) -> dict:
    group_id = id
    stock_code = payload.stock_code.strip()
    if not stock_code:
        raise HTTPException(status_code=422, detail={"error": "invalid_code", "message": "股票代码不能为空"})

    # 编号合法性核验：确保股票编号真实存在，避免脏数据入库
    if not _is_valid_stock_code(stock_code):
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_code", "message": f"股票代码无效或未收录：{stock_code}"},
        )

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
            description=payload.description,
            sort_order=0,
            delete_flag=0,
            create_date_time=_now(),
            update_date_time=_now(),
        )
        session.add(item)
        session.flush()
        result = item.to_dict()
        session.commit()
        return result


@router.post(
    "/update_item/{id}",
    response_model=WatchlistItemOut,
    summary="编辑自选股（备注/名称）",
    responses={404: {"description": "自选股不存在"}},
)
def update_watchlist_item(id: int, payload: WatchlistItemUpdate) -> dict:
    with db.get_session() as session:
        item = session.get(WatchlistItem, id)
        if item is None:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "自选股不存在"})

        if payload.description is not None:
            item.description = payload.description
        if payload.stock_name is not None:
            item.stock_name = payload.stock_name

        item.update_date_time = _now()
        result = item.to_dict()
        session.commit()
        return result


@router.delete(
    "/delete_item/{id}",
    response_model=SimpleSuccess,
    summary="删除自选股（逻辑删除）",
    responses={404: {"description": "自选股不存在"}},
)
def delete_watchlist_item(id: int) -> dict:
    with db.get_session() as session:
        item = session.get(WatchlistItem, id)
        if item is None:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "自选股不存在"})
        item.delete_flag = 1
        item.update_date_time = _now()
        session.commit()
        return {"success": True}


@router.put(
    "/move_item/{id}",
    response_model=WatchlistItemOut,
    summary="移动自选股到其他分类",
    responses={
        404: {"description": "自选股或目标分类不存在"},
        409: {"description": "目标分类下已存在该股票"},
    },
)
def move_watchlist_item(id: int, payload: WatchlistItemMove) -> dict:
    with db.get_session() as session:
        item = session.get(WatchlistItem, id)
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
            item.update_date_time = _now()

        result = item.to_dict()
        session.commit()
        return result
