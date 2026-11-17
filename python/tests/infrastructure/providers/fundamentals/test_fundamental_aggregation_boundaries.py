"""独立聚合实现保留旧导出、动态资源、缓存预算隔离和导入边界。"""

import importlib
import pickle
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from data_provider.runtime.manager import DataFetcherManager


@pytest.mark.parametrize("module,classname,manager_attribute", [
    ("akshare_source", "AkshareFundamentalAdapter", "_fundamental_adapter"),
    ("yfinance_source", "YfinanceFundamentalAdapter", "_yfinance_fundamental_adapter"),
])
def test_manager_uses_canonical_adapter_and_class_round_trips(module, classname, manager_attribute):
    canonical = importlib.import_module("data_provider.fundamentals." + module)
    cls = getattr(canonical, classname)
    owner = DataFetcherManager(fetchers=[SimpleNamespace(name="unused", priority=1)])
    assert type(getattr(owner, manager_attribute)) is cls
    assert pickle.loads(pickle.dumps(cls)) is cls


def test_bound_aggregation_reads_current_adapter_and_shares_facade_budget_cache(monkeypatch):
    import src.config

    cfg = SimpleNamespace(
        enable_fundamental_pipeline=True,
        fundamental_cache_ttl_seconds=60,
        fundamental_stage_timeout_seconds=2,
        fundamental_fetch_timeout_seconds=1,
        fundamental_retry_max=1,
        fundamental_cache_max_entries=256,
    )
    owner = DataFetcherManager(fetchers=[SimpleNamespace(name="unused", priority=1)])
    old_bundle = Mock(side_effect=AssertionError("stale adapter must not run"))
    old_quote = Mock(side_effect=AssertionError("stale quote method must not run"))
    owner._yfinance_fundamental_adapter = SimpleNamespace(get_fundamental_bundle=old_bundle)
    owner.get_realtime_quote = old_quote
    aggregation = owner._fundamental_source()
    bundle = {
        "status": "ok",
        "growth": {"revenue_yoy": 1},
        "earnings": {"financial_report": {"revenue": 100}},
        "belong_boards": [],
        "source_chain": [],
        "errors": [],
    }
    current_bundle = Mock(return_value=bundle)
    current_quote = Mock(return_value=None)
    owner._yfinance_fundamental_adapter = SimpleNamespace(get_fundamental_bundle=current_bundle)
    owner.get_realtime_quote = current_quote
    monkeypatch.setattr(src.config, "get_config", lambda: cfg)
    first = aggregation.get_fundamental_context("AAPL", budget_seconds=1)
    assert owner.get_fundamental_context("AAPL", budget_seconds=1) is first
    assert current_bundle.call_count == 1
    assert current_quote.call_count == 1
    second = owner.get_fundamental_context("AAPL", budget_seconds=2)
    assert second is not first
    assert current_bundle.call_count == 2
    assert len(owner._fundamental_cache) == 2
    assert aggregation.current_fundamental_cache() is owner._fundamental_cache
    assert aggregation.current_fundamental_cache_lock() is owner._fundamental_cache_lock
    old_bundle.assert_not_called()
    old_quote.assert_not_called()


@pytest.mark.parametrize("first", ["akshare_source", "yfinance_source", "aggregate", "tushare_source"])
def test_fundamental_leaf_import_does_not_construct_default_capability_manager(first):
    script = f"""
import importlib
import sys
importlib.import_module("data_provider.fundamentals.{first}")
assert "data_provider.fundamentals.base" not in sys.modules
from data_provider.fundamentals import FundamentalsRequest
from data_provider.fundamentals.base import FundamentalsRequest as Request, _MANAGER
from data_provider.fundamentals.aggregate import FundamentalAggregation
assert FundamentalsRequest is Request
assert set(_MANAGER.sources) == {{"tushare"}}
assert isinstance(_MANAGER.sources["tushare"]._context_loader.__self__, FundamentalAggregation)
"""
    result = subprocess.run([sys.executable, "-c", script], text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("kind", ["FundamentalsRequest", "FundamentalsResult"])
def test_old_fundamental_contract_pickle_payloads_still_load(kind):
    from data_provider.fundamentals import source_contract as contract
    from data_provider.fundamentals import base

    cls = getattr(contract, kind)
    value = (
        cls("AAPL", budget_seconds=1.25)
        if kind == "FundamentalsRequest"
        else cls(
            "AAPL",
            {"status": "partial"},
            source="tushare",
            metadata={"budget_seconds": 1.25},
        )
    )
    assert getattr(base, kind) is cls
    payload = pickle.dumps(value, protocol=0).replace(
        b"data_provider.fundamentals.source_contract",
        b"data_provider.fundamentals.base",
    )
    restored = pickle.loads(payload)
    assert type(restored) is cls
    assert restored == value
