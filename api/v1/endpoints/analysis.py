# -*- coding: utf-8 -*-
"""
@file: analysis.py
@description: 股票分析端点：同步/异步分析任务、批量提交与重复任务处理、大盘复盘后台任务、任务列表与 SSE 状态流、任务运行流与结果规范化；由 api.v1.router 挂到 /api/v1/analysis。
@author: Lensgcx (GaoCangxiong)

===================================
股票分析接口
===================================

职责：
1. 提供 POST /api/v1/analysis/analyze 触发分析接口
2. 提供 GET /api/v1/analysis/status/{task_id} 查询任务状态接口
3. 提供 GET /api/v1/analysis/tasks 获取任务列表接口
4. 提供 GET /api/v1/analysis/tasks/stream SSE 实时推送接口

特性：
- 异步任务队列：分析任务异步执行，不阻塞请求
- 防重复提交：相同股票代码正在分析时返回 409
- SSE 实时推送：任务状态变化实时通知前端
"""

import asyncio
import copy
import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import JSONResponse, StreamingResponse

from api.deps import get_config_dep, get_history_query_service
from api.v1.errors import api_error
from api.v1.schemas.analysis import (
    AnalyzeRequest,
    AnalysisResultResponse,
    TaskAccepted,
    BatchTaskAcceptedResponse,
    BatchTaskAcceptedItem,
    BatchDuplicateTaskItem,
    TaskStatus,
    TaskInfo,
    TaskListResponse,
    DuplicateTaskErrorResponse,
    MarketReviewRequest,
    MarketReviewAccepted,
)
from api.v1.schemas.common import ErrorResponse
from api.v1.schemas.history import (
    AnalysisReport,
    ReportMeta,
    ReportSummary,
    ReportStrategy,
    ReportDetails,
)
from src.domain.analysis.flow_snapshot import RunFlowSnapshot
from src.application.history import HistoryQueryService
from src.data.stock_index_loader import resolve_index_stock_code
from src.config import Config
from src.application.market.market_review_lock import (
    MarketReviewExecutionLock as _MarketReviewExecutionLock,
    market_review_lock_path,
    release_market_review_lock as _release_market_review_lock,
    try_acquire_market_review_lock as _try_acquire_market_review_lock,
)
from src.application.market.market_review_runtime import (
    build_market_review_runtime as _runtime_build_market_review_runtime,
)
from src.application.analysis.context_pack_overview import (
    extract_analysis_context_pack_overview,
    sanitize_context_snapshot_for_api,
)
from src.application.market.phase_summary import (
    extract_market_phase_summary,
    rebuild_market_phase_summary_for_stock_code,
)
from src.application.quote.stock_code_utils import (
    canonical_stock_code_for_analysis,
    is_code_like,
    normalize_stock_code_for_analysis,
    resolve_index_stock_code_for_analysis,
)
from src.domain.shared.report_language import get_localized_stock_name, normalize_report_language
from src.domain.decision.action import build_action_fields
from src.application.quote.name_to_code_resolver import resolve_name_to_code
from src.application.runtime.task_queue import (
    get_task_queue,
    DuplicateTaskError,
    TaskStatus as TaskStatusEnum,
)
from src.application.runtime.run_diagnostics import build_run_diagnostic_summary
from src.application.runtime.run_flow import build_task_run_flow_snapshot
from src.utils.data_processing import (
    normalize_model_used,
    parse_json_field,
    extract_fundamental_detail_fields,
    extract_board_detail_fields,
    extract_market_structure_detail_field,
    extract_realtime_detail_fields,
)
from src.utils.market_review_region import normalize_market_review_region_lenient

# 模块级日志器，记录任务提交、复盘与报告组装异常。
logger = logging.getLogger(__name__)

# 本模块的 APIRouter；由 api.v1.router 挂到 /api/v1/analysis。
router = APIRouter()

# 允许进入解析器的自由文本字符规则；用于尽早排除乱码与不支持符号。
_SUPPORTED_FREE_TEXT_RE = re.compile(r"^[A-Za-z0-9.*\-+\u3400-\u9fff\s]+$")


def _get_task_trace_id(task: Any) -> Optional[str]:
    """返回任务的链路追踪 ID。

    Args:
        task: 任务对象或任务字典。

    Returns:
        Optional[str]: trace ID；旧任务未记录时为 None。
    """
    trace_id = getattr(task, "trace_id", None)
    if isinstance(trace_id, str) and trace_id.strip():
        return trace_id
    task_id = getattr(task, "task_id", None)
    if isinstance(task_id, str) and task_id.strip():
        return task_id
    return None


def _market_review_lock_path(config: Config) -> Path:
    """返回大盘复盘锁文件路径。

    锁文件用于跨进程互斥，避免多个 worker 同时执行复盘。

    Args:
        config: 运行时配置，决定数据目录位置。

    Returns:
        Path: 复盘锁文件路径。
    """
    return market_review_lock_path(config)


def _build_market_review_runtime(config: Config, source_message: Optional[Any] = None) -> tuple[Any, Any, Any]:
    """构建大盘复盘运行上下文。

    把配置、来源消息与运行时依赖打包，供后台任务在无请求上下文时执行。

    Args:
        config: 运行时配置。
        source_message: 触发来源说明，写入运行上下文便于追溯。

    Returns:
        tuple[Any, Any, Any]: 运行上下文所需的组件三元组。
    """
    return _runtime_build_market_review_runtime(config, source_message)


def _with_request_report_language(config: Config, report_language: Optional[str]) -> Config:
    """Return a request-scoped config copy when the caller overrides report language.

    调用方指定报告语言时返回请求级配置副本，避免修改进程级全局配置影响并发的其他任务。

    Args:
        config: 全局配置。
        report_language: 请求指定的语言；None 表示沿用全局配置。

    Returns:
        Config: 原配置或带语言覆盖的请求级副本。
    """
    normalized = normalize_report_language(report_language, default="")
    if not normalized:
        return config

    scoped_config = copy.copy(config)
    scoped_config.report_language = normalized
    return scoped_config


