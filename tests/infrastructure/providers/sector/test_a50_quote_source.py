"""富时中国 A50 卡片按上游行情时间选择现货 / 期指源的回归测试。

背景：100.XIN9 是只在 A 股时段计算的现货指数，收盘后行情时间固定在 15:00，
原实现仅取该标的，导致夜间卡片停在昨收 0.00%。现按 f124 行情时间的新鲜度
切换到覆盖 SGX 夜盘的 104.CN00Y，本测试锁定判源、降级与卡片身份稳定性。
"""

import logging
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from data_provider.market.indices import EastmoneyCardIndices
from data_provider.sector.market_cards_source import _append_a50_index

_NOW = 1794279600.0
_SPOT_CFG = [{"secid": "100.XIN9", "name": "富时中国A50", "code": "XIN9"}]
_FUTURES_CFG = [{"secid": "104.CN00Y", "name": "富时中国A50", "code": "CN00Y"}]


def _quote(code: str, price: float, timestamp: float, name: str = "富时中国A50") -> dict:
    """构造东财 ulist.np 的单条行情，f124 为上游行情时间。"""
    return {
        "f2": price,
        "f3": 0.32,
        "f4": 41.0,
        "f5": 100,
        "f6": 0.0,
        "f12": code,
        "f14": name,
        "f15": price + 10,
        "f16": price - 10,
        "f18": price - 41.0,
        "f124": timestamp,
        "f297": 20261110,
    }


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeSession:
    """按 secids 返回预置行情；未预置的标的模拟上游无数据。"""

    def __init__(self, quotes_by_secid):
        self.quotes_by_secid = quotes_by_secid
        self.secids_requested = []

    def get(self, url, params=None, timeout=None):
        secids = params["secids"]
        self.secids_requested.append(secids)
        rows = self.quotes_by_secid.get(secids)
        if not rows:
            return _FakeResponse({"rc": 1, "data": None})
        return _FakeResponse({"rc": 0, "data": {"diff": rows}})


def _make_indices(session, now=_NOW, cache=None) -> EastmoneyCardIndices:
    read_now = now if callable(now) else lambda: now
    return EastmoneyCardIndices(
        call_fetch_market_indices=lambda *args, **kwargs: None,
        read_eastmoney_index_url=lambda: "http://push2",
        read_eastmoney_index_url_delay=lambda: "http://push2delay",
        read_market_indices=lambda: [],
        read_market_indices_a50=lambda: _SPOT_CFG,
        read_market_indices_a50_futures=lambda: _FUTURES_CFG,
        read_market_indices_jp_kr=lambda: [],
        read_market_indices_us=lambda: [],
        read_request_timeout=lambda: (5, 10),
        read_index_cache=lambda: cache if cache is not None else {},
        read_session=lambda: session,
        read_logger=lambda: logging.getLogger("test.a50"),
        read_time=lambda: SimpleNamespace(time=read_now),
    )


def _as_of(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, ZoneInfo("Asia/Shanghai")).isoformat()


def test_fresh_spot_quote_follows_a_share_and_skips_futures_request():
    """盘中现货行情新鲜时用 100.XIN9，且不必额外请求期指。"""
    session = _FakeSession(
        {
            "100.XIN9": [_quote("XIN9", 12978.19, _NOW - 10)],
            "104.CN00Y": [_quote("CN00Y", 13027.0, _NOW - 10, "A50期指当月连续")],
        }
    )

    result = _make_indices(session).fetch_a50_index()

    assert len(result) == 1
    assert result[0]["price"] == 12978.19
    assert result[0]["quoteSource"] == "index"
    assert result[0]["code"] == "XIN9"
    assert result[0]["quoteAsOf"] == _as_of(_NOW - 10)
    assert session.secids_requested == ["100.XIN9"]


def test_stale_spot_quote_switches_to_overnight_futures():
    """收盘后现货停在 15:00 时切到 104.CN00Y，卡片身份保持不变。"""
    session = _FakeSession(
        {
            "100.XIN9": [_quote("XIN9", 12939.17, _NOW - 3600)],
            "104.CN00Y": [_quote("CN00Y", 13027.0, _NOW - 10, "A50期指当月连续")],
        }
    )

    result = _make_indices(session).fetch_a50_index()

    assert len(result) == 1
    assert result[0]["price"] == 13027.0
    assert result[0]["quoteSource"] == "futures"
    assert result[0]["quoteAsOf"] == _as_of(_NOW - 10)
    # 切源不改变卡片 code/name，避免 cardKey 变化导致卡片重挂载。
    assert result[0]["code"] == "XIN9"
    assert result[0]["name"] == "富时中国A50"
    assert session.secids_requested == ["100.XIN9", "104.CN00Y"]


def test_futures_unavailable_falls_back_to_last_spot_snapshot():
    """期指取数失败时仍返回现货最后一份快照，不让卡片消失。"""
    session = _FakeSession({"100.XIN9": [_quote("XIN9", 12939.17, _NOW - 3600)]})

    result = _make_indices(session).fetch_a50_index()

    assert result[0]["price"] == 12939.17
    assert result[0]["quoteSource"] == "index"


def test_both_sources_unavailable_returns_none():
    """两个源都无数据时返回 None，由聚合层按单源失败降级。"""
    result = _make_indices(_FakeSession({})).fetch_a50_index()

    assert result is None


def test_invalid_quote_timestamp_is_treated_as_stale():
    """上游缺失或给出非法 f124 时不能误判为盘中实时行情。"""
    indices = _make_indices(_FakeSession({}))

    assert indices._quote_as_of("-") is None
    assert indices._quote_as_of(0) is None
    assert indices._is_spot_quote_fresh({"quoteAsOf": None}) is False
    assert indices._is_spot_quote_fresh({"quoteAsOf": _as_of(_NOW - 3600)}) is False
    assert indices._is_spot_quote_fresh({"quoteAsOf": _as_of(_NOW - 30)}) is True


def test_cached_quote_switches_source_when_user_opens_after_close():
    """夜间首次打开：缓存过期后重新判源，返回夜盘期指而非下午的现货快照。"""
    clock = [_NOW]
    session = _FakeSession(
        {
            "100.XIN9": [_quote("XIN9", 12978.19, _NOW - 10)],
            "104.CN00Y": [_quote("CN00Y", 13027.0, _NOW - 10, "A50期指当月连续")],
        }
    )
    cache = {}
    indices = _make_indices(session, now=lambda: clock[0], cache=cache)

    assert indices.get_cached_a50_index()[0]["quoteSource"] == "index"

    # 时间推进到收盘后：现货停更，夜盘期指仍在跳动。
    clock[0] = _NOW + 8 * 3600
    session.quotes_by_secid["100.XIN9"] = [_quote("XIN9", 12939.17, _NOW + 10)]
    session.quotes_by_secid["104.CN00Y"] = [
        _quote("CN00Y", 13120.0, clock[0] - 10, "A50期指当月连续")
    ]

    refreshed = indices.get_cached_a50_index()[0]

    assert refreshed["quoteSource"] == "futures"
    assert refreshed["price"] == 13120.0
    assert refreshed["quoteAsOf"] == _as_of(clock[0] - 10)


def test_a50_card_survives_empty_main_indices():
    """A 股主指数批量失败时，A50 卡片仍应单独出现。"""
    a50 = [{"code": "XIN9", "name": "富时中国A50", "price": 13120.0, "quoteSource": "futures"}]

    assert _append_a50_index([], a50) == a50
    assert _append_a50_index(None, a50) == a50
