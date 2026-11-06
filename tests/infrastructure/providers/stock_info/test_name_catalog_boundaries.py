"""名称/清单提取保留缓存所有权、精确匹配、原会话清理与分页语义。"""

import importlib
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock, call

import pandas as pd
import pytest

from data_provider.runtime.manager import DataFetcherManager
from data_provider.runtime.fetchers.baostock import BaostockFetcher
from data_provider.runtime.fetchers.pytdx import PytdxFetcher
from data_provider.runtime.fetchers.tushare import TushareFetcher


def test_bound_name_lookup_reads_current_manager_cache_without_remote_lookup(monkeypatch):
    fetcher = SimpleNamespace(name="Unused", priority=1, get_stock_name=Mock())
    manager = DataFetcherManager(fetchers=[fetcher])
    manager.get_realtime_quote = Mock(side_effect=AssertionError("cache hit must not fetch quotes"))
    lookup = manager._stock_names()
    monkeypatch.setattr("data_provider.runtime.manager.get_index_stock_name", Mock(side_effect=AssertionError("cache must win")))
    replacement = {"123456": "current name"}
    manager._stock_name_cache = replacement
    assert lookup.get_stock_name("SH123456", allow_realtime=False) == "current name"
    assert lookup.read_stock_name_cache() is replacement
    manager.get_realtime_quote.assert_not_called()
    fetcher.get_stock_name.assert_not_called()


def test_bulk_names_keep_requested_keys_and_warm_same_cache_for_catalog_rows():
    catalog = pd.DataFrame({"code": ["123456", "654321"], "name": ["requested", "other"]})
    fetcher = SimpleNamespace(
        name="Catalog", priority=1, get_stock_list=Mock(return_value=catalog), get_stock_name=Mock()
    )
    manager = DataFetcherManager(fetchers=[fetcher])
    manager.get_realtime_quote = Mock(side_effect=AssertionError("catalog cache must prevent quote fetch"))
    result = manager.batch_get_stock_names(["SH123456"])
    assert result == {"SH123456": "requested"}
    assert manager._stock_name_cache == {"123456": "requested", "654321": "other"}
    assert manager.get_stock_name("654321", allow_realtime=False) == "other"
    fetcher.get_stock_list.assert_called_once_with()
    fetcher.get_stock_name.assert_not_called()
    manager.get_realtime_quote.assert_not_called()


def test_tushare_catalog_names_and_daily_keep_same_api_cache_and_quota():
    fetcher = TushareFetcher.__new__(TushareFetcher)
    fetcher._call_count, fetcher._minute_start, fetcher.rate_limit_per_minute = 0, None, 100
    rows = pd.DataFrame(
        {"ts_code": ["600519.SH"], "name": ["first"], "industry": ["sector"], "area": ["area"], "market": ["main"]}
    )
    first_api = SimpleNamespace(stock_basic=Mock(return_value=rows))
    fetcher._api = first_api
    names, catalog = fetcher._stock_names(), fetcher._stock_catalog()
    assert not hasattr(fetcher, "_stock_name_cache")
    assert catalog.get_stock_list()["code"].tolist() == ["600519"]
    assert names.get_stock_name("600519") == "first"
    assert fetcher._call_count == 1
    first_api.stock_basic.assert_called_once_with(
        exchange="", list_status="L", fields="ts_code,name,industry,area,market"
    )
    current_api = SimpleNamespace(
        stock_basic=Mock(return_value=rows.assign(ts_code="000001.SZ", name="second")),
        daily=Mock(return_value=pd.DataFrame({"close": [10]})),
    )
    fetcher._api = current_api
    assert catalog.get_stock_list()["name"].tolist() == ["second"]
    assert names.get_stock_name("000001") == "second"
    assert fetcher._call_count == 2
    fetcher._fetch_raw_data("600519", "2026-01-01", "2026-01-02")
    assert fetcher._call_count == 3
    current_api.daily.assert_called_once_with(ts_code="600519.SH", start_date="20260101", end_date="20260102")
    assert names.read_stock_name_cache() is fetcher._stock_name_cache


