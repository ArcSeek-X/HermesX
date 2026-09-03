# -*- coding: utf-8 -*-
"""快讯 ``importance`` 统一业务量纲回归测试（P0 量纲改造）。

覆盖 docs/Live-calendar.md §5.7.9 的核心断言：
1. ``normalize_live_news_importance`` 映射正确（缺失 / 非法 -> 0）；
2. 存量迁移正确性（上游 score -> 业务量纲，NULL -> 0，非 channel 行不受影响）；
3. 迁移幂等性（连续执行两次 / 重启后结果不变）；
4. 「重要」判定迁移前后等价（阈值 2 vs 3）。

本文件仅依赖 ``src.storage`` / ``src.services.intelligence_service``，不触网、
不依赖完整后端依赖链（litellm 等），可离线运行。
"""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from src.services.intelligence_service import IntelligenceService


class NormalizeImportanceTest(unittest.TestCase):
    """归一化入口映射（语义守恒，缺失归 0）。"""

    def test_score_to_unified_scale(self) -> None:
        cases = {
            1: 1,   # 普通 -> 普通
            2: 3,   # 重要 -> 重要
            3: 4,   # 非常重要 -> 非常重要
        }
        for raw, expected in cases.items():
            self.assertEqual(
                IntelligenceService.normalize_live_news_importance(raw),
                expected,
            )

    def test_missing_is_none_not_normal(self) -> None:
        # 「没告诉我」≠「这是普通的」：缺失 / 非法必须归 0（无），不可兜底为 1
        for raw in (None, 0, 9, -1, "x", ""):
            self.assertEqual(
                IntelligenceService.normalize_live_news_importance(raw),
                0,
            )


class _MigrationHarness(unittest.TestCase):
    """迁移测试的公共脚手架：临时 SQLite + 还原「存量库待升级」场景。"""

    def setUp(self) -> None:
        from src.storage import DatabaseManager

        self._tmp = tempfile.TemporaryDirectory()
        self._env = patch.dict(
            os.environ,
            {"DATABASE_PATH": os.path.join(self._tmp.name, "test.db")},
        )
        self._env.start()
        DatabaseManager.reset_instance()
        self._db = DatabaseManager.get_instance()
        self._seed()
        self._remove_migration_marker()  # 还原存量库待升级场景

    def tearDown(self) -> None:
        from src.storage import DatabaseManager

        DatabaseManager.reset_instance()
        self._env.stop()
        self._tmp.cleanup()

    def _seed(self) -> None:
        from src.storage import IntelligenceItem

        rows = [
            ("channel", "global", 1, "news_score_1"),
            ("channel", "global", 2, "news_score_2"),
            ("channel", "global", 3, "news_score_3"),
            ("channel", "global", None, "news_null"),
            ("market", "cn", None, "generic_market_null"),
            ("calendar", "macro", 4, "calendar_already_new_scale"),
        ]
        with self._db.get_session() as session:
            for scope_type, scope_value, importance, title in rows:
                session.add(IntelligenceItem(
                    source_name="seed",
                    source_type="wscn_live_news" if scope_type == "channel" else "other",
                    title=title,
                    url=f"seed/{title}",
                    scope_type=scope_type,
                    scope_value=scope_value,
                    market="cn",
                    importance=importance,
                ))
            session.commit()

    def _remove_migration_marker(self) -> None:
        from src.storage import (
            LIVE_NEWS_IMPORTANCE_RESCALE_VERSION,
            DatabaseSchemaMigration,
        )

        with self._db.get_session() as session:
            session.query(DatabaseSchemaMigration).filter_by(
                version=LIVE_NEWS_IMPORTANCE_RESCALE_VERSION
            ).delete()
            session.commit()

    def _dump(self) -> dict:
        from src.storage import IntelligenceItem

        with self._db.get_session() as session:
            return {
                row.title: row.importance
                for row in session.query(IntelligenceItem).all()
            }

    def _run_migration(self) -> None:
        self._db._ensure_live_news_importance_rescaled()


class MigrationCorrectnessTest(_MigrationHarness):
    """迁移正确性。"""

    def test_channel_rows_rescaled(self) -> None:
        self._run_migration()
        data = self._dump()
        self.assertEqual(data["news_score_1"], 1)   # 普通保持
        self.assertEqual(data["news_score_2"], 3)   # 重要 -> 3
        self.assertEqual(data["news_score_3"], 4)   # 非常重要 -> 4
        self.assertEqual(data["news_null"], 0)      # NULL -> 0（无）

    def test_non_channel_rows_untouched(self) -> None:
        self._run_migration()
        data = self._dump()
        self.assertIsNone(data["generic_market_null"])   # 通用资讯 NULL 不受影响
        self.assertEqual(data["calendar_already_new_scale"], 4)  # 日历行不受影响


class MigrationIdempotencyTest(_MigrationHarness):
    """迁移幂等性（最关键：迁移前后取值集合有交集，重复执行会二次映射）。"""

    def test_twice_in_same_instance(self) -> None:
        self._run_migration()
        first = self._dump()
        self._run_migration()
        self.assertEqual(first, self._dump())

    def test_restart_does_not_rescale_again(self) -> None:
        from src.storage import DatabaseManager

        self._run_migration()
        first = self._dump()
        DatabaseManager.reset_instance()  # 模拟重启
        self._db = DatabaseManager.get_instance()  # 重新获取新实例
        self.assertEqual(first, self._dump())


class ImportantJudgementConsistencyTest(unittest.TestCase):
    """「重要」判定在迁移前后等价（阈值 2 -> 3）。"""

    def _make_item(self, importance) -> object:
        class _FakeItem:
            raw_payload = '{"id": 1, "score": 2, "channels": ["global"]}'
            published_at = None
            url = "https://wallstreetcn.com/livenews/1"
            scope_value = "global"
            title = "t"
            summary = "s"
            id = 1

            def __init__(self, imp):  # noqa: ANN001
                self.importance = imp

        return _FakeItem(importance)

    def test_important_mapping_equivalent(self) -> None:
        service = IntelligenceService.__new__(IntelligenceService)  # 跳过 __init__ 依赖
        # 旧量纲：score=2（重要），阈值 2 -> important=True
        old = IntelligenceService._live_news_item_to_dict(
            service, self._make_item(2), threshold=2
        )
        # 新量纲：importance=3（映射后），阈值 3 -> important=True
        new = IntelligenceService._live_news_item_to_dict(
            service, self._make_item(3), threshold=3
        )
        self.assertTrue(old["important"])
        self.assertTrue(new["important"])

    def test_normal_and_none_not_important(self) -> None:
        service = IntelligenceService.__new__(IntelligenceService)
        normal = IntelligenceService._live_news_item_to_dict(
            service, self._make_item(1), threshold=3
        )
        none_level = IntelligenceService._live_news_item_to_dict(
            service, self._make_item(0), threshold=3
        )
        self.assertFalse(normal["important"])
        self.assertFalse(none_level["important"])
        # 无重要级时 score 输出仍为 number（0），而非 None
        self.assertEqual(none_level["score"], 0)

    def test_null_column_falls_back_to_zero(self) -> None:
        service = IntelligenceService.__new__(IntelligenceService)
        item = IntelligenceService._live_news_item_to_dict(
            service, self._make_item(None), threshold=3
        )
        self.assertEqual(item["score"], 0)
        self.assertFalse(item["important"])


if __name__ == "__main__":
    unittest.main()
