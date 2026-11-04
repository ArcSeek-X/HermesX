# -*- coding: utf-8 -*-
"""Runtime scheduler service for long-lived API/Web/Desktop processes.

为长期运行的 API/Web/Desktop 进程提供运行时调度服务。封装一个 Scheduler，
按配置时间每日触发分析任务，并支持事件监控等后台任务；通过全局分析锁避免并发运行，
并记录最近运行/成功/错误/跳过状态。所有调度任务都在守护线程中执行，失败不应拖垮主进程。
"""

from __future__ import annotations

import logging
import os
import threading
import _thread
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Set

from src.application.runtime.scheduler import Scheduler
from src.config import Config, get_config
from src.domain.shared.schedule_times import normalize_schedule_times

logger = logging.getLogger(__name__)
CLI_SCHEDULER_OWNER_ENV = "HRS_CLI_SCHEDULER_OWNS_SCHEDULE"
RUNTIME_SCHEDULER_FORCE_ENABLED_ENV = "HRS_RUNTIME_SCHEDULER_FORCE_ENABLED"
RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV = "HRS_RUNTIME_SCHEDULER_RUN_IMMEDIATELY"
RUNTIME_SCHEDULER_SUPPRESS_START_ENV = "HRS_RUNTIME_SCHEDULER_SUPPRESS_START"
RUNTIME_SCHEDULER_ARGS_ENV = "HRS_RUNTIME_SCHEDULER_ARGS"
_RUNTIME_ANALYSIS_LOCK = threading.Lock()
SCHEDULE_ARGS_OVERRIDE_KEYS = {
    "no_notify",
    "no_market_review",
    "dry_run",
    "force_run",
    "single_notify",
    "no_context_snapshot",
    "workers",
    "portfolio",
}


def run_with_global_analysis_lock(
    task_runner: Callable[[Config, Any, Optional[List[str]]], Any],
    config: Config,
    args: Any,
    stock_codes: Optional[List[str]] = None,
    *,
    blocking: bool = True,
) -> bool:
    """Execute a task while holding the shared runtime analysis lock."""
    if not _RUNTIME_ANALYSIS_LOCK.acquire(blocking=blocking):
        return False
    try:
        task_runner(config, args, stock_codes)
    finally:
        _RUNTIME_ANALYSIS_LOCK.release()
    return True


def _agent_event_monitor_interval_seconds(config: Config) -> int:
    """Return the validated Event Monitor polling interval in seconds."""
    interval_minutes = getattr(config, "agent_event_monitor_interval_minutes", 5)
    try:
        interval_minutes = max(1, int(interval_minutes))
    except (TypeError, ValueError):  # pragma: no cover - defensive branch
        logger.warning(
            "Invalid AGENT_EVENT_MONITOR_INTERVAL_MINUTES=%r; use fallback 5",
            interval_minutes,
        )
        interval_minutes = 5
    return interval_minutes * 60


def build_agent_event_monitor_background_tasks(
    config: Config,
    *,
    config_provider: Callable[[], Config],
) -> List[Dict[str, Any]]:
    """Build scheduler background tasks used by the runtime scheduler."""
    if not getattr(config, "agent_event_monitor_enabled", False):
        return []

    from src.bootstrap.alert import build_alert_worker

    interval_seconds = _agent_event_monitor_interval_seconds(config)
    try:
        alert_worker = build_alert_worker(config_provider=config_provider)
    except Exception as exc:  # pragma: no cover - defensive branch
        logger.warning("Failed to initialize AlertWorker for event monitor: %s", exc)
        return []

    def event_monitor_task() -> None:
        """事件监控后台任务：调用 AlertWorker.run_once 执行一次告警检查，若有触发则记日志。"""
        stats = alert_worker.run_once()
        triggered_count = stats.get("triggered", 0)
        if triggered_count:
            logger.info("[EventMonitor] triggered %d alert(s)", triggered_count)

    return [{
        "task": event_monitor_task,
        "interval_seconds": interval_seconds,
        "run_immediately": True,
        "name": "agent_event_monitor",
    }]


