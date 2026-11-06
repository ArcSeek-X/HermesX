"""B20：用边界反例约束策略审计，避免为去重改变缓存/并发语义。"""

from types import SimpleNamespace

import pytest

from data_provider.clients import stockdb
from data_provider.common import cache
from data_provider.common.rate_limit import RateLimitRegistry


@pytest.mark.parametrize("value", [None, False, [], {}, 0])
def test_cache_falsey_payload_is_not_a_miss_and_expiry_is_strict(value, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(cache, "time", SimpleNamespace(time=lambda: clock[0]))
    store = cache.SharedTtlCache()
    store.set("key", value, 2)
    assert store.get("key") is value
    clock[0] = 102.0
    assert store.get("key") is value
    clock[0] = 102.01
    assert store.get("key") is cache._MISS


def test_stockdb_fractional_ttl_is_not_equivalent_to_common_integer_ttl(monkeypatch):
    clock = [100.0]
    for module in (cache, stockdb):
        monkeypatch.setattr(module, "time", SimpleNamespace(time=lambda: clock[0]))
    local = stockdb._TtlCache()
    shared = cache.SharedTtlCache()
    local.set("key", "data", 1.9)
    shared.set("key", "data", 1.9)
    clock[0] = 101.5
    assert local.get("key") == "data"
    assert shared.get("key") is cache._MISS


def test_named_quota_keeps_first_capacity_and_releases_after_failure():
    registry = RateLimitRegistry()
    semaphore = registry.get("source", 1)
    assert registry.get("source", 20) is semaphore
    with pytest.raises(RuntimeError):
        with registry.guard("source"):
            assert semaphore.acquire(blocking=False) is False
            raise RuntimeError("fetch failed")
    assert semaphore.acquire(blocking=False)
    semaphore.release()


def test_retry_attempts_consume_one_budget_and_stop_when_exhausted(monkeypatch):
    from data_provider.runtime.manager import DataFetcherManager

    manager = DataFetcherManager(fetchers=[])
    monkeypatch.setattr(
        manager,
        "_get_fundamental_config",
        lambda: SimpleNamespace(fundamental_retry_max=5),
    )
    budgets = []

    def timeout(task, remaining, name):
        budgets.append(remaining)
        return None, "failed", 600

    monkeypatch.setattr(manager, "_run_with_timeout", timeout)
    assert manager._run_with_retry(lambda: None, 1.0, "probe") == (None, "failed", 1200)
    assert budgets == [1.0, 0.4]


def test_timeout_start_failure_returns_original_slot(monkeypatch):
    from data_provider.runtime import manager as base

    manager = base.DataFetcherManager(fetchers=[])
    semaphore = __import__("threading").BoundedSemaphore(1)
    monkeypatch.setattr(manager, "_fundamental_timeout_slots", semaphore)

    def start():
        raise RuntimeError("cannot start")

    monkeypatch.setattr(base, "Thread", lambda **kwargs: SimpleNamespace(start=start))
    result, error, _ = manager._run_with_timeout(lambda: "unused", 1, "probe")
    assert result is None
    assert error == "cannot start"
    assert semaphore.acquire(blocking=False)
    semaphore.release()
