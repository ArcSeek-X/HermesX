"""Tests for system config setup."""

from tests.application.runtime._system_config_service_support import (
    Path,
    _SystemConfigServiceTestCaseFixture,
    os,
    patch,
    unittest,
)


class SystemConfigServiceTestCase(_SystemConfigServiceTestCaseFixture, unittest.TestCase):
    def test_get_setup_status_reports_required_gaps_for_empty_config(self) -> None:
        self._rewrite_env("")

        with patch.dict(os.environ, {}, clear=True):
            status = self.service.get_setup_status()

        self.assertFalse(status["is_complete"])
        self.assertFalse(status["ready_for_smoke"])
        self.assertEqual(status["next_step_key"], "llm_primary")
        self.assertIn("llm_primary", status["required_missing_keys"])
        self.assertIn("stock_list", status["required_missing_keys"])

    def test_get_setup_status_marks_minimal_config_complete(self) -> None:
        self._rewrite_env(
            "LITELLM_MODEL=gemini/gemini-3-flash-preview",
            "GEMINI_API_KEY=secret-key-value",
            "STOCK_LIST=600519",
        )

        with patch.dict(os.environ, {}, clear=True):
            status = self.service.get_setup_status()

        checks = {check["key"]: check for check in status["checks"]}
        self.assertTrue(status["is_complete"])
        self.assertTrue(status["ready_for_smoke"])
        self.assertEqual(checks["llm_primary"]["status"], "configured")
        self.assertEqual(checks["llm_agent"]["status"], "inherited")
        self.assertEqual(checks["stock_list"]["status"], "configured")
        self.assertEqual(checks["notification"]["status"], "optional")

    def test_get_setup_status_treats_codex_cli_as_primary_runtime_without_api_keys(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=codex_cli",
            "GENERATION_FALLBACK_BACKEND=",
            "STOCK_LIST=600519",
        )

        with patch.dict(os.environ, {}, clear=True), \
             patch("src.application.runtime.system_config_service.shutil.which", return_value="/usr/bin/codex"):
            status = self.service.get_setup_status()

        checks = {check["key"]: check for check in status["checks"]}
        self.assertFalse(status["is_complete"])
        self.assertTrue(status["ready_for_smoke"])
        self.assertEqual(checks["llm_primary"]["status"], "configured")
        self.assertEqual(checks["llm_agent"]["status"], "needs_action")
        self.assertIn("Codex CLI", checks["llm_primary"]["message"])
        self.assertNotIn("llm_primary", status["required_missing_keys"])
        self.assertIn("llm_agent", status["required_missing_keys"])

    def test_get_setup_status_allows_local_cli_primary_smoke_without_agent_model(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=claude_code_cli",
            "GENERATION_FALLBACK_BACKEND=",
            "STOCK_LIST=AAPL",
        )

        with patch.dict(os.environ, {}, clear=True), \
             patch("src.application.runtime.system_config_service.shutil.which", return_value="/usr/bin/claude"):
            status = self.service.get_setup_status()

        checks = {check["key"]: check for check in status["checks"]}
        self.assertFalse(status["is_complete"])
        self.assertTrue(status["ready_for_smoke"])
        self.assertEqual(checks["llm_primary"]["status"], "configured")
        self.assertEqual(checks["stock_list"]["status"], "configured")
        self.assertEqual(checks["llm_agent"]["status"], "needs_action")
        self.assertIn("local CLI 主生成方式不会被自动继承", checks["llm_agent"]["message"])
        self.assertEqual(status["required_missing_keys"], ["llm_agent"])

    def test_get_setup_status_codex_cli_missing_reports_backend_path(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=codex_cli",
            "GENERATION_FALLBACK_BACKEND=",
            "STOCK_LIST=600519",
        )

        with patch.dict(os.environ, {}, clear=True), \
             patch("src.application.runtime.system_config_service.shutil.which", return_value=None):
            status = self.service.get_setup_status()

        checks = {check["key"]: check for check in status["checks"]}
        self.assertEqual(checks["llm_primary"]["status"], "needs_action")
        self.assertIn("后端进程当前 PATH", checks["llm_primary"]["message"])
        self.assertIn("Codex CLI 交互窗口", checks["llm_primary"]["next_step"])
        self.assertNotIn("请先安装并登录", checks["llm_primary"]["next_step"])

    def test_get_setup_status_codex_primary_agent_model_explains_litellm_split(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=codex_cli",
            "GENERATION_FALLBACK_BACKEND=",
            "AGENT_LITELLM_MODEL=openai/gpt-5.5",
            "OPENAI_API_KEY=secret-key-value",
            "STOCK_LIST=600519",
        )

        with patch.dict(os.environ, {}, clear=True), \
             patch("src.application.runtime.system_config_service.shutil.which", return_value="/usr/bin/codex"):
            status = self.service.get_setup_status()

        checks = {check["key"]: check for check in status["checks"]}
        self.assertEqual(checks["llm_agent"]["status"], "configured")
        self.assertIn("普通分析使用 Codex CLI", checks["llm_agent"]["message"])
        self.assertIn("Agent 工具调用仍使用 LiteLLM 主模型", checks["llm_agent"]["message"])

    def test_get_setup_status_codex_primary_agent_inherited_model_explains_litellm_split(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=codex_cli",
            "GENERATION_FALLBACK_BACKEND=",
            "LITELLM_MODEL=openai/gpt-5.5",
            "OPENAI_API_KEY=secret-key-value",
            "STOCK_LIST=600519",
        )

        with patch.dict(os.environ, {}, clear=True), \
             patch("src.application.runtime.system_config_service.shutil.which", return_value="/usr/bin/codex"):
            status = self.service.get_setup_status()

        checks = {check["key"]: check for check in status["checks"]}
        self.assertEqual(checks["llm_agent"]["status"], "configured")
        self.assertIn(
            "普通分析使用 Codex CLI；Agent 工具调用仍使用 LiteLLM 主模型: openai/gpt-5.5",
            checks["llm_agent"]["message"],
        )

    def test_get_setup_status_codex_primary_hermes_only_agent_inheritance_needs_action(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=codex_cli",
            "GENERATION_FALLBACK_BACKEND=",
            "LLM_CHANNELS=hermes",
            "LLM_HERMES_PROTOCOL=openai",
            "LLM_HERMES_BASE_URL=http://127.0.0.1:8765/v1",
            "LLM_HERMES_API_KEY=test-key",
            "LLM_HERMES_MODELS=hermes-agent",
            "LITELLM_MODEL=openai/hermes-agent",
            "STOCK_LIST=600519",
        )

        with patch.dict(os.environ, {}, clear=True), \
             patch("src.application.runtime.system_config_service.shutil.which", return_value="/usr/bin/codex"):
            status = self.service.get_setup_status()

        checks = {check["key"]: check for check in status["checks"]}
        self.assertEqual(checks["llm_primary"]["status"], "configured")
        self.assertEqual(checks["llm_agent"]["status"], "needs_action")
        self.assertIn("Hermes", checks["llm_agent"]["message"])
        self.assertIn("llm_agent", status["required_missing_keys"])
        self.assertNotIn(
            "Agent 工具调用仍使用 LiteLLM 主模型",
            checks["llm_agent"]["message"],
        )

    def test_get_setup_status_rejects_agent_codex_cli_tool_backend(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=codex_cli",
            "AGENT_GENERATION_BACKEND=codex_cli",
            "STOCK_LIST=600519",
        )

        with patch.dict(os.environ, {}, clear=True), \
             patch("src.application.runtime.system_config_service.shutil.which", return_value="/usr/bin/codex"):
            status = self.service.get_setup_status()

        checks = {check["key"]: check for check in status["checks"]}
        self.assertEqual(checks["llm_agent"]["status"], "needs_action")
        self.assertIn("暂不支持 codex_cli", checks["llm_agent"]["message"])

    def test_get_setup_status_rejects_agent_claude_and_opencode_tool_backends(self) -> None:
        for backend in ("claude_code_cli", "opencode_cli"):
            with self.subTest(backend=backend):
                self._rewrite_env(
                    "GENERATION_BACKEND=litellm",
                    f"AGENT_GENERATION_BACKEND={backend}",
                    "STOCK_LIST=600519",
                )

                with patch.dict(os.environ, {}, clear=True):
                    status = self.service.get_setup_status()

                checks = {check["key"]: check for check in status["checks"]}
                self.assertEqual(checks["llm_agent"]["status"], "needs_action")
                self.assertIn(f"暂不支持 {backend}", checks["llm_agent"]["message"])

    def test_get_setup_status_accepts_opencode_without_model_override(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=opencode_cli",
            "GENERATION_FALLBACK_BACKEND=",
            "STOCK_LIST=600519",
        )

        with patch.dict(os.environ, {}, clear=True), \
             patch("src.application.runtime.system_config_service.shutil.which", return_value="/usr/bin/opencode"):
            status = self.service.get_setup_status()

        checks = {check["key"]: check for check in status["checks"]}
        self.assertEqual(checks["llm_primary"]["status"], "configured")
        self.assertIn("OpenCode CLI", checks["llm_primary"]["message"])

    def test_get_setup_status_agent_litellm_without_model_reports_missing_model(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=codex_cli",
            "AGENT_GENERATION_BACKEND=litellm",
            "STOCK_LIST=600519",
        )

        with patch.dict(os.environ, {}, clear=True), \
             patch("src.application.runtime.system_config_service.shutil.which", return_value="/usr/bin/codex"):
            status = self.service.get_setup_status()

        checks = {check["key"]: check for check in status["checks"]}
        self.assertEqual(checks["llm_agent"]["status"], "needs_action")
        self.assertIn("未检测到可用 LiteLLM 模型配置", checks["llm_agent"]["message"])
        self.assertNotIn("需要 LiteLLM backend", checks["llm_agent"]["message"])

    def test_get_setup_status_accepts_anspire_one_key_llm(self) -> None:
        self._rewrite_env(
            "ANSPIRE_API_KEYS=sk-anspire-test-value",
            "STOCK_LIST=600519",
        )

        with patch.dict(os.environ, {}, clear=True):
            status = self.service.get_setup_status()

        checks = {check["key"]: check for check in status["checks"]}
        self.assertTrue(status["is_complete"])
        self.assertEqual(checks["llm_primary"]["status"], "configured")
        self.assertIn("openai/Doubao-Seed-2.0-lite", checks["llm_primary"]["message"])

    def test_get_setup_status_treats_blank_anspire_channel_enabled_as_shared_disable(self) -> None:
        self._rewrite_env(
            "LLM_CHANNELS=anspire",
            "LLM_ANSPIRE_ENABLED=",
            "ANSPIRE_LLM_ENABLED=false",
            "ANSPIRE_API_KEYS=sk-anspire-test-value",
            "STOCK_LIST=600519",
        )

        with patch.dict(os.environ, {}, clear=True):
            status = self.service.get_setup_status()

        checks = {check["key"]: check for check in status["checks"]}
        self.assertFalse(status["is_complete"])
        self.assertEqual(checks["llm_primary"]["status"], "needs_action")
        self.assertIn("llm_primary", status["required_missing_keys"])

    def test_get_setup_status_respects_disabled_anspire_channel_without_legacy_fallback(self) -> None:
        self._rewrite_env(
            "LLM_CHANNELS=anspire",
            "LLM_ANSPIRE_ENABLED=false",
            "ANSPIRE_API_KEYS=sk-anspire-test-value",
            "STOCK_LIST=600519",
        )

        with patch.dict(os.environ, {}, clear=True):
            status = self.service.get_setup_status()

        checks = {check["key"]: check for check in status["checks"]}
        self.assertFalse(status["is_complete"])
        self.assertEqual(checks["llm_primary"]["status"], "needs_action")
        self.assertIn("llm_primary", status["required_missing_keys"])

    def test_get_setup_status_accepts_direct_env_primary_without_provider_key(self) -> None:
        self._rewrite_env(
            "LITELLM_MODEL=minimax/MiniMax-M1",
            "STOCK_LIST=600519",
        )

        with patch.dict(os.environ, {}, clear=True):
            status = self.service.get_setup_status()

        checks = {check["key"]: check for check in status["checks"]}
        self.assertTrue(status["is_complete"])
        self.assertEqual(checks["llm_primary"]["status"], "configured")
        self.assertEqual(checks["llm_agent"]["status"], "inherited")

    def test_get_setup_status_matches_notification_channel_requirements(self) -> None:
        base_lines = [
            "LITELLM_MODEL=gemini/gemini-3-flash-preview",
            "GEMINI_API_KEY=secret-key-value",
            "STOCK_LIST=600519",
        ]

        self._rewrite_env(*base_lines, "PUSHOVER_USER_KEY=user-key")
        with patch.dict(os.environ, {}, clear=True):
            status = self.service.get_setup_status()
        pushover_partial = next(check for check in status["checks"] if check["key"] == "notification")
        self.assertEqual(pushover_partial["status"], "optional")

        self._rewrite_env(*base_lines, "PUSHOVER_USER_KEY=user-key", "PUSHOVER_API_TOKEN=app-token")
        with patch.dict(os.environ, {}, clear=True):
            status = self.service.get_setup_status()
        pushover_complete = next(check for check in status["checks"] if check["key"] == "notification")
        self.assertEqual(pushover_complete["status"], "configured")

        self._rewrite_env(*base_lines, "SLACK_BOT_TOKEN=xoxb-test", "SLACK_CHANNEL_ID=C123")
        with patch.dict(os.environ, {}, clear=True):
            status = self.service.get_setup_status()
        slack_complete = next(check for check in status["checks"] if check["key"] == "notification")
        self.assertEqual(slack_complete["status"], "configured")

        self._rewrite_env(*base_lines, "ASTRBOT_URL=https://astrbot.example/webhook")
        with patch.dict(os.environ, {}, clear=True):
            status = self.service.get_setup_status()
        astrbot_complete = next(check for check in status["checks"] if check["key"] == "notification")
        self.assertEqual(astrbot_complete["status"], "configured")

        self._rewrite_env(*base_lines, "NTFY_URL=https://ntfy.sh/hrs-topic")
        with patch.dict(os.environ, {}, clear=True):
            status = self.service.get_setup_status()
        ntfy_complete = next(check for check in status["checks"] if check["key"] == "notification")
        self.assertEqual(ntfy_complete["status"], "configured")

        self._rewrite_env(*base_lines, "NTFY_URL=https://ntfy.sh")
        with patch.dict(os.environ, {}, clear=True):
            status = self.service.get_setup_status()
        ntfy_without_topic = next(check for check in status["checks"] if check["key"] == "notification")
        self.assertEqual(ntfy_without_topic["status"], "optional")

        self._rewrite_env(*base_lines, "GOTIFY_URL=https://gotify.example")
        with patch.dict(os.environ, {}, clear=True):
            status = self.service.get_setup_status()
        gotify_partial = next(check for check in status["checks"] if check["key"] == "notification")
        self.assertEqual(gotify_partial["status"], "optional")

        self._rewrite_env(*base_lines, "GOTIFY_URL=https://gotify.example", "GOTIFY_TOKEN=app-token")
        with patch.dict(os.environ, {}, clear=True):
            status = self.service.get_setup_status()
        gotify_complete = next(check for check in status["checks"] if check["key"] == "notification")
        self.assertEqual(gotify_complete["status"], "configured")

        self._rewrite_env(*base_lines, "GOTIFY_URL=https://gotify.example/message", "GOTIFY_TOKEN=app-token")
        with patch.dict(os.environ, {}, clear=True):
            status = self.service.get_setup_status()
        gotify_with_message = next(check for check in status["checks"] if check["key"] == "notification")
        self.assertEqual(gotify_with_message["status"], "optional")

    def test_get_setup_status_accepts_feishu_app_bot_triad(self) -> None:
        self._rewrite_env(
            "LITELLM_MODEL=gemini/gemini-3-flash-preview",
            "GEMINI_API_KEY=secret-key-value",
            "STOCK_LIST=600519",
            "FEISHU_APP_ID=cli_xxx",
            "FEISHU_APP_SECRET=secret_xxx",
            "FEISHU_CHAT_ID=oc_xxx",
        )

        with patch.dict(os.environ, {}, clear=True):
            status = self.service.get_setup_status()

        notification = next(check for check in status["checks"] if check["key"] == "notification")
        self.assertEqual(notification["status"], "configured")

    def test_get_setup_status_rejects_partial_feishu_app_bot_triad(self) -> None:
        base_lines = [
            "LITELLM_MODEL=gemini/gemini-3-flash-preview",
            "GEMINI_API_KEY=secret-key-value",
            "STOCK_LIST=600519",
        ]
        partial_cases = [
            ("FEISHU_APP_ID=cli_xxx", "FEISHU_APP_SECRET=secret_xxx"),
            ("FEISHU_APP_ID=cli_xxx", "FEISHU_CHAT_ID=oc_xxx"),
            ("FEISHU_APP_SECRET=secret_xxx", "FEISHU_CHAT_ID=oc_xxx"),
        ]

        for partial in partial_cases:
            with self.subTest(partial=partial):
                self._rewrite_env(*base_lines, *partial)
                with patch.dict(os.environ, {}, clear=True):
                    status = self.service.get_setup_status()
                notification = next(check for check in status["checks"] if check["key"] == "notification")
                self.assertEqual(notification["status"], "optional")

    def test_get_setup_status_uses_runtime_env_without_reloading_singletons(self) -> None:
        self._rewrite_env("")

        with patch.dict(
            os.environ,
            {
                "LITELLM_MODEL": "gemini/gemini-3-flash-preview",
                "GEMINI_API_KEY": "runtime-secret",
                "STOCK_LIST": "600519",
            },
            clear=True,
        ), patch("src.application.runtime.system_config_service.Config.reset_instance") as mock_reset, \
             patch("src.application.runtime.system_config_service.setup_env") as mock_setup_env:
            status = self.service.get_setup_status()

        self.assertTrue(status["is_complete"])
        mock_reset.assert_not_called()
        mock_setup_env.assert_not_called()

    def test_get_setup_status_storage_check_does_not_create_database_parent(self) -> None:
        missing_parent = Path(self.temp_dir.name) / "missing-data"
        db_path = missing_parent / "stock_analysis.db"
        self._rewrite_env(
            "LITELLM_MODEL=gemini/gemini-3-flash-preview",
            "GEMINI_API_KEY=secret-key-value",
            "STOCK_LIST=600519",
            f"DATABASE_PATH={db_path}",
        )

        with patch.dict(os.environ, {}, clear=True):
            status = self.service.get_setup_status()

        storage_check = next(check for check in status["checks"] if check["key"] == "storage")
        self.assertEqual(storage_check["status"], "configured")
        self.assertFalse(missing_parent.exists())
