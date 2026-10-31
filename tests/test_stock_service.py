# -*- coding: utf-8 -*-
"""StockService 端口化 + get_history_data 修复的回归测试。

覆盖：
- 实时行情：端口返回源字段字典 → API 响应整形；``None`` → ``None``；
- 历史 K 线：复用 :class:`QuoteService.get_kline`（同一 ``QuoteProviderPort`` 链路），
  成交量按「手」整形、字段裁剪为 ``KLineData`` 契约键、``stock_name`` 取自取数结果；
- ``period`` 非 daily 抛 ``ValueError``；取数异常降级为空数据（保持既有「不 500」契约）；
- ``DataProviderRealtimeQuoteProvider``：``UnifiedRealtimeQuote`` dataclass → 源字段字典收敛。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from src.application.quote.service import QuoteService
from src.application.quote.stock_service import StockService
from src.infrastructure.providers import realtime_provider


class _FakeQuoteProvider:
    """实现 QuoteProviderPort.fetch_kline 的假端口，返回逐行原始 K 线字典。"""

    def __init__(self, *, rows: List[Dict[str, Any]], stock_name: Optional[str] = "贵州茅台"):
        self._rows = rows
        self._stock_name = stock_name
        self.calls: List[Dict[str, Any]] = []

    def fetch_kline(self, *, stock_code, period, limit, fqt, before_date) -> Dict[str, Any]:
        self.calls.append(
            {"stock_code": stock_code, "period": period, "limit": limit, "fqt": fqt, "before_date": before_date}
        )
        return {
            "stock_code": stock_code,
            "stock_name": self._stock_name,
            "period": period,
            "secid": "1.600519",
            "prev_close": 1600.0,
            "source": "eastmoney",
            "data": self._rows,
        }

    def fetch_stock_info(self, *, stock_code):  # pragma: no cover - 未被本用例消费
        return {}

    def search_codes(self, *, keyword, limit):  # pragma: no cover - 未被本用例消费
        return []


class _FakeRealtimePort:
    def __init__(self, quote: Optional[Dict[str, Any]]):
        self._quote = quote
        self.calls: List[str] = []

    def fetch_realtime_quote(self, *, stock_code: str) -> Optional[Dict[str, Any]]:
        self.calls.append(stock_code)
        return self._quote


class _RaisingProvider(_FakeQuoteProvider):
    def fetch_kline(self, **kwargs):
        raise RuntimeError("数据源不可用")


def _make_service(provider, realtime_quote=None) -> StockService:
    return StockService(
        quote_service=QuoteService(provider=provider),
        realtime_port=_FakeRealtimePort(realtime_quote),
    )


def test_get_history_data_delegates_to_kline_and_reshapes():
    rows = [
        {"date": "2026-10-20", "open": 100.0, "high": 110.0, "low": 95.0, "close": 105.0,
         "volume": 20000.0, "amount": 2100000.0, "change_percent": 1.2, "turnover_rate": 0.5},
        {"date": "2026-10-21", "open": 105.0, "high": 108.0, "low": 102.0, "close": 106.0,
         "volume": 15000.0, "amount": 1600000.0, "change_percent": 0.95, "turnover_rate": 0.4},
    ]
    provider = _FakeQuoteProvider(rows=rows)
    service = _make_service(provider)

    result = service.get_history_data(stock_code="600519", period="daily", days=2)

    assert result["stock_code"] == "600519"
    assert result["stock_name"] == "贵州茅台"
    assert result["period"] == "daily"
    # 委托 QuoteService.get_kline：成交量按「手」整形（/100）
    assert provider.calls[0] == {
        "stock_code": "600519", "period": "daily", "limit": 2, "fqt": 1, "before_date": None
    }
    assert result["data"][0] == {
        "date": "2026-10-20", "open": 100.0, "high": 110.0, "low": 95.0, "close": 105.0,
        "volume": 200.0, "amount": 2100000.0, "change_percent": 1.2,
    }
    # 契约键裁剪：行内 turnover_rate / prev_close 不透出
    assert "turnover_rate" not in result["data"][0]
    assert len(result["data"]) == 2


def test_get_history_data_rejects_non_daily_period():
    service = _make_service(_FakeQuoteProvider(rows=[]))
    with pytest.raises(ValueError):
        service.get_history_data(stock_code="600519", period="weekly", days=30)


def test_get_history_data_falls_back_to_empty_on_provider_error():
    service = _make_service(_RaisingProvider(rows=[]))
    result = service.get_history_data(stock_code="600519", period="daily", days=30)
    assert result == {"stock_code": "600519", "period": "daily", "data": []}


def test_get_realtime_quote_maps_source_fields():
    quote = {
        "code": "600519", "name": "贵州茅台", "price": 1680.0, "change_amount": 12.0,
        "change_pct": 0.72, "open_price": 1670.0, "high": 1690.0, "low": 1665.0,
        "pre_close": 1668.0, "volume": 3_000_000, "amount": 5.0e9,
        "turnover_rate": 0.24, "total_mv": 2.1e12,
    }
    service = _make_service(_FakeQuoteProvider(rows=[]), realtime_quote=quote)

    result = service.get_realtime_quote("600519")

    assert result is not None
    assert result["stock_code"] == "600519"
    assert result["stock_name"] == "贵州茅台"
    assert result["current_price"] == 1680.0
    assert result["change"] == 12.0
    assert result["change_percent"] == 0.72
    assert result["open"] == 1670.0
    assert result["prev_close"] == 1668.0
    assert result["total_mv"] == 2.1e12
    assert result["update_time"]


def test_get_realtime_quote_returns_none_when_port_has_no_data():
    service = _make_service(_FakeQuoteProvider(rows=[]), realtime_quote=None)
    assert service.get_realtime_quote("600519") is None


def test_realtime_provider_converges_dataclass_to_dict(monkeypatch):
    class _Quote:
        code = "000001"
        name = "平安银行"
        price = 11.0
        change_amount = 0.1
        change_pct = 0.9
        open_price = 10.9
        high = 11.2
        low = 10.8
        pre_close = 10.9
        volume = 1_000_000
        amount = 1.1e7
        turnover_rate = 0.5
        total_mv = 2.1e11
        # 端口字段之外的属性应被忽略
        volume_ratio = 1.3

    monkeypatch.setattr(realtime_provider, "get_realtime_quote", lambda code: _Quote())
    result = realtime_provider.DataProviderRealtimeQuoteProvider().fetch_realtime_quote(stock_code="000001")

    assert result["code"] == "000001"
    assert result["price"] == 11.0
    assert result["total_mv"] == 2.1e11
    assert "volume_ratio" not in result


def test_realtime_provider_returns_none_when_no_quote(monkeypatch):
    monkeypatch.setattr(realtime_provider, "get_realtime_quote", lambda code: None)
    assert realtime_provider.DataProviderRealtimeQuoteProvider().fetch_realtime_quote(stock_code="000001") is None
