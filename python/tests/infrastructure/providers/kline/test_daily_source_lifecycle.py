"""日线拆分后的真实会话释放、连接冷却与旧 HTTP 替换入口回归。"""

import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from data_provider.runtime.fetchers.baostock import BaostockFetcher
from data_provider.common.errors import DataFetchError
from data_provider.runtime.fetchers.longbridge import LongbridgeFetcher
from data_provider.runtime.fetchers.pytdx import PytdxFetcher
from data_provider.runtime.fetchers.yfinance import YfinanceFetcher


@pytest.mark.parametrize("fail", [False, True])
def test_baostock_daily_uses_original_session_and_logs_out_on_query_failure(fail):
    result = SimpleNamespace(
        error_code="1" if fail else "0", error_msg="query denied",
        fields=["date", "close"], next=Mock(side_effect=[True, False]),
        get_row_data=Mock(return_value=["2026-01-02", "10"]),
    )
    sdk = SimpleNamespace(
        login=Mock(return_value=SimpleNamespace(error_code="0")),
        logout=Mock(return_value=SimpleNamespace(error_code="0")),
        query_history_k_data_plus=Mock(return_value=result),
    )
    fetcher = BaostockFetcher()
    fetcher._bs_module = sdk
    if fail:
        with pytest.raises(DataFetchError, match="query denied"):
            fetcher._fetch_raw_data("600519", "2026-01-01", "2026-01-03")
    else:
        frame = fetcher._fetch_raw_data("600519", "2026-01-01", "2026-01-03")
        assert frame["close"].tolist() == ["10"]
    sdk.login.assert_called_once_with()
    sdk.logout.assert_called_once_with()
    sdk.query_history_k_data_plus.assert_called_once_with(
        code="sh.600519", fields="date,open,high,low,close,volume,amount,pctChg",
        start_date="2026-01-01", end_date="2026-01-03", frequency="d", adjustflag="2",
    )


@pytest.mark.parametrize("fail", [False, True])
def test_pytdx_daily_keeps_host_selection_and_disconnects_on_query_failure(monkeypatch, fail):
    api = SimpleNamespace(
        connect=Mock(side_effect=[False, True]), disconnect=Mock(),
        get_security_bars=Mock(side_effect=ValueError("query denied")) if fail else Mock(return_value=[1]),
        to_df=Mock(return_value=pd.DataFrame({"datetime": ["2026-01-02"], "close": [10]})),
    )
    # Fake transport only: production host selection, context manager and cleanup run unchanged.
    fetcher = PytdxFetcher(hosts=[("first.invalid", 1), ("second.invalid", 2)])
    monkeypatch.setattr(fetcher, "_get_pytdx", lambda: lambda: api)
    if fail:
        with pytest.raises(DataFetchError, match="query denied"):
            fetcher._fetch_raw_data("600519", "2026-01-01", "2026-01-03")
    else:
        frame = fetcher._fetch_raw_data("600519", "2026-01-01", "2026-01-03")
        assert frame["close"].tolist() == [10]
    assert fetcher._current_host_idx == 1
    assert api.connect.call_args_list[1].args == ("second.invalid", 2)
    api.disconnect.assert_called_once_with()
    api.get_security_bars.assert_called_once_with(category=9, market=1, code="600519", start=0, count=30)


def test_yfinance_daily_selects_requested_ticker_without_mutating_download(monkeypatch):
    columns = pd.MultiIndex.from_tuples([("Close", "AAPL"), ("Close", "MSFT")])
    original = pd.DataFrame([[10, 20]], columns=columns, index=pd.DatetimeIndex(["2026-01-02"], name="Date"))
    before = original.copy(deep=True)
    download = Mock(return_value=original)
    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(download=download))
    fetcher = YfinanceFetcher()
    raw = fetcher._fetch_raw_data("AAPL", "2026-01-01", "2026-01-03")
    assert raw.columns.tolist() == [("Close", "AAPL")]
    assert fetcher._normalize_data(raw, "AAPL")["close"].tolist() == [10]
    pd.testing.assert_frame_equal(original, before)
    download.assert_called_once_with(
        tickers="AAPL", start="2026-01-01", end="2026-01-03", progress=False,
        auto_adjust=True, multi_level_index=True,
    )


def test_longbridge_daily_connection_error_invalidates_shared_context_and_cools_realtime(monkeypatch):
    monkeypatch.setenv("LONGBRIDGE_CONNECTION_COOLDOWN_SECONDS", "15")
    monkeypatch.setitem(sys.modules, "longbridge.openapi", SimpleNamespace(
        Period=SimpleNamespace(Day="day"), AdjustType=SimpleNamespace(ForwardAdjust="forward"),
    ))
    fetcher = LongbridgeFetcher()
    fetcher._available = True
    api = SimpleNamespace(history_candlesticks_by_date=Mock(side_effect=RuntimeError("connection closed")))
    fetcher._ctx = api
    monkeypatch.setattr(fetcher, "_get_ctx", lambda: fetcher._ctx)
    with pytest.raises(RuntimeError, match="connection closed"):
        fetcher._fetch_raw_data("AAPL", "2026-01-01", "2026-01-03")
    assert fetcher._ctx is None
    assert fetcher._cooldown_until > 0
    assert not fetcher.is_available_for_request("realtime_quote")
    with pytest.raises(RuntimeError, match="temporarily unavailable"):
        fetcher._fetch_raw_data("AAPL", "2026-01-01", "2026-01-03")
    api.history_candlesticks_by_date.assert_called_once()


@pytest.mark.parametrize("vendor", ["finnhub", "alphavantage"])
def test_daily_http_source_resolves_current_credentials_and_legacy_transport_patch(monkeypatch, vendor):
    if vendor == "finnhub":
        from data_provider.runtime.fetchers import finnhub as module
        fetcher = module.FinnhubFetcher.__new__(module.FinnhubFetcher)
        payload = {"s": "ok", "c": [10], "h": [11], "l": [9], "o": [10], "t": [1767312000], "v": [100]}
        token_field, timeout = "token", 15
    else:
        from data_provider.runtime.fetchers import alphavantage as module
        fetcher = module.AlphaVantageFetcher.__new__(module.AlphaVantageFetcher)
        payload = {"Time Series (Daily)": {"2026-01-02": {"4. close": "10", "5. volume": "100"}}}
        token_field, timeout = "apikey", 30
    fetcher._api_key = "old-test-key"
    source = fetcher._daily_history_source()
    fetcher._api_key = "current-test-key"
    # Replace only this fetcher's transport reference; do not patch global requests.get.
    get = Mock(return_value=SimpleNamespace(raise_for_status=lambda: None, json=lambda: payload))
    monkeypatch.setattr(module, "requests", SimpleNamespace(get=get))
    monkeypatch.setattr(fetcher, "random_sleep", lambda *_: None)
    # The source deliberately binds throttle behavior at construction; rebuild to use the test clock.
    source = fetcher._daily_history_source()
    fetcher._api_key = "latest-test-key"
    result = source.fetch_raw_data("aapl", "2026-01-01", "2026-01-03")
    assert not result.empty
    assert get.call_args.kwargs["params"][token_field] == "latest-test-key"
    assert get.call_args.kwargs["params"]["symbol"] == "AAPL"
    assert get.call_args.kwargs["timeout"] == timeout
    assert source.normalize_data(result, "AAPL")["close"].tolist() == [10]
