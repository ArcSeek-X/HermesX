# -*- coding: utf-8 -*-
"""Tests for the StockSDK bridge and provider sources."""

from __future__ import annotations

import importlib
from types import SimpleNamespace

# 先初始化 base 模块，保持与运行时 manager 初始化顺序一致，避免 source 直导时的循环依赖。
importlib.import_module("data_provider.code_search.base")
importlib.import_module("data_provider.kline.base")
importlib.import_module("data_provider.stock_info.base")
from data_provider.code_search.stocksdk_source import StockSdkCodeSearchSource
from data_provider.kline.base import KLineRequest
from data_provider.kline.stocksdk_source import StockSdkKLineSource
from data_provider.stock_info.stocksdk_source import StockSdkStockInfoSource
from data_provider.stocksdk_bridge import (
    StockSdkBridgeClient,
    StockSdkSettings,
    resolve_stocksdk_symbol,
)


def test_resolve_stocksdk_symbol_normalizes_cn_hk_and_us_codes() -> None:
    assert resolve_stocksdk_symbol("600519").symbol == "600519"
    assert resolve_stocksdk_symbol("HK700").symbol == "00700"
    assert resolve_stocksdk_symbol("00700").market == "hk"
    assert resolve_stocksdk_symbol("AAPL").market == "us"


def test_stocksdk_bridge_invokes_node_script(monkeypatch) -> None:
    calls = {}

    def fake_run(command, **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs
        return SimpleNamespace(
            returncode=0,
            stdout='{"ok": true, "data": {"pong": true}}',
            stderr="",
        )

    monkeypatch.setattr("data_provider.stocksdk_bridge.shutil.which", lambda _: "/usr/bin/node")
    monkeypatch.setattr("data_provider.stocksdk_bridge.subprocess.run", fake_run)

    client = StockSdkBridgeClient(
        StockSdkSettings(
            enabled=True,
            node_bin="node",
            bridge_entry="scripts/stocksdk_bridge/bridge.mjs",
            timeout_ms=8000,
            rate_limit_rps=3,
            kline_fallback=True,
        )
    )

    result = client.invoke("ping", {})

    assert result == {"pong": True}
    assert calls["command"][0] == "/usr/bin/node"
    assert calls["command"][1].endswith("scripts/stocksdk_bridge/bridge.mjs")
    assert '"action": "ping"' in calls["kwargs"]["input"]


def test_stocksdk_kline_source_normalizes_bridge_rows(monkeypatch) -> None:
    class FakeClient:
        def is_available(self):
            return True

        def fetch_kline(self, *_args, **_kwargs):
            return [
                {
                    "date": "20261001",
                    "open": 10.0,
                    "close": 11.0,
                    "high": 12.0,
                    "low": 9.5,
                    "volume": 1000,
                    "amount": 2000,
                    "changePercent": 5.0,
                    "prevClose": 10.5,
                    "name": "贵州茅台",
                },
                {
                    "date": "20261002",
                    "open": 11.0,
                    "close": 12.0,
                    "high": 12.5,
                    "low": 10.8,
                    "volume": 1100,
                    "amount": 2400,
                    "changePercent": 9.09,
                    "prevClose": 11.0,
                },
            ]

    monkeypatch.setattr("data_provider.kline.stocksdk_source.get_stocksdk_client", lambda: FakeClient())

    result = StockSdkKLineSource().fetch(KLineRequest(stock_code="600519", period="daily", limit=2))

    assert result is not None
    assert result.source == "stocksdk"
    assert result.stock_name == "贵州茅台"
    assert result.secid == "1.600519"
    assert result.data[-1]["close"] == 12.0


def test_stocksdk_stock_info_source_scales_cn_quote_units(monkeypatch) -> None:
    class FakeClient:
        def is_available(self):
            return True

        def fetch_quote(self, stock_code):
            assert stock_code == "600519"
            return {
                "name": "贵州茅台",
                "price": 1688.0,
                "change": 20.0,
                "changePercent": 1.2,
                "open": 1666.0,
                "prevClose": 1668.0,
                "high": 1699.0,
                "low": 1660.0,
                "volume": 123.0,
                "amount": 456.0,
                "turnoverRate": 1.5,
                "amplitude": 2.3,
                "peDynamic": 28.0,
                "totalMarketCap": 200.0,
                "circulatingMarketCap": 180.0,
            }

    monkeypatch.setattr("data_provider.stock_info.stocksdk_source.get_stocksdk_client", lambda: FakeClient())

    result = StockSdkStockInfoSource().fetch("600519")

    assert result is not None
    assert result.source == "stocksdk"
    assert result.current_price == 1688.0
    assert result.volume == 12300.0
    assert result.amount == 4560000.0
    assert result.total_market_cap == 200.0 * 1e8


def test_stocksdk_code_search_source_maps_search_results(monkeypatch) -> None:
    class FakeClient:
        def is_available(self):
            return True

        def search(self, query, limit=10):
            assert query == "茅台"
            assert limit == 5
            return [
                {"code": "sh600519", "name": "贵州茅台", "market": "sh"},
                {"code": "00700", "name": "腾讯控股", "market": "hk"},
                {"code": "AAPL", "name": "Apple", "market": "us"},
            ]

    monkeypatch.setattr("data_provider.code_search.stocksdk_source.get_stocksdk_client", lambda: FakeClient())

    results = StockSdkCodeSearchSource().search("茅台", limit=5)

    assert results is not None
    assert results[0].code == "600519"
    assert results[0].market == "SH"
    assert results[0].secid == "1.600519"
    assert results[1].code == "00700"
    assert results[1].market == "HK"
    assert results[2].code == "AAPL"
    assert results[2].market == "US"
