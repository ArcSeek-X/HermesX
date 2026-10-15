# -*- coding: utf-8 -*-
"""
技术信号扫描器（Scanner）服务层。

设计要点：
- 与尾盘选股（eod_picker_service）同构：后端异步任务 + 进度回调，单只失败不拖垮整体。
- 两阶段：
  1) 解析股票池（自选股 / 榜单 TopN / 涨停池）
  2) 对池内每只股票取日 K（前复权，约 1 年）并做信号检测（scanner_indicators）
- 增量结果：命中即写入本次运行的快照，任务未完成时前端轮询也能看到已命中结果
  （对齐参考项目 stock-dashboard 的 onResult 逐条出结果的体验）。
- 取消：协作式。本模块自持 task_id -> threading.Event 注册表，worker 循环检查；
  不修改通用任务队列（task_queue 无 cancel API，避免动到既有契约）。
- 代码格式：对外统一返回**裸码**（600519）；K 线请求同样使用裸码，
  由 data_provider 内部按源自行转换为 secid / sina symbol。
"""
from __future__ import annotations

import datetime
import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from data_provider.base import canonical_stock_code, normalize_stock_code
from data_provider.kline.base import KLineRequest, get_kline_data
from src.services.scanner_indicators import SIGNAL_KEYS, detect_signals

logger = logging.getLogger(__name__)

# ----------------------------- 契约常量（前端 /options 与请求校验共用） -----------------------------

POOL_SOURCES: Tuple[str, ...] = ("watchlist", "ranking", "limit_up")
RANKING_FIELDS: Tuple[str, ...] = ("amount", "change_percent", "turnover_rate")
TOP_N_OPTIONS: Tuple[int, ...] = (20, 50, 100)

DEFAULT_POOL_SOURCE = "watchlist"
DEFAULT_RANKING_FIELD = "amount"
DEFAULT_TOP_N = 20
DEFAULT_SIGNALS: Tuple[str, ...] = ("ma_golden",)

# 股票池上限：防止自选股一次性灌入超大池拖垮扫描
MAX_POOL_SIZE = 300

# 日 K 取样根数：约 1 年交易日，满足 MACD / BOLL 窗口需求
KLINE_LIMIT = 250

# 并发上限：与 eod_picker_service 一致，东财 push2his 对突发高并发限流严格
DEFAULT_CONCURRENCY = 4

# 进度区间：池解析占 0~POOL_STAGE_MAX，扫描占 POOL_STAGE_MAX~100
POOL_STAGE_MAX = 10

# 步骤快照标识（前端按 key 映射本地化标题，与语言解耦）
STEP_POOL = "pool"          # 第一步：解析股票池（候选）
STEP_SIGNAL = "signal"      # 第二步：技术信号扫描（命中）

# 单个步骤快照返回的股票条目上限（防轮询 payload 膨胀；total 仍为真实数量）
STEP_STOCK_LIMIT = 200

# 榜单排序字段 -> 全市场快照中文列名（eod_picker_service.get_realtime_quote_snapshot 的列）
_RANKING_FIELD_TO_COLUMN: Dict[str, str] = {
    "amount": "成交额",
    "change_percent": "涨跌幅",
    "turnover_rate": "换手率",
}


class ScanCancelled(Exception):
    """扫描被用户取消（协作式中断）。"""


# ----------------------------- 运行态注册表（取消 + 增量结果） -----------------------------

@dataclass
class _RunState:
    """单次扫描的运行态快照：取消信号 + 增量结果 + 进度 + 分步快照。"""

    cancel_event: threading.Event
    lock: threading.Lock = field(default_factory=threading.Lock)
    results: List[Dict[str, Any]] = field(default_factory=list)
    progress: int = 0
    message: str = "待开始"
    pool_count: int = 0
    scanned: int = 0
    cancelled: bool = False
    finished: bool = False
    steps: List[Dict[str, Any]] = field(default_factory=list)


_RUNS: Dict[str, _RunState] = {}
_RUNS_LOCK = threading.Lock()


def register_run(task_id: str) -> _RunState:
    """登记一次扫描运行态（同 task_id 重复调用以首次为准）。"""
    with _RUNS_LOCK:
        state = _RUNS.get(task_id)
        if state is None:
            state = _RunState(cancel_event=threading.Event())
            _RUNS[task_id] = state
        return state


def get_run_state(task_id: str) -> Optional[_RunState]:
    """取运行态；不存在（任务过期或从未登记）返回 None。"""
    with _RUNS_LOCK:
        return _RUNS.get(task_id)


def request_cancel(task_id: str) -> bool:
    """请求取消扫描。返回是否已登记该任务（False 表示任务不存在或已结束）。"""
    state = get_run_state(task_id)
    if state is None or state.finished:
        return False
    state.cancel_event.set()
    with state.lock:
        state.cancelled = True
        state.message = "正在取消扫描"
    return True


