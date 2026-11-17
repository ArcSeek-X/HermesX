"""Tests for system config save."""

from tests.application.runtime._system_config_service_support import (
    Config,
    ConfigConflictError,
    Path,
    SystemConfigService,
    _SystemConfigServiceTestCaseFixture,
    os,
    patch,
    unittest,
)


class SystemConfigServiceTestCase(_SystemConfigServiceTestCaseFixture, unittest.TestCase):
    def test_update_persists_public_searxng_toggle(self) -> None:
        old_version = self.manager.get_config_version()
        response = self.service.update(
            config_version=old_version,
            items=[{"key": "SEARXNG_PUBLIC_INSTANCES_ENABLED", "value": "false"}],
            reload_now=False,
        )

        self.assertTrue(response["success"])
        current_map = self.manager.read_config_map()
        self.assertEqual(current_map["SEARXNG_PUBLIC_INSTANCES_ENABLED"], "false")

    def test_update_minifies_multiline_json_before_storage(self) -> None:
        response = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[{
                "key": "AGENT_EVENT_ALERT_RULES_JSON",
                "value": (
                    "[\n"
                    '  {"stock_code":"600519","alert_type":"price_cross","direction":"above","price":1800}\n'
                    "]"
                ),
            }],
            reload_now=False,
        )

        self.assertTrue(response["success"])
        current_map = self.manager.read_config_map()
        self.assertEqual(
            current_map["AGENT_EVENT_ALERT_RULES_JSON"],
            '[{"stock_code":"600519","alert_type":"price_cross","direction":"above","price":1800}]',
        )

    def test_update_runtime_model_cleanup_does_not_rewrite_temperature(self) -> None:
        self._rewrite_env(
            "STOCK_LIST=600519,000001",
            "LLM_CHANNELS=deepseek",
            "LLM_DEEPSEEK_PROTOCOL=deepseek",
            "LLM_DEEPSEEK_BASE_URL=https://api.deepseek.com",
            "LLM_DEEPSEEK_API_KEY=sk-test-value",
            "LLM_DEEPSEEK_MODELS=deepseek-chat,deepseek-v4-flash",
            "LITELLM_MODEL=deepseek/deepseek-chat",
            "AGENT_LITELLM_MODEL=deepseek/deepseek-v4-flash",
            "LLM_TEMPERATURE=0.42",
            "LITELLM_FALLBACK_MODELS=deepseek/deepseek-v4-flash,cohere/command-r-plus",
            "VISION_MODEL=deepseek/deepseek-chat",
        )

        response = self.service.update(
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

        self.assertTrue(response["success"])
        current_map = self.manager.read_config_map()
        self.assertEqual(current_map["LLM_TEMPERATURE"], "0.42")
        self.assertEqual(current_map["LITELLM_MODEL"], "")
        self.assertEqual(current_map["AGENT_LITELLM_MODEL"], "")
        self.assertEqual(current_map["VISION_MODEL"], "")
        self.assertEqual(
            current_map["LITELLM_FALLBACK_MODELS"],
            "deepseek/deepseek-v4-flash",
        )

    @patch.object(SystemConfigService, "_reload_runtime_singletons")
    def test_update_with_reload_resets_runtime_singletons(
        self,
        mock_reload_runtime_singletons,
    ) -> None:
        response = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[{"key": "STOCK_LIST", "value": "600519"}],
            reload_now=True,
        )

        self.assertTrue(response["success"])
        mock_reload_runtime_singletons.assert_called_once()

    def test_update_with_reload_applies_updated_env_file_when_process_env_is_stale(self) -> None:
        os.environ["STOCK_LIST"] = "600519,000001"

        response = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[{"key": "STOCK_LIST", "value": "300750,TSLA"}],
            reload_now=True,
        )

        self.assertTrue(response["success"])
        self.assertEqual(Config.get_instance().stock_list, ["300750", "TSLA"])

    def test_update_raises_conflict_for_stale_version(self) -> None:
        with self.assertRaises(ConfigConflictError):
            self.service.update(
                config_version="stale-version",
                items=[{"key": "STOCK_LIST", "value": "600519"}],
                reload_now=False,
            )

    def test_update_appends_news_window_explainability_warning(self) -> None:
        response = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[
                {"key": "NEWS_STRATEGY_PROFILE", "value": "ultra_short"},
                {"key": "NEWS_MAX_AGE_DAYS", "value": "7"},
            ],
            reload_now=False,
        )

        self.assertTrue(response["success"])
        joined = " | ".join(response["warnings"])
        self.assertIn("effective_days=1", joined)
        self.assertIn("min(profile_days, NEWS_MAX_AGE_DAYS)", joined)

    def test_update_appends_max_workers_warning(self) -> None:
        response = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[{"key": "MAX_WORKERS", "value": "1"}],
            reload_now=False,
        )

        self.assertTrue(response["success"])
        joined = " | ".join(response["warnings"])
        self.assertIn("MAX_WORKERS=1", joined)
        self.assertIn("reload_now=false", joined)

    def test_update_appends_mode_specific_startup_warnings(self) -> None:
        response = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[
                {"key": "RUN_IMMEDIATELY", "value": "false"},
                {"key": "SCHEDULE_ENABLED", "value": "true"},
                {"key": "SCHEDULE_RUN_IMMEDIATELY", "value": "true"},
            ],
            reload_now=True,
        )

        self.assertTrue(response["success"])
        run_warning = next(
            warning
            for warning in response["warnings"]
            if "RUN_IMMEDIATELY 已写入 .env" in warning
        )
        schedule_warning = next(
            warning
            for warning in response["warnings"]
            if "SCHEDULE_ENABLED" in warning
        )
        schedule_run_warning = next(
            warning
            for warning in response["warnings"]
            if "SCHEDULE_RUN_IMMEDIATELY" in warning
        )

        self.assertIn("非 schedule 模式", run_warning)
        self.assertNotIn("以 schedule 模式", run_warning)
        self.assertIn("runtime scheduler", schedule_warning)
        self.assertIn("CLI schedule", schedule_warning)
        self.assertIn("SCHEDULE_RUN_IMMEDIATELY", schedule_run_warning)
        self.assertIn("不会因为本次保存启动、停止或重建 scheduler", schedule_run_warning)
        self.assertIn("以 schedule 模式重新启动后生效", schedule_run_warning)
        self.assertNotIn("它属于启动期单次运行配置", schedule_run_warning)

    def test_update_appends_schedule_time_runtime_rebind_warning(self) -> None:
        response = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[{"key": "SCHEDULE_TIME", "value": "09:30"}],
            reload_now=True,
        )

        self.assertTrue(response["success"])
        schedule_time_warning = next(
            warning
            for warning in response["warnings"]
            if "SCHEDULE_TIME=09:30 已写入 .env" in warning
        )

        self.assertIn("已经以 schedule 模式运行", schedule_time_warning)
        self.assertIn("自动重建 daily job", schedule_time_warning)
        self.assertIn("不会启动 scheduler", schedule_time_warning)
        self.assertNotIn("重启当前进程", schedule_time_warning)
        self.assertNotIn("不会因为本次保存启动、停止或重建 scheduler", schedule_time_warning)

    def test_update_schedule_time_blank_warning_reports_effective_default(self) -> None:
        response = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[{"key": "SCHEDULE_TIME", "value": "   "}],
            reload_now=True,
        )

        self.assertTrue(response["success"])
        self.assertTrue(
            any("SCHEDULE_TIME=18:00 已写入 .env" in warning for warning in response["warnings"]),
            response["warnings"],
        )

    def test_update_appends_webui_bind_restart_warning(self) -> None:
        response = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[
                {"key": "WEBUI_HOST", "value": "0.0.0.0"},
                {"key": "WEBUI_PORT", "value": "18000"},
            ],
            reload_now=True,
        )

        self.assertTrue(response["success"])
        bind_warning = next(
            warning
            for warning in response["warnings"]
            if "WEBUI_HOST" in warning and "WEBUI_PORT" in warning
        )

        self.assertIn("启动期监听配置", bind_warning)
        self.assertIn("不会因为本次保存重新绑定监听地址或端口", bind_warning)
        self.assertIn("重启当前进程、Docker 容器或服务管理器后生效", bind_warning)

    def test_update_warns_when_runtime_model_references_are_cleared(self) -> None:
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

        response = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[
                {"key": "LLM_DEEPSEEK_MODELS", "value": "deepseek-v4-flash,deepseek-v4-pro"},
                {"key": "LITELLM_MODEL", "value": ""},
                {"key": "AGENT_LITELLM_MODEL", "value": ""},
                {"key": "LITELLM_FALLBACK_MODELS", "value": "deepseek/deepseek-v4-pro,cohere/command-r-plus"},
                {"key": "VISION_MODEL", "value": ""},
            ],
            reload_now=False,
        )

        self.assertTrue(response["success"])
        warning = next(
            warning
            for warning in response["warnings"]
            if "已同步清理失效的运行时模型引用" in warning
        )
        self.assertIn("主模型 / Agent 主模型 / Vision 模型 / 备选模型中的失效项", warning)
        self.assertIn("桌面端导出备份", warning)

    def test_update_market_review_region_does_not_trigger_runtime_model_cleanup(self) -> None:
        litellm_config_path = Path(self.temp_dir.name) / "litellm_config.yaml"
        litellm_config_path.write_text("model_list: []\n", encoding="utf-8")

        self._rewrite_env(
            "MARKET_REVIEW_REGION=cn",
            "LITELLM_MODEL=openai/gpt-4o-mini",
            "AGENT_LITELLM_MODEL=openai/gpt-4o",
            "LITELLM_FALLBACK_MODELS=openai/gpt-4o-mini,openai/gpt-4o",
            "VISION_MODEL=openai/gpt-4o",
            f"LITELLM_CONFIG={litellm_config_path}",
            "LLM_CHANNELS=openai",
            "LLM_OPENAI_PROTOCOL=openai",
            "LLM_OPENAI_BASE_URL=https://llm-openai.example.com/v1",
            "LLM_OPENAI_API_KEYS=legacy-openai-secret",
            "LLM_OPENAI_MODELS=openai/gpt-4o-mini,openai/gpt-4o",
            "OPENAI_BASE_URL=https://openai.example.com/v1",
            "OPENAI_API_KEY=sk-openai",
            "OPENAI_MODEL=gpt-4.1",
            "ANTHROPIC_MODEL=claude-sonnet-4-6",
        )

        response = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[{"key": "MARKET_REVIEW_REGION", "value": "both"}],
            reload_now=False,
        )

        self.assertTrue(response["success"])
        self.assertIn("MARKET_REVIEW_REGION", response["updated_keys"])
        current_map = self.manager.read_config_map()
        self.assertEqual(current_map["MARKET_REVIEW_REGION"], "both")
        self.assertEqual(current_map["LITELLM_MODEL"], "openai/gpt-4o-mini")
        self.assertEqual(current_map["AGENT_LITELLM_MODEL"], "openai/gpt-4o")
        self.assertEqual(current_map["LITELLM_FALLBACK_MODELS"], "openai/gpt-4o-mini,openai/gpt-4o")
        self.assertEqual(current_map["VISION_MODEL"], "openai/gpt-4o")
        self.assertEqual(current_map["LITELLM_CONFIG"], str(litellm_config_path))
        self.assertEqual(current_map["LLM_CHANNELS"], "openai")
        self.assertEqual(current_map["LLM_OPENAI_PROTOCOL"], "openai")
        self.assertEqual(current_map["LLM_OPENAI_BASE_URL"], "https://llm-openai.example.com/v1")
        self.assertEqual(current_map["LLM_OPENAI_API_KEYS"], "legacy-openai-secret")
        self.assertEqual(current_map["LLM_OPENAI_MODELS"], "openai/gpt-4o-mini,openai/gpt-4o")
        self.assertEqual(current_map["OPENAI_BASE_URL"], "https://openai.example.com/v1")
        self.assertEqual(current_map["OPENAI_API_KEY"], "sk-openai")
        self.assertEqual(current_map["OPENAI_MODEL"], "gpt-4.1")
        self.assertEqual(current_map["ANTHROPIC_MODEL"], "claude-sonnet-4-6")
        self.assertFalse(
            any("已同步清理失效的运行时模型引用" in warning for warning in response["warnings"]),
            response["warnings"],
        )

    def test_update_market_review_region_accepts_comma_separated_regions(self) -> None:
        response = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[{"key": "MARKET_REVIEW_REGION", "value": "cn,jp,us"}],
            reload_now=False,
        )

        self.assertTrue(response["success"])
        self.assertIn("MARKET_REVIEW_REGION", response["updated_keys"])
        current_map = self.manager.read_config_map()
        self.assertEqual(current_map["MARKET_REVIEW_REGION"], "cn,jp,us")
