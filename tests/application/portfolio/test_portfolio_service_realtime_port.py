# -*- coding: utf-8 -*-
# 本文件主要测试：持仓快照实时行情取数端口（S2f-3）的降级与适配器语义
"""Tests for PortfolioService realtime quote port (S2f-3).

Covers:
- 未装配端口 → _fetch_realtime_position_price 优雅降级为 (None, None)
- 端口透传有效价；price <=0 / 非数值 / quote None / 取数异常 → (None, None)（与迁移前一致）
- set_realtime_port 幂等：传 None 保持既有指向
- _prefetch_realtime_position_prices：>=5 只时调用端口 bulk prefetch；未装配→ no-op 不抛
- 适配器 DataProviderPortfolioRealtimeQuote：quote None→None、对象→(price, provider)、
  异常上抛（由用例降级）、prefetch 调用 manager 一次
- configure_portfolio_service_realtime 装配指向适配器
"""

from __future__ import annotations

import pytest

import data_provider.base as dp_base
from src.application.portfolio import portfolio_service as ps
from src.application.portfolio.portfolio_service import PortfolioService
from src.infrastructure.providers.portfolio_realtime_provider import (
    DataProviderPortfolioRealtimeQuote,
)


@pytest.fixture(autouse=True)
def _isolate_module_port(monkeypatch):
    """每个用例前后把模块级端口指向复位为 None，避免装配状态互相泄漏。"""
    monkeypatch.setattr(ps, "_realtime_port", None)
    yield
    monkeypatch.setattr(ps, "_realtime_port", None)


class _FakePort:
    def __init__(self, fetched=None, raises=False):
        self._fetched = fetched
        self._raises = raises
        self.prefetched = None

    def prefetch_quotes(self, *, codes):
        self.prefetched = list(codes)

    def fetch_price_and_source(self, *, code):
        if self._raises:
            raise RuntimeError("source down")
        return self._fetched


# ---------------------------------------------------------------------------
# 用例侧：单票取价降级矩阵 + 幂等
# ---------------------------------------------------------------------------

def test_unconfigured_fetch_degrades_none():
    assert PortfolioService._fetch_realtime_position_price("600519") == (None, None)


def test_fetch_valid_passthrough():
    ps.set_realtime_port(_FakePort(fetched=(12.5, "east_money")))
    assert PortfolioService._fetch_realtime_position_price("600519") == (12.5, "east_money")


@pytest.mark.parametrize(
    "fetched",
    [(0.0, "x"), (-1.0, "x"), ("not-a-number", "x"), (None, "x")],
)
def test_fetch_invalid_price_degrades_none(fetched):
    ps.set_realtime_port(_FakePort(fetched=fetched))
    assert PortfolioService._fetch_realtime_position_price("600519") == (None, None)


def test_fetch_none_quote_degrades_none():
    ps.set_realtime_port(_FakePort(fetched=None))
    assert PortfolioService._fetch_realtime_position_price("600519") == (None, None)


def test_fetch_exception_degrades_none():
    ps.set_realtime_port(_FakePort(raises=True))
    assert PortfolioService._fetch_realtime_position_price("600519") == (None, None)


def test_setter_idempotent_none_keeps_existing():
    ps.set_realtime_port(_FakePort(fetched=(9.9, "src")))
    ps.set_realtime_port(None)  # 传 None 不覆盖既有指向
    assert PortfolioService._fetch_realtime_position_price("600519") == (9.9, "src")


# ---------------------------------------------------------------------------
# 用例侧：bulk prefetch
# ---------------------------------------------------------------------------

def test_prefetch_calls_port_when_configured():
    port = _FakePort(fetched=(1.0, "src"))
    ps.set_realtime_port(port)
    svc = PortfolioService.__new__(PortfolioService)
    symbols = [f"60000{i}" for i in range(6)]
    svc._prefetch_realtime_position_prices(symbols)
    assert port.prefetched == sorted(symbols)


def test_prefetch_unconfigured_is_noop_no_raise():
    svc = PortfolioService.__new__(PortfolioService)
    symbols = [f"60000{i}" for i in range(6)]
    # 未装配端口：bulk 跳过、单票降级为 (None, None)，整体不抛
    result = svc._prefetch_realtime_position_prices(symbols)
    assert set(result.keys()) == set(symbols)
    assert all(v == (None, None) for v in result.values())


# ---------------------------------------------------------------------------
# 适配器 best-effort 语义（异常上抛由用例降级）
# ---------------------------------------------------------------------------

def _patch_manager(monkeypatch, manager):
    monkeypatch.setattr(dp_base, "DataFetcherManager", manager, raising=False)


def test_adapter_quote_none_returns_none(monkeypatch):
    class _M:
        def get_realtime_quote(self, code, *, log_final_failure=True):
            return None

    _patch_manager(monkeypatch, _M)
    assert DataProviderPortfolioRealtimeQuote().fetch_price_and_source(code="600519") is None


def test_adapter_extracts_price_and_provider(monkeypatch):
    class _Src:
        value = "east_money"

    class _Quote:
        price = 8.88
        source = _Src()

    class _M:
        def get_realtime_quote(self, code, *, log_final_failure=True):
            assert log_final_failure is False  # 适配器保持源侧末次失败不告警
            return _Quote()

    _patch_manager(monkeypatch, _M)
    assert DataProviderPortfolioRealtimeQuote().fetch_price_and_source(code="600519") == (
        8.88,
        "east_money",
    )


def test_adapter_source_without_value_falls_back_str(monkeypatch):
    class _Quote:
        price = 5.0
        source = "raw_src"  # 无 .value → str(source)

    class _M:
        def get_realtime_quote(self, code, *, log_final_failure=True):
            return _Quote()

    _patch_manager(monkeypatch, _M)
    assert DataProviderPortfolioRealtimeQuote().fetch_price_and_source(code="600519") == (
        5.0,
        "raw_src",
    )


def test_adapter_exception_propagates(monkeypatch):
    class _M:
        def get_realtime_quote(self, code, *, log_final_failure=True):
            raise RuntimeError("down")

    _patch_manager(monkeypatch, _M)
    with pytest.raises(RuntimeError):
        DataProviderPortfolioRealtimeQuote().fetch_price_and_source(code="600519")


def test_adapter_prefetch_invokes_manager_once(monkeypatch):
    calls = {}

    class _M:
        def prefetch_realtime_quotes(self, codes):
            calls["codes"] = list(codes)
            return len(calls["codes"])

    _patch_manager(monkeypatch, _M)
    DataProviderPortfolioRealtimeQuote().prefetch_quotes(codes=["600000", "600001"])
    assert calls["codes"] == ["600000", "600001"]


# ---------------------------------------------------------------------------
# 装配入口
# ---------------------------------------------------------------------------

def test_configure_wires_realtime_adapter():
    from src.bootstrap.portfolio import configure_portfolio_service_realtime

    configure_portfolio_service_realtime()
    assert isinstance(ps._get_realtime_port(), DataProviderPortfolioRealtimeQuote)