def build_partial_payload(state: _RunState) -> Dict[str, Any]:
    """构造轮询响应体：任务未完成也带上已命中的结果与分步快照。"""
    with state.lock:
        return {
            "progress": state.progress,
            "message": state.message,
            "pool_count": state.pool_count,
            "scanned": state.scanned,
            "match_count": len(state.results),
            "results": list(state.results),
            "steps": list(state.steps),
            "cancelled": state.cancelled,
            "finished": state.finished,
        }


def release_run(task_id: Optional[str]) -> None:
    """扫描结束后释放运行态（结果已在任务 result 中留存，注册表无需常驻）。"""
    if not task_id:
        return
    with _RUNS_LOCK:
        _RUNS.pop(task_id, None)


def build_cancelled_result(
    payload: Mapping[str, Any], task_id: Optional[str]
) -> Dict[str, Any]:
    """构造「已取消」结果：保留取消前已命中的部分结果，cancelled=True。"""
    state = get_run_state(task_id) if task_id else None
    partial = build_partial_payload(state) if state else None
    if partial is None:
        results: List[Dict[str, Any]] = []
        pool_count = 0
        scanned = 0
    else:
        results = list(partial.get("results") or [])
        pool_count = int(partial.get("pool_count") or 0)
        scanned = int(partial.get("scanned") or 0)

    return _build_result(
        payload,
        pool_count=pool_count,
        scanned=scanned,
        results=results,
        cancelled=True,
    )


def get_scanner_options() -> Dict[str, Any]:
    """返回前端渲染所需的选项契约（池来源 / 榜单字段 / TopN / 信号键）。"""
    return {
        "pool_sources": list(POOL_SOURCES),
        "ranking_fields": list(RANKING_FIELDS),
        "top_n_options": list(TOP_N_OPTIONS),
        "signals": list(SIGNAL_KEYS),
        "defaults": {
            "pool_source": DEFAULT_POOL_SOURCE,
            "ranking_field": DEFAULT_RANKING_FIELD,
            "top_n": DEFAULT_TOP_N,
            "signals": list(DEFAULT_SIGNALS),
        },
        "max_pool_size": MAX_POOL_SIZE,
    }


# ----------------------------- 请求规整 -----------------------------

def _safe_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(value)))
    except (TypeError, ValueError):
        return default


