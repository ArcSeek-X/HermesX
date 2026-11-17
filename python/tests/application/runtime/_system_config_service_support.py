# -*- coding: utf-8 -*-
"""Unit tests for system configuration service.
测试system配置服务相关功能测试
"""

import os
import json
import logging
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, patch

import requests

from tests.support.stubs.litellm_stub import ensure_litellm_stub

ensure_litellm_stub()

from src.config import ANSPIRE_LLM_MODEL_DEFAULT, DEFAULT_ALPHASIFT_INSTALL_SPEC, Config
from src.config.env_file import ConfigManager
from src.domain.generation.backend_identity import (
    GENERATION_ONLY_BACKEND_IDS,
)
from src.application.runtime import system_config_service
from src.application.runtime.system_config_service import (
    ConfigConflictError,
    ConfigImportError,
    ConfigValidationError,
    SystemConfigService,
    _build_llm_models_url,
)
from src.bootstrap.system_config import configure_system_config_runtime
from src.bootstrap.generation import configure_generation_runtime

# 顶层装配 SystemConfig 运行时端口（test_alphasift_api configure 同型）：service 的
# 探测/通知试发/单例重置外调簇已下沉 infra 适配器，用例经 seam 消费，未装配即 fail-fast。
configure_system_config_runtime()
# 生成链路端口（R2-A3）：预设解析 / 参数归一外调簇同样下沉 infra 适配器。
configure_generation_runtime()


class _SystemConfigServiceTestCaseFixture:
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env_path = Path(self.temp_dir.name) / ".env"
        self.env_path.write_text(
            "\n".join(
                [
                    "STOCK_LIST=600519,000001",
                    "GEMINI_API_KEY=secret-key-value",
                    "SCHEDULE_TIME=18:00",
                    "LOG_LEVEL=INFO",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        os.environ["ENV_FILE"] = str(self.env_path)
        Config.reset_instance()

        self.manager = ConfigManager(env_path=self.env_path)
        self.service = SystemConfigService(manager=self.manager)
    def tearDown(self) -> None:
        Config.reset_instance()
        os.environ.pop("ENV_FILE", None)
        self.temp_dir.cleanup()
    def _rewrite_env(self, *lines: str) -> None:
        self.env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        Config.reset_instance()
        self.manager = ConfigManager(env_path=self.env_path)
        self.service = SystemConfigService(manager=self.manager)
    @staticmethod
    def _mock_completion_response(content: str = "OK", tool_calls=None):
        message = SimpleNamespace(content=content, tool_calls=tool_calls or [])
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])
    def _assert_agent_backend_status_matches_runtime(
        self,
        *,
        saved_backend: str,
        runtime_backend: str,
    ) -> None:
        from src.application.agent.agent_backend import resolve_agent_backend_id
        from src.application.runtime.agent_backend_status import AgentBackendStatusService

        self._rewrite_env(
            "GEMINI_API_KEY=secret-key-value",
            f"AGENT_BACKEND={saved_backend}",
            "AGENT_ARCH=single",
        )
        codex_status = {
            "backend": "codex_app_server",
            "available": True,
            "experimental": True,
            "version": "codex-cli test",
            "error_code": None,
            "message": None,
        }
        with (
            patch.dict(os.environ, {"AGENT_BACKEND": runtime_backend}),
            patch.object(
                AgentBackendStatusService,
                "_codex_cheap_status",
                return_value=codex_status,
            ),
        ):
            Config.reset_instance()
            runtime_config = Config.get_instance()
            with patch.dict(os.environ, {"AGENT_BACKEND": saved_backend}):
                settings_status = self.service.get_agent_backend_status()
                chat_status = AgentBackendStatusService(config=runtime_config).get_status()
                selected_backend = resolve_agent_backend_id(runtime_config)
                preview_baseline = self.service.preview_agent_backend_status(items=[])
                preview_draft = self.service.preview_agent_backend_status(
                    items=[{"key": "AGENT_BACKEND", "value": saved_backend}],
                )

        self.assertEqual(settings_status["backend"], runtime_backend)
        self.assertEqual(chat_status["backend"], runtime_backend)
        self.assertEqual(selected_backend, runtime_backend)
        self.assertEqual(preview_baseline["backend"], runtime_backend)
        self.assertEqual(preview_draft["backend"], saved_backend)
        self.assertIs(Config.get_instance(), runtime_config)
    @staticmethod
    def _mock_http_response(status_code: int, json_body: Optional[Dict[str, Any]] = None):
        response = Mock()
        response.status_code = status_code
        response.text = "ok" if status_code == 200 else "error"
        response.json.return_value = json_body or {"errcode": 0}
        return response
    def _notification_test_env(self):
        return patch.dict(os.environ, {"ENV_FILE": str(self.env_path)}, clear=True)


class _SystemConfigRuntimePortWiringTestCaseFixture:
    """§4.3 拆分 F3 后的端口装配链路回归：bootstrap 绑定 seam、未装配 fail-fast。"""

