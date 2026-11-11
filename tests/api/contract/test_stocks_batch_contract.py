# -*- coding: utf-8 -*-
"""最近搜索卡片所依赖的批量行情契约测试。

覆盖两条新增批量接口与它们共用的 schema：

- ``StockQuote`` / ``BatchQuoteResponse``：响应字段必须是规范 camelCase（与 ``StockQuoteCore`` 同名）；
- ``BatchCodesRequest``：代码列表 1~10 的边界；
- ``POST /api/v1/stocks/batch-quote``：请求代码去重保序、单只失败跳过、响应代码以请求代码为准；
- ``POST /api/v1/stocks/batch-timeline``：分时下采样到 48 点且保留首尾、单只失败降级为空点列。

端点测试用最小 FastAPI app + TestClient，mock 掉取数入口，不触碰真实数据源。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.v1.endpoints import stocks
from api.v1.schemas.stocks import (
    BatchCodesRequest,
    BatchQuoteResponse,
    BatchTimelineItem,
    BatchTimelineResponse,
    StockQuote,
    StockTimelinePoint,
    StockTimelineResponse,
)


def _canonical_quote(code: str) -> Dict[str, Any]:
    """构造一份规范 camelCase 行情字典（字段与 StockQuoteCore 对齐）。"""
    return {
        "code": code,
        "name": "贵州茅台",
        "price": 1680.0,
        "change": 12.0,
        "changePct": 0.72,
        "prevClose": 1668.0,
        "turnoverRate": 0.24,
        "amplitude": 1.5,
        "peRatioTTM": 28.5,
        "totalMarketCap": 2.1e12,
    }


class _FakeStockService:
    """按代码返回预置行情；None 表示该代码取数失败。"""

    def __init__(self, quotes: Dict[str, Optional[Dict[str, Any]]]) -> None:
        self._quotes = quotes
        self.calls: list[str] = []

    def get_realtime_quote(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """记录调用并返回预置行情。"""
        self.calls.append(stock_code)
        return self._quotes.get(stock_code)


@pytest.fixture
def batch_client() -> TestClient:
    """只挂载 stocks 路由的最小应用，避免装配完整后端依赖。"""
    app = FastAPI()
    app.include_router(stocks.router, prefix="/api/v1/stocks")
    return TestClient(app)


# ---------------------------------------------------------------------------
# Schema 契约
# ---------------------------------------------------------------------------

def test_stock_quote_uses_canonical_camel_case_names() -> None:
    quote = StockQuote.model_validate(_canonical_quote("600519"))
    assert quote.code == "600519"
    assert quote.price == 1680.0
    assert quote.changePct == 0.72
    assert quote.prevClose == 1668.0
    assert quote.amplitude == 1.5
    assert quote.peRatioTTM == 28.5
    assert quote.totalMarketCap == 2.1e12


def test_stock_quote_rejects_legacy_snake_case_payload() -> None:
    """全量收敛不保留兼容层：缺 code/price 的旧响应必须被拒绝。"""
    with pytest.raises(ValidationError):
        StockQuote.model_validate({"stock_code": "600519", "current_price": 1680.0})


@pytest.mark.parametrize("codes", [[], [f"code{i}" for i in range(11)]])
def test_batch_codes_request_rejects_out_of_range(codes: list[str]) -> None:
    with pytest.raises(ValidationError):
        BatchCodesRequest.model_validate({"codes": codes})


def test_batch_quote_response_wraps_canonical_quotes() -> None:
    resp = BatchQuoteResponse.model_validate({"items": [_canonical_quote("600519")]})
    assert resp.items[0].totalMarketCap == 2.1e12


def test_batch_timeline_item_uses_canonical_prev_close() -> None:
    item = BatchTimelineItem.model_validate(
        {"code": "600519", "name": "贵州茅台", "prevClose": 1668.0, "points": []}
    )
    assert item.prevClose == 1668.0
    assert item.points == []
    assert BatchTimelineResponse(items=[item]).items[0].code == "600519"


# ---------------------------------------------------------------------------
# 批量行情端点
# ---------------------------------------------------------------------------

def test_batch_quote_deduplicates_codes_and_keeps_request_code(
    monkeypatch: pytest.MonkeyPatch, batch_client: TestClient
) -> None:
    """数据源回带后缀代码时，响应仍以请求代码标识，前端才能按代码合并卡片。"""
    service = _FakeStockService({"600519": _canonical_quote("600519.SH"), "000001": _canonical_quote("000001")})
    monkeypatch.setattr(stocks, "build_stock_service", lambda: service)

    resp = batch_client.post(
        "/api/v1/stocks/batch-quote", json={"codes": ["600519", "600519", "000001"]}
    )

    assert resp.status_code == 200
    items = resp.json()["items"]
    assert [item["code"] for item in items] == ["600519", "000001"]
    assert items[0]["totalMarketCap"] == 2.1e12
    assert items[0]["amplitude"] == 1.5
    assert service.calls == ["600519", "000001"]


def test_batch_quote_skips_failed_stock_without_breaking_others(
    monkeypatch: pytest.MonkeyPatch, batch_client: TestClient
) -> None:
    service = _FakeStockService({"600519": None, "000001": _canonical_quote("000001")})
    monkeypatch.setattr(stocks, "build_stock_service", lambda: service)

    resp = batch_client.post("/api/v1/stocks/batch-quote", json={"codes": ["600519", "000001"]})

    assert resp.status_code == 200
    assert [item["code"] for item in resp.json()["items"]] == ["000001"]


def test_batch_quote_rejects_empty_codes(batch_client: TestClient) -> None:
    assert batch_client.post("/api/v1/stocks/batch-quote", json={"codes": []}).status_code == 422


# ---------------------------------------------------------------------------
# 批量分时端点
# ---------------------------------------------------------------------------

def _timeline_point(index: int) -> StockTimelinePoint:
    """构造一个分时点；时间仅用于下采样首尾点断言。"""
    return StockTimelinePoint(date=f"2026-11-11 09:{index:02d}:00", close=float(1600 + index))


def test_batch_timeline_downsamples_points_and_keeps_first_last(
    monkeypatch: pytest.MonkeyPatch, batch_client: TestClient
) -> None:
    points = [_timeline_point(index) for index in range(60)]
    monkeypatch.setattr(
        stocks,
        "_load_timeline",
        lambda code: StockTimelineResponse(stock_code=code, stock_name="贵州茅台", prev_close=1668.0, points=points),
    )

    resp = batch_client.post("/api/v1/stocks/batch-timeline", json={"codes": ["600519"]})

    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["code"] == "600519"
    assert item["prevClose"] == 1668.0
    assert len(item["points"]) == stocks.TIMELINE_THUMBNAIL_POINTS
    assert item["points"][0]["date"] == points[0].date
    assert item["points"][-1]["date"] == points[-1].date


def test_batch_timeline_degrades_failed_stock_to_empty_points(
    monkeypatch: pytest.MonkeyPatch, batch_client: TestClient
) -> None:
    from fastapi import HTTPException

    def _raise(code: str) -> StockTimelineResponse:
        raise HTTPException(status_code=500, detail="上游不可用")

    monkeypatch.setattr(stocks, "_load_timeline", _raise)

    resp = batch_client.post("/api/v1/stocks/batch-timeline", json={"codes": ["600519"]})

    assert resp.status_code == 200
    assert resp.json()["items"] == [{"code": "600519", "name": None, "prevClose": None, "points": []}]
