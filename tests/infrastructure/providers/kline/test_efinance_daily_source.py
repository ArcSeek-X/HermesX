"""Efinance 日线提取保留 SDK 边界、同实例节流与本地标准化。"""

import sys
from types import SimpleNamespace

import pandas as pd
from pandas.testing import assert_frame_equal

from data_provider.runtime.fetchers import efinance as module
from data_provider.common.health import CircuitBreaker


def make_fetcher(monkeypatch):
    monkeypatch.setattr(module, "get_config", lambda: SimpleNamespace(enable_eastmoney_patch=False))
    return module.EfinanceFetcher(sleep_min=0, sleep_max=0)


def test_local_normalization_does_not_require_sdk_or_modify_input(monkeypatch):
    fetcher = make_fetcher(monkeypatch)
    monkeypatch.setitem(sys.modules, "efinance", None)
    frame = pd.DataFrame({"日期": ["2026-01-01"], "收盘": [12.5]})
    before = frame.copy(deep=True)
    normalized = fetcher._normalize_data(frame, "600519")
    assert_frame_equal(frame, before)
    assert normalized.iloc[0].to_dict() == {
        "code": "600519", "date": "2026-01-01", "open": 12.5,
        "high": 12.5, "low": 12.5, "close": 12.5, "volume": 0, "amount": 0,
    }


def test_stock_realtime_and_etf_share_the_original_fetcher_throttle(monkeypatch):
    fetcher = make_fetcher(monkeypatch)
    history_api = object()
    realtime_api = object()
    fake_sdk = SimpleNamespace(stock=SimpleNamespace(
        get_quote_history=history_api, get_realtime_quotes=realtime_api,
    ))
    monkeypatch.setitem(sys.modules, "efinance", fake_sdk)
    monkeypatch.setattr(module, "_realtime_cache", {"data": None, "timestamp": 0, "ttl": 60})
    monkeypatch.setattr(module, "get_realtime_circuit_breaker", lambda: CircuitBreaker())
    monkeypatch.setattr(fetcher, "_set_random_user_agent", lambda: None)
    previous_times = []
    limiter = fetcher._enforce_rate_limit

    def rate_limit():
        previous_times.append(fetcher._last_request_time)
        limiter()

    monkeypatch.setattr(fetcher, "_enforce_rate_limit", rate_limit)
    calls = []

    def sdk_call(api, **kwargs):
        calls.append((api, kwargs))
        if api is history_api:
            return pd.DataFrame({"日期": ["2026-01-01"], "收盘": [12.5], "成交量": [100]})
        assert api is realtime_api
        return pd.DataFrame({
            "股票代码": ["600519"], "股票名称": ["样本"], "最新价": [12.5],
            "涨跌幅": [1.0], "涨跌额": [0.1], "成交量": [100], "成交额": [1250],
            "开盘": [12.0], "最高": [13.0], "最低": [11.0], "昨收": [12.4],
        })

    monkeypatch.setattr(module, "_ef_call_with_timeout", sdk_call)
    fetcher.get_daily_data("600519", start_date="2026-01-01", end_date="2026-01-02")
    after_daily = fetcher._last_request_time
    quote = fetcher.get_realtime_quote("600519")
    assert quote is not None
    after_realtime = fetcher._last_request_time
    fetcher.get_daily_data("510300", start_date="2026-01-01", end_date="2026-01-02")
    assert previous_times == [None, after_daily, after_realtime]
    assert calls == [
        (history_api, {"stock_codes": "600519", "beg": "20260101", "end": "20260102", "klt": 101, "fqt": 1, "timeout": 60}),
        (realtime_api, {}),
        (history_api, {"stock_codes": "1.510300", "beg": "20260101", "end": "20260102", "klt": 101, "fqt": 1, "quote_id_mode": True, "use_id_cache": False, "timeout": 60}),
    ]
