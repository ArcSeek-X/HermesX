"""板块/卡片归位仍使用原状态对象、有效期、动态入口及预热策略。"""

import importlib
import sys
import time
from threading import RLock
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from data_provider.runtime.manager import DataFetcherManager
from data_provider.runtime.fetchers.tickflow import TickFlowFetcher


def test_concept_cache_remains_shared_per_class_returns_copies_and_reads_replaced_cache():
    class Manager(DataFetcherManager):
        _concept_rankings_cache = {}
        _concept_rankings_cache_lock = RLock()

    fetch = Mock(return_value=([{"name": "original", "change_pct": 2}], []))
    backend = SimpleNamespace(name="Sample", priority=1, get_concept_rankings=fetch)
    first, second = Manager(fetchers=[backend]), Manager(fetchers=[backend])
    source = first._sector_source()
    rows, _ = source.get_concept_rankings(5)
    rows[0]["name"] = "caller edit"
    assert second.get_concept_rankings(5)[0][0]["name"] == "original"
    fetch.assert_called_once_with(5)
    Manager._concept_rankings_cache = {5: (time.monotonic() + 60, [{"name": "replaced"}], [])}
    assert source.get_concept_rankings(5)[0][0]["name"] == "replaced"
    assert source.class_concept_rankings_cache() is Manager._concept_rankings_cache


@pytest.mark.parametrize("vendor", ["eastmoney", "stocksdk"])
def test_card_index_helpers_reuse_current_original_cache_and_preserve_failed_refresh(monkeypatch, vendor):
    module = importlib.import_module("data_provider.sector." + vendor + "_source")
    source = module._market_card_indices()
    clock = [110]
    data = [{"code": "index", "price": 10}]
    cache = {"a": {"data": data, "timestamp": 100, "ttl": 60}}
    monkeypatch.setattr(module, "_INDEX_CACHE", cache)
    monkeypatch.setattr(module, "time", SimpleNamespace(time=lambda: clock[0]))
    refresh = Mock(return_value=[{"code": "index", "price": 20}])
    monkeypatch.setattr(module, "fetch_market_indices", refresh)
    assert source.get_cached_market_indices("a") is data
    assert module.get_cached_market_indices("a") is data
    refresh.assert_not_called()
    clock[0] = 170
    updated = source.get_cached_market_indices("a")
    assert updated[0]["price"] == 20
    assert cache["a"]["data"] is updated
    assert cache["a"]["timestamp"] == 170
    refresh.assert_called_once_with("a")
    clock[0] = 240
    refresh.return_value = None
    assert module.get_cached_market_indices("a") is updated
    assert cache["a"]["timestamp"] == 170
    assert refresh.call_count == 2


def test_eastmoney_card_indices_keep_original_session_and_delay_domain_fallback(monkeypatch):
    from data_provider.sector import eastmoney_source as module

    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {
            "rc": 0,
            "data": {
                "diff": [
                    {"f12": "DJI", "f14": "index", "f2": 100, "f6": "0"},
                ]
            },
        },
    )
    get = Mock(side_effect=[TimeoutError("primary unavailable"), response])
    session = SimpleNamespace(get=get)
    monkeypatch.setattr(module, "_session", session)
    result = module.fetch_market_indices("us")
    assert result[0]["code"] == "DJI"
    assert result[0]["amount"] is None
    assert [c.args[0] for c in get.call_args_list] == [module.EASTMONEY_INDEX_URL, module.EASTMONEY_INDEX_URL_DELAY]
    assert module._session is session
    assert get.call_args.kwargs["timeout"] == module.REQUEST_TIMEOUT


