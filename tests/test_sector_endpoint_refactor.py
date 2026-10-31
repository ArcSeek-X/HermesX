# -*- coding: utf-8 -*-
"""``api/v1/endpoints/sector.py`` 的分层接线、响应契约与数据源回退回归。

该端点曾直接 ``from data_provider.sector.{eastmoney,market_cards,shidaotec,stocksdk}_source
import ...``，并在端点里内联多来源回退。现在链路为：端点（Query 校验、错误映射
400/404/502）→ ``SectorService``（用例：响应信封、字段投影、空数据降级）→
``DataProviderSectorProvider``（适配器：来源优先级与快照错误翻译）→
``data_provider/sector/*``（各来源的 TTL 缓存与真实请求保持不变）。
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.app import create_app
from api.deps import get_sector_service
from api.v1.endpoints import sector as sector_endpoint
from src.application.market import SectorService, SectorSnapshotUnavailableError
from src.infrastructure.providers import sector_provider

ROOT = Path(__file__).resolve().parents[1]
SECTOR_ENDPOINT_PATH = ROOT / "api/v1/endpoints/sector.py"
APPLICATION_DIR = ROOT / "src" / "application" / "market"

# 需要用例注入的路由（``/{sector_code}/stocks`` 当前无取数，不在此列）。
SERVICE_ROUTES = (
    "get_industry_sectors",
    "get_market_indices",
    "get_market_cards",
    "get_market_overview",
    "get_northbound_flow",
    "get_market_fund_flow",
    "get_stock_cloud_map",
    "get_etf_cloud_map",
    "get_sector_fund_flow_history",
    "get_sector_fund_flow_sector_list",
    "get_board_list",
    "get_concept_cloud_map",
)


def _imported_modules(path: Path) -> List[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            modules.append(node.module or "")
        elif isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
    return modules


def _outer_layer_imports(path: Path, forbidden_roots: tuple) -> List[str]:
    hits: List[str] = []
    for module in _imported_modules(path):
        for root in forbidden_roots:
            if module == root or module.startswith(root + "."):
                hits.append(module)
                break
    return hits


class FakeSectorProvider:
    """按端口契约返回固定值或抛错，并记录调用参数。"""

    def __init__(self, **responses: Any) -> None:
        self._responses = dict(responses)
        self.calls: List[tuple] = []

    def _respond(self, name: str, *call: Any) -> Any:
        self.calls.append((name,) + call)
        error = self._responses.get("error")
        if error is not None:
            raise error
        return self._responses.get(name)

    def fetch_industry_treemap(self, *, time_str: str) -> Optional[Dict[str, Any]]:
        return self._respond("fetch_industry_treemap", time_str)

    def fetch_stock_treemap(self, *, time_str: str) -> Optional[Dict[str, Any]]:
        return self._respond("fetch_stock_treemap", time_str)

    def fetch_etf_treemap(self, *, period: str, top_n: int) -> Optional[Dict[str, Any]]:
        return self._respond("fetch_etf_treemap", period, top_n)

    def fetch_concept_treemap(self, *, period: str, top_n: int) -> Optional[Dict[str, Any]]:
        return self._respond("fetch_concept_treemap", period, top_n)

    def fetch_market_indices(self, *, market: str) -> Optional[List[Dict[str, Any]]]:
        return self._respond("fetch_market_indices", market)

    def fetch_market_overview(self) -> Optional[Dict[str, Any]]:
        return self._respond("fetch_market_overview")

    def fetch_northbound_flow(self) -> Optional[Dict[str, Any]]:
        return self._respond("fetch_northbound_flow")

    def fetch_market_fund_flow(self) -> Optional[Dict[str, Any]]:
        return self._respond("fetch_market_fund_flow")

    def fetch_market_cards(self, *, market: str) -> Optional[Dict[str, Any]]:
        return self._respond("fetch_market_cards", market)

    def fetch_board_list(self, *, sector_type: str) -> Optional[List[Dict[str, Any]]]:
        return self._respond("fetch_board_list", sector_type)

    def fetch_sector_fund_flow_rank(
        self, *, sector_type: str, top_n: int
    ) -> Optional[List[Dict[str, Any]]]:
        return self._respond("fetch_sector_fund_flow_rank", sector_type, top_n)

    def fetch_sector_fund_flow_history(
        self,
        *,
        sector_type: str,
        limit: int,
        top_n: int,
        sector_codes: Optional[List[str]],
    ) -> Optional[Dict[str, Any]]:
        return self._respond(
            "fetch_sector_fund_flow_history", sector_type, limit, top_n, sector_codes
        )


# --------------------------------------------------------------------------
# 用例层：响应信封、字段投影、空数据降级
# --------------------------------------------------------------------------


def test_service_wraps_market_indices_in_envelope() -> None:
    indices = [{"code": "000001", "name": "上证指数", "price": 3200.0}]
    service = SectorService(provider=FakeSectorProvider(fetch_market_indices=indices))

    assert service.get_market_indices(market="a") == {"indices": indices}


def test_service_returns_none_when_market_indices_empty() -> None:
    service = SectorService(provider=FakeSectorProvider(fetch_market_indices=None))

    assert service.get_market_indices(market="a") is None


def test_service_passes_market_key_through_to_cards() -> None:
    payload = {"market": "hk-us", "cards": [{"cardType": "index_quote"}]}
    provider = FakeSectorProvider(fetch_market_cards=payload)
    service = SectorService(provider=provider)

    assert service.get_market_cards(market="hk-us") == payload
    assert provider.calls == [("fetch_market_cards", "hk-us")]


def test_service_degrades_northbound_and_fund_flow_to_placeholders() -> None:
    service = SectorService(provider=FakeSectorProvider())

    assert service.get_northbound_flow() == {"netInflow": None, "name": "北向资金"}
    assert service.get_market_fund_flow() == {
        "mainNetInflow": None,
        "mainNetInflowPercent": None,
        "date": None,
    }


def test_service_projects_fund_flow_sector_list_to_code_and_name() -> None:
    provider = FakeSectorProvider(
        fetch_sector_fund_flow_rank=[{"code": "BK0475", "name": "电池", "latest": 12.34}]
    )
    service = SectorService(provider=provider)

    assert service.get_sector_fund_flow_sector_list(sector_type="industry") == {
        "sectors": [{"code": "BK0475", "name": "电池"}]
    }
    # 下拉框固定取 200 条，这个上限属于用例语义，不交给调用方传参。
    assert provider.calls == [("fetch_sector_fund_flow_rank", "industry", 200)]


def test_service_wraps_board_list_with_actual_total() -> None:
    boards = [
        {"rank": 1, "code": "BK0475", "name": "电池"},
        {"rank": 2, "code": "BK0717", "name": "半导体"},
    ]
    service = SectorService(provider=FakeSectorProvider(fetch_board_list=boards))

    assert service.get_board_list(sector_type="concept") == {
        "sectorType": "concept",
        "total": 2,
        "boards": boards,
    }


def test_service_returns_none_for_empty_board_list() -> None:
    service = SectorService(provider=FakeSectorProvider(fetch_board_list=[]))

    assert service.get_board_list(sector_type="industry") is None


def test_service_does_not_swallow_provider_errors() -> None:
    for error in (LookupError("not found"), RuntimeError("boom")):
        service = SectorService(provider=FakeSectorProvider(error=error))
        with pytest.raises(type(error)):
            service.get_sector_fund_flow_history(
                sector_type="industry", limit=30, top_n=10, sector_codes=["BK0475"]
            )


def test_application_layer_imports_no_outer_packages() -> None:
    for path in sorted(APPLICATION_DIR.glob("*.py")):
        assert (
            _outer_layer_imports(
                path,
                ("fastapi", "sqlalchemy", "data_provider", "src.infrastructure", "api", "bot"),
            )
            == []
        ), path.name


# --------------------------------------------------------------------------
# 端点层：不接触数据源包，全部取数路由走用例依赖
# --------------------------------------------------------------------------


def test_endpoint_module_has_no_direct_provider_import() -> None:
    assert (
        _outer_layer_imports(
            SECTOR_ENDPOINT_PATH,
            ("data_provider", "src.storage", "src.repositories", "src.infrastructure"),
        )
        == []
    )


def test_all_data_routes_depend_on_sector_service() -> None:
    for name in SERVICE_ROUTES:
        handler = getattr(sector_endpoint, name)
        default = inspect.signature(handler).parameters["service"].default
        assert default.dependency is get_sector_service, name


def test_endpoint_no_longer_inlines_shidaotec_requests() -> None:
    source = SECTOR_ENDPOINT_PATH.read_text(encoding="utf-8")

    assert "import requests" not in source
    assert "shidaotec.com" not in source
    assert "getStockMapScale" not in source
    assert "getETFMapScale" not in source


def test_endpoint_maps_snapshot_error_to_502_with_source_message() -> None:
    service = SectorService(
        provider=FakeSectorProvider(
            error=SectorSnapshotUnavailableError("历史快照数据获取失败：10:00")
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        sector_endpoint.get_industry_sectors("10:00", service=service)

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "历史快照数据获取失败：10:00"


# --------------------------------------------------------------------------
# HTTP 契约：状态码与响应字段与迁移前一致
# --------------------------------------------------------------------------


@pytest.fixture
def client(monkeypatch, tmp_path):
    # 本机 ``.env`` 可能是 ``ADMIN_AUTH_ENABLED=true``，认证在请求期判定，
    # 所以 patch 必须覆盖整个用例，而不是只包住 ``create_app``。
    monkeypatch.setattr("api.middlewares.auth.is_auth_enabled", lambda: False)
    return TestClient(create_app(static_dir=tmp_path))


@pytest.fixture
def client_for(client):
    def _override(service: SectorService) -> TestClient:
        client.app.dependency_overrides[get_sector_service] = lambda: service
        return client

    yield _override
    client.app.dependency_overrides.clear()


def test_http_industry_returns_treemap(client_for) -> None:
    treemap = {"total": 1, "sectors": [], "snapshotTime": None}
    http = client_for(
        SectorService(provider=FakeSectorProvider(fetch_industry_treemap=treemap))
    )

    response = http.get("/api/v1/sector/industry", params={"time": "10:00"})

    assert response.status_code == 200
    assert response.json() == treemap


def test_http_industry_maps_snapshot_error_to_502(client_for) -> None:
    http = client_for(
        SectorService(provider=FakeSectorProvider(error=SectorSnapshotUnavailableError("快照缺失")))
    )

    response = http.get("/api/v1/sector/industry")

    assert response.status_code == 502
    assert response.json()["message"] == "快照缺失"


def test_http_empty_payload_maps_to_502(client_for) -> None:
    cases = (
        ("/api/v1/sector/industry", "数据获取失败"),
        ("/api/v1/sector/stock-map", "个股云图数据获取失败"),
        ("/api/v1/sector/etf-map", "ETF 云图数据获取失败"),
        ("/api/v1/sector/concept-map", "概念云图数据获取失败"),
        ("/api/v1/sector/market-indices", "市场指数数据获取失败"),
        ("/api/v1/sector/market-overview", "市场概览数据获取失败"),
        ("/api/v1/sector/market-cards", "市场卡片数据获取失败"),
        ("/api/v1/sector/board-list", "板块列表获取失败"),
        ("/api/v1/sector/fund-flow-sectors", "板块列表获取失败"),
        ("/api/v1/sector/fund-flow-history", "板块资金流排行数据获取失败"),
    )
    http = client_for(SectorService(provider=FakeSectorProvider()))

    for path, message in cases:
        response = http.get(path)
        assert response.status_code == 502, path
        assert response.json()["message"] == message, path


def test_http_invalid_market_is_client_error(client_for) -> None:
    http = client_for(SectorService(provider=FakeSectorProvider()))

    assert http.get("/api/v1/sector/market-indices", params={"market": "hk"}).status_code == 400
    assert http.get("/api/v1/sector/market-cards", params={"market": "us"}).status_code == 400


def test_http_missing_sector_codes_map_to_404(client_for) -> None:
    http = client_for(
        SectorService(provider=FakeSectorProvider(error=LookupError("specified sector codes not found")))
    )

    response = http.get(
        "/api/v1/sector/fund-flow-history", params={"sector_codes": "BK0000"}
    )

    assert response.status_code == 404
    assert response.json()["message"] == "指定的板块代码未找到"


def test_http_northbound_and_fund_flow_degrade_to_200(client_for) -> None:
    http = client_for(SectorService(provider=FakeSectorProvider()))

    northbound = http.get("/api/v1/sector/northbound-flow")
    assert northbound.status_code == 200
    assert northbound.json() == {"netInflow": None, "name": "北向资金"}

    fund_flow = http.get("/api/v1/sector/market-fund-flow")
    assert fund_flow.status_code == 200
    assert fund_flow.json() == {
        "mainNetInflow": None,
        "mainNetInflowPercent": None,
        "date": None,
    }


def test_http_fund_flow_history_splits_sector_codes(client_for) -> None:
    provider = FakeSectorProvider(fetch_sector_fund_flow_history={"dates": [], "sectors": []})
    http = client_for(SectorService(provider=provider))

    http.get("/api/v1/sector/fund-flow-history", params={"sector_codes": " BK0475 , ,BK0717 "})

    assert provider.calls == [
        ("fetch_sector_fund_flow_history", "industry", 30, 10, ["BK0475", "BK0717"])
    ]


def test_http_sector_stocks_stays_empty_contract(client_for) -> None:
    http = client_for(SectorService(provider=FakeSectorProvider()))

    response = http.get("/api/v1/sector/BK0475/stocks")

    assert response.status_code == 200
    assert response.json() == {"total": 0, "stocks": []}


# --------------------------------------------------------------------------
# 适配器层：来源优先级与快照错误翻译
# --------------------------------------------------------------------------


def test_adapter_prefers_stocksdk_over_eastmoney(monkeypatch) -> None:
    monkeypatch.setattr(
        sector_provider,
        "get_cached_market_indices_from_stocksdk",
        lambda market: [{"code": "sdk", "market": market}],
    )
    monkeypatch.setattr(
        sector_provider,
        "get_cached_market_indices_from_eastmoney",
        lambda market: [{"code": "em"}],
    )

    payload = sector_provider.DataProviderSectorProvider().fetch_market_indices(market="a")

    assert payload == [{"code": "sdk", "market": "a"}]


@pytest.mark.parametrize("stocksdk_result", [None, []])
def test_adapter_falls_back_to_eastmoney_when_stocksdk_empty(monkeypatch, stocksdk_result) -> None:
    eastmoney = [{"code": "399001", "name": "深证成指"}]
    monkeypatch.setattr(
        sector_provider, "get_cached_market_indices_from_stocksdk", lambda market: stocksdk_result
    )
    monkeypatch.setattr(
        sector_provider, "get_cached_market_indices_from_eastmoney", lambda market: eastmoney
    )

    assert (
        sector_provider.DataProviderSectorProvider().fetch_market_indices(market="a")
        == eastmoney
    )


def test_adapter_falls_back_when_stocksdk_raises(monkeypatch) -> None:
    def _boom(market: str):
        raise RuntimeError("sdk down")

    eastmoney = [{"code": "000001", "name": "上证指数"}]
    monkeypatch.setattr(sector_provider, "get_cached_market_indices_from_stocksdk", _boom)
    monkeypatch.setattr(
        sector_provider, "get_cached_market_indices_from_eastmoney", lambda market: eastmoney
    )

    assert (
        sector_provider.DataProviderSectorProvider().fetch_market_indices(market="a")
        == eastmoney
    )


def test_adapter_board_list_walks_three_source_chain(monkeypatch) -> None:
    shidaotec = [{"rank": 1, "code": "720000", "name": "传媒"}]
    monkeypatch.setattr(
        sector_provider, "get_cached_board_list_from_stocksdk", lambda sector_type: None
    )
    monkeypatch.setattr(
        sector_provider, "get_cached_board_list_from_eastmoney", lambda sector_type: None
    )
    monkeypatch.setattr(
        sector_provider,
        "get_board_card_list_from_shidaotec",
        lambda sector_type, top_n=200: shidaotec,
    )

    assert (
        sector_provider.DataProviderSectorProvider().fetch_board_list(sector_type="industry")
        == shidaotec
    )


def test_adapter_board_list_returns_none_when_all_sources_empty(monkeypatch) -> None:
    for name in (
        "get_cached_board_list_from_stocksdk",
        "get_cached_board_list_from_eastmoney",
        "get_board_card_list_from_shidaotec",
    ):
        monkeypatch.setattr(sector_provider, name, lambda *args, **kwargs: None)

    assert (
        sector_provider.DataProviderSectorProvider().fetch_board_list(sector_type="industry")
        is None
    )


def test_adapter_board_list_swallows_every_source_error(monkeypatch) -> None:
    def _boom(*args, **kwargs):
        raise RuntimeError("provider down")

    for name in (
        "get_cached_board_list_from_stocksdk",
        "get_cached_board_list_from_eastmoney",
        "get_board_card_list_from_shidaotec",
    ):
        monkeypatch.setattr(sector_provider, name, _boom)

    assert (
        sector_provider.DataProviderSectorProvider().fetch_board_list(sector_type="industry")
        is None
    )


def test_adapter_translates_snapshot_error_and_keeps_message(monkeypatch) -> None:
    def _raise(time_str: str):
        raise sector_provider.SnapshotDataUnavailableError(f"历史快照数据获取失败：{time_str}")

    monkeypatch.setattr(sector_provider, "get_industry_treemap", _raise)
    monkeypatch.setattr(sector_provider, "get_stock_treemap", _raise)
    provider = sector_provider.DataProviderSectorProvider()

    with pytest.raises(SectorSnapshotUnavailableError) as industry_ctx:
        provider.fetch_industry_treemap(time_str="10:00")
    assert str(industry_ctx.value) == "历史快照数据获取失败：10:00"

    with pytest.raises(SectorSnapshotUnavailableError) as stock_ctx:
        provider.fetch_stock_treemap(time_str="14:30")
    assert str(stock_ctx.value) == "历史快照数据获取失败：14:30"


def test_adapter_passes_treemap_arguments(monkeypatch) -> None:
    seen: List[tuple] = []
    monkeypatch.setattr(sector_provider, "get_etf_treemap", lambda **kw: seen.append(("etf", kw)) or {})
    monkeypatch.setattr(
        sector_provider, "get_concept_treemap", lambda **kw: seen.append(("concept", kw)) or {}
    )
    provider = sector_provider.DataProviderSectorProvider()

    provider.fetch_etf_treemap(period="week", top_n=50)
    provider.fetch_concept_treemap(period="month", top_n=80)

    assert seen == [
        ("etf", {"period": "week", "top_n": 50}),
        ("concept", {"period": "month", "top_n": 80}),
    ]


def test_adapter_fund_flow_history_falls_back_and_keeps_lookup_error(monkeypatch) -> None:
    monkeypatch.setattr(
        sector_provider, "get_sector_fund_flow_history_data_from_stocksdk", lambda **kw: None
    )

    def _not_found(**kwargs):
        raise LookupError("specified sector codes not found")

    monkeypatch.setattr(
        sector_provider, "get_sector_fund_flow_history_data_from_eastmoney", _not_found
    )

    with pytest.raises(LookupError):
        sector_provider.DataProviderSectorProvider().fetch_sector_fund_flow_history(
            sector_type="industry", limit=30, top_n=10, sector_codes=["BK0000"]
        )


def test_adapter_fund_flow_rank_passes_sector_type_and_top_n(monkeypatch) -> None:
    monkeypatch.setattr(
        sector_provider, "fetch_sector_fund_flow_rank_from_stocksdk", lambda *args: None
    )
    seen: List[tuple] = []
    monkeypatch.setattr(
        sector_provider,
        "fetch_sector_fund_flow_rank_from_eastmoney",
        lambda *args: seen.append(args) or [{"code": "BK0475", "name": "电池"}],
    )

    payload = sector_provider.DataProviderSectorProvider().fetch_sector_fund_flow_rank(
        sector_type="concept", top_n=200
    )

    assert seen == [("concept", 200)]
    assert payload == [{"code": "BK0475", "name": "电池"}]
