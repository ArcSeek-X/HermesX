# -*- coding: utf-8 -*-
"""单票分时取数服务离线单元测试：不依赖真实网络数据源。

覆盖趋势（自选股分时缩略图、个股分时图、尾盘选股共用）：
1. 分时必须走 trends2/get（JSON）而非被东财断连的 trends2/sse；
2. 多 CDN 主机轮换；
3. 直连失败回退 stock-sdk 桥接；
4. 输出 KLinePoint 契约（date 标准化为 YYYY-MM-DD HH:mm:ss）。
"""
from __future__ import annotations

from src.application.quote import intraday_timeline_service as tls


class _FakeTrendsResp:
    """最小化 trends2/get 响应桩：仅需 raise_for_status() 与 json()。"""

    def __init__(self, data: dict):
        self._data = data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"rc": 0, "data": self._data}


def test_fetch_intraday_trends_uses_json_get(monkeypatch):
    """回归：分时必须走 trends2/get（JSON），而非被东财断连的 trends2/sse。

    校验 f51..f58 解析、昨收/名称透传、成交量手->股、均价取 f58，且请求 URL
    以 /trends2/get 结尾、绝不出现 /trends2/sse。
    """
    called_urls = []

    def fake_get(url, params=None, timeout=None, headers=None, **kwargs):
        called_urls.append(url)
        return _FakeTrendsResp({
            "code": "600000",
            "name": "浦发银行",
            "preClose": "9.6",
            "trends": [
                "2026-10-14 09:30,9.7,9.8,9.9,9.6,1000,980000,9.75",
                "2026-10-14 09:31,9.8,9.85,9.9,9.78,1200,1180000,9.80",
            ],
        })

    monkeypatch.setattr(tls._SESSION, "get", fake_get)

    points, prev_close, name = tls.fetch_intraday_trends("600000")
    assert len(points) == 2
    assert prev_close == 9.6
    assert name == "浦发银行"
    assert points[0]["close"] == 9.8
    assert points[0]["avg_price"] == 9.75        # f58 真实均价
    assert points[0]["volume"] == 1000 * 100      # 手 -> 股
    assert called_urls and called_urls[0].endswith("/trends2/get")
    assert all(not u.endswith("/trends2/sse") for u in called_urls)


def test_fetch_intraday_trends_rotates_host_on_disconnect(monkeypatch):
    """首主机被断连（RemoteDisconnected）时轮换到下一个 CDN 主机重试。"""
    tried = []

    def fake_get(url, params=None, timeout=None, headers=None, **kwargs):
        tried.append(url)
        if url == tls._TRENDS_URLS[0]:
            raise ConnectionError("RemoteDisconnected")
        return _FakeTrendsResp({
            "name": "X", "preClose": "1.0",
            "trends": ["2026-10-14 09:30,1,1,1,1,10,10,1"],
        })

    monkeypatch.setattr(tls._SESSION, "get", fake_get)
    monkeypatch.setattr(tls.time, "sleep", lambda *_a, **_k: None)  # 跳过退避

    points, prev_close, name = tls.fetch_intraday_trends("600000")
    assert len(points) == 1
    assert tried[0] == tls._TRENDS_URLS[0]
    assert tried[1] == tls._TRENDS_URLS[1]   # 轮换到第二个主机


def test_fetch_intraday_trends_falls_back_to_bridge(monkeypatch):
    """直连全部失败时回退到注入的 stock-sdk 桥接端口（price/avgPrice 口径）。

    桥接改为经 `IntradayTimelineBridgePort` 注入后，测试不再 patch data_provider，
    而是直接装配一个假端口（验证回退链路与输出口径）。
    """
    monkeypatch.setattr(tls.time, "sleep", lambda *_a, **_k: None)

    def boom(*args, **kwargs):
        raise ConnectionError("RemoteDisconnected")

    monkeypatch.setattr(tls._SESSION, "get", boom)

    class _FakeBridgePort:
        def fetch_timeline(self, *, code):
            return {
                "code": code,
                "preClose": 9.6,
                "points": [
                    {"date": "2026-10-14 09:30", "open": 9.8, "close": 9.8, "high": 9.8,
                     "low": 9.8, "volume": 1000, "amount": 9800, "avg_price": 9.75},
                ],
            }

    monkeypatch.setattr(tls, "_get_bridge_port", lambda: _FakeBridgePort())

    points, prev_close, name = tls.fetch_intraday_trends("600000")
    assert len(points) == 1
    assert points[0]["close"] == 9.8
    assert points[0]["avg_price"] == 9.75
    assert prev_close == 9.6


