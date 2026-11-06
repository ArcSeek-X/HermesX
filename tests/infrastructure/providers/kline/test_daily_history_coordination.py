"""日线职责提取后，真实锁、熔断、诊断和字段清洗仍遵守原契约。"""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
import time

import pandas as pd
from pandas.testing import assert_frame_equal

from data_provider.runtime.manager import DataFetcherManager
from data_provider.kline.daily_normalize import clean_daily_data
from data_provider.common.health import CircuitBreaker
from src.application.runtime.run_diagnostics import (
    activate_run_diagnostic_context,
    current_diagnostic_snapshot,
    reset_run_diagnostic_context,
)


class DailyFetcher:
    name = "NextForRouting"
    priority = 1

    def __init__(self):
        self.calls = []

    def get_daily_data(self, stock_code, start_date=None, end_date=None, days=30):
        self.calls.append((stock_code, start_date, end_date, days))
        return pd.DataFrame({"date": ["2026-01-01"], "close": [1.0], "volume": [10]})


def test_daily_cleaning_keeps_input_untouched_and_drops_invalid_required_values():
    original = pd.DataFrame({
        "date": ["2026-01-02", "2026-01-01", "2026-01-03"],
        "close": ["2", "1", "invalid"], "volume": ["20", "10", "invalid"],
    })
    before = original.copy(deep=True)
    result = clean_daily_data(original)
    assert_frame_equal(original, before)
    assert result["close"].tolist() == [1.0, 2.0]
    assert result["volume"].tolist() == [10.0, 20.0]
    assert result["date"].dt.strftime("%Y-%m-%d").tolist() == ["2026-01-01", "2026-01-02"]
    assert result.index.tolist() == [0, 1]


def test_daily_route_uses_the_same_manager_owned_fetcher_lock_for_parallel_requests():
    entry = Barrier(2)
    guard = Lock()
    active = 0
    maximum = 0

    class BlockingFetcher(DailyFetcher):
        name = "SerializedDailyFetcher"

        def get_daily_data(self, *args, **kwargs):
            nonlocal active, maximum
            with guard:
                active += 1
                maximum = max(maximum, active)
            try:
                time.sleep(0.02)
                return super().get_daily_data(*args, **kwargs)
            finally:
                with guard:
                    active -= 1

    fetcher = BlockingFetcher()
    manager = DataFetcherManager(fetchers=[fetcher])
    original_lock = manager._get_fetcher_call_lock(fetcher)

    def request(code):
        entry.wait(timeout=5)
        return manager.get_daily_data(code, start_date="2026-01-01", end_date="2026-01-02", days=2)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(request, "SH600519")
        second = pool.submit(request, "SZ000001")
        assert first.result(timeout=10)[1] == fetcher.name
        assert second.result(timeout=10)[1] == fetcher.name
    assert maximum == 1
    assert manager._get_fetcher_call_lock(fetcher) is original_lock
    assert sorted(fetcher.calls) == [
        ("000001", "2026-01-01", "2026-01-02", 2),
        ("600519", "2026-01-01", "2026-01-02", 2),
    ]


def test_daily_fallback_keeps_health_state_between_requests_and_records_real_attempts(monkeypatch):
    monkeypatch.setattr(DataFetcherManager, "_daily_source_health", CircuitBreaker(
        failure_threshold=1, cooldown_seconds=300,
    ))

    class FailedFetcher(DailyFetcher):
        name = "FailureForRouting"
        priority = 0

        def get_daily_data(self, *args, **kwargs):
            self.calls.append(args)
            raise TimeoutError("daily source timed out")

    failed = FailedFetcher()
    successful = DailyFetcher()
    manager = DataFetcherManager(fetchers=[failed, successful])
    token = activate_run_diagnostic_context(trace_id="daily-health")
    try:
        assert manager.get_daily_data("600519")[1] == successful.name
        assert manager.get_daily_data("600519")[1] == successful.name
        attempts = current_diagnostic_snapshot()["provider_runs"]
    finally:
        reset_run_diagnostic_context(token)
    assert len(failed.calls) == 1
    assert len(successful.calls) == 2
    assert [x["provider"] for x in attempts] == [failed.name, successful.name, successful.name]
    assert [x["success"] for x in attempts] == [False, True, True]
    assert attempts[0]["fallback_to"] == successful.name
    assert attempts[0]["error_type"] == "TimeoutError"
    assert {x["trace_id"] for x in attempts} == {"daily-health"}
