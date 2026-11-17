# -*- coding: utf-8 -*-
"""
@file: eod_picker.py
@description: 尾盘选股法端点：默认筛选条件、异步选股任务提交与轮询、单股分时明细懒加载；由 api.v1.router 挂到 /api/v1/eod-picker，筛选逻辑在 src.application.analysis.eod_picker_service。
@author: Lensgcx (GaoCangxiong)

尾盘选股法（EOD Picker）API 路由。

- GET  /eod-picker/defaults            默认筛选条件
- POST /eod-picker/tasks               提交选股任务 -> 202 + task_id（异步）
- GET  /eod-picker/tasks/{id}          轮询任务进度与结果
- GET  /eod-picker/stocks/{code}/timeline  单只股票完整分时明细（懒加载）
"""
from __future__ import annotations

import copy
import threading
import uuid
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from api.deps import get_config_dep
from src.config import Config
from src.application.analysis import eod_picker_service
from src.application.runtime.task_queue import TaskStatus as QueueTaskStatus
from src.application.runtime.task_queue import get_task_queue

# 本模块的 APIRouter；由 api.v1.router 挂到 /api/v1/eod-picker。
router = APIRouter()

# 任务级步骤快照存储：task_id -> 最近一次 update_steps 全量快照。
# 仅服务于 eod-picker 轮询接口，不侵入通用 task_queue；按 LRU 限量并在
# 任务到达终态时清理，避免长驻内存。
# 保护步骤快照存储的互斥锁；后台写与轮询读都需持有。
_STEP_STORE_LOCK = threading.Lock()
# 任务 ID 到最近一次全量步骤快照的有序字典，按 LRU 淘汰。
_STEP_STORE: "OrderedDict[str, List[Dict[str, Any]]]" = OrderedDict()
# 步骤快照最多保留的任务数；终态任务读取一次后即清理。
_STEP_STORE_MAX_TASKS = 32


def _store_steps(task_id: str, steps: List[Dict[str, Any]]) -> None:
    """写入（替换）某任务的步骤快照；超出容量时淘汰最旧条目。

    深拷贝避免后台线程后续修改同一列表影响轮询读到的快照；move_to_end 让活跃任务保持最新，LRU 上限防止快照长驻内存。

    Args:
        task_id: 任务唯一标识。
        steps: 该任务最近一次全量步骤快照。

    Returns:
        None。

    Side Effects:
        在锁内修改模块级 _STEP_STORE，可能淘汰最旧任务条目。
    """
    with _STEP_STORE_LOCK:
        _STEP_STORE[task_id] = copy.deepcopy(steps)
        _STEP_STORE.move_to_end(task_id)
        while len(_STEP_STORE) > _STEP_STORE_MAX_TASKS:
            _STEP_STORE.popitem(last=False)


def _get_steps(task_id: str) -> List[Dict[str, Any]]:
    """读取某任务的步骤快照（不存在时返回空列表）。

    返回深拷贝，调用方修改结果不会污染存储中的快照。

    Args:
        task_id: 任务唯一标识。

    Returns:
        List[Dict[str, Any]]: 步骤快照副本；无记录时为空列表。

    Side Effects:
        无；仅在锁内读取。
    """
    with _STEP_STORE_LOCK:
        steps = _STEP_STORE.get(task_id)
        return copy.deepcopy(steps) if steps else []


def _clear_steps(task_id: str) -> None:
    """清理某任务的步骤快照（任务终态时调用）。

    Args:
        task_id: 任务唯一标识；不存在时静默忽略。

    Returns:
        None。

    Side Effects:
        在锁内从 _STEP_STORE 移除该任务条目。
    """
    with _STEP_STORE_LOCK:
        _STEP_STORE.pop(task_id, None)


class EodPickerStartRequest(BaseModel):
    """提交选股任务的请求体；filters 缺省时使用服务端默认值。

    @author: Lensgcx (GaoCangxiong)
    """
    # 筛选条件字典；None 时服务端使用 get_eod_picker_defaults() 的默认值。
    filters: Optional[Dict[str, Any]] = None