def test_fetch_intraday_trends_bridge_degrades_when_port_not_configured(monkeypatch):
    """桥接端口未装配时优雅降级为空（直连仍是主路径），不抛异常。

    与 S2c name_to_code_resolver 同型的未装配降级：保证搬入 application 后不依赖
    data_provider 仍可导入、仍可仅走直连。
    """
    monkeypatch.setattr(tls.time, "sleep", lambda *_a, **_k: None)

    def boom(*args, **kwargs):
        raise ConnectionError("RemoteDisconnected")

    monkeypatch.setattr(tls._SESSION, "get", boom)
    monkeypatch.setattr(tls, "_get_bridge_port", lambda: None)

    points, prev_close, name = tls.fetch_intraday_trends("600000")
    assert points == []
    assert prev_close is None
    assert name == ""


def test_normalize_trend_date_supports_compact_and_padded_formats():
    """东财 f51 两种时间串都标准化为 KLineView 可解析的 'YYYY-MM-DD HH:mm:ss'。"""
    assert tls._normalize_trend_date("20261014 09:30") == "2026-10-14 09:30:00"
    assert tls._normalize_trend_date("2026-10-14 09:30") == "2026-10-14 09:30:00"
    assert tls._normalize_trend_date("2026-10-14 09:30:05") == "2026-10-14 09:30:05"


def test_fetch_intraday_timeline_returns_kline_points(monkeypatch):
    """fetch_intraday_timeline 走完整链路时输出 KLinePoint 契约，且时间串被标准化。

    东财 trends2 的 f51 为 'YYYYMMDD HH:mm'（无连字符），必须被标准化为
    'YYYY-MM-DD HH:mm:ss'，否则前端 KLineView 会把全部分时点过滤为空。
    """

    def fake_get(url, params=None, timeout=None, headers=None, **kwargs):
        return _FakeTrendsResp({
            "name": "浦发银行",
            "preClose": "9.6",
            "trends": ["20261014 09:30,9.7,9.8,9.9,9.6,1000,980000,9.75"],
        })

    monkeypatch.setattr(tls._SESSION, "get", fake_get)

    data = tls.fetch_intraday_timeline("600000")
    assert data["code"] == "600000"
    assert data["name"] == "浦发银行"
    assert data["prev_close"] == 9.6
    assert len(data["points"]) == 1
    point = data["points"][0]
    assert point["date"] == "2026-10-14 09:30:00"
    assert set(point.keys()) == {"date", "open", "close", "high", "low", "volume", "amount"}


def test_fetch_intraday_timeline_empty_when_source_fails(monkeypatch):
    """上游取空时 points 为空列表（调用方按无数据渲染占位），不抛异常。"""
    monkeypatch.setattr(tls, "fetch_intraday_trends", lambda code: ([], None, ""))

    data = tls.fetch_intraday_timeline("600000")
    assert data["points"] == []
    assert data["prev_close"] is None


def test_stocksdk_bridge_adapter_best_effort_semantics(monkeypatch):
    """桥接适配器：SDK 不可用 / 调用异常均返回 None（best-effort），可用时透传原始字典。

    适配器把 data_provider.stocksdk_bridge 转成 IntradayTimelineBridgePort 形状，
    本身不抛异常、不拖垮调用方（由应用层降级为空）。
    """
    import data_provider.stocksdk_bridge as bridge_mod
    from src.infrastructure.providers.stocksdk_timeline_provider import (
        DataProviderStocksdkTimelineBridge,
    )

    adapter = DataProviderStocksdkTimelineBridge()

    class _Client:
        def __init__(self, available, result=None, raises=False):
            self._available = available
            self._result = result
            self._raises = raises

        def is_available(self):
            return self._available

        def fetch_timeline(self, code):
            if self._raises:
                raise RuntimeError("node missing")
            return self._result

    # 不可用 -> None
    monkeypatch.setattr(
        bridge_mod, "get_stocksdk_client", lambda: _Client(available=False)
    )
    assert adapter.fetch_timeline(code="600000") is None

    # 可用 -> 透传原始字典
    payload = {"points": [{"date": "x", "close": 1.0}], "preClose": 9.6, "name": "Y"}
    monkeypatch.setattr(
        bridge_mod,
        "get_stocksdk_client",
        lambda: _Client(available=True, result=payload),
    )
    assert adapter.fetch_timeline(code="600000") == payload

    # 调用异常 -> None（不抛）
    monkeypatch.setattr(
        bridge_mod,
        "get_stocksdk_client",
        lambda: _Client(available=True, raises=True),
    )
    assert adapter.fetch_timeline(code="600000") is None

    # get_stocksdk_client 自身抛 -> None（不抛）
    def _boom():
        raise RuntimeError("import fail")

    monkeypatch.setattr(bridge_mod, "get_stocksdk_client", _boom)
    assert adapter.fetch_timeline(code="600000") is None
