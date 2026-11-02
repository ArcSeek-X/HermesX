# -*- coding: utf-8 -*-
"""数据库 schema 双场景验收测试（空库 / 存量库升级）。

对应架构迁移文档第 8 节第 3 项：`_ensure_*` 系列升级逻辑在后续拆分
``src/storage.py`` 时必须保持行为等价，因此先固定两个场景：

1. 空库：``create_all`` 建表后，关键表、遥测列、索引与 schema 基线标记齐全；
2. 存量库：模拟“老库缺列”，重新初始化后应原地补齐列与索引，且业务数据不丢失。

第二个场景通过先建现代库、再手工回退列/索引来构造老库，避免在测试里维护
一份与模型定义脱节的历史 DDL。
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import inspect

from src.config import Config
from src.storage import DatabaseManager
from src.infrastructure.persistence.base import CURRENT_SCHEMA_VERSION
from src.infrastructure.persistence.models.agent import LLMUsage, _LLM_USAGE_TELEMETRY_COLUMN_SQL
from src.infrastructure.persistence.models.intelligence import IntelligenceItem
from src.infrastructure.persistence.models.schema import DatabaseSchemaMigration
from src.infrastructure.persistence.models.watchlist import WatchlistGroup, WatchlistItem

_IMPORTANCE_INDEXES = (
    "ix_intelligence_items_importance",
    "ix_intel_item_channel_importance_time",
)


class StorageSchemaUpgradeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._db_path = Path(self._temp_dir.name) / "schema.db"
        self._previous_database_path = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = str(self._db_path)
        Config.reset_instance()
        DatabaseManager.reset_instance()

    def tearDown(self) -> None:
        DatabaseManager.reset_instance()
        Config.reset_instance()
        if self._previous_database_path is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = self._previous_database_path
        self._temp_dir.cleanup()

    @staticmethod
    def _columns(db: DatabaseManager, table: str) -> set:
        return {column["name"] for column in inspect(db._engine).get_columns(table)}

    @staticmethod
    def _indexes(db: DatabaseManager, table: str) -> set:
        return {index["name"] for index in inspect(db._engine).get_indexes(table)}

    def test_fresh_database_creates_baseline_schema(self) -> None:
        db = DatabaseManager.get_instance()
        inspector = inspect(db._engine)

        for table in (
            LLMUsage.__tablename__,
            IntelligenceItem.__tablename__,
            DatabaseSchemaMigration.__tablename__,
            WatchlistGroup.__tablename__,
            WatchlistItem.__tablename__,
        ):
            self.assertTrue(inspector.has_table(table), f"missing table: {table}")

        llm_columns = self._columns(db, LLMUsage.__tablename__)
        self.assertTrue(
            set(_LLM_USAGE_TELEMETRY_COLUMN_SQL).issubset(llm_columns),
            "fresh llm_usage table must contain every telemetry column",
        )

        intel_columns = self._columns(db, IntelligenceItem.__tablename__)
        self.assertIn("importance", intel_columns)
        intel_indexes = self._indexes(db, IntelligenceItem.__tablename__)
        for index_name in _IMPORTANCE_INDEXES:
            self.assertIn(index_name, intel_indexes)

        with db._SessionLocal() as session:
            self.assertIsNotNone(
                session.get(DatabaseSchemaMigration, CURRENT_SCHEMA_VERSION),
                "baseline schema version must be recorded once",
            )

    def test_existing_database_is_upgraded_in_place(self) -> None:
        db = DatabaseManager.get_instance()
        with db._SessionLocal() as session:
            session.add(
                LLMUsage(
                    call_type="analysis",
                    model="test-model",
                    prompt_tokens=11,
                    completion_tokens=7,
                    total_tokens=18,
                )
            )
            session.add(
                IntelligenceItem(
                    source_type="rss",
                    title="升级前写入的资讯",
                    url="https://example.com/legacy-upgrade",
                    scope_type="market",
                    scope_value="cn",
                    market="cn",
                )
            )
            session.commit()
            intel_id = session.query(IntelligenceItem.id).scalar()

        # 回退到“老库”形态：缺 importance 列、缺遥测列、缺相关索引
        with db._engine.begin() as connection:
            for index_name in _IMPORTANCE_INDEXES:
                connection.exec_driver_sql(f"DROP INDEX IF EXISTS {index_name}")
            connection.exec_driver_sql(
                f"ALTER TABLE {IntelligenceItem.__tablename__} DROP COLUMN importance"
            )
            for column in _LLM_USAGE_TELEMETRY_COLUMN_SQL:
                connection.exec_driver_sql(
                    f"ALTER TABLE {LLMUsage.__tablename__} DROP COLUMN {column}"
                )

        self.assertNotIn("importance", self._columns(db, IntelligenceItem.__tablename__))

        # 模拟进程重启：重新初始化同一路径的数据库
        DatabaseManager.reset_instance()
        upgraded = DatabaseManager.get_instance()

        self.assertIn("importance", self._columns(upgraded, IntelligenceItem.__tablename__))
        self.assertTrue(
            set(_LLM_USAGE_TELEMETRY_COLUMN_SQL).issubset(
                self._columns(upgraded, LLMUsage.__tablename__)
            ),
            "existing llm_usage table must regain every telemetry column",
        )
        upgraded_indexes = self._indexes(upgraded, IntelligenceItem.__tablename__)
        for index_name in _IMPORTANCE_INDEXES:
            self.assertIn(index_name, upgraded_indexes)

        with upgraded._SessionLocal() as session:
            usage = session.query(LLMUsage).one()
            self.assertEqual(usage.total_tokens, 18)
            intel = session.get(IntelligenceItem, intel_id)
            self.assertIsNotNone(intel, "upgrade must not drop existing rows")
            self.assertEqual(intel.title, "升级前写入的资讯")
            self.assertIsNone(intel.importance)


if __name__ == "__main__":
    unittest.main()
