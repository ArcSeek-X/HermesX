# -*- coding: utf-8 -*-
"""尾盘选股法（EOD Picker）API 路由。

- GET  /eod-picker/defaults            默认筛选条件
- POST /eod-picker/tasks               提交选股任务 -> 202 + task_id（异步）
- GET  /eod-picker/tasks/{id}          轮询任务进度与结果
- GET  /eod-picker/stocks/{code}/timeline  单只股票完整分时明细（懒加载）
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from api.deps import get_config_dep
from src.config import Config
from src.services import eod_picker_service
from src.services.task_queue import TaskStatus as QueueTaskStatus
from src.services.task_queue import get_task_queue

router = APIRouter()


class EodPickerStartRequest(BaseModel):
    """提交选股任务的请求体；filters 缺省时使用服务端默认值。"""
    filters: Optional[Dict[str, Any]] = None


class EodPickerAccepted(BaseModel):
    task_id: str
    trace_id: str
    status: str = "pending"
    message: str


class EodPickerTaskStatus(BaseModel):
    task_id: str
    trace_id: Optional[str] = None
    status: str
    progress: int = 0
    message: Optional[str] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class EodPickerTimelinePoint(BaseModel):
    """与前端 KLineChart 的 KLinePoint 对齐（period='1m' 分时）。"""
    date: str
    open: Optional[float] = None
    close: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None


class EodPickerTimeline(BaseModel):
    code: str
    name: str
    prev_close: Optional[float] = None
    points: List[EodPickerTimelinePoint]


@router.get("/defaults")
def eod_picker_defaults() -> Dict[str, Any]:
    """返回默认筛选条件（前端「恢复默认」按钮的数据源）。"""
    return eod_picker_service.get_eod_picker_defaults()


@router.post("/tasks", status_code=202, response_model=EodPickerAccepted)
def eod_picker_start(
    request: EodPickerStartRequest,
    http_request: Request,
    config: Config = Depends(get_config_dep),
) -> EodPickerAccepted:
    """提交一次尾盘选股任务，立即返回 task_id，前端轮询 /tasks/{id} 获取进度与结果。"""
    task_id = uuid.uuid4().hex
    task_queue = get_task_queue()
    filters = request.filters or {}

    def run() -> Dict[str, Any]:
        return eod_picker_service.run_eod_picker(
            filters,
            update_progress=lambda p, m: task_queue.update_task_progress(task_id, p, m),
        )

    task_queue.submit_background_task(
        run,
        stock_code="eod_picker",
        stock_name="尾盘选股",
        report_type="eod_picker",
        message="尾盘选股任务已提交",
        task_id=task_id,
        trace_id=task_id,
    )
    return EodPickerAccepted(
        task_id=task_id,
        trace_id=task_id,
        status="pending",
        message="尾盘选股任务已提交",
    )


@router.get("/tasks/{task_id}", response_model=EodPickerTaskStatus)
def eod_picker_task_status(task_id: str) -> EodPickerTaskStatus:
    """轮询选股任务状态；completed 时 result 携带筛选结果。"""
    task = get_task_queue().get_task(task_id)
    if task is None or task.report_type != "eod_picker":
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    result = (
        task.result
        if task.status == QueueTaskStatus.COMPLETED and isinstance(task.result, dict)
        else None
    )
    return EodPickerTaskStatus(
        task_id=task.task_id,
        trace_id=task.trace_id or task.task_id,
        status=task.status.value if isinstance(task.status, QueueTaskStatus) else str(task.status),
        progress=task.progress,
        message=task.message,
        error=task.error,
        result=result,
    )


@router.get("/stocks/{code}/timeline", response_model=EodPickerTimeline)
def eod_picker_timeline(
    code: str, limit: int = Query(240, ge=1, le=480)
) -> EodPickerTimeline:
    """返回单只股票的完整分时明细（价格线 + 均价线 VWAP），用于分时图懒加载。"""
    data = eod_picker_service.fetch_intraday_timeline(code, limit)
    return EodPickerTimeline(
        code=data["code"],
        name=data.get("name", ""),
        prev_close=data.get("prev_close"),
        points=[EodPickerTimelinePoint(**p) for p in data.get("points", [])],
    )