def _run_market_review_background(
    send_notification: bool,
    effective_region: str,
    lock_token: Optional[_MarketReviewExecutionLock] = None,
    config: Optional[Config] = None,
    query_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Run market review after the API response has been accepted.

    在响应已返回后执行复盘，避免长耗时任务阻塞 HTTP 请求；锁令牌用于释放跨进程互斥。

    Args:
        send_notification: 完成后是否发送通知。
        effective_region: 规范化后的市场范围。
        lock_token: 复盘锁令牌，结束时释放。
        config: 运行时配置。
        query_id: 本次复盘关联的记录 ID。

    Returns:
        Dict[str, Any]: 复盘执行结果，由任务队列保存。

    Side Effects:
        生成报告、可能发送通知，并释放复盘锁。
    """
    from src.application.market.market_review import run_market_review

    runtime_config = config or get_config_dep()
    try:
        notifier, analyzer, search_service = _build_market_review_runtime(runtime_config)
        review_kwargs = {
            "notifier": notifier,
            "analyzer": analyzer,
            "search_service": search_service,
            "config": runtime_config,
            "send_notification": send_notification,
            "override_region": effective_region,
            "return_structured": True,
            "trigger_source": "api",
        }
        if query_id:
            review_kwargs["query_id"] = query_id
        logger.info(
            "[MarketReview] component=market_review action=background_start "
            "trigger_source=api task_id=%s region=%s",
            query_id or "-",
            effective_region,
        )
        report = run_market_review(**review_kwargs)
        if not report:
            raise RuntimeError("大盘复盘未返回可持久化报告")
        if hasattr(report, "report"):
            return {
                "result": report.report,
                "market_review_payload": getattr(report, "market_review_payload", None),
                "region": effective_region,
            }
        return {"result": report, "region": effective_region}
    finally:
        _release_market_review_lock(lock_token)


def _coalesce_text(*values: Any) -> Optional[str]:
    """返回首个非空文本值。

    把 None、空串与纯空白统一视为无值，避免下游拿到空字符串写入报告。

    Args:
        *values: 任意数量的候选值。

    Returns:
        Optional[str]: 首个去空白后非空的字符串；全为空时返回 None。
    """
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _extract_guardrail_reason(raw_result: Any) -> Optional[str]:
    """提取护栏拦截原因。

    从原始结果中识别护栏结构化字段，供状态接口给出可读的拦截说明。

    Args:
        raw_result: 分析结果字典，结构可能随版本变化。

    Returns:
        Optional[str]: 拦截原因；未拦截或无原因时为 None。
    """
    if not isinstance(raw_result, dict):
        return None
    for reason in (
        raw_result.get("guardrail_reason"),
        raw_result.get("downgrade_reason"),
        raw_result.get("decision_score_guardrail_reason"),
    ):
        if reason is not None:
            text = str(reason).strip()
            if text:
                return text
    metadata = raw_result.get("metadata")
    if isinstance(metadata, dict):
        metadata_reason = metadata.get("guardrail_reason") or metadata.get("downgrade_reason")
        if metadata_reason is not None:
            text = str(metadata_reason).strip()
            if text:
                return text
    return None


def _invalid_analysis_input_error() -> HTTPException:
    """构造无效分析入参的错误响应。

    Args:
        无参数。

    Returns:
        HTTPException: 400 错误对象，提示输入无法解析为股票代码。
    """
    return api_error(400, "validation_error", "请输入有效的股票代码或股票名称")


def _is_obviously_invalid_analysis_input(text: str) -> bool:
    """Reject mixed alphanumeric noise and unsupported symbols early.

    在调用解析器与提交任务前拦截明显的乱码与不支持符号，避免把无效输入送进昂贵的解析与队列流程。

    Args:
        text: 用户输入的原始文本。

    Returns:
        bool: 明显无效返回 True。
    """
    if not text or is_code_like(text):
        return False

    if not _SUPPORTED_FREE_TEXT_RE.fullmatch(text):
        return True

    has_letters = any(ch.isalpha() and ch.isascii() for ch in text)
    has_digits = any(ch.isdigit() for ch in text)
    return has_letters and has_digits


def _resolve_and_normalize_input(raw_value: str) -> str:
    """Resolve and normalize a stock input for analysis requests.

    Code-like values keep the existing canonical path.
    Non-code inputs must resolve to a known stock code. Obvious garbage
    input is rejected before expensive resolver and task-queue work.

    形似代码的值走既有规范化路径；中文名、拼音等非代码输入必须能解析到已知股票代码。明显乱码在解析器与任务队列之前就拒绝。

    Args:
        raw_value: 用户输入的股票代码或名称。

    Returns:
        str: 规范化后的股票代码。

    Raises:
        HTTPException: 输入为空、明显无效或无法解析时返回 400。
    """
    text = (raw_value or "").strip()
    if not text:
        return ""

    if is_code_like(text):
        return resolve_index_stock_code_for_analysis(text)

    if text.isdigit() and len(text) == 4:
        resolved_index_code = resolve_index_stock_code_for_analysis(text)
        if resolved_index_code != canonical_stock_code_for_analysis(text):
            return resolved_index_code

    if _is_obviously_invalid_analysis_input(text):
        raise _invalid_analysis_input_error()

    resolved = resolve_name_to_code(text)
    if resolved:
        return canonical_stock_code_for_analysis(resolved)

    raise _invalid_analysis_input_error()


# ============================================================
# POST /analyze - 触发股票分析
# ============================================================

@router.post(
    "/analyze",
    response_model=AnalysisResultResponse,
    responses={
        200: {"description": "分析完成（同步模式）", "model": AnalysisResultResponse},
        202: {
            "description": "分析任务已接受（异步模式）",
            "model": Union[TaskAccepted, BatchTaskAcceptedResponse],
        },
        400: {"description": "请求参数错误", "model": ErrorResponse},
        409: {"description": "股票正在分析中，拒绝重复提交", "model": DuplicateTaskErrorResponse},
        500: {"description": "分析失败", "model": ErrorResponse},
    },
    summary="触发股票分析",
    description="启动 AI 智能分析任务，支持同步和异步模式。异步模式下相同股票代码不允许重复提交。"
)
def trigger_analysis(
        request: AnalyzeRequest,
        config: Config = Depends(get_config_dep),
        history_service: HistoryQueryService = Depends(get_history_query_service),
) -> Union[AnalysisResultResponse, JSONResponse]:
    """触发股票分析

    启动 AI 智能分析任务，支持单只或多只股票批量分析

    流程：
    1. 校验请求参数
    2. 异步模式：检查重复 -> 提交任务队列 -> 返回 202
    3. 同步模式：直接执行分析 -> 返回 200

    Args:
        request: 分析请求参数
        config: 配置依赖
        history_service: 分析历史用例（同步模式回填上下文与基本面快照）

    Returns:
        AnalysisResultResponse: 分析结果（同步模式）
        TaskAccepted | BatchTaskAcceptedResponse: 任务已接受（异步模式，返回 202）

    Raises:
        HTTPException: 400 - 请求参数错误
        HTTPException: 409 - 股票正在分析中
        HTTPException: 500 - 分析失败

    Side Effects:
        异步模式提交后台任务并占用去重槽位；同步模式写入分析历史与报告。
    """
    # 校验请求参数
    stock_codes = []
    if request.stock_code:
        stock_codes.append(request.stock_code)
    if request.stock_codes:
        stock_codes.extend(request.stock_codes)

    if not stock_codes:
        raise api_error(400, "validation_error", "必须提供 stock_code 或 stock_codes 参数")

    # Normalize and de-duplicate inputs while preserving compatibility.
    # 在保持旧入参兼容的前提下统一规范化并去重，避免同一标的被重复提交任务。
    resolved = [_resolve_and_normalize_input(c) for c in stock_codes]
    
    seen = set()
    unique_codes = []
    for code in resolved:
        if not code:
            continue
        # Use normalize_stock_code to ensure '600519' and '600519.SH' are merged
        # 用统一代码规范化把带后缀与不带后缀的写法合并，否则会被当成两只股票各起一个任务。
        norm = normalize_stock_code_for_analysis(code)
        if norm not in seen:
            seen.add(norm)
            unique_codes.append(code)
    
    stock_codes = unique_codes

    # Limit the number of stocks in a single request to prevent DoS
    # 限制单次请求的股票数量，防止一次提交压满任务队列与数据源配额。
    MAX_BATCH_SIZE = 50
    if len(stock_codes) > MAX_BATCH_SIZE:
        raise api_error(400, "validation_error", f"单次分析请求最多支持 {MAX_BATCH_SIZE} 只股票")

    if not stock_codes:
        raise api_error(400, "validation_error", "股票代码不能为空或仅包含空白字符")

    # Sync mode only supports single-stock analysis.
    # 同步模式会阻塞到分析完成，多标的批量请求必须走异步模式。
    if not request.async_mode:
        if len(stock_codes) > 1:
            raise api_error(
                400,
                "validation_error",
                "同步模式仅支持单只股票分析，请使用 async_mode=true 进行批量分析",
            )
        return _handle_sync_analysis(stock_codes[0], request, history_service)

    # Async mode submits one task per stock.
    # 异步模式按标的逐个提交任务，单只重复不影响其余标的入队。
    return _handle_async_analysis_batch(stock_codes, request)


def _handle_async_analysis_batch(
    stock_codes: list,
    request: AnalyzeRequest
) -> JSONResponse:
    """Handle asynchronous analysis requests, including batch submission.

    逐标的检查是否已有进行中任务，通过的提交队列、重复的回传已有 task_id，单只重复不会导致整批失败。

    Args:
        stock_codes: 已规范化并去重的股票代码列表。
        request: 原始分析请求，用于透传报告类型、语言与阶段等参数。

    Returns:
        JSONResponse: 202 响应，体为 BatchTaskAcceptedResponse 或 TaskAccepted。

    Side Effects:
        向任务队列提交若干后台任务。
    """
    task_queue = get_task_queue()
    
    # Preserve metadata for single-stock requests. For batch requests,
    # only carry through metadata that semantically applies to the whole
    # batch, such as import/image source tracking.
    # 单股请求完整保留来源元数据；批量请求只透传语义上属于整批的字段（如导入/图片来源），避免把单股的 stock_name、original_query 错贴到每一只股票上。
    is_single = len(stock_codes) == 1
    preserve_batch_metadata = request.selection_source in {"import", "image"}

    stock_name = request.stock_name if is_single else None
    original_query = request.original_query if (is_single or preserve_batch_metadata) else None
    selection_source = request.selection_source if (is_single or preserve_batch_metadata) else None
    notify = getattr(request, "notify", True)
    skills = getattr(request, "skills", None)
    analysis_phase = request.analysis_phase
    report_language = normalize_report_language(getattr(request, "report_language", None), default="")

    submit_kwargs = dict(
        stock_codes=stock_codes,
        stock_name=stock_name,
        original_query=original_query,
        selection_source=selection_source,
        report_type=request.report_type,
        analysis_phase=analysis_phase,
        force_refresh=request.force_refresh,
        notify=notify,
    )
    if report_language:
        submit_kwargs["report_language"] = report_language
    if skills is not None:
        submit_kwargs["skills"] = skills

    accepted_tasks, duplicate_errors = task_queue.submit_tasks_batch(**submit_kwargs)

    accepted = [
        BatchTaskAcceptedItem(
            task_id=task.task_id,
            trace_id=_get_task_trace_id(task),
            stock_code=task.stock_code,
            status="pending",
            message=f"分析任务已加入队列: {task.stock_code}",
            analysis_phase=task.analysis_phase,
        )
        for task in accepted_tasks
    ]
    duplicates = [
        BatchDuplicateTaskItem(
            stock_code=dup.stock_code,
            existing_task_id=dup.existing_task_id,
            message=str(dup),
        )
        for dup in duplicate_errors
    ]
    
    # 单只股票且被拒绝：保持 409 兼容性
    if len(stock_codes) == 1 and duplicates:
        dup = duplicates[0]
        error_response = DuplicateTaskErrorResponse(
            error="duplicate_task",
            message=dup.message,
            stock_code=dup.stock_code,
            existing_task_id=dup.existing_task_id,
        )
        return JSONResponse(
            status_code=409,
            content=error_response.model_dump()
        )
    
    # 单只股票成功：保持原有响应格式兼容性
    if len(stock_codes) == 1 and accepted:
        task_accepted = TaskAccepted(
            task_id=accepted[0].task_id,
            trace_id=accepted[0].trace_id,
            status="pending",
            message=accepted[0].message,
            analysis_phase=accepted[0].analysis_phase,
        )
        return JSONResponse(
            status_code=202,
            content=task_accepted.model_dump()
        )
    
    # 批量：返回汇总结果
    batch_response = BatchTaskAcceptedResponse(
        accepted=accepted,
        duplicates=duplicates,
        message=f"已提交 {len(accepted)} 个任务，{len(duplicates)} 个重复跳过",
    )
    return JSONResponse(
        status_code=202,
        content=batch_response.model_dump()
    )


def _handle_sync_analysis(
    stock_code: str,
    request: AnalyzeRequest,
    history_service: HistoryQueryService,
) -> AnalysisResultResponse:
    """处理同步分析请求。

    执行完整分析链路并把原始结果组装为公开响应结构；基本面与上下文快照由历史用例按 query_id 回填。

    Args:
        stock_code: 规范化后的股票代码。
        request: 分析请求参数。
        history_service: 分析历史用例，由 Depends 注入。

    Returns:
        AnalysisResultResponse: 报告正文、查询 ID 与诊断摘要。

    Raises:
        HTTPException: 分析失败或报告组装失败。

    Side Effects:
        写入分析历史与报告数据。
    """
    import uuid
    from src.application.analysis.analysis_service import AnalysisService
    
    query_id = uuid.uuid4().hex
    
    try:
        service = AnalysisService()
        result = service.analyze_stock(
            stock_code=stock_code,
            report_type=request.report_type,
            force_refresh=request.force_refresh,
            query_id=query_id,
            send_notification=getattr(request, "notify", True),
            skills=getattr(request, "skills", None),
            analysis_phase=request.analysis_phase,
            report_language=getattr(request, "report_language", None),
        )

        if result is None:
            error_message = service.last_error or f"分析股票 {stock_code} 失败"
            raise api_error(500, "analysis_failed", error_message)

        # 构建报告结构
        report_data = result.get("report", {})
        context_snapshot, fundamental_snapshot, raw_result_snapshot = _load_sync_fundamental_sources(
            query_id=query_id,
            stock_code=result.get("stock_code", stock_code),
            history_service=history_service,
        )
        report = _build_analysis_report(
            report_data,
            query_id,
            stock_code,
            result.get("stock_name"),
            context_snapshot=context_snapshot,
            fallback_fundamental_payload=fundamental_snapshot,
            fallback_raw_result_payload=raw_result_snapshot or result,
        )

        return AnalysisResultResponse(
            query_id=query_id,
            trace_id=result.get("trace_id") or query_id,
            stock_code=result.get("stock_code", stock_code),
            stock_name=result.get("stock_name"),
            report=report.model_dump() if report else None,
            diagnostic_summary=result.get("diagnostic_summary"),
            created_at=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析失败: {e}", exc_info=True)
        raise api_error(500, "internal_error", f"分析过程发生错误: {str(e)}")


# ============================================================
# POST /market-review - 触发大盘复盘
# ============================================================

@router.post(
    "/market-review",
    response_model=MarketReviewAccepted,
    status_code=202,
    responses={
        202: {"description": "大盘复盘任务已接受", "model": MarketReviewAccepted},
        409: {"description": "大盘复盘正在执行", "model": ErrorResponse},
        500: {"description": "提交失败", "model": ErrorResponse},
    },
    summary="触发大盘复盘",
    description="提交一个后台大盘复盘任务，复用 CLI 的大盘复盘运行时装配并保存报告。该人工触发入口不按交易日检查跳过；接口内部仅提供进程内/单机防重，如多实例（多 Worker/多容器）部署，需结合外部幂等机制避免重复触发。",
)
def trigger_market_review(
    request: Optional[MarketReviewRequest] = Body(None),
    config: Config = Depends(get_config_dep),
) -> MarketReviewAccepted:
    """Trigger market review from Web/API without blocking the request.

    先取得跨进程复盘锁再提交后台任务，重复触发返回已有任务 ID 而非再起一个任务。

    Args:
        request: 大盘复盘请求体，region 已严格校验并规范化。
        config: 运行时配置，由 Depends 注入。

    Returns:
        MarketReviewAccepted: 任务接受状态与规范化后的市场范围。

    Raises:
        HTTPException: 区域非法 400、已有复盘进行中 409。

    Side Effects:
        获取复盘锁并提交后台任务。
    """
    request = request or MarketReviewRequest()

    runtime_config = _with_request_report_language(config, request.report_language)
    effective_region = request.region or (
        normalize_market_review_region_lenient(runtime_config.market_review_region) or "cn"
    )

    lock_token = _try_acquire_market_review_lock(runtime_config)
    if lock_token is None:
        raise api_error(409, "duplicate_market_review", "大盘复盘正在执行中，请稍后再试")

    try:
        task_id = uuid.uuid4().hex
        logger.info(
            "[MarketReview] component=market_review action=submit trigger_source=api "
            "task_id=%s region=%s send_notification=%s",
            task_id,
            effective_region,
            request.send_notification,
        )
        task = get_task_queue().submit_background_task(
            lambda: _run_market_review_background(
                request.send_notification,
                effective_region=effective_region,
                lock_token=lock_token,
                config=runtime_config,
                query_id=task_id,
            ),
            stock_code="market_review",
            stock_name="大盘复盘",
            message="大盘复盘任务已提交",
            task_id=task_id,
            region=effective_region,
        )
    except Exception:
        _release_market_review_lock(lock_token)
        raise

    return MarketReviewAccepted(
        status="accepted",
        message="大盘复盘任务已提交，完成后会保存报告并按配置推送通知",
        send_notification=request.send_notification,
        region=effective_region,
        task_id=task.task_id,
        trace_id=_get_task_trace_id(task),
    )


# ============================================================
# GET /tasks - 获取任务列表
# ============================================================

@router.get(
    "/tasks",
    response_model=TaskListResponse,
    responses={
        200: {"description": "任务列表"},
    },
    summary="获取分析任务列表",
    description="获取当前所有分析任务，可按状态筛选"
)
def get_task_list(
    status: Optional[str] = Query(
        None,
        description="筛选状态：pending, processing, completed, failed, cancel_requested, cancelled（支持逗号分隔多个）"
    ),
    limit: int = Query(20, description="返回数量限制", ge=1, le=100),
) -> TaskListResponse:
    """获取分析任务列表。

    Args:
        status: 任务状态过滤；None 表示不限。
        limit: 返回条数上限。

    Returns:
        TaskListResponse: 总数、待处理/执行中计数与任务明细。
    """
    task_queue = get_task_queue()
    
    # 获取所有任务
    all_tasks = task_queue.list_all_tasks(limit=limit)
    
    # 状态筛选
    if status:
        status_list = [s.strip().lower() for s in status.split(",")]
        all_tasks = [t for t in all_tasks if t.status.value in status_list]
    
    # 统计信息
    stats = task_queue.get_task_stats()
    
    # 转换为 Schema
    task_infos = [
        TaskInfo(
            task_id=t.task_id,
            trace_id=_get_task_trace_id(t),
            stock_code=t.stock_code,
            stock_name=t.stock_name,
            status=t.status.value,
            progress=t.progress,
            message=t.message,
            report_type=t.report_type,
            created_at=t.created_at.isoformat(),
            started_at=t.started_at.isoformat() if t.started_at else None,
            completed_at=t.completed_at.isoformat() if t.completed_at else None,
            error=t.error,
            original_query=t.original_query,
            selection_source=t.selection_source,
            analysis_phase=t.analysis_phase,
            skills=getattr(t, "skills", None),
            region=t.region,
        )
        for t in all_tasks
    ]
    
    return TaskListResponse(
        total=stats["total"],
        pending=stats["pending"],
        processing=stats["processing"],
        tasks=task_infos,
    )


# ============================================================
# GET /tasks/stream - SSE 实时推送
# ============================================================

@router.get(
    "/tasks/stream",
    responses={
        200: {"description": "SSE 事件流", "content": {"text/event-stream": {}}},
    },
    summary="任务状态 SSE 流",
    description="通过 Server-Sent Events 实时推送任务状态变化"
)
async def task_stream():
    """SSE 任务状态流

    事件类型：
    - connected: 连接成功
    - task_created: 新任务创建
    - task_started: 任务开始执行
    - task_progress: 任务阶段进度更新
    - task_completed: 任务完成
    - task_failed: 任务失败
    - heartbeat: 心跳（每 30 秒）

    Args:
        无参数。

    Returns:
        StreamingResponse: SSE 事件流

    Side Effects:
        订阅任务队列事件；连接断开时释放订阅，心跳用于穿透代理空闲超时。
    """
    async def event_generator():
        """生成任务状态 SSE 事件流。

        Args:
            无显式参数；捕获外层订阅与请求上下文。

        Returns:
            Iterator[str]: 由 _format_sse_event 格式化的事件文本。

        Side Effects:
            在连接关闭时取消订阅。
        """
        task_queue = get_task_queue()
        event_queue: asyncio.Queue = asyncio.Queue()
        
        # 发送连接成功事件
        yield _format_sse_event("connected", {"message": "Connected to task stream"})
        
        # 发送当前进行中的任务
        pending_tasks = task_queue.list_pending_tasks()
        for task in pending_tasks:
            yield _format_sse_event("task_created", task.to_dict())
        
        # 订阅任务事件
        task_queue.subscribe(event_queue)
        
        try:
            while True:
                try:
                    # 等待事件，超时发送心跳
                    event = await asyncio.wait_for(event_queue.get(), timeout=30)
                    yield _format_sse_event(event["type"], event["data"])
                except asyncio.TimeoutError:
                    # 心跳
                    yield _format_sse_event("heartbeat", {
                        "timestamp": datetime.now().isoformat()
                    })
        except asyncio.CancelledError:
            logger.debug("SSE client disconnected, cancelling event generator")
            raise
        finally:
            task_queue.unsubscribe(event_queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        }
    )


def _format_sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """格式化 SSE 事件。

    Args:
        event_type: 事件类型名。
        data: 可 JSON 序列化的事件载荷。

    Returns:
        str: 含 event 与 data 行、以空行结尾的 SSE 文本块。
    """
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _load_history_run_flow_by_query_id(
    query_id: str,
    *,
    history_service: HistoryQueryService,
    code: Optional[str] = None,
    report_type: Optional[str] = None,
    fail_open: bool = False,
) -> Optional[RunFlowSnapshot]:
    """按查询 ID 加载历史运行流程。

    历史运行流可能缺失；fail_open=True 时静默降级返回 None，不阻断状态查询。

    Args:
        query_id: 分析记录关联 ID。
        history_service: 分析历史用例。
        code: 股票代码，用于缩小回查范围。
        report_type: 报告类型，用于匹配历史记录。
        fail_open: 读取失败时是否降级而不抛错。

    Returns:
        Optional[RunFlowSnapshot]: 运行流快照；无记录或降级时为 None。
    """
    try:
        return history_service.get_run_flow(
            query_id,
            code=code,
            report_type=report_type,
        )
    except Exception as e:
        if fail_open:
            logger.debug(
                "load history run-flow failed, falling back to task skeleton: query_id=%s err=%s",
                query_id,
                e,
            )
            return None
        raise


@router.get(
    "/tasks/{task_id}/flow",
    response_model=RunFlowSnapshot,
    responses={
        200: {"description": "任务运行流快照"},
        404: {"description": "任务不存在", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="获取分析任务运行流",
    description="根据 task_id 查询任务数据流/信息流快照；活跃任务缺少诊断时返回骨架流。",
)
def get_task_run_flow(
    task_id: str,
    history_service: HistoryQueryService = Depends(get_history_query_service),
) -> RunFlowSnapshot:
    """查询分析任务运行流。

    Active tasks are served from the in-memory task queue. Completed tasks try
    to hydrate from persisted history diagnostics using the same task_id/query_id.

    进行中任务直接读内存队列；已完成任务用同一 task_id/query_id 回查历史诊断并补齐运行流。

    Args:
        task_id: 任务 ID，来自路径参数。
        history_service: 分析历史用例，由 Depends 注入。

    Returns:
        RunFlowSnapshot: 任务运行流快照。

    Raises:
        HTTPException: 任务不存在或无可用运行流时返回 404。
    """
    task_queue = get_task_queue()
    task = task_queue.get_task(task_id)

    if task:
        if task.status == TaskStatusEnum.COMPLETED:
            task_report_type = _history_report_type_for_task_flow(
                getattr(task, "report_type", None)
            )
            task_stock_code = _safe_task_flow_text(getattr(task, "stock_code", None), max_length=32)
            if task_report_type == "market_review":
                task_stock_code = "MARKET"
            history_snapshot = _load_history_run_flow_by_query_id(
                task_id,
                history_service=history_service,
                code=task_stock_code,
                report_type=task_report_type,
                fail_open=True,
            )
            if history_snapshot is not None:
                return history_snapshot
        return build_task_run_flow_snapshot(task)

    try:
        history_snapshot = _load_history_run_flow_by_query_id(
            task_id,
            history_service=history_service,
        )
        if history_snapshot is not None:
            return history_snapshot
    except Exception as e:
        logger.error(f"查询任务运行流失败: {e}", exc_info=True)
        raise api_error(500, "internal_error", f"查询任务运行流失败: {str(e)}")

    raise api_error(404, "not_found", f"任务 {task_id} 不存在或已过期")


def _safe_task_flow_text(value: Any, *, max_length: int) -> Optional[str]:
    """安全提取任务流程文本。

    对非字符串值做转换并截断到最大长度，避免异常文案撑爆 SSE 事件。

    Args:
        value: 任意候选值。
        max_length: 允许的最大字符数。

    Returns:
        Optional[str]: 截断后的文本；空值返回 None。
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_length]


