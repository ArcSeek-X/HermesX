# -*- coding: utf-8 -*-
"""
@file: recent_search.py
@description: 个股最近搜索端点：列表、记录与一键清空；由 api.v1.router 挂到 /api/v1/recent-search，业务规则在 src.application.recent_search.RecentSearchService。
@author: Lensgcx (GaoCangxiong)

===================================
个股最近搜索 API
===================================

路由前缀：/api/v1/recent-search

传输层只做三件事：解析请求、调用用例、把业务校验错误映射为 HTTP 422。
查重、顶置与队列裁剪在应用层与仓储的单个写事务内完成，本模块不访问 ORM。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_recent_search_service
from api.v1.errors import api_error
from api.v1.schemas.recent_search import (
    RecentSearchItem,
    RecentSearchListResponse,
    RecentSearchRecordCreate,
    RecentSearchRecordResponse,
    SimpleSuccess,
)
from src.application.recent_search import RecentSearchService, RecentSearchValidationError

logger = logging.getLogger(__name__)

# 路由前缀统一在 api/v1/router.py 的 include_router(prefix="/recent-search") 处添加。
router = APIRouter(tags=["recent-search"])


@router.get(
    "/list",
    response_model=RecentSearchListResponse,
    summary="列出最近搜索",
    description="按最近搜索时间倒序返回当前用户最多 10 条记录。",
)
def list_recent_search(
    user_id: str | None = Query(None, max_length=64, description="用户标识，缺省 default"),
    service: RecentSearchService = Depends(get_recent_search_service),
) -> RecentSearchListResponse:
    """查询最近搜索列表。"""
    records = service.list_recent(user_id=user_id)
    return RecentSearchListResponse(items=[RecentSearchItem(**record) for record in records])


@router.post(
    "/record",
    response_model=RecentSearchRecordResponse,
    summary="记录一次搜索",
    description="同代码刷新并顶到队首；写入后队列裁剪到 10 条。",
)
def record_recent_search(
    payload: RecentSearchRecordCreate,
    service: RecentSearchService = Depends(get_recent_search_service),
) -> RecentSearchRecordResponse:
    """记录或更新一条最近搜索。"""
    try:
        record = service.record(
            stock_code=payload.stock_code,
            stock_name=payload.stock_name,
            market=payload.market,
            user_id=payload.user_id,
        )
    except RecentSearchValidationError as exc:
        raise api_error(422, exc.error_code, str(exc)) from exc
    except Exception as exc:  # pragma: no cover - 数据库异常统一记录并转 500
        logger.exception("记录最近搜索失败: stock_code=%s", payload.stock_code)
        raise HTTPException(status_code=500, detail="最近搜索记录失败") from exc
    return RecentSearchRecordResponse(item=RecentSearchItem(**record))


@router.delete(
    "/clear",
    response_model=SimpleSuccess,
    summary="一键清空最近搜索",
    description="删除当前用户的全部最近搜索记录，重复调用保持幂等。",
)
def clear_recent_search(
    user_id: str | None = Query(None, max_length=64, description="用户标识，缺省 default"),
    service: RecentSearchService = Depends(get_recent_search_service),
) -> SimpleSuccess:
    """清空当前用户的最近搜索列表。"""
    service.clear_all(user_id=user_id)
    return SimpleSuccess(success=True)
