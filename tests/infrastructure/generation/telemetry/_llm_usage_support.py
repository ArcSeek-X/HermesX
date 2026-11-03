# -*- coding: utf-8 -*-
"""Unit tests for LLM usage tracking (storage + analyzer helper).
测试llm用量相关功能测试
"""

import hashlib
import hmac as py_hmac
import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError

from tests.support.stubs.litellm_stub import ensure_litellm_stub, remove_litellm_stub

remove_litellm_stub()
try:
    from litellm.types.utils import Usage
except ModuleNotFoundError:
    ensure_litellm_stub()
    from litellm.types.utils import Usage

from src.infrastructure.generation.usage import (
    attach_legacy_message_stability_audit,
    attach_message_hmacs,
    build_message_hmacs,
    extract_usage_payload,
    has_provider_usage_payload,
    normalize_litellm_usage,
    should_persist_usage_telemetry,
    _reset_usage_hmac_secret_cache_for_tests,
)
from src.infrastructure.generation.provider_cache import filter_prompt_cache_telemetry
from src.storage import DatabaseManager, persist_llm_usage
from src.infrastructure.persistence.models.agent import LLMUsage, _LLM_USAGE_TELEMETRY_COLUMN_SQL


def _fresh_db() -> DatabaseManager:
    """Return a DatabaseManager backed by a fresh in-memory SQLite database."""
    DatabaseManager.reset_instance()
    db = DatabaseManager(db_url="sqlite:///:memory:")
    return db


class _TestRecordLLMUsageFixture:
    def setUp(self):
        self.db = _fresh_db()
    def tearDown(self):
        DatabaseManager.reset_instance()


class _TestLLMUsageHMACFixture:
    def tearDown(self):
        _reset_usage_hmac_secret_cache_for_tests()


class _TestLegacyMessageStabilityAuditFixture:
    def setUp(self):
        self._hmac_secret_patch = patch.dict(
            os.environ,
            {"LLM_USAGE_HMAC_SECRET": "audit-secret"},
            clear=False,
        )
        self._hmac_secret_patch.start()
        _reset_usage_hmac_secret_cache_for_tests()
    def tearDown(self):
        self._hmac_secret_patch.stop()
        _reset_usage_hmac_secret_cache_for_tests()
        DatabaseManager.reset_instance()
    def _messages(self):
        return [
            {"role": "system", "content": "system policy for zh stock analysis"},
            {
                "role": "user",
                "content": (
                    "# 决策仪表盘分析请求\n\n"
                    "## 📊 股票基础信息\n"
                    "| 股票代码 | **600519** |\n"
                    "| 股票名称 | **贵州茅台** |\n"
                    "| 分析日期 | 2026-06-19 |\n\n"
                    "## 📈 技术面数据\n"
                    "收盘价 1500 元\n\n"
                    "## 📰 舆情情报\n"
                    "IMPORTANT_NEWS_TEXT\n"
                ),
            },
        ]
    def _audit_context(self):
        return {
            "language": "zh",
            "market_group": "cn",
            "analysis_mode": "stock_analysis",
            "legacy_prompt_mode": "skill_aware",
            "skill_config": {
                "skill_instructions": "RSI breakout skill raw instructions",
                "default_skill_policy": "Default skill policy raw text",
                "use_legacy_default_prompt": False,
            },
            "provider": "gemini",
            "transport": "litellm",
            "dynamic_markers": [
                {"marker_name": "stock_code", "message_role": "user", "text": "600519"},
                {"marker_name": "stock_name", "message_role": "user", "text": "贵州茅台"},
                {"marker_name": "analysis_date", "message_role": "user", "text": "2026-06-19"},
                {"marker_name": "quote", "message_role": "user", "text": "## 📈 技术面数据"},
                {"marker_name": "news_context", "message_role": "user", "text": "IMPORTANT_NEWS_TEXT"},
                {"marker_name": "raw-header", "message_role": "user", "text": "Authorization: Bearer token"},
            ],
        }


class _TestGetLLMUsageSummaryFixture:
    def setUp(self):
        self.db = _fresh_db()
        now = datetime.now()
        yesterday = now - timedelta(days=1)

        # 3 analysis calls today
        for _ in range(3):
            row = LLMUsage(
                call_type="analysis",
                model="gemini/gemini-2.5-flash",
                prompt_tokens=100,
                completion_tokens=200,
                total_tokens=300,
                called_at=now,
            )
            with self.db.session_scope() as session:
                session.add(row)

        # 2 agent calls today
        for _ in range(2):
            row = LLMUsage(
                call_type="agent",
                model="openai/gpt-4o",
                prompt_tokens=50,
                completion_tokens=100,
                total_tokens=150,
                called_at=now,
            )
            with self.db.session_scope() as session:
                session.add(row)

        # 1 old call that should be excluded
        old_row = LLMUsage(
            call_type="analysis",
            model="gemini/gemini-2.5-flash",
            prompt_tokens=999,
            completion_tokens=999,
            total_tokens=999,
            called_at=yesterday,
        )
        with self.db.session_scope() as session:
            session.add(old_row)
    def tearDown(self):
        DatabaseManager.reset_instance()
    def _today_range(self):
        now = datetime.now()
        return now.replace(hour=0, minute=0, second=0, microsecond=0), now


class _TestPersistUsageHelperFixture:
    """Test that _persist_usage swallows exceptions and writes correctly."""
    def setUp(self):
        self.db = _fresh_db()
    def tearDown(self):
        DatabaseManager.reset_instance()


class _TestLLMUsageMigrationFixture:
    def tearDown(self):
        DatabaseManager.reset_instance()
    def _create_legacy_usage_db(self, db_path: Path, telemetry_columns=()):
        extra_columns = "".join(
            f",\n                        {column} {_LLM_USAGE_TELEMETRY_COLUMN_SQL[column]}"
            for column in telemetry_columns
        )
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                f"""
                CREATE TABLE llm_usage (
                    id INTEGER PRIMARY KEY,
                    call_type VARCHAR(64) NOT NULL,
                    model VARCHAR(128) NOT NULL,
                    stock_code VARCHAR(32),
                    prompt_tokens INTEGER NOT NULL DEFAULT 0,
                    completion_tokens INTEGER NOT NULL DEFAULT 0,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    called_at DATETIME{extra_columns}
                )
                """
            )
            conn.commit()
    def _usage_columns(self, db_path: Path):
        with sqlite3.connect(db_path) as conn:
            return {
                row[1]
                for row in conn.execute("PRAGMA table_info(llm_usage)").fetchall()
            }
    def _assert_all_telemetry_columns(self, db_path: Path):
        columns = self._usage_columns(db_path)
        missing = set(_LLM_USAGE_TELEMETRY_COLUMN_SQL) - columns
        self.assertFalse(missing, f"Missing telemetry columns: {sorted(missing)}")
    @staticmethod
    def _is_add_column_statement(statement: str, column: str) -> bool:
        return (
            "ALTER TABLE llm_usage ADD COLUMN" in statement
            and f"ADD COLUMN {column} " in statement
        )

