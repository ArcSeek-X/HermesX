"""Unit tests for K 线数据模型 (api/v1/schemas/kline.py)。

覆盖 4 个响应/数据模型的字段契约：
- KLinePoint：K 线数据点
- KLineResponse：K 线数据响应（嵌套 KLinePoint 列表）
- StockSearchResult / StockSearchResponse：股票搜索结果
- StockInfoResponse：股票实时信息响应

测试重点：
1. 必填字段缺失 / 类型错误时应被 Pydantic 拒绝（ValidationError）；
2. 可选字段可省略，默认 None；
3. 嵌套列表（KLineResponse.data）的逐项校验；
4. model_validate / model_dump 往返一致；
5. 数值字段传入非数值类型应被拒绝。
"""

from typing import Any

import pytest
from pydantic import ValidationError

from api.v1.schemas.kline import (
    KLinePoint,
    KLineResponse,
    StockInfoResponse,
    StockSearchResponse,
    StockSearchResult,
)


# ---------------------------------------------------------------------------
# KLinePoint
# ---------------------------------------------------------------------------

def _valid_kline_point() -> dict[str, Any]:
    return {
        "date": "2024-01-02",
        "open": 1685.0,
        "close": 1700.5,
        "high": 1710.0,
        "low": 1680.0,
    }


def test_kline_point_accepts_minimal_required_fields() -> None:
    point = KLinePoint.model_validate(_valid_kline_point())
    assert point.date == "2024-01-02"
    assert point.open == 1685.0
    assert point.close == 1700.5
    assert point.high == 1710.0
    assert point.low == 1680.0
    # 可选字段默认 None
    assert point.volume is None
    assert point.amount is None
    assert point.change_percent is None
    assert point.turnover_rate is None


@pytest.mark.parametrize("missing", ["date", "open", "close", "high", "low"])
def test_kline_point_rejects_missing_required_field(missing: str) -> None:
    payload = _valid_kline_point()
    del payload[missing]
    with pytest.raises(ValidationError):
        KLinePoint.model_validate(payload)


@pytest.mark.parametrize("bad_field", ["open", "close", "high", "low"])
def test_kline_point_rejects_non_numeric_price(bad_field: str) -> None:
    payload = _valid_kline_point()
    payload[bad_field] = "not-a-number"
    with pytest.raises(ValidationError):
        KLinePoint.model_validate(payload)


def test_kline_point_accepts_optional_fields() -> None:
    payload = {**_valid_kline_point(), "volume": 12345.0, "amount": 67890.12,
               "change_percent": 1.23, "turnover_rate": 0.55}
    point = KLinePoint.model_validate(payload)
    assert point.volume == 12345.0
    assert point.amount == 67890.12
    assert point.change_percent == 1.23
    assert point.turnover_rate == 0.55


def test_kline_point_round_trip_dump_validate() -> None:
    point = KLinePoint.model_validate(_valid_kline_point())
    dumped = point.model_dump()
    restored = KLinePoint.model_validate(dumped)
    assert restored == point


# ---------------------------------------------------------------------------
# KLineResponse（嵌套 KLinePoint）
# ---------------------------------------------------------------------------

def _valid_kline_response() -> dict[str, Any]:
    return {
        "stock_code": "600519",
        "stock_name": "贵州茅台",
        "period": "daily",
        "secid": "1.600519",
        "data": [_valid_kline_point(), _valid_kline_point()],
    }


def test_kline_response_accepts_nested_points() -> None:
    resp = KLineResponse.model_validate(_valid_kline_response())
    assert resp.stock_code == "600519"
    assert resp.period == "daily"
    assert resp.secid == "1.600519"
    assert isinstance(resp.data, list)
    assert len(resp.data) == 2
    assert all(isinstance(p, KLinePoint) for p in resp.data)
    # stock_name 可选
    assert resp.stock_name == "贵州茅台"
    assert resp.prev_close is None


@pytest.mark.parametrize("missing", ["stock_code", "period", "secid", "data"])
def test_kline_response_rejects_missing_required_field(missing: str) -> None:
    payload = _valid_kline_response()
    del payload[missing]
    with pytest.raises(ValidationError):
        KLineResponse.model_validate(payload)


def test_kline_response_rejects_non_list_data() -> None:
    payload = _valid_kline_response()
    payload["data"] = _valid_kline_point()  # 不是 list
    with pytest.raises(ValidationError):
        KLineResponse.model_validate(payload)


