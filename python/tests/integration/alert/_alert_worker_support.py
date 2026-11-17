# -*- coding: utf-8 -*-
"""Alert worker tests for Issue #1202 P2.
测试预警工作线程相关功能测试
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd

from src.config import Config
from src.application.notification.notification import ChannelAttemptResult, NotificationDispatchResult
from src.domain.alert.alert_indicators import (
    calculate_rsi,
    compute_requested_days,
    compute_required_bars,
    evaluate_indicator_alert,
    normalize_indicator_parameters,
)
from src.bootstrap.alert import build_alert_service
from src.application.alert.worker import AlertWorker
from src.application.decision.decision_signal_service import DecisionSignalService
from src.storage import DatabaseManager
from src.bootstrap.decision import configure_decision_repositories
from src.bootstrap.portfolio import configure_portfolio_repository
from src.bootstrap.quote import configure_stock_repository

configure_portfolio_repository()
configure_decision_repositories()
configure_stock_repository()


class _AlertWorkerTestCaseFixture:
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.env_path = self.data_dir / ".env"
        self.db_path = self.data_dir / "alert_worker_test.db"
        self.env_path.write_text(
            "\n".join([
                "STOCK_LIST=600519",
                "GEMINI_API_KEY=test",
                "ADMIN_AUTH_ENABLED=false",
                f"DATABASE_PATH={self.db_path}",
            ])
            + "\n",
            encoding="utf-8",
        )
        os.environ["ENV_FILE"] = str(self.env_path)
        os.environ["DATABASE_PATH"] = str(self.db_path)
        Config.reset_instance()
        DatabaseManager.reset_instance()
        self.service = build_alert_service()
    def tearDown(self) -> None:
        DatabaseManager.reset_instance()
        Config.reset_instance()
        os.environ.pop("ENV_FILE", None)
        os.environ.pop("DATABASE_PATH", None)
        self.temp_dir.cleanup()
    def _config(self, raw_rules: str = "") -> SimpleNamespace:
        return SimpleNamespace(
            agent_event_monitor_enabled=True,
            agent_event_alert_rules_json=raw_rules,
            trading_day_check_enabled=False,
        )
    def _create_rule(self, **overrides) -> dict:
        payload = {
            "name": "Moutai breakout",
            "target_scope": "single_symbol",
            "target": "600519",
            "alert_type": "price_cross",
            "parameters": {"direction": "above", "price": 1800},
            "severity": "warning",
            "enabled": True,
        }
        payload.update(overrides)
        return self.service.create_rule(payload)
    def _triggers(self, **filters) -> list[dict]:
        return self.service.list_triggers(page_size=100, **filters)["items"]
    def _notifications(self, **filters) -> list[dict]:
        return self.service.list_notifications(page_size=100, **filters)["items"]
    def _dispatch_result(
        self,
        success: bool = True,
        *,
        dispatched: bool = True,
        status: str | None = None,
        channel: str = "custom",
        error_code: str | None = None,
    ) -> NotificationDispatchResult:
        if status is None:
            status = "sent" if success else "all_failed"
        channel_results = []
        if dispatched:
            channel_results.append(
                ChannelAttemptResult(
                    channel=channel,
                    success=success,
                    error_code=error_code if error_code is not None else (None if success else "send_failed"),
                    retryable=not success,
                )
            )
        return NotificationDispatchResult(
            dispatched=dispatched,
            success=success,
            status=status,
            channel_results=channel_results,
        )
    def _notifier(self, *results) -> MagicMock:
        notifier = MagicMock()
        if not results:
            results = (self._dispatch_result(True),)
        if len(results) == 1:
            notifier.send_with_results.return_value = results[0]
        else:
            notifier.send_with_results.side_effect = list(results)
        return notifier

