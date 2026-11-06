"""真实诊断实现下验证数据源转发、脱敏与跨线程 trace 隔离。"""

from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
import subprocess
import sys
from unittest.mock import patch

import pytest

from data_provider.common import diagnostics
from src.application.runtime.run_diagnostics import (
    activate_run_diagnostic_context,
    current_diagnostic_snapshot,
    get_current_diagnostic_context,
    reset_run_diagnostic_context,
)
from tests.support.paths import get_repo_root


def emit(success=True):
    diagnostics.record_provider_run_started(data_type="daily", provider="TencentFetcher", operation="daily")
    diagnostics.record_provider_run(
        data_type="daily", provider="TencentFetcher", operation="daily", success=success,
        latency_ms=19, error_type=None if success else "TimeoutError",
        error_message=None if success else "token=private-value", fallback_from="primary",
        fallback_to="TencentFetcher", cache_hit=False, stale_seconds=3, record_count=8,
    )


@pytest.mark.parametrize("success", [True, False])
def test_provider_events_keep_fields_redaction_and_start_completion_pair(success):
    events = []
    token = activate_run_diagnostic_context(trace_id="provider-trace", event_sink=events.append)
    try:
        emit(success)
        snapshot = current_diagnostic_snapshot()
    finally:
        reset_run_diagnostic_context(token)
    run, = snapshot["provider_runs"]
    assert run["trace_id"] == "provider-trace"
    assert run["provider"] == "TencentFetcher"
    assert run["operation"] == "daily"
    assert run["success"] is success
    assert run["latency_ms"] == 19
    assert run["fallback_from"] == "primary"
    assert run["fallback_to"] == "TencentFetcher"
    assert run["cache_hit"] is False
    assert run["stale_seconds"] == 3
    assert run["record_count"] == 8
    if not success:
        assert run["error_type"] == "TimeoutError"
        assert "private-value" not in run["error_message_sanitized"]
    assert len(events) == 2
    assert events[0]["type"] == "provider_run_started"
    assert events[0]["node_id"] == events[1]["node_id"]


def test_copied_worker_context_and_untraced_worker_do_not_share_trace():
    token = activate_run_diagnostic_context(trace_id="parent-trace")
    try:
        copied = copy_context()
        with ThreadPoolExecutor(max_workers=2) as pool:
            pool.submit(emit).result(timeout=5)
            assert current_diagnostic_snapshot()["provider_runs"] == []
            pool.submit(copied.run, emit).result(timeout=5)
        run, = current_diagnostic_snapshot()["provider_runs"]
        assert run["trace_id"] == "parent-trace"
    finally:
        reset_run_diagnostic_context(token)


def test_nested_trace_reset_restores_parent_recorder_context():
    parent = activate_run_diagnostic_context(trace_id="parent")
    try:
        child = activate_run_diagnostic_context(trace_id="child")
        try:
            emit()
            assert current_diagnostic_snapshot()["provider_runs"][0]["trace_id"] == "child"
        finally:
            reset_run_diagnostic_context(child)
        assert current_diagnostic_snapshot()["provider_runs"] == []
        emit()
        assert current_diagnostic_snapshot()["provider_runs"][0]["trace_id"] == "parent"
    finally:
        reset_run_diagnostic_context(parent)
    emit()
    assert current_diagnostic_snapshot() is None


def test_recording_failure_keeps_existing_fail_open_behavior(caplog):
    token = activate_run_diagnostic_context(trace_id="fail-open")
    try:
        context = get_current_diagnostic_context()
        with patch.object(context, "record_provider_run", side_effect=RuntimeError("recorder unavailable")):
            emit()
        assert "provider diagnostic record failed" in caplog.text
    finally:
        reset_run_diagnostic_context(token)


def test_fresh_library_process_binds_on_trace_activation_without_bootstrap():
    script = '''
from data_provider.common.diagnostics import record_provider_run
from src.application.runtime.provider_diagnostic_ports import provider_diagnostic_callbacks
assert provider_diagnostic_callbacks() is None
record_provider_run(data_type="daily", provider="test", operation="daily", success=True)
from src.application.runtime.run_diagnostics import (
    activate_run_diagnostic_context, reset_run_diagnostic_context, current_diagnostic_snapshot,
)
token = activate_run_diagnostic_context(trace_id="library")
try:
    record_provider_run(data_type="daily", provider="test", operation="daily", success=True)
    assert current_diagnostic_snapshot()["provider_runs"][0]["trace_id"] == "library"
finally:
    reset_run_diagnostic_context(token)
'''
    subprocess.run([sys.executable, "-c", script], cwd=get_repo_root(), check=True,
                   capture_output=True, text=True, timeout=30)


def test_simultaneous_threads_keep_separate_diagnostic_contexts():
    from threading import Barrier

    barrier = Barrier(2)

    def traced_worker(trace_id):
        token = activate_run_diagnostic_context(trace_id=trace_id)
        try:
            barrier.wait(timeout=5)
            emit()
            run, = current_diagnostic_snapshot()["provider_runs"]
            return run["trace_id"]
        finally:
            reset_run_diagnostic_context(token)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(traced_worker, "first-thread")
        second = pool.submit(traced_worker, "second-thread")
        assert first.result(timeout=10) == "first-thread"
        assert second.result(timeout=10) == "second-thread"
