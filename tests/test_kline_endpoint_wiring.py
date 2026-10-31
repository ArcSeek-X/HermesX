# -*- coding: utf-8 -*-
"""``api/v1/endpoints/kline.py`` 的分层接线、契约整形与数据源适配回归。

该端点曾直接 ``from data_provider.{code_search,kline,stock_info}.base import ...``，
把取数、单位换算与响应组装混在一起。现在链路为：端点 → ``QuoteService``（用例：
对外契约整形）→ ``DataProviderQuoteProvider``（适配器：dataclass → 字典）→
``data_provider`` 各能力 Manager（选源、回退、TTL、健康冷却保持原位）。
"""

from __future__ import annotations

import ast
import inspect
import tempfile
import unittest
from dataclasses import fields
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.app import create_app
from api.deps import get_quote_service
from api.v1.endpoints import kline as kline_endpoint
from data_provider.kline.base import KLineResult
from data_provider.stock_info.base import StockInfoResult
from src.application.quote import QuoteDataError, QuoteService
from src.infrastructure.providers import kline_provider

_APPLICATION_DIR = (
    Path(__file__).resolve().parent.parent / "src" / "application" / "quote"
)


def _imported_modules(path: Path) -> List[str]:
    """返回文件里出现的全部 import 目标（含 ``import a.b`` 的绝对名）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            modules.append(node.module or "")
        elif isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
    return modules


def _outer_layer_imports(path: Path, forbidden_roots: tuple) -> List[str]:
    """返回文件里命中禁用根包的 import 目标（空列表表示分层干净）。"""
    hits: List[str] = []
    for module in _imported_modules(path):
        for root in forbidden_roots:
            if module == root or module.startswith(root + "."):
                hits.append(module)
                break
    return hits


def _kline_result(**overrides: Any) -> KLineResult:
    payload: Dict[str, Any] = {
        "stock_code": "600519",
        "stock_name": "贵州茅台",
        "period": "daily",
        "secid": "1.600519",
        "prev_close": 1660.0,
        "source": "eastmoney",
        "data": [
            {
                "date": "2026-10-23",
                "open": 1.0,
                "close": 2.0,
                "high": 3.0,
                "low": 0.5,
                "volume": 123400,
                "prev_close": 1650.0,
            }
        ],
    }
    payload.update(overrides)
    return KLineResult(**payload)


def _stock_info_result(**overrides: Any) -> StockInfoResult:
    payload: Dict[str, Any] = {
        "stock_code": "600519",
        "stock_name": "贵州茅台",
        "current_price": 1690.0,
        "change": 1.0,
        "change_percent": 0.06,
        "open": 1680.0,
        "prev_close": 1689.0,
        "high": 1695.0,
        "low": 1675.0,
        "volume": 1000.0,
        "amount": 1690000.0,
        "turnover_rate": 0.1,
        "amplitude": 1.2,
        "pe_ratio_ttm": 30.0,
        "total_market_cap": 2.1e12,
        "source": "local",
    }
    payload.update(overrides)
    return StockInfoResult(**payload)


class FakeQuoteProvider:
    """记录调用参数，并按需返回固定值或抛错。"""

    def __init__(
        self,
        *,
        search: Optional[List[Dict[str, Any]]] = None,
        kline: Optional[Dict[str, Any]] = None,
        info: Optional[Dict[str, Any]] = None,
        error: Optional[BaseException] = None,
    ) -> None:
        self.search = search or []
        self.kline = kline
        self.info = info
        self.error = error
        self.calls: List[tuple] = []

    def search_codes(self, *, keyword: str, limit: int) -> List[Dict[str, Any]]:
        self.calls.append(("search_codes", keyword, limit))
        if self.error is not None:
            raise self.error
        return self.search

    def fetch_kline(
        self,
        *,
        stock_code: str,
        period: str,
        limit: int,
        fqt: int,
        before_date: Optional[str],
    ) -> Dict[str, Any]:
        self.calls.append(("fetch_kline", stock_code, period, limit, fqt, before_date))
        if self.error is not None:
            raise self.error
        assert self.kline is not None, "测试需显式提供 kline 载荷"
        return self.kline

    def fetch_stock_info(self, *, stock_code: str) -> Dict[str, Any]:
        self.calls.append(("fetch_stock_info", stock_code))
        if self.error is not None:
            raise self.error
        assert self.info is not None, "测试需显式提供 info 载荷"
        return self.info


class QuoteServiceContractTestCase(unittest.TestCase):
    """用例层只做对外契约整形，不吞取数异常。"""

    def test_search_codes_forwards_keyword_and_limit(self) -> None:
        provider = FakeQuoteProvider(
            search=[{"code": "600519", "name": "贵州茅台", "market": "SH", "secid": "1.600519"}]
        )
        service = QuoteService(provider=provider)

        payload = service.search_codes(keyword="茅台", limit=5)

        self.assertEqual(
            payload, [{"code": "600519", "name": "贵州茅台", "market": "SH", "secid": "1.600519"}]
        )
        self.assertEqual(provider.calls, [("search_codes", "茅台", 5)])

    def test_get_kline_converts_volume_to_lots_and_drops_row_prev_close(self) -> None:
        provider = FakeQuoteProvider(
            kline={
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "period": "daily",
                "secid": "1.600519",
                "prev_close": 1660.0,
                "source": "eastmoney",
                "data": [
                    {"date": "2026-10-23", "open": 1.0, "close": 2.0, "high": 3.0, "low": 0.5, "volume": 123400, "prev_close": 1650.0},
                ],
            }
        )
        service = QuoteService(provider=provider)

        payload = service.get_kline(stock_code="600519", period="daily", limit=250)

        row = payload["data"][0]
        self.assertEqual(row["volume"], 1234.0)
        self.assertNotIn("prev_close", row)
        # 顶层 prev_close 是响应契约的一部分，必须保留（分时图按它算涨跌幅）。
        self.assertEqual(payload["prev_close"], 1660.0)
        self.assertEqual(provider.calls, [("fetch_kline", "600519", "daily", 250, 1, None)])

    def test_get_kline_tolerates_missing_volume_and_empty_rows(self) -> None:
        rows = [
            {"date": "2026-10-23", "open": 1.0, "close": 2.0, "high": 3.0, "low": 0.5},
        ]
        provider = FakeQuoteProvider(
            kline={
                "stock_code": "600519",
                "stock_name": None,
                "period": "daily",
                "secid": "1.600519",
                "prev_close": None,
                "source": "local",
                "data": rows,
            }
        )
        service = QuoteService(provider=provider)

        payload = service.get_kline(stock_code="600519", period="daily", limit=1)

        self.assertIsNone(payload["data"][0].get("volume"))
        self.assertEqual(payload["data"][0]["date"], "2026-10-23")

    def test_get_kline_does_not_swallow_provider_errors(self) -> None:
        for error in (LookupError("no source"), ValueError("bad period"), RuntimeError("boom")):
            service = QuoteService(provider=FakeQuoteProvider(error=error))
            with self.assertRaises(type(error)):
                service.get_kline(stock_code="600519", period="daily", limit=1)

    def test_malformed_row_raises_quote_data_error_not_value_error(self) -> None:
        """整形失败不能是 ``ValueError``，否则端点的 422 分支会把它归错到客户端。"""
        provider = FakeQuoteProvider(
            kline={
                "stock_code": "600519",
                "period": "daily",
                "secid": "1.600519",
                "data": ["not-a-row"],
            }
        )
        service = QuoteService(provider=provider)

        with self.assertRaises(QuoteDataError) as ctx:
            service.get_kline(stock_code="600519", period="daily", limit=1)

        self.assertNotIsInstance(ctx.exception, ValueError)
        self.assertIn("第 0 行", str(ctx.exception))

    def test_get_stock_info_adds_update_time_none(self) -> None:
        provider = FakeQuoteProvider(info={"stock_code": "600519", "current_price": 1690.0})
        service = QuoteService(provider=provider)

        payload = service.get_stock_info(stock_code="600519")

        self.assertIsNone(payload["update_time"])
        self.assertEqual(provider.calls, [("fetch_stock_info", "600519")])

    def test_application_layer_imports_no_outer_packages(self) -> None:
        for path in sorted(_APPLICATION_DIR.glob("*.py")):
            self.assertEqual(
                _outer_layer_imports(
                    path, ("fastapi", "sqlalchemy", "data_provider", "src.infrastructure", "api", "bot")
                ),
                [],
                path.name,
            )


class KlineEndpointLayeringTestCase(unittest.TestCase):
    def test_endpoint_module_has_no_direct_provider_or_storage_import(self) -> None:
        self.assertEqual(
            _outer_layer_imports(
                Path(kline_endpoint.__file__),
                ("data_provider", "src.storage", "src.repositories", "src.infrastructure"),
            ),
            [],
        )

    def test_all_routes_depend_on_quote_service(self) -> None:
        for handler in (
            kline_endpoint.search_stocks,
            kline_endpoint.get_kline_endpoint,
            kline_endpoint.get_stock_info_endpoint,
        ):
            default = inspect.signature(handler).parameters["service"].default
            self.assertIs(default.dependency, get_quote_service, handler.__name__)


class KlineEndpointHttpContractTestCase(unittest.TestCase):
    """走真实 HTTP：Query 校验、错误映射与响应字段都不变。"""

    @classmethod
    def setUpClass(cls) -> None:
        # 本机 ``.env`` 可能是 ``ADMIN_AUTH_ENABLED=true``，会让 ``/api/v1/*`` 全部 401；
        # 认证在请求期判定，必须让 patch 覆盖整个用例类而不是只包住 ``create_app``。
        cls._auth_patch = patch("api.middlewares.auth.is_auth_enabled", return_value=False)
        cls._auth_patch.start()
        cls._temp_dir = tempfile.TemporaryDirectory()
        cls.client = TestClient(create_app(static_dir=Path(cls._temp_dir.name)))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temp_dir.cleanup()
        cls._auth_patch.stop()

    def setUp(self) -> None:
        kline_endpoint._kline_cache.clear()
        kline_endpoint._info_cache.clear()
        kline_endpoint._search_cache.clear()

    def _client_with(self, service: QuoteService) -> TestClient:
        self.client.app.dependency_overrides[get_quote_service] = lambda: service
        self.addCleanup(self.client.app.dependency_overrides.clear)
        return self.client

    def _kline_payload(self) -> Dict[str, Any]:
        return {
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "period": "daily",
            "secid": "1.600519",
            "prev_close": 1660.0,
            "source": "eastmoney",
            "data": [
                {"date": "2026-10-23", "open": 1.0, "close": 2.0, "high": 3.0, "low": 0.5, "volume": 123400, "prev_close": 1650.0},
            ],
        }

    def test_kline_returns_lots_and_keeps_top_level_prev_close(self) -> None:
        service = QuoteService(provider=FakeQuoteProvider(kline=self._kline_payload()))
        client = self._client_with(service)

        response = client.get("/api/v1/kline/600519/kline", params={"period": "daily", "limit": 10})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["stock_code"], "600519")
        self.assertEqual(body["prev_close"], 1660.0)
        self.assertEqual(body["data"][0]["volume"], 1234.0)
        self.assertNotIn("prev_close", body["data"][0])

    def test_kline_maps_provider_errors_to_http_status(self) -> None:
        cases = ((LookupError("none"), 404), (ValueError("bad"), 422), (RuntimeError("boom"), 502))
        for error, expected in cases:
            kline_endpoint._kline_cache.clear()
            service = QuoteService(provider=FakeQuoteProvider(error=error))
            client = self._client_with(service)
            response = client.get("/api/v1/kline/600519/kline")
            self.assertEqual(response.status_code, expected, type(error).__name__)

    def test_kline_rejects_invalid_query(self) -> None:
        service = QuoteService(provider=FakeQuoteProvider(kline=self._kline_payload()))
        client = self._client_with(service)

        self.assertEqual(client.get("/api/v1/kline/600519/kline", params={"limit": 0}).status_code, 422)
        self.assertEqual(client.get("/api/v1/kline/600519/kline", params={"fqt": 3}).status_code, 422)
        self.assertEqual(client.get("/api/v1/kline/600519/kline", params={"period": "2h"}).status_code, 422)

    def test_info_returns_contract_fields_and_maps_errors(self) -> None:
        info = {
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "current_price": 1690.0,
            "source": "local",
        }
        ok_client = self._client_with(QuoteService(provider=FakeQuoteProvider(info=info)))
        ok = ok_client.get("/api/v1/kline/600519/info")
        self.assertEqual(ok.status_code, 200)
        self.assertIsNone(ok.json()["update_time"])

        kline_endpoint._info_cache.clear()
        fail_client = self._client_with(QuoteService(provider=FakeQuoteProvider(error=LookupError("none"))))
        self.assertEqual(fail_client.get("/api/v1/kline/600519/info").status_code, 404)

        kline_endpoint._info_cache.clear()
        boom_client = self._client_with(QuoteService(provider=FakeQuoteProvider(error=RuntimeError("boom"))))
        self.assertEqual(boom_client.get("/api/v1/kline/600519/info").status_code, 502)

    def test_search_returns_results_and_maps_errors(self) -> None:
        search = [{"code": "600519", "name": "贵州茅台", "market": "SH", "secid": "1.600519"}]
        ok = self._client_with(QuoteService(provider=FakeQuoteProvider(search=search))).get(
            "/api/v1/kline/search", params={"q": "茅台"}
        )
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["results"], search)

        kline_endpoint._search_cache.clear()
        fail = self._client_with(QuoteService(provider=FakeQuoteProvider(error=RuntimeError("boom")))).get(
            "/api/v1/kline/search", params={"q": "茅台"}
        )
        self.assertEqual(fail.status_code, 502)
        # 全局错误处理器把 HTTPException 归一为 {"error", "message", "detail"}。
        self.assertEqual(fail.json()["message"], "股票搜索数据获取失败")

    def test_malformed_upstream_row_is_reported_as_upstream_failure(self) -> None:
        """上游行不是字典时归入 502，而不是 422（参数错误）或 500。

        迁移前 ``dict(row)`` 在端点 ``try`` 之外，会直接 500；这是本片唯一的行为
        差异，归属为「上游数据格式异常」。用例抛专用 ``QuoteDataError``，避免被
        端点的 ``ValueError → 422`` 分支误判。
        """
        payload = self._kline_payload()
        payload["data"] = ["not-a-row"]
        service = QuoteService(provider=FakeQuoteProvider(kline=payload))
        client = self._client_with(service)

        response = client.get("/api/v1/kline/600519/kline")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["message"], "K 线数据获取失败")


class DataProviderQuoteAdapterTestCase(unittest.TestCase):
    def test_search_maps_code_search_results(self) -> None:
        item = type(
            "Row",
            (),
            {"code": "600519", "name": "贵州茅台", "market": "SH", "secid": "1.600519", "source": "local"},
        )()
        with patch.object(kline_provider, "search_codes", return_value=[item]) as fake:
            payload = kline_provider.DataProviderQuoteProvider().search_codes(keyword="茅台", limit=10)

        self.assertEqual(payload, [{"code": "600519", "name": "贵州茅台", "market": "SH", "secid": "1.600519"}])
        fake.assert_called_once_with("茅台", limit=10)

    def test_fetch_kline_builds_request_and_keeps_rows_raw(self) -> None:
        result = _kline_result()
        with patch.object(kline_provider, "get_kline_data", return_value=result) as fake:
            payload = kline_provider.DataProviderQuoteProvider().fetch_kline(
                stock_code="600519",
                period="weekly",
                limit=150,
                fqt=2,
                before_date="2026-10-01",
            )

        request = fake.call_args.args[0]
        self.assertEqual(
            (request.stock_code, request.period, request.limit, request.fqt, request.before_date),
            ("600519", "weekly", 150, 2, "2026-10-01"),
        )
        # 适配器只做字段收敛：单位与行内 prev_close 原样保留，整形在用例层。
        self.assertEqual(payload["data"][0]["volume"], 123400)
        self.assertEqual(payload["data"][0]["prev_close"], 1650.0)
        self.assertEqual(payload["source"], "eastmoney")

    def test_fetch_stock_info_field_set_matches_result_dataclass(self) -> None:
        with patch.object(kline_provider, "get_stock_info", return_value=_stock_info_result()):
            payload = kline_provider.DataProviderQuoteProvider().fetch_stock_info(stock_code="600519")

        expected = {f.name for f in fields(StockInfoResult)} - {"metadata"}
        self.assertEqual(set(payload), expected)

    def test_adapter_does_not_swallow_errors(self) -> None:
        provider = kline_provider.DataProviderQuoteProvider()
        with patch.object(kline_provider, "get_kline_data", side_effect=LookupError("none")):
            with self.assertRaises(LookupError):
                provider.fetch_kline(
                    stock_code="600519", period="daily", limit=1, fqt=1, before_date=None
                )
        with patch.object(kline_provider, "get_stock_info", side_effect=ValueError("bad")):
            with self.assertRaises(ValueError):
                provider.fetch_stock_info(stock_code="600519")


if __name__ == "__main__":
    unittest.main()
