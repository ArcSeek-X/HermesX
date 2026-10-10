# -*- coding: utf-8 -*-
"""Sector endpoint refactor regressions.
验证 sector endpoint 已收敛为能力包入口编排层。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
SECTOR_ENDPOINT_PATH = ROOT / "api/v1/endpoints/sector.py"


spec = importlib.util.spec_from_file_location("test_sector_endpoint_module", SECTOR_ENDPOINT_PATH)
assert spec and spec.loader
sector_endpoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sector_endpoint)


def test_sector_endpoint_delegates_industry_route_to_shidaotec_provider(monkeypatch) -> None:
    expected = {
        "total": 1,
        "sectors": [{"code": "801001", "name": "农林牧渔", "value": 1, "changePercent": 1.2}],
        "snapshotTime": None,
    }

    monkeypatch.setattr(sector_endpoint, "get_industry_treemap", lambda time: expected)

    assert sector_endpoint.get_industry_sectors("") == expected


def test_sector_endpoint_maps_snapshot_provider_error_to_http_502(monkeypatch) -> None:
    def _raise_snapshot_error(time: str):
        raise sector_endpoint.SnapshotDataUnavailableError(f"历史快照数据获取失败：{time}")

    monkeypatch.setattr(sector_endpoint, "get_industry_treemap", _raise_snapshot_error)

    with pytest.raises(HTTPException) as exc_info:
        sector_endpoint.get_industry_sectors("10:00")

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "历史快照数据获取失败：10:00"


def test_sector_endpoint_delegates_stock_map_route_to_shidaotec_provider(monkeypatch) -> None:
    expected = {
        "total": 1,
        "sectors": [{"code": "600519", "name": "贵州茅台", "value": 1, "changePercent": 2.3}],
        "snapshotTime": None,
    }

    monkeypatch.setattr(sector_endpoint, "get_stock_treemap", lambda time: expected)

    assert sector_endpoint.get_stock_cloud_map("") == expected


def test_sector_endpoint_delegates_etf_and_concept_routes_to_shidaotec_provider(monkeypatch) -> None:
    etf_result = {
        "total": 1,
        "sectors": [{"code": "510300", "name": "沪深300ETF", "value": 1, "changePercent": 0.8}],
        "period": "yesterday",
        "periodLabel": "昨日涨跌幅",
    }
    concept_result = {
        "total": 1,
        "sectors": [{"code": "301558", "name": "AI 概念", "value": 1, "changePercent": 4.5}],
        "period": "week",
        "periodLabel": "近一周",
    }

    monkeypatch.setattr(
        sector_endpoint,
        "get_etf_treemap",
        lambda *, period, top_n: etf_result,
    )
    monkeypatch.setattr(
        sector_endpoint,
        "get_concept_treemap",
        lambda *, period, top_n: concept_result,
    )

    assert sector_endpoint.get_etf_cloud_map("yesterday", 100) == etf_result
    assert sector_endpoint.get_concept_cloud_map("week", 50) == concept_result


def test_market_indices_prefers_stocksdk_provider(monkeypatch) -> None:
    stocksdk_result = [{"code": "000001", "name": "上证指数", "price": 3200.0}]

    monkeypatch.setattr(sector_endpoint, "get_cached_market_indices_from_stocksdk", lambda market: stocksdk_result)
    monkeypatch.setattr(
        sector_endpoint,
        "get_cached_market_indices_from_eastmoney",
        lambda market: [{"code": "fallback", "name": "fallback"}],
    )

    assert sector_endpoint.get_market_indices("a") == {"indices": stocksdk_result}


def test_market_indices_falls_back_to_eastmoney_when_stocksdk_empty(monkeypatch) -> None:
    eastmoney_result = [{"code": "399001", "name": "深证成指", "price": 10000.0}]

    monkeypatch.setattr(sector_endpoint, "get_cached_market_indices_from_stocksdk", lambda market: None)
    monkeypatch.setattr(sector_endpoint, "get_cached_market_indices_from_eastmoney", lambda market: eastmoney_result)

    assert sector_endpoint.get_market_indices("a") == {"indices": eastmoney_result}


def test_market_cards_uses_tab_key_as_market_param(monkeypatch) -> None:
    market_cards = {
        "market": "hk-us",
        "cards": [
            {
                "cardType": "index_quote",
                "cardKey": "index_quote:HSI",
                "payload": {"code": "HSI", "name": "恒生指数", "price": 20000.0},
            }
        ],
    }

    monkeypatch.setattr(sector_endpoint, "get_market_cards_from_source", lambda market: market_cards if market == "hk-us" else None)

    assert sector_endpoint.get_market_cards("hk-us") == market_cards


def test_board_list_prefers_stocksdk_provider(monkeypatch) -> None:
    boards = [
        {
            "rank": 1,
            "code": "BK0475",
            "name": "电池",
            "changePercent": 2.5,
            "totalMarketCap": 1234.56,
            "turnoverRate": 1.23,
            "riseCount": 12,
            "fallCount": 3,
        }
    ]

    monkeypatch.setattr(sector_endpoint, "get_cached_board_list_from_stocksdk", lambda sector_type: boards)
    monkeypatch.setattr(sector_endpoint, "get_cached_board_list_from_eastmoney", lambda sector_type: [])
    monkeypatch.setattr(sector_endpoint, "get_board_card_list_from_shidaotec", lambda sector_type: [])

    result = sector_endpoint.get_board_list("industry")

    assert result["sectorType"] == "industry"
    assert result["boards"] == boards


def test_board_list_falls_back_to_shidaotec_when_other_sources_empty(monkeypatch) -> None:
    shidaotec_boards = [
        {
            "rank": 1,
            "code": "720000",
            "name": "传媒",
            "changePercent": 4.93,
            "totalMarketCap": 13398.81,
            "turnoverRate": 0.0,
            "riseCount": 127,
            "fallCount": 3,
        }
    ]

    monkeypatch.setattr(sector_endpoint, "get_cached_board_list_from_stocksdk", lambda sector_type: None)
    monkeypatch.setattr(sector_endpoint, "get_cached_board_list_from_eastmoney", lambda sector_type: None)
    monkeypatch.setattr(sector_endpoint, "get_board_card_list_from_shidaotec", lambda sector_type: shidaotec_boards)

    result = sector_endpoint.get_board_list("industry")

    assert result == {
        "sectorType": "industry",
        "total": 1,
        "boards": shidaotec_boards,
    }


def test_fund_flow_sector_list_falls_back_when_stocksdk_rank_missing(monkeypatch) -> None:
    fallback = [{"code": "BK0475", "name": "电池", "latest": 12.34}]

    monkeypatch.setattr(sector_endpoint, "fetch_sector_fund_flow_rank_from_stocksdk", lambda *_args: None)
    monkeypatch.setattr(sector_endpoint, "fetch_sector_fund_flow_rank_from_eastmoney", lambda *_args: fallback)

    assert sector_endpoint.get_sector_fund_flow_sector_list("industry") == {
        "sectors": [{"code": "BK0475", "name": "电池"}]
    }


def test_market_overview_prefers_stocksdk_provider(monkeypatch) -> None:
    overview = {
        "riseCount": 3000,
        "fallCount": 1800,
        "flatCount": 120,
        "totalAmount": 1234567890.0,
        "volumeRatio": 1.23,
        "limitUpCount": 88,
        "limitDownCount": 5,
    }

    monkeypatch.setattr(sector_endpoint, "get_cached_market_overview_from_stocksdk", lambda: overview)
    monkeypatch.setattr(sector_endpoint, "get_cached_market_overview_from_eastmoney", lambda: None)

    assert sector_endpoint.get_market_overview() == overview


def test_sector_endpoint_source_file_no_longer_inlines_shidaotec_requests() -> None:
    source = (ROOT / "api/v1/endpoints/sector.py").read_text(encoding="utf-8")

    assert "import requests" not in source
    assert "shidaotec.com" not in source
    assert "getStockMapScale" not in source
    assert "getETFMapScale" not in source
