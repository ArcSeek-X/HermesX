# -*- coding: utf-8 -*-
"""Tests for the new data_provider-backed K-line services."""

from types import SimpleNamespace
from unittest.mock import patch

from data_provider.code_search import base as code_search_base
from data_provider.code_search.base import CodeSearchResult, search_codes
from data_provider.kline import base as kline_base
from data_provider.kline.base import KLineRequest, KLineResult, get_kline_data
from data_provider.stock_info import base as stock_info_base
from data_provider.stock_info.base import StockInfoResult, get_stock_info


def test_search_codes_returns_first_non_empty_source_result() -> None:
    local_result = [CodeSearchResult(code="600519", name="贵州茅台", market="SH", secid="1.600519", source="local")]
    code_search_base._MANAGER.cache.clear()
    with patch.object(code_search_base._MANAGER, "resolve_source_order", return_value=["local", "eastmoney"]):
        with patch.dict(code_search_base._MANAGER.sources, {
            "local": type("LocalSource", (), {
                "is_available": lambda self: True,
                "fetch": lambda self, request: local_result,
            })(),
            "eastmoney": type("EastMoneySource", (), {
                "is_available": lambda self: True,
                "fetch": lambda self, request: [],
            })(),
        }, clear=True):
            results = search_codes("贵州茅台")

    assert results == local_result


def test_get_kline_data_uses_configured_fallback_chain() -> None:
    expected = KLineResult(
        stock_code="600519",
        stock_name="贵州茅台",
        period="daily",
        secid="1.600519",
        prev_close=1660.0,
        source="eastmoney",
        data=[{"date": "2026-07-29", "open": 1, "close": 2, "high": 3, "low": 0}],
    )
    request = KLineRequest(stock_code="600519", period="daily", limit=10)

    kline_base._MANAGER.cache.clear()
    with patch.object(kline_base._MANAGER, "resolve_source_order", return_value=["local", "eastmoney"]):
        with patch.dict(kline_base._MANAGER.sources, {
            "local": type("LocalSource", (), {
                "is_available": lambda self: True,
                "fetch": lambda self, req: None,
            })(),
            "eastmoney": type("EastMoneySource", (), {
                "is_available": lambda self: True,
                "fetch": lambda self, req: expected,
            })(),
        }, clear=True):
            result = get_kline_data(request)

    assert result.source == "eastmoney"
    assert result.stock_name == "贵州茅台"


def test_get_stock_info_uses_first_available_source() -> None:
    expected = StockInfoResult(
        stock_code="600519",
        stock_name="贵州茅台",
        current_price=1690.0,
        source="local",
    )

    stock_info_base._MANAGER.cache.clear()
    with patch.object(stock_info_base._MANAGER, "resolve_source_order", return_value=["local", "eastmoney"]):
        with patch.dict(stock_info_base._MANAGER.sources, {
            "local": type("LocalSource", (), {
                "is_available": lambda self: True,
                "fetch": lambda self, code: expected,
            })(),
            "eastmoney": type("EastMoneySource", (), {
                "is_available": lambda self: True,
                "fetch": lambda self, code: None,
            })(),
        }, clear=True):
            result = get_stock_info("600519")

    assert result.source == "local"
    assert result.current_price == 1690.0


def test_kline_source_order_honors_primary_and_priority_settings() -> None:
    config = SimpleNamespace(
        kline_data_source="eastmoney",
        kline_fallback_enabled=True,
        kline_source_priority="local,sina,eastmoney,tencent",
    )

    with patch("data_provider.common.base.get_config", return_value=config):
        assert list(kline_base.resolve_kline_source_order()) == ["eastmoney", "local", "sina", "tencent"]


def test_stockinfo_source_order_can_disable_fallback() -> None:
    config = SimpleNamespace(
        stockinfo_data_source="eastmoney",
        stockinfo_fallback_enabled=False,
        stockinfo_source_priority="local,eastmoney",
    )

    with patch("data_provider.common.base.get_config", return_value=config):
        assert list(stock_info_base.resolve_stock_info_source_order()) == ["eastmoney"]


def test_codesearch_source_order_keeps_legacy_comma_separated_value() -> None:
    config = SimpleNamespace(
        codesearch_data_source="eastmoney,local",
        codesearch_fallback_enabled=True,
        codesearch_source_priority="local,eastmoney",
    )

    with patch("data_provider.common.base.get_config", return_value=config):
        assert list(code_search_base.resolve_code_search_source_order()) == ["eastmoney", "local"]