def _history_report_type_for_task_flow(value: Any) -> Optional[str]:
    """返回历史记录的报告类型。

    Args:
        value: 历史记录中的报告类型候选值。

    Returns:
        Optional[str]: 受支持的报告类型标识；无法识别时返回 None。
    """
    text = _safe_task_flow_text(value, max_length=64)
    if text is None:
        return None
    normalized = text.lower().strip().replace("-", "_")
    aliases = {
        "detailed": "full",
        "simple": "simple",
        "full": "full",
        "brief": "brief",
        "market": "market_review",
        "market_review": "market_review",
    }
    return aliases.get(normalized, normalized)


def _datetime_to_iso(value: Any) -> Optional[str]:
    """将 datetime 转换为 ISO 字符串。

    Args:
        value: datetime 或其他候选值。

    Returns:
        Optional[str]: ISO 8601 字符串；无法转换时为 None。
    """
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str) and value.strip():
        return value
    return None


def _extract_report_created_at(payload: Dict[str, Any]) -> Optional[str]:
    """提取报告创建时间。

    兼容不同版本报告中 created_at 的字段位置与类型。

    Args:
        payload: 报告或历史记录字典。

    Returns:
        Optional[str]: 规范化后的创建时间字符串。
    """
    report = payload.get("report")
    if not isinstance(report, dict):
        return None

    meta = report.get("meta")
    if not isinstance(meta, dict):
        return None

    return _datetime_to_iso(meta.get("created_at"))


