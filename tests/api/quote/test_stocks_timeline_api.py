# -*- coding: utf-8 -*-
"""单票分时接口（GET /api/v1/stocks/{code}/timeline）离线测试。

覆盖：
1. 正常映射为 KLinePoint 契约响应（含昨收价）；
2. 上游取空时降级为 200 + 空 points（不让自选股缩略图报错）；
3. 短 TTL 缓存命中后不再重复请求上游；
4. 服务层抛异常时映射为 500。
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from api.v1.endpoints import stocks as stocks_endpoint


@pytest.fixture(autouse=True)
def _clear_timeline_cache():
    """每个用例前清空端点级分时缓存，避免用例间相互污染。"""
    stocks_endpoint._timeline_cache.clear()
    yield
    stocks_endpoint._timeline_cache.clear()


def _fake_timeline_result() -> dict:
    return {
        "code": "600519",
        "name": "贵州茅台",
        "prev_close": 1785.0,
        "points": [
            {
                "date": "2026-10-15 09:30:00",
                "open": 1785.0,
                "close": 1786.5,
                "high": 1787.0,
                "low": 1784.0,
                "volume": 120000.0,
                "amount": 214380000.0,
            }
        ],
    }


def test_get_stock_timeline_maps_kline_points(monkeypatch) -> None:
    monkeypatch.setattr(
        stocks_endpoint, "fetch_intraday_timeline", lambda code: _fake_timeline_result()
    )

    response = stocks_endpoint.get_stock_timeline("600519")

    assert response.stock_code == "600519"
    assert response.stock_name == "贵州茅台"
    assert response.prev_close == 1785.0
    assert len(response.points) == 1
    point = response.points[0]
    assert point.date == "2026-10-15 09:30:00"
    assert point.close == 1786.5
    assert point.volume == 120000.0


def test_get_stock_timeline_empty_points_is_not_an_error(monkeypatch) -> None:
    """上游取空（限流 / 休市无数据）时返回 200 + 空 points，前端渲染占位。"""
    monkeypatch.setattr(
        stocks_endpoint,
        "fetch_intraday_timeline",
        lambda code: {"code": code, "name": "", "prev_close": None, "points": []},
    )

    response = stocks_endpoint.get_stock_timeline("600519")

    assert response.points == []
    assert response.prev_close is None


def test_get_stock_timeline_uses_short_ttl_cache(monkeypatch) -> None:
    """同一代码在 TTL 内只请求上游一次（自选股一页多行的重复请求压力）。"""
    calls: list[str] = []

    def fake_fetch(code: str) -> dict:
        calls.append(code)
        return _fake_timeline_result()

    monkeypatch.setattr(stocks_endpoint, "fetch_intraday_timeline", fake_fetch)

    first = stocks_endpoint.get_stock_timeline("600519")
    second = stocks_endpoint.get_stock_timeline("600519")

    assert calls == ["600519"]
    assert second.points == first.points


def test_get_stock_timeline_maps_service_error_to_500(monkeypatch) -> None:
    def boom(code: str) -> dict:
        raise RuntimeError("upstream down")

    monkeypatch.setattr(stocks_endpoint, "fetch_intraday_timeline", boom)

    with pytest.raises(HTTPException) as exc_info:
        stocks_endpoint.get_stock_timeline("600519")

    assert exc_info.value.status_code == 500
