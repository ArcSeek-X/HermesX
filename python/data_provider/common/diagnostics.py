"""数据源诊断转发；只依赖应用侧端口，不导入具体诊断服务。

activate_run_diagnostic_context 在创建 trace 前绑定回调，确保直接库调用也不漏事件。
此模块不保存 trace，也不创建第二份 ContextVar 或异常/脱敏实现。
"""

from typing import Any, Optional

from src.application.runtime.provider_diagnostic_ports import provider_diagnostic_callbacks


def record_provider_run(
    *,
    data_type: str,
    provider: str,
    operation: str,
    success: bool,
    latency_ms: Optional[int] = None,
    error_type: Optional[str] = None,
    error_message: Optional[Any] = None,
    fallback_from: Optional[str] = None,
    fallback_to: Optional[str] = None,
    cache_hit: Optional[bool] = None,
    stale_seconds: Optional[int] = None,
    record_count: Optional[int] = None,
) -> None:
    """转发诊断事件；字段、脱敏和 ContextVar 语义由原记录器保持。"""
    callbacks = provider_diagnostic_callbacks()
    if callbacks is None:
        # 无 trace 激活时的普通取数，沿用原诊断函数的不记录语义。
        return
    callbacks.finished(
        data_type=data_type,
        provider=provider,
        operation=operation,
        success=success,
        latency_ms=latency_ms,
        error_type=error_type,
        error_message=error_message,
        fallback_from=fallback_from,
        fallback_to=fallback_to,
        cache_hit=cache_hit,
        stale_seconds=stale_seconds,
        record_count=record_count,
    )


def record_provider_run_started(*, data_type: str, provider: str, operation: str) -> None:
    """转发诊断事件；字段、脱敏和 ContextVar 语义由原记录器保持。"""
    callbacks = provider_diagnostic_callbacks()
    if callbacks is None:
        # 无 trace 激活时的普通取数，沿用原诊断函数的不记录语义。
        return
    callbacks.started(
        data_type=data_type,
        provider=provider,
        operation=operation,
    )
