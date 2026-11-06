"""实时职责拆分保留时间语义、扩展点、共享缓存与真实串行调用锁。"""

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event, RLock
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from data_provider.runtime.manager import DataFetcherManager
from data_provider.realtime.types import UnifiedRealtimeQuote
from data_provider.runtime.fetchers.tickflow import TickFlowFetcher


@pytest.mark.parametrize(
    "provider,ttl,seconds,stale",
    [
        (None, 10, None, None),
        ("invalid", 10, None, None),
        ("2026-01-01T08:00:00+08:00", 10, 10, False),
        ("2026-01-01T00:00:00Z", 9, 10, True),
        ("2026-01-01T00:00:11", 0, 0, False),
    ],
)
def test_manager_enrichment_uses_original_clock_override_and_timestamp_boundaries(provider, ttl, seconds, stale):
    manager = DataFetcherManager.__new__(DataFetcherManager)
    manager._utc_now_iso = lambda: "2026-01-01T00:00:10+00:00"
    quote = UnifiedRealtimeQuote(code="AAPL", price=10, provider_timestamp=provider)
    result = manager._enrich_realtime_quote(quote, fallback_from="primary", realtime_cache_ttl=ttl)
    assert result is quote
    assert quote.fetched_at == "2026-01-01T00:00:10+00:00"
    assert quote.fallback_from == "primary"
    assert quote.stale_seconds == seconds
    assert quote.is_stale is stale
    if seconds is None:
        assert quote.provider_timestamp is None
    else:
        assert quote.provider_timestamp.endswith("+00:00")


def test_supplement_uses_subclass_field_policy_and_preserves_zero_and_primary_price():
    class CustomManager(DataFetcherManager):
        _SUPPLEMENT_FIELDS = ["volume"]

    primary = UnifiedRealtimeQuote(code="AAPL", price=10)
    secondary = UnifiedRealtimeQuote(code="AAPL", price=20, volume=0)
    manager = CustomManager.__new__(CustomManager)
    manager._try_fetcher_quote = Mock(return_value=secondary)
    assert manager._supplement_quote("AAPL", primary, "secondary", source="custom") is primary
    manager._try_fetcher_quote.assert_called_once_with("AAPL", "secondary", source="custom")
    assert primary.price == 10
    assert primary.volume == 0
    assert not manager._quote_needs_supplement(primary)
    CustomManager._SUPPLEMENT_FIELDS.append("pe_ratio")
    assert manager._quote_needs_supplement(primary)


def test_prefetch_and_quote_still_serialize_on_same_real_fetcher_lock(monkeypatch):
    import src.config

    config = SimpleNamespace(
        prefetch_realtime_quotes=True,
        enable_realtime_quote=True,
        realtime_source_priority="tickflow",
        tickflow_batch_size=3,
        realtime_cache_ttl=600,
    )
    monkeypatch.setattr(src.config, "get_config", lambda: config)
    entered, release, second_attempt = Event(), Event(), Event()
    order = []

    class Fetcher:
        name, priority = "TickFlowFetcher", 1

        def prefetch_realtime_quotes(self, codes, batch_size=None):
            order.append(("prefetch", codes, batch_size))
            entered.set()
            assert release.wait(timeout=5)
            order.append("prefetch-done")
            return len(codes)

        def get_realtime_quote(self, code):
            order.append("quote")
            return UnifiedRealtimeQuote(
                code=code,
                price=10,
                volume_ratio=1,
                turnover_rate=1,
                pe_ratio=1,
                pb_ratio=1,
                total_mv=1,
                circ_mv=1,
                amplitude=1,
            )

    class ObservedLock:
        def __init__(self):
            self.lock = RLock()
            self.attempts = 0

        def __enter__(self):
            self.attempts += 1
            if self.attempts == 2:
                second_attempt.set()
            self.lock.acquire()

        def __exit__(self, *_):
            self.lock.release()

    fetcher = Fetcher()
    manager = DataFetcherManager(fetchers=[fetcher])
    lock = ObservedLock()
    manager._fetcher_call_locks[id(fetcher)] = lock
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(manager.prefetch_realtime_quotes, ["SH600519"] * 5)
        try:
            assert entered.wait(timeout=5)
            second = pool.submit(manager.get_realtime_quote, "600519")
            assert second_attempt.wait(timeout=5)
            assert order == [("prefetch", ["600519"] * 5, 3)]
        finally:
            release.set()
        assert first.result(timeout=5) == 5
        assert second.result(timeout=5).price == 10
    assert order[-2:] == ["prefetch-done", "quote"]
    assert manager._get_fetcher_call_lock(fetcher) is lock


