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
- ``GET    /live-news/channels`` 查询快讯频道列表（降级时只返回「要闻」）
- ``GET    /live-news``          分页查询快讯（支持频道/重要级/关键词/日期过滤）
- ``POST   /live-news/refresh``  手动触发快讯抓取（官方源失败自动降级 NewsNow）
- ``GET    /live-news/{item_id}`` 查询单条快讯详情

设计约束
--------
- 路由层只做协议转换与异常映射，不承载业务校验（SSRF 校验、字段归一化等下沉到服务层）；
- 错误响应统一结构为 ``{"error": ..., "message": ...}``，500 级响应不回显内部细节；
- 服务层 ``IntelligenceService`` 为无状态工厂，路由内按需实例化（``IntelligenceService()``）。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
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
    LiveNewsChannelsResponse,
    LiveNewsItem,
    LiveNewsListResponse,
    LiveNewsRefreshRequest,
    LiveNewsRefreshResponse,
    CalendarCountriesResponse,
    CalendarMonthResponse,
    CalendarRefreshRequest,
    CalendarRefreshResponse,
    CalendarTabsResponse,
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


# ---------------------------------------------------------------------------
# 实时财经快讯（Live News）
#
# 数据源：华尔街见闻 7x24 快讯接口（主），失败时自动降级到 NewsNow 聚合源。
# 降级后仅保留「要闻」单频道且无重要级，前端据此调整 Tab 与隐藏重要级筛选。
# 接口契约与降级策略详见 docs/live-news.md。
#
# 注意路由顺序：/live-news/channels 与 /live-news/refresh 必须注册在
# /live-news/{item_id} 之前，否则会被路径参数 {item_id} 优先匹配。
# ---------------------------------------------------------------------------


def _parse_day_start(raw: str) -> datetime:
    """把 ``YYYY-MM-DD`` 解析为当天 00:00:00（服务端本地时区）。

    Raises:
        HTTPException: 400，日期格式非法。
    """
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d")
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "validation_error", "message": f"invalid date format, expected YYYY-MM-DD: {raw}"},
        ) from exc


def _parse_day_end(raw: str) -> datetime:
    """把 ``YYYY-MM-DD`` 解析为当天 23:59:59，用于闭区间上界。"""
    start = _parse_day_start(raw)
    return start + timedelta(days=1) - timedelta(seconds=1)


@router.get(
    "/live-news/channels",
    response_model=LiveNewsChannelsResponse,
    responses={500: {"model": ErrorResponse}},
    summary="List live news channels",
)
def list_live_news_channels() -> LiveNewsChannelsResponse:
    """查询快讯频道列表（前端 Tab 的数据源）。

    正常模式返回全部 8 个频道；官方源不可用处于降级模式时只返回「要闻」，
    并置 ``degraded=True``，前端据此隐藏「只看重要的」开关并展示降级提示。
    """
    try:
        return LiveNewsChannelsResponse(**IntelligenceService().live_news_channels())
    except Exception as exc:
        raise _internal_error("List live news channels failed", exc)


@router.get(
    "/live-news",
    response_model=LiveNewsListResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="List live news items",
)
def list_live_news(
    channel: str = Query(..., description="频道 ID，如 global-channel / a-stock-channel / tech-channel"),
    important_only: bool = Query(False, description="只看重要的（score >= 阈值）"),
    keyword: Optional[str] = Query(None, max_length=100, description="关键词，匹配标题与正文"),
    date: Optional[str] = Query(None, description="精确查询某日，格式 YYYY-MM-DD；与 date_from/date_to 同时传时以本参数为准"),
    date_from: Optional[str] = Query(None, description="起始日期 YYYY-MM-DD（含当天）"),
    date_to: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD（含当天）"),
    cursor: Optional[str] = Query(None, description="分页游标，取上次响应的 next_cursor"),
    limit: int = Query(30, ge=1, le=100, description="每页条数"),
) -> LiveNewsListResponse:
    """分页查询已落库的快讯，支持频道 / 重要级 / 关键词 / 日期区间过滤。"""
    # 日期区间解析：date 优先级最高，其次 date_from / date_to 组合
    published_from: Optional[datetime] = None
    published_to: Optional[datetime] = None
    try:
        if date:
            published_from = _parse_day_start(date)
            published_to = _parse_day_end(date)
        else:
            if date_from:
                published_from = _parse_day_start(date_from)
            if date_to:
                published_to = _parse_day_end(date_to)
        service = IntelligenceService()
        # 按需刷新：频道无数据时同步抓取保证首屏不空白，数据陈旧时后台异步刷新。
        # 刷新失败只记日志，不影响本次查询（列表始终读库返回）。
        service.ensure_live_news_fresh(channel)
        return LiveNewsListResponse(**service.list_live_news(
            channel=channel,
            important_only=important_only,
            keyword=keyword,
            published_from=published_from,
            published_to=published_to,
            cursor=cursor,
            limit=limit,
        ))
    except IntelligenceServiceError as exc:
        raise _bad_request(exc)
    except HTTPException:
        raise
    except Exception as exc:
        raise _internal_error("List live news failed", exc)


