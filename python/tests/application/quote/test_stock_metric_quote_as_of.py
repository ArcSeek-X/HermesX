# -*- coding: utf-8 -*-
"""在线快照抓取时刻（quoteAsOf）契约回归测试。

覆盖从 data_provider TTL 缓存到查询响应的完整链路：
- 首次回源记录本批抓取时刻（ISO 8601 带 UTC 偏移）；
- 命中缓存 / 回源失败沿用旧快照（stale-while-error）时都返回该批缓存自己的时刻，
  不用当前时刻顶替；强制刷新成功才产生新时刻；
- 端口未装配 / 全部市场失败时 ``quoteAsOf`` 留空，多市场取最早的抓取时刻。
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from data_provider.market import eastmoney_source
from src.application.quote.stock_metric_service import StockMetricService


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


@pytest.fixture(autouse=True)
def _reset_snapshot_cache(monkeypatch):
    """每个用例独立缓存 + 固定时钟，避免用例间相互污染。"""
    monkeypatch.setattr(eastmoney_source, "_METRIC_SNAPSHOT_CACHE", {})
    monkeypatch.setattr(eastmoney_source, "_METRIC_SNAPSHOT_REFRESH_LOCKS", {})
    monkeypatch.setattr(eastmoney_source, "datetime", _FixedClock)
    _FixedClock.value = "2026-11-08T07:00:00+00:00"
    yield
    _FixedClock.value = ""


def _rows() -> List[Dict[str, Any]]:
    return [{"market": "cn", "code": "600519", "name": "贵州茅台", "totalMarketCap": 100.0}]


def test_cache_hit_returns_batch_fetch_time(monkeypatch):
    monkeypatch.setattr(eastmoney_source, "_load_metric_snapshot", lambda *a, **kw: _rows())
    first = eastmoney_source.fetch_eastmoney_clist_snapshot("cn")
    assert first is not None
    assert first[1] == "2026-11-08T07:00:00+00:00"

    _FixedClock.value = "2026-11-08T08:00:00+00:00"
    second = eastmoney_source.fetch_eastmoney_clist_snapshot("cn")
    assert second is not None
    # 命中 TTL 缓存仍是本批抓取时刻，不是第二次请求的当前时刻
    assert second[1] == first[1]
    assert second[0] == _rows()


def test_stale_snapshot_keeps_cached_fetch_time(monkeypatch):
    monkeypatch.setattr(eastmoney_source, "_load_metric_snapshot", lambda *a, **kw: _rows())
    first = eastmoney_source.fetch_eastmoney_clist_snapshot("cn")
    assert first is not None

    _FixedClock.value = "2026-11-08T08:00:00+00:00"
    monkeypatch.setattr(eastmoney_source, "_load_metric_snapshot", lambda *a, **kw: None)
    stale = eastmoney_source.fetch_eastmoney_clist_snapshot("cn", force_refresh=True)
    assert stale is not None
    # 沿用旧快照时仍报旧时刻，让 UI 能看出数据并非刚更新
    assert stale[1] == first[1]


def test_force_refresh_success_records_new_fetch_time(monkeypatch):
    monkeypatch.setattr(eastmoney_source, "_load_metric_snapshot", lambda *a, **kw: _rows())
    first = eastmoney_source.fetch_eastmoney_clist_snapshot("cn")
    assert first is not None

    _FixedClock.value = "2026-11-08T09:00:00+00:00"
    refreshed = eastmoney_source.fetch_eastmoney_clist_snapshot("cn", force_refresh=True)
    assert refreshed is not None
    assert refreshed[1] == "2026-11-08T09:00:00+00:00"


def test_no_cache_and_source_failure_returns_none(monkeypatch):
    monkeypatch.setattr(eastmoney_source, "_load_metric_snapshot", lambda *a, **kw: None)
    assert eastmoney_source.fetch_eastmoney_clist_snapshot("cn") is None


def _service_query(snapshot_port, markets=("cn",)):
    service = StockMetricService(snapshot_port=snapshot_port)
    filter_list = [SimpleNamespace(field="market", op="in", value=list(markets))]
    return service.query(
        filter_list=filter_list,
        sort=SimpleNamespace(field="totalMarketCap", order="desc"),
        page_num=1,
        page_size=20,
    )


def test_service_passes_through_fetch_time():
    result = _service_query(
        lambda market, *, force_refresh=False: (_rows(), "2026-11-08T07:12:33+00:00")
    )
    assert result["quoteAsOf"] == "2026-11-08T07:12:33+00:00"


def test_service_uses_earliest_time_across_markets():
    def fake_port(market, *, force_refresh=False):
        stamp = "2026-11-08T07:00:00+00:00" if market == "cn" else "2026-11-08T07:30:00+00:00"
        return _rows(), stamp

    result = _service_query(fake_port, markets=("cn", "hk"))
    assert result["quoteAsOf"] == "2026-11-08T07:00:00+00:00"


def test_service_leaves_quote_as_of_empty_when_degraded():
    result = _service_query(lambda market, *, force_refresh=False: None)
    assert result["quoteAsOf"] == ""
    assert result["degraded"] is True


def test_service_leaves_quote_as_of_empty_without_snapshot_port():
    service = StockMetricService(snapshot_port=None)
    result = service.query(
        filter_list=[SimpleNamespace(field="market", op="in", value=["cn"])],
        sort=SimpleNamespace(field="totalMarketCap", order="desc"),
        page_num=1,
        page_size=20,
    )
    assert result["quoteAsOf"] == ""
    assert result["degraded"] is True


def test_export_still_consumes_snapshot_rows():
    """_fetch_all 返回值扩展后，export 仍取第 0 项行数据生成 CSV。"""
    service = StockMetricService(
        snapshot_port=lambda market, *, force_refresh=False: (
            _rows(), "2026-11-08T07:12:33+00:00"
        )
    )
    csv_bytes, truncated = service.export(
        filter_list=[SimpleNamespace(field="market", op="in", value=["cn"])],
        sort=SimpleNamespace(field="totalMarketCap", order="desc"),
        visible_columns=["totalMarketCap"],
        headers={"totalMarketCap": "总市值"},
        limit=100,
    )
    assert truncated is False
    text = csv_bytes.decode("utf-8-sig")
    assert "600519" in text
    assert "总市值" in text
