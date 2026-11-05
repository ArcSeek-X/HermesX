# -*- coding: utf-8 -*-
"""
@file: alphasift.py
@description: AlphaSift 选股筛选端点：组件状态与安装、策略与热点、异步/同步筛选任务及状态查询；由 api.v1.router 挂到 /api/v1/alphasift，筛选逻辑在 src.application 的 AlphaSiftService。
@author: Lensgcx (GaoCangxiong)

AlphaSift stock screening API routes.

Exposes component status and guarded installation, strategy and
hotspot discovery, plus asynchronous and synchronous screening
tasks with polling support.
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from api.deps import get_config_dep
from api.v1.errors import api_error
from src.config import Config
from src.auth import COOKIE_NAME, is_auth_enabled, refresh_auth_state, verify_session
from src.application.analysis.alphasift_service import AlphaSiftService, AlphaSiftServiceError
from src.application.runtime.task_queue import TaskStatus as QueueTaskStatus
from src.application.runtime.task_queue import get_task_queue

# 本模块的 APIRouter；由 api.v1.router 挂到 /api/v1/alphasift。
router = APIRouter()


class AlphaSiftScreenRequest(BaseModel):
    """AlphaSift 选股筛选请求体。

    @author: Lensgcx (GaoCangxiong)
    """
    # 筛选目标市场标识。
    market: str = Field("cn", min_length=1, max_length=16)
    # 采用的选股策略 ID。
    strategy: str = Field("dual_low", min_length=1, max_length=64)
    # 最多返回的候选股票数，防止大范围筛选拖慢响应。
    max_results: int = Field(20, ge=1, le=100)


class AlphaSiftStrategyResponse(BaseModel):
    """AlphaSift 策略信息响应体。

    @author: Lensgcx (GaoCangxiong)
    """
    # 策略稳定标识，作为筛选请求入参。
    id: str
    # 策略内部名称。
    name: str = ""
    # 策略展示标题。
    title: str = ""
    # 策略说明文案。
    description: str = ""
    # 策略分类，供前端分组展示。
    category: str = ""
    # 主标签，兼容旧前端的单标签展示。
    tag: str = ""
    # 多标签列表，供筛选与检索。
    tags: List[str] = Field(default_factory=list)
    # 策略适用的市场范围列表。
    market_scope: List[str] = Field(default_factory=list)
    # 策略默认市场标识。
    market: str = ""


class AlphaSiftScreenAccepted(BaseModel):
    """AlphaSift 筛选任务已受理响应体。

    @author: Lensgcx (GaoCangxiong)
    """
    # 异步任务 ID，供状态轮询。
    task_id: str
    # 诊断 trace ID。
    trace_id: str
    # 提交时的任务状态，默认 pending。
    status: str = "pending"
    # 面向用户的提交提示。
    message: str
    # 回显本次采用的策略 ID。
    strategy: str
    # 回显本次筛选的市场。
    market: str
    # 回显本次生效的结果上限。
    max_results: int


class AlphaSiftScreenTaskStatus(BaseModel):
    """AlphaSift 筛选任务状态响应体。

    @author: Lensgcx (GaoCangxiong)
    """
    # 被轮询的任务 ID。
    task_id: str
    # 诊断 trace ID；旧任务可能缺失。
    trace_id: Optional[str] = None
    # 任务状态字符串。
    status: str
    # 执行进度百分比，默认 0。
    progress: int = 0
    # 当前阶段说明；可为空。
    message: Optional[str] = None
    # 失败原因；仅失败态有值。
    error: Optional[str] = None
    # 完成态的筛选结果；未完成时为空。
    result: Optional[Dict[str, Any]] = None


def _service(config: Config) -> AlphaSiftService:
    """返回 AlphaSift 服务实例。

    按当前配置构造，便于草稿配置预览与正式调用共用同一装配入口。

    Args:
        config: 运行时配置，由 Depends(get_config_dep) 注入。

    Returns:
        AlphaSiftService: 使用给定配置的服务实例。
    """
    return AlphaSiftService(config=config)


def _ensure_alphasift_install_access(request: Request) -> None:
    """Gate AlphaSift repair install to desktop mode or an admin-authenticated session.

    限制修复安装入口：仅桌面端本机或已通过管理员认证的请求可执行。安装会改动运行环境，不能对匿名 Web 请求开放。

    Args:
        request: 原始请求对象，用于判断运行模式与会话凭证。

    Returns:
        None。

    Raises:
        HTTPException: 无权限时返回 401/403。
    """
    if os.getenv("HRS_DESKTOP_MODE") == "true":
        return

    refresh_auth_state()
    if not is_auth_enabled():
        raise api_error(
            403,
            "alphasift_install_access_denied",
            "AlphaSift 修复安装仅允许桌面模式或已启用管理员认证的会话。请先启用管理员认证后重试。",
        )

    cookie_val = request.cookies.get(COOKIE_NAME)
    if cookie_val and verify_session(cookie_val):
        return

    raise api_error(
        401,
        "alphasift_install_access_denied",
        "AlphaSift 修复安装需要有效管理员会话。",
    )


def _call_service(fn, /, *args, **kwargs):
    """把服务层业务异常翻译为 HTTP 响应（传输层职责归驱动层）。

    统一捕获服务层携带 status_code/detail 的异常，避免每个端点重复写异常分支。

    Args:
        *args: 被包装调用的入参，原样转给服务层函数。

    Returns:
        服务层调用的返回值。

    Raises:
        HTTPException: 服务层异常按原状态码与 detail 透出。
    """
    try:
        return fn(*args, **kwargs)
    except AlphaSiftServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _screening_task_not_found(task_id: str) -> HTTPException:
    """构造筛选任务不存在的错误响应。

    Args:
        task_id: 查询的任务 ID。

    Returns:
        HTTPException: 404 错误对象。
    """
    return api_error(
        404,
        "alphasift_screen_task_not_found",
        f"选股任务 {task_id} 不存在或已过期",
    )


@router.get("/status")
def alphasift_status(config: Config = Depends(get_config_dep)) -> Dict[str, Any]:
    """返回 AlphaSift 组件状态。

    Args:
        config: 运行时配置，由 Depends 注入。

    Returns:
        Dict[str, Any]: 安装状态、版本与可用性信息。

    Raises:
        HTTPException: 服务层异常经 _call_service 映射。
    """
    return _call_service(_service(config).status)


@router.get("/strategies")
def alphasift_strategies(
    request: Request,
    config: Config = Depends(get_config_dep),
) -> Dict[str, Any]:
    """列出 AlphaSift 可用策略。

    Args:
        request: 原始请求对象。
        config: 运行时配置，由 Depends 注入。

    Returns:
        Dict[str, Any]: 策略列表与元信息。
    """
    return _call_service(_service(config).strategies)


@router.get("/hotspots")
def alphasift_hotspots(
    provider: str = Query("", max_length=32),
    top: int = Query(12, ge=1, le=50),
    refresh: bool = Query(False),
    include_details: bool = Query(False),
    config: Config = Depends(get_config_dep),
) -> Dict[str, Any]:
    """获取 AlphaSift 市场热点。

    Args:
        provider: 热点数据来源标识。
        top: 返回热点数量上限。
        refresh: 是否强制刷新缓存。
        include_details: 是否附带热点明细。
        config: 运行时配置，由 Depends 注入。

    Returns:
        Dict[str, Any]: 热点列表及可选明细。
    """
    refresh_value = refresh if isinstance(refresh, bool) else bool(getattr(refresh, "default", False))
    include_details_value = (
        include_details
        if isinstance(include_details, bool)
        else bool(getattr(include_details, "default", False))
    )
    return _call_service(
        _service(config).hotspots,
        provider=provider,
        top=top,
        refresh=refresh_value,
        include_details=include_details_value,
    )


@router.get("/hotspots/{topic:path}")
def alphasift_hotspot_detail(
    topic: str,
    provider: str = Query("", max_length=32),
    refresh: bool = Query(False),
    config: Config = Depends(get_config_dep),
) -> Dict[str, Any]:
    """获取单个热点详情。

    Args:
        topic: 热点主题标识。
        provider: 热点数据来源标识。
        refresh: 是否强制刷新缓存。
        config: 运行时配置，由 Depends 注入。

    Returns:
        Dict[str, Any]: 该热点的成分与说明。
    """
    refresh_value = refresh if isinstance(refresh, bool) else bool(getattr(refresh, "default", False))
    return _call_service(
        _service(config).hotspot_detail, topic=topic, provider=provider, refresh=refresh_value
    )


@router.post("/install")
def alphasift_install(
    request: Request,
    config: Config = Depends(get_config_dep),
) -> Dict[str, Any]:
    """安装或更新 AlphaSift 组件。

    先经 _ensure_alphasift_install_access 做权限校验，再调用服务层安装。

    Args:
        request: 原始请求对象，用于访问校验。
        config: 运行时配置，由 Depends 注入。

    Returns:
        Dict[str, Any]: 安装结果。

    Side Effects:
        可能下载/更新组件文件，改变运行环境。
    """
    _ensure_alphasift_install_access(request)
    return _call_service(_service(config).install)


@router.post("/screen/tasks", status_code=202, response_model=AlphaSiftScreenAccepted)
def alphasift_start_screen_task(
    request: AlphaSiftScreenRequest,
    http_request: Request,
    config: Config = Depends(get_config_dep),
) -> AlphaSiftScreenAccepted:
    """启动异步选股筛选任务。

    任务在后台线程执行并写入任务队列，端点立即返回 task_id；前端通过 /tasks/{id} 轮询进度。

    Args:
        request: 筛选请求体（市场、策略、结果上限）。
        http_request: 原始请求对象。
        config: 运行时配置，由 Depends 注入。

    Returns:
        AlphaSiftScreenAccepted: 任务 ID、状态与回显参数。

    Side Effects:
        向任务队列提交 run_screen 后台任务。
    """
    task_id = uuid.uuid4().hex
    task_queue = get_task_queue()

    def run_screen() -> Dict[str, Any]:
        """后台线程中执行筛选的主体逻辑。

        Args:
            无显式参数；捕获外层请求与配置。

        Returns:
            Dict[str, Any]: 筛选结果，由任务队列保存为 task.result。

        Side Effects:
            更新任务进度与结果。
        """
        task_queue.update_task_progress(
            task_id,
            20,
            "正在执行 AlphaSift 选股，外部数据源较慢时会持续后台运行",
        )
        result = _call_service(
            _service(config).screen,
            strategy=request.strategy,
            market=request.market,
            max_results=request.max_results,
        )
        task_queue.update_task_progress(
            task_id,
            90,
            f"选股已完成，正在整理 {result.get('candidate_count', 0)} 条候选",
        )
        return result

    task = task_queue.submit_background_task(
        run_screen,
        stock_code="alphasift_screen",
        stock_name=f"{request.strategy} / {request.market}",
        report_type="alphasift_screen",
        message="AlphaSift 选股任务已提交",
        task_id=task_id,
        trace_id=task_id,
    )
    return AlphaSiftScreenAccepted(
        task_id=task.task_id,
        trace_id=task.trace_id or task.task_id,
        status=task.status.value if isinstance(task.status, QueueTaskStatus) else str(task.status),
        message=task.message or "AlphaSift 选股任务已提交",
        strategy=request.strategy,
        market=request.market,
        max_results=request.max_results,
    )


@router.get("/screen/tasks/{task_id}", response_model=AlphaSiftScreenTaskStatus)
def alphasift_screen_task_status(task_id: str) -> AlphaSiftScreenTaskStatus:
    """查询筛选任务状态。

    Args:
        task_id: 任务 ID，来自路径参数。

    Returns:
        AlphaSiftScreenTaskStatus: 状态、进度、错误与结果。

    Raises:
        HTTPException: 任务不存在时返回 404。
    """
    task = get_task_queue().get_task(task_id)
    if task is None or task.report_type != "alphasift_screen":
        raise _screening_task_not_found(task_id)

    result = task.result if task.status == QueueTaskStatus.COMPLETED and isinstance(task.result, dict) else None
    return AlphaSiftScreenTaskStatus(
        task_id=task.task_id,
        trace_id=task.trace_id or task.task_id,
        status=task.status.value if isinstance(task.status, QueueTaskStatus) else str(task.status),
        progress=task.progress,
        message=task.message,
        error=task.error,
        result=result,
    )


@router.post("/screen")
def alphasift_screen(
    request: AlphaSiftScreenRequest,
    http_request: Request,
    config: Config = Depends(get_config_dep),
) -> Dict[str, Any]:
    """同步执行选股筛选。

    适用于结果量小、需要立即拿到的场景；大范围筛选应使用异步任务接口。

    Args:
        request: 筛选请求体。
        http_request: 原始请求对象。
        config: 运行时配置，由 Depends 注入。

    Returns:
        Dict[str, Any]: 筛选结果。

    Side Effects:
        无后台任务提交，但可能触发服务层缓存更新。
    """
    return _call_service(
        _service(config).screen,
        strategy=request.strategy,
        market=request.market,
        max_results=request.max_results,
    )