def test_akshare_realtime_and_snapshot_read_same_current_module_cache(monkeypatch):
    from data_provider.runtime.fetchers import akshare as module
    from data_provider.common.health import CircuitBreaker

    monkeypatch.setattr(module, "get_config", lambda: SimpleNamespace(enable_eastmoney_patch=False))
    breaker = CircuitBreaker()
    monkeypatch.setattr(module, "get_realtime_circuit_breaker", lambda: breaker)
    download = Mock(side_effect=AssertionError("cached quotes must not request the SDK"))
    monkeypatch.setitem(sys.modules, "akshare", SimpleNamespace(stock_zh_a_spot_em=download))
    frame = pd.DataFrame({"代码": ["600519"], "名称": ["sample"], "最新价": [10]})
    monkeypatch.setattr(module, "_realtime_cache", {"data": frame, "timestamp": time.time(), "ttl": 1200})
    first = module.AkshareFetcher(sleep_min=0, sleep_max=0)
    second = module.AkshareFetcher(sleep_min=0, sleep_max=0)
    source = first._realtime_source()
    assert first.get_realtime_quote("600519").price == 10
    assert second.get_realtime_quote_snapshot() is frame
    replacement = frame.assign(最新价=20)
    monkeypatch.setattr(module, "_realtime_cache", {"data": replacement, "timestamp": time.time(), "ttl": 1200})
    assert source.get_stock_realtime_quote_em("600519").price == 20
    assert second.get_realtime_quote_snapshot() is replacement
    download.assert_not_called()


def test_tickflow_prefetch_name_and_quote_share_client_cache_and_conversion():
    quote = {"symbol": "600519.SH", "name": "sample", "last_price": 10, "volume": 2, "ext": {"change_pct": 0.05}}
    get = Mock(return_value=[quote])
    close = Mock()
    fetcher = TickFlowFetcher(api_key="test-key")
    client = SimpleNamespace(quotes=SimpleNamespace(get=get), close=close)
    fetcher._client = client
    try:
        assert fetcher.prefetch_realtime_quotes(["600519"]) == 1
        assert fetcher.get_stock_name("600519") == "sample"
        result = fetcher.get_realtime_quote("600519")
        assert result.price == 10
        assert result.volume == 200
        assert result.change_pct == 5
        get.assert_called_once_with(symbols=["600519.SH"])
        assert fetcher._client is client
    finally:
        fetcher.close()
    close.assert_called_once_with()


@pytest.mark.parametrize("first", ["akshare", "tickflow"])
def test_concrete_realtime_source_import_does_not_construct_default_manager(first):
    import subprocess

    script = f"""
import importlib
import sys
importlib.import_module("data_provider.realtime.{first}_source")
assert "data_provider.realtime.base" not in sys.modules
from data_provider.realtime.source_contract import RealtimeSource as Contract
from data_provider.realtime.base import RealtimeSource, _MANAGER
assert RealtimeSource is Contract
assert set(_MANAGER.sources) == {{"tickflow", "tencent", "akshare_sina", "akshare_em"}}
"""
    result = subprocess.run([sys.executable, "-c", script], text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
