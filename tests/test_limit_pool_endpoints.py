# -*- coding: utf-8 -*-
"""``api/v1/endpoints/limit_pool.py`` 的分层接线、降级语义与数据源适配回归。

该端点曾直接 ``from data_provider.limit_pool import get_limit_pool``，把选源、降级与
响应组装混在一起。现在链路为：端点 → ``LimitPoolService``（用例，失败降级为空榜）
→ ``DataProviderLimitPoolProvider``（适配器）→ ``data_provider/limit_pool``（Manager
负责选源、回退、60s TTL 缓存）。本文件锁定这条契约，避免分层回退。
"""

from __future__ import annotations

import ast
import inspect
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

from api.deps import get_limit_pool_service
from api.v1.endpoints import limit_pool as limit_pool_endpoint
from data_provider import limit_pool as limit_pool_pkg
from data_provider.limit_pool.base import (
    LIMIT_DOWN as DATA_PROVIDER_LIMIT_DOWN,
    LIMIT_UP as DATA_PROVIDER_LIMIT_UP,
    VALID_POOL_TYPES,
)
from src.application.market import (
    LIMIT_DOWN,
    LIMIT_UP,
    VALID_LIMIT_POOL_TYPES,
    LimitPoolService,
)
from src.infrastructure.providers import limit_pool_provider

