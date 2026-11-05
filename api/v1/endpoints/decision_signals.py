# -*- coding: utf-8 -*-
"""
@file: decision_signals.py
@description: 决策信号端点：信号创建/查询/重评估/状态更新/反馈，以及结果评估、统计与画像校准；写操作要求管理员会话，由 api.v1.router 挂到 /api/v1/decision-signals。
@author: Lensgcx (GaoCangxiong)

DecisionSignal API endpoints.

Exposes CRUD-like signal operations, guardrail-aware reassessment,
outcome evaluation, statistics and profile calibration.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Security
from fastapi.security import APIKeyCookie

from api.v1.schemas.common import ErrorResponse
from api.v1.schemas.decision_signals import (
    DecisionSignalCreateRequest,
    DecisionSignalFeedbackItem,
    DecisionSignalFeedbackRequest,
    DecisionSignalItem,
    DecisionSignalListResponse,
    DecisionSignalMutationResponse,
    DecisionSignalOutcomeListResponse,
    DecisionSignalOutcomeRunRequest,
    DecisionSignalOutcomeRunResponse,
    DecisionSignalOutcomeStatsResponse,
    DecisionSignalReassessRequest,
    DecisionSignalReassessErrorResponse,
    DecisionSignalReassessResponse,
    DecisionSignalStatusUpdateRequest,
)
from src.auth import COOKIE_NAME
from src.application.decision.decision_signal_service import (
    DecisionSignalNotFoundError,
    DecisionSignalService,
    DecisionSignalStorageError,
)
from src.application.decision.decision_signal_outcome_service import DecisionSignalOutcomeService
from src.application.decision.decision_signal_reassess_service import (
    DecisionSignalReassessGuardrailBlockedError,
    DecisionSignalReassessService,
    DecisionSignalSourceReportNotFoundError,
    DecisionSignalUnsupportedReportSnapshotError,
    DecisionSignalUnsupportedReportTypeError,
)


# 模块级日志器，记录信号服务异常与堆栈。
logger = logging.getLogger(__name__)

# 管理员会话 Cookie 提取器，用于写操作的 Security 依赖。
admin_session_cookie = APIKeyCookie(
    name=COOKIE_NAME,
    scheme_name="AdminSessionCookie",
    auto_error=False,
)
# 本模块的 APIRouter；由 api.v1.router 挂到 /api/v1/decision-signals。
router = APIRouter(dependencies=[Security(admin_session_cookie)])

# OpenAPI 中写操作共用的 401 响应描述，避免每个路由重复声明。
AUTH_RESPONSE = {
    401: {
        "model": ErrorResponse,
        "description": "未登录或管理员会话无效（ADMIN_AUTH_ENABLED=true 时）",
    },
}


def _bad_request(exc: Exception, *, error: str = "validation_error") -> HTTPException:
    """构造请求参数错误响应。

    Args:
        exc: 服务层校验异常。
        error: 写入响应体的错误码。

    Returns:
        HTTPException: 400 错误对象。
    """
    return HTTPException(
        status_code=400,
        detail={"error": error, "message": str(exc)},
    )


def _not_found(exc: Exception) -> HTTPException:
    """构造资源不存在响应。

    Args:
        exc: 服务层资源不存在异常。

    Returns:
        HTTPException: 404 错误对象。
    """
    return HTTPException(
        status_code=404,
        detail={"error": "not_found", "message": str(exc)},
    )


def _error(status_code: int, exc: Exception, *, error: str) -> HTTPException:
    """构造通用错误响应。

    Args:
        status_code: HTTP 状态码。
        exc: 原始异常，其可读文案写入 message。
        error: 机器可识别错误码。

    Returns:
        HTTPException: 指定状态码的错误对象。
    """
    return HTTPException(
        status_code=status_code,
        detail={"error": error, "message": str(exc)},
    )


def _internal_error(message: str, exc: Exception) -> HTTPException:
    """构造内部错误响应。

    堆栈只进日志，对外返回统一 500 文案。

    Args:
        message: 日志上下文。
        exc: 原始异常。

    Returns:
        HTTPException: 500 错误对象。

    Side Effects:
        写一条带堆栈的 ERROR 级日志。
    """
    logger.error("%s: %s", message, exc, exc_info=True)
    return HTTPException(
        status_code=500,
        detail={"error": "internal_error", "message": message},
    )


def _guardrail_blocked(exc: DecisionSignalReassessGuardrailBlockedError) -> HTTPException:
    """构造护栏拦截响应。

    把服务层的护栏异常转成结构化错误体，供前端展示具体拦截原因。

    Args:
        exc: 护栏拦截异常。

    Returns:
        HTTPException: 400 错误对象，detail 为 DecisionSignalReassessErrorResponse 形状。
    """
    response = DecisionSignalReassessErrorResponse(
        error="guardrail_blocked",
        message="Reassessed decision signal was blocked by guardrail.",
        blocked_reason=exc.blocked_reason,
        warnings=exc.warnings,
    )
    return HTTPException(status_code=400, detail=response.model_dump())


@router.post(
    "",
    response_model=DecisionSignalMutationResponse,
    responses={
        **AUTH_RESPONSE,
        400: {"model": ErrorResponse, "description": "请求字段非法"},
        422: {"model": ErrorResponse, "description": "请求体或路径参数校验失败"},
        500: {"model": ErrorResponse, "description": "创建失败"},
    },
    summary="创建或去重决策信号",
    description=(
        "显式写入 DecisionSignal。未传 horizon/expires_at 时由服务补默认生命周期；"
        "命中同源去重键或窄 relaxed 去重时返回已有记录和 created=false；"
        "active 新建或 expired 续期会失效同股旧 active 相反信号，"
        "active duplicate retry 也会重跑该修复；普通旧 duplicate/replay 不作为新的激活事件；"
        "不保证并发绝对幂等。"
    ),
    operation_id="createDecisionSignal",
)
def create_signal(request: DecisionSignalCreateRequest) -> DecisionSignalMutationResponse:
    """创建决策信号。

    Args:
        request: 信号创建请求体；须通过管理员会话校验。

    Returns:
        DecisionSignalMutationResponse: 信号详情与是否新建。

    Raises:
        HTTPException: 参数错误 400、未授权 401、服务异常 500。

    Side Effects:
        写入决策信号记录。
    """
    service = DecisionSignalService()
    try:
        payload = request.model_dump(exclude_unset=True)
        return DecisionSignalMutationResponse(**service.create_signal(payload))
    except DecisionSignalStorageError as exc:
        raise _internal_error("Create decision signal failed", exc)
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Create decision signal failed", exc)


@router.get(
    "",
    response_model=DecisionSignalListResponse,
    responses={
        **AUTH_RESPONSE,
        400: {"model": ErrorResponse, "description": "查询参数非法"},
        422: {"model": ErrorResponse, "description": "查询参数校验失败"},
        500: {"model": ErrorResponse, "description": "查询失败"},
    },
    summary="查询决策信号列表",
    description=(
        "分页查询 DecisionSignal；读取前会懒过期已到 expires_at 的 active 信号。"
        "当 source_type=analysis 且只传 source_report_id 查询时，若无命中信号会尝试基于该历史报告一次性懒回填 "
        "（仅首次命中列表场景，且该精确查询会触发历史决策信号回填写入，属于 read-with-write 行为；"
        "不影响其他分页列表筛选参数场景）。"
        "holding_only=true 只读取 active 账户的 portfolio_positions 缓存持仓，不触发 portfolio snapshot replay。"
    ),
    operation_id="listDecisionSignals",
)
def list_signals(
    market: Optional[str] = Query(None, description="Optional market filter: cn/hk/us/jp/kr/tw"),
    stock_code: Optional[str] = Query(None, description="Optional stock code filter"),
    action: Optional[str] = Query(None, description="Optional decision action filter"),
    market_phase: Optional[str] = Query(None, description="Optional market phase filter"),
    decision_profile: Optional[str] = Query(
        None,
        description="Optional decision profile filter: conservative/balanced/aggressive/unknown",
    ),
    source_type: Optional[str] = Query(None, description="Optional source type filter"),
    source_report_id: Optional[int] = Query(None, description="Optional source report id filter"),
    trace_id: Optional[str] = Query(None, description="Optional trace id filter"),
    trigger_source: Optional[str] = Query(None, description="Optional trigger source filter"),
    status: Optional[str] = Query(None, description="Optional status filter"),
    created_from: Optional[str] = Query(None, description="Inclusive created_at lower bound"),
    created_to: Optional[str] = Query(None, description="Inclusive created_at upper bound"),
    expires_from: Optional[str] = Query(None, description="Inclusive expires_at lower bound"),
    expires_to: Optional[str] = Query(None, description="Inclusive expires_at upper bound"),
    holding_only: bool = Query(False, description="Filter to active cached portfolio holdings only"),
    account_id: Optional[int] = Query(
        None,
        description="Optional active portfolio account id for holding_only",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> DecisionSignalListResponse:
    """列出决策信号。

    支持按市场、代码、动作、阶段、画像、来源、报告/跟踪 ID、触发来源、状态、创建与过期时间区间、以及持仓与账户维度组合过滤。

    Args:
        market / stock_code / action / market_phase / decision_profile / source_type: 信号属性过滤。
        source_report_id / trace_id / trigger_source: 来源与链路过滤。
        status / created_from / created_to / expires_from / expires_to: 状态与时间区间过滤。
        holding_only / account_id: 与持仓账户关联的过滤。
        page / page_size: 分页参数。

    Returns:
        DecisionSignalListResponse: 当前页信号与总数。

    Raises:
        HTTPException: 参数错误 400、服务异常 500。
    """
    service = DecisionSignalService()
    try:
        return DecisionSignalListResponse(
            **service.list_signals(
                market=market,
                stock_code=stock_code,
                action=action,
                market_phase=market_phase,
                decision_profile=decision_profile,
                source_type=source_type,
                source_report_id=source_report_id,
                trace_id=trace_id,
                trigger_source=trigger_source,
                status=status,
                created_from=created_from,
                created_to=created_to,
                expires_from=expires_from,
                expires_to=expires_to,
                holding_only=holding_only,
                account_id=account_id,
                page=page,
                page_size=page_size,
            )
        )
    except DecisionSignalStorageError as exc:
        raise _internal_error("List decision signals failed", exc)
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("List decision signals failed", exc)


@router.post(
    "/outcomes/run",
    response_model=DecisionSignalOutcomeRunResponse,
    responses={
        **AUTH_RESPONSE,
        400: {"model": ErrorResponse, "description": "请求字段非法"},
        404: {"model": ErrorResponse, "description": "信号不存在"},
        422: {"model": ErrorResponse, "description": "请求体校验失败"},
        500: {"model": ErrorResponse, "description": "后验计算失败"},
    },
    summary="触发决策信号后验评估",
    description=(
        "显式触发 signal-level outcome 计算；默认跳过 completed 和终态 unable，"
        "但会重算缺少行情数据等可恢复 unable；force=true 会重算并覆盖同一 "
        "signal_id+horizon+engine_version。"
    ),
    operation_id="runDecisionSignalOutcomes",
)
def run_outcomes(request: DecisionSignalOutcomeRunRequest) -> DecisionSignalOutcomeRunResponse:
    """执行信号结果评估。

    Args:
        request: 评估请求体，可指定信号 ID、周期、强制重算与批量筛选条件。

    Returns:
        DecisionSignalOutcomeRunResponse: 结果明细与各状态计数。

    Raises:
        HTTPException: 参数错误 400、服务异常 500。

    Side Effects:
        写入或刷新结果评估记录。
    """
    service = DecisionSignalOutcomeService()
    try:
        return DecisionSignalOutcomeRunResponse(
            **service.run_outcomes(
                signal_id=request.signal_id,
                horizons=request.horizons,
                force=request.force,
                market=request.market,
                stock_code=request.stock_code,
                action=request.action,
                source_type=request.source_type,
                status=request.status,
                limit=request.limit,
            )
        )
    except DecisionSignalNotFoundError as exc:
        raise _not_found(exc)
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Run decision signal outcomes failed", exc)


@router.get(
    "/outcomes",
    response_model=DecisionSignalOutcomeListResponse,
    responses={
        **AUTH_RESPONSE,
        400: {"model": ErrorResponse, "description": "查询参数非法"},
        422: {"model": ErrorResponse, "description": "查询参数校验失败"},
        500: {"model": ErrorResponse, "description": "查询失败"},
    },
    summary="查询决策信号后验结果",
    description="分页查询 signal-level outcome；默认只查当前 signal 后验 engine_version。",
    operation_id="listDecisionSignalOutcomes",
)
def list_outcomes(
    signal_id: Optional[int] = Query(None, gt=0),
    horizon: Optional[str] = Query(None),
    engine_version: Optional[str] = Query(None),
    eval_status: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> DecisionSignalOutcomeListResponse:
    """列出信号评估结果。

    Args:
        signal_id: 指定信号 ID；为空表示不限。
        horizon: 持有周期过滤。
        engine_version: 引擎版本过滤。
        eval_status: 评估状态过滤。
        outcome: 结果值过滤。
        page / page_size: 分页参数。

    Returns:
        DecisionSignalOutcomeListResponse: 当前页评估记录与总数。
    """
    service = DecisionSignalOutcomeService()
    try:
        return DecisionSignalOutcomeListResponse(
            **service.list_outcomes(
                signal_id=signal_id,
                horizon=horizon,
                engine_version=engine_version,
                eval_status=eval_status,
                outcome=outcome,
                page=page,
                page_size=page_size,
            )
        )
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("List decision signal outcomes failed", exc)


@router.get(
    "/outcomes/stats",
    response_model=DecisionSignalOutcomeStatsResponse,
    responses={
        **AUTH_RESPONSE,
        400: {"model": ErrorResponse, "description": "查询参数非法"},
        422: {"model": ErrorResponse, "description": "查询参数校验失败"},
        500: {"model": ErrorResponse, "description": "统计失败"},
    },
    summary="查询决策信号后验统计",
    description="默认统计当前 engine_version，且排除 archived 信号。",
    operation_id="getDecisionSignalOutcomeStats",
)
def get_outcome_stats(
    horizons: Optional[List[str]] = Query(None),
    engine_version: Optional[str] = Query(None),
    statuses: Optional[List[str]] = Query(None),
) -> DecisionSignalOutcomeStatsResponse:
    """获取信号评估统计。

    Args:
        horizons: 统计覆盖的持有周期列表。
        engine_version: 引擎版本过滤。
        statuses: 参与统计的信号状态列表。

    Returns:
        DecisionSignalOutcomeStatsResponse: 总体指标、分桶明细与画像校准结果。
    """
    service = DecisionSignalOutcomeService()
    try:
        return DecisionSignalOutcomeStatsResponse(
            **service.get_stats(
                horizons=horizons,
                engine_version=engine_version,
                statuses=statuses,
            )
        )
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Get decision signal outcome stats failed", exc)


@router.post(
    "/reassess",
    response_model=DecisionSignalReassessResponse,
    responses={
        **AUTH_RESPONSE,
        400: {"model": DecisionSignalReassessErrorResponse, "description": "历史报告不适用或持久化被风控阻断"},
        404: {"model": ErrorResponse, "description": "来源历史报告不存在"},
        422: {"model": ErrorResponse, "description": "请求体校验失败"},
        500: {"model": ErrorResponse, "description": "重评估失败"},
    },
    summary="重评估决策风格并可选保存",
    description=(
        "基于 source_report_id 对应的持久化历史报告快照重新计算 decision_profile 信号；"
        "persist=false 返回只读 preview，persist=true 将通过 guardrail 的服务端结果写入 DecisionSignal。"
    ),
    operation_id="reassessDecisionSignalPreview",
)
def reassess_signal(request: DecisionSignalReassessRequest) -> DecisionSignalReassessResponse:
    """重评估指定信号。

    基于历史报告重新生成信号；护栏拦截时返回具名错误，未要求持久化时只给预览。

    Args:
        request: 重评估请求体，含报告 ID、画像与是否落库。

    Returns:
        DecisionSignalReassessResponse: 预览、落库项与持久化状态。

    Raises:
        HTTPException: 报告类型/快照不支持或护栏拦截时返回 400。

    Side Effects:
        persist=True 时写入或刷新信号记录。
    """
    service = DecisionSignalReassessService()
    try:
        return DecisionSignalReassessResponse(
            **service.reassess(
                source_report_id=request.source_report_id,
                decision_profile=request.decision_profile,
                persist=request.persist,
            )
        )
    except DecisionSignalSourceReportNotFoundError as exc:
        raise _error(404, exc, error="source_report_not_found")
    except DecisionSignalUnsupportedReportTypeError as exc:
        raise _error(400, exc, error="unsupported_report_type")
    except DecisionSignalUnsupportedReportSnapshotError as exc:
        raise _error(400, exc, error="unsupported_report_snapshot")
    except DecisionSignalReassessGuardrailBlockedError as exc:
        raise _guardrail_blocked(exc)
    except Exception as exc:
        raise _internal_error("Reassess decision signal failed", exc)


@router.get(
    "/latest/{stock_code}",
    response_model=DecisionSignalListResponse,
    responses={
        **AUTH_RESPONSE,
        400: {"model": ErrorResponse, "description": "请求参数非法"},
        422: {"model": ErrorResponse, "description": "路径或查询参数校验失败"},
        500: {"model": ErrorResponse, "description": "查询失败"},
    },
    summary="查询股票最新 active 决策信号",
    description="返回指定股票最新 active 信号列表；读取前会执行懒过期。",
    operation_id="getLatestDecisionSignals",
)
def get_latest_active(
    stock_code: str,
    market: Optional[str] = Query(None, description="Optional market filter: cn/hk/us/jp/kr/tw"),
    limit: int = Query(1, ge=1, le=100),
) -> DecisionSignalListResponse:
    """获取最新有效信号。

    按股票与市场取仍在生效期内的最新信号，供个股页直接展示。

    Args:
        stock_code: 股票代码。
        market: 市场标识。
        limit: 返回条数上限。

    Returns:
        DecisionSignalListResponse: 有效信号列表。
    """
    service = DecisionSignalService()
    try:
        return DecisionSignalListResponse(
            **service.get_latest_active(
                stock_code=stock_code,
                market=market,
                limit=limit,
            )
        )
    except DecisionSignalStorageError as exc:
        raise _internal_error("Get latest decision signals failed", exc)
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Get latest decision signals failed", exc)


@router.get(
    "/{signal_id}",
    response_model=DecisionSignalItem,
    responses={
        **AUTH_RESPONSE,
        404: {"model": ErrorResponse, "description": "信号不存在"},
        422: {"model": ErrorResponse, "description": "路径参数校验失败"},
        500: {"model": ErrorResponse, "description": "查询失败"},
    },
    summary="查询单条决策信号",
    description="按 ID 查询单条 DecisionSignal；读取前会执行懒过期。",
    operation_id="getDecisionSignal",
)
def get_signal(signal_id: int) -> DecisionSignalItem:
    """按 ID 获取信号。

    Args:
        signal_id: 信号主键，来自路径参数。

    Returns:
        DecisionSignalItem: 完整信号详情。

    Raises:
        HTTPException: 不存在 404。
    """
    service = DecisionSignalService()
    try:
        return DecisionSignalItem(**service.get_signal(signal_id))
    except DecisionSignalNotFoundError as exc:
        raise _not_found(exc)
    except DecisionSignalStorageError as exc:
        raise _internal_error("Get decision signal failed", exc)
    except Exception as exc:
        raise _internal_error("Get decision signal failed", exc)


@router.get(
    "/{signal_id}/outcomes",
    response_model=DecisionSignalOutcomeListResponse,
    responses={
        **AUTH_RESPONSE,
        404: {"model": ErrorResponse, "description": "信号不存在"},
        422: {"model": ErrorResponse, "description": "路径参数校验失败"},
        500: {"model": ErrorResponse, "description": "查询失败"},
    },
    summary="查询单个决策信号后验结果",
    description="返回指定 signal_id 在当前 engine_version 下的后验结果。",
    operation_id="listDecisionSignalOutcomesBySignal",
)
def list_signal_outcomes(signal_id: int) -> DecisionSignalOutcomeListResponse:
    """列出指定信号的结果记录。

    Args:
        signal_id: 信号主键，来自路径参数。

    Returns:
        DecisionSignalOutcomeListResponse: 该信号在各周期下的评估结果。
    """
    service = DecisionSignalOutcomeService()
    try:
        return DecisionSignalOutcomeListResponse(**service.list_signal_outcomes(signal_id))
    except DecisionSignalNotFoundError as exc:
        raise _not_found(exc)
    except Exception as exc:
        raise _internal_error("List decision signal outcomes failed", exc)


@router.get(
    "/{signal_id}/feedback",
    response_model=DecisionSignalFeedbackItem,
    responses={
        **AUTH_RESPONSE,
        404: {"model": ErrorResponse, "description": "信号不存在"},
        422: {"model": ErrorResponse, "description": "路径参数校验失败"},
        500: {"model": ErrorResponse, "description": "查询失败"},
    },
    summary="查询决策信号用户反馈",
    description="没有反馈时返回 feedback_value=null；信号不存在时返回 404。",
    operation_id="getDecisionSignalFeedback",
)
def get_feedback(signal_id: int) -> DecisionSignalFeedbackItem:
    """获取信号反馈。

    Args:
        signal_id: 信号主键，来自路径参数。

    Returns:
        DecisionSignalFeedbackItem: 反馈值、原因码与备注；未反馈时字段为空。
    """
    service = DecisionSignalOutcomeService()
    try:
        return DecisionSignalFeedbackItem(**service.get_feedback(signal_id))
    except DecisionSignalNotFoundError as exc:
        raise _not_found(exc)
    except Exception as exc:
        raise _internal_error("Get decision signal feedback failed", exc)


@router.put(
    "/{signal_id}/feedback",
    response_model=DecisionSignalFeedbackItem,
    responses={
        **AUTH_RESPONSE,
        400: {"model": ErrorResponse, "description": "请求字段非法"},
        404: {"model": ErrorResponse, "description": "信号不存在"},
        422: {"model": ErrorResponse, "description": "请求体或路径参数校验失败"},
        500: {"model": ErrorResponse, "description": "更新失败"},
    },
    summary="写入决策信号用户反馈",
    description="按 signal_id upsert 最新 useful/not_useful 反馈。",
    operation_id="putDecisionSignalFeedback",
)
def put_feedback(signal_id: int, request: DecisionSignalFeedbackRequest) -> DecisionSignalFeedbackItem:
    """提交信号反馈。

    同一信号重复提交按更新处理，不产生多条记录。

    Args:
        signal_id: 信号主键，来自路径参数。
        request: 反馈请求体。

    Returns:
        DecisionSignalFeedbackItem: 落库后的反馈记录。

    Side Effects:
        写入或更新反馈记录。
    """
    service = DecisionSignalOutcomeService()
    try:
        return DecisionSignalFeedbackItem(
            **service.put_feedback(
                signal_id,
                feedback_value=request.feedback_value,
                reason_code=request.reason_code,
                note=request.note,
                source=request.source,
            )
        )
    except DecisionSignalNotFoundError as exc:
        raise _not_found(exc)
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Put decision signal feedback failed", exc)


@router.patch(
    "/{signal_id}/status",
    response_model=DecisionSignalItem,
    responses={
        **AUTH_RESPONSE,
        400: {"model": ErrorResponse, "description": "状态非法"},
        404: {"model": ErrorResponse, "description": "信号不存在"},
        422: {"model": ErrorResponse, "description": "请求体或路径参数校验失败"},
        500: {"model": ErrorResponse, "description": "更新失败"},
    },
    summary="更新决策信号状态",
    description=(
        "只更新合法状态和可选 metadata；省略 metadata 时保留原值，null 时清空，"
        "object 时按整包替换并保持正式 decision_profile 身份。"
        "expired/invalidated/closed/archived 等 terminal 状态不能直接 PATCH 回 active。"
    ),
    operation_id="updateDecisionSignalStatus",
)
def update_status(signal_id: int, request: DecisionSignalStatusUpdateRequest) -> DecisionSignalItem:
    """更新信号状态。

    Args:
        signal_id: 信号主键，来自路径参数。
        request: 状态更新请求体；metadata 省略保留、null 清空、对象整体替换。

    Returns:
        DecisionSignalItem: 更新后的信号。

    Raises:
        HTTPException: 参数错误 400、不存在 404。

    Side Effects:
        修改信号状态与元数据。
    """
    service = DecisionSignalService()
    try:
        return DecisionSignalItem(
            **service.update_status(
                signal_id,
                status=request.status,
                metadata=request.metadata,
                replace_metadata="metadata" in request.model_fields_set,
            )
        )
    except DecisionSignalNotFoundError as exc:
        raise _not_found(exc)
    except DecisionSignalStorageError as exc:
        raise _internal_error("Update decision signal status failed", exc)
    except ValueError as exc:
        raise _bad_request(exc)
    except Exception as exc:
        raise _internal_error("Update decision signal status failed", exc)
