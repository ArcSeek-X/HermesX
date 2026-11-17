"""供应商日线提取保留真实限额/共享状态与动态 SDK 读取。"""

import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd

from data_provider.runtime.fetchers import akshare as ak_module
from data_provider.runtime.fetchers.tushare import TushareFetcher


def test_akshare_daily_channels_share_original_instance_throttle_and_timeout(monkeypatch):
    monkeypatch.setattr(ak_module, "get_config", lambda: SimpleNamespace(enable_eastmoney_patch=False))
    fetcher = ak_module.AkshareFetcher(sleep_min=0, sleep_max=0)
    sina_api, tx_api = object(), object()
    monkeypatch.setitem(sys.modules, "akshare", SimpleNamespace(
        stock_zh_a_daily=sina_api, stock_zh_a_hist_tx=tx_api,
    ))
    limiter = fetcher._enforce_rate_limit
    before_times = []

    def rate_limit():
        before_times.append(fetcher._last_request_time)
        limiter()

    monkeypatch.setattr(fetcher, "_enforce_rate_limit", rate_limit)
    calls = []

    def history_call(api, **kwargs):
        calls.append((api, kwargs))
        return pd.DataFrame({"date": ["2026-01-01"], "close": [12.5], "volume": [100]})

    monkeypatch.setattr(ak_module, "_akshare_call_with_timeout", history_call)
    fetcher._history_call_timeout = 0.25
    fetcher._fetch_stock_data_sina("600519", "2026-01-01", "2026-01-02")
    after_sina = fetcher._last_request_time
    fetcher._history_call_timeout = 0.75
    fetcher._fetch_stock_data_tx("600519", "2026-01-01", "2026-01-02")
    assert before_times == [None, after_sina]
    assert [x[0] for x in calls] == [sina_api, tx_api]
    assert [x[1]["timeout"] for x in calls] == [0.25, 0.75]
    assert [x[1]["call_name"] for x in calls] == ["ak.stock_zh_a_daily", "ak.stock_zh_a_hist_tx"]
    assert {x[1]["symbol"] for x in calls} == {"sh600519"}


def make_tushare():
    fetcher = TushareFetcher.__new__(TushareFetcher)
    fetcher._call_count = 0
    fetcher._minute_start = None
    fetcher.rate_limit_per_minute = 100
    return fetcher


def test_tushare_daily_and_catalog_keep_one_rate_limit_counter():
    fetcher = make_tushare()
    history = pd.DataFrame({"trade_date": ["20260101"], "close": [12.5], "vol": [1], "amount": [2]})
    catalog = pd.DataFrame({
        "ts_code": ["600519.SH"], "name": ["样本"], "industry": ["行业"], "area": ["地区"], "market": ["主板"],
    })
    api = SimpleNamespace(daily=Mock(return_value=history), fund_daily=Mock(return_value=history),
                          hk_daily=Mock(return_value=history), stock_basic=Mock(return_value=catalog))
    fetcher._api = api
    fetcher._fetch_raw_data("600519", "2026-01-01", "2026-01-02")
    assert fetcher._call_count == 1
    assert fetcher.get_stock_list()["code"].tolist() == ["600519"]
    assert fetcher._call_count == 2
    fetcher._fetch_raw_data("510300", "2026-01-01", "2026-01-02")
    assert fetcher._call_count == 3
    fetcher._fetch_raw_data("HK00700", "2026-01-01", "2026-01-02")
    assert fetcher._call_count == 4
    api.daily.assert_called_once_with(ts_code="600519.SH", start_date="20260101", end_date="20260102")
    api.fund_daily.assert_called_once_with(ts_code="510300.SH", start_date="20260101", end_date="20260102")
    api.hk_daily.assert_called_once_with(ts_code="00700.HK", start_date="20260101", end_date="20260102")


def test_tushare_resolves_current_sdk_after_rate_limit_without_capturing_stale_api(monkeypatch):
    fetcher = make_tushare()
    old_api = SimpleNamespace(daily=Mock())
    result = pd.DataFrame({"close": [12.5]})
    current_api = SimpleNamespace(daily=Mock(return_value=result))
    fetcher._api = old_api
    monkeypatch.setattr(fetcher, "_check_rate_limit", lambda: setattr(fetcher, "_api", current_api))
    assert fetcher._fetch_raw_data("600519", "2026-01-01", "2026-01-02") is result
    old_api.daily.assert_not_called()
    current_api.daily.assert_called_once_with(ts_code="600519.SH", start_date="20260101", end_date="20260102")
