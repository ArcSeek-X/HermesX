# -*- coding: utf-8 -*-
"""API tests for DecisionSignal P1.
测试决策信号接口相关功能测试
"""

from __future__ import annotations

import os
import sys
import time
import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

try:
    import litellm  # noqa: F401
except ModuleNotFoundError:
    sys.modules["litellm"] = MagicMock()

import src.auth as auth
from api.app import create_app
from src.application.analysis.analyzer import AnalysisResult
from src.config import Config
from src.application.decision.decision_signal_extractor import extract_and_persist_from_analysis_result
from src.application.decision.decision_signal_service import DecisionSignalService
from src.storage import DatabaseManager
from src.infrastructure.persistence.base import utc_naive_now
from src.infrastructure.persistence.models.analysis import AnalysisHistory
from src.infrastructure.persistence.models.decision import DecisionSignalRecord
from src.infrastructure.persistence.models.portfolio import PortfolioAccount, PortfolioPosition
from src.bootstrap.decision import configure_decision_repositories
from src.bootstrap.portfolio import configure_portfolio_repository
from src.bootstrap.quote import configure_stock_repository
from tests.support.paths import get_repo_root

configure_portfolio_repository()
configure_decision_repositories()
configure_stock_repository()


@contextmanager
def _temporary_tz(tz_name: str):
    old_tz = os.environ.get("TZ")
    os.environ["TZ"] = tz_name
    if hasattr(time, "tzset"):
        time.tzset()
    try:
        yield
    finally:
        if old_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = old_tz
        if hasattr(time, "tzset"):
            time.tzset()


def _reset_auth_globals() -> None:
    auth._auth_enabled = None
    auth._session_secret = None
    auth._password_hash_salt = None
    auth._password_hash_stored = None
    auth._rate_limit = {}


@pytest.fixture()
def client_and_db(tmp_path):
    old_env_file = os.environ.get("ENV_FILE")
    old_database_path = os.environ.get("DATABASE_PATH")
    env_path = tmp_path / ".env"
    db_path = tmp_path / "decision_signal_api.db"
    static_dir = tmp_path / "empty-static"
    static_dir.mkdir()
    env_path.write_text(
        "\n".join(
            [
                "STOCK_LIST=600519",
                "GEMINI_API_KEY=test",
                "ADMIN_AUTH_ENABLED=false",
                f"DATABASE_PATH={db_path}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    os.environ["ENV_FILE"] = str(env_path)
    os.environ["DATABASE_PATH"] = str(db_path)
    _reset_auth_globals()
    Config.reset_instance()
    DatabaseManager.reset_instance()
    app = create_app(static_dir=Path(static_dir))
    client = TestClient(app)
    db = DatabaseManager.get_instance()
    try:
        yield client, db
    finally:
        DatabaseManager.reset_instance()
        Config.reset_instance()
        _reset_auth_globals()
        if old_env_file is None:
            os.environ.pop("ENV_FILE", None)
        else:
            os.environ["ENV_FILE"] = old_env_file
        if old_database_path is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = old_database_path


def _payload(**overrides):
    payload = {
        "stock_code": "SH600519",
        "stock_name": "贵州茅台",
        "market": "cn",
        "source_type": "analysis",
        "source_agent": "api-test",
        "source_report_id": 3001,
        "trace_id": "trace-3001",
        "market_phase": "intraday",
        "trigger_source": "api",
        "action": "buy",
        "confidence": 0.75,
        "score": 80,
        "horizon": "3d",
        "entry_low": 1680,
        "stop_loss": 1600,
        "reason": "突破平台",
        "evidence": {"source": "unit-test"},
        "metadata": {"task_id": "task-3001", "alert_trigger_id": "alert-1"},
    }
    payload.update(overrides)
    return payload


def _decision_signal_count(db: DatabaseManager) -> int:
    with db.session_scope() as session:
        return session.query(DecisionSignalRecord).count()


def _save_reassess_history(
    db: DatabaseManager,
    *,
    code: str = "600519",
    report_type: str = "full",
    operation_advice: str | None = "买入",
    raw_result: dict | str | None = None,
    context_snapshot: dict | str | None = None,
    sentiment_score: int | None = 72,
    stop_loss: float | None = 1600,
    take_profit: float | None = 1850,
) -> int:
    raw_payload = raw_result
    if isinstance(raw_payload, dict):
        raw_payload = json.dumps(raw_payload, ensure_ascii=False)
    context_payload = context_snapshot
    if isinstance(context_payload, dict):
        context_payload = json.dumps(context_payload, ensure_ascii=False)
    with db.session_scope() as session:
        row = AnalysisHistory(
            query_id="query-reassess-test",
            code=code,
            name="贵州茅台",
            report_type=report_type,
            sentiment_score=sentiment_score,
            operation_advice=operation_advice,
            trend_prediction="震荡上行",
            analysis_summary="趋势改善但需要风控。",
            raw_result=raw_payload,
            context_snapshot=context_payload,
            ideal_buy=1680,
            secondary_buy=1700,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        session.add(row)
        session.flush()
        return int(row.id)


def _set_reassess_history_created_at(
    db: DatabaseManager,
    record_id: int,
    created_at: datetime | None,
) -> None:
    with db.session_scope() as session:
        row = session.query(AnalysisHistory).filter(AnalysisHistory.id == record_id).one()
        row.created_at = created_at


def _valid_reassess_raw(**overrides) -> dict:
    raw = {
        "action": "buy",
        "operation_advice": "买入",
        "sentiment_score": 72,
        "confidence_level": "中",
        "analysis_summary": "趋势改善但需要确认。",
        "risk_warning": "跌破关键支撑需退出。",
        "dashboard": {
            "battle_plan": {
                "sniper_points": {
                    "ideal_buy": 1680,
                    "secondary_buy": 1700,
                    "stop_loss": 1600,
                    "take_profit": 1850,
                },
                "action_checklist": ["放量突破", "资金流转正"],
            },
            "phase_decision": {
                "watch_conditions": ["量能维持"],
            },
        },
    }
    raw.update(overrides)
    return raw


def _valid_reassess_context() -> dict:
    return {
        "market_phase_summary": {"phase": "intraday"},
        "analysis_context_pack_overview": {
            "data_quality": {"level": "usable"},
        },
    }


def _persist_auto_balanced_signal(
    db: DatabaseManager,
    *,
    source_report_id: int,
    raw_result: dict | None = None,
    context_snapshot: dict | None = None,
) -> dict:
    raw = raw_result or _valid_reassess_raw(invalidation="跌破关键支撑")
    result = AnalysisResult(
        code="600519",
        name="贵州茅台",
        sentiment_score=raw.get("sentiment_score", 72),
        trend_prediction="震荡上行",
        operation_advice=raw.get("operation_advice", "买入"),
        decision_type="buy",
        confidence_level=raw.get("confidence_level", "中"),
        analysis_summary=raw.get("analysis_summary", "趋势改善但需要确认。"),
        risk_warning=raw.get("risk_warning", "跌破关键支撑需退出。"),
        report_language="zh",
        action=raw.get("action", "buy"),
    )
    result.dashboard = raw.get("dashboard")
    persisted = extract_and_persist_from_analysis_result(
        result,
        context_snapshot=context_snapshot or _valid_reassess_context(),
        source_report_id=source_report_id,
        trace_id=f"trace-auto-{source_report_id}",
        query_source="api",
        report_type="full",
        profile_source="auto_default",
        service=DecisionSignalService(db_manager=db),
    )
    assert persisted is not None
    return persisted["item"]