class RuntimeSchedulerService:
    """Manage scheduled analysis inside the current API/Web/Desktop process."""

    def __init__(
        self,
        *,
        config_provider: Callable[[], Config] = get_config,
        task_runner: Optional[Callable[[Config, Any, Optional[List[str]]], Any]] = None,
        owns_schedule: Optional[bool] = None,
        force_enabled: bool = False,
        run_immediately_in_background: bool = False,
        background_tasks_provider: Optional[Callable[[Config], List[Dict[str, Any]]]] = None,
        schedule_args_overrides: Optional[Dict[str, Any]] = None,
    ) -> None:
        """装配调度服务：解析 owns_schedule（可被环境变量覆盖）、force_enabled、task_runner、后台任务提供方与计划参数覆盖，并初始化锁/调度器/状态字段。"""
        self._config_provider = config_provider
        self._task_runner = task_runner
        if owns_schedule is None:
            owns_schedule = os.getenv(CLI_SCHEDULER_OWNER_ENV, "").strip().lower() not in {
                "1",
                "true",
                "yes",
                "on",
            }
        self._owns_schedule = owns_schedule
        self._force_enabled = force_enabled
        self._run_immediately_in_background = run_immediately_in_background
        self._background_tasks_provider = background_tasks_provider
        self._schedule_args_overrides = {
            key: value
            for key, value in (schedule_args_overrides or {}).items()
            if key in SCHEDULE_ARGS_OVERRIDE_KEYS
        }
        self._background_task_cache: Dict[str, Dict[str, Any]] = {}
        self._background_task_registered_names: Set[str] = set()
        self._lock = threading.RLock()
        self._run_lock = _RUNTIME_ANALYSIS_LOCK
        self._scheduler: Optional[Scheduler] = None
        self._thread: Optional[threading.Thread] = None
        self._enabled = False
        self._last_run_at: Optional[str] = None
        self._last_success_at: Optional[str] = None
        self._last_error: Optional[str] = None
        self._last_skipped_at: Optional[str] = None
        self._last_skip_reason: Optional[str] = None

    def _make_schedule_args(self) -> SimpleNamespace:
        """构造传给计划分析任务的参数命名空间：以默认值为底，叠加 schedule_args_overrides 中允许的键（no_notify/dry_run 等）。"""
        defaults = {
            "schedule": True,
            "no_run_immediately": True,
            "no_notify": False,
            "no_market_review": False,
            "dry_run": False,
            "force_run": False,
            "single_notify": False,
            "no_context_snapshot": False,
            "market_review": False,
            "serve": False,
            "serve_only": True,
            "stocks": None,
            "portfolio": None,
            "workers": None,
        }
        defaults.update(self._schedule_args_overrides)
        return SimpleNamespace(**defaults)

    def _reload_config(self) -> Config:
        """运行时重载配置：委托 main._reload_runtime_config 返回最新 Config。"""
        from main import _reload_runtime_config

        return _reload_runtime_config()

    def _record_analysis_busy_skip(self) -> None:
        """记录一次因分析已在运行而被跳过的调度：记下跳过时间与原因，并输出警告日志。"""
        self._last_skipped_at = datetime.now().isoformat()
        self._last_skip_reason = "analysis_already_running"
        logger.warning("Runtime scheduler skipped run: analysis already running")

    def _run_analysis_locked(self, stock_codes: Optional[List[str]]) -> None:
        """在已持有全局分析锁的前提下执行一次分析：重载配置→解析 runner→更新运行时间→执行，失败则记录错误但不向上抛（保护宿主进程）。"""
        try:
            config = self._reload_config()
            runner = self._task_runner
            if runner is None:
                from main import run_scheduled_analysis

                runner = run_scheduled_analysis
            self._last_run_at = datetime.now().isoformat()
            result = runner(config, self._make_schedule_args(), stock_codes)
            if result is False:
                raise RuntimeError("runtime scheduled analysis reported failure")
            self._last_success_at = datetime.now().isoformat()
            self._last_error = None
        except Exception as exc:  # noqa: BLE001 - scheduled runs must not kill API process.
            self._last_error = str(exc)
            logger.exception("Runtime scheduled analysis failed: %s", exc)

    def _run_analysis_once(self, stock_codes: Optional[List[str]] = None) -> bool:
        """尝试非阻塞获取全局分析锁并执行一次分析；若锁被占用则记录跳过并返回 False，否则执行并在 finally 释放锁。"""
        if not self._run_lock.acquire(blocking=False):
            self._record_analysis_busy_skip()
            return False
        try:
            self._run_analysis_locked(stock_codes)
        finally:
            self._run_lock.release()
        return True

    def _current_times(self) -> List[str]:
        """返回当前配置的调度时刻列表：从 config 取 schedule_times，缺失回退 schedule_time（默认 18:00）。"""
        config = self._config_provider()
        return normalize_schedule_times(
            getattr(config, "schedule_times", None),
            fallback_time=getattr(config, "schedule_time", "18:00"),
        )

    def _is_schedule_enabled(self, config: Config) -> bool:
        """判断调度是否启用：force_enabled 或 config.schedule_enabled 为真即启用。"""
        return self._force_enabled or bool(getattr(config, "schedule_enabled", False))

    def _current_background_tasks(self, config: Config) -> List[Dict[str, Any]]:
        """获取当前后台任务列表：优先用注入的 provider，否则回退到事件监控后台任务。"""
        if self._background_tasks_provider is not None:
            return self._background_tasks_provider(config)
        return self._current_agent_event_monitor_background_tasks(config)

    def _current_agent_event_monitor_background_tasks(self, config: Config) -> List[Dict[str, Any]]:
        """构造（并带缓存地维护）事件监控后台任务：未启用时清理缓存并返回空；首次构建后缓存，再次调用按 interval 与是否已注册决定 run_immediately。"""
        name = "agent_event_monitor"
        if not getattr(config, "agent_event_monitor_enabled", False):
            self._background_task_cache.pop(name, None)
            self._background_task_registered_names.discard(name)
            return []

        cached = self._background_task_cache.get(name)
        if cached is None:
            entries = build_agent_event_monitor_background_tasks(
                config,
                config_provider=self._reload_config,
            )
            if not entries:
                self._background_task_cache.pop(name, None)
                self._background_task_registered_names.discard(name)
                return []
            cached = dict(entries[0])
            cached["name"] = name
            self._background_task_cache[name] = cached
            interval_seconds = int(cached["interval_seconds"])
        else:
            interval_seconds = _agent_event_monitor_interval_seconds(config)

        run_immediately = (
            bool(cached.get("run_immediately", False))
            and name not in self._background_task_registered_names
        )
        self._background_task_registered_names.add(name)
        return [{
            "task": cached["task"],
            "interval_seconds": interval_seconds,
            "run_immediately": run_immediately,
            "name": name,
        }]

    @staticmethod
    def _run_in_background_thread(target: Callable[[], None]) -> None:
        """Run a callback in a background thread without blocking startup."""
        try:
            _thread.start_new_thread(target, ())
            return
        except Exception:
            # Best-effort fallback for environments where the low-level thread API
            # is unavailable or restricted.
            thread = threading.Thread(target=target, daemon=True)
            thread.start()

    def start(self, *, run_immediately: bool = False) -> None:
        """启动调度：在锁内判定是否拥有调度权与是否启用，重建 Scheduler、注册每日分析任务与后台任务，并在守护线程中运行；需要后台立即执行时改为新线程触发。"""
        with self._lock:
            if not self._owns_schedule:
                self.stop()
                return
            config = self._config_provider()
            if not self._is_schedule_enabled(config):
                self.stop()
                return
            background_tasks = self._current_background_tasks(config)
            self.stop()
            times = normalize_schedule_times(
                getattr(config, "schedule_times", None),
                fallback_time=getattr(config, "schedule_time", "18:00"),
            )
            scheduler = Scheduler(
                schedule_time=getattr(config, "schedule_time", "18:00"),
                schedule_times=times,
                schedule_times_provider=self._current_times,
                register_signals=False,
            )
            if run_immediately and self._run_immediately_in_background:
                scheduler.set_daily_task(self._run_analysis_once, run_immediately=False)
            else:
                scheduler.set_daily_task(self._run_analysis_once, run_immediately=run_immediately)
            for entry in background_tasks:
                scheduler.add_background_task(
                    entry["task"],
                    interval_seconds=entry["interval_seconds"],
                    run_immediately=entry.get("run_immediately", False),
                    name=entry.get("name"),
                )
            if run_immediately and self._run_immediately_in_background:
                self._run_in_background_thread(self._run_analysis_once)
            thread = threading.Thread(
                target=scheduler.run,
                daemon=True,
                name="runtime-scheduler",
            )
            self._scheduler = scheduler
            self._thread = thread
            self._enabled = True
            thread.start()

    def stop(self) -> None:
        """停止调度：停止底层 Scheduler 并清空调度器/线程引用，置 enabled=False。"""
        scheduler = self._scheduler
        if scheduler is not None:
            scheduler.stop()
        self._scheduler = None
        self._thread = None
        self._enabled = False

    def reconcile_from_config(
        self,
        *,
        run_immediately: bool = False,
        clear_enabled_override: bool = False,
    ) -> None:
        """依据最新配置协调调度状态：可选清除 force_enabled 覆盖，若失去调度权或不启用则停止，否则按配置启动（可立即运行）。"""
        if clear_enabled_override:
            self._force_enabled = False
        if not self._owns_schedule:
            self.stop()
            return
        config = self._config_provider()
        if self._is_schedule_enabled(config):
            self.start(run_immediately=run_immediately)
        else:
            self.stop()

    def run_now(self) -> Dict[str, Any]:
        """立即触发一次分析（非阻塞）：获取不到锁则返回已占用；否则在守护线程中执行并立即返回 {accepted:True,running:True}。"""
        if not self._run_lock.acquire(blocking=False):
            self._record_analysis_busy_skip()
            return {
                "accepted": False,
                "running": True,
                "reason": "analysis_already_running",
            }

        def run_and_release() -> None:
            """run_now 的后台执行体：在持有锁的线程中跑一次分析，结束后在 finally 释放锁。"""
            try:
                self._run_analysis_locked(None)
            finally:
                self._run_lock.release()

        worker = threading.Thread(
            target=run_and_release,
            daemon=True,
            name="runtime-scheduler-run-now",
        )
        try:
            worker.start()
        except Exception:
            self._run_lock.release()
            raise
        return {"accepted": True, "running": True}

    def status(self) -> Dict[str, Any]:
        """返回调度状态快照：是否启用/运行中、调度时刻列表、下次运行时间、最近运行/成功/错误/跳过时间与跳过原因。"""
        scheduler = self._scheduler
        jobs = scheduler.schedule.get_jobs() if scheduler is not None else []
        next_run = None
        if jobs:
            next_run = min(job.next_run for job in jobs).isoformat()
        if scheduler is not None:
            schedule_times = list(getattr(scheduler, "schedule_times", []))
        else:
            try:
                schedule_times = self._current_times()
            except Exception:  # pragma: no cover - defensive status fallback
                schedule_times = []
        running = self._run_lock.locked()
        return {
            "enabled": self._enabled,
            "running": running,
            "schedule_times": schedule_times,
            "next_run_at": next_run,
            "last_run_at": self._last_run_at,
            "last_success_at": self._last_success_at,
            "last_error": self._last_error,
            "last_skipped_at": self._last_skipped_at,
            "last_skip_reason": self._last_skip_reason,
        }
