# -*- coding: utf-8 -*-
"""
@file: scanner.py
@description: 技术信号扫描器端点：扫描选项契约、异步扫描任务提交、进度轮询（含增量结果）与协作式取消；由 api.v1.router 挂到 /api/v1/scanner，扫描逻辑在 src.application.decision.signal_scanner_service。
@author: Lensgcx (GaoCangxiong)

技术信号扫描器（Scanner）API 路由。

- GET  /scanner/options              扫描选项契约（池来源 / 榜单字段 / TopN / 信号键）
- POST /scanner/tasks                提交扫描任务 -> 202 + task_id（异步）
- GET  /scanner/tasks/{id}           轮询进度与结果（未完成时也返回已命中的增量结果）
- POST /scanner/tasks/{id}/cancel    请求取消扫描（协作式，保留已命中部分结果）
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.application.decision import signal_scanner_service as scanner_service
from src.application.runtime.task_queue import TaskStatus as QueueTaskStatus
from src.application.runtime.task_queue import get_task_queue

# 本模块的 APIRouter；由 api.v1.router 挂到 /api/v1/scanner。
router = APIRouter()

# 任务类型标记：与 eod-picker 同构，用于任务归属校验
# 任务类型标记，用于轮询/取消时校验任务归属，避免误操作其他业务的任务。
TASK_REPORT_TYPE = "signal_scanner"


class ScannerWatchlistItem(BaseModel):
    """自选股池条目：前端传入（自选条目自带名称，后端无需再取行情补名）。

    @author: Lensgcx (GaoCangxiong)
    """

    # 股票代码，支持 600519 与带后缀的 600519.SH 两种写法。
    code: str = Field(..., description="股票代码，支持 600519 / 600519.SH")
    # 股票名称；可为空，命中时回退到 K 线数据源给出的名称。
    name: str = Field("", description="股票名称（可为空，命中时回退 K 线源名称）")


class ScannerStartRequest(BaseModel):
    """提交扫描任务的请求体；非法取值由服务端回落到默认值。

    @author: Lensgcx (GaoCangxiong)
    """

    # 股票池来源 watchlist / ranking / limit_up，默认 watchlist。
    pool_source: str = Field("watchlist", description="watchlist / ranking / limit_up")
    # 榜单排序字段 amount / change_percent / turnover_rate，默认 amount。
    ranking_field: str = Field("amount", description="amount / change_percent / turnover_rate")
    # 从榜单或涨停池取前 N 只，范围 1~300，默认 20。
    top_n: int = Field(20, ge=1, le=300, description="榜单 / 涨停池取前 N 只")
    # 待扫描的信号键列表，默认 ma_golden（均线金叉）。
    signals: List[str] = Field(default_factory=lambda: ["ma_golden"], description="信号键列表")
    # 自选股池条目；pool_source=watchlist 时必填。
    watchlist: Optional[List[ScannerWatchlistItem]] = Field(
        None, description="自选股池（pool_source=watchlist 时必填）"
    )


class ScannerAccepted(BaseModel):
    """扫描任务已受理响应体。

    @author: Lensgcx (GaoCangxiong)
    """
    # 任务 ID，供轮询与取消使用。
    task_id: str
    # 提交时的状态，固定 pending。
    status: str = "pending"
    # 面向用户的提交提示。
    message: str


class ScannerResultRow(BaseModel):
    """单条命中结果。

    @author: Lensgcx (GaoCangxiong)
    """

    # 命中信号的股票代码。
    code: str
    # 股票名称；未取到时为空字符串。
    name: str = ""
    # 该股票命中的信号键列表，默认空列表。
    signals: List[str] = Field(default_factory=list)
    # 扫描完成时间字符串，默认空字符串。
    scanned_at: str = ""


class ScannerStepStock(BaseModel):
    """步骤快照中的单只股票（仅展示用，含代码与名称）。

    @author: Lensgcx (GaoCangxiong)
    """

    # 步骤快照中的股票代码。
    code: str
    # 步骤快照中的股票名称，未取到时为空字符串。
    name: str = ""


class ScannerStep(BaseModel):
    """扫描分步快照：全量下发、前端整体替换。

    - key: 步骤标识（pool=解析股票池 / signal=技术信号扫描），前端据此映射本地化标题
    - status: running / done
    - total: 该步真实股票数量（stocks 可能截断）
    - stocks: 该步过滤出的股票（上限见服务层 STEP_STOCK_LIMIT）

    @author: Lensgcx (GaoCangxiong)
    """

    # 步骤标识：pool 解析股票池 / signal 技术信号扫描，前端据此映射本地化标题。
    key: str
    # 步骤状态 running / done，默认 running。
    status: str = "running"
    # 该步真实股票数量；stocks 可能被服务层截断，故此值可能更大。
    total: int = 0
    # 该步过滤出的股票展示列表，上限由服务层 STEP_STOCK_LIMIT 决定。
    stocks: List[ScannerStepStock] = Field(default_factory=list)


class ScannerTaskStatus(BaseModel):
    """任务状态：拍平结果字段，运行中也能拿到增量结果。

    @author: Lensgcx (GaoCangxiong)
    """

    # 被轮询的任务 ID。
    task_id: str
    # 任务状态字符串。
    status: str
    # 执行进度百分比，默认 0。
    progress: int = 0
    # 当前阶段说明；可为空。
    message: Optional[str] = None
    # 失败原因；仅失败态有值。
    error: Optional[str] = None
    # 本次扫描的股票池总数，默认 0。
    pool_count: int = 0
    # 已扫描的股票数，运行中会持续增长。
    scanned: int = 0
    # 已命中的股票数，运行中会持续增长。
    match_count: int = 0
    # 当前已命中的结果列表，默认空列表。
    results: List[ScannerResultRow] = Field(default_factory=list)
    # 分步快照列表，前端整体替换而非增量合并。
    steps: List[ScannerStep] = Field(default_factory=list)
    # 是否已取消，默认 False。
    cancelled: bool = False
    # 是否已结束，默认 False；部分结果也可能标记为已结束。
    finished: bool = False


class ScannerCancelResult(BaseModel):
    """扫描任务取消结果响应体。

    @author: Lensgcx (GaoCangxiong)
    """
    # 被请求取消的任务 ID。
    task_id: str
    # 取消请求是否被受理；任务已结束时为 False。
    cancelled: bool
    # 取消结果的说明文案。
    message: str


@router.get("/options")
def scanner_options() -> Dict[str, Any]:
    """返回前端渲染所需的选项契约（避免前端写死池来源与信号键）。

    Args:
        无参数。

    Returns:
        Dict[str, Any]: 池来源、榜单字段、TopN 范围与可用信号键。

    Side Effects:
        无。
    """
    return scanner_service.get_scanner_options()


@router.post("/tasks", status_code=202, response_model=ScannerAccepted)
def scanner_start(request: ScannerStartRequest) -> ScannerAccepted:
    """提交一次信号扫描任务，立即返回 task_id，前端轮询 /tasks/{id}。

    请求先在服务层归一化（非法值回落默认），再注册任务运行态；后台任务在 finally 中释放运行态，避免取消或异常导致状态泄漏。

    Args:
        request: 扫描参数；pool_source=watchlist 时须提供 watchlist。

    Returns:
        ScannerAccepted: task_id、初始状态与提示文案（HTTP 202）。

    Side Effects:
        注册扫描运行态并向全局任务队列提交后台任务。
    """
    task_id = uuid.uuid4().hex
    task_queue = get_task_queue()
    payload = scanner_service.normalize_request(request.model_dump())
    scanner_service.register_run(task_id)

    def run() -> Dict[str, Any]:
        """后台执行信号扫描任务。

        收到取消请求时返回「部分结果」而非抛异常，保证已命中的标的仍可展示；无论正常结束还是取消都释放运行态。

        Args:
            无显式参数；捕获外层 payload、task_id 与 task_queue。

        Returns:
            Dict[str, Any]: 完整结果或 build_cancelled_result 生成的部分结果。

        Side Effects:
            更新任务进度，并在 finally 中释放扫描运行态。
        """
        try:
            return scanner_service.run_signal_scan(
                payload,
                task_id=task_id,
                update_progress=lambda p, m: task_queue.update_task_progress(task_id, p, m),
            )
        except scanner_service.ScanCancelled:
            return scanner_service.build_cancelled_result(payload, task_id)
        finally:
            scanner_service.release_run(task_id)

    task_queue.submit_background_task(
        run,
        stock_code=TASK_REPORT_TYPE,
        stock_name="技术信号扫描",
        report_type=TASK_REPORT_TYPE,
        message="技术信号扫描任务已提交",
        task_id=task_id,
        trace_id=task_id,
    )
    return ScannerAccepted(
        task_id=task_id,
        status="pending",
        message="技术信号扫描任务已提交",
    )


@router.get("/tasks/{task_id}", response_model=ScannerTaskStatus)
def scanner_task_status(task_id: str) -> ScannerTaskStatus:
    """轮询扫描任务状态；运行中返回增量结果，完成时返回完整结果。

    优先使用队列中的终态结果；否则回退到服务层运行态的增量快照，两者都没有时只返回基础状态，保证前端轮询始终有响应。

    Args:
        task_id: 任务 ID，来自路径参数。

    Returns:
        ScannerTaskStatus: 状态、进度、计数、结果与步骤快照。

    Raises:
        HTTPException: 任务不存在、已过期或类型不匹配时返回 404。

    Side Effects:
        无；仅读取队列与服务层运行态。
    """
    task = get_task_queue().get_task(task_id)
    if task is None or task.report_type != TASK_REPORT_TYPE:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    status = task.status.value if isinstance(task.status, QueueTaskStatus) else str(task.status)
    result = (
        task.result
        if task.status == QueueTaskStatus.COMPLETED and isinstance(task.result, dict)
        else None
    )

    state = scanner_service.get_run_state(task_id)
    partial = scanner_service.build_partial_payload(state) if state else None

    if result:
        rows = result.get("results") or []
        step_rows = result.get("steps") or []
        return ScannerTaskStatus(
            task_id=task_id,
            status=status,
            progress=task.progress,
            message=task.message,
            error=task.error,
            pool_count=int(result.get("pool_count") or 0),
            scanned=int(result.get("scanned") or 0),
            match_count=int(result.get("match_count") or 0),
            results=[ScannerResultRow(**row) for row in rows],
            steps=[ScannerStep(**row) for row in step_rows],
            cancelled=bool(result.get("cancelled")),
            finished=True,
        )

    if partial:
        return ScannerTaskStatus(
            task_id=task_id,
            status=status,
            progress=int(partial.get("progress") or task.progress),
            message=partial.get("message") or task.message,
            error=task.error,
            pool_count=int(partial.get("pool_count") or 0),
            scanned=int(partial.get("scanned") or 0),
            match_count=int(partial.get("match_count") or 0),
            results=[ScannerResultRow(**row) for row in (partial.get("results") or [])],
            steps=[ScannerStep(**row) for row in (partial.get("steps") or [])],
            cancelled=bool(partial.get("cancelled")),
            finished=bool(partial.get("finished")),
        )

    return ScannerTaskStatus(
        task_id=task_id,
        status=status,
        progress=task.progress,
        message=task.message,
        error=task.error,
    )


@router.post("/tasks/{task_id}/cancel", response_model=ScannerCancelResult)
def scanner_cancel(task_id: str) -> ScannerCancelResult:
    """请求取消扫描：worker 在下一个检查点停止，已命中结果保留。

    协作式取消不强制杀线程，accepted=False 表示任务已结束，此时返回可读提示而不是报错。

    Args:
        task_id: 任务 ID，来自路径参数。

    Returns:
        ScannerCancelResult: 是否受理取消请求及说明文案。

    Raises:
        HTTPException: 任务不存在或类型不匹配时返回 404。

    Side Effects:
        在服务层标记取消标志，后台任务在检查点自行退出。
    """
    task = get_task_queue().get_task(task_id)
    if task is None or task.report_type != TASK_REPORT_TYPE:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    accepted = scanner_service.request_cancel(task_id)
    return ScannerCancelResult(
        task_id=task_id,
        cancelled=accepted,
        message=(
            "已请求取消，扫描将在当前批次后停止"
            if accepted
            else "任务已结束，无需取消"
        ),
    )