def test_kline_response_rejects_invalid_nested_point() -> None:
    payload = _valid_kline_response()
    payload["data"] = [{"date": "2024-01-02"}]  # 缺 open/close/high/low
    with pytest.raises(ValidationError):
        KLineResponse.model_validate(payload)


def test_kline_response_accepts_empty_data_list() -> None:
    payload = _valid_kline_response()
    payload["data"] = []
    resp = KLineResponse.model_validate(payload)
    assert resp.data == []


# ---------------------------------------------------------------------------
# StockSearchResult / StockSearchResponse
# ---------------------------------------------------------------------------

def _valid_search_result() -> dict[str, Any]:
    return {"code": "600519", "name": "贵州茅台", "market": "sh", "secid": "1.600519"}


def test_stock_search_result_accepts_required_fields() -> None:
    item = StockSearchResult.model_validate(_valid_search_result())
    assert item.code == "600519"
    assert item.name == "贵州茅台"
    assert item.market == "sh"
    assert item.secid == "1.600519"


@pytest.mark.parametrize("missing", ["code", "name", "market", "secid"])
def test_stock_search_result_rejects_missing_required_field(missing: str) -> None:
    payload = _valid_search_result()
    del payload[missing]
    with pytest.raises(ValidationError):
        StockSearchResult.model_validate(payload)


def test_stock_search_response_wraps_results_list() -> None:
    resp = StockSearchResponse.model_validate({"results": [_valid_search_result()]})
    assert isinstance(resp.results, list)
    assert len(resp.results) == 1
    assert isinstance(resp.results[0], StockSearchResult)


def test_stock_search_response_rejects_missing_results() -> None:
    with pytest.raises(ValidationError):
        StockSearchResponse.model_validate({})


# ---------------------------------------------------------------------------
# StockInfoResponse
# ---------------------------------------------------------------------------

def _valid_stock_info() -> dict[str, Any]:
    return {
        "stock_code": "600519",
        "stock_name": "贵州茅台",
        "current_price": 1700.5,
    }


def test_stock_info_response_requires_current_price() -> None:
    info = StockInfoResponse.model_validate(_valid_stock_info())
    assert info.stock_code == "600519"
    assert info.current_price == 1700.5
    # 其余均为可选
    assert info.change is None
    assert info.change_percent is None
    assert info.pe_ratio_ttm is None
    assert info.update_time is None


def test_stock_info_response_rejects_missing_current_price() -> None:
    payload = _valid_stock_info()
    del payload["current_price"]
    with pytest.raises(ValidationError):
        StockInfoResponse.model_validate(payload)


def test_stock_info_response_rejects_missing_stock_code() -> None:
    payload = _valid_stock_info()
    del payload["stock_code"]
    with pytest.raises(ValidationError):
        StockInfoResponse.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    ["current_price", "change", "change_percent", "open", "prev_close",
     "high", "low", "volume", "amount", "turnover_rate", "amplitude",
     "pe_ratio_ttm", "total_market_cap"],
)
def test_stock_info_response_rejects_non_numeric_metric(field: str) -> None:
    payload = _valid_stock_info()
    payload[field] = "n/a"
    with pytest.raises(ValidationError):
        StockInfoResponse.model_validate(payload)


def test_stock_info_response_accepts_full_payload() -> None:
    payload = {
        "stock_code": "600519",
        "stock_name": "贵州茅台",
        "current_price": 1700.5,
        "change": 12.3,
        "change_percent": 0.73,
        "open": 1690.0,
        "prev_close": 1688.2,
        "high": 1715.0,
        "low": 1685.0,
        "volume": 2345678.0,
        "amount": 3987654321.0,
        "turnover_rate": 0.19,
        "amplitude": 1.77,
        "pe_ratio_ttm": 28.5,
        "total_market_cap": 2138400000000.0,
        "update_time": "2024-01-02 15:00:00",
    }
    info = StockInfoResponse.model_validate(payload)
    assert info.pe_ratio_ttm == 28.5
    assert info.total_market_cap == 2138400000000.0
    assert info.update_time == "2024-01-02 15:00:00"


def test_stock_info_response_round_trip_dump_validate() -> None:
    info = StockInfoResponse.model_validate(_valid_stock_info())
    restored = StockInfoResponse.model_validate(info.model_dump())
    assert restored == info
