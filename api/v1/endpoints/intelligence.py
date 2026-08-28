# -*- coding: utf-8 -*-
"""资讯源（情报源）API 端点。

作用
----
本文件是「本地资讯池 / 情报源」能力的 FastAPI 路由层，把 HTTP 请求转发给
``src/services/intelligence_service.py`` 中的 ``IntelligenceService``，并负责：

1. 请求 -> 服务层：把 Pydantic 请求模型转成普通 dict（``model_dump``）传入服务层；
2. 异常 -> HTTP 错误：将 ``IntelligenceServiceError`` 映射为 400（校验失败）或
   404（模板/源不存在），其余未预期异常统一映射为 500（错误文案先脱敏）；
3. 响应 -> 模型：把服务层返回 dict 包装成对应的 Pydantic 响应模型。

所有路由挂载在 ``/intelligence`` 前缀下（由上层 router 注册决定），包括：

- ``POST   /sources``            创建自定义资讯源
- ``GET    /sources``            分页列出资讯源（支持按启用状态/类型/作用域/市场过滤）
- ``GET    /sources/templates``  列出内置源模板（可按类型/市场过滤）
- ``POST   /sources/templates/{id}``  基于内置模板创建源
- ``POST   /sources/defaults``   批量创建全部内置源（默认停用）
- ``POST   /sources/test``       不落库的连通性试抓取（dry-run）
- ``POST   /sources/{id}/fetch`` 抓取单个源并入库（支持 dry_run）
- ``POST   /sources/fetch-enabled``  抓取全部启用源（fail-open）
- ``GET    /items``              分页查询已落库的资讯条目（支持作用域/市场/关键词/时间窗过滤）

设计约束
--------
- 路由层只做协议转换与异常映射，不承载业务校验（SSRF 校验、字段归一化等下沉到服务层）；
- 错误响应统一结构为 ``{"error": ..., "message": ...}``，500 级响应不回显内部细节；
- 服务层 ``IntelligenceService`` 为无状态工厂，路由内按需实例化（``IntelligenceService()``）。
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.v1.schemas.common import ErrorResponse
from api.v1.schemas.intelligence import (
    IntelligenceDefaultSourceCreateResponse,
    IntelligenceDefaultSourcesCreateRequest,
    IntelligenceFetchResponse,
    IntelligenceItemListResponse,
    IntelligenceSourceCreateRequest,
    IntelligenceSourceItem,
    IntelligenceSourceListResponse,
    IntelligenceSourceTemplateCreateRequest,
    IntelligenceSourceTemplateListResponse,
    IntelligenceSourceTestResponse,
)
from src.services.intelligence_service import IntelligenceService, IntelligenceServiceError
from src.services.run_diagnostics import sanitize_diagnostic_text

logger = logging.getLogger(__name__)
router = APIRouter()


def _bad_request(exc: Exception) -> HTTPException:
    """把服务层抛出的校验错误包装成 400 响应（保留原始可读文案）。"""
    return HTTPException(status_code=400, detail={"error": "validation_error", "message": str(exc)})


def _not_found(message: str) -> HTTPException:
    """把“模板/源不存在”包装成 404 响应。"""
    return HTTPException(status_code=404, detail={"error": "not_found", "message": message})


def _internal_error(message: str, exc: Exception) -> HTTPException:
    """未预期异常：内部记录脱敏后的错误详情，对外统一返回 500 且不泄漏内部信息。

    注意：响应 message 使用泛化文案，真实细节只写入日志（已先经 sanitize）。
    """
    sanitized_error = sanitize_diagnostic_text(str(exc), max_length=300) or "internal intelligence error"
    logger.error("%s: %s", message, sanitized_error)
    return HTTPException(
        status_code=500,
        detail={"error": "internal_error", "message": f"{message}: internal intelligence service error"},
    )


@router.post("/sources", response_model=IntelligenceSourceItem, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}, summary="Create intelligence source")
def create_source(request: IntelligenceSourceCreateRequest) -> IntelligenceSourceItem:
    """创建自定义资讯源：校验失败（如 SSRF 校验不通过、名称重复）返回 400。"""
    try:
        return IntelligenceSourceItem(**IntelligenceService().create_source(request.model_dump()))
    except IntelligenceServiceError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Create intelligence source failed", exc)


@router.get("/sources", response_model=IntelligenceSourceListResponse, responses={500: {"model": ErrorResponse}}, summary="List intelligence sources")
def list_sources(
    enabled: Optional[bool] = Query(None),  # 按启用状态过滤（None 表示不过滤）
    source_type: Optional[str] = Query(None),
    scope_type: Optional[str] = Query(None),
    market: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> IntelligenceSourceListResponse:
    try:
        return IntelligenceSourceListResponse(**IntelligenceService().list_sources(
            enabled=enabled, source_type=source_type, scope_type=scope_type,
            market=market, page=page, page_size=page_size,
        ))
    except Exception as exc:
        raise _internal_error("List intelligence sources failed", exc)


@router.get("/sources/templates", response_model=IntelligenceSourceTemplateListResponse, responses={500: {"model": ErrorResponse}}, summary="List built-in intelligence source templates")
def list_source_templates(
    source_type: Optional[str] = Query(None),  # 按数据源类型过滤（rss/atom/newsnow）
    market: Optional[str] = Query(None),
) -> IntelligenceSourceTemplateListResponse:
    try:
        return IntelligenceSourceTemplateListResponse(**IntelligenceService().list_source_templates(
            source_type=source_type,
            market=market,
        ))
    except Exception as exc:
        raise _internal_error("List intelligence source templates failed", exc)


@router.post("/sources/template/{template_id}", response_model=IntelligenceSourceItem, responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}, summary="Create intelligence source from a built-in template")
def create_source_from_template(
    template_id: str,  # 内置模板标识（如 cctv-finance）
    request: IntelligenceSourceTemplateCreateRequest = IntelligenceSourceTemplateCreateRequest(),
) -> IntelligenceSourceItem:
    try:
        return IntelligenceSourceItem(**IntelligenceService().create_source_from_template(
            template_id,
            request.model_dump(exclude_none=True),  # 仅把非 None 的覆盖字段传给服务层
        ))
    except IntelligenceServiceError as exc:
        message = str(exc)
        # 模板不存在映射为 404，其余校验失败映射为 400
        if "template not found" in message.lower():
            raise _not_found(message)
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Create intelligence source from template failed", exc)


@router.post("/sources/defaults", response_model=IntelligenceDefaultSourceCreateResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}, summary="Create built-in default intelligence sources")
def create_default_sources(
    request: IntelligenceDefaultSourcesCreateRequest = IntelligenceDefaultSourcesCreateRequest(),  # 可选覆盖字段（如 enabled）
) -> IntelligenceDefaultSourceCreateResponse:
    """批量创建全部内置资讯源：已存在的同名源会被跳过并保留原记录。"""
    try:
        return IntelligenceDefaultSourceCreateResponse(**IntelligenceService().create_default_sources(
            request.model_dump(exclude_none=True),
        ))
    except IntelligenceServiceError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Create default intelligence sources failed", exc)


@router.post("/sources/test", response_model=IntelligenceSourceTestResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}, summary="Dry-run an intelligence source payload")
def test_source_payload(request: IntelligenceSourceCreateRequest) -> IntelligenceSourceTestResponse:
    """连通性试抓取：只拉取少量样本用于确认源可用，不写入数据库。"""
    try:
        return IntelligenceSourceTestResponse(**IntelligenceService().test_source(request.model_dump()))
    except IntelligenceServiceError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Test intelligence source failed", exc)


@router.post("/sources/{source_id}/fetch", response_model=IntelligenceFetchResponse, responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}, summary="Fetch one intelligence source")
def fetch_source(source_id: int, dry_run: bool = Query(False)) -> IntelligenceFetchResponse:
    """抓取单个资讯源并入库；dry_run=True 时只解析不落库。

    源不存在映射为 404，其余校验失败（如 URL 不合法）映射为 400。
    """
    try:
        return IntelligenceFetchResponse(**IntelligenceService().fetch_source(source_id, dry_run=dry_run))
    except IntelligenceServiceError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise _not_found(message)
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Fetch intelligence source failed", exc)


@router.post("/sources/fetch-enabled", response_model=IntelligenceFetchResponse, responses={500: {"model": ErrorResponse}}, summary="Fetch all enabled intelligence sources with fail-open semantics")
def fetch_enabled_sources() -> IntelligenceFetchResponse:
    """抓取所有已启用资讯源：单源失败不影响其他源（fail-open），整体不会抛 400。"""
    try:
        return IntelligenceFetchResponse(**IntelligenceService().fetch_enabled_sources())
    except Exception as exc:
        raise _internal_error("Fetch enabled intelligence sources failed", exc)


@router.get("/items", response_model=IntelligenceItemListResponse, responses={500: {"model": ErrorResponse}}, summary="List persisted intelligence items")
def list_items(
    scope_type: Optional[str] = Query(None),  # 按作用域类型过滤（symbol/market/sector）
    scope_value: Optional[str] = Query(None),  # 作用域取值（如股票代码、板块名）
    market: Optional[str] = Query(None),  # 按市场过滤
    query: Optional[str] = Query(None),  # 关键词模糊匹配（标题/摘要）
    days: Optional[int] = Query(None, ge=1),  # 仅返回最近 N 天条目
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> IntelligenceItemListResponse:
    try:
        return IntelligenceItemListResponse(**IntelligenceService().list_items(
            scope_type=scope_type, scope_value=scope_value, market=market,
            query=query, days=days, page=page, page_size=page_size,
        ))
    except Exception as exc:
        raise _internal_error("List intelligence items failed", exc)  # 仅内部异常可能触发 500
