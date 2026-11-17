"""Tests for system config channels."""

from src.application.runtime.notification_channel_test import NotificationChannelTester

from tests.application.runtime._system_config_service_support import (
    ANSPIRE_LLM_MODEL_DEFAULT,
    Any,
    Config,
    DEFAULT_ALPHASIFT_INSTALL_SPEC,
    Dict,
    Mock,
    SimpleNamespace,
    SystemConfigService,
    _SystemConfigServiceTestCaseFixture,
    _build_llm_models_url,
    os,
    patch,
    requests,
    unittest,
)


class SystemConfigServiceTestCase(_SystemConfigServiceTestCaseFixture, unittest.TestCase):
    def test_get_config_preserves_explicit_empty_report_show_llm_model_value(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519,000001",
            "GEMINI_API_KEY=secret-key-value",
            "SCHEDULE_TIME=18:00",
            "LOG_LEVEL=INFO",
            "REPORT_SHOW_LLM_MODEL=",
        )

        payload = self.service.get_config(include_schema=True)
        items = {item["key"]: item for item in payload["items"]}

        self.assertEqual(items["REPORT_SHOW_LLM_MODEL"]["value"], "")
        self.assertTrue(items["REPORT_SHOW_LLM_MODEL"]["raw_value_exists"])

    def test_get_config_runtime_env_fallback_does_not_persist_llm_fields_on_save(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519",
            "LOG_LEVEL=INFO",
        )

        startup_env = {
            "LITELLM_MODEL": "openai/gpt-5",
            "LLM_CHANNELS": "my_proxy",
            "LLM_MY_PROXY_PROTOCOL": "openai",
            "LLM_MY_PROXY_BASE_URL": "https://proxy.example.com/v1",
            "LLM_MY_PROXY_API_KEYS": "sk-test-value",
            "LLM_MY_PROXY_MODELS": "openai/gpt-5",
        }
        with patch.dict(os.environ, startup_env, clear=False):
            payload_before = self.service.get_config(include_schema=True)
            items_before = {item["key"]: item for item in payload_before["items"]}
            self.assertEqual(items_before["LITELLM_MODEL"]["value"], "openai/gpt-5")
            self.assertFalse(items_before["LITELLM_MODEL"]["raw_value_exists"])
            self.assertEqual(
                items_before["LLM_MY_PROXY_BASE_URL"]["value"],
                "https://proxy.example.com/v1",
            )
            self.assertFalse(items_before["LLM_MY_PROXY_BASE_URL"]["raw_value_exists"])
            self.assertEqual(items_before["LLM_MY_PROXY_MODELS"]["value"], "openai/gpt-5")
            self.assertFalse(items_before["LLM_MY_PROXY_MODELS"]["raw_value_exists"])

            current_version = self.manager.get_config_version()
            response = self.service.update(
                config_version=current_version,
                items=[{"key": "STOCK_LIST", "value": "300750"}],
                reload_now=False,
            )
            self.assertTrue(response["success"])

            current_map = self.manager.read_config_map()
            self.assertEqual(current_map["STOCK_LIST"], "300750")
            self.assertNotIn("LITELLM_MODEL", current_map)
            self.assertNotIn("LLM_MY_PROXY_BASE_URL", current_map)
            self.assertNotIn("LLM_MY_PROXY_MODELS", current_map)

            payload_after = self.service.get_config(include_schema=True)
            items_after = {item["key"]: item for item in payload_after["items"]}
            self.assertEqual(items_after["LITELLM_MODEL"]["value"], "openai/gpt-5")
            self.assertFalse(items_after["LITELLM_MODEL"]["raw_value_exists"])
            self.assertEqual(
                items_after["LLM_MY_PROXY_BASE_URL"]["value"],
                "https://proxy.example.com/v1",
            )
            self.assertFalse(items_after["LLM_MY_PROXY_BASE_URL"]["raw_value_exists"])
            self.assertEqual(items_after["LLM_MY_PROXY_MODELS"]["value"], "openai/gpt-5")
            self.assertFalse(items_after["LLM_MY_PROXY_MODELS"]["raw_value_exists"])

    def test_validate_uses_runtime_injected_llm_channels_for_support_keys(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519",
            "LOG_LEVEL=INFO",
        )

        with patch.dict(
            os.environ,
            {
                "LLM_CHANNELS": "my_proxy",
                "LLM_MY_PROXY_PROTOCOL": "openai",
                "LLM_MY_PROXY_API_KEYS": "sk-test-value",
                "LLM_MY_PROXY_BASE_URL": "https://proxy.example.com/v1",
                "LLM_MY_PROXY_MODELS": "openai/gpt-5",
            },
            clear=False,
        ):
            validation = self.service.validate(
                items=[{"key": "LLM_MY_PROXY_BASE_URL", "value": "not-a-url"}],
            )

        self.assertFalse(validation["valid"])
        self.assertTrue(
            any(
                issue["key"] == "LLM_MY_PROXY_BASE_URL" and issue["code"] == "invalid_url"
                for issue in validation["issues"]
            )
        )

    def test_get_config_with_schema_keeps_declared_llm_channel_support_keys(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519,000001",
            "LLM_CHANNELS=deepseek,my_proxy",
            "LLM_DEEPSEEK_PROTOCOL=deepseek",
            "LLM_DEEPSEEK_BASE_URL=https://api.deepseek.com",
            "LLM_DEEPSEEK_API_KEY=sk-test-value",
            "LLM_DEEPSEEK_MODELS=deepseek-v4-flash,deepseek-v4-pro",
            "LLM_MY_PROXY_PROTOCOL=openai",
            "LLM_MY_PROXY_API_KEYS=sk-key-1,sk-key-2",
            "LLM_MY_PROXY_MODELS=gpt-5.5",
            "LLM_UNUSED_API_KEY=sk-should-not-leak",
            "DATABASE_PATH=./custom/stock_analysis.db",
        )

        payload = self.service.get_config(include_schema=True)
        items = {item["key"]: item for item in payload["items"]}

        self.assertIn("LLM_CHANNELS", items)
        self.assertEqual(items["LLM_DEEPSEEK_API_KEY"]["value"], "sk-test-value")
        self.assertEqual(items["LLM_DEEPSEEK_MODELS"]["value"], "deepseek-v4-flash,deepseek-v4-pro")
        self.assertEqual(items["LLM_MY_PROXY_API_KEYS"]["value"], "sk-key-1,sk-key-2")
        self.assertEqual(items["LLM_MY_PROXY_MODELS"]["value"], "gpt-5.5")
        self.assertEqual(items["LLM_MY_PROXY_API_KEYS"]["schema"]["category"], "ai_model")
        self.assertNotIn("LLM_UNUSED_API_KEY", items)
        self.assertNotIn("DATABASE_PATH", items)

    def test_update_alphasift_enable_does_not_rewrite_llm_fields(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519,000001",
            "LITELLM_MODEL=openai/gpt-4o-mini",
            "AGENT_LITELLM_MODEL=openai/gpt-4o",
            "OPENAI_BASE_URL=https://api.openai.com/v1",
            "LLM_CHANNELS=openai",
            "LLM_OPENAI_PROTOCOL=openai",
            "LLM_OPENAI_BASE_URL=https://api.openai.com/v1",
            "LLM_OPENAI_API_KEYS=legacy-openai-secret",
            "LLM_OPENAI_MODELS=openai/gpt-4o-mini,openai/gpt-4o",
            "LITELLM_FALLBACK_MODELS=openai/gpt-4o-mini,openai/gpt-4o",
            "ALPHASIFT_ENABLED=false",
            f"ALPHASIFT_INSTALL_SPEC={DEFAULT_ALPHASIFT_INSTALL_SPEC}",
            "LLM_USAGE_HMAC_SECRET=telemetry-secret",
            "LLM_USAGE_HMAC_KEY_VERSION=test-v1",
            "GEMINI_API_KEY=legacy-secret",
        )

        response = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[
                {"key": "ALPHASIFT_ENABLED", "value": "true"},
                {"key": "ALPHASIFT_INSTALL_SPEC", "value": "******"},
                {"key": "LLM_USAGE_HMAC_SECRET", "value": "******"},
                {"key": "GEMINI_API_KEY", "value": "******"},
            ],
            mask_token="******",
            reload_now=False,
        )

        self.assertTrue(response["success"])
        self.assertEqual(response["applied_count"], 1)
        self.assertIn("ALPHASIFT_ENABLED", response["updated_keys"])
        self.assertEqual(response["skipped_masked_count"], 3)

        current_map = self.manager.read_config_map()
        self.assertEqual(current_map["ALPHASIFT_ENABLED"], "true")
        self.assertEqual(
            current_map["ALPHASIFT_INSTALL_SPEC"],
            DEFAULT_ALPHASIFT_INSTALL_SPEC,
        )
        self.assertEqual(current_map["LLM_USAGE_HMAC_SECRET"], "telemetry-secret")
        self.assertEqual(current_map["LLM_USAGE_HMAC_KEY_VERSION"], "test-v1")
        self.assertEqual(current_map["GEMINI_API_KEY"], "legacy-secret")
        self.assertEqual(current_map["LITELLM_MODEL"], "openai/gpt-4o-mini")
        self.assertEqual(current_map["AGENT_LITELLM_MODEL"], "openai/gpt-4o")
        self.assertEqual(current_map["OPENAI_BASE_URL"], "https://api.openai.com/v1")
        self.assertEqual(current_map["LLM_CHANNELS"], "openai")
        self.assertEqual(current_map["LLM_OPENAI_PROTOCOL"], "openai")
        self.assertEqual(current_map["LLM_OPENAI_BASE_URL"], "https://api.openai.com/v1")
        self.assertEqual(current_map["LLM_OPENAI_API_KEYS"], "legacy-openai-secret")
        self.assertEqual(current_map["LLM_OPENAI_MODELS"], "openai/gpt-4o-mini,openai/gpt-4o")
        self.assertEqual(current_map["LITELLM_FALLBACK_MODELS"], "openai/gpt-4o-mini,openai/gpt-4o")

    def test_validate_reports_invalid_notification_route_channel(self) -> None:
        validation = self.service.validate(
            items=[{"key": "NOTIFICATION_REPORT_CHANNELS", "value": "wechat,not-a-channel,email"}]
        )
        self.assertFalse(validation["valid"])
        self.assertTrue(
            any(
                issue["key"] == "NOTIFICATION_REPORT_CHANNELS"
                and issue["code"] == "invalid_allowed_value"
                for issue in validation["issues"]
            )
        )

    def test_validate_reports_invalid_llm_channel_definition(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "primary"},
                {"key": "LLM_PRIMARY_PROTOCOL", "value": "openai"},
                {"key": "LLM_PRIMARY_MODELS", "value": "gpt-4o-mini"},
                {"key": "LLM_PRIMARY_API_KEY", "value": ""},
            ]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(any(issue["code"] == "missing_api_key" for issue in validation["issues"]))

    def test_validate_preserves_model_based_protocol_inference_for_ollama_channel(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "lab"},
                {"key": "LLM_LAB_MODELS", "value": "ollama/llama3"},
                {"key": "LLM_LAB_API_KEY", "value": ""},
            ]
        )

        self.assertTrue(validation["valid"], validation["issues"])
        self.assertEqual(validation["issues"], [])

    def test_validate_reports_unknown_primary_model_for_channels(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "primary"},
                {"key": "LLM_PRIMARY_PROTOCOL", "value": "openai"},
                {"key": "LLM_PRIMARY_API_KEY", "value": "sk-test-value"},
                {"key": "LLM_PRIMARY_MODELS", "value": "gpt-4o-mini"},
                {"key": "LITELLM_MODEL", "value": "openai/gpt-4o"},
            ]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(any(issue["key"] == "LITELLM_MODEL" and issue["code"] == "unknown_model" for issue in validation["issues"]))

    def test_validate_rejects_bare_primary_when_channel_route_is_openai_canonical(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "primary"},
                {"key": "LLM_PRIMARY_PROTOCOL", "value": "openai"},
                {"key": "LLM_PRIMARY_API_KEY", "value": "sk-test-value"},
                {"key": "LLM_PRIMARY_MODELS", "value": "gpt-4o-mini"},
                {"key": "LITELLM_MODEL", "value": "gpt-4o-mini"},
            ]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(any(issue["key"] == "LITELLM_MODEL" and issue["code"] == "unknown_model" for issue in validation["issues"]))

    def test_validate_rejects_bare_fallback_when_channel_route_is_openai_canonical(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "primary"},
                {"key": "LLM_PRIMARY_PROTOCOL", "value": "openai"},
                {"key": "LLM_PRIMARY_API_KEY", "value": "sk-test-value"},
                {"key": "LLM_PRIMARY_MODELS", "value": "gpt-4o-mini"},
                {"key": "LITELLM_MODEL", "value": "openai/gpt-4o-mini"},
                {"key": "LITELLM_FALLBACK_MODELS", "value": "gpt-4o-mini"},
            ]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(
            any(
                issue["key"] == "LITELLM_FALLBACK_MODELS"
                and issue["code"] == "unknown_model"
                for issue in validation["issues"]
            )
        )

    def test_validate_reports_bare_vision_when_channel_route_is_openai_canonical(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "primary"},
                {"key": "LLM_PRIMARY_PROTOCOL", "value": "openai"},
                {"key": "LLM_PRIMARY_API_KEY", "value": "sk-test-value"},
                {"key": "LLM_PRIMARY_MODELS", "value": "gpt-4o-mini"},
                {"key": "VISION_MODEL", "value": "gpt-4o-mini"},
            ]
        )

        self.assertTrue(
            any(
                issue["key"] == "VISION_MODEL"
                and issue["code"] == "unknown_model"
                for issue in validation["issues"]
            ),
            validation["issues"],
        )

    def test_validate_accepts_deepseek_v4_primary_model_for_channel(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "deepseek"},
                {"key": "LLM_DEEPSEEK_PROTOCOL", "value": "deepseek"},
                {"key": "LLM_DEEPSEEK_BASE_URL", "value": "https://api.deepseek.com"},
                {"key": "LLM_DEEPSEEK_API_KEY", "value": "sk-test-value"},
                {"key": "LLM_DEEPSEEK_MODELS", "value": "deepseek-v4-flash,deepseek-v4-pro"},
                {"key": "LITELLM_MODEL", "value": "deepseek/deepseek-v4-flash"},
            ]
        )

        self.assertTrue(validation["valid"], validation["issues"])
        self.assertEqual(validation["issues"], [])

    def test_validate_reports_unknown_agent_primary_model_for_channels(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "primary"},
                {"key": "LLM_PRIMARY_PROTOCOL", "value": "openai"},
                {"key": "LLM_PRIMARY_API_KEY", "value": "sk-test-value"},
                {"key": "LLM_PRIMARY_MODELS", "value": "gpt-4o-mini"},
                {"key": "AGENT_LITELLM_MODEL", "value": "openai/gpt-4o"},
            ]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(any(issue["key"] == "AGENT_LITELLM_MODEL" and issue["code"] == "unknown_model" for issue in validation["issues"]))

    def test_validate_accepts_unprefixed_agent_model_when_channel_declares_openai_model(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "primary"},
                {"key": "LLM_PRIMARY_PROTOCOL", "value": "openai"},
                {"key": "LLM_PRIMARY_API_KEY", "value": "sk-test-value"},
                {"key": "LLM_PRIMARY_MODELS", "value": "gpt-4o-mini"},
                {"key": "AGENT_LITELLM_MODEL", "value": "gpt-4o-mini"},
            ]
        )

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["issues"], [])

    @patch.object(
        Config,
        "parse_litellm_yaml",
        return_value=[{"model_name": "gemini/gemini-2.5-flash", "litellm_params": {"model": "gemini/gemini-2.5-flash"}}],
    )
    def test_validate_skips_channel_checks_when_litellm_yaml_is_active(self, _mock_parse_yaml) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LITELLM_CONFIG", "value": "/tmp/litellm.yaml"},
                {"key": "LLM_CHANNELS", "value": "primary"},
                {"key": "LLM_PRIMARY_PROTOCOL", "value": "openai"},
                {"key": "LLM_PRIMARY_MODELS", "value": "gpt-4o-mini"},
                {"key": "LLM_PRIMARY_API_KEY", "value": ""},
                {"key": "LITELLM_MODEL", "value": "gemini/gemini-2.5-flash"},
            ]
        )
        self.assertTrue(validation["valid"])
        self.assertEqual(validation["issues"], [])

    @patch.object(
        Config,
        "parse_litellm_yaml",
        return_value=[{"model_name": "gemini/gemini-2.5-flash", "litellm_params": {"model": "gemini/gemini-2.5-flash"}}],
    )
    def test_validate_reports_unknown_primary_model_for_litellm_yaml(self, _mock_parse_yaml) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LITELLM_CONFIG", "value": "/tmp/litellm.yaml"},
                {"key": "LITELLM_MODEL", "value": "openai/gpt-4o-mini"},
            ]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(any(issue["key"] == "LITELLM_MODEL" and issue["code"] == "unknown_model" for issue in validation["issues"]))

    @patch.object(Config, "parse_litellm_yaml", return_value=[])
    def test_validate_keeps_channel_checks_when_litellm_yaml_has_no_models(self, _mock_parse_yaml) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LITELLM_CONFIG", "value": "/tmp/litellm.yaml"},
                {"key": "LLM_CHANNELS", "value": "primary"},
                {"key": "LLM_PRIMARY_PROTOCOL", "value": "openai"},
                {"key": "LLM_PRIMARY_MODELS", "value": "gpt-4o-mini"},
                {"key": "LLM_PRIMARY_API_KEY", "value": ""},
            ]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(any(issue["code"] == "missing_api_key" for issue in validation["issues"]))

    def test_validate_reports_stale_primary_model_when_all_channels_disabled(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "primary"},
                {"key": "LLM_PRIMARY_PROTOCOL", "value": "openai"},
                {"key": "LLM_PRIMARY_API_KEY", "value": "sk-test-value"},
                {"key": "LLM_PRIMARY_MODELS", "value": "gpt-4o-mini"},
                {"key": "LLM_PRIMARY_ENABLED", "value": "false"},
                {"key": "LITELLM_MODEL", "value": "openai/gpt-4o-mini"},
            ]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(any(issue["key"] == "LITELLM_MODEL" and issue["code"] == "missing_runtime_source" for issue in validation["issues"]))

    def test_validate_reports_stale_agent_primary_model_when_all_channels_disabled(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "primary"},
                {"key": "LLM_PRIMARY_PROTOCOL", "value": "openai"},
                {"key": "LLM_PRIMARY_API_KEY", "value": "sk-test-value"},
                {"key": "LLM_PRIMARY_MODELS", "value": "gpt-4o-mini"},
                {"key": "LLM_PRIMARY_ENABLED", "value": "false"},
                {"key": "AGENT_LITELLM_MODEL", "value": "openai/gpt-4o-mini"},
            ]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(any(issue["key"] == "AGENT_LITELLM_MODEL" and issue["code"] == "missing_runtime_source" for issue in validation["issues"]))

    def test_validate_allows_primary_model_when_all_channels_disabled_but_legacy_key_exists(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "primary"},
                {"key": "LLM_PRIMARY_PROTOCOL", "value": "openai"},
                {"key": "LLM_PRIMARY_API_KEY", "value": "sk-test-value"},
                {"key": "LLM_PRIMARY_MODELS", "value": "gpt-4o-mini"},
                {"key": "LLM_PRIMARY_ENABLED", "value": "false"},
                {"key": "OPENAI_API_KEY", "value": "sk-legacy-value"},
                {"key": "LITELLM_MODEL", "value": "openai/gpt-4o-mini"},
            ]
        )

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["issues"], [])

    def test_validate_allows_anspire_channel_with_shared_key_defaults(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "anspire"},
                {"key": "ANSPIRE_API_KEYS", "value": "sk-anspire-test-value"},
            ]
        )

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["issues"], [])

    def test_validate_treats_blank_anspire_channel_enabled_as_shared_disable(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "anspire"},
                {"key": "LLM_ANSPIRE_ENABLED", "value": "   "},
                {"key": "ANSPIRE_LLM_ENABLED", "value": "false"},
            ]
        )

        self.assertTrue(validation["valid"], validation["issues"])
        self.assertEqual(validation["issues"], [])

    def test_validate_excludes_blank_disabled_anspire_channel_from_runtime_models(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "anspire"},
                {"key": "LLM_ANSPIRE_ENABLED", "value": "   "},
                {"key": "ANSPIRE_LLM_ENABLED", "value": "false"},
                {"key": "ANSPIRE_API_KEYS", "value": "sk-anspire-test-value"},
                {"key": "LITELLM_MODEL", "value": f"openai/{ANSPIRE_LLM_MODEL_DEFAULT}"},
            ]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(any(issue["key"] == "LITELLM_MODEL" and issue["code"] == "missing_runtime_source" for issue in validation["issues"]))

    def test_validate_excludes_disabled_anspire_channel_from_legacy_runtime_source(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "LLM_CHANNELS", "value": "anspire"},
                {"key": "LLM_ANSPIRE_ENABLED", "value": "false"},
                {"key": "ANSPIRE_API_KEYS", "value": "sk-anspire-test-value"},
                {"key": "LITELLM_MODEL", "value": f"openai/{ANSPIRE_LLM_MODEL_DEFAULT}"},
            ]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(any(issue["key"] == "LITELLM_MODEL" and issue["code"] == "missing_runtime_source" for issue in validation["issues"]))

    @patch("src.infrastructure.notification.senders.wechat_sender.requests.post")
    def test_test_notification_channel_uses_temporary_items_without_persisting(self, mock_post) -> None:
        mock_post.return_value = self._mock_http_response(200, {"errcode": 0})

        with self._notification_test_env():
            before_instance = Config.get_instance()
            payload = self.service.test_notification_channel(
                channel="wechat",
                items=[{"key": "WECHAT_WEBHOOK_URL", "value": "https://qyapi.example.com/cgi-bin/webhook/send?key=secret"}],
                title="Test title",
                content="hello",
                timeout_seconds=3,
            )
            self.assertIs(Config.get_instance(), before_instance)

        self.assertTrue(payload["success"])
        self.assertEqual(payload["attempts"][0]["latency_ms"] >= 0, True)
        self.assertIn("key=***", payload["attempts"][0]["target"])
        self.assertNotIn("WECHAT_WEBHOOK_URL", self.env_path.read_text(encoding="utf-8"))
        self.assertEqual(mock_post.call_args.kwargs["timeout"], 3)

    def test_test_notification_channel_reports_missing_config(self) -> None:
        with self._notification_test_env():
            payload = self.service.test_notification_channel(
                channel="telegram",
                items=[{"key": "TELEGRAM_BOT_TOKEN", "value": "token"}],
                title="Test title",
                content="hello",
                timeout_seconds=3,
            )

        self.assertFalse(payload["success"])
        self.assertEqual(payload["error_code"], "config_missing")
        self.assertIn("TELEGRAM_CHAT_ID", payload["message"])

    def test_test_notification_channel_reports_nearest_feishu_app_bot_missing_key(self) -> None:
        with self._notification_test_env():
            payload = self.service.test_notification_channel(
                channel="feishu",
                items=[
                    {"key": "FEISHU_APP_ID", "value": "cli_xxx"},
                    {"key": "FEISHU_APP_SECRET", "value": "secret_xxx"},
                ],
                title="Test title",
                content="hello",
                timeout_seconds=3,
            )

        self.assertFalse(payload["success"])
        self.assertEqual(payload["error_code"], "config_missing")
        self.assertIn("FEISHU_CHAT_ID", payload["message"])
        self.assertNotIn("FEISHU_WEBHOOK_URL", payload["message"])

    def test_test_notification_channel_feishu_domain_draft_builds_isolated_config(self) -> None:
        captured: Dict[str, Any] = {}

        def fake_dispatch(**kwargs):
            captured.update(kwargs)
            return {
                "success": True,
                "message": "ok",
                "error_code": None,
                "stage": "notification_send",
                "retryable": False,
                "latency_ms": 0,
                "attempts": [],
            }

        with self._notification_test_env(), patch.object(
            NotificationChannelTester,
            "_dispatch_notification_test",
            side_effect=fake_dispatch,
        ):
            payload = self.service.test_notification_channel(
                channel="feishu",
                items=[
                    {"key": "FEISHU_APP_ID", "value": "cli_xxx"},
                    {"key": "FEISHU_APP_SECRET", "value": "secret_xxx"},
                    {"key": "FEISHU_CHAT_ID", "value": "oc_xxx"},
                    {"key": "FEISHU_DOMAIN", "value": "lark"},
                ],
                title="Test title",
                content="hello",
                timeout_seconds=3,
            )

        self.assertTrue(payload["success"])
        self.assertEqual(captured["config"].feishu_domain, "lark")

    @patch("src.infrastructure.notification.senders.custom_webhook_sender.requests.post")
    def test_test_notification_channel_returns_custom_webhook_attempts(self, mock_post) -> None:
        mock_post.side_effect = [
            self._mock_http_response(500),
            self._mock_http_response(200),
        ]

        with self._notification_test_env():
            payload = self.service.test_notification_channel(
                channel="custom",
                items=[
                    {
                        "key": "CUSTOM_WEBHOOK_URLS",
                        "value": (
                            "https://example.com/robot/send?access_token=first,"
                            "https://example.com/verylongsecrettoken1234567890"
                        ),
                    }
                ],
                title="Test title",
                content="hello",
                timeout_seconds=4,
            )

        self.assertTrue(payload["success"])
        self.assertIn("部分成功", payload["message"])
        self.assertIn("1/2", payload["message"])
        self.assertEqual(len(payload["attempts"]), 2)
        self.assertFalse(payload["attempts"][0]["success"])
        self.assertTrue(payload["attempts"][1]["success"])
        self.assertIn("access_token=***", payload["attempts"][0]["target"])
        self.assertNotIn("verylongsecrettoken1234567890", payload["attempts"][1]["target"])
        self.assertNotIn("access_token=first", str(payload))
        self.assertEqual(mock_post.call_args_list[0].kwargs["timeout"], 4)

    @patch("src.infrastructure.notification.senders.custom_webhook_sender.requests.post")
    def test_test_notification_channel_custom_webhook_all_failures_are_retryable(self, mock_post) -> None:
        mock_post.side_effect = [
            self._mock_http_response(500),
            self._mock_http_response(429),
        ]

        with self._notification_test_env():
            payload = self.service.test_notification_channel(
                channel="custom",
                items=[
                    {
                        "key": "CUSTOM_WEBHOOK_URLS",
                        "value": (
                            "https://example.com/robot/send?access_token=first,"
                            "https://example.com/robot/send?token=second"
                        ),
                    }
                ],
                title="Test title",
                content="hello",
                timeout_seconds=4,
            )

        self.assertFalse(payload["success"])
        self.assertEqual(payload["error_code"], "send_failed")
        self.assertTrue(payload["retryable"])
        self.assertIn("失败", payload["message"])
        self.assertIn("0/2", payload["message"])
        self.assertEqual(len(payload["attempts"]), 2)
        self.assertTrue(all(attempt["retryable"] for attempt in payload["attempts"]))
        self.assertNotIn("access_token=first", str(payload))
        self.assertNotIn("token=second", str(payload))

    @patch("src.infrastructure.notification.senders.ntfy_sender.requests.post")
    def test_test_notification_channel_rejects_ntfy_url_without_topic(self, mock_post) -> None:
        with self._notification_test_env():
            payload = self.service.test_notification_channel(
                channel="ntfy",
                items=[{"key": "NTFY_URL", "value": "https://ntfy.sh"}],
                title="Test title",
                content="hello",
                timeout_seconds=4,
            )

        self.assertFalse(payload["success"])
        self.assertEqual(payload["error_code"], "config_invalid")
        self.assertEqual(payload["stage"], "config_validation")
        self.assertIn("NTFY_URL", payload["message"])
        mock_post.assert_not_called()

    @patch("src.infrastructure.notification.senders.gotify_sender.requests.post")
    def test_test_notification_channel_supports_gotify_and_keeps_token_out_of_url(self, mock_post) -> None:
        mock_post.return_value = self._mock_http_response(200)

        with self._notification_test_env():
            payload = self.service.test_notification_channel(
                channel="gotify",
                items=[
                    {"key": "GOTIFY_URL", "value": "https://gotify.example"},
                    {"key": "GOTIFY_TOKEN", "value": "secret-token"},
                ],
                title="Test title",
                content="hello",
                timeout_seconds=4,
            )

        self.assertTrue(payload["success"])
        self.assertEqual(mock_post.call_args.args[0], "https://gotify.example/message")
        self.assertEqual(mock_post.call_args.kwargs["headers"]["X-Gotify-Key"], "secret-token")
        self.assertEqual(mock_post.call_args.kwargs["timeout"], 4)
        self.assertEqual(payload["attempts"][0]["target"], "https://gotify.example")
        self.assertNotIn("secret-token", str(payload))
        self.assertNotIn("GOTIFY_URL", self.env_path.read_text(encoding="utf-8"))

    @patch("src.infrastructure.notification.senders.gotify_sender.requests.post")
    def test_test_notification_channel_rejects_gotify_message_endpoint(self, mock_post) -> None:
        with self._notification_test_env():
            payload = self.service.test_notification_channel(
                channel="gotify",
                items=[
                    {"key": "GOTIFY_URL", "value": "https://gotify.example/message"},
                    {"key": "GOTIFY_TOKEN", "value": "secret-token"},
                ],
                title="Test title",
                content="hello",
                timeout_seconds=4,
            )

        self.assertFalse(payload["success"])
        self.assertEqual(payload["error_code"], "config_invalid")
        self.assertEqual(payload["stage"], "config_validation")
        self.assertIn("GOTIFY_URL", payload["message"])
        mock_post.assert_not_called()

    @patch(
        "src.infrastructure.notification.senders.WechatSender.send_to_wechat",
        side_effect=requests.exceptions.Timeout(
            "timeout for https://qyapi.example.com/cgi-bin/webhook/send?key=secret token=abc123"
        ),
    )
    def test_test_notification_channel_classifies_escaped_timeout(self, _mock_send) -> None:
        with self._notification_test_env():
            payload = self.service.test_notification_channel(
                channel="wechat",
                items=[
                    {
                        "key": "WECHAT_WEBHOOK_URL",
                        "value": "https://qyapi.example.com/cgi-bin/webhook/send?key=secret",
                    }
                ],
                title="Test title",
                content="hello",
                timeout_seconds=3,
            )

        self.assertFalse(payload["success"])
        self.assertEqual(payload["error_code"], "timeout")
        self.assertTrue(payload["retryable"])
        self.assertEqual(payload["attempts"][0]["error_code"], "timeout")
        self.assertIn("key=***", payload["attempts"][0]["target"])
        self.assertNotIn("key=secret", str(payload))
        self.assertNotIn("abc123", str(payload))

    @patch("src.infrastructure.notification.senders.wechat_sender.requests.post")
    def test_test_notification_channel_strips_url_userinfo_from_target(self, mock_post) -> None:
        mock_post.return_value = self._mock_http_response(200, {"errcode": 0})

        with self._notification_test_env():
            payload = self.service.test_notification_channel(
                channel="wechat",
                items=[
                    {
                        "key": "WECHAT_WEBHOOK_URL",
                        "value": "https://user:password@example.com/cgi-bin/webhook/send?key=secret",
                    }
                ],
                title="Test title",
                content="hello",
                timeout_seconds=3,
            )

        self.assertTrue(payload["success"])
        target = payload["attempts"][0]["target"]
        self.assertIn("https://example.com/cgi-bin/webhook/send?key=***", target)
        self.assertNotIn("user", target)
        self.assertNotIn("password", target)

    @patch("src.infrastructure.notification.senders.discord_sender.requests.post")
    def test_test_notification_channel_prefers_discord_main_channel_alias(self, mock_post) -> None:
        mock_post.return_value = self._mock_http_response(200)

        with self._notification_test_env():
            payload = self.service.test_notification_channel(
                channel="discord",
                items=[
                    {"key": "DISCORD_BOT_TOKEN", "value": "bot-token"},
                    {"key": "DISCORD_MAIN_CHANNEL_ID", "value": "main-channel"},
                    {"key": "DISCORD_CHANNEL_ID", "value": "legacy-channel"},
                ],
                title="Test title",
                content="hello",
                timeout_seconds=3,
            )

        self.assertTrue(payload["success"])
        self.assertIn("/channels/main-channel/messages", mock_post.call_args[0][0])

    @patch("litellm.completion")
    def test_test_llm_channel_returns_success_payload(self, mock_completion) -> None:
        mock_completion.return_value = type(
            "MockResponse",
            (),
            {
                "choices": [type("Choice", (), {"message": type("Message", (), {"content": "OK"})()})()],
            },
        )()

        payload = self.service.test_llm_channel(
            name="primary",
            protocol="openai",
            base_url="https://api.deepseek.com/v1",
            api_key="sk-test-value",
            models=["deepseek-chat"],
        )

        self.assertTrue(payload["success"])
        self.assertEqual(payload["resolved_protocol"], "openai")
        self.assertEqual(payload["resolved_model"], "openai/deepseek-chat")
        self.assertEqual(payload["capability_results"], {})
        self.assertEqual(mock_completion.call_count, 1)

    @patch("litellm.completion")
    def test_test_llm_channel_falls_back_to_message_content_when_content_blocks_empty(
        self,
        mock_completion,
    ) -> None:
        mock_completion.return_value = type(
            "MockResponse",
            (),
            {
                "choices": [
                    type(
                        "Choice",
                        (),
                        {
                            "content_blocks": [],
                            "message": type("Message", (), {"content": "OK"})(),
                        },
                    )(),
                ]
            },
        )()

        payload = self.service.test_llm_channel(
            name="primary",
            protocol="openai",
            base_url="https://api.deepseek.com/v1",
            api_key="sk-test-value",
            models=["deepseek-chat"],
        )

        self.assertTrue(payload["success"])
        self.assertEqual(payload["resolved_model"], "openai/deepseek-chat")

    @patch("litellm.completion")
    def test_test_llm_channel_allows_ollama_prefix_without_explicit_protocol(self, mock_completion) -> None:
        mock_completion.return_value = type(
            "MockResponse",
            (),
            {
                "choices": [type("Choice", (), {"message": type("Message", (), {"content": "OK"})()})()],
            },
        )()

        payload = self.service.test_llm_channel(
            name="lab",
            protocol="",
            base_url="http://localhost:11434/v1",
            api_key="",
            models=["ollama/llama3"],
        )

        self.assertTrue(payload["success"])
        self.assertEqual(payload["resolved_protocol"], "ollama")
        self.assertEqual(payload["resolved_model"], "ollama/llama3")

    @patch("litellm.completion")
    def test_test_llm_channel_normalizes_kimi_temperature(self, mock_completion) -> None:
        mock_completion.return_value = type(
            "MockResponse",
            (),
            {
                "choices": [type("Choice", (), {"message": type("Message", (), {"content": "OK"})()})()],
            },
        )()

        payload = self.service.test_llm_channel(
            name="primary",
            protocol="openai",
            base_url="https://api.moonshot.cn/v1",
            api_key="sk-test-value",
            models=["kimi-k2.6"],
        )

        self.assertTrue(payload["success"])
        self.assertEqual(payload["resolved_model"], "openai/kimi-k2.6")
        self.assertEqual(mock_completion.call_args.kwargs["temperature"], 1.0)

    def test_update_switching_to_kimi_does_not_rewrite_saved_llm_temperature(self) -> None:
        self._rewrite_env(
            "LITELLM_MODEL=openai/gpt-4o-mini",
            "LLM_TEMPERATURE=0.42",
        )

        response = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[{"key": "LITELLM_MODEL", "value": "openai/kimi-k2.6"}],
            reload_now=False,
        )

        self.assertTrue(response["success"])
        current_map = self.manager.read_config_map()
        self.assertEqual(current_map["LITELLM_MODEL"], "openai/kimi-k2.6")
        self.assertEqual(current_map["LLM_TEMPERATURE"], "0.42")

    @patch("litellm.completion")
    def test_test_llm_channel_does_not_persist_normalized_kimi_temperature(self, mock_completion) -> None:
        self._rewrite_env("LLM_TEMPERATURE=0.42")
        mock_completion.return_value = type(
            "MockResponse",
            (),
            {
                "choices": [type("Choice", (), {"message": type("Message", (), {"content": "OK"})()})()],
            },
        )()

        payload = self.service.test_llm_channel(
            name="primary",
            protocol="openai",
            base_url="https://api.moonshot.cn/v1",
            api_key="sk-test-value",
            models=["kimi-k2.6"],
        )

        self.assertTrue(payload["success"])
        self.assertEqual(mock_completion.call_args.kwargs["temperature"], 1.0)
        self.assertEqual(self.manager.read_config_map()["LLM_TEMPERATURE"], "0.42")

    @patch("litellm.completion")
    def test_test_llm_channel_omits_temperature_for_gpt5_family(self, mock_completion) -> None:
        mock_completion.return_value = type(
            "MockResponse",
            (),
            {
                "choices": [type("Choice", (), {"message": type("Message", (), {"content": "OK"})()})()],
            },
        )()

        payload = self.service.test_llm_channel(
            name="primary",
            protocol="openai",
            base_url="https://api.example.com/v1",
            api_key="sk-test-value",
            models=["gpt5.5-ferr"],
        )

        self.assertTrue(payload["success"])
        self.assertEqual(payload["resolved_model"], "openai/gpt5.5-ferr")
        self.assertNotIn("temperature", mock_completion.call_args.kwargs)

    @patch("litellm.completion")
    @patch("src.application.runtime.system_config_service.Config._load_from_env")
    def test_test_llm_channel_recovers_from_unsupported_temperature(
        self,
        mock_load_config,
        mock_completion,
    ) -> None:
        from src.infrastructure.generation.generation_params import clear_litellm_generation_param_recovery_cache

        clear_litellm_generation_param_recovery_cache()
        mock_load_config.return_value = SimpleNamespace(llm_temperature=0.42)
        mock_completion.side_effect = [
            RuntimeError("Unsupported parameter: temperature is not supported"),
            type(
                "MockResponse",
                (),
                {
                    "choices": [type("Choice", (), {"message": type("Message", (), {"content": "OK"})()})()],
                },
            )(),
        ]

        payload = self.service.test_llm_channel(
            name="primary",
            protocol="openai",
            base_url="https://api.example.com/v1",
            api_key="sk-test-value",
            models=["custom-temp-locked-settings"],
        )

        self.assertTrue(payload["success"])
        self.assertEqual(mock_completion.call_args_list[0].kwargs["temperature"], 0.42)
        self.assertNotIn("temperature", mock_completion.call_args_list[1].kwargs)

    @patch("litellm.completion")
    @patch("src.application.runtime.system_config_service.Config._load_from_env")
    def test_test_llm_channel_uses_runtime_temperature_for_non_kimi_models(
        self,
        mock_load_config,
        mock_completion,
    ) -> None:
        mock_load_config.return_value = SimpleNamespace(llm_temperature=0.42)
        mock_completion.return_value = type(
            "MockResponse",
            (),
            {
                "choices": [type("Choice", (), {"message": type("Message", (), {"content": "OK"})()})()],
            },
        )()

        payload = self.service.test_llm_channel(
            name="primary",
            protocol="openai",
            base_url="https://api.example.com/v1",
            api_key="sk-test-value",
            models=["gpt-4o-mini"],
        )

        self.assertTrue(payload["success"])
        self.assertEqual(payload["resolved_model"], "openai/gpt-4o-mini")
        self.assertEqual(mock_completion.call_args.kwargs["temperature"], 0.42)

    @patch("litellm.completion")
    def test_test_llm_channel_classifies_common_failure_scenarios(self, mock_completion) -> None:
        cases = [
            (PermissionError("401 Unauthorized Bearer sk-secret-value"), "auth", "chat_completion", False),
            (TimeoutError("request timed out"), "timeout", "chat_completion", True),
            (Exception("404 model not found: gpt-4o-mini"), "model_not_found", "chat_completion", False),
            (Exception("The model `gpt-4o-mini` does not exist"), "model_not_found", "chat_completion", False),
            (Exception("404 Not Found: page not found"), "network_error", "chat_completion", False),
            (
                type("MockResponse", (), {"choices": [type("Choice", (), {"message": type("Message", (), {"content": ""})()})()]})(),
                "empty_response",
                "response_parse",
                False,
            ),
            (object(), "format_error", "response_parse", False),
        ]

        for response_or_exc, error_code, stage, retryable in cases:
            with self.subTest(error_code=error_code):
                mock_completion.reset_mock()
                if isinstance(response_or_exc, Exception):
                    mock_completion.side_effect = response_or_exc
                    mock_completion.return_value = None
                else:
                    mock_completion.side_effect = None
                    mock_completion.return_value = response_or_exc

                payload = self.service.test_llm_channel(
                    name="primary",
                    protocol="openai",
                    base_url="https://api.example.com/v1",
                    api_key="sk-secret-value",
                    models=["gpt-4o-mini"],
                )

                self.assertFalse(payload["success"])
                self.assertEqual(payload["error_code"], error_code)
                self.assertEqual(payload["stage"], stage)
                self.assertEqual(payload["retryable"], retryable)
                if error_code == "auth":
                    self.assertNotIn("sk-secret-value", payload["error"])
                if error_code == "format_error":
                    self.assertIn("choices", payload["error"])

    @patch("litellm.completion")
    def test_test_llm_channel_marks_requested_capabilities_skipped_when_base_fails(self, mock_completion) -> None:
        mock_completion.side_effect = PermissionError("401 Unauthorized Bearer sk-secret-value")

        payload = self.service.test_llm_channel(
            name="primary",
            protocol="openai",
            base_url="https://api.example.com/v1",
            api_key="sk-secret-value",
            models=["gpt-4o-mini"],
            capability_checks=["json", "tools"],
        )

        self.assertFalse(payload["success"])
        self.assertEqual(payload["error_code"], "auth")
        self.assertEqual(payload["details"]["reason"], "api_key_rejected")
        self.assertEqual(payload["capability_results"]["json"]["status"], "skipped")
        self.assertEqual(payload["capability_results"]["tools"]["details"]["reason"], "base_test_failed")
        self.assertEqual(mock_completion.call_count, 1)

    @patch("litellm.completion")
    def test_test_llm_channel_runs_json_and_tools_capability_checks(self, mock_completion) -> None:
        tool_call = SimpleNamespace(function=SimpleNamespace(name="hrs_probe_echo"))
        mock_completion.side_effect = [
            self._mock_completion_response("OK"),
            self._mock_completion_response('{"status":"ok"}'),
            self._mock_completion_response("", tool_calls=[tool_call]),
        ]

        payload = self.service.test_llm_channel(
            name="primary",
            protocol="openai",
            base_url="https://api.example.com/v1",
            api_key="sk-test-value",
            models=["gpt-4o-mini"],
            capability_checks=["tools", "json", "tools"],
        )

        self.assertTrue(payload["success"])
        self.assertEqual(list(payload["capability_results"].keys()), ["json", "tools"])
        self.assertEqual(payload["capability_results"]["json"]["status"], "passed")
        self.assertEqual(payload["capability_results"]["tools"]["status"], "passed")
        self.assertEqual(mock_completion.call_count, 3)
        self.assertEqual(mock_completion.call_args_list[1].kwargs["response_format"], {"type": "json_object"})
        self.assertEqual(mock_completion.call_args_list[2].kwargs["tool_choice"]["function"]["name"], "hrs_probe_echo")

    @patch("litellm.completion")
    def test_test_llm_channel_json_capability_ignores_minimax_reasoning_blocks(self, mock_completion) -> None:
        mock_completion.side_effect = [
            self._mock_completion_response("OK"),
            {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "content_blocks": [
                                {"type": "reasoning", "content": "Internal reasoning"},
                                {"type": "text", "text": '{"status":"ok"}'},
                            ],
                        }
                    }
                ]
            },
        ]

        payload = self.service.test_llm_channel(
            name="minimax",
            protocol="openai",
            base_url="https://api.minimax.io/v1",
            api_key="sk-test-value",
            models=["MiniMax-M3"],
            capability_checks=["json"],
        )

        self.assertTrue(payload["success"])
        self.assertEqual(payload["capability_results"]["json"]["status"], "passed")

    @patch("litellm.completion")
    def test_test_llm_channel_json_capability_strips_minimax_think_wrapper(self, mock_completion) -> None:
        mock_completion.side_effect = [
            self._mock_completion_response("OK"),
            self._mock_completion_response('<think>Internal reasoning</think>{"status":"ok"}'),
        ]

        payload = self.service.test_llm_channel(
            name="minimax",
            protocol="openai",
            base_url="https://api.minimax.io/v1",
            api_key="sk-test-value",
            models=["MiniMax-M3"],
            capability_checks=["json"],
        )

        self.assertTrue(payload["success"])
        self.assertEqual(payload["capability_results"]["json"]["status"], "passed")

    @patch("litellm.completion")
    def test_test_llm_channel_reports_json_capability_failures(self, mock_completion) -> None:
        mock_completion.side_effect = [
            self._mock_completion_response("OK"),
            self._mock_completion_response("not json"),
        ]

        payload = self.service.test_llm_channel(
            name="primary",
            protocol="openai",
            base_url="https://api.example.com/v1",
            api_key="sk-test-value",
            models=["gpt-4o-mini"],
            capability_checks=["json"],
        )

        self.assertTrue(payload["success"])
        result = payload["capability_results"]["json"]
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_code"], "format_error")
        self.assertEqual(result["details"]["reason"], "non_json")

    @patch("litellm.completion")
    def test_test_llm_channel_runs_stream_capability_check_and_closes_stream(self, mock_completion) -> None:
        class _Stream:
            def __init__(self):
                self.closed = False

            def __iter__(self):
                yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="OK"))])

            def close(self):
                self.closed = True

        stream = _Stream()
        mock_completion.side_effect = [
            self._mock_completion_response("OK"),
            stream,
        ]

        payload = self.service.test_llm_channel(
            name="primary",
            protocol="openai",
            base_url="https://api.example.com/v1",
            api_key="sk-test-value",
            models=["gpt-4o-mini"],
            capability_checks=["stream"],
        )

        self.assertTrue(payload["success"])
        self.assertEqual(payload["capability_results"]["stream"]["status"], "passed")
        self.assertTrue(stream.closed)
        self.assertTrue(mock_completion.call_args_list[1].kwargs["stream"])

    @patch("litellm.completion")
    def test_test_llm_channel_ignores_stream_close_failures(self, mock_completion) -> None:
        class _Stream:
            def __init__(self):
                self.close_attempted = False

            def __iter__(self):
                yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="OK"))])

            def close(self):
                self.close_attempted = True
                raise RuntimeError("transport already closed")

        stream = _Stream()
        mock_completion.side_effect = [
            self._mock_completion_response("OK"),
            stream,
        ]

        payload = self.service.test_llm_channel(
            name="primary",
            protocol="openai",
            base_url="https://api.example.com/v1",
            api_key="sk-test-value",
            models=["gpt-4o-mini"],
            capability_checks=["stream"],
        )

        self.assertTrue(payload["success"])
        self.assertEqual(payload["capability_results"]["stream"]["status"], "passed")
        self.assertTrue(stream.close_attempted)

    @patch("litellm.completion")
    def test_test_llm_channel_runs_vision_capability_check(self, mock_completion) -> None:
        mock_completion.side_effect = [
            self._mock_completion_response("OK"),
            self._mock_completion_response("OK"),
        ]

        payload = self.service.test_llm_channel(
            name="primary",
            protocol="openai",
            base_url="https://api.example.com/v1",
            api_key="sk-test-value",
            models=["gpt-4o-mini"],
            capability_checks=["vision"],
        )

        self.assertTrue(payload["success"])
        self.assertEqual(payload["capability_results"]["vision"]["status"], "passed")
        vision_content = mock_completion.call_args_list[1].kwargs["messages"][0]["content"]
        self.assertEqual(vision_content[1]["type"], "image_url")
        self.assertTrue(vision_content[1]["image_url"]["url"].startswith("data:image/png;base64,"))

    @patch("litellm.completion")
    def test_test_llm_channel_classifies_capability_unsupported(self, mock_completion) -> None:
        mock_completion.side_effect = [
            self._mock_completion_response("OK"),
            Exception("response_format is not supported"),
        ]

        payload = self.service.test_llm_channel(
            name="primary",
            protocol="openai",
            base_url="https://api.example.com/v1",
            api_key="sk-test-value",
            models=["gpt-4o-mini"],
            capability_checks=["json"],
        )

        result = payload["capability_results"]["json"]
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_code"], "capability_unsupported")
        self.assertEqual(result["details"]["reason"], "capability_unsupported")

    @patch("litellm.completion")
    def test_test_llm_channel_adds_focused_diagnostic_reasons(self, mock_completion) -> None:
        class RateLimitError(Exception):
            pass

        cases = [
            (Exception("account balance insufficient"), "quota", "insufficient_balance"),
            (RateLimitError("account balance insufficient"), "quota", "insufficient_balance"),
            (RateLimitError("insufficient_quota"), "quota", "quota_exceeded"),
            (Exception("account balance insufficient; your request was blocked"), "quota", "insufficient_balance"),
            (RateLimitError("rate limit: your request was blocked by policy"), "quota", "rate_limit"),
            (Exception("DNS lookup failed"), "network_error", "dns_error"),
            (Exception("TLS certificate verify failed"), "network_error", "tls_error"),
            (Exception("Connection refused"), "network_error", "connection_refused"),
            (Exception("connection request was blocked by firewall"), "network_error", "network_error"),
            (Exception("connection blocked by policy"), "network_error", "network_error"),
            (Exception("request blocked by firewall"), "network_error", "network_error"),
            (Exception("blocked"), "network_error", "unknown_error"),
            (Exception("model gpt-4o is not authorized for this account"), "model_not_found", "model_access_denied"),
            (Exception("litellm.APIError: APIError: OpenAIException - Model disabled."), "model_not_found", "model_access_denied"),
            (Exception("Model is disabled for this account"), "model_not_found", "model_access_denied"),
            (
                Exception("litellm.APIError: APIError: OpenAIException - Your request was blocked."),
                "request_blocked",
                "provider_blocked",
            ),
            (Exception("Forbidden: your request was blocked by content policy"), "request_blocked", "provider_blocked"),
            (Exception("blocked by policy"), "request_blocked", "provider_blocked"),
            (Exception("moderation_blocked"), "request_blocked", "provider_blocked"),
            (Exception("LLM Provider NOT provided for model foo"), "model_not_found", "provider_prefix_mismatch"),
        ]

        for exc, error_code, reason in cases:
            with self.subTest(reason=reason):
                mock_completion.reset_mock()
                mock_completion.side_effect = exc
                payload = self.service.test_llm_channel(
                    name="primary",
                    protocol="openai",
                    base_url="https://api.example.com/v1",
                    api_key="sk-test-value",
                    models=["gpt-4o-mini"],
                )

                self.assertFalse(payload["success"])
                self.assertEqual(payload["error_code"], error_code)
                self.assertEqual(payload["details"]["reason"], reason)
                if reason in {"model_access_denied", "provider_blocked"}:
                    self.assertFalse(payload["retryable"])
                    self.assertEqual(payload["details"]["model"], "openai/gpt-4o-mini")
                    self.assertEqual(payload["resolved_model"], "openai/gpt-4o-mini")

    def test_test_llm_channel_reports_comma_only_api_key_as_missing(self) -> None:
        payload = self.service.test_llm_channel(
            name="primary",
            protocol="openai",
            base_url="https://api.example.com/v1",
            api_key=", ,",
            models=["gpt-4o-mini"],
        )

        self.assertFalse(payload["success"])
        self.assertEqual(payload["error_code"], "invalid_config")
        self.assertEqual(payload["details"]["reason"], "missing_api_key")

    @patch("src.application.runtime.system_config_service.requests.get")
    def test_discover_llm_channel_models_returns_deduped_ids(self, mock_get) -> None:
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "qwen-plus"},
                {"id": "qwen-plus"},
                {"id": "qwen-turbo"},
            ]
        }
        mock_get.return_value = mock_response

        payload = self.service.discover_llm_channel_models(
            name="dashscope",
            protocol="openai",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key="sk-test-value",
        )

        self.assertTrue(payload["success"])
        self.assertEqual(payload["resolved_protocol"], "openai")
        self.assertEqual(payload["models"], ["qwen-plus", "qwen-turbo"])
        mock_get.assert_called_once()
        self.assertEqual(
            mock_get.call_args.args[0],
            "https://dashscope.aliyuncs.com/compatible-mode/v1/models",
        )
        self.assertEqual(
            mock_get.call_args.kwargs["headers"]["Authorization"],
            "Bearer sk-test-value",
        )
        self.assertFalse(mock_get.call_args.kwargs["allow_redirects"])

    @patch("src.application.runtime.system_config_service.requests.get")
    def test_discover_llm_channel_models_classifies_error_scenarios(self, mock_get) -> None:
        auth_response = Mock(ok=False, status_code=401, text="invalid api key sk-secret-value")
        auth_response.json.return_value = {"error": {"message": "invalid api key sk-secret-value"}}
        not_found_response = Mock(ok=False, status_code=404, text="not found")
        not_found_response.json.return_value = {"error": {"message": "not found"}}
        billing_response = Mock(ok=False, status_code=402, text="account balance insufficient")
        billing_response.json.return_value = {"error": {"message": "account balance insufficient"}}
        billing_rate_limit_response = Mock(ok=False, status_code=429, text="account balance insufficient")
        billing_rate_limit_response.json.return_value = {"error": {"message": "account balance insufficient"}}
        quota_exceeded_response = Mock(ok=False, status_code=429, text="insufficient_quota")
        quota_exceeded_response.json.return_value = {"error": {"message": "insufficient_quota"}}
        quota_blocked_response = Mock(ok=False, status_code=403, text="account balance insufficient; your request was blocked")
        quota_blocked_response.json.return_value = {"error": {"message": "account balance insufficient; your request was blocked"}}
        rate_limit_response = Mock(ok=False, status_code=429, text="too many requests")
        rate_limit_response.json.return_value = {"error": {"message": "too many requests"}}
        blocked_response = Mock(ok=False, status_code=403, text="Forbidden: your request was blocked by content policy")
        blocked_response.json.return_value = {"error": {"message": "Forbidden: your request was blocked by content policy"}}
        connection_blocked_response = Mock(ok=False, status_code=403, text="connection blocked by policy")
        connection_blocked_response.json.return_value = {"error": {"message": "connection blocked by policy"}}
        invalid_json_response = Mock(ok=True, status_code=200, text="<html>bad gateway</html>")
        invalid_json_response.json.side_effect = ValueError("invalid json")

        for response, error_code, stage, retryable, reason in [
            (auth_response, "auth", "model_discovery", False, "api_key_rejected"),
            (not_found_response, "network_error", "model_discovery", False, "endpoint_not_found"),
            (billing_response, "quota", "model_discovery", True, "insufficient_balance"),
            (billing_rate_limit_response, "quota", "model_discovery", True, "insufficient_balance"),
            (quota_exceeded_response, "quota", "model_discovery", True, "quota_exceeded"),
            (quota_blocked_response, "quota", "model_discovery", True, "insufficient_balance"),
            (rate_limit_response, "quota", "model_discovery", True, "rate_limit"),
            (blocked_response, "request_blocked", "model_discovery", False, "provider_blocked"),
            (connection_blocked_response, "network_error", "model_discovery", True, "network_error"),
            (invalid_json_response, "format_error", "response_parse", False, "non_json"),
        ]:
            with self.subTest(error_code=error_code):
                mock_get.return_value = response
                payload = self.service.discover_llm_channel_models(
                    name="dashscope",
                    protocol="openai",
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                    api_key="sk-secret-value",
                )

                self.assertFalse(payload["success"])
                self.assertEqual(payload["error_code"], error_code)
                self.assertEqual(payload["stage"], stage)
                self.assertEqual(payload["retryable"], retryable)
                self.assertEqual(payload["details"]["reason"], reason)
                if error_code == "auth":
                    self.assertNotIn("sk-secret-value", payload["error"])

    @patch("src.application.runtime.system_config_service.requests.get")
    def test_discover_llm_channel_models_rejects_redirect_responses(self, mock_get) -> None:
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 302
        mock_get.return_value = mock_response

        payload = self.service.discover_llm_channel_models(
            name="dashscope",
            protocol="openai",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key="sk-test-value",
        )

        self.assertFalse(payload["success"])
        self.assertEqual(payload["message"], "Model discovery request was redirected")
        self.assertIn("Redirect responses are not allowed", payload["error"])
        self.assertFalse(mock_get.call_args.kwargs["allow_redirects"])

    def test_discover_llm_channel_models_requires_base_url(self) -> None:
        payload = self.service.discover_llm_channel_models(
            name="primary",
            protocol="openai",
            base_url="",
            api_key="sk-test-value",
        )

        self.assertFalse(payload["success"])
        self.assertIn("base URL", payload["error"])
        self.assertEqual(payload["models"], [])

    def test_discover_llm_channel_models_rejects_unsupported_protocol(self) -> None:
        payload = self.service.discover_llm_channel_models(
            name="gemini",
            protocol="gemini",
            base_url="https://example.com/v1",
            api_key="sk-test-value",
        )

        self.assertFalse(payload["success"])
        self.assertEqual(payload["resolved_protocol"], "gemini")
        self.assertIn("does not support /models discovery yet", payload["error"])

    def test_build_llm_models_url_strips_query_and_fragment(self) -> None:
        models_url = _build_llm_models_url(
            "https://example.com/v1/chat/completions?api-version=1#frag"
        )

        self.assertEqual(models_url, "https://example.com/v1/models")

    def test_build_llm_models_url_supports_deepseek_root_base_url(self) -> None:
        models_url = _build_llm_models_url("https://api.deepseek.com")

        self.assertEqual(models_url, "https://api.deepseek.com/models")