@pytest.mark.parametrize("fail", [False, True])
def test_baostock_catalog_uses_original_session_cleanup_and_name_cache(fail):
    rows = SimpleNamespace(
        error_code="0",
        fields=["code", "code_name"],
        next=Mock(side_effect=[True, False]),
        get_row_data=Mock(return_value=["sh.600519", "sample"]),
    )
    api = SimpleNamespace(
        login=Mock(return_value=SimpleNamespace(error_code="0")),
        logout=Mock(return_value=SimpleNamespace(error_code="0")),
        query_stock_basic=Mock(side_effect=ValueError("query denied")) if fail else Mock(return_value=rows),
    )
    fetcher = BaostockFetcher()
    fetcher._bs_module = api
    result = fetcher.get_stock_list()
    if fail:
        assert result is None
        assert not hasattr(fetcher, "_stock_name_cache")
    else:
        assert result.to_dict("records") == [{"code": "600519", "name": "sample"}]
        assert fetcher.get_stock_name("600519") == "sample"
    api.query_stock_basic.assert_called_once_with()
    api.login.assert_called_once_with()
    api.logout.assert_called_once_with()


def test_pytdx_catalog_keeps_two_market_pagination_and_current_host_cache():
    fetcher = PytdxFetcher()
    catalog = fetcher._stock_catalog()
    fetcher.SECURITY_LIST_PAGE_SIZE = 2
    api = SimpleNamespace(
        get_security_list=Mock(
            side_effect=[
                [{"code": "000001", "name": "one"}, {"code": "000002", "name": "two"}],
                [{"code": "000003", "name": "three"}],
                [{"code": "600519", "name": "four"}],
            ]
        )
    )
    catalog.build_stock_list_cache(api)
    assert api.get_security_list.call_args_list == [call(0, 0), call(0, 2), call(1, 0)]
    assert fetcher._stock_list_cache == {"000001": "one", "000002": "two", "000003": "three", "600519": "four"}
    assert catalog.read_stock_list_cache() is fetcher._stock_list_cache
    assert fetcher._stock_name_cache == {}  # The original list and queried-name caches remain distinct.


@pytest.mark.parametrize("vendor", ["finnhub", "alphavantage"])
def test_name_lookup_keeps_exact_symbol_matching_and_current_http_credentials(monkeypatch, vendor):
    module = importlib.import_module("data_provider.runtime.fetchers." + vendor)
    cls = module.FinnhubFetcher if vendor == "finnhub" else module.AlphaVantageFetcher
    fetcher = cls.__new__(cls)
    fetcher._api_key = "old-test-key"
    lookup = fetcher._stock_names()
    fetcher._api_key = "current-test-key"
    payload = (
        {"result": [{"symbol": "AAPL.B", "description": "wrong"}, {"symbol": "AAPL", "description": "exact"}]}
        if vendor == "finnhub"
        else {
            "bestMatches": [{"1. symbol": "AAPL.B", "2. name": "wrong"}, {"1. symbol": "AAPL", "2. name": "exact"}],
        }
    )
    get = Mock(return_value=SimpleNamespace(raise_for_status=lambda: None, json=lambda: payload))
    # Replace only this fetcher's transport binding, keeping global requests untouched.
    monkeypatch.setattr(module, "requests", SimpleNamespace(get=get))
    assert lookup.get_stock_name("aapl") == "exact"
    params = get.call_args.kwargs["params"]
    assert params["token" if vendor == "finnhub" else "apikey"] == "current-test-key"
    assert params["q" if vendor == "finnhub" else "keywords"] == "AAPL"
    assert get.call_args.kwargs["timeout"] == 10


@pytest.mark.parametrize("module", ["name_lookup", "catalog"])
def test_leaf_import_does_not_register_info_sources_or_load_code_search(module):
    script = f"""
import data_provider
import importlib, sys
before = set(sys.modules)
importlib.import_module("data_provider.stock_info.{module}")
assert not {{"data_provider.stock_info.base", "data_provider.code_search.base"}} & (set(sys.modules) - before)
"""
    result = subprocess.run([sys.executable, "-c", script], text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