_APPLICATION_DIR = (
    Path(__file__).resolve().parent.parent / "src" / "application" / "market"
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


class FakeLimitPoolProvider:
    """记录调用参数的端口替身。"""

    def __init__(
        self,
        entries: Optional[List[Dict[str, Any]]] = None,
        error: Optional[BaseException] = None,
    ) -> None:
        self.entries = [] if entries is None else entries
        self.error = error
        self.calls: List[Dict[str, Any]] = []

    def fetch_board(
        self,
        *,
        pool_type: str,
        date: Optional[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        self.calls.append({"pool_type": pool_type, "date": date, "limit": limit})
        if self.error is not None:
            raise self.error
        return self.entries


class LimitPoolServiceTestCase(unittest.TestCase):
    def test_get_board_forwards_request_to_port(self) -> None:
        provider = FakeLimitPoolProvider(entries=[{"code": "600519"}])

        items = LimitPoolService(provider=provider).get_board(
            board=LIMIT_UP, date="20261024", limit=30
        )

        self.assertEqual(items, [{"code": "600519"}])
        self.assertEqual(
            provider.calls,
            [{"pool_type": LIMIT_UP, "date": "20261024", "limit": 30}],
        )

    def test_get_board_degrades_to_empty_list_on_provider_error(self) -> None:
        provider = FakeLimitPoolProvider(error=LookupError("all sources failed"))

        with self.assertLogs("src.application.market.limit_pool", level="WARNING") as logs:
            items = LimitPoolService(provider=provider).get_board(
                board=LIMIT_DOWN, date=None, limit=10
            )

        self.assertEqual(items, [])
        self.assertEqual(
            provider.calls, [{"pool_type": LIMIT_DOWN, "date": None, "limit": 10}]
        )
        self.assertIn("[LimitPool] 获取榜单失败", logs.output[0])
        self.assertIn(LIMIT_DOWN, logs.output[0])

    def test_empty_board_stays_empty_without_error(self) -> None:
        provider = FakeLimitPoolProvider(entries=[])

        self.assertEqual(
            LimitPoolService(provider=provider).get_board(board=LIMIT_UP, limit=5), []
        )

    def test_application_layer_does_not_import_outer_layers(self) -> None:
        for path in sorted(_APPLICATION_DIR.glob("*.py")):
            self.assertEqual(
                _outer_layer_imports(
                    path,
                    ("fastapi", "sqlalchemy", "data_provider", "src.infrastructure", "api", "bot"),
                ),
                [],
                path.name,
            )


class LimitPoolBoardVocabularyTestCase(unittest.TestCase):
    def test_board_constants_match_data_provider_contract(self) -> None:
        self.assertEqual(LIMIT_UP, DATA_PROVIDER_LIMIT_UP)
        self.assertEqual(LIMIT_DOWN, DATA_PROVIDER_LIMIT_DOWN)
        self.assertEqual(VALID_LIMIT_POOL_TYPES, VALID_POOL_TYPES)


class LimitPoolEndpointWiringTestCase(unittest.TestCase):
    def test_endpoint_module_has_no_direct_provider_import(self) -> None:
        self.assertEqual(
            _outer_layer_imports(
                Path(limit_pool_endpoint.__file__),
                ("data_provider", "src.storage", "src.repositories", "src.infrastructure"),
            ),
            [],
        )

    def test_routes_depend_on_limit_pool_service(self) -> None:
        for endpoint in (
            limit_pool_endpoint.get_limit_up_board,
            limit_pool_endpoint.get_limit_down_board,
        ):
            param = inspect.signature(endpoint).parameters.get("service")
            self.assertIsNotNone(param, endpoint.__name__)
            self.assertEqual(param.default.dependency, get_limit_pool_service)

    def test_routes_forward_board_and_echo_requested_date(self) -> None:
        provider = FakeLimitPoolProvider(entries=[{"code": "600519", "name": "贵州茅台"}])

        up = limit_pool_endpoint.get_limit_up_board(
            date="20261024", limit=30, service=LimitPoolService(provider=provider)
        )
        down = limit_pool_endpoint.get_limit_down_board(
            date=None, limit=20, service=LimitPoolService(provider=provider)
        )

        self.assertEqual(
            up, {"date": "20261024", "items": [{"code": "600519", "name": "贵州茅台"}]}
        )
        # date 缺省时回显当天交易日，不依赖数据源返回的 date
        self.assertRegex(down["date"], r"^\d{8}$")
        self.assertEqual(
            [call["pool_type"] for call in provider.calls], [LIMIT_UP, LIMIT_DOWN]
        )
        self.assertEqual([call["limit"] for call in provider.calls], [30, 20])

    def test_route_response_keeps_empty_items_on_failure(self) -> None:
        provider = FakeLimitPoolProvider(error=RuntimeError("upstream down"))

        payload = limit_pool_endpoint.get_limit_up_board(
            date="20261024", limit=100, service=LimitPoolService(provider=provider)
        )

        self.assertEqual(payload, {"date": "20261024", "items": []})


class DataProviderLimitPoolAdapterTestCase(unittest.TestCase):
    def test_fetch_board_maps_entries_to_dicts_and_forwards_request(self) -> None:
        captured: Dict[str, Any] = {}
        entry = limit_pool_pkg.LimitPoolEntry(
            code="600519", name="贵州茅台", price=1234.5, consecutive_boards=2
        )

        def fake_get_limit_pool(
            pool_type: str = LIMIT_UP,
            date: Optional[str] = None,
            n: int = 20,
        ) -> Any:
            captured.update(pool_type=pool_type, date=date, n=n)
            return limit_pool_pkg.LimitPoolResult(entries=[entry])

        with patch.object(limit_pool_provider, "get_limit_pool", fake_get_limit_pool):
            items = limit_pool_provider.DataProviderLimitPoolProvider().fetch_board(
                pool_type=LIMIT_UP, date="20261024", limit=25
            )

        self.assertEqual(
            captured, {"pool_type": LIMIT_UP, "date": "20261024", "n": 25}
        )
        self.assertEqual(len(items), 1)
        # 字段集与 LimitPoolEntry 契约一致，未在适配器里增删
        self.assertEqual(set(items[0]), set(limit_pool_pkg.LimitPoolEntry().to_dict()))
        self.assertEqual(items[0]["price"], 1234.5)
        self.assertEqual(items[0]["consecutive_boards"], 2)

    def test_fetch_board_returns_empty_list_for_empty_result(self) -> None:
        with patch.object(
            limit_pool_provider,
            "get_limit_pool",
            lambda **_: limit_pool_pkg.LimitPoolResult(entries=[]),
        ):
            self.assertEqual(
                limit_pool_provider.DataProviderLimitPoolProvider().fetch_board(
                    pool_type=LIMIT_DOWN, date=None, limit=10
                ),
                [],
            )

    def test_fetch_board_propagates_provider_error(self) -> None:
        """适配器不做二次降级：异常上抛给用例层统一处理。"""

        def boom(**_: Any) -> Any:
            raise LookupError("no available source")

        with patch.object(limit_pool_provider, "get_limit_pool", boom):
            with self.assertRaises(LookupError):
                limit_pool_provider.DataProviderLimitPoolProvider().fetch_board(
                    pool_type=LIMIT_UP, date=None, limit=10
                )

    def test_entry_serialization_failure_is_regulated_by_the_use_case(self) -> None:
        """序列化也被纳入用例的 fail-open 边界。

        旧端点的 ``to_dict()`` 写在 ``try`` 之外，序列化异常会直接 500；改为适配器
        后序列化在用例的 ``try`` 内，与取数失败同样降级为空榜（差异已在对账中确认）。
        """

        class _BrokenEntry:
            def to_dict(self) -> Dict[str, Any]:
                raise ValueError("to_dict boom")

        with patch.object(
            limit_pool_provider,
            "get_limit_pool",
            lambda **_: limit_pool_pkg.LimitPoolResult(entries=[_BrokenEntry()]),
        ):
            with self.assertLogs("src.application.market.limit_pool", level="WARNING"):
                items = LimitPoolService(
                    provider=limit_pool_provider.DataProviderLimitPoolProvider()
                ).get_board(board=LIMIT_UP, limit=10)

        self.assertEqual(items, [])


if __name__ == "__main__":
    unittest.main()