def normalize_request(request: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """规整扫描请求：未知项回落默认值，避免脏参数打穿下游。"""
    raw = dict(request or {})

    pool_source = str(raw.get("pool_source") or DEFAULT_POOL_SOURCE)
    if pool_source not in POOL_SOURCES:
        pool_source = DEFAULT_POOL_SOURCE

    ranking_field = str(raw.get("ranking_field") or DEFAULT_RANKING_FIELD)
    if ranking_field not in RANKING_FIELDS:
        ranking_field = DEFAULT_RANKING_FIELD

    signals = [str(key) for key in (raw.get("signals") or []) if str(key) in SIGNAL_KEYS]
    if not signals:
        signals = list(DEFAULT_SIGNALS)

    watchlist: List[Dict[str, str]] = []
    for item in raw.get("watchlist") or []:
        if not isinstance(item, Mapping):
            continue
        code = normalize_stock_code(str(item.get("code") or ""))
        if not code:
            continue
        watchlist.append({"code": code, "name": str(item.get("name") or "")})
        if len(watchlist) >= MAX_POOL_SIZE:
            break

    return {
        "pool_source": pool_source,
        "ranking_field": ranking_field,
        "top_n": _safe_int(raw.get("top_n"), DEFAULT_TOP_N, 1, MAX_POOL_SIZE),
        "signals": signals,
        "watchlist": watchlist,
    }


# ----------------------------- 股票池解析 -----------------------------

def _resolve_watchlist_pool(watchlist: Sequence[Mapping[str, Any]]) -> List[Dict[str, str]]:
    """自选股池：由调用方（前端）传入，后端仅做去重与代码归一化。"""
    pool: List[Dict[str, str]] = []
    seen = set()
    for item in watchlist:
        code = normalize_stock_code(str(item.get("code") or ""))
        if not code or code in seen:
            continue
        seen.add(code)
        pool.append({"code": code, "name": str(item.get("name") or "")})
    return pool


def _resolve_ranking_pool(ranking_field: str, top_n: int) -> List[Dict[str, str]]:
    """榜单 TopN：复用尾盘选股的全市场快照（东财 -> 腾讯 -> akshare 三级回退）。"""
    from src.services.eod_picker_service import get_realtime_quote_snapshot

    import pandas as pd

    frame = get_realtime_quote_snapshot()
    if frame is None or frame.empty:
        logger.warning("[Scanner] 全市场快照不可用，榜单池为空")
        return []

    column = _RANKING_FIELD_TO_COLUMN[ranking_field]
    if column not in frame.columns:
        logger.warning("[Scanner] 全市场快照缺少排序列 %s", column)
        return []

    working = frame.copy()
    working["_code"] = working["代码"].astype(str).map(lambda v: normalize_stock_code(v))
    working["_sort"] = pd.to_numeric(working[column], errors="coerce")
    working = working.dropna(subset=["_sort", "_code"]).sort_values(
        by="_sort", ascending=False, kind="stable"
    )

    pool: List[Dict[str, str]] = []
    for _, row in working.head(top_n).iterrows():
        code = str(row.get("_code") or "")
        if not code:
            continue
        pool.append({"code": code, "name": str(row.get("名称") or "")})
    return pool


def _resolve_limit_up_pool(top_n: int) -> List[Dict[str, str]]:
    """涨停池：DataFetcherManager 多源回退，已按连板数 / 封板时间排序。"""
    from data_provider.base import DataFetcherManager

    try:
        rows = DataFetcherManager().get_limit_up_pool(n=top_n) or []
    except Exception as exc:  # 数据源异常不拖垮整体，降级为空池由上层提示
        logger.warning("[Scanner] 获取涨停池失败: %s", exc)
        return []

    pool: List[Dict[str, str]] = []
    seen = set()
    for row in rows:
        code = normalize_stock_code(str(row.get("code") or ""))
        if not code or code in seen:
            continue
        seen.add(code)
        pool.append({"code": code, "name": str(row.get("name") or "")})
    return pool


def resolve_stock_pool(request: Mapping[str, Any]) -> List[Dict[str, str]]:
    """按请求解析股票池，返回 [{'code': 裸码, 'name': 名称}]。"""
    source = request.get("pool_source")
    if source == "ranking":
        return _resolve_ranking_pool(
            str(request.get("ranking_field") or DEFAULT_RANKING_FIELD),
            int(request.get("top_n") or DEFAULT_TOP_N),
        )
    if source == "limit_up":
        return _resolve_limit_up_pool(int(request.get("top_n") or DEFAULT_TOP_N))
    return _resolve_watchlist_pool(request.get("watchlist") or [])


def _step_snapshot(
    key: str, status: str, entries: Sequence[Mapping[str, Any]]
) -> Dict[str, Any]:
    """构造单个步骤快照：{key, status, total(真实数量), stocks(截断后)}。

    stocks 为 [{code, name}]，截断到 STEP_STOCK_LIMIT 以防轮询 payload 膨胀。
    """
    return {
        "key": key,
        "status": status,
        "total": len(entries),
        "stocks": [{"code": str(e.get("code") or ""), "name": str(e.get("name") or "")} for e in entries][
            :STEP_STOCK_LIMIT
        ],
    }


# ----------------------------- 扫描执行 -----------------------------

def _scan_one(item: Mapping[str, str], signals: Sequence[str]) -> Optional[Dict[str, Any]]:
    """扫描单只股票：取日 K -> 检测信号；无数据或无命中返回 None。"""
    code = str(item.get("code") or "")
    try:
        kline = get_kline_data(
            KLineRequest(stock_code=code, period="daily", limit=KLINE_LIMIT, fqt=1)
        )
    except Exception as exc:
        logger.warning("[Scanner] 获取 %s 日K失败: %s", code, exc)
        return None

    bars = kline.data if kline else []
    if not bars:
        return None

    matched = detect_signals(bars, signals)
    if not matched:
        return None

    name = str(item.get("name") or "") or (kline.stock_name if kline else "") or ""
    return {
        "code": canonical_stock_code(code),
        "name": name,
        "signals": list(matched),
        "scanned_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }


def run_signal_scan(
    request: Optional[Mapping[str, Any]] = None,
    *,
    task_id: Optional[str] = None,
    update_progress: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, Any]:
    """执行一次技术信号扫描。

    Args:
        request: 扫描请求（见 normalize_request）。
        task_id: 任务 ID，用于登记取消信号与增量结果；缺省时仍可运行（离线场景）。
        update_progress: 进度回调 (progress:int[0..100], message:str) -> None。

    Returns:
        结果字典：request / pool_count / scanned / match_count / results / cancelled / generated_at。

    Raises:
        ScanCancelled: 扫描被取消（由调用方转换为「已取消」语义，不应记为失败）。
    """
    payload = normalize_request(request)
    update = update_progress or (lambda p, m: None)
    state = register_run(task_id) if task_id else None

    def report(progress: int, message: str) -> None:
        update(progress, message)
        if state is not None:
            with state.lock:
                state.progress = progress
                state.message = message

    def report_steps(steps: Sequence[Mapping[str, Any]]) -> None:
        if state is not None:
            with state.lock:
                state.steps = [dict(s) for s in steps]

    # 阶段 1：解析股票池
    report(2, "解析股票池")
    pool = resolve_stock_pool(payload)
    if state is not None:
        with state.lock:
            state.pool_count = len(pool)

    pool_entries = [{"code": p["code"], "name": p.get("name", "")} for p in pool]

    if not pool:
        report(100, "股票池为空")
        if state is not None:
            state.finished = True
        report_steps([_step_snapshot(STEP_POOL, "done", []), _step_snapshot(STEP_SIGNAL, "done", [])])
        return _build_result(payload, pool_count=0, scanned=0, results=[], steps=[], cancelled=False)

    if state is not None and state.cancel_event.is_set():
        raise ScanCancelled()

    report(POOL_STAGE_MAX, f"股票池 {len(pool)} 只，开始技术信号扫描")
    logger.debug("[Scanner] 股票池 %d 只，信号 %s", len(pool), ",".join(payload["signals"]))
    report_steps([
        _step_snapshot(STEP_POOL, "done", pool_entries),
        _step_snapshot(STEP_SIGNAL, "running", []),
    ])

    # 阶段 2：有界并发扫描
    signals = payload["signals"]
    total = len(pool)
    workers = max(1, min(DEFAULT_CONCURRENCY, total))
    scanned = 0
    matched_results: List[Dict[str, Any]] = []
    lock = threading.Lock()

    def worker(item: Mapping[str, str]) -> Optional[Dict[str, Any]]:
        if state is not None and state.cancel_event.is_set():
            return None
        return _scan_one(item, signals)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures: List[Future] = [executor.submit(worker, item) for item in pool]
        pending = set(futures)

        for future in as_completed(futures):
            pending.discard(future)
            result = None
            try:
                result = future.result()
            except Exception as exc:  # 单只异常不影响整体（数据源失败 fail-open）
                logger.warning("[Scanner] 扫描单只股票异常: %s", exc)

            with lock:
                scanned += 1
                if result:
                    matched_results.append(result)

            if state is not None:
                with state.lock:
                    state.scanned = scanned
                    if result:
                        state.results.append(result)

            report(
                POOL_STAGE_MAX + int((100 - POOL_STAGE_MAX) * scanned / total),
                f"技术信号扫描 {scanned}/{total}",
            )

            # 协作式取消：停掉尚未开始的任务，已完成的保留为部分结果
            if state is not None and state.cancel_event.is_set():
                for pending_future in pending:
                    pending_future.cancel()
                break

    cancelled = bool(state is not None and state.cancel_event.is_set())
    if cancelled:
        report(100, f"扫描已取消，已命中 {len(matched_results)} 只")
        raise ScanCancelled()

    # 结果顺序对齐股票池顺序，避免并发完成顺序导致列表跳动
    order = {item["code"]: index for index, item in enumerate(pool)}
    matched_results.sort(key=lambda row: order.get(str(row.get("code") or ""), len(order)))

    matched_entries = [{"code": r["code"], "name": r["name"]} for r in matched_results]
    report_steps([
        _step_snapshot(STEP_POOL, "done", pool_entries),
        _step_snapshot(STEP_SIGNAL, "done", matched_entries),
    ])

    report(100, f"扫描完成，命中 {len(matched_results)} 只")
    if state is not None:
        with state.lock:
            state.results = list(matched_results)
            state.finished = True

    return _build_result(
        payload,
        pool_count=total,
        scanned=scanned,
        results=matched_results,
        steps=[
            _step_snapshot(STEP_POOL, "done", pool_entries),
            _step_snapshot(STEP_SIGNAL, "done", matched_entries),
        ],
        cancelled=False,
    )


def _build_result(
    payload: Mapping[str, Any],
    *,
    pool_count: int,
    scanned: int,
    results: List[Dict[str, Any]],
    cancelled: bool,
    steps: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    return {
        "request": dict(payload),
        "pool_count": pool_count,
        "scanned": scanned,
        "match_count": len(results),
        "results": results,
        "steps": list(steps or []),
        "cancelled": cancelled,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }


__all__ = [
    "POOL_SOURCES",
    "RANKING_FIELDS",
    "TOP_N_OPTIONS",
    "ScanCancelled",
    "get_scanner_options",
    "normalize_request",
    "resolve_stock_pool",
    "run_signal_scan",
    "request_cancel",
    "get_run_state",
    "build_partial_payload",
    "build_cancelled_result",
    "register_run",
    "release_run",
]
