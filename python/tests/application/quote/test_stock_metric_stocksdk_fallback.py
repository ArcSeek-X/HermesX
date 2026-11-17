# -*- coding: utf-8 -*-
"""股票度量视图 stock-sdk 兜底源回归测试。

覆盖三层：
- 行映射：字段口径、市值单位换算（亿元→元）、缺失列置 None、美股交易所后缀归一；
- 缓存：命中 TTL 返回本批抓取时刻、回源失败沿用旧快照、桥接不可用返回 None；
- 装配：主源（东财）有数据不切备源，主源无数据才切 stock-sdk，两源皆空返回 None。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pytest

from data_provider.market import stocksdk_source
from src.bootstrap import quote as bootstrap_quote


class _FixedMoment:
    """``datetime.now(...)`` 替身：只提供 isoformat()。"""

    def __init__(self, value: str) -> None:
        self._value = value

    def isoformat(self) -> str:
        return self._value


class _FixedClock:
    """模块级 datetime 替身，让每个用例可显式设定「当前时刻」。"""

    value = ""

    @classmethod
    def now(cls, tz: Any = None) -> _FixedMoment:
        return _FixedMoment(cls.value)


class _FakeClient:
    """StockSDK 桥接客户端替身：可设定返回行与可用性，并记录调用次数。"""

    def __init__(self, rows: List[Dict[str, Any]], available: bool = True) -> None:
        self.rows = rows
        self.available = available
        self.calls = 0

    def is_available(self) -> bool:
        return self.available

    def fetch_market_snapshot(self, market: str) -> List[Dict[str, Any]]:
        self.calls += 1
        return self.rows


@pytest.fixture(autouse=True)
def _reset_snapshot_cache(monkeypatch):
    """每个用例独立缓存 + 固定时钟，避免用例间相互污染。"""
    monkeypatch.setattr(stocksdk_source, "_SNAPSHOT_CACHE", {})
    monkeypatch.setattr(stocksdk_source, "_SNAPSHOT_REFRESH_LOCKS", {})
    monkeypatch.setattr(stocksdk_source, "datetime", _FixedClock)
    _FixedClock.value = "2026-11-16T07:00:00+00:00"
    yield
    _FixedClock.value = ""


def _raw_cn() -> Dict[str, Any]:
    return {
        "code": "600519",
        "name": "贵州茅台",
        "price": 1435.26,
        "changePct": 1.77,
        "volume": 41780.0,
        "relativeVolume": 1.28,
        "totalMarketCapYi": 18000.0,
        "peRatioTTM": 21.84,
        "pbRatio": 5.1,
    }


def test_map_row_aligns_units_and_keeps_missing_columns_null():
    row = stocksdk_source._map_row(_raw_cn(), "cn")

    assert row is not None
    assert row["market"] == "cn"
    assert row["code"] == "600519"
    # 上游亿元 -> 契约元，与东财 f20 对齐
    assert row["totalMarketCap"] == pytest.approx(18000.0 * 100_000_000.0)
    assert row["relativeVolume"] == pytest.approx(1.28)
    assert row["peRatioTTM"] == pytest.approx(21.84)
    # stock-sdk 不提供这些列，按契约置 None，不填 0、不估算
    for missing in (
        "epsDiluted",
        "dividendYieldPct",
        "industry",
        "roePct",
        "psRatioTTM",
        "revenueGrowthYoyPct",
    ):
        assert row[missing] is None


def test_map_row_normalizes_us_exchange_suffix():
    row = stocksdk_source._map_row({"code": "AAPL.OQ", "name": "苹果", "price": 356.27}, "us")
    assert row is not None and row["code"] == "AAPL"

    # 股票类别后缀（BRK.A）不能被当成交易所后缀截断
    row = stocksdk_source._map_row({"code": "BRK.A.N", "name": "伯克希尔", "price": 1.0}, "us")
    assert row is not None and row["code"] == "BRK.A"


def test_map_row_drops_invalid_rows():
    assert stocksdk_source._map_row({"code": "X", "name": "停牌", "price": 0}, "cn") is None
    assert stocksdk_source._map_row({"code": "", "name": "空代码", "price": 1.0}, "cn") is None
    assert stocksdk_source._map_row({"code": "X", "name": "", "price": 1.0}, "cn") is None


def test_hk_rows_keep_null_pe_and_pb(monkeypatch):
    fake = _FakeClient(
        [{"code": "00700", "name": "腾讯控股", "price": 393.0, "totalMarketCapYi": 35734.0}]
    )
    monkeypatch.setattr(stocksdk_source, "get_stocksdk_client", lambda: fake)

    snapshot = stocksdk_source.fetch_stocksdk_metric_snapshot("hk")
    assert snapshot is not None
    row = snapshot[0][0]
    assert row["peRatioTTM"] is None
    assert row["pbRatio"] is None
    assert row["relativeVolume"] is None


def test_cache_hit_returns_batch_fetch_time(monkeypatch):
    fake = _FakeClient([_raw_cn()])
    monkeypatch.setattr(stocksdk_source, "get_stocksdk_client", lambda: fake)

    first = stocksdk_source.fetch_stocksdk_metric_snapshot("cn")
    assert first is not None
    assert first[1] == "2026-11-16T07:00:00+00:00"

    _FixedClock.value = "2026-11-16T08:00:00+00:00"
    second = stocksdk_source.fetch_stocksdk_metric_snapshot("cn")
    assert second is not None
    # 命中 TTL 缓存仍是本批抓取时刻，且没有再次拉起桥接
    assert second[1] == first[1]
    assert fake.calls == 1


def test_failure_keeps_last_snapshot(monkeypatch):
    fake = _FakeClient([_raw_cn()])
    monkeypatch.setattr(stocksdk_source, "get_stocksdk_client", lambda: fake)
    first = stocksdk_source.fetch_stocksdk_metric_snapshot("cn")
    assert first is not None

    # 回源为空（上游失败）后，过期缓存仍按 stale-while-error 沿用
    fake.rows = []
    monkeypatch.setattr(stocksdk_source, "_SNAPSHOT_TTL_SECONDS", 0.0)
    second = stocksdk_source.fetch_stocksdk_metric_snapshot("cn", force_refresh=True)
    assert second is not None
    assert second[1] == first[1]
    assert second[0][0]["code"] == "600519"
    assert fake.calls == 2


def test_unavailable_bridge_returns_none(monkeypatch):
    fake = _FakeClient([_raw_cn()], available=False)
    monkeypatch.setattr(stocksdk_source, "get_stocksdk_client", lambda: fake)

    assert stocksdk_source.fetch_stocksdk_metric_snapshot("cn") is None
    assert fake.calls == 0


def test_unsupported_market_returns_none():
    assert stocksdk_source.fetch_stocksdk_metric_snapshot("jp") is None


def test_fallback_port_prefers_primary_source():
    calls: List[Tuple[str, str]] = []

    def _primary(market: str, *, force_refresh: bool = False):
        calls.append(("primary", market))
        return [{"market": market}], "primary-time"

    def _fallback(market: str, *, force_refresh: bool = False):
        calls.append(("fallback", market))
        return [{"market": market}], "fallback-time"

    port = bootstrap_quote._metric_snapshot_with_fallback(_primary, _fallback)
    rows, fetched_at = port("cn")

    assert fetched_at == "primary-time"
    assert rows == [{"market": "cn"}]
    assert calls == [("primary", "cn")]


def test_fallback_port_switches_when_primary_has_no_data():
    calls: List[Tuple[str, str]] = []

    def _primary(market: str, *, force_refresh: bool = False) -> Optional[Tuple[Any, str]]:
        calls.append(("primary", market))
        return None

    def _fallback(market: str, *, force_refresh: bool = False):
        calls.append(("fallback", market))
        return [{"market": market}], "fallback-time"

    port = bootstrap_quote._metric_snapshot_with_fallback(_primary, _fallback)
    rows, fetched_at = port("us")

    assert fetched_at == "fallback-time"
    assert rows == [{"market": "us"}]
    assert calls == [("primary", "us"), ("fallback", "us")]


def test_fallback_port_returns_none_when_both_sources_empty():
    def _empty(market: str, *, force_refresh: bool = False) -> Optional[Tuple[Any, str]]:
        return None

    port = bootstrap_quote._metric_snapshot_with_fallback(_empty, _empty)
    assert port("hk") is None


def test_fallback_port_passes_force_refresh():
    seen: List[bool] = []

    def _source(market: str, *, force_refresh: bool = False):
        seen.append(force_refresh)
        return [{"market": market}], "t"

    port = bootstrap_quote._metric_snapshot_with_fallback(_source, _source)
    port("cn", force_refresh=True)

    assert seen == [True]
