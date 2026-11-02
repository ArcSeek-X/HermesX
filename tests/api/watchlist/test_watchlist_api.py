# -*- coding: utf-8 -*-
"""自选股路由依赖接线回归测试。

``api/v1/endpoints/watchlist.py`` 曾持有模块级 ``DatabaseManager`` 单例，
导致导入 ``api.app`` 时立即建库。现在路由只依赖 ``Depends(get_watchlist_service)``
获取应用用例，本文件锁定该契约，避免回退到导入期副作用或直连持久化层。
"""

from __future__ import annotations

import inspect
import os
import tempfile
import unittest
from pathlib import Path

from api.deps import get_watchlist_service
from api.v1.endpoints import watchlist
from api.v1.schemas.watchlist import (
    WatchlistGroupCreate,
    WatchlistItemsQueryRequest,
)
from src.bootstrap.watchlist import build_watchlist_service
from src.config import Config
from src.storage import DatabaseManager


class WatchlistDependencyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._data_dir = Path(self._temp_dir.name)
        self._previous_database_path = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = str(self._data_dir / "watchlist.db")
        Config.reset_instance()
        DatabaseManager.reset_instance()
        self.db_manager = DatabaseManager.get_instance()

    def tearDown(self) -> None:
        DatabaseManager.reset_instance()
        Config.reset_instance()
        if self._previous_database_path is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = self._previous_database_path
        self._temp_dir.cleanup()

    def test_router_has_no_module_level_database_singleton(self) -> None:
        self.assertFalse(
            hasattr(watchlist, "db"),
            "watchlist router must not hold a module-level DatabaseManager instance",
        )
        self.assertFalse(
            hasattr(watchlist, "db_manager"),
            "watchlist router must not hold a module-level DatabaseManager instance",
        )

    def test_every_route_injects_the_watchlist_use_case_dependency(self) -> None:
        routes = [route for route in watchlist.router.routes if hasattr(route, "endpoint")]
        self.assertTrue(routes, "watchlist router must expose at least one route")
        for route in routes:
            parameters = inspect.signature(route.endpoint).parameters
            self.assertIn(
                "service",
                parameters,
                f"{route.path} must receive the watchlist use case via dependency injection",
            )
            dependency = parameters["service"].default
            self.assertIs(
                getattr(dependency, "dependency", None),
                get_watchlist_service,
                f"{route.path} must depend on api.deps.get_watchlist_service",
            )

    def test_group_queries_use_the_injected_use_case(self) -> None:
        service = build_watchlist_service()
        created = watchlist.create_watchlist_group(
            payload=WatchlistGroupCreate(name="核心持仓"),
            service=service,
        )
        self.assertEqual(created["name"], "核心持仓")
        self.assertEqual(created["item_count"], 0)
        self.assertTrue(created["group_code"].startswith("WG-"))

        groups = watchlist.get_watchlist_groups(service=service)
        self.assertEqual([group["name"] for group in groups], ["核心持仓"])

        page = watchlist.get_watchlist_items(
            payload=WatchlistItemsQueryRequest(
                group_id=created["id"],
                pageNum=1,
                pageSize=10,
            ),
            service=service,
        )
        self.assertEqual(page["total"], 0)
        self.assertEqual(page["list"], [])


if __name__ == "__main__":
    unittest.main()
