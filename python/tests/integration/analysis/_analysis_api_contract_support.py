# -*- coding: utf-8 -*-
"""Regression tests for analysis API/report-type contracts.
测试分析接口契约相关功能测试
"""

import asyncio
from concurrent.futures import Future
from datetime import datetime
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import ANY, MagicMock, patch

with tempfile.TemporaryDirectory() as _import_dir:
    with patch.dict(os.environ):
        _MODULE_ENV_FILE = Path(_import_dir) / ".env"
        _MODULE_ENV_FILE.write_text("STOCK_LIST=600519,000001\n", encoding="utf-8")
        os.environ["ENV_FILE"] = str(_MODULE_ENV_FILE)

        from tests.support.stubs.litellm_stub import ensure_litellm_stub

        ensure_litellm_stub()

        try:
            from api.app import create_app
            from api.v1.endpoints import analysis as analysis_endpoint_module
            from api.v1.endpoints.analysis import (
                trigger_analysis,
                trigger_market_review,
                _handle_sync_analysis,
                _build_analysis_report,
                _load_sync_fundamental_sources,
                get_analysis_status,
                get_task_list,
            )
        except Exception:  # pragma: no cover - optional dependency environments
            create_app = None
            analysis_endpoint_module = None
            trigger_analysis = None
            trigger_market_review = None
            _handle_sync_analysis = None
            _build_analysis_report = None
            _load_sync_fundamental_sources = None
            get_analysis_status = None
            get_task_list = None

        from src.domain.shared.enums import ReportType
        from src.application.history import HistoryQueryService
        from src.config import Config
        from src.infrastructure.indexing.stock_code_normalizer import (
            DataProviderStockCodeNormalizer,
        )
        from src.application.analysis.analysis_service import AnalysisService
        from src.application.analysis.image_stock_extractor import _call_litellm_vision
        from src.application.runtime.task_queue import AnalysisTaskQueue, TaskInfo as QueueTaskInfo, TaskStatus

Config.reset_instance()


def _analysis_context_pack_overview() -> dict:
    return {
        "pack_version": "1.0",
        "created_at": "2026-04-10T08:30:00+00:00",
        "subject": {
            "code": "600519",
            "stock_name": "贵州茅台",
            "market": "cn",
        },
        "blocks": [
            {
                "key": "quote",
                "label": "行情",
                "status": "available",
                "source": "mock",
                "warnings": [],
                "missing_reasons": [],
            },
            {
                "key": "news",
                "label": "新闻",
                "status": "missing",
                "source": None,
                "warnings": [],
                "missing_reasons": ["news_context_missing"],
            },
        ],
        "counts": {
            "available": 1,
            "missing": 1,
            "not_supported": 0,
            "fallback": 0,
            "stale": 0,
            "estimated": 0,
            "partial": 0,
            "fetch_failed": 0,
        },
        "data_quality": {
            "overall_score": 88,
            "level": "good",
            "block_scores": {
                "quote": 100,
                "daily_bars": 100,
                "technical": 100,
                "news": 35,
                "fundamentals": 100,
                "chip": 100,
            },
            "limitations": [],
        },
        "warnings": ["news_context_missing"],
        "metadata": {
            "trigger_source": "api",
            "news_result_count": 0,
        },
    }


def _market_structure_context() -> dict:
    return {
        "schema_version": "market-structure-v1",
        "status": "partial",
        "market": "cn",
        "market_theme_context": {
            "schema_version": "market-theme-v1",
            "status": "partial",
            "market": "cn",
            "active_themes": [{"name": "机器人概念"}],
        },
        "stock_market_position": {
            "schema_version": "stock-market-position-v1",
            "status": "partial",
            "stock_code": "300024",
            "market": "cn",
            "primary_theme": {"name": "机器人概念"},
        },
    }


def _market_phase_summary() -> dict:
    return {
        "market": "cn",
        "phase": "intraday",
        "market_local_time": "2026-03-27T10:00:00+08:00",
        "session_date": "2026-03-27",
        "effective_daily_bar_date": "2026-03-26",
        "is_trading_day": True,
        "is_market_open_now": True,
        "is_partial_bar": True,
        "minutes_to_open": None,
        "minutes_to_close": 300,
        "trigger_source": "api",
        "analysis_intent": "auto",
        "warnings": ["partial_bar"],
    }


class _AnalysisApiContractTestCaseFixture:
    def _history_service(self, *, record=None, fundamental=None):
        """构造注入了假仓储的分析历史用例。

        分析端点已改为依赖注入 ``HistoryQueryService``，不再在函数体内取
        ``DatabaseManager``；本 helper 返回 ``(service, repository)``，便于测试继续
        断言底层收到的查询参数。
        """
        repository = MagicMock()
        repository.get_latest_analysis_by_query_id.return_value = record
        repository.get_latest_fundamental_snapshot.return_value = fundamental
        service = HistoryQueryService(
            repository=repository,
            code_normalizer=DataProviderStockCodeNormalizer(),
        )
        return service, repository


class _BatchTaskQueueContractTestCaseFixture:
    def setUp(self) -> None:
        self._original_instance = AnalysisTaskQueue._instance
        AnalysisTaskQueue._instance = None
    def tearDown(self) -> None:
        queue = AnalysisTaskQueue._instance
        if queue is not None and queue is not self._original_instance:
            executor = getattr(queue, "_executor", None)
            if executor is not None and hasattr(executor, "shutdown"):
                executor.shutdown(wait=False, cancel_futures=True)
        AnalysisTaskQueue._instance = self._original_instance