def test_market_cards_keep_fresh_stale_cold_paths_and_all_tab_warmup(monkeypatch):
    from data_provider.sector import market_cards_source as cards

    clock = [100.0]
    old = {"market": "a", "cards": [{"cardType": "market_breadth", "payload": {"riseCount": 1}}]}
    cache = {"a": {"payload": old, "timestamp": 90.0}}
    monkeypatch.setattr(cards, "_PAYLOAD_CACHE", cache)
    monkeypatch.setattr(cards, "time", SimpleNamespace(time=lambda: clock[0]))
    refresh = Mock()
    monkeypatch.setattr(cards, "_schedule_refresh", refresh)
    build = Mock(side_effect=lambda market: {"market": market, "cards": [{"cardType": "sample"}]})
    monkeypatch.setattr(cards, "_build_payload", build)
    assert cards.get_market_cards("a") is old
    build.assert_not_called()
    refresh.assert_not_called()
    clock[0] = 120.0
    assert cards.get_market_cards("a") is old
    refresh.assert_called_once_with("a")
    build.assert_not_called()
    clock[0] = 1000.0
    current = cards.get_market_cards("a")
    assert current is cache["a"]["payload"] and current is not old
    assert cache["a"]["timestamp"] == 1000.0
    build.reset_mock()
    cards.warm_market_cards_cache()
    assert [c.args[0] for c in build.call_args_list] == list(cards.MARKET_TAB_KEYS)
    assert set(cache) == set(cards.MARKET_TAB_KEYS)


def test_akshare_sector_and_limit_pool_keep_same_instance_throttle(monkeypatch):
    from data_provider.runtime.fetchers import akshare as module

    monkeypatch.setattr(module, "get_config", lambda: SimpleNamespace(enable_eastmoney_patch=False))
    fetcher = module.AkshareFetcher(sleep_min=0, sleep_max=0)
    fetcher.realtime_sleep_min = fetcher.realtime_sleep_max = 0
    monkeypatch.setattr(fetcher, "_set_random_user_agent", lambda: None)
    sector = Mock(return_value=pd.DataFrame({"板块名称": ["sample"], "涨跌幅": [1]}))
    pool = Mock(
        return_value=pd.DataFrame({"代码": ["600519"], "名称": ["sample"], "连板数": [2], "首次封板时间": ["093000"]})
    )
    monkeypatch.setitem(
        sys.modules, "akshare", SimpleNamespace(stock_board_industry_name_em=sector, stock_zt_pool_em=pool)
    )
    original_std, original_light = fetcher._enforce_rate_limit, fetcher._enforce_realtime_rate_limit
    before = []

    def std():
        before.append(fetcher._last_request_time)
        original_std()

    def light():
        before.append(fetcher._last_request_time)
        original_light()

    monkeypatch.setattr(fetcher, "_enforce_rate_limit", std)
    monkeypatch.setattr(fetcher, "_enforce_realtime_rate_limit", light)
    assert fetcher.get_sector_rankings(1)[0][0]["name"] == "sample"
    after_sector = fetcher._last_request_time
    result = fetcher.get_limit_up_pool(date="20260102", n=1)
    assert result[0]["code"] == "600519"
    assert result[0]["first_limit_time"] == "093000"
    assert before == [None, after_sector]
    pool.assert_called_once_with(date="20260102")


def test_tickflow_sector_cache_setter_and_sdk_remain_on_original_host():
    owner = TickFlowFetcher(api_key="test-key")
    universe_id = "CN_Equity_SW1_sample"
    quote = {"symbol": "600519.SH", "ext": {"change_pct": 0.1}}
    get = Mock(return_value=[quote])
    client = SimpleNamespace(
        universes=SimpleNamespace(
            list=Mock(return_value=[{"id": universe_id, "name": "SW1 sample"}]),
            batch=Mock(return_value={universe_id: {"symbols": ["600519.SH"]}}),
        ),
        quotes=SimpleNamespace(get=get),
        close=Mock(),
    )
    owner._client = client
    source = owner._sector_source()
    try:
        first = source.get_sector_rankings(1)
        assert first[0][0]["name"] == "sample"
        assert first[0][0]["change_pct"] == 10.0
        first[0][0]["name"] = "caller edit"
        assert owner.get_sector_rankings(1)[0][0]["name"] == "sample"
        assert source.current_sector_rankings_cache() is owner._sector_rankings_cache
        assert owner._client is client
        get.assert_called_once()
    finally:
        owner.close()
    client.close.assert_called_once_with()
