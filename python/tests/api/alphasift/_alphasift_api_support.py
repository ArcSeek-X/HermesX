# -*- coding: utf-8 -*-
"""Tests for the AlphaSift screening endpoints.
测试AlphaSift接口相关功能测试
"""

from __future__ import annotations

import os
import json
import sys
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import ANY, MagicMock, patch
import threading

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

try:
    import litellm  # noqa: F401
except ModuleNotFoundError:
    sys.modules["litellm"] = MagicMock()

from api.v1.endpoints import alphasift as alphasift_endpoint
from src.config import Config, DEFAULT_ALPHASIFT_INSTALL_SPEC
from src.application.analysis import alphasift_service
from src.application.runtime.task_queue import TaskInfo, TaskStatus as QueueTaskStatus
from src.infrastructure.providers import hrs_alphasift_bridge
from src.bootstrap.alphasift import configure_alphasift_runtime

# 顶层装配 AlphaSift 运行时端口（test_live_news configure_news_source 同型）：
# service 的 IO 簇已下沉 infra 适配器，用例经 seam 消费，未装配即 fail-fast。
configure_alphasift_runtime()

DEFAULT_ALPHASIFT_TEST_SPEC = DEFAULT_ALPHASIFT_INSTALL_SPEC


def _alphasift_unavailable() -> alphasift_service.AlphaSiftServiceError:
    return alphasift_service.AlphaSiftServiceError(
        status_code=424,
        detail={"error": "alphasift_unavailable", "message": "AlphaSift is unavailable"},
    )


def _raise_alphasift_unavailable() -> None:
    raise _alphasift_unavailable()


def _make_adapter_module(
    *,
    screen=None,
    list_strategies=None,
    get_status=None,
) -> SimpleNamespace:
    return SimpleNamespace(
        screen=screen or MagicMock(return_value=[]),
        list_strategies=list_strategies or (lambda: [{"id": "dual_low", "name": "双低选股", "description": "", "category": "价值"}]),
        get_status=get_status or (lambda: {"supported_markets": ["cn"], "contract_version": "1", "version": "0.2.0", "strategy_count": 1}),
    )


def _missing_alphasift_module_diagnostics() -> Dict[str, str]:
    return {
        "reason": "missing_module",
        "stage": "import_adapter",
        "error_type": "ModuleNotFoundError",
        "module": "alphasift.dsa_adapter",
    }


class _AlphaSiftOpportunitiesApiTestCaseFixture:
    def setUp(self) -> None:
        Config.reset_instance()
        self.env_patch = patch.dict(os.environ, {"ALPHASIFT_DATA_DIR": ""}, clear=False)
        self.env_patch.start()
    def tearDown(self) -> None:
        self.env_patch.stop()
        Config.reset_instance()
    def _config(self, *, enabled: bool, install_spec: str = DEFAULT_ALPHASIFT_TEST_SPEC) -> Config:
        return Config(alphasift_enabled=enabled, alphasift_install_spec=install_spec)
    @staticmethod
    def _request(cookies=None) -> SimpleNamespace:
        return SimpleNamespace(cookies=cookies or {})
    def _screen(self, config: Config, *, mock_enrichment: bool = True, **kwargs):
        if not mock_enrichment:
            return alphasift_endpoint.alphasift_screen(
                alphasift_endpoint.AlphaSiftScreenRequest(**kwargs),
                http_request=self._request(),
                config=config,
            )
        with patch(
            "src.infrastructure.providers.hrs_alphasift_bridge._enrich_candidates_with_hrs",
            side_effect=lambda candidates: (
                candidates,
                {
                    "enabled": True,
                    "max_candidates": 3,
                    "requested_count": min(len(candidates), 3),
                    "enriched_count": 0,
                    "warnings": [],
                },
            ),
        ):
            return alphasift_endpoint.alphasift_screen(
                alphasift_endpoint.AlphaSiftScreenRequest(**kwargs),
                http_request=self._request(),
                config=config,
            )
    def _strategies(self, config: Config):
        return alphasift_endpoint.alphasift_strategies(request=self._request(), config=config)
    def _hotspots(self, config: Config, **kwargs):
        return alphasift_endpoint.alphasift_hotspots(config=config, **kwargs)
    def _hotspot_detail(self, config: Config, **kwargs):
        if os.environ.get("ALPHASIFT_DATA_DIR"):
            return alphasift_endpoint.alphasift_hotspot_detail(config=config, **kwargs)
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"ALPHASIFT_DATA_DIR": str(Path(tmpdir) / "alphasift")}, clear=False):
                return alphasift_endpoint.alphasift_hotspot_detail(config=config, **kwargs)


class _AlphaSiftRuntimePortWiringTestCaseFixture:
    """§4.3 拆分后的端口装配链路回归：bootstrap 绑定 seam、未装配 fail-fast。"""