def _display_stock_code_from_index(stock_code: Any) -> str:
    """从股票索引提取展示代码。

    Args:
        stock_code: 内部规范股票代码。

    Returns:
        str: 适合前端展示的代码；索引无对应项时回退原代码。
    """
    code = str(stock_code or "").strip()
    if not code:
        return code
    return resolve_index_stock_code(code) or code


def _display_market_phase_summary(stock_code: Any, context_snapshot: Any) -> Any:
    """返回展示用大盘阶段摘要。

    只取低敏字段，避免把完整上下文快照下发到状态接口。

    Args:
        stock_code: 股票代码，用于确定市场。
        context_snapshot: 分析上下文快照；可为 None。

    Returns:
        Any: 可公开的阶段摘要；不可得时为 None。
    """
    return rebuild_market_phase_summary_for_stock_code(
        _display_stock_code_from_index(stock_code),
        context_snapshot,
    )


def _prepare_report_for_task_enrichment(
    report_data: Dict[str, Any],
    created_at: Optional[str],
) -> Dict[str, Any]:
    """为任务富化处理准备报告数据。

    补齐创建时间并把报告归一为可安全改写的字典，避免修改任务队列中的原始对象。

    Args:
        report_data: 任务结果中的报告数据。
        created_at: 回退使用的创建时间。

    Returns:
        Dict[str, Any]: 富化处理用的报告字典副本。
    """
    enriched_report = dict(report_data)
    meta = dict(enriched_report.get("meta") or {})
    if created_at and not _datetime_to_iso(meta.get("created_at")):
        meta["created_at"] = created_at
    enriched_report["meta"] = meta
    return enriched_report


