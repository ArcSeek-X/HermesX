"""类型规范路径保持序列化、共享熔断状态与包导入顺序；旧内部路径退出。"""

import importlib
import pickle
import subprocess
import sys

import pytest

from data_provider.common import health
from data_provider.realtime import types


def test_realtime_consumers_share_canonical_types():
    from data_provider.realtime.akshare_source import UnifiedRealtimeQuote
    from data_provider.realtime.base import UnifiedRealtimeQuote as ManagerQuote
    assert UnifiedRealtimeQuote is types.UnifiedRealtimeQuote
    assert ManagerQuote is types.UnifiedRealtimeQuote
    from data_provider.realtime import RealtimeSource, RealtimeDataSourceManager
    from data_provider.realtime.base import RealtimeSource as Source, RealtimeDataSourceManager as Manager
    assert RealtimeSource is Source
    assert RealtimeDataSourceManager is Manager
    assert RealtimeSource is not types.RealtimeSource


@pytest.mark.parametrize("value", [
    types.RealtimeSource.TENCENT,
    types.UnifiedRealtimeQuote(code="AAPL", source=types.RealtimeSource.TENCENT, price=10, is_stale=False),
])
def test_pickle_payloads_use_canonical_module_and_round_trip(value):
    payload = pickle.dumps(value, protocol=0)
    assert b"data_provider.realtime.types" in payload
    restored = pickle.loads(payload)
    if isinstance(value, types.RealtimeSource):
        assert restored is value
    else:
        assert type(restored) is types.UnifiedRealtimeQuote
        assert restored.to_dict() == value.to_dict()


def test_health_registry_realtime_and_chip_keep_independent_shared_state(monkeypatch):
    realtime = health.get_realtime_circuit_breaker()
    chip = health.get_chip_circuit_breaker()
    registry = health.get_health_probe_registry()
    assert realtime is health.get_realtime_circuit_breaker()
    assert chip is health.get_chip_circuit_breaker()
    assert realtime is not chip
    for owner in (realtime, chip, registry):
        monkeypatch.setattr(owner, "_states", {})
    for _ in range(realtime.failure_threshold):
        realtime.record_failure("same-source")
    assert not health.get_realtime_circuit_breaker().is_available("same-source")
    assert chip.is_available("same-source")
    assert registry.can_try("same-source")
    for _ in range(chip.failure_threshold):
        chip.record_failure("same-source")
    realtime.reset("same-source")
    assert realtime.is_available("same-source")
    assert not chip.is_available("same-source")
    registry.mark_failure("same-source", "denied")
    assert registry.get_state("same-source").failure_count == 1
    assert realtime.get_status()["same-source"] == realtime.CLOSED


@pytest.mark.parametrize("first", [
    "data_provider.realtime.types", "data_provider.realtime.base",
    "data_provider.common.health", "data_provider.realtime",
])
def test_fresh_process_import_order_keeps_types_and_package_exports(first):
    # A fresh process is necessary: the parent process's loaded modules would hide cycles.
    script = f'''
import importlib
importlib.import_module({first!r})
from data_provider.realtime import types
from data_provider.common import health
from data_provider.realtime import RealtimeDataSourceManager, RealtimeSource
from data_provider.realtime.base import RealtimeDataSourceManager as Manager, RealtimeSource as Source
from data_provider.realtime.base import UnifiedRealtimeQuote
assert UnifiedRealtimeQuote is types.UnifiedRealtimeQuote
assert health.get_chip_circuit_breaker() is not health.get_realtime_circuit_breaker()
assert RealtimeDataSourceManager is Manager
assert RealtimeSource is Source
assert health.get_health_probe_registry().can_try("fresh-process")
'''
    result = subprocess.run([sys.executable, "-c", script], text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert not result.stdout


def test_realtime_package_unknown_attribute_remains_an_attribute_error():
    package = importlib.import_module("data_provider.realtime")
    with pytest.raises(AttributeError):
        getattr(package, "_not_a_public_capability")
