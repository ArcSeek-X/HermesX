# -*- coding: utf-8 -*-
"""自选股用例与仓储的行为回归测试。

覆盖从 HTTP 层下沉到 ``src/application/watchlist`` + ``watchlist_repo`` 后的业务契约：
编码生成、重名/重复股票冲突、删除分类级联软删、移动归类与分页统计。
测试用临时数据库与假代码核验器，不依赖股票索引文件或网络。
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from typing import Iterable

from src.application.watchlist import (
    UnknownStockCodeError,
    WatchlistConflictError,
    WatchlistNotFoundError,
    WatchlistService,
    WatchlistValidationError,
)
from src.config import Config
from src.infrastructure.persistence.repositories.watchlist_repo import (
    SqlAlchemyWatchlistRepository,
)
from src.storage import DatabaseManager


class _FakeCodeValidator:
    def __init__(self, known: Iterable[str] = ("600519.SH", "00700.HK")) -> None:
        self._known = set(known)

    def is_known(self, stock_code: str) -> bool:
        return stock_code in self._known


class WatchlistUseCaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._previous_database_path = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = str(Path(self._temp_dir.name) / "watchlist.db")
        Config.reset_instance()
        DatabaseManager.reset_instance()
        self.db_manager = DatabaseManager.get_instance()
        self.service = WatchlistService(
            repository=SqlAlchemyWatchlistRepository(self.db_manager),
            stock_code_validator=_FakeCodeValidator(),
        )

    def tearDown(self) -> None:
        DatabaseManager.reset_instance()
        Config.reset_instance()
        if self._previous_database_path is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = self._previous_database_path
        self._temp_dir.cleanup()

    def test_group_code_and_sort_order_are_generated_in_creation_order(self) -> None:
        first = self.service.create_group(name=" 核心持仓 ")
        second = self.service.create_group(name="观察池")

        self.assertEqual(first["name"], "核心持仓")
        self.assertEqual(first["sort_order"], 0)
        self.assertEqual(second["sort_order"], 1)
        self.assertTrue(first["group_code"].endswith("-000001"))
        self.assertTrue(second["group_code"].endswith("-000002"))
        self.assertEqual([group["name"] for group in self.service.list_groups()], ["核心持仓", "观察池"])

    def test_duplicate_group_name_is_a_conflict(self) -> None:
        self.service.create_group(name="核心持仓")

        with self.assertRaises(WatchlistConflictError) as ctx:
            self.service.create_group(name="核心持仓")
        self.assertEqual(ctx.exception.error_code, "duplicate_name")

        second = self.service.create_group(name="观察池")
        with self.assertRaises(WatchlistConflictError):
            self.service.update_group(group_code=second["group_code"], name="核心持仓")

    def test_empty_group_name_is_rejected_before_touching_the_database(self) -> None:
        with self.assertRaises(WatchlistValidationError) as ctx:
            self.service.create_group(name="   ")
        self.assertEqual(ctx.exception.error_code, "invalid_name")

    def test_unknown_stock_code_is_rejected(self) -> None:
        group = self.service.create_group(name="核心持仓")

        with self.assertRaises(UnknownStockCodeError):
            self.service.create_item(group_id=group["id"], stock_code="000000.XX")

        with self.assertRaises(WatchlistValidationError):
            self.service.create_item(group_id=group["id"], stock_code="   ")

    def test_delete_group_cascades_soft_delete_to_items(self) -> None:
        group = self.service.create_group(name="核心持仓")
        self.service.create_item(group_id=group["id"], stock_code="600519.SH", stock_name="贵州茅台")

        self.service.delete_group(group["group_code"])

        self.assertEqual(self.service.list_groups(), [])
        page = self.service.list_items(group_id=group["id"], page_num=1, page_size=10)
        self.assertEqual((page.total, page.items), (0, []))
        with self.assertRaises(WatchlistNotFoundError):
            self.service.delete_group(group["group_code"])

    def test_move_item_rejects_duplicate_in_target_group(self) -> None:
        source = self.service.create_group(name="核心持仓")
        target = self.service.create_group(name="观察池")
        item = self.service.create_item(group_id=source["id"], stock_code="600519.SH")
        self.service.create_item(group_id=target["id"], stock_code="600519.SH")

        with self.assertRaises(WatchlistConflictError):
            self.service.move_item(item_id=item["id"], target_group_id=target["id"])

        other = self.service.create_item(group_id=source["id"], stock_code="00700.HK")
        moved = self.service.move_item(item_id=other["id"], target_group_id=target["id"])
        self.assertEqual(moved["group_id"], target["id"])

    def test_items_are_paginated_with_stable_total(self) -> None:
        group = self.service.create_group(name="核心持仓")
        for code in ("600519.SH", "00700.HK"):
            self.service.create_item(group_id=group["id"], stock_code=code)

        first_page = self.service.list_items(group_id=group["id"], page_num=1, page_size=1)
        second_page = self.service.list_items(group_id=group["id"], page_num=2, page_size=1)

        self.assertEqual(first_page.total, 2)
        self.assertEqual(len(first_page.items), 1)
        self.assertEqual(len(second_page.items), 1)
        self.assertNotEqual(first_page.items[0]["id"], second_page.items[0]["id"])

    def test_missing_group_is_reported_for_item_operations(self) -> None:
        with self.assertRaises(WatchlistNotFoundError):
            self.service.list_items(group_id=9999, page_num=1, page_size=10)
        with self.assertRaises(WatchlistNotFoundError):
            self.service.create_item(group_id=9999, stock_code="600519.SH")


if __name__ == "__main__":
    unittest.main()
