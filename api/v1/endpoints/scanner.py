# -*- coding: utf-8 -*-
"""技术信号扫描器（Scanner）API 路由。

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

from src.services import signal_scanner_service as scanner_service
from src.services.task_queue import TaskStatus as QueueTaskStatus
from src.services.task_queue import get_task_queue

router = APIRouter()

# 任务类型标记：与 eod-picker 同构，用于任务归属校验
TASK_REPORT_TYPE = "signal_scanner"


class ScannerWatchlistItem(BaseModel):
    """自选股池条目：前端传入（自选条目自带名称，后端无需再取行情补名）。"""

    code: str = Field(..., description="股票代码，支持 600519 / 600519.SH")
    name: str = Field("", description="股票名称（可为空，命中时回退 K 线源名称）")


class ScannerStartRequest(BaseModel):
    """提交扫描任务的请求体；非法取值由服务端回落到默认值。"""

    pool_source: str = Field("watchlist", description="watchlist / ranking / limit_up")
    ranking_field: str = Field("amount", description="amount / change_percent / turnover_rate")
    top_n: int = Field(20, ge=1, le=300, description="榜单 / 涨停池取前 N 只")
    signals: List[str] = Field(default_factory=lambda: ["ma_golden"], description="信号键列表")
    watchlist: Optional[List[ScannerWatchlistItem]] = Field(
        None, description="自选股池（pool_source=watchlist 时必填）"
    )


class ScannerAccepted(BaseModel):
    task_id: str
    status: str = "pending"
    message: str


class ScannerResultRow(BaseModel):
    """单条命中结果。"""

    code: str
    name: str = ""
    signals: List[str] = Field(default_factory=list)
    scanned_at: str = ""


class ScannerStepStock(BaseModel):
    """步骤快照中的单只股票（仅展示用，含代码与名称）。"""

    code: str
    name: str = ""


class ScannerStep(BaseModel):
    """扫描分步快照：全量下发、前端整体替换。

    - key: 步骤标识（pool=解析股票池 / signal=技术信号扫描），前端据此映射本地化标题
    - status: running / done
    - total: 该步真实股票数量（stocks 可能截断）
    - stocks: 该步过滤出的股票（上限见服务层 STEP_STOCK_LIMIT）
    """

    key: str
    status: str = "running"
    total: int = 0
    stocks: List[ScannerStepStock] = Field(default_factory=list)


class ScannerTaskStatus(BaseModel):
    """任务状态：拍平结果字段，运行中也能拿到增量结果。"""

    task_id: str
    status: str
    progress: int = 0
    message: Optional[str] = None
    error: Optional[str] = None
    pool_count: int = 0
    scanned: int = 0
    match_count: int = 0
    results: List[ScannerResultRow] = Field(default_factory=list)
    steps: List[ScannerStep] = Field(default_factory=list)
    cancelled: bool = False
    finished: bool = False


class ScannerCancelResult(BaseModel):
    task_id: str
    cancelled: bool
    message: str


@router.get("/options")
def scanner_options() -> Dict[str, Any]:
    """返回前端渲染所需的选项契约（避免前端写死池来源与信号键）。"""
    return scanner_service.get_scanner_options()


@router.post("/tasks", status_code=202, response_model=ScannerAccepted)
def scanner_start(request: ScannerStartRequest) -> ScannerAccepted:
    """提交一次信号扫描任务，立即返回 task_id，前端轮询 /tasks/{id}。"""
    task_id = uuid.uuid4().hex
    task_queue = get_task_queue()
    payload = scanner_service.normalize_request(request.model_dump())
    scanner_service.register_run(task_id)

    def run() -> Dict[str, Any]:
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
    """轮询扫描任务状态；运行中返回增量结果，完成时返回完整结果。"""
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
    """请求取消扫描：worker 在下一个检查点停止，已命中结果保留。"""
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