def _first_non_empty_report_value(*values: Any) -> Any:
    """返回报告中首个非空取值。

    Args:
        *values: 按优先级排列的候选值。

    Returns:
        Any: 首个非 None、非空串的值；全为空时返回 None。
    """
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _ensure_report_action_fields(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """确保报告含完整决策动作字段。

    旧版报告只有 operation_advice，需要据此补齐 action 与 action_label，避免前端对历史任务显示空白动作。

    Args:
        report_data: 报告字典。

    Returns:
        Dict[str, Any]: 补齐动作字段后的报告字典。

    Side Effects:
        原地修改传入的报告字典。
    """
    enriched_report = dict(report_data)
    meta = dict(enriched_report.get("meta") or {})
    summary = dict(enriched_report.get("summary") or {})
    details = enriched_report.get("details") if isinstance(enriched_report.get("details"), dict) else {}
    raw_result = details.get("raw_result") if isinstance(details.get("raw_result"), dict) else {}
    report_language = normalize_report_language(
        meta.get("report_language") or raw_result.get("report_language")
    )
    action_fields = build_action_fields(
        operation_advice=raw_result.get("operation_advice") or summary.get("operation_advice"),
        explicit_action=raw_result.get("action") or summary.get("action"),
        report_type=meta.get("report_type"),
        report_language=report_language,
        sentiment_score=_first_non_empty_report_value(
            summary.get("sentiment_score"),
            raw_result.get("sentiment_score"),
        ),
        guardrail_reason=_extract_guardrail_reason(raw_result),
        align_with_score=True,
    )
    summary["action"] = action_fields["action"]
    summary["action_label"] = action_fields["action_label"]
    enriched_report["summary"] = summary
    return enriched_report


def _build_task_analysis_result(
    task: Any,
    *,
    history_service: HistoryQueryService,
) -> AnalysisResultResponse:
    """Normalize an in-memory completed task result to the public API contract.

    Older AnalysisService payloads contain stock_code/stock_name/report only.
    The status endpoint owns the task metadata, so it can supply the missing
    response fields without waiting for the database fallback path.

    把内存中的已完成任务结果规范化为公开响应：旧版载荷只有代码、名称与报告，缺失的元数据由状态端点持有的任务信息补齐，无需等数据库回退路径。

    Args:
        task: 内存中的任务对象。
        history_service: 分析历史用例，用于可选的历史回查。

    Returns:
        AnalysisResultResponse: 符合公开契约的分析结果。
    """
    payload = dict(task.result)
    if not payload.get("query_id"):
        payload["query_id"] = task.task_id
    if not payload.get("trace_id"):
        payload["trace_id"] = _get_task_trace_id(task) or task.task_id
    if not payload.get("stock_code"):
        payload["stock_code"] = task.stock_code
    display_stock_code = _display_stock_code_from_index(payload.get("stock_code"))
    if display_stock_code:
        payload["stock_code"] = display_stock_code

    if not payload.get("stock_name") and getattr(task, "stock_name", None):
        payload["stock_name"] = task.stock_name

    if not payload.get("created_at"):
        payload["created_at"] = (
            _extract_report_created_at(payload)
            or _datetime_to_iso(getattr(task, "created_at", None))
            or _datetime_to_iso(getattr(task, "completed_at", None))
            or datetime.now().isoformat()
        )

    report_data = payload.get("report")
    stock_code = payload.get("stock_code")
    query_id = payload.get("query_id")
    report_enriched = False

    if isinstance(report_data, dict) and stock_code and query_id:
        context_snapshot, fundamental_snapshot, raw_result_snapshot = _load_sync_fundamental_sources(
            query_id=query_id,
            stock_code=stock_code,
            history_service=history_service,
        )
        report_task_details = report_data.get("details")
        report_task_raw_result = (
            report_task_details.get("raw_result")
            if isinstance(report_task_details, dict)
            else None
        )
        should_rebuild_report = (
            context_snapshot is not None
            or fundamental_snapshot is not None
            or raw_result_snapshot is not None
            or report_task_raw_result is not None
        )
        if should_rebuild_report:
            try:
                report = _build_analysis_report(
                    _prepare_report_for_task_enrichment(
                        report_data,
                        payload.get("created_at"),
                    ),
                    query_id,
                    stock_code,
                    payload.get("stock_name") or getattr(task, "stock_name", None),
                    context_snapshot=context_snapshot,
                    fallback_fundamental_payload=fundamental_snapshot,
                    fallback_raw_result_payload=raw_result_snapshot or payload,
                )
                payload["report"] = report.model_dump()
                report_enriched = True
            except Exception as e:
                logger.debug(
                    "enrich in-memory task report failed (fail-open): task_id=%s err=%s",
                    getattr(task, "task_id", None),
                    e,
                )

    if not report_enriched and isinstance(report_data, dict):
        meta = report_data.get("meta")
        if isinstance(meta, dict) and display_stock_code:
            raw_meta_code = meta.get("stock_code") or getattr(task, "stock_code", None)
            meta["stock_code"] = display_stock_code
            meta["market_phase_summary"] = _display_market_phase_summary(
                raw_meta_code,
                {"market_phase_summary": meta.get("market_phase_summary")},
            )
        payload["report"] = _ensure_report_action_fields(report_data)

    return AnalysisResultResponse.model_validate(payload)


# ============================================================
# GET /status/{task_id} - 查询单个任务状态
# ============================================================

@router.get(
    "/status/{task_id}",
    response_model=TaskStatus,
    responses={
        200: {"description": "任务状态"},
        404: {"description": "任务不存在", "model": ErrorResponse},
    },
    summary="查询分析任务状态",
    description="根据 task_id 查询单个任务的状态"
)
def get_analysis_status(
    task_id: str,
    history_service: HistoryQueryService = Depends(get_history_query_service),
) -> TaskStatus:
    """查询分析任务状态。

    进行中任务读内存队列；已完成任务优先用内存结果，必要时回查历史记录补齐报告字段。

    Args:
        task_id: 任务 ID，来自路径参数。
        history_service: 分析历史用例，由 Depends 注入。

    Returns:
        TaskStatus: 状态、进度、结果与诊断信息。

    Raises:
        HTTPException: 任务不存在或已过期时返回 404。
    """
    # 1. 先从任务队列查询
    task_queue = get_task_queue()
    task = task_queue.get_task(task_id)
    
    if task:
        result: Optional[AnalysisResultResponse] = None
        market_review_report = None
        market_review_payload = None

        if task.status == TaskStatusEnum.COMPLETED and isinstance(task.result, dict):
            if task.stock_code == "market_review":
                report_text = task.result.get("result")
                if isinstance(report_text, str) and report_text.strip():
                    market_review_report = report_text
                payload = task.result.get("market_review_payload")
                if isinstance(payload, dict):
                    market_review_payload = payload
            else:
                try:
                    result = _build_task_analysis_result(task, history_service=history_service)
                except Exception:
                    logger.warning(
                        "解析任务结果失败，回退为空返回: task_id=%s",
                        task.task_id,
                    )

        return TaskStatus(
            task_id=task.task_id,
            trace_id=_get_task_trace_id(task),
            status=task.status.value,
            progress=task.progress,
            result=result,
            market_review_report=market_review_report,
            market_review_payload=market_review_payload,
            region=task.region,
            error=task.error,
            stock_name=task.stock_name,
            original_query=task.original_query,
            selection_source=task.selection_source,
            analysis_phase=task.analysis_phase,
            skills=getattr(task, "skills", None),
        )
    
    # 2. 从数据库查询已完成的记录
    try:
        record = history_service.get_latest_by_query_id(task_id)

        if record:
            raw_result = parse_json_field(record.raw_result)
            if getattr(record, "report_type", None) == "market_review":
                market_review_report = None
                context_snapshot = parse_json_field(getattr(record, "context_snapshot", None))
                market_review_payload = None
                region = None
                if isinstance(context_snapshot, dict):
                    raw_region = context_snapshot.get("market_review_region")
                    if isinstance(raw_region, str) and raw_region.strip():
                        region = raw_region.strip()
                    payload = context_snapshot.get("market_review_payload")
                    if isinstance(payload, dict):
                        market_review_payload = payload
                        if region is None:
                            payload_region = payload.get("region")
                            if isinstance(payload_region, str) and payload_region.strip():
                                region = payload_region.strip()
                if isinstance(raw_result, dict):
                    report_text = raw_result.get("raw_response") or raw_result.get("market_review_report")
                    if isinstance(report_text, str) and report_text.strip():
                        market_review_report = report_text
                if not market_review_report and record.news_content:
                    market_review_report = record.news_content

                return TaskStatus(
                    task_id=task_id,
                    trace_id=task_id,
                    status="completed",
                    progress=100,
                    result=None,
                    market_review_report=market_review_report,
                    market_review_payload=market_review_payload,
                    region=region,
                    error=None,
                    stock_name=record.name,
                )

            model_used = normalize_model_used(
                (raw_result or {}).get("model_used") if isinstance(raw_result, dict) else None
            )
            report_language = normalize_report_language(
                (raw_result or {}).get("report_language") if isinstance(raw_result, dict) else None
            )
            stock_name = get_localized_stock_name(record.name, record.code, report_language)
            display_stock_code = _display_stock_code_from_index(record.code)

            # Extract current_price / change_pct from context_snapshot
            skills = None
            context_snapshot = parse_json_field(getattr(record, 'context_snapshot', None))
            analysis_context_pack_overview = extract_analysis_context_pack_overview(context_snapshot)
            market_phase_summary = _display_market_phase_summary(record.code, context_snapshot)
            api_context_snapshot = sanitize_context_snapshot_for_api(context_snapshot)
            if context_snapshot and isinstance(context_snapshot, dict):
                raw_skills = context_snapshot.get("skills")
                if isinstance(raw_skills, list):
                    skills = [str(skill) for skill in raw_skills]
            realtime_fields = extract_realtime_detail_fields(context_snapshot)
            current_price = realtime_fields.get("current_price")
            change_pct = realtime_fields.get("change_pct")
            fallback_fundamental = history_service.get_latest_fundamental_snapshot(
                query_id=task_id,
                code=record.code,
            )
            extracted_fundamental = extract_fundamental_detail_fields(
                context_snapshot=context_snapshot,
                fallback_fundamental_payload=fallback_fundamental,
            )
            extracted_boards = extract_board_detail_fields(
                context_snapshot=context_snapshot,
                fallback_fundamental_payload=fallback_fundamental,
            )
            market_structure = extract_market_structure_detail_field(
                context_snapshot,
                raw_result,
            )
            has_board_details = (
                bool(extracted_boards.get("belong_boards"))
                or extracted_boards.get("sector_rankings") is not None
                or extracted_boards.get("concept_rankings") is not None
            )
            details = None
            if (
                any(extracted_fundamental.values())
                or has_board_details
                or market_structure is not None
                or context_snapshot is not None
                or analysis_context_pack_overview is not None
            ):
                details = ReportDetails(
                    news_content=getattr(record, "news_content", None),
                    raw_result=raw_result,
                    context_snapshot=api_context_snapshot,
                    analysis_context_pack_overview=analysis_context_pack_overview,
                    financial_report=extracted_fundamental.get("financial_report"),
                    dividend_metrics=extracted_fundamental.get("dividend_metrics"),
                    belong_boards=extracted_boards.get("belong_boards"),
                    sector_rankings=extracted_boards.get("sector_rankings"),
                    concept_rankings=extracted_boards.get("concept_rankings"),
                    market_structure=market_structure,
                )

            raw_dict = raw_result if isinstance(raw_result, dict) else {}
            action_fields = build_action_fields(
                operation_advice=raw_dict.get("operation_advice") or record.operation_advice,
                explicit_action=raw_dict.get("action"),
                report_type=getattr(record, 'report_type', None),
                report_language=report_language,
                sentiment_score=record.sentiment_score if record.sentiment_score is not None else raw_dict.get("sentiment_score"),
                guardrail_reason=_extract_guardrail_reason(raw_dict),
                align_with_score=True,
            )

            # Build report from DB record so completed tasks return real data
            report_dict = AnalysisReport(
                meta=ReportMeta(
                    id=record.id,
                    query_id=task_id,
                    stock_code=display_stock_code,
                    stock_name=stock_name,
                    report_type=getattr(record, 'report_type', None),
                    report_language=report_language,
                    created_at=record.created_at.isoformat() if record.created_at else None,
                    model_used=model_used,
                    current_price=current_price,
                    change_pct=change_pct,
                    market_phase_summary=market_phase_summary,
                ),
                summary=ReportSummary(
                    sentiment_score=record.sentiment_score,
                    operation_advice=record.operation_advice,
                    action=action_fields["action"],
                    action_label=action_fields["action_label"],
                    trend_prediction=record.trend_prediction,
                    analysis_summary=record.analysis_summary,
                ),
                strategy=ReportStrategy(
                    ideal_buy=_stringify_report_strategy_value(getattr(record, 'ideal_buy', None)),
                    secondary_buy=_stringify_report_strategy_value(getattr(record, 'secondary_buy', None)),
                    stop_loss=_stringify_report_strategy_value(getattr(record, 'stop_loss', None)),
                    take_profit=_stringify_report_strategy_value(getattr(record, 'take_profit', None)),
                ),
                details=details,
            ).model_dump()
            return TaskStatus(
                task_id=task_id,
                trace_id=task_id,
                status="completed",
                progress=100,
                result=AnalysisResultResponse(
                    query_id=task_id,
                    trace_id=task_id,
                    stock_code=display_stock_code,
                    stock_name=stock_name,
                    report=report_dict,
                    diagnostic_summary=build_run_diagnostic_summary(
                        context_snapshot=context_snapshot,
                        raw_result=raw_result,
                        report_saved=True,
                        query_id=task_id,
                        stock_code=display_stock_code,
                    ),
                    created_at=record.created_at.isoformat() if record.created_at else datetime.now().isoformat()
                ),
                error=None,
                skills=skills,
            )

    except Exception as e:
        logger.error(f"查询任务状态失败: {e}", exc_info=True)
        raise api_error(500, "internal_error", f"查询任务状态失败: {str(e)}")

    # 3. 任务不存在
    raise api_error(404, "not_found", f"任务 {task_id} 不存在或已过期")


# ============================================================
# 辅助函数
# ============================================================

def _load_sync_fundamental_sources(
    query_id: str,
    stock_code: str,
    *,
    history_service: HistoryQueryService,
) -> tuple[Optional[Any], Optional[Dict[str, Any]], Optional[Any]]:
    """Load report enrichment payloads for sync analyze response.

    为同步分析响应加载基本面快照与原始结果载荷，找不到时逐项返回 None 而不中断响应。

    Args:
        query_id: 分析记录关联 ID。
        stock_code: 股票代码。
        history_service: 分析历史用例。

    Returns:
        tuple[Optional[Any], Optional[Dict[str, Any]], Optional[Any]]: 上下文快照、基本面载荷与原始结果载荷。
    """
    try:
        latest_record = history_service.get_latest_by_query_id(query_id, code=stock_code)
        context_snapshot = None
        raw_result_snapshot = None
        if latest_record is not None:
            context_snapshot = parse_json_field(getattr(latest_record, "context_snapshot", None))
            raw_result_snapshot = parse_json_field(getattr(latest_record, "raw_result", None))

        fallback_fundamental = history_service.get_latest_fundamental_snapshot(
            query_id=query_id,
            code=stock_code,
        )
        return context_snapshot, fallback_fundamental, raw_result_snapshot
    except Exception as e:
        logger.debug(
            "load sync fundamental sources failed (fail-open): query_id=%s stock_code=%s err=%s",
            query_id,
            stock_code,
            e,
        )
        return None, None, None


def _stringify_report_strategy_value(value: Any) -> Optional[str]:
    """将报告策略值转换为字符串。

    保留区间、单位与「--」等原始表达，无法转换时返回 None。

    Args:
        value: 策略字段的任意值。

    Returns:
        Optional[str]: 可直接展示的字符串。
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _build_analysis_report(
        report_data: Dict[str, Any],
        query_id: str,
        stock_code: str,
        stock_name: Optional[str] = None,
        context_snapshot: Optional[Any] = None,
        fallback_fundamental_payload: Optional[Dict[str, Any]] = None,
        fallback_raw_result_payload: Optional[Any] = None,
) -> AnalysisReport:
    """构建符合 API 规范的分析报告

    Args:
        report_data: 原始报告数据
        query_id: 查询 ID
        stock_code: 股票代码
        stock_name: 股票名称
        context_snapshot: 上下文快照（可选）
        fallback_fundamental_payload: 基本面快照 payload（可选）
        fallback_raw_result_payload: 原始分析结果 payload（可选）

    Returns:
        AnalysisReport: 结构化的分析报告

    Side Effects:
        无；基于回退载荷补齐详情区，但不修改持久化记录。
    """
    meta_data = report_data.get("meta", {})
    summary_data = report_data.get("summary", {})
    strategy_data = report_data.get("strategy", {})
    details_data = report_data.get("details", {})
    report_language = normalize_report_language(
        meta_data.get("report_language")
        or (context_snapshot or {}).get("report_language")
        or getattr(Config.get_instance(), "report_language", "zh")
    )
    display_stock_code = _display_stock_code_from_index(meta_data.get("stock_code", stock_code))
    localized_stock_name = get_localized_stock_name(
        meta_data.get("stock_name", stock_name),
        display_stock_code,
        report_language,
    )
    realtime_fields = extract_realtime_detail_fields(context_snapshot)
    current_price = meta_data.get("current_price")
    if current_price is None:
        current_price = realtime_fields.get("current_price")
    change_pct = meta_data.get("change_pct")
    if change_pct is None:
        change_pct = realtime_fields.get("change_pct")
    raw_stock_code = meta_data.get("stock_code", stock_code)
    market_phase_summary = _display_market_phase_summary(raw_stock_code, context_snapshot)
    if market_phase_summary is None:
        meta_phase_summary = meta_data.get("market_phase_summary")
        if meta_phase_summary is not None:
            market_phase_summary = _display_market_phase_summary(
                raw_stock_code,
                {"market_phase_summary": meta_phase_summary},
            )

    meta = ReportMeta(
        query_id=meta_data.get("query_id", query_id),
        stock_code=display_stock_code,
        stock_name=localized_stock_name,
        report_type=meta_data.get("report_type", "detailed"),
        report_language=report_language,
        created_at=meta_data.get("created_at", datetime.now().isoformat()),
        current_price=current_price,
        change_pct=change_pct,
        model_used=normalize_model_used(meta_data.get("model_used")),
        market_phase_summary=market_phase_summary,
    )

    def _looks_like_raw_result_payload(candidate: Any) -> bool:
        """判断载荷是否形似原始结果数据。

        用于在多个回退来源中区分「原始分析结果」与「上下文快照」，避免填错详情字段。

        Args:
            candidate: 待判定的字典或任意值。

        Returns:
            bool: 含原始结果特征字段时返回 True。
        """
        return (
            isinstance(candidate, dict)
            and (
                "analysis_summary" in candidate
                or "operation_advice" in candidate
                or "trend_prediction" in candidate
                or "sentiment_score" in candidate
                or "market_structure_context" in candidate
                or "model_used" in candidate
                or "dashboard" in candidate
                or "action" in candidate
            )
        )

    raw_result_data = details_data.get("raw_result")
    if not isinstance(raw_result_data, dict):
        raw_result_data = {}
        if isinstance(fallback_raw_result_payload, dict):
            if isinstance(fallback_raw_result_payload.get("raw_result"), dict):
                raw_result_data = fallback_raw_result_payload["raw_result"]
            elif _looks_like_raw_result_payload(fallback_raw_result_payload):
                raw_result_data = fallback_raw_result_payload
        if not raw_result_data and isinstance(details_data, dict):
            raw_result_data = details_data
    action_fields = build_action_fields(
        operation_advice=(
            raw_result_data.get("operation_advice")
            or details_data.get("operation_advice")
            or summary_data.get("operation_advice")
        ),
        explicit_action=raw_result_data.get("action") or details_data.get("action") or summary_data.get("action"),
        report_type=meta.report_type,
        report_language=report_language,
        sentiment_score=_first_non_empty_report_value(
            summary_data.get("sentiment_score"),
            raw_result_data.get("sentiment_score"),
            details_data.get("sentiment_score"),
        ),
        guardrail_reason=_extract_guardrail_reason(raw_result_data),
        align_with_score=True,
    )

    summary = ReportSummary(
        analysis_summary=summary_data.get("analysis_summary"),
        operation_advice=summary_data.get("operation_advice"),
        action=action_fields["action"],
        action_label=action_fields["action_label"],
        trend_prediction=summary_data.get("trend_prediction"),
        sentiment_score=summary_data.get("sentiment_score"),
        sentiment_label=summary_data.get("sentiment_label")
    )

    strategy = None
    if strategy_data:
        strategy = ReportStrategy(
            ideal_buy=_stringify_report_strategy_value(strategy_data.get("ideal_buy")),
            secondary_buy=_stringify_report_strategy_value(strategy_data.get("secondary_buy")),
            stop_loss=_stringify_report_strategy_value(strategy_data.get("stop_loss")),
            take_profit=_stringify_report_strategy_value(strategy_data.get("take_profit"))
        )

    extracted_fundamental = extract_fundamental_detail_fields(
        context_snapshot=context_snapshot,
        fallback_fundamental_payload=fallback_fundamental_payload,
    )
    extracted_boards = extract_board_detail_fields(
        context_snapshot=context_snapshot,
        fallback_fundamental_payload=fallback_fundamental_payload,
    )
    market_structure = None
    for raw_candidate in (fallback_raw_result_payload, raw_result_data, details_data):
        if raw_candidate is None:
            continue
        market_structure = extract_market_structure_detail_field(
            context_snapshot,
            raw_candidate,
        )
        if market_structure is not None:
            break
    analysis_context_pack_overview = extract_analysis_context_pack_overview(context_snapshot)
    api_context_snapshot = sanitize_context_snapshot_for_api(context_snapshot)
    details = None
    has_board_details = (
        bool(extracted_boards.get("belong_boards"))
        or extracted_boards.get("sector_rankings") is not None
        or extracted_boards.get("concept_rankings") is not None
    )
    if (
        details_data
        or any(extracted_fundamental.values())
        or has_board_details
        or market_structure is not None
        or context_snapshot is not None
        or analysis_context_pack_overview is not None
    ):
        details = ReportDetails(
            news_content=details_data.get("news_summary") or details_data.get("news_content"),
            raw_result=raw_result_data,
            context_snapshot=api_context_snapshot,
            analysis_context_pack_overview=analysis_context_pack_overview,
            financial_report=extracted_fundamental.get("financial_report"),
            dividend_metrics=extracted_fundamental.get("dividend_metrics"),
            belong_boards=extracted_boards.get("belong_boards"),
            sector_rankings=extracted_boards.get("sector_rankings"),
            concept_rankings=extracted_boards.get("concept_rankings"),
            market_structure=market_structure,
        )

    return AnalysisReport(
        meta=meta,
        summary=summary,
        strategy=strategy,
        details=details
    )
