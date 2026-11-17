"""Tests for system config read."""

from tests.application.runtime._system_config_service_support import (
    Config,
    _SystemConfigRuntimePortWiringTestCaseFixture,
    _SystemConfigServiceTestCaseFixture,
    configure_system_config_runtime,
    os,
    patch,
    system_config_service,
    unittest,
)


class SystemConfigServiceTestCase(_SystemConfigServiceTestCaseFixture, unittest.TestCase):
    def test_get_config_uses_switch_default_for_missing_report_model_toggle(self) -> None:
        payload = self.service.get_config(include_schema=True)
        items = {item["key"]: item for item in payload["items"]}

        self.assertEqual(items["REPORT_SHOW_LLM_MODEL"]["value"], "true")
        self.assertFalse(items["REPORT_SHOW_LLM_MODEL"]["raw_value_exists"])

        self._rewrite_env(
            "STOCK_LIST=600519,000001",
            "GEMINI_API_KEY=secret-key-value",
            "SCHEDULE_TIME=18:00",
            "LOG_LEVEL=INFO",
            "REPORT_SHOW_LLM_MODEL=false",
        )

        payload = self.service.get_config(include_schema=True)
        items = {item["key"]: item for item in payload["items"]}

        self.assertEqual(items["REPORT_SHOW_LLM_MODEL"]["value"], "false")
        self.assertTrue(items["REPORT_SHOW_LLM_MODEL"]["raw_value_exists"])

    def test_get_config_preserves_explicit_empty_switch_value(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519,000001",
            "GEMINI_API_KEY=secret-key-value",
            "SCHEDULE_TIME=18:00",
            "LOG_LEVEL=INFO",
            "WEBHOOK_VERIFY_SSL=",
        )

        payload = self.service.get_config(include_schema=True)
        items = {item["key"]: item for item in payload["items"]}

        self.assertEqual(items["WEBHOOK_VERIFY_SSL"]["value"], "")
        self.assertTrue(items["WEBHOOK_VERIFY_SSL"]["raw_value_exists"])

    def test_get_config_uses_runtime_env_as_display_fallback(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519",
            "LOG_LEVEL=INFO",
        )

        with patch.dict(
            os.environ,
            {
                "STOCK_LIST": "300750",
                "LITELLM_MODEL": "openai/gpt-5",
                "LLM_CHANNELS": "my_proxy",
                "LLM_MY_PROXY_BASE_URL": "https://proxy.example.com/v1",
                "LLM_MY_PROXY_MODELS": "gpt-5",
                "LLM_UNUSED_API_KEY": "sk-should-not-leak",
                "UNRELATED_API_KEY": "sk-should-not-leak",
            },
        ):
            payload = self.service.get_config(include_schema=True)
            raw_payload = self.service.get_config(include_schema=False)

        items = {item["key"]: item for item in payload["items"]}
        raw_items = {item["key"]: item for item in raw_payload["items"]}
        self.assertEqual(items["STOCK_LIST"]["value"], "600519")
        self.assertTrue(items["STOCK_LIST"]["raw_value_exists"])
        self.assertEqual(items["LITELLM_MODEL"]["value"], "openai/gpt-5")
        self.assertFalse(items["LITELLM_MODEL"]["raw_value_exists"])
        self.assertEqual(items["LLM_CHANNELS"]["value"], "my_proxy")
        self.assertFalse(items["LLM_CHANNELS"]["raw_value_exists"])
        self.assertEqual(items["LLM_MY_PROXY_BASE_URL"]["value"], "https://proxy.example.com/v1")
        self.assertFalse(items["LLM_MY_PROXY_BASE_URL"]["raw_value_exists"])
        self.assertEqual(items["LLM_MY_PROXY_MODELS"]["value"], "gpt-5")
        self.assertFalse(items["LLM_MY_PROXY_MODELS"]["raw_value_exists"])
        self.assertNotIn("LLM_UNUSED_API_KEY", items)
        self.assertNotIn("UNRELATED_API_KEY", items)
        self.assertNotIn("LLM_UNUSED_API_KEY", raw_items)
        self.assertNotIn("UNRELATED_API_KEY", raw_items)

    def test_get_config_switch_type_uses_runtime_env_display_fallback(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519",
            "LOG_LEVEL=INFO",
        )

        with patch.dict(os.environ, {"REPORT_SHOW_LLM_MODEL": "false"}, clear=False):
            payload = self.service.get_config(include_schema=True)

        items = {item["key"]: item for item in payload["items"]}
        self.assertEqual(items["REPORT_SHOW_LLM_MODEL"]["value"], "false")
        self.assertFalse(items["REPORT_SHOW_LLM_MODEL"]["raw_value_exists"])

    def test_get_config_with_schema_hides_unregistered_env_keys(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519,000001",
            "DATABASE_PATH=./custom/stock_analysis.db",
            "SQLITE_WAL_ENABLED=true",
            "USE_PROXY=true",
            "PROXY_HOST=127.0.0.1",
            "PROXY_PORT=10809",
            "LOG_DIR=./logs",
        )

        payload = self.service.get_config(include_schema=True)
        items = {item["key"]: item for item in payload["items"]}

        self.assertNotIn("DATABASE_PATH", items)
        self.assertNotIn("SQLITE_WAL_ENABLED", items)
        self.assertNotIn("USE_PROXY", items)
        self.assertNotIn("PROXY_HOST", items)
        self.assertNotIn("PROXY_PORT", items)
        self.assertIn("LOG_DIR", items)
        self.assertEqual(items["LOG_DIR"]["schema"]["help_key"], "settings.system.LOG_DIR")

    def test_get_config_without_schema_keeps_unregistered_env_keys(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519,000001",
            "DATABASE_PATH=./custom/stock_analysis.db",
            "SQLITE_WAL_ENABLED=true",
        )

        payload = self.service.get_config(include_schema=False)
        items = {item["key"]: item for item in payload["items"]}

        self.assertEqual(items["DATABASE_PATH"]["value"], "./custom/stock_analysis.db")
        self.assertEqual(items["SQLITE_WAL_ENABLED"]["value"], "true")
        self.assertNotIn("schema", items["DATABASE_PATH"])

    def test_get_config_preserves_labeled_select_options_and_enum_validation(self) -> None:
        payload = self.service.get_config(include_schema=True)
        items = {item["key"]: item for item in payload["items"]}

        agent_arch_schema = items["AGENT_ARCH"]["schema"]
        self.assertEqual(agent_arch_schema["options"][0]["value"], "single")
        self.assertEqual(agent_arch_schema["options"][1]["label"], "Multi Agent (Orchestrator)")
        self.assertEqual(agent_arch_schema["validation"]["enum"], ["single", "multi"])

        report_language_schema = items["REPORT_LANGUAGE"]["schema"]
        self.assertEqual(report_language_schema["validation"]["enum"], ["zh", "en", "ko"])
        self.assertEqual(report_language_schema["options"][1]["value"], "en")
        self.assertEqual(report_language_schema["options"][2]["value"], "ko")

        self.assertEqual(items["AGENT_ORCHESTRATOR_TIMEOUT_S"]["schema"]["default_value"], "600")
        self.assertTrue(items["AGENT_DEEP_RESEARCH_BUDGET"]["schema"]["is_editable"])
        self.assertTrue(items["AGENT_EVENT_MONITOR_ENABLED"]["schema"]["is_editable"])

        context_profile_schema = items["AGENT_CONTEXT_COMPRESSION_PROFILE"]["schema"]
        self.assertEqual(
            [option["label"] for option in context_profile_schema["options"]],
            ["成本优先", "均衡推荐", "长上下文原文优先"],
        )
        self.assertEqual(
            context_profile_schema["validation"]["enum"],
            ["cost", "balanced", "long_context_raw_first"],
        )
        market_review_schema = items["MARKET_REVIEW_REGION"]["schema"]
        self.assertEqual(
            market_review_schema["validation"]["allowed_values"],
            ["cn", "hk", "us", "jp", "kr", "both"],
        )
        self.assertEqual(market_review_schema["validation"]["delimiter"], ",")
        self.assertEqual(
            items["AGENT_CONTEXT_COMPRESSION_TRIGGER_TOKENS"]["schema"]["default_value"],
            "",
        )
        self.assertEqual(
            items["AGENT_CONTEXT_PROTECTED_TURNS"]["schema"]["default_value"],
            "",
        )

    def test_config_loads_context_compression_preset_when_numeric_values_are_blank(self) -> None:
        self.env_path.write_text(
            "\n".join(
                [
                    "AGENT_CONTEXT_COMPRESSION_PROFILE=cost",
                    "AGENT_CONTEXT_COMPRESSION_TRIGGER_TOKENS=",
                    "AGENT_CONTEXT_PROTECTED_TURNS=",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        with patch.dict(os.environ, {"ENV_FILE": str(self.env_path)}, clear=True):
            config = Config._load_from_env()

        self.assertEqual(config.agent_context_compression_profile, "cost")
        self.assertEqual(config.agent_context_compression_trigger_tokens, 6000)
        self.assertEqual(config.agent_context_protected_turns, 2)

        self.env_path.write_text(
            "AGENT_CONTEXT_COMPRESSION_PROFILE=long_context_raw_first\n",
            encoding="utf-8",
        )
        with patch.dict(os.environ, {"ENV_FILE": str(self.env_path)}, clear=True):
            config = Config._load_from_env()

        self.assertEqual(config.agent_context_compression_profile, "long_context_raw_first")
        self.assertEqual(config.agent_context_compression_trigger_tokens, 24000)
        self.assertEqual(config.agent_context_protected_turns, 6)

        self.env_path.write_text(
            "\n".join(
                [
                    "AGENT_CONTEXT_COMPRESSION_PROFILE=bad-profile",
                    "AGENT_CONTEXT_COMPRESSION_TRIGGER_TOKENS=bad-int",
                    "AGENT_CONTEXT_PROTECTED_TURNS=0",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        with patch.dict(os.environ, {"ENV_FILE": str(self.env_path)}, clear=True):
            config = Config._load_from_env()

        self.assertEqual(config.agent_context_compression_profile, "balanced")
        self.assertEqual(config.agent_context_compression_trigger_tokens, 12000)
        self.assertEqual(config.agent_context_protected_turns, 4)

    def test_get_config_projects_legacy_strategy_aliases_onto_skill_fields(self) -> None:
        self._rewrite_env(
            "AGENT_STRATEGY_DIR=legacy-strategies",
            "AGENT_STRATEGY_AUTOWEIGHT=false",
            "AGENT_STRATEGY_ROUTING=manual",
        )

        payload = self.service.get_config(include_schema=True)
        items = {item["key"]: item for item in payload["items"]}

        self.assertEqual(items["AGENT_SKILL_DIR"]["value"], "legacy-strategies")
        self.assertEqual(items["AGENT_SKILL_AUTOWEIGHT"]["value"], "false")
        self.assertEqual(items["AGENT_SKILL_ROUTING"]["value"], "manual")
        self.assertNotIn("AGENT_STRATEGY_DIR", items)
        self.assertNotIn("AGENT_STRATEGY_AUTOWEIGHT", items)
        self.assertNotIn("AGENT_STRATEGY_ROUTING", items)

    def test_get_config_respects_empty_canonical_skill_field_over_legacy_alias(self) -> None:
        self._rewrite_env(
            "AGENT_SKILL_DIR=",
            "AGENT_STRATEGY_DIR=legacy-strategies",
        )

        payload = self.service.get_config(include_schema=True)
        items = {item["key"]: item for item in payload["items"]}

        self.assertEqual(items["AGENT_SKILL_DIR"]["value"], "")

    def test_get_config_normalizes_legacy_orchestrator_mode_for_ui(self) -> None:
        self._rewrite_env("AGENT_ORCHESTRATOR_MODE=strategy")

        payload = self.service.get_config(include_schema=True)
        items = {item["key"]: item for item in payload["items"]}

        self.assertEqual(items["AGENT_ORCHESTRATOR_MODE"]["value"], "specialist")
        self.assertEqual(
            items["AGENT_ORCHESTRATOR_MODE"]["schema"]["validation"]["enum"],
            ["quick", "standard", "full", "specialist", "strategy", "skill"],
        )

    def test_import_env_market_review_region_accepts_comma_separated_regions(self) -> None:
        response = self.service.import_env(
            config_version=self.manager.get_config_version(),
            content="MARKET_REVIEW_REGION=jp,kr\n",
            reload_now=False,
        )

        self.assertTrue(response["success"])
        current_map = self.manager.read_config_map()
        self.assertEqual(current_map["MARKET_REVIEW_REGION"], "jp,kr")


class SystemConfigRuntimePortWiringTestCase(_SystemConfigRuntimePortWiringTestCaseFixture, unittest.TestCase):
    def test_configure_system_config_runtime_binds_adapters_idempotently(self) -> None:
        from src.application.runtime.system_config_ports import (  # noqa: F401  契约锚点
            ConfigProbePort,
            NotificationDispatchPort,
            RuntimeResetPort,
        )
        from src.infrastructure.providers.system_config_runtime import (
            NotificationDispatchAdapter,
            RuntimeResetAdapter,
            SystemConfigProbeAdapter,
        )

        originals = (
            system_config_service._config_probe_port,
            system_config_service._notification_dispatch_port,
            system_config_service._runtime_reset_port,
        )
        try:
            system_config_service.set_config_probe_port(None)  # None 不覆盖：幂等语义
            system_config_service.set_notification_dispatch_port(None)
            system_config_service.set_runtime_reset_port(None)
            self.assertIsInstance(
                system_config_service._get_config_probe_port(), SystemConfigProbeAdapter
            )
            configure_system_config_runtime()
            configure_system_config_runtime()
            self.assertIsInstance(
                system_config_service._get_config_probe_port(), SystemConfigProbeAdapter
            )
            self.assertIsInstance(
                system_config_service._get_notification_dispatch_port(),
                NotificationDispatchAdapter,
            )
            self.assertIsInstance(
                system_config_service._get_runtime_reset_port(), RuntimeResetAdapter
            )
        finally:
            (
                system_config_service._config_probe_port,
                system_config_service._notification_dispatch_port,
                system_config_service._runtime_reset_port,
            ) = originals
