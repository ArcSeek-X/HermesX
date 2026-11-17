# -*- coding: utf-8 -*-
# 本文件主要测试：持仓风险用例板块归属取数端口（S2f-2）的降级与适配器语义
"""Tests for PortfolioRiskService belong-boards port (S2f-2).

Covers:
- 未装配端口 → _fetch_belong_boards 优雅降级为空列表（等价迁移前 DataFetcherManager 初始化失败）
- 端口透传 / 异常降级 / 非 list 归一为空
- set_belong_boards_port 幂等：传 None 保持既有指向
- 适配器 DataProviderPortfolioBelongBoards best-effort：可用透传、调用异常/非 list → 空
- configure_portfolio_risk_belong_boards 装配指向适配器
"""

from __future__ import annotations

import pytest

import data_provider
from src.application.portfolio import portfolio_risk_service as prs
from src.application.portfolio.portfolio_risk_service import PortfolioRiskService
from src.infrastructure.providers.portfolio_belong_boards_provider import (
    DataProviderPortfolioBelongBoards,
)


@pytest.fixture(autouse=True)
def _isolate_module_port(monkeypatch):
    """每个用例前后把模块级端口指向复位为 None，避免装配状态互相泄漏。"""
    monkeypatch.setattr(prs, "_belong_boards_port", None)
    yield
    monkeypatch.setattr(prs, "_belong_boards_port", None)


def _svc() -> PortfolioRiskService:
    # 端口逻辑不依赖 __init__ 注入，直接绕过构造取实例
    return PortfolioRiskService.__new__(PortfolioRiskService)


# ---------------------------------------------------------------------------
# 用例侧：未装配 / 透传 / 异常 / 非 list / 幂等
# ---------------------------------------------------------------------------

def test_unconfigured_port_degrades_to_empty():
    assert _svc()._fetch_belong_boards("600519") == []


def test_port_list_passthrough():
    class _P:
        def get_belong_boards(self, *, code):
            return [{"name": "白酒", "type": "行业"}]

    prs.set_belong_boards_port(_P())
    assert _svc()._fetch_belong_boards("600519") == [{"name": "白酒", "type": "行业"}]


def test_port_exception_degrades_to_empty():
    class _E:
        def get_belong_boards(self, *, code):
            raise RuntimeError("source down")

    prs.set_belong_boards_port(_E())
    assert _svc()._fetch_belong_boards("600519") == []


def test_port_non_list_normalized_to_empty():
    class _N:
        def get_belong_boards(self, *, code):
            return None

    prs.set_belong_boards_port(_N())
    assert _svc()._fetch_belong_boards("600519") == []


def test_setter_idempotent_none_keeps_existing():
    class _P:
        def get_belong_boards(self, *, code):
            return [{"name": "白酒"}]

    prs.set_belong_boards_port(_P())
    prs.set_belong_boards_port(None)  # 传 None 不覆盖既有指向
    assert _svc()._fetch_belong_boards("600519") == [{"name": "白酒"}]


# ---------------------------------------------------------------------------
# 适配器 best-effort 语义
# ---------------------------------------------------------------------------

def test_adapter_list_passthrough(monkeypatch):
    rows = [{"name": "白酒", "type": "行业"}]

    class _M:
        def get_belong_boards(self, stock_code):
            return rows

    monkeypatch.setattr(data_provider, "DataFetcherManager", _M, raising=False)
    assert DataProviderPortfolioBelongBoards().get_belong_boards(code="600519") == rows


def test_adapter_exception_degrades_to_empty(monkeypatch):
    class _M:
        def get_belong_boards(self, stock_code):
            raise RuntimeError("sdk missing")

    monkeypatch.setattr(data_provider, "DataFetcherManager", _M, raising=False)
    assert DataProviderPortfolioBelongBoards().get_belong_boards(code="600519") == []


def test_adapter_non_list_degrades_to_empty(monkeypatch):
    class _M:
        def get_belong_boards(self, stock_code):
            return "unexpected"

    monkeypatch.setattr(data_provider, "DataFetcherManager", _M, raising=False)
    assert DataProviderPortfolioBelongBoards().get_belong_boards(code="600519") == []


def test_adapter_constructor_failure_degrades_to_empty(monkeypatch):
    def _boom():
        raise ImportError("data_provider unavailable")

    monkeypatch.setattr(data_provider, "DataFetcherManager", _boom, raising=False)
    assert DataProviderPortfolioBelongBoards().get_belong_boards(code="600519") == []


# ---------------------------------------------------------------------------
# 装配入口
# ---------------------------------------------------------------------------

def test_configure_wires_belong_boards_adapter():
    from src.bootstrap.portfolio import configure_portfolio_risk_belong_boards

    configure_portfolio_risk_belong_boards()
    assert isinstance(prs._get_belong_boards_port(), DataProviderPortfolioBelongBoards)
