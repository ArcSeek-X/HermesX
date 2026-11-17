"""市场职责归位保持旧入口、指数顺序、统计规则与快照真实边界。"""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from data_provider.runtime.manager import DataFetcherManager
from data_provider.runtime.fetchers.akshare import AkshareFetcher
from data_provider.runtime.fetchers.efinance import EfinanceFetcher
from data_provider.runtime.fetchers.tushare import TushareFetcher
from data_provider.market import eastmoney_source as east
from data_provider.market import tencent_source as tencent
from src.infrastructure.providers.market_snapshot_provider import DataProviderMarketSnapshotSource


def test_snapshot_entrypoints_use_canonical_implementation_and_index_location(monkeypatch):
    from data_provider.market import snapshot
    from tests.support.paths import get_repo_root

    east_fetch = Mock(return_value=object())
    tencent_fetch = Mock(return_value=object())
    monkeypatch.setattr(east, "fetch_eastmoney_market_snapshot", east_fetch)
    monkeypatch.setattr(tencent, "fetch_tencent_market_snapshot", tencent_fetch)
    assert snapshot.fetch_eastmoney_market_snapshot() is east_fetch.return_value
    assert snapshot.fetch_tencent_market_snapshot() is tencent_fetch.return_value
    east_fetch.assert_called_once_with()
    tencent_fetch.assert_called_once_with()
    expected = get_repo_root() / "apps" / "hrs-web" / "public" / "stocks.index.json"
    assert tencent._stock_index_path() == expected


@pytest.mark.parametrize("cls", [AkshareFetcher, EfinanceFetcher, TushareFetcher])
def test_three_legacy_statistic_entrypoints_preserve_limits_units_and_input(cls):
    frame = pd.DataFrame(
        {
            "代码": ["600519", "002001", "300001", "688001", "920001", "600000", "000001", "600001"],
            "名称": ["normal", "ST sample", "growth", "science", "beijing", "flat", "paused", "down"],
            "最新价": [11, 10.5, 12, 8, 7, 10, "-", 9],
            "昨收": [10] * 8,
            "成交额": [1e8] * 6 + [0, 1e8],
        }
    )
    before = frame.copy(deep=True)
    result = cls.__new__(cls)._calc_market_stats(frame)
    assert result == {
        "up_count": 3,
        "down_count": 3,
        "flat_count": 1,
        "limit_up_count": 3,
        "limit_down_count": 3,
        "total_amount": 7.0,
    }
    pd.testing.assert_frame_equal(frame, before)


def test_market_index_route_keeps_single_tickflow_attempt_and_fallback_order(monkeypatch):
    calls = []

    def failed(region):
        calls.append(("tickflow", region))
        raise TimeoutError("offline failure")

    tickflow = SimpleNamespace(name="TickFlowFetcher", priority=0, get_main_indices=failed)
    fallback = SimpleNamespace(
        name="Fallback",
        priority=1,
        get_main_indices=lambda region: calls.append(("fallback", region)) or [{"code": "index"}],
    )
    owner = DataFetcherManager(fetchers=[tickflow, fallback])
    monkeypatch.setattr(owner, "_get_tickflow_fetcher", lambda: tickflow)
    assert owner.get_main_indices("cn") == [{"code": "index"}]
    assert calls == [("tickflow", "cn"), ("fallback", "cn")]


def test_snapshot_adapter_does_not_add_fallback_when_east_first_page_fails(monkeypatch):
    get = Mock(side_effect=TimeoutError("offline"))
    monkeypatch.setattr(east, "_SESSION", SimpleNamespace(get=get))
    fallback = Mock(side_effect=AssertionError("fallback belongs to application layer"))
    monkeypatch.setattr(tencent, "fetch_tencent_market_snapshot", fallback)
    assert DataProviderMarketSnapshotSource().fetch_eastmoney_snapshot() is None
    get.assert_called_once()
    fallback.assert_not_called()


def test_east_snapshot_preserves_later_page_retry_and_partial_result(monkeypatch):
    first = {"data": {"total": 101, "diff": [{"f12": "600519", "f14": "sample", "f2": 10}]}}

    def get(_url, *, params, timeout):
        if params["pn"] != 1:
            raise TimeoutError("page unavailable")
        assert params["pz"] == 100 and params["fid"] == "f12"
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: first)

    get_mock = Mock(side_effect=get)
    sleep = Mock()
    monkeypatch.setattr(east, "_SESSION", SimpleNamespace(get=get_mock))
    monkeypatch.setattr(east, "time", SimpleNamespace(sleep=sleep))
    result = east.fetch_eastmoney_market_snapshot(page_size=1000, max_workers=1)
    assert result["代码"].tolist() == ["600519"]
    assert get_mock.call_count == 1 + east._PAGE_RETRIES
    assert sleep.call_count == east._PAGE_RETRIES - 1


def test_tencent_index_filter_batch_parse_and_original_units(monkeypatch, tmp_path):
    index = tmp_path / "stocks.index.json"
    records = [
        ["000001.SZ", "000001", "", "", "", "", "CN", "stock"],
        ["600519.SH", "600519", "", "", "", "", "CN", "stock"],
        ["920001.BJ", "920001", "", "", "", "", "CN", "stock"],
        ["000001.SZ", "000001", "", "", "", "", "CN", "stock"],
        ["00700.HK", "00700", "", "", "", "", "HK", "stock"],
        ["510300.SH", "510300", "", "", "", "", "CN", "etf"],
    ]
    index.write_text(json.dumps(records))
    monkeypatch.setattr(tencent, "_stock_index_path", lambda: index)
    assert tencent._load_a_share_symbols() == ["sz000001", "sh600519", "bj920001"]
    urls = []

    def get(url, *, headers, timeout):
        urls.append(url)
        entries = []
        for symbol in url.split("=", 1)[1].split(","):
            fields = [""] * 50
            for field, value in [
                (tencent._F_NAME, "sample"),
                (tencent._F_CODE, symbol[2:]),
                (tencent._F_PRICE, "10"),
                (tencent._F_AMOUNT, "4"),
                (tencent._F_CIRC_MV, "3"),
                (tencent._F_VOLUME, "7"),
            ]:
                fields[field] = value
            entries.append(f'v_{symbol}="' + "~".join(fields) + '";')
        return SimpleNamespace(raise_for_status=lambda: None, content="".join(entries).encode("gbk"))

    monkeypatch.setattr(tencent, "requests", SimpleNamespace(get=get))
    result = tencent.fetch_tencent_market_snapshot(batch_size=2, max_workers=1)
    assert result["代码"].tolist() == ["000001", "600519", "920001"]
    assert result["成交额"].tolist() == [40000.0] * 3
    assert result["流通市值"].tolist() == [3.0] * 3
    assert result["成交量"].tolist() == [7.0] * 3
    assert len(urls) == 2
