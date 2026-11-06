"""原预算/重试/超时执行机制；不新建资源，不统一不同供应商策略。"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple


@dataclass(frozen=True)
class BoundedExecution:
    """复用原超时槽；超时后由真实 worker 退出时归还配额。"""

    read_timeout_slots: Callable
    read_config: Callable
    use_run_with_timeout: Callable
    read_time: Callable
    read_thread: Callable

    def _run_with_timeout(
        self, task: Callable[[], Any], timeout_seconds: float, task_name: str
    ) -> Tuple[Optional[Any], Optional[str], int]:
        """
        Execute a task in a short-lived thread and enforce a timeout.

        Returns:
            (result, error, duration_ms)
        """
        start = self.read_time().time()
        timeout_value = max(0.0, timeout_seconds)
        if timeout_value <= 0:
            return (None, f"{task_name} timeout", 0)
        result_holder: Dict[str, Any] = {}
        error_holder: Dict[str, Exception] = {}
        if not self.read_timeout_slots().acquire(blocking=False):
            return (
                None,
                f"{task_name} timeout worker pool exhausted",
                int(timeout_value * 1000),
            )

        def runner() -> None:
            """并发执行取数任务的主循环。"""
            try:
                result_holder["value"] = task()
            except Exception as exc:
                error_holder["value"] = exc
            finally:
                try:
                    self.read_timeout_slots().release()
                except ValueError:
                    pass

        worker = self.read_thread()(
            target=runner, daemon=True, name=f"fundamental-{task_name}"
        )
        try:
            worker.start()
        except Exception as exc:
            try:
                self.read_timeout_slots().release()
            except ValueError:
                pass
            return (None, str(exc), int((self.read_time().time() - start) * 1000))
        worker.join(timeout=timeout_value)
        if worker.is_alive():
            return (None, f"{task_name} timeout", int(timeout_value * 1000))
        if "value" in error_holder:
            return (
                None,
                str(error_holder["value"]),
                int((self.read_time().time() - start) * 1000),
            )
        return (
            result_holder.get("value"),
            None,
            int((self.read_time().time() - start) * 1000),
        )

    def _run_with_retry(
        self, task: Callable[[], Any], timeout_seconds: float, task_name: str
    ) -> Tuple[Optional[Any], Optional[str], int]:
        """
        Execute a task with bounded budget and best-effort retries.

        Returns:
            (result, error, total_duration_ms)
        """
        config = self.read_config()
        attempts = max(1, int(config.fundamental_retry_max))
        remaining_seconds = max(0.0, float(timeout_seconds))
        total_cost_ms = 0
        last_error: Optional[str] = None
        for _ in range(attempts):
            if remaining_seconds <= 0:
                break
            result, err, cost_ms = self.use_run_with_timeout(
                task, remaining_seconds, task_name
            )
            total_cost_ms += cost_ms
            remaining_seconds = max(0.0, remaining_seconds - cost_ms / 1000)
            if err is None:
                return (result, None, total_cost_ms)
            last_error = err
            if remaining_seconds <= 0:
                break
        return (None, last_error, total_cost_ms)
