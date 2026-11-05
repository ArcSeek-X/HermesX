# -*- coding: utf-8 -*-
"""
@file: watchlist.py
@description: 自选股管理端点：分组与条目的增删改查、分页查询与移动归类；由 api.v1.router 挂到 /api/v1/watchlist，业务规则在 src.application.watchlist.WatchlistService。
@author: Lensgcx (GaoCangxiong)

===================================
自选股管理 API
===================================

路由前缀：/api/v1/watchlist

提供自选股分类（group）与自选股（item）的增删改查，以及移动归类能力。
排序与搜索由前端完成，本模块仅负责结构化数据的 CRUD。

传输层只做三件事：解析请求、调用 :class:`~src.application.watchlist.service.WatchlistService`、
把业务错误映射成 HTTP 状态码。业务规则、唯一性判定与事务边界在应用层和仓储实现中，
本模块不直接访问 ORM 或数据库会话。
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_watchlist_service
from api.v1.errors import api_error
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
from src.application.watchlist import (
    UnknownStockCodeError,
    WatchlistConflictError,
    WatchlistError,
    WatchlistNotFoundError,
    WatchlistService,
    WatchlistValidationError,
)
from src.utils.pagination import paginate_response

# 模块级日志器，记录自选股操作异常。
logger = logging.getLogger(__name__)

# 路由前缀统一在 api/v1/router.py 的 include_router(prefix="/watchlist") 处添加，
# 此处不再重复加前缀，避免形成 /api/v1/watchlist/watchlist/... 的双重前缀。
# 本模块的 APIRouter；由 api.v1.router 挂到 /api/v1/watchlist。
router = APIRouter(tags=["watchlist"])


def _to_http_error(exc: WatchlistError) -> HTTPException:
    """把业务错误映射为 HTTP 状态码。

    统一走 api.v1.errors.api_error，保证错误体形状与全局异常处理器一致。

    Args:
        exc: 服务层抛出的业务异常，携带 error_code 与可读消息。

    Returns:
        HTTPException: 带统一 error/message 错误体的异常对象。
    """
    if isinstance(exc, UnknownStockCodeError):
        status_code = 400
    elif isinstance(exc, WatchlistValidationError):
        status_code = 422
    elif isinstance(exc, WatchlistConflictError):
        status_code = 409
    elif isinstance(exc, WatchlistNotFoundError):
        status_code = 404
    else:  # pragma: no cover - 新增错误类型时必须显式决定状态码
        status_code = 500
    return api_error(status_code, exc.error_code, str(exc))


# === 分类 CRUD ===

@router.get(
    "/get_group_list",
    response_model=List[WatchlistGroupList],
    summary="列出所有自选股分类",
    description="按 sort_order 升序返回所有未删除分类，并实时统计每个分类下的个股数量",
)
def get_watchlist_groups(
    service: WatchlistService = Depends(get_watchlist_service),
) -> List[dict]:
    """获取自选股分组列表。

    Args:
        service: 自选股用例，由 Depends(get_watchlist_service) 装配。

    Returns:
        List[dict]: 分组列表，含每组的条目数量。
    """
    return service.list_groups()


@router.post(
    "/create_group",
    response_model=WatchlistGroupList,
    summary="新增自选股分类",
    responses={409: {"description": "分类名称已存在"}},
)
def create_watchlist_group(
    payload: WatchlistGroupCreate,
    service: WatchlistService = Depends(get_watchlist_service),
) -> dict:
    """创建自选股分组。

    分组编码由服务端生成，请求体只含用户可编辑字段。

    Args:
        payload: 新建分组请求体（名称、描述、排序权重）。
        service: 自选股用例，由 Depends(get_watchlist_service) 装配。

    Returns:
        dict: 创建后的分组数据。

    Raises:
        HTTPException: 业务校验失败时由 _to_http_error 映射。

    Side Effects:
        写入分组记录。
    """
    try:
        return service.create_group(
            name=payload.name,
            sort_order=payload.sort_order,
            description=payload.description,
        )
    except WatchlistError as exc:
        raise _to_http_error(exc) from exc


@router.post(
    "/update_group",
    response_model=WatchlistGroupList,
    summary="编辑自选股分类（按 group_code 定位）",
    responses={404: {"description": "分类不存在"}, 409: {"description": "分类名称已存在"}},
)
def update_watchlist_group(
    payload: WatchlistGroupUpdate,
    service: WatchlistService = Depends(get_watchlist_service),
) -> dict:
    """更新自选股分组。

    Args:
        payload: 更新请求体，按 group_code 定位且仅修改显式提供的字段。
        service: 自选股用例，由 Depends(get_watchlist_service) 装配。

    Returns:
        dict: 更新后的分组数据。

    Raises:
        HTTPException: 分组不存在或校验失败。

    Side Effects:
        修改分组记录。
    """
    try:
        return service.update_group(
            group_code=payload.group_code,
            name=payload.name,
            description=payload.description,
            sort_order=payload.sort_order,
        )
    except WatchlistError as exc:
        raise _to_http_error(exc) from exc


@router.delete(
    "/delete_group/{group_code}",
    response_model=SimpleSuccess,
    summary="删除自选股分类（逻辑删除）",
    responses={404: {"description": "分类不存在"}},
)
def delete_watchlist_group(
    group_code: str,
    service: WatchlistService = Depends(get_watchlist_service),
) -> dict:
    """删除自选股分组。

    Args:
        group_code: 分组唯一编码，来自路径参数。
        service: 自选股用例，由 Depends(get_watchlist_service) 装配。

    Returns:
        dict: 删除结果。

    Raises:
        HTTPException: 分组不存在或分组非空等业务错误。

    Side Effects:
        删除分组记录。
    """
    try:
        service.delete_group(group_code)
    except WatchlistError as exc:
        raise _to_http_error(exc) from exc
    return {"success": True}


# === 自选股 CRUD ===

@router.post(
    "/get_items_list",
    response_model=WatchlistItemsPaginatedResponse,
    summary="分页查询自选股",
    responses={404: {"description": "分类不存在"}},
)
def get_watchlist_items(
    payload: WatchlistItemsQueryRequest,
    service: WatchlistService = Depends(get_watchlist_service),
) -> dict:
    """分页查询某分类下的自选股。

    Args:
        payload: 分页查询请求体（group_id、pageNum、pageSize）。
        service: 自选股用例，由 Depends(get_watchlist_service) 装配。

    Returns:
        dict: 通用分页结构，list 为当前页条目。

    Raises:
        HTTPException: 分组不存在或查询失败。
    """
    try:
        page = service.list_items(
            group_id=payload.group_id,
            page_num=payload.pageNum,
            page_size=payload.pageSize,
        )
    except WatchlistError as exc:
        raise _to_http_error(exc) from exc
    return paginate_response(page.items, page.total, payload.pageNum, payload.pageSize)


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
def create_watchlist_item(
    id: int,
    payload: WatchlistItemCreate,
    service: WatchlistService = Depends(get_watchlist_service),
) -> dict:
    """新增自选股条目。

    Args:
        id: 目标分组标识，来自路径参数。
        payload: 新增请求体（股票代码、名称、备注）。
        service: 自选股用例，由 Depends(get_watchlist_service) 装配。

    Returns:
        dict: 创建后的条目数据。

    Raises:
        HTTPException: 重复添加或代码非法。

    Side Effects:
        写入自选股记录。
    """
    try:
        return service.create_item(
            group_id=id,
            stock_code=payload.stock_code,
            stock_name=payload.stock_name,
            description=payload.description,
        )
    except WatchlistError as exc:
        raise _to_http_error(exc) from exc


@router.post(
    "/update_item/{id}",
    response_model=WatchlistItemOut,
    summary="编辑自选股（备注/名称）",
    responses={404: {"description": "自选股不存在"}},
)
def update_watchlist_item(
    id: int,
    payload: WatchlistItemUpdate,
    service: WatchlistService = Depends(get_watchlist_service),
) -> dict:
    """更新自选股条目。

    Args:
        id: 条目主键，来自路径参数。
        payload: 更新请求体（备注、冗余名称）。
        service: 自选股用例，由 Depends(get_watchlist_service) 装配。

    Returns:
        dict: 更新后的条目数据。

    Raises:
        HTTPException: 条目不存在或校验失败。

    Side Effects:
        修改自选股记录。
    """
    try:
        return service.update_item(
            item_id=id,
            stock_name=payload.stock_name,
            description=payload.description,
        )
    except WatchlistError as exc:
        raise _to_http_error(exc) from exc


@router.delete(
    "/delete_item/{id}",
    response_model=SimpleSuccess,
    summary="删除自选股（逻辑删除）",
    responses={404: {"description": "自选股不存在"}},
)
def delete_watchlist_item(
    id: int,
    service: WatchlistService = Depends(get_watchlist_service),
) -> dict:
    """删除自选股条目。

    Args:
        id: 条目主键，来自路径参数。
        service: 自选股用例，由 Depends(get_watchlist_service) 装配。

    Returns:
        dict: 删除结果。

    Raises:
        HTTPException: 条目不存在。

    Side Effects:
        删除自选股记录。
    """
    try:
        service.delete_item(id)
    except WatchlistError as exc:
        raise _to_http_error(exc) from exc
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
def move_watchlist_item(
    id: int,
    payload: WatchlistItemMove,
    service: WatchlistService = Depends(get_watchlist_service),
) -> dict:
    """移动自选股条目到其他分组。

    Args:
        id: 条目主键，来自路径参数。
        payload: 移动请求体，含目标分组 ID。
        service: 自选股用例，由 Depends(get_watchlist_service) 装配。

    Returns:
        dict: 移动后的条目数据。

    Raises:
        HTTPException: 条目或目标分组不存在。

    Side Effects:
        修改条目的分组归属。
    """
    try:
        return service.move_item(
            item_id=id,
            target_group_id=payload.target_group_id,
        )
    except WatchlistError as exc:
        raise _to_http_error(exc) from exc