class EodPickerAccepted(BaseModel):
    """收盘选股任务已受理响应体。

    @author: Lensgcx (GaoCangxiong)
    """
    # 任务 ID，供轮询状态接口使用。
    task_id: str
    # 诊断 trace ID；本端点与 task_id 同值。
    trace_id: str
    # 提交时的状态，固定 pending。
    status: str = "pending"
    # 面向用户的提交提示。
    message: str


class EodPickerStepStock(BaseModel):
    """进度步骤中的单只股票条目。

    @author: Lensgcx (GaoCangxiong)
    """
    # 步骤快照中的股票代码。
    code: str
    # 步骤快照中的股票名称。
    name: str


class EodPickerStep(BaseModel):
    """进度步骤快照：一步筛选的阶段状态与该步过滤出的股票。

    @author: Lensgcx (GaoCangxiong)
    """
    key: str                                   # basic 基础过滤 / strength 分时强度过滤
    status: str = "running"                    # running 进行中 / done 已完成
    total: int = 0                             # 该步真实股票数（stocks 可能被截断）
    # 该步过滤出的股票列表；可能被服务层截断，真实数量见 total。
    stocks: List[EodPickerStepStock] = Field(default_factory=list)


class EodPickerTaskStatus(BaseModel):
    """收盘选股任务状态响应体。

    @author: Lensgcx (GaoCangxiong)
    """
    # 被轮询的任务 ID。
    task_id: str
    # 诊断 trace ID；旧任务可能与 task_id 相同。
    trace_id: Optional[str] = None
    # 任务状态字符串。
    status: str
    # 执行进度百分比，默认 0。
    progress: int = 0
    # 当前阶段的状态说明；可为空。
    message: Optional[str] = None
    # 失败原因；仅失败态有值。
    error: Optional[str] = None
    # 完成态的筛选结果字典；未完成为 None。
    result: Optional[Dict[str, Any]] = None
    # 各步骤的股票快照列表，默认空列表。
    steps: List[EodPickerStep] = Field(default_factory=list)


class EodPickerTimelinePoint(BaseModel):
    """与前端 KLineChart 的 KLinePoint 对齐（period='1m' 分时）。

    @author: Lensgcx (GaoCangxiong)
    """
    # 分时点时间，与前端 1m K 线的 date 字段对齐。
    date: str
    # 该分钟开盘价；无 OHLC 时为 None。
    open: Optional[float] = None
    # 该分钟最新价，分时曲线主取值。
    close: Optional[float] = None
    # 该分钟最高价；无 OHLC 时为 None。
    high: Optional[float] = None
    # 该分钟最低价；无 OHLC 时为 None。
    low: Optional[float] = None
    # 该分钟成交量；缺失时为 None。
    volume: Optional[float] = None
    # 该分钟成交额；缺失时为 None。
    amount: Optional[float] = None


class EodPickerTimeline(BaseModel):
    """收盘选股时间线响应体。

    @author: Lensgcx (GaoCangxiong)
    """
    # 请求的股票代码。
    code: str
    # 股票名称；服务层未返回时为空字符串。
    name: str
    # 昨收价，作为涨跌幅基准线；缺失时为 None。
    prev_close: Optional[float] = None
    # 按时间升序的分时点列表，必填。
    points: List[EodPickerTimelinePoint]


@router.get("/defaults")
def eod_picker_defaults() -> Dict[str, Any]:
    """返回默认筛选条件（前端「恢复默认」按钮的数据源）。

    默认值放在服务层，保证提交任务时缺省 filters 与前端展示的一致。

    Args:
        无参数。

    Returns:
        Dict[str, Any]: 可直接表单回填的筛选条件字典。

    Side Effects:
        无。
    """
    return eod_picker_service.get_eod_picker_defaults()


