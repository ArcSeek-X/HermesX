"""Tests for system config env transfer."""

from tests.application.runtime._system_config_service_support import (
    ConfigConflictError,
    ConfigImportError,
    _SystemConfigServiceTestCaseFixture,
    unittest,
)


class SystemConfigServiceTestCase(_SystemConfigServiceTestCaseFixture, unittest.TestCase):
    def test_export_desktop_env_returns_raw_text(self) -> None:
        self.env_path.write_text(
            "# Desktop config\nSTOCK_LIST=600519,000001\n\nGEMINI_API_KEY=secret-key-value\n",
            encoding="utf-8",
        )

        payload = self.service.export_desktop_env()

        self.assertEqual(
            payload["content"],
            "# Desktop config\nSTOCK_LIST=600519,000001\n\nGEMINI_API_KEY=secret-key-value\n",
        )
        self.assertEqual(payload["config_version"], self.manager.get_config_version())

    def test_export_desktop_env_preserves_hidden_web_settings_keys(self) -> None:
        self.env_path.write_text(
            "STOCK_LIST=600519\nDATABASE_PATH=./custom/stock_analysis.db\nUSE_PROXY=true\n",
            encoding="utf-8",
        )

        payload = self.service.export_desktop_env()

        self.assertIn("DATABASE_PATH=./custom/stock_analysis.db\n", payload["content"])
        self.assertIn("USE_PROXY=true\n", payload["content"])

    def test_import_desktop_env_merges_keys_without_deleting_unspecified_values(self) -> None:
        current_version = self.manager.get_config_version()

        payload = self.service.import_desktop_env(
            config_version=current_version,
            content="STOCK_LIST=300750\nCUSTOM_NOTE=desktop backup\n",
            reload_now=False,
        )

        self.assertTrue(payload["success"])
        current_map = self.manager.read_config_map()
        self.assertEqual(current_map["STOCK_LIST"], "300750")
        self.assertEqual(current_map["CUSTOM_NOTE"], "desktop backup")
        self.assertEqual(current_map["GEMINI_API_KEY"], "secret-key-value")

    def test_import_desktop_env_preserves_hidden_web_settings_keys(self) -> None:
        current_version = self.manager.get_config_version()

        self.service.import_desktop_env(
            config_version=current_version,
            content="DATABASE_PATH=./custom/stock_analysis.db\nPROXY_HOST=127.0.0.1\n",
            reload_now=False,
        )

        current_map = self.manager.read_config_map()
        self.assertEqual(current_map["DATABASE_PATH"], "./custom/stock_analysis.db")
        self.assertEqual(current_map["PROXY_HOST"], "127.0.0.1")

    def test_import_desktop_env_uses_last_duplicate_assignment(self) -> None:
        current_version = self.manager.get_config_version()

        self.service.import_desktop_env(
            config_version=current_version,
            content="STOCK_LIST=000001\nSTOCK_LIST=300750\n",
            reload_now=False,
        )

        current_map = self.manager.read_config_map()
        self.assertEqual(current_map["STOCK_LIST"], "300750")

    def test_import_desktop_env_allows_empty_assignment(self) -> None:
        current_version = self.manager.get_config_version()

        self.service.import_desktop_env(
            config_version=current_version,
            content="LOG_LEVEL=\n",
            reload_now=False,
        )

        current_map = self.manager.read_config_map()
        self.assertEqual(current_map["LOG_LEVEL"], "")

    def test_import_desktop_env_preserves_exported_braced_webhook_template(self) -> None:
        template = '{"content":${content_json}}'

        save_payload = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[{"key": "CUSTOM_WEBHOOK_BODY_TEMPLATE", "value": template}],
            reload_now=False,
        )
        self.assertTrue(save_payload["success"])
        backup_content = self.service.export_desktop_env()["content"]
        self.assertIn(
            'CUSTOM_WEBHOOK_BODY_TEMPLATE={"content":$${content_json}}\n',
            backup_content,
        )

        clear_payload = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[{"key": "CUSTOM_WEBHOOK_BODY_TEMPLATE", "value": ""}],
            reload_now=False,
        )
        self.assertTrue(clear_payload["success"])

        restore_payload = self.service.import_desktop_env(
            config_version=self.manager.get_config_version(),
            content=backup_content,
            reload_now=False,
        )

        self.assertTrue(restore_payload["success"])
        self.assertEqual(
            self.manager.read_config_map()["CUSTOM_WEBHOOK_BODY_TEMPLATE"],
            template,
        )

    def test_import_desktop_env_rejects_empty_or_comment_only_content(self) -> None:
        with self.assertRaises(ConfigImportError):
            self.service.import_desktop_env(
                config_version=self.manager.get_config_version(),
                content="   \n# only comments\n\n",
                reload_now=False,
            )

    def test_import_desktop_env_raises_conflict_for_stale_version(self) -> None:
        with self.assertRaises(ConfigConflictError):
            self.service.import_desktop_env(
                config_version="stale-version",
                content="STOCK_LIST=300750\n",
                reload_now=False,
            )

    def test_import_desktop_env_restores_runtime_models_after_cleanup(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519,000001",
            "LLM_CHANNELS=deepseek",
            "LLM_DEEPSEEK_PROTOCOL=deepseek",
            "LLM_DEEPSEEK_BASE_URL=https://api.deepseek.com",
            "LLM_DEEPSEEK_API_KEY=sk-test-value",
            "LLM_DEEPSEEK_MODELS=deepseek-chat,deepseek-v4-flash,deepseek-v4-pro",
            "LITELLM_MODEL=deepseek/deepseek-chat",
            "AGENT_LITELLM_MODEL=deepseek/deepseek-v4-pro",
            "LITELLM_FALLBACK_MODELS=deepseek/deepseek-v4-pro,deepseek/deepseek-chat,cohere/command-r-plus",
            "VISION_MODEL=deepseek/deepseek-v4-flash",
        )

        backup_content = self.service.export_desktop_env()["content"]
        pre_clear_map = dict(self.manager.read_config_map())

        clear_response = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[
                {"key": "LLM_DEEPSEEK_MODELS", "value": "deepseek-v4-flash"},
                {"key": "LITELLM_MODEL", "value": ""},
                {"key": "AGENT_LITELLM_MODEL", "value": ""},
                {"key": "LITELLM_FALLBACK_MODELS", "value": "deepseek/deepseek-v4-flash"},
                {"key": "VISION_MODEL", "value": ""},
            ],
            reload_now=False,
        )
        self.assertTrue(clear_response["success"])

        cleared_map = self.manager.read_config_map()
        self.assertEqual(cleared_map["LITELLM_MODEL"], "")
        self.assertEqual(cleared_map["AGENT_LITELLM_MODEL"], "")
        self.assertEqual(cleared_map["VISION_MODEL"], "")
        self.assertEqual(cleared_map["LITELLM_FALLBACK_MODELS"], "deepseek/deepseek-v4-flash")

        restore_payload = self.service.import_desktop_env(
            config_version=self.manager.get_config_version(),
            content=backup_content,
            reload_now=False,
        )
        self.assertTrue(restore_payload["success"])

        restored_map = self.manager.read_config_map()
        self.assertEqual(restored_map["LITELLM_MODEL"], pre_clear_map["LITELLM_MODEL"])
        self.assertEqual(restored_map["AGENT_LITELLM_MODEL"], pre_clear_map["AGENT_LITELLM_MODEL"])
        self.assertEqual(restored_map["VISION_MODEL"], pre_clear_map["VISION_MODEL"])
        self.assertEqual(restored_map["LITELLM_FALLBACK_MODELS"], pre_clear_map["LITELLM_FALLBACK_MODELS"])

    def test_import_desktop_env_restores_provider_and_base_url_after_provider_cleanup(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519,000001",
            "LITELLM_MODEL=openai/gpt-4o-mini",
            "OPENAI_MODEL=gpt-4.1",
            "OPENAI_BASE_URL=https://openai.example.com/v1",
            "OPENAI_API_KEY=legacy-openai-key",
        )

        backup_content = self.service.export_desktop_env()["content"]
        pre_clear_map = dict(self.manager.read_config_map())

        clear_response = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[
                {"key": "LITELLM_MODEL", "value": ""},
                {"key": "OPENAI_MODEL", "value": ""},
                {"key": "OPENAI_BASE_URL", "value": ""},
                {"key": "OPENAI_API_KEY", "value": ""},
            ],
            reload_now=False,
        )
        self.assertTrue(clear_response["success"])

        cleared_map = self.manager.read_config_map()
        self.assertEqual(cleared_map["LITELLM_MODEL"], "")
        self.assertEqual(cleared_map["OPENAI_MODEL"], "")
        self.assertEqual(cleared_map["OPENAI_BASE_URL"], "")
        self.assertEqual(cleared_map["OPENAI_API_KEY"], "")

        restore_payload = self.service.import_desktop_env(
            config_version=self.manager.get_config_version(),
            content=backup_content,
            reload_now=False,
        )
        self.assertTrue(restore_payload["success"])

        restored_map = self.manager.read_config_map()
        self.assertEqual(restored_map["LITELLM_MODEL"], pre_clear_map["LITELLM_MODEL"])
        self.assertEqual(restored_map["OPENAI_MODEL"], pre_clear_map["OPENAI_MODEL"])
        self.assertEqual(restored_map["OPENAI_BASE_URL"], pre_clear_map["OPENAI_BASE_URL"])
        self.assertEqual(restored_map["OPENAI_API_KEY"], pre_clear_map["OPENAI_API_KEY"])
