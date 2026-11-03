"""Tests for system config backends."""

from tests.application.runtime._system_config_service_support import (
    Config,
    ConfigValidationError,
    GENERATION_ONLY_BACKEND_IDS,
    _SystemConfigServiceTestCaseFixture,
    os,
    patch,
    unittest,
)


class SystemConfigServiceTestCase(_SystemConfigServiceTestCaseFixture, unittest.TestCase):
    def test_agent_backend_status_prefers_runtime_litellm_over_saved_codex(self) -> None:
        self._assert_agent_backend_status_matches_runtime(
            saved_backend="codex_app_server",
            runtime_backend="litellm",
        )

    def test_agent_backend_status_prefers_runtime_codex_over_saved_litellm(self) -> None:
        self._assert_agent_backend_status_matches_runtime(
            saved_backend="litellm",
            runtime_backend="codex_app_server",
        )

    def test_agent_backend_empty_preview_uses_runtime_generation_route(self) -> None:
        from src.application.runtime.agent_backend_status import AgentBackendStatusService

        self._rewrite_env(
            "AGENT_BACKEND=litellm",
            "LITELLM_MODEL=",
            "OPENAI_API_KEY=",
        )
        runtime_env = {
            "ENV_FILE": str(self.env_path),
            "AGENT_BACKEND": "litellm",
            "LITELLM_MODEL": "openai/gpt-4o",
            "OPENAI_API_KEY": "runtime-key",
        }
        with patch.dict(os.environ, runtime_env, clear=True):
            Config.reset_instance()
            runtime_config = Config.get_instance()
            settings_status = self.service.get_agent_backend_status()
            chat_status = AgentBackendStatusService(config=runtime_config).get_status()
            preview_baseline = self.service.preview_agent_backend_status(items=[])
            preview_draft = self.service.preview_agent_backend_status(
                items=[
                    {"key": "LITELLM_MODEL", "value": ""},
                    {"key": "OPENAI_API_KEY", "value": ""},
                ],
            )

        self.assertEqual(settings_status, chat_status)
        self.assertEqual(preview_baseline, chat_status)
        self.assertTrue(chat_status["available"])
        self.assertFalse(preview_draft["available"])
        self.assertEqual(preview_draft["message"], "no_agent_primary")

    def test_get_config_preserves_manual_agent_codex_cli_value_without_schema_option(self) -> None:
        for backend in sorted(GENERATION_ONLY_BACKEND_IDS):
            with self.subTest(backend=backend):
                self._rewrite_env(
                    "STOCK_LIST=600519,000001",
                    f"AGENT_GENERATION_BACKEND={backend}",
                )

                payload = self.service.get_config(include_schema=True)
                items = {item["key"]: item for item in payload["items"]}
                agent_item = items["AGENT_GENERATION_BACKEND"]

                self.assertEqual(agent_item["value"], backend)
                self.assertNotIn(
                    backend,
                    {option["value"] for option in agent_item["schema"]["options"]},
                )

    def test_generation_backend_status_preview_uses_draft_backend(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=litellm",
            "LITELLM_MODEL=gemini/gemini-3-flash-preview",
            "GEMINI_API_KEY=secret-key-value",
        )

        with patch("src.infrastructure.generation.local_cli_backend.shutil.which", return_value=None):
            payload = self.service.preview_generation_backend_status(
                items=[
                    {"key": "GENERATION_BACKEND", "value": "codex_cli"},
                    {"key": "GENERATION_FALLBACK_BACKEND", "value": ""},
                ],
                mask_token="******",
            )

        self.assertEqual(payload["primary_backend_id"], "codex_cli")
        self.assertFalse(payload["primary"]["available"])
        self.assertEqual(payload["primary"]["health_status"], "failed")
        self.assertEqual(payload["primary"]["last_error_code"], "command_not_found")

    def test_generation_backend_status_saved_invalid_numeric_returns_failed_status(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=codex_cli",
            "GENERATION_FALLBACK_BACKEND=",
            "GENERATION_BACKEND_TIMEOUT_SECONDS=not-int",
        )

        payload = self.service.get_generation_backend_status()

        self.assertEqual(payload["primary_backend_id"], "codex_cli")
        self.assertFalse(payload["primary"]["available"])
        self.assertEqual(payload["primary"]["health_status"], "failed")
        self.assertEqual(payload["primary"]["last_error_code"], "unsafe_config")

    def test_generation_backend_preview_invalid_numeric_returns_validation_error(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=codex_cli",
            "GENERATION_FALLBACK_BACKEND=",
        )

        with self.assertRaises(ConfigValidationError) as ctx:
            self.service.preview_generation_backend_status(
                items=[{"key": "GENERATION_BACKEND_TIMEOUT_SECONDS", "value": "not-int"}],
                mask_token="******",
            )

        self.assertEqual(ctx.exception.issues[0]["key"], "GENERATION_BACKEND_TIMEOUT_SECONDS")
        self.assertEqual(ctx.exception.issues[0]["severity"], "error")

    def test_generation_backend_status_saved_litellm_invalid_channel_returns_failed_status(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=litellm",
            "LLM_CHANNELS=remote",
            "LLM_REMOTE_PROTOCOL=openai",
            "LLM_REMOTE_BASE_URL=http://169.254.169.254/v1",
            "LLM_REMOTE_API_KEY=sk-remote",
            "LLM_REMOTE_MODELS=gpt-4o-mini",
        )

        payload = self.service.get_generation_backend_status()

        self.assertEqual(payload["primary_backend_id"], "litellm")
        self.assertFalse(payload["primary"]["available"])
        self.assertEqual(payload["primary"]["health_status"], "failed")
        self.assertEqual(payload["primary"]["last_error_code"], "unsafe_config")

    def test_generation_backend_status_saved_litellm_model_without_key_returns_failed_status(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=litellm",
            "LITELLM_MODEL=gemini/gemini-3-flash-preview",
        )

        with patch.dict(os.environ, {"ENV_FILE": str(self.env_path)}, clear=True):
            payload = self.service.get_generation_backend_status()

        self.assertEqual(payload["primary_backend_id"], "litellm")
        self.assertFalse(payload["primary"]["available"])
        self.assertEqual(payload["primary"]["health_status"], "failed")
        self.assertEqual(payload["primary"]["last_error_code"], "unsafe_config")

    def test_generation_backend_preview_litellm_model_without_key_returns_validation_error(self) -> None:
        self._rewrite_env("GENERATION_BACKEND=litellm")

        with patch.dict(os.environ, {"ENV_FILE": str(self.env_path)}, clear=True):
            with self.assertRaises(ConfigValidationError) as ctx:
                self.service.preview_generation_backend_status(
                    items=[{"key": "LITELLM_MODEL", "value": "gemini/gemini-3-flash-preview"}],
                    mask_token="******",
                )

        self.assertEqual(ctx.exception.issues[0]["key"], "LITELLM_MODEL")
        self.assertEqual(ctx.exception.issues[0]["code"], "missing_runtime_source")

    def test_generation_backend_preview_uses_openai_model_draft(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=litellm",
            "OPENAI_API_KEY=secret-key-value",
            "OPENAI_MODEL=gpt-5.5",
        )

        with patch.dict(os.environ, {"ENV_FILE": str(self.env_path)}, clear=True):
            payload = self.service.preview_generation_backend_status(
                items=[{"key": "OPENAI_MODEL", "value": "gemini/gemini-3-flash-preview"}],
                mask_token="******",
            )

        self.assertEqual(payload["primary_backend_id"], "litellm")
        self.assertFalse(payload["primary"]["available"])
        self.assertEqual(payload["primary"]["last_error_code"], "unsafe_config")

    def test_generation_backend_preview_uses_gemini_model_draft(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=litellm",
            "GEMINI_API_KEY=secret-key-value",
            "GEMINI_MODEL=gemini-3.1-pro-preview",
        )

        with patch.dict(os.environ, {"ENV_FILE": str(self.env_path)}, clear=True):
            payload = self.service.preview_generation_backend_status(
                items=[{"key": "GEMINI_MODEL", "value": "openai/gpt-5.5"}],
                mask_token="******",
            )

        self.assertEqual(payload["primary_backend_id"], "litellm")
        self.assertFalse(payload["primary"]["available"])
        self.assertEqual(payload["primary"]["last_error_code"], "unsafe_config")

    def test_generation_backend_status_uses_runtime_provider_key_fallback(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=litellm",
            "LITELLM_MODEL=gemini/gemini-3-flash-preview",
        )

        with patch.dict(
            os.environ,
            {
                "ENV_FILE": str(self.env_path),
                "GEMINI_API_KEY": "runtime-secret-value",
            },
            clear=True,
        ):
            payload = self.service.get_generation_backend_status()

        self.assertEqual(payload["primary_backend_id"], "litellm")
        self.assertTrue(payload["primary"]["available"])
        self.assertIsNone(payload["primary"]["last_error_code"])

    def test_generation_backend_preview_local_cli_ignores_inactive_litellm_model_error(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=litellm",
            "LITELLM_MODEL=gemini/gemini-3-flash-preview",
        )

        with patch("src.infrastructure.generation.local_cli_backend.shutil.which", return_value=None):
            payload = self.service.preview_generation_backend_status(
                items=[
                    {"key": "GENERATION_BACKEND", "value": "codex_cli"},
                    {"key": "GENERATION_FALLBACK_BACKEND", "value": ""},
                ],
                mask_token="******",
            )

        self.assertEqual(payload["primary_backend_id"], "codex_cli")
        self.assertEqual(payload["primary"]["last_error_code"], "command_not_found")

    def test_generation_backend_preview_ignores_unrelated_draft_errors(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=litellm",
            "LITELLM_MODEL=gemini/gemini-3-flash-preview",
            "GEMINI_API_KEY=secret-key-value",
        )

        payload = self.service.preview_generation_backend_status(
            items=[{"key": "WECHAT_WEBHOOK_URL", "value": "not-a-url"}],
            mask_token="******",
        )

        self.assertEqual(payload["primary_backend_id"], "litellm")
        self.assertTrue(payload["primary"]["available"])

    def test_generation_backend_status_fallback_error_does_not_fail_primary(self) -> None:
        self._rewrite_env(
            "GENERATION_BACKEND=codex_cli",
            "GENERATION_FALLBACK_BACKEND=bad_backend",
        )

        with patch("src.infrastructure.generation.local_cli_backend.shutil.which", return_value="/usr/bin/codex"), \
             patch("src.infrastructure.generation.local_cli_backend.os.access", return_value=True):
            payload = self.service.get_generation_backend_status()

        self.assertTrue(payload["primary"]["available"])
        self.assertEqual(payload["fallback"]["backend_id"], "bad_backend")
        self.assertFalse(payload["fallback"]["available"])

    def test_validate_rejects_mixed_generation_primary_and_fallback(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "hermes,remote"},
                {"key": "LLM_HERMES_API_KEY", "value": "sk-hermes-test-value"},
                {"key": "LLM_HERMES_MODELS", "value": "shared-route"},
                {"key": "LLM_REMOTE_PROTOCOL", "value": "openai"},
                {"key": "LLM_REMOTE_BASE_URL", "value": "https://api.example.com/v1"},
                {"key": "LLM_REMOTE_API_KEY", "value": "sk-remote-test-value"},
                {"key": "LLM_REMOTE_MODELS", "value": "shared-route"},
                {"key": "LITELLM_MODEL", "value": "openai/shared-route"},
                {"key": "LITELLM_FALLBACK_MODELS", "value": "openai/shared-route"},
            ]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(
            any(
                issue["key"] == "LITELLM_MODEL"
                and issue["code"] == "mixed_hermes_route_unsupported"
                for issue in validation["issues"]
            )
        )
        self.assertTrue(
            any(
                issue["key"] == "LITELLM_FALLBACK_MODELS"
                and issue["code"] == "mixed_hermes_route_unsupported"
                for issue in validation["issues"]
            )
        )

    def test_validate_rejects_bare_mixed_generation_primary_and_fallback(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "hermes,remote"},
                {"key": "LLM_HERMES_API_KEY", "value": "sk-hermes-test-value"},
                {"key": "LLM_HERMES_MODELS", "value": "shared-route"},
                {"key": "LLM_REMOTE_PROTOCOL", "value": "openai"},
                {"key": "LLM_REMOTE_BASE_URL", "value": "https://api.example.com/v1"},
                {"key": "LLM_REMOTE_API_KEY", "value": "sk-remote-test-value"},
                {"key": "LLM_REMOTE_MODELS", "value": "shared-route"},
                {"key": "LITELLM_MODEL", "value": "shared-route"},
                {"key": "LITELLM_FALLBACK_MODELS", "value": "shared-route"},
            ]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(
            any(
                issue["key"] == "LITELLM_MODEL"
                and issue["code"] == "mixed_hermes_route_unsupported"
                for issue in validation["issues"]
            )
        )
        self.assertTrue(
            any(
                issue["key"] == "LITELLM_FALLBACK_MODELS"
                and issue["code"] == "mixed_hermes_route_unsupported"
                for issue in validation["issues"]
            )
        )

    def test_validate_rejects_codex_backend_with_multi_agent_architecture(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "AGENT_BACKEND", "value": "codex_app_server"},
                {"key": "AGENT_ARCH", "value": "multi"},
            ]
        )

        self.assertFalse(validation["valid"])
        issue = next(
            issue
            for issue in validation["issues"]
            if issue["code"] == "unsupported_agent_arch"
        )
        self.assertEqual(issue["key"], "AGENT_ARCH")
        self.assertEqual(issue["expected"], "single")

    def test_validate_rejects_disabled_timeout_for_codex_only(self) -> None:
        codex = self.service.validate(
            items=[
                {"key": "AGENT_BACKEND", "value": "codex_app_server"},
                {"key": "AGENT_ORCHESTRATOR_TIMEOUT_S", "value": "0"},
            ]
        )
        litellm = self.service.validate(
            items=[
                {"key": "AGENT_BACKEND", "value": "litellm"},
                {"key": "AGENT_ORCHESTRATOR_TIMEOUT_S", "value": "0"},
            ]
        )

        self.assertFalse(codex["valid"])
        self.assertTrue(
            any(issue["code"] == "codex_timeout_required" for issue in codex["issues"])
        )
        self.assertTrue(litellm["valid"])

    def test_validate_reports_generation_backend_numeric_maximum(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "GENERATION_BACKEND_TIMEOUT_SECONDS", "value": "3601"},
                {"key": "GENERATION_BACKEND_MAX_OUTPUT_BYTES", "value": "33554433"},
                {"key": "GENERATION_BACKEND_MAX_CONCURRENCY", "value": "17"},
                {"key": "LOCAL_CLI_BACKEND_MAX_CONCURRENCY", "value": "5"},
            ]
        )

        self.assertFalse(validation["valid"])
        issues = {issue["key"]: issue for issue in validation["issues"]}
        self.assertEqual(issues["GENERATION_BACKEND_TIMEOUT_SECONDS"]["expected"], "<=3600")
        self.assertEqual(issues["GENERATION_BACKEND_MAX_OUTPUT_BYTES"]["expected"], "<=33554432")
        self.assertEqual(issues["GENERATION_BACKEND_MAX_CONCURRENCY"]["expected"], "<=16")
        self.assertEqual(issues["LOCAL_CLI_BACKEND_MAX_CONCURRENCY"]["expected"], "<=4")