@router.post(
    "/live-news/refresh",
    response_model=LiveNewsRefreshResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Refresh live news from upstream",
)
def refresh_live_news(request: LiveNewsRefreshRequest) -> LiveNewsRefreshResponse:
    """手动触发快讯抓取并落库。

    按频道逐个抓取（fail-open）：单频道失败不影响其他频道；
    全部频道失败且允许降级时，自动改用 NewsNow 兜底源并标记 ``degraded=True``。
    """
    try:
        return LiveNewsRefreshResponse(**IntelligenceService().refresh_live_news(channels=request.channels))
    except IntelligenceServiceError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Refresh live news failed", exc)


@router.get(
    "/live-news/{item_id}",
    response_model=LiveNewsItem,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get one live news item",
)
def get_live_news_item(item_id: int) -> LiveNewsItem:
    """按快讯 ID 查询单条详情；未找到返回 404。

    快讯 ID 未单独建列，但稳定出现在原文链接末尾（``.../livenews/<id>``），
    由仓储层按 URL 后缀匹配，官方源与降级源均可命中。
    """
    try:
        service = IntelligenceService()
        row = service.repo.get_live_news_item_by_id(item_id)
        if row is None:
            raise _not_found(f"live news item not found: {item_id}")
        # 复用服务层的取值辅助：避免 `0 or 默认值` 这类 falsy 陷阱。
        # 阈值按统一业务量纲判定，默认值取自服务层常量（3=重要）
        threshold = max(1, service._config_int("wscn_live_news_important_score", service.IMPORTANT_THRESHOLD))
        return LiveNewsItem(**service._live_news_item_to_dict(row, threshold=threshold))
    except HTTPException:
        raise
    except Exception as exc:
        raise _internal_error("Get live news item failed", exc)


@router.get(
    "/live-calendar/tabs",
    response_model=CalendarTabsResponse,
    summary="List live calendar tabs",
)
def list_live_calendar_tabs() -> CalendarTabsResponse:
    """返回日历分类 Tab 列表（服务端常量，不依赖上游）。"""
    try:
        return CalendarTabsResponse(**IntelligenceService().list_calendar_tabs())
    except Exception as exc:
        raise _internal_error("List calendar tabs failed", exc)


@router.get(
    "/live-calendar/countries",
    response_model=CalendarCountriesResponse,
    summary="List live calendar countries",
)
def list_live_calendar_countries() -> CalendarCountriesResponse:
    """返回国家字典；上游失败时降级为空列表并置 degraded=True。"""
    try:
        return CalendarCountriesResponse(**IntelligenceService().list_calendar_countries())
    except Exception as exc:
        raise _internal_error("List calendar countries failed", exc)


@router.get(
    "/live-calendar",
    response_model=CalendarMonthResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="List live calendar events by month",
)
def list_live_calendar(
    year: int = Query(..., ge=2000, le=2100, description="年（UTC 口径）"),
    month: int = Query(..., ge=1, le=12, description="月"),
    tab: Optional[str] = Query(None, description="分类过滤：macro / earnings / ipo / activity / all"),
    country_id: Optional[str] = Query(None, max_length=2, description="国家代码过滤"),
    importance_min: Optional[int] = Query(None, ge=0, le=4, description="最低重要级（统一业务量纲 0~4）"),
    include_economic_data: bool = Query(False, description="是否包含 FD 经济数据（默认不含）"),
) -> CalendarMonthResponse:
    """查询指定月份的日历事件（聚合去重 + 分类 / 国家 / 重要级过滤）。"""
    try:
        return CalendarMonthResponse(**IntelligenceService().list_calendar(
            year=year,
            month=month,
            tab=tab,
            country_id=country_id,
            importance_min=importance_min,
            include_economic_data=include_economic_data,
        ))
    except IntelligenceServiceError as exc:
        raise _bad_request(exc)
    except HTTPException:
        raise
    except Exception as exc:
        raise _internal_error("List live calendar failed", exc)


@router.post(
    "/live-calendar/refresh",
    response_model=CalendarRefreshResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Refresh live calendar from upstream",
)
def refresh_live_calendar(request: CalendarRefreshRequest) -> CalendarRefreshResponse:
    """手动触发指定月份日历抓取并落库。"""
    try:
        return CalendarRefreshResponse(**IntelligenceService().refresh_calendar(
            year=request.year,
            month=request.month,
        ))
    except IntelligenceServiceError as exc:
        raise _bad_request(exc)
    except HTTPException:
        raise
    except Exception as exc:
        raise _internal_error("Refresh live calendar failed", exc)