@router.post("/tasks", status_code=202, response_model=EodPickerAccepted)
def eod_picker_start(
    request: EodPickerStartRequest,
    http_request: Request,
    config: Config = Depends(get_config_dep),
) -> EodPickerAccepted:
    """提交一次尾盘选股任务，立即返回 task_id，前端轮询 /tasks/{id} 获取进度与结果。

    任务在通用后台队列执行，进度与步骤快照分别通过 task_queue 与 _store_steps 回写，端点不等待筛选完成，因此以 202 响应。

    Args:
        request: 选股请求体；filters 为空时使用服务端默认值。
        http_request: 原始请求对象，供后续扩展读取会话信息。
        config: 运行时配置，由 Depends(get_config_dep) 注入。

    Returns:
        EodPickerAccepted: task_id、trace_id、初始状态与提示文案。

    Side Effects:
        向全局任务队列提交后台任务；任务执行期间写入 _STEP_STORE。
    """
    task_id = uuid.uuid4().hex
    task_queue = get_task_queue()
    filters = request.filters or {}

    def run() -> Dict[str, Any]:
        """后台执行收盘选股任务。

        把队列进度回调与步骤快照回调接到服务层，服务本身不感知 task_queue。

        Args:
            无显式参数；捕获外层 filters、task_id 与 task_queue。

        Returns:
            Dict[str, Any]: 选股结果，由任务队列写入 task.result。

        Side Effects:
            更新任务进度并写入步骤快照存储。
        """
        return eod_picker_service.run_eod_picker(
            filters,
            update_progress=lambda p, m: task_queue.update_task_progress(task_id, p, m),
            update_steps=lambda steps: _store_steps(task_id, steps),
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
    """轮询选股任务状态；completed 时 result 携带筛选结果，steps 携带各步骤股票快照。

    通过 report_type 校验任务归属，避免拿到其他类型任务；终态读取一次后清理步骤快照，防止长驻内存。

    Args:
        task_id: 任务 ID，来自路径参数。

    Returns:
        EodPickerTaskStatus: 状态、进度、错误信息、结果与步骤快照。

    Raises:
        HTTPException: 任务不存在、已过期或类型不匹配时返回 404。

    Side Effects:
        任务处于完成/失败/取消态时清理 _STEP_STORE 对应条目。
    """
    task = get_task_queue().get_task(task_id)
    if task is None or task.report_type != "eod_picker":
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    result = (
        task.result
        if task.status == QueueTaskStatus.COMPLETED and isinstance(task.result, dict)
        else None
    )
    steps = _get_steps(task.task_id)
    if task.status in (
        QueueTaskStatus.COMPLETED,
        QueueTaskStatus.FAILED,
        QueueTaskStatus.CANCELLED,
    ):
        # 终态后前端不再轮询，读一次即清理，避免快照长驻内存
        _clear_steps(task.task_id)
    return EodPickerTaskStatus(
        task_id=task.task_id,
        trace_id=task.trace_id or task.task_id,
        status=task.status.value if isinstance(task.status, QueueTaskStatus) else str(task.status),
        progress=task.progress,
        message=task.message,
        error=task.error,
        result=result,
        steps=steps,
    )


@router.get("/stocks/{code}/timeline", response_model=EodPickerTimeline)
def eod_picker_timeline(
    code: str, limit: int = Query(240, ge=1, le=480)
) -> EodPickerTimeline:
    """返回单只股票的完整分时明细（价格线 + 均价线 VWAP），用于分时图懒加载。

    选股结果列表不携带逐分钟数据，用户展开某只股票时才按需拉取。

    Args:
        code: 股票代码，来自路径参数。
        limit: 分时点数量，范围 1~480，默认 240（一个完整交易日）。

    Returns:
        EodPickerTimeline: 代码、名称、昨收与分时点列表。

    Side Effects:
        无；取数由服务层完成。
    """
    data = eod_picker_service.fetch_intraday_timeline(code, limit)
    return EodPickerTimeline(
        code=data["code"],
        name=data.get("name", ""),
        prev_close=data.get("prev_close"),
        points=[EodPickerTimelinePoint(**p) for p in data.get("points", [])],
    )
