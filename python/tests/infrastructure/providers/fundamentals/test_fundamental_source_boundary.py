"""基本面 Source 不回调可能委托新能力的旧门面，保持原门控及 payload。"""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from data_provider.runtime.manager import DataFetcherManager
from data_provider.common.health import HealthProbeRegistry
from data_provider.fundamentals.base import (
    FundamentalsDataSourceManager,
    FundamentalsRequest,
)
from data_provider.fundamentals.tushare_source import TushareFundamentalsSource


@pytest.mark.parametrize("budget", [0.0, 1.25])
def test_source_preserves_loader_budget_payload_and_source_metadata(budget):
    payload = {"status": "partial", "valuation": {"data": {"pe_ratio": 12}}}
    loader = Mock(return_value=payload)
    source = TushareFundamentalsSource(context_loader=loader)
    result = source.fetch(FundamentalsRequest("600519", budget_seconds=budget))
    loader.assert_called_once_with("600519", budget_seconds=budget)
    assert result.payload is payload
    assert result.stock_code == "600519"
    assert result.source == "tushare"
    assert result.metadata == {"budget_seconds": budget}


def test_source_preserves_empty_payload_and_does_not_swallow_loader_failure():
    source = TushareFundamentalsSource(context_loader=lambda *args, **kwargs: {})
    assert source.fetch(FundamentalsRequest("600519")) is None
    failure = TimeoutError("fundamental budget exhausted")
    source = TushareFundamentalsSource(context_loader=Mock(side_effect=failure))
    with pytest.raises(TimeoutError) as caught:
        source.fetch(FundamentalsRequest("600519"))
    assert caught.value is failure


@pytest.mark.parametrize("token, available", [("", False), ("configured", True)])
def test_tushare_configuration_gate_remains_unchanged(monkeypatch, token, available):
    monkeypatch.setattr("data_provider.fundamentals.tushare_source.get_config",
                        lambda: SimpleNamespace(tushare_token=token))
    source = TushareFundamentalsSource(context_loader=Mock())
    assert source.is_available() is available


def test_facade_can_delegate_to_capability_without_source_calling_back(monkeypatch):
    # 全部使用真实聚合叶实现和能力 Manager；仅隔离无关 SDK 构造及外部请求。
    config = SimpleNamespace(tushare_token="configured", enable_fundamental_pipeline=False)
    monkeypatch.setattr("src.config.get_config", lambda: config)
    monkeypatch.setattr("data_provider.fundamentals.tushare_source.get_config", lambda: config)
    monkeypatch.setattr(DataFetcherManager, "_init_default_fetchers", lambda self: None)
    source = TushareFundamentalsSource()
    capability = FundamentalsDataSourceManager(
        sources={"tushare": source}, default_source_order=["tushare"],
        data_source_key="fundamentals_data_source",
        source_priority_key="fundamentals_source_priority",
        fallback_enabled_key="fundamentals_fallback_enabled",
        cache_ttl_seconds=0, health_registry=HealthProbeRegistry(),
    )

    entry_calls = 0

    def delegated(self, stock_code, budget_seconds=None):
        nonlocal entry_calls
        entry_calls += 1
        assert entry_calls == 1, "Source called the facade recursively"
        return capability.get_fundamentals(
            FundamentalsRequest(stock_code, budget_seconds=budget_seconds)
        ).payload

    # 模拟后续旧门面转接新能力的最终入口，旧代码在这里会产生递归调用。
    monkeypatch.setattr(DataFetcherManager, "get_fundamental_context", delegated)
    result = DataFetcherManager().get_fundamental_context("600519", budget_seconds=0.25)
    assert entry_calls == 1
    assert result["market"] == "cn"
    assert result["status"] == "not_supported"
    assert result["errors"] == ["fundamental pipeline disabled"]
    assert set(result["coverage"]) == {
        "valuation", "growth", "earnings", "institution", "capital_flow", "dragon_tiger", "boards",
    }
