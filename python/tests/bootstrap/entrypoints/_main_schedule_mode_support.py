# -*- coding: utf-8 -*-
"""Regression tests for scheduled mode stock selection behavior.
测试主流程调度mode相关功能测试
"""

import json
import logging
import os
import socket
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tests.support.stubs.litellm_stub import ensure_litellm_stub

ensure_litellm_stub()

_ENV_BEFORE_MAIN_IMPORT = dict(os.environ)
import main
from src.brokers.futu.portfolio import FutuPortfolioError
from src.config import Config

_MAIN_IMPORT_ENV_ADDITIONS = frozenset(set(os.environ) - set(_ENV_BEFORE_MAIN_IMPORT))
_MAIN_IMPORT_ENV_OVERRIDES = {
    key: value
    for key, value in _ENV_BEFORE_MAIN_IMPORT.items()
    if os.environ.get(key) != value
}


def _api_app_stub_modules():
    """sys.modules entries so ``start_api_server`` can ``from api.app import app``
    without importing the real (heavy) app tree in these isolated unit tests.

    ``start_api_server`` imports the ASGI app object in the calling thread so the
    import stays out of the uvicorn startup probe window; these control-flow tests
    stub it the same way they already stub uvicorn.
    """
    import types

    api_pkg = types.ModuleType("api")
    api_app_mod = types.ModuleType("api.app")
    api_app_mod.app = SimpleNamespace()
    api_pkg.app = api_app_mod
    return {"api": api_pkg, "api.app": api_app_mod}


class _DummyConfig(SimpleNamespace):
    def validate(self):
        return []


class _MainScheduleModeTestCaseFixture:
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env_path = Path(self.temp_dir.name) / ".env"
        self.env_path.write_text("STOCK_LIST=600519\n", encoding="utf-8")
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)
        self.env_patch = patch.dict(os.environ, {"ENV_FILE": str(self.env_path)}, clear=False)
        self.env_patch.start()
        Config.reset_instance()
        root_logger = logging.getLogger()
        self._original_root_handlers = list(root_logger.handlers)
        self._original_root_level = root_logger.level
    def tearDown(self) -> None:
        root_logger = logging.getLogger()
        current_handlers = list(root_logger.handlers)
        for handler in current_handlers:
            if handler not in self._original_root_handlers:
                root_logger.removeHandler(handler)
                try:
                    handler.close()
                except Exception:
                    pass
        root_logger.setLevel(self._original_root_level)
        os.chdir(self.original_cwd)
        Config.reset_instance()
        self.env_patch.stop()
        for key in _MAIN_IMPORT_ENV_ADDITIONS:
            os.environ.pop(key, None)
        for key, value in _MAIN_IMPORT_ENV_OVERRIDES.items():
            os.environ[key] = value
        self.temp_dir.cleanup()
    def _make_args(self, **overrides):
        defaults = {
            "debug": False,
            "stocks": None,
            "portfolio": None,
            "webui": False,
            "webui_only": False,
            "serve": False,
            "serve_only": False,
            "host": None,
            "port": None,
            "backtest": False,
            "market_review": False,
            "schedule": False,
            "no_run_immediately": False,
            "no_notify": False,
            "check_notify": False,
            "no_market_review": False,
            "dry_run": False,
            "workers": 1,
            "force_run": False,
            "single_notify": False,
            "no_context_snapshot": False,
        }
        defaults.update(overrides)
        return SimpleNamespace(**defaults)
    def _make_config(self, **overrides):
        defaults = {
            "log_dir": self.temp_dir.name,
            "webui_enabled": False,
            "webui_host": "127.0.0.1",
            "webui_port": 8000,
            "dingtalk_stream_enabled": False,
            "feishu_stream_enabled": False,
            "schedule_enabled": False,
            "schedule_time": "18:00",
            "schedule_run_immediately": True,
            "run_immediately": True,
            "agent_event_monitor_enabled": False,
            "agent_event_alert_rules_json": "",
            "agent_event_monitor_interval_minutes": 5,
            "daily_market_context_enabled": True,
        }
        defaults.update(overrides)
        return _DummyConfig(**defaults)

