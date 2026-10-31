# -*- coding: utf-8 -*-
# 本文件主要测试：测试配置注册表相关功能
"""Tests for config_registry field definitions and schema building.

Ensures every notification channel that has a sender implementation also
has its config keys registered in _FIELD_DEFINITIONS so the Web settings
page and /api/v1/system/config/schema can expose them.
"""
import re
import unittest
from pathlib import Path

from src.config.registry import (
    SCHEMA_VERSION,
    WEB_SETTINGS_HIDDEN_FROM_UI,
    WEB_SETTINGS_LEGACY_ALIASES,
    WEB_SETTINGS_PENDING_EXPOSURE,
    WEB_SETTINGS_UNREGISTERED_KEYS,
    build_schema_response,
    get_field_definition,
    get_registered_field_keys,
)


class TestSlackFieldsRegistered(unittest.TestCase):
    """Slack config keys must be present in the registry."""

    _SLACK_KEYS = ("SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID", "SLACK_WEBHOOK_URL")

    def test_field_definitions_exist(self):
        for key in self._SLACK_KEYS:
            field = get_field_definition(key)
            self.assertEqual(field["category"], "notification", f"{key} category")
            self.assertNotEqual(
                field["display_order"], 9000,
                f"{key} should be explicitly registered, not inferred",
            )

    def test_bot_token_is_sensitive(self):
        field = get_field_definition("SLACK_BOT_TOKEN")
        self.assertTrue(field["is_sensitive"])
        self.assertEqual(field["ui_control"], "password")

    def test_webhook_url_is_sensitive(self):
        field = get_field_definition("SLACK_WEBHOOK_URL")
        self.assertTrue(field["is_sensitive"])
        self.assertEqual(field["ui_control"], "password")

    def test_channel_id_not_sensitive(self):
        field = get_field_definition("SLACK_CHANNEL_ID")
        self.assertFalse(field["is_sensitive"])

    def test_schema_response_includes_slack(self):
        schema = build_schema_response()
        notification_cat = next(
            (c for c in schema["categories"] if c["category"] == "notification"),
            None,
        )
        self.assertIsNotNone(notification_cat, "notification category missing")
        field_keys = {f["key"] for f in notification_cat["fields"]}
        for key in self._SLACK_KEYS:
            self.assertIn(key, field_keys, f"{key} missing from schema response")

    def test_display_order_between_discord_and_pushover(self):
        discord = get_field_definition("DISCORD_MAIN_CHANNEL_ID")
        pushover = get_field_definition("PUSHOVER_USER_KEY")
        for key in self._SLACK_KEYS:
            order = get_field_definition(key)["display_order"]
            self.assertGreater(order, discord["display_order"],
                               f"{key} should appear after Discord")
            self.assertLess(order, pushover["display_order"],
                            f"{key} should appear before Pushover")


class TestFeishuWebhookFieldsRegistered(unittest.TestCase):
    """Feishu webhook security fields must be registered for the settings UI."""

    _FEISHU_KEYS = (
        "FEISHU_WEBHOOK_URL",
        "FEISHU_WEBHOOK_SECRET",
        "FEISHU_WEBHOOK_KEYWORD",
    )

    def test_field_definitions_exist(self):
        for key in self._FEISHU_KEYS:
            field = get_field_definition(key)
            self.assertEqual(field["category"], "notification", f"{key} category")
            self.assertNotEqual(
                field["display_order"], 9000,
                f"{key} should be explicitly registered, not inferred",
            )

    def test_secret_is_sensitive(self):
        field = get_field_definition("FEISHU_WEBHOOK_SECRET")
        self.assertTrue(field["is_sensitive"])
        self.assertEqual(field["ui_control"], "password")

    def test_keyword_is_not_sensitive(self):
        field = get_field_definition("FEISHU_WEBHOOK_KEYWORD")
        self.assertFalse(field["is_sensitive"])
        self.assertEqual(field["ui_control"], "text")

    def test_webhook_url_uses_url_validation(self):
        field = get_field_definition("FEISHU_WEBHOOK_URL")
        self.assertEqual(field["validation"]["item_type"], "url")
        self.assertIn("https", field["validation"]["allowed_schemes"])

    def test_schema_response_includes_feishu_webhook_fields(self):
        schema = build_schema_response()
        notification_cat = next(
            (c for c in schema["categories"] if c["category"] == "notification"),
            None,
        )
        self.assertIsNotNone(notification_cat, "notification category missing")
        field_keys = {f["key"] for f in notification_cat["fields"]}
        for key in self._FEISHU_KEYS:
            self.assertIn(key, field_keys, f"{key} missing from schema response")


class TestAstrBotFieldsRegistered(unittest.TestCase):
    """AstrBot config keys must be explicitly registered for settings UI."""

    _ASTRBOT_KEYS = ("ASTRBOT_URL", "ASTRBOT_TOKEN")

    def test_field_definitions_exist(self):
        for key in self._ASTRBOT_KEYS:
            field = get_field_definition(key)
            self.assertEqual(field["category"], "notification", f"{key} category")
            self.assertNotEqual(
                field["display_order"], 9000,
                f"{key} should be explicitly registered, not inferred",
            )

    def test_url_and_token_are_sensitive_password_controls(self):
        for key in self._ASTRBOT_KEYS:
            field = get_field_definition(key)
            self.assertTrue(field["is_sensitive"], f"{key} should be sensitive")
            self.assertEqual(field["ui_control"], "password")

    def test_url_uses_url_validation(self):
        field = get_field_definition("ASTRBOT_URL")
        self.assertEqual(field["validation"]["item_type"], "url")
        self.assertIn("https", field["validation"]["allowed_schemes"])

    def test_schema_response_includes_astrbot_fields(self):
        schema = build_schema_response()
        notification_cat = next(
            (c for c in schema["categories"] if c["category"] == "notification"),
            None,
        )
        self.assertIsNotNone(notification_cat, "notification category missing")
        field_keys = {f["key"] for f in notification_cat["fields"]}
        for key in self._ASTRBOT_KEYS:
            self.assertIn(key, field_keys, f"{key} missing from schema response")


class TestAlphaSiftFieldsRegistered(unittest.TestCase):
    def test_install_spec_is_sensitive(self):
        field = get_field_definition("ALPHASIFT_INSTALL_SPEC")

        self.assertTrue(field["is_sensitive"])
        self.assertEqual(field["ui_control"], "password")


class TestLLMUsageHMACFieldsRegistered(unittest.TestCase):
    def test_secret_is_sensitive_password_field(self):
        field = get_field_definition("LLM_USAGE_HMAC_SECRET")

        self.assertEqual(field["category"], "ai_model")
        self.assertTrue(field["is_sensitive"])
        self.assertEqual(field["ui_control"], "password")
        self.assertEqual(field["help_key"], "settings.ai_model.LLM_USAGE_HMAC_SECRET")
        self.assertIn("high-entropy", field["description"])
        self.assertIn("version control", field["description"])
        self.assertIn("openssl rand -hex 32", field["examples"][0])
        self.assertIn("secret_value", field.get("warning_codes", []))

    def test_key_version_is_visible_non_sensitive_field(self):
        field = get_field_definition("LLM_USAGE_HMAC_KEY_VERSION")

        self.assertEqual(field["category"], "ai_model")
        self.assertFalse(field["is_sensitive"])
        self.assertEqual(field["ui_control"], "text")
        self.assertEqual(field["default_value"], "local-v1")
        self.assertEqual(field["help_key"], "settings.ai_model.LLM_USAGE_HMAC_KEY_VERSION")


class TestGenerationBackendFieldsRegistered(unittest.TestCase):
    def test_analysis_backend_fields_are_ai_model_selects(self):
        expected = {
            "GENERATION_BACKEND": "settings.ai_model.GENERATION_BACKEND",
            "GENERATION_FALLBACK_BACKEND": "settings.ai_model.GENERATION_FALLBACK_BACKEND",
        }
        for key, help_key in expected.items():
            field = get_field_definition(key)
            self.assertEqual(field["category"], "ai_model")
            self.assertEqual(field["ui_control"], "select")
            self.assertEqual(field["default_value"], "litellm")
            if key == "GENERATION_BACKEND":
                self.assertEqual(
                    field["validation"],
                    {"enum": ["litellm", "codex_cli", "claude_code_cli", "opencode_cli"]},
                )
                self.assertIn({"label": "Default model settings", "value": "litellm"}, field["options"])
                self.assertIn({"label": "Codex CLI (experimental)", "value": "codex_cli"}, field["options"])
                self.assertIn({"label": "Claude Code CLI (experimental)", "value": "claude_code_cli"}, field["options"])
                self.assertIn({"label": "OpenCode CLI (experimental)", "value": "opencode_cli"}, field["options"])
            else:
                self.assertEqual(field["validation"], {"enum": ["", "litellm"]})
                self.assertIn({"label": "Disabled", "value": ""}, field["options"])
                self.assertIn({"label": "Default model settings", "value": "litellm"}, field["options"])
            self.assertEqual(field["help_key"], help_key)
            self.assertNotEqual(field["display_order"], 9000)

    def test_agent_generation_backend_field_is_agent_select(self):
        field = get_field_definition("AGENT_GENERATION_BACKEND")

        self.assertEqual(field["category"], "agent")
        self.assertEqual(field["ui_control"], "select")
        self.assertEqual(field["default_value"], "auto")
        self.assertEqual(field["validation"], {"enum": ["auto", "litellm"]})
        self.assertEqual(
            field["options"],
            [
                {"label": "Auto", "value": "auto"},
                {"label": "Default model settings", "value": "litellm"},
            ],
        )
        self.assertEqual(field["help_key"], "settings.agent.AGENT_GENERATION_BACKEND")
        self.assertNotEqual(field["display_order"], 9000)

    def test_generation_backend_numeric_fields_have_upper_bounds(self):
        expected = {
            "GENERATION_BACKEND_TIMEOUT_SECONDS": {"min": 1, "max": 3600},
            "GENERATION_BACKEND_MAX_OUTPUT_BYTES": {"min": 1, "max": 33554432},
            "GENERATION_BACKEND_MAX_CONCURRENCY": {"min": 1, "max": 16},
            "LOCAL_CLI_BACKEND_MAX_CONCURRENCY": {"min": 1, "max": 4},
        }

        for key, validation in expected.items():
            self.assertEqual(get_field_definition(key)["validation"], validation)

    def test_schema_response_groups_generation_backend_fields(self):
        schema = build_schema_response()
        self.assertEqual(schema["schema_version"], SCHEMA_VERSION)
        self.assertEqual(SCHEMA_VERSION, "2026-06-29-claude-code-cli-backend")

        categories = {
            category["category"]: {field["key"] for field in category["fields"]}
            for category in schema["categories"]
        }

        self.assertIn("GENERATION_BACKEND", categories["ai_model"])
        self.assertIn("GENERATION_FALLBACK_BACKEND", categories["ai_model"])
        self.assertIn("GENERATION_BACKEND_TIMEOUT_SECONDS", categories["ai_model"])
        self.assertIn("GENERATION_BACKEND_MAX_OUTPUT_BYTES", categories["ai_model"])
        self.assertIn("GENERATION_BACKEND_MAX_CONCURRENCY", categories["ai_model"])
        self.assertIn("LOCAL_CLI_BACKEND_MAX_CONCURRENCY", categories["ai_model"])
        self.assertIn("AGENT_GENERATION_BACKEND", categories["agent"])


class TestScheduleTimesFieldRegistered(unittest.TestCase):
    def test_schedule_times_pattern_accepts_documented_empty_fallback(self):
        field = get_field_definition("SCHEDULE_TIMES")
        pattern = re.compile(field["validation"]["pattern"])

        self.assertIsNotNone(pattern.fullmatch(""))
        self.assertIsNotNone(pattern.fullmatch("   "))
        self.assertIsNotNone(pattern.fullmatch("09:20,12:30,15:10"))
        self.assertIsNone(pattern.fullmatch("09:20,"))
        self.assertIsNone(pattern.fullmatch("25:70"))


class TestLLMPromptCacheFieldsRegistered(unittest.TestCase):
    def test_prompt_cache_telemetry_default_enabled(self):
        field = get_field_definition("LLM_PROMPT_CACHE_TELEMETRY_ENABLED")

        self.assertEqual(field["category"], "ai_model")
        self.assertEqual(field["ui_control"], "switch")
        self.assertEqual(field["data_type"], "boolean")
        self.assertEqual(field["default_value"], "true")
        self.assertEqual(field["help_key"], "settings.ai_model.LLM_PROMPT_CACHE_TELEMETRY_ENABLED")

    def test_prompt_cache_hints_default_disabled(self):
        field = get_field_definition("LLM_PROMPT_CACHE_HINTS_ENABLED")

        self.assertEqual(field["category"], "ai_model")
        self.assertEqual(field["ui_control"], "switch")
        self.assertEqual(field["data_type"], "boolean")
        self.assertEqual(field["default_value"], "false")
        self.assertEqual(field["help_key"], "settings.ai_model.LLM_PROMPT_CACHE_HINTS_ENABLED")

    def test_prompt_cache_diagnostics_is_select(self):
        field = get_field_definition("LLM_PROMPT_CACHE_DIAGNOSTICS_LEVEL")

        self.assertEqual(field["category"], "ai_model")
        self.assertEqual(field["ui_control"], "select")
        self.assertEqual(field["default_value"], "off")
        self.assertEqual(
            [option["value"] for option in field["options"]],
            ["off", "basic", "debug"],
        )
        self.assertEqual(field["validation"], {"enum": ["off", "basic", "debug"]})
        self.assertEqual(field["help_key"], "settings.ai_model.LLM_PROMPT_CACHE_DIAGNOSTICS_LEVEL")


class TestSettingsHelpMetadata(unittest.TestCase):
    """Field help metadata should be available for covered settings help slices."""

    _AI_MODEL_HIDDEN_KEYS = {
        "LLM_CHANNELS",
        "LLM_TEMPERATURE",
        "LITELLM_MODEL",
        "AGENT_LITELLM_MODEL",
        "LITELLM_FALLBACK_MODELS",
        "AIHUBMIX_KEY",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_API_KEYS",
        "GEMINI_API_KEY",
        "GEMINI_API_KEYS",
        "GEMINI_MODEL",
        "GEMINI_MODEL_FALLBACK",
        "GEMINI_TEMPERATURE",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_API_KEYS",
        "ANTHROPIC_MODEL",
        "ANTHROPIC_TEMPERATURE",
        "ANTHROPIC_MAX_TOKENS",
        "OPENAI_API_KEY",
        "OPENAI_API_KEYS",
        "OPENAI_BASE_URL",
        "OPENAI_MODEL",
        "OPENAI_VISION_MODEL",
        "OPENAI_TEMPERATURE",
        "VISION_MODEL",
    }
    _SYSTEM_HIDDEN_KEYS = {
        "ADMIN_AUTH_ENABLED",
    }

    _HELP_KEYS = (
        "STOCK_LIST",
        "GENERATION_BACKEND",
        "GENERATION_FALLBACK_BACKEND",
        "LITELLM_MODEL",
        "LLM_CHANNELS",
        "FEISHU_WEBHOOK_URL",
        "WEBUI_HOST",
        "AGENT_GENERATION_BACKEND",
        "AGENT_LITELLM_MODEL",
        "LITELLM_FALLBACK_MODELS",
        "TUSHARE_TOKEN",
        "REALTIME_SOURCE_PRIORITY",
        "TAVILY_API_KEYS",
        "NEWS_STRATEGY_PROFILE",
        "WECHAT_WEBHOOK_URL",
        "EMAIL_RECEIVERS",
        "SCHEDULE_TIME",
        "ADMIN_AUTH_ENABLED",
        # PR3 Phase 1: Agent + Event Alert
        "AGENT_MODE",
        "AGENT_MAX_STEPS",
        "AGENT_SKILLS",
        "AGENT_SKILL_DIR",
        "AGENT_NL_ROUTING",
        "AGENT_ARCH",
        "AGENT_ORCHESTRATOR_MODE",
        "AGENT_ORCHESTRATOR_TIMEOUT_S",
        "AGENT_SKILL_CONCURRENCY",
        "AGENT_RISK_OVERRIDE",
        "AGENT_DEEP_RESEARCH_BUDGET",
        "AGENT_DEEP_RESEARCH_TIMEOUT",
        "AGENT_MEMORY_ENABLED",
        "AGENT_SKILL_AUTOWEIGHT",
        "AGENT_SKILL_ROUTING",
        "AGENT_CONTEXT_COMPRESSION_ENABLED",
        "AGENT_CONTEXT_COMPRESSION_PROFILE",
        "AGENT_CONTEXT_COMPRESSION_TRIGGER_TOKENS",
        "AGENT_CONTEXT_PROTECTED_TURNS",
        "AGENT_EVENT_MONITOR_ENABLED",
        "AGENT_EVENT_MONITOR_INTERVAL_MINUTES",
        "AGENT_EVENT_ALERT_RULES_JSON",
        # PR3 Phase 2: Backtest
        "BACKTEST_ENABLED",
        "BACKTEST_EVAL_WINDOW_DAYS",
        "BACKTEST_MIN_AGE_DAYS",
        "BACKTEST_ENGINE_VERSION",
        "BACKTEST_NEUTRAL_BAND_PCT",
        # PR3 Phase 3: Report + Notification Route
        "REPORT_SUMMARY_ONLY",
        "REPORT_SHOW_LLM_MODEL",
        "REPORT_TEMPLATES_DIR",
        "REPORT_RENDERER_ENABLED",
        "REPORT_INTEGRITY_ENABLED",
        "REPORT_INTEGRITY_RETRY",
        "REPORT_HISTORY_COMPARE_N",
        "SINGLE_STOCK_NOTIFY",
        "MERGE_EMAIL_NOTIFICATION",
        "NOTIFICATION_REPORT_CHANNELS",
        "NOTIFICATION_ALERT_CHANNELS",
        "NOTIFICATION_SYSTEM_ERROR_CHANNELS",
        "NOTIFICATION_DEDUP_TTL_SECONDS",
        "NOTIFICATION_COOLDOWN_SECONDS",
        "NOTIFICATION_QUIET_HOURS",
        "NOTIFICATION_TIMEZONE",
        "NOTIFICATION_MIN_SEVERITY",
        "NOTIFICATION_DAILY_DIGEST_ENABLED",
        # PR3 Phase 4: System Runtime
        "LOG_LEVEL",
        "DEBUG",
        "MAX_WORKERS",
        "ANALYSIS_DELAY",
        "SAVE_CONTEXT_SNAPSHOT",
        "MARKET_REVIEW_ENABLED",
        "DAILY_MARKET_CONTEXT_ENABLED",
        "MARKET_REVIEW_REGION",
        "MARKET_REVIEW_COLOR_SCHEME",
        # Issue #1512: stream, log, and WebUI startup fields
        "DINGTALK_STREAM_ENABLED",
        "FEISHU_STREAM_ENABLED",
        "LOG_DIR",
        "WEBUI_ENABLED",
        "WEBUI_AUTO_BUILD",
    )

    def test_representative_fields_have_help_metadata(self):
        for key in self._HELP_KEYS:
            field = get_field_definition(key)
            self.assertTrue(field.get("help_key"), f"{key} missing help_key")
            self.assertTrue(field.get("examples"), f"{key} missing examples")
            self.assertTrue(field.get("docs"), f"{key} missing docs")

    def test_web_settings_visible_fields_have_help_metadata(self):
        """Every field rendered by SettingsField must have Help metadata."""

        missing = []
        for key in get_registered_field_keys():
            field = get_field_definition(key)
            if key in self._SYSTEM_HIDDEN_KEYS:
                continue
            if field.get("category") == "ai_model" and key in self._AI_MODEL_HIDDEN_KEYS:
                # These legacy fields are hidden only when channel config is active;
                # they are still visible/configurable in legacy setups.
                pass

            if not field.get("help_key") or not field.get("examples") or not field.get("docs"):
                missing.append(key)

        self.assertEqual([], missing)

    def test_webui_host_is_explicitly_registered(self):
        field = get_field_definition("WEBUI_HOST")
        self.assertEqual(field["category"], "system")
        self.assertNotEqual(field["display_order"], 9000)

    def test_save_context_snapshot_is_explicitly_registered(self):
        field = get_field_definition("SAVE_CONTEXT_SNAPSHOT")

        self.assertEqual(field["category"], "system")
        self.assertEqual(field["data_type"], "boolean")
        self.assertEqual(field["ui_control"], "switch")
        self.assertFalse(field["is_sensitive"])
        self.assertTrue(field["is_editable"])
        self.assertEqual(field["default_value"], "true")
        self.assertEqual(field["display_order"], 52)
        self.assertEqual(field["help_key"], "settings.system.SAVE_CONTEXT_SNAPSHOT")
        self.assertTrue(field.get("examples"))
        self.assertTrue(field.get("docs"))
        self.assertIn("analysis-context-pack.md#p6-", field["docs"][0]["href"])

    def test_restart_warning_codes_match_runtime_behavior(self):
        restart_required_keys = (
            "RUN_IMMEDIATELY",
            "SCHEDULE_ENABLED",
            "SCHEDULE_RUN_IMMEDIATELY",
            "WEBUI_HOST",
            "WEBUI_PORT",
            "WEBUI_ENABLED",
            "WEBUI_AUTO_BUILD",
            "LOG_DIR",
            "DINGTALK_STREAM_ENABLED",
            "FEISHU_STREAM_ENABLED",
            "LOG_LEVEL",
        )
        for key in restart_required_keys:
            field = get_field_definition(key)
            self.assertIn("restart_required", field.get("warning_codes", []))

        schedule_time = get_field_definition("SCHEDULE_TIME")
        self.assertNotIn("restart_required", schedule_time.get("warning_codes", []))

    def test_schema_response_includes_help_metadata(self):
        schema = build_schema_response()
        fields = {
            field["key"]: field
            for category in schema["categories"]
            for field in category["fields"]
        }

        self.assertEqual(fields["STOCK_LIST"]["help_key"], "settings.base.STOCK_LIST")
        self.assertIn("docs/full-guide.md", fields["STOCK_LIST"]["docs"][0]["href"])

    def test_admin_auth_help_is_read_only_in_generic_settings(self):
        field = get_field_definition("ADMIN_AUTH_ENABLED")
        self.assertFalse(field["is_editable"])
        self.assertIn("auth_settings_endpoint_required", field.get("warning_codes", []))


class TestIssue1512SettingsFields(unittest.TestCase):
    """Issue #1512 visible fields must be explicitly registered."""

    def test_stream_fields_are_registered_as_notification_switches(self) -> None:
        expected = {
            "FEISHU_STREAM_ENABLED": 17,
            "DINGTALK_STREAM_ENABLED": 35,
        }
        for key, display_order in expected.items():
            field = get_field_definition(key)
            self.assertEqual(field["category"], "notification")
            self.assertEqual(field["data_type"], "boolean")
            self.assertEqual(field["ui_control"], "switch")
            self.assertEqual(field["default_value"], "false")
            self.assertEqual(field["display_order"], display_order)
            self.assertTrue(field.get("help_key"))
            self.assertTrue(field.get("examples"))
            self.assertTrue(field.get("docs"))
            self.assertIn("not_webhook_delivery", field.get("warning_codes", []))
            self.assertIn("restart_required", field.get("warning_codes", []))

    def test_system_runtime_fields_are_registered_with_restart_boundary(self) -> None:
        expected = {
            "LOG_DIR": ("string", "text", "./logs", 31),
            "WEBUI_ENABLED": ("boolean", "switch", "false", 37),
            "WEBUI_AUTO_BUILD": ("boolean", "switch", "true", 38),
        }
        for key, (data_type, ui_control, default_value, display_order) in expected.items():
            field = get_field_definition(key)
            self.assertEqual(field["category"], "system")
            self.assertEqual(field["data_type"], data_type)
            self.assertEqual(field["ui_control"], ui_control)
            self.assertEqual(field["default_value"], default_value)
            self.assertEqual(field["display_order"], display_order)
            self.assertTrue(field.get("help_key"))
            self.assertTrue(field.get("examples"))
            self.assertTrue(field.get("docs"))
            self.assertIn("restart_required", field.get("warning_codes", []))


class TestEnvExampleWebSettingsCoverage(unittest.TestCase):
    """Active .env.example keys must be registered or explicitly declared."""

    _ENV_EXAMPLE = Path(__file__).resolve().parents[1] / ".env.example"
    _ACTIVE_ENV_ASSIGNMENT_RE = re.compile(r"^([A-Z][A-Z0-9_]*)=")

    def test_active_env_example_keys_are_registered_or_hidden_from_web_ui(self) -> None:
        active_keys = {
            match.group(1)
            for line in self._ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
            for match in [self._ACTIVE_ENV_ASSIGNMENT_RE.match(line.strip())]
            if match
        }
        registered_keys = set(get_registered_field_keys())

        self.assertEqual(
            sorted(active_keys - registered_keys - WEB_SETTINGS_UNREGISTERED_KEYS),
            [],
        )


class TestUnregisteredConfigKeysDeclared(unittest.TestCase):
    """``src/config/settings.py`` reads must be registered or declared as non-UI keys.

    Web settings only render registered fields. Without this guard a new
    ``os.getenv`` call silently becomes an invisible configuration knob:
    visible in ``.env`` but impossible to edit from the settings page.
    """

    _ROOT = Path(__file__).resolve().parents[1]
    _CONFIG_PY = _ROOT / "src/config/settings.py"
    _ENV_EXAMPLE = _ROOT / ".env.example"
    # os.getenv('KEY') / os.getenv("KEY") / os.environ.get('KEY')
    _ENV_READ_RE = re.compile(
        r"os\.(?:getenv|environ\.get)\(\s*[\"']([A-Z][A-Z0-9_]*)[\"']"
    )
    _ENV_ASSIGNMENT_RE = re.compile(r"^#?\s*([A-Z][A-Z0-9_]*)=")

    @classmethod
    def _config_read_keys(cls) -> set[str]:
        return set(cls._ENV_READ_RE.findall(cls._CONFIG_PY.read_text(encoding="utf-8")))

    @classmethod
    def _env_example_keys(cls) -> set[str]:
        return {
            match.group(1)
            for line in cls._ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
            for match in [cls._ENV_ASSIGNMENT_RE.match(line.strip())]
            if match
        }

    def test_config_reads_are_registered_or_declared(self) -> None:
        undeclared = sorted(
            self._config_read_keys()
            - set(get_registered_field_keys())
            - WEB_SETTINGS_UNREGISTERED_KEYS
        )
        self.assertEqual(
            undeclared,
            [],
            "src/config/settings.py 读取了未声明的配置键。请二选一：在 _FIELD_DEFINITIONS 中注册"
            "（会出现在 Web 设置页），或登记到 WEB_SETTINGS_HIDDEN_FROM_UI / "
            "WEB_SETTINGS_PENDING_EXPOSURE / WEB_SETTINGS_LEGACY_ALIASES。",
        )

    def test_declarations_do_not_overlap_registry(self) -> None:
        registered = set(get_registered_field_keys())
        for name, keys in (
            ("WEB_SETTINGS_HIDDEN_FROM_UI", WEB_SETTINGS_HIDDEN_FROM_UI),
            ("WEB_SETTINGS_PENDING_EXPOSURE", set(WEB_SETTINGS_PENDING_EXPOSURE)),
            ("WEB_SETTINGS_LEGACY_ALIASES", set(WEB_SETTINGS_LEGACY_ALIASES)),
        ):
            self.assertEqual(
                sorted(keys & registered),
                [],
                f"{name} 与 _FIELD_DEFINITIONS 重叠：注册后必须从声明表中移除。",
            )

    def test_declaration_tables_are_mutually_exclusive(self) -> None:
        tables = {
            "hidden": WEB_SETTINGS_HIDDEN_FROM_UI,
            "pending": set(WEB_SETTINGS_PENDING_EXPOSURE),
            "legacy": set(WEB_SETTINGS_LEGACY_ALIASES),
        }
        names = sorted(tables)
        for index, left in enumerate(names):
            for right in names[index + 1:]:
                self.assertEqual(
                    sorted(tables[left] & tables[right]),
                    [],
                    f"{left} 与 {right} 不得重复登记同一个键。",
                )

    def test_declared_keys_exist_in_config_or_env_example(self) -> None:
        config_keys = self._config_read_keys()
        env_keys = self._env_example_keys()
        for name, keys in (
            ("WEB_SETTINGS_HIDDEN_FROM_UI", WEB_SETTINGS_HIDDEN_FROM_UI),
            ("WEB_SETTINGS_PENDING_EXPOSURE", set(WEB_SETTINGS_PENDING_EXPOSURE)),
            ("WEB_SETTINGS_LEGACY_ALIASES", set(WEB_SETTINGS_LEGACY_ALIASES)),
        ):
            stale = sorted(keys - config_keys - env_keys)
            self.assertEqual(
                stale,
                [],
                f"{name} 中存在已失效的键（src/config/settings.py 和 .env.example 都不再出现）：{stale}",
            )

    def test_legacy_aliases_point_to_registered_keys(self) -> None:
        registered = set(get_registered_field_keys())
        broken = sorted(
            alias
            for alias, canonical in WEB_SETTINGS_LEGACY_ALIASES.items()
            if canonical not in registered
        )
        self.assertEqual(
            broken,
            [],
            "legacy 别名必须指向已注册的 canonical 键，否则设置页会失去唯一入口。",
        )


class TestSettingsHelpContract(unittest.TestCase):
    """Help keys must map to registry metadata or be editor-only.

    The LLM Channel editor uses internal field-level keys prefixed with
    ``settings.llm_channel.``. Those keys are valid for UI only and should not be
    expected in the backend registry.
    """

    _LLM_CHANNEL_HELP_PREFIX = "settings.llm_channel."
    _SETTINGS_HELP_FILE = Path(__file__).resolve().parents[1] / "apps/hrs-web/src/locales/settingsHelp.ts"

    @classmethod
    def _collect_registry_help_keys(cls) -> set[str]:
        keys = set()
        for key in get_registered_field_keys():
            definition = get_field_definition(key)
            help_key = definition.get("help_key")
            if help_key:
                keys.add(help_key)
        return keys

    @classmethod
    def _collect_locale_help_keys(cls) -> set[str]:
        content = cls._SETTINGS_HELP_FILE.read_text(encoding="utf-8")
        return set(re.findall(r"^\s*'([^']+)'\s*:\s*\{", content, flags=re.MULTILINE))

    def test_registry_help_keys_exist_in_locales(self) -> None:
        locale_keys = self._collect_locale_help_keys()
        registry_help_keys = self._collect_registry_help_keys()
        missing = sorted(registry_help_keys - locale_keys)
        self.assertEqual(missing, [], f"Registry help keys missing locale: {missing}")

    def test_locale_help_keys_are_registry_or_llm_channel_internal(self) -> None:
        registry_help_keys = self._collect_registry_help_keys()
        locale_keys = self._collect_locale_help_keys()
        external_keys = sorted(
            key
            for key in locale_keys
            if key not in registry_help_keys and not key.startswith(self._LLM_CHANNEL_HELP_PREFIX)
        )
        self.assertEqual(external_keys, [], f"Unexpected locale-only help keys: {external_keys}")


class TestSensitiveFieldsUsePasswordControl(unittest.TestCase):
    """Every is_sensitive field must use ui_control='password' to avoid
    leaking secrets in the Web settings page."""

    def test_all_sensitive_fields_use_password(self):
        schema = build_schema_response()
        violations = []
        for cat in schema["categories"]:
            for field in cat["fields"]:
                if field.get("is_sensitive") and field.get("ui_control") != "password":
                    violations.append(field["key"])
        self.assertEqual(violations, [],
                         f"Sensitive fields with non-password ui_control: {violations}")


class TestDiscordInteractionPublicKeyField(unittest.TestCase):
    def test_field_definition_exists(self):
        field = get_field_definition("DISCORD_INTERACTIONS_PUBLIC_KEY")
        self.assertEqual(field["category"], "notification")
        self.assertFalse(field["is_sensitive"])
        self.assertEqual(field["ui_control"], "text")

    def test_schema_response_includes_public_key_field(self):
        schema = build_schema_response()
        notification_cat = next(
            (c for c in schema["categories"] if c["category"] == "notification"),
            None,
        )
        self.assertIsNotNone(notification_cat, "notification category missing")
        field_keys = {f["key"] for f in notification_cat["fields"]}
        self.assertIn("DISCORD_INTERACTIONS_PUBLIC_KEY", field_keys)


class TestNotificationRouteFieldsRegistered(unittest.TestCase):
    """P3 notification route keys must be visible and validated in settings schema."""

    _ROUTE_KEYS = (
        "NOTIFICATION_REPORT_CHANNELS",
        "NOTIFICATION_ALERT_CHANNELS",
        "NOTIFICATION_SYSTEM_ERROR_CHANNELS",
    )

    def test_field_definitions_exist(self):
        for key in self._ROUTE_KEYS:
            field = get_field_definition(key)
            self.assertEqual(field["category"], "notification", f"{key} category")
            self.assertEqual(field["data_type"], "array", f"{key} data_type")
            self.assertFalse(field["is_sensitive"], f"{key} should not be sensitive")
            self.assertIn("email", field["validation"]["allowed_values"])

    def test_schema_response_includes_route_fields(self):
        schema = build_schema_response()
        notification_cat = next(
            (c for c in schema["categories"] if c["category"] == "notification"),
            None,
        )
        self.assertIsNotNone(notification_cat, "notification category missing")
        field_keys = {f["key"] for f in notification_cat["fields"]}
        for key in self._ROUTE_KEYS:
            self.assertIn(key, field_keys, f"{key} missing from schema response")


class TestAgentEventAlertRulesJsonField(unittest.TestCase):
    """Event Monitor legacy JSON config must advertise its P8 boundary."""

    def test_description_marks_legacy_and_web_api_boundaries(self):
        field = get_field_definition("AGENT_EVENT_ALERT_RULES_JSON")
        description = field["description"]

        self.assertIn("Legacy JSON supports only price_cross, price_change_percent, and volume_spike", description)
        self.assertIn("Technical indicator", description)
        self.assertIn("watchlist", description)
        self.assertIn("portfolio", description)
        self.assertIn("market light", description)
        self.assertIn("Alert API/Web center", description)


class TestAgentContextCompressionFields(unittest.TestCase):
    """Visible chat context compression config must be exposed consistently."""

    def test_profile_uses_chinese_labels_and_enum(self):
        field = get_field_definition("AGENT_CONTEXT_COMPRESSION_PROFILE")

        self.assertEqual(field["category"], "agent")
        self.assertEqual(field["ui_control"], "select")
        self.assertEqual(
            field["validation"]["enum"],
            ["cost", "balanced", "long_context_raw_first"],
        )
        self.assertEqual(
            [option["label"] for option in field["options"]],
            ["成本优先", "均衡推荐", "长上下文原文优先"],
        )

    def test_trigger_and_protected_turns_can_follow_profile_preset(self):
        trigger = get_field_definition("AGENT_CONTEXT_COMPRESSION_TRIGGER_TOKENS")
        protected = get_field_definition("AGENT_CONTEXT_PROTECTED_TURNS")

        self.assertEqual(trigger["default_value"], "")
        self.assertEqual(protected["default_value"], "")
        self.assertFalse(trigger["is_required"])
        self.assertFalse(protected["is_required"])
        self.assertIn("Leave empty", trigger["description"])
        self.assertIn("Leave empty", protected["description"])


class TestNotificationNoiseFieldsRegistered(unittest.TestCase):
    """P4 notification noise-control keys must be visible in settings schema."""

    _NOISE_KEYS = (
        "NOTIFICATION_DEDUP_TTL_SECONDS",
        "NOTIFICATION_COOLDOWN_SECONDS",
        "NOTIFICATION_QUIET_HOURS",
        "NOTIFICATION_TIMEZONE",
        "NOTIFICATION_MIN_SEVERITY",
        "NOTIFICATION_DAILY_DIGEST_ENABLED",
    )

    def test_field_definitions_exist(self):
        for key in self._NOISE_KEYS:
            field = get_field_definition(key)
            self.assertEqual(field["category"], "notification", f"{key} category")
            self.assertFalse(field["is_sensitive"], f"{key} should not be sensitive")
            self.assertFalse(field["is_required"], f"{key} should not be required")

        self.assertEqual(get_field_definition("NOTIFICATION_DEDUP_TTL_SECONDS")["data_type"], "integer")
        self.assertEqual(get_field_definition("NOTIFICATION_COOLDOWN_SECONDS")["data_type"], "integer")
        self.assertEqual(get_field_definition("NOTIFICATION_DAILY_DIGEST_ENABLED")["data_type"], "boolean")
        min_severity = get_field_definition("NOTIFICATION_MIN_SEVERITY")
        self.assertEqual(min_severity["options"][0]["value"], "")
        self.assertIn("", min_severity["validation"]["enum"])
        self.assertIn("warning", min_severity["validation"]["enum"])

    def test_schema_response_includes_noise_fields(self):
        schema = build_schema_response()
        notification_cat = next(
            (c for c in schema["categories"] if c["category"] == "notification"),
            None,
        )
        self.assertIsNotNone(notification_cat, "notification category missing")
        field_keys = {f["key"] for f in notification_cat["fields"]}
        for key in self._NOISE_KEYS:
            self.assertIn(key, field_keys, f"{key} missing from schema response")

class TestReportDisplayFieldsRegistered(unittest.TestCase):
    """Report display toggles should be visible in settings schema."""

    def test_report_show_llm_model_field_definition_exists(self):
        field = get_field_definition("REPORT_SHOW_LLM_MODEL")
        self.assertEqual(field["category"], "notification")
        self.assertEqual(field["data_type"], "boolean")
        self.assertEqual(field["ui_control"], "switch")
        self.assertEqual(field["default_value"], "true")
        self.assertFalse(field["is_sensitive"])

    def test_schema_response_includes_report_show_llm_model(self):
        schema = build_schema_response()
        notification_cat = next(
            (c for c in schema["categories"] if c["category"] == "notification"),
            None,
        )
        self.assertIsNotNone(notification_cat, "notification category missing")
        field_keys = {f["key"] for f in notification_cat["fields"]}
        self.assertIn("REPORT_SHOW_LLM_MODEL", field_keys)


class TestMarketReviewFieldsRegistered(unittest.TestCase):
    """Market review behavior toggles should be visible in settings schema."""

    def test_market_review_color_scheme_field_definition_exists(self):
        field = get_field_definition("MARKET_REVIEW_COLOR_SCHEME")
        self.assertEqual(field["category"], "system")
        self.assertEqual(field["data_type"], "string")
        self.assertEqual(field["ui_control"], "select")
        self.assertEqual(field["default_value"], "green_up")
        self.assertEqual(field["validation"]["enum"], ["green_up", "red_up"])
        self.assertFalse(field["is_sensitive"])

    def test_market_review_region_field_definition_exists(self):
        field = get_field_definition("MARKET_REVIEW_REGION")
        self.assertEqual(field["category"], "system")
        self.assertEqual(field["data_type"], "string")
        self.assertEqual(field["ui_control"], "text")
        self.assertEqual(field["default_value"], "cn")
        self.assertEqual(
            field["validation"]["allowed_values"],
            ["cn", "hk", "us", "jp", "kr", "both"],
        )
        self.assertEqual(
            field["validation"]["delimiter"],
            ",",
        )
        self.assertFalse(field["is_sensitive"])

    def test_daily_market_context_field_definition_exists(self):
        field = get_field_definition("DAILY_MARKET_CONTEXT_ENABLED")
        self.assertEqual(field["category"], "system")
        self.assertEqual(field["data_type"], "boolean")
        self.assertEqual(field["ui_control"], "switch")
        self.assertEqual(field["default_value"], "true")
        self.assertFalse(field["is_sensitive"])

    def test_schema_response_includes_market_review_color_scheme(self):
        schema = build_schema_response()
        system_cat = next((c for c in schema["categories"] if c["category"] == "system"), None)
        self.assertIsNotNone(system_cat, "system category missing")
        field_keys = {f["key"] for f in system_cat["fields"]}
        self.assertIn("MARKET_REVIEW_COLOR_SCHEME", field_keys)
        self.assertIn("DAILY_MARKET_CONTEXT_ENABLED", field_keys)
        self.assertIn("MARKET_REVIEW_REGION", field_keys)


class TestDingTalkWebhookFieldsRegistered(unittest.TestCase):
    """DingTalk group robot fields follow the visible settings contract."""

    def test_dingtalk_webhook_fields_are_visible_sensitive_and_documented(self):
        expected = {
            "DINGTALK_WEBHOOK_URL": "settings.notification.DINGTALK_WEBHOOK_URL",
            "DINGTALK_SECRET": "settings.notification.DINGTALK_SECRET",
        }
        for key, help_key in expected.items():
            field = get_field_definition(key)
            self.assertEqual(field["category"], "notification")
            self.assertEqual(field["ui_control"], "password")
            self.assertTrue(field["is_sensitive"])
            self.assertEqual(field["help_key"], help_key)
            self.assertTrue(field["examples"])
            self.assertTrue(field["docs"])
            self.assertNotIn(key, WEB_SETTINGS_HIDDEN_FROM_UI)

    def test_dingtalk_webhook_url_has_url_validation(self):
        field = get_field_definition("DINGTALK_WEBHOOK_URL")
        self.assertEqual(field["validation"]["item_type"], "url")
        self.assertEqual(field["validation"]["allowed_schemes"], ["http", "https"])

    def test_schema_response_includes_dingtalk_webhook_fields(self):
        schema = build_schema_response()
        notification = next(
            category
            for category in schema["categories"]
            if category["category"] == "notification"
        )
        fields = {field["key"]: field for field in notification["fields"]}
        self.assertIn("DINGTALK_WEBHOOK_URL", fields)
        self.assertIn("DINGTALK_SECRET", fields)
        self.assertEqual(
            fields["DINGTALK_WEBHOOK_URL"]["help_key"],
            "settings.notification.DINGTALK_WEBHOOK_URL",
        )


class TestRegistryDefaultsMatchRuntime(unittest.TestCase):
    """registry.default_value 必须反映无环境变量时 Config 的真实默认值。

    Web 设置页用 default_value 展示“未配置时的默认行为”，两套定义长期分叉
    会让用户看到与实际运行不一致的默认值。这里以 Config（运行时唯一真源）
    为基准做机械比对。

    例外：以下字段的默认值由其他配置推导，registry 用空串表示“跟随运行时”，
    因此不参与字面比对：

    - AGENT_CONTEXT_COMPRESSION_TRIGGER_TOKENS / AGENT_CONTEXT_PROTECTED_TURNS
      —— 由压缩档位预设推导；
    - SCHEDULE_TIMES —— 为空时回退 SCHEDULE_TIME；
    - AGENT_SKILL_DIR —— 为空时使用内置 strategies/ 目录。
    """

    _DERIVED_DEFAULT_KEYS = frozenset({
        "AGENT_CONTEXT_COMPRESSION_TRIGGER_TOKENS",
        "AGENT_CONTEXT_PROTECTED_TURNS",
        "AGENT_SKILL_DIR",
        "SCHEDULE_TIMES",
    })

    @staticmethod
    def _runtime_defaults():
        import os
        from dataclasses import fields
        from unittest.mock import patch

        from src.config import Config

        # 隔离本机环境与 .env：ENV_FILE 指向不存在的路径，其余配置键全部清空。
        preserved = {
            key: os.environ[key]
            for key in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "PYTHONPATH", "VIRTUAL_ENV")
            if key in os.environ
        }
        preserved["ENV_FILE"] = "/nonexistent/hermesx-test.env"
        with patch.dict(os.environ, preserved, clear=True):
            config = Config()
        return {field.name: getattr(config, field.name) for field in fields(config)}

    def test_registry_defaults_match_runtime(self) -> None:
        runtime = self._runtime_defaults()
        mismatches = []
        for key in get_registered_field_keys():
            if key in self._DERIVED_DEFAULT_KEYS:
                continue
            attribute = key.lower()
            if attribute not in runtime:
                continue
            expected = get_field_definition(key).get("default_value")
            if expected is None:
                continue

            actual = runtime[attribute]
            if isinstance(actual, bool):
                actual_text = "true" if actual else "false"
            elif isinstance(actual, (list, tuple)):
                actual_text = ",".join(str(item) for item in actual)
            elif actual is None:
                actual_text = ""
            else:
                actual_text = str(actual)

            if actual_text == str(expected):
                continue
            try:
                if float(actual_text) == float(expected):
                    continue
            except ValueError:
                pass
            mismatches.append((key, str(expected), actual_text))

        self.assertEqual(
            [],
            mismatches,
            "registry default_value 与 Config 运行时默认值不一致："
            f"{mismatches}",
        )


class TestP1DataSourceFieldsRegistered(unittest.TestCase):
    """P1 批次：外部行情凭证与板块 / 涨跌停池路由必须是正式注册字段。

    Sector / limit-pool routing mirrors the KLINE_* family. The option list must
    track the sources actually registered in each manager, otherwise the settings
    page offers values that never resolve.
    """

    _ROUTING_KEYS = (
        "SECTOR_DATA_SOURCE",
        "SECTOR_FALLBACK_ENABLED",
        "SECTOR_SOURCE_PRIORITY",
        "LIMITPOOL_DATA_SOURCE",
        "LIMITPOOL_FALLBACK_ENABLED",
        "LIMITPOOL_SOURCE_PRIORITY",
    )
    _CREDENTIAL_KEYS = (
        "ALPHAVANTAGE_API_KEY",
        "FINNHUB_API_KEY",
        "LONGBRIDGE_APP_KEY",
        "LONGBRIDGE_APP_SECRET",
        "LONGBRIDGE_ACCESS_TOKEN",
        "LONGBRIDGE_OAUTH_CLIENT_ID",
        "SOCIAL_SENTIMENT_API_KEY",
    )
    _RUNTIME_DEFAULTS = {
        "SECTOR_DATA_SOURCE": "auto",
        "SECTOR_FALLBACK_ENABLED": "true",
        "SECTOR_SOURCE_PRIORITY": "eastmoney",
        "LIMITPOOL_DATA_SOURCE": "auto",
        "LIMITPOOL_FALLBACK_ENABLED": "true",
        "LIMITPOOL_SOURCE_PRIORITY": "eastmoney",
        "SOCIAL_SENTIMENT_API_URL": "https://api.adanos.org",
    }

    def test_fields_are_explicitly_registered(self) -> None:
        keys = self._ROUTING_KEYS + self._CREDENTIAL_KEYS + ("SOCIAL_SENTIMENT_API_URL",)
        for key in keys:
            field = get_field_definition(key)
            self.assertEqual(field["category"], "data_source", key)
            self.assertNotEqual(
                field["display_order"],
                9000,
                f"{key} 必须是 _FIELD_DEFINITIONS 中的正式字段，不能依赖自动推断",
            )
            self.assertTrue(field.get("help_key"), f"{key} 缺少 help_key")
            self.assertTrue(field.get("examples"), f"{key} 缺少 examples")
            self.assertTrue(field.get("docs"), f"{key} 缺少 docs")

    def test_credential_fields_use_password_and_are_sensitive(self) -> None:
        for key in self._CREDENTIAL_KEYS:
            field = get_field_definition(key)
            self.assertTrue(field["is_sensitive"], key)
            self.assertEqual(field["ui_control"], "password", key)

    def test_routing_defaults_match_runtime(self) -> None:
        # 默认值必须与 src/config/settings.py 中对应的 os.getenv 回退值一致。
        for key, expected in self._RUNTIME_DEFAULTS.items():
            self.assertEqual(get_field_definition(key)["default_value"], expected, key)

    def test_routing_options_match_registered_sources(self) -> None:
        # 以 data_provider/{sector,limit_pool}/base.py 的 _build_sources() 为唯一事实源。
        from data_provider.limit_pool.base import _build_sources as build_limit_pool_sources
        from data_provider.sector.base import _build_sources as build_sector_sources

        for key, builder in (
            ("SECTOR_DATA_SOURCE", build_sector_sources),
            ("LIMITPOOL_DATA_SOURCE", build_limit_pool_sources),
        ):
            registered_sources = set(builder().keys())
            option_values = {
                option["value"] for option in get_field_definition(key)["options"]
            } - {"auto"}
            self.assertEqual(
                option_values,
                registered_sources,
                f"{key} 的 options 必须与该数据源管理器真实注册的 source 一致",
            )


class TestP2NewsFieldsRegistered(unittest.TestCase):
    """P2 批次：资讯源（快讯 / 财经日历 / 本地资讯池 / NewsNow）必须是正式注册字段。

    这批字段此前只能改 `.env`，而它们直接决定「行情资讯」页面是否有数据。
    除注册形态外，这里额外绑定两件容易漂移的事：

    * 数值字段的 `validation.min/max` 必须与 `parse_env_int/parse_env_float` 的
      收敛边界一致——否则设置页会接受一个运行时被静默 clamp 的值；
    * URL 字段的默认值必须与运行时去尾斜杠后的结果一致。
    """

    _FIELD_KEYS = (
        "WSCN_LIVE_NEWS_ENABLED",
        "WSCN_LIVE_NEWS_FETCH_INTERVAL_SEC",
        "WSCN_LIVE_NEWS_IMPORTANT_SCORE",
        "WSCN_LIVE_NEWS_DEFAULT_LIMIT",
        "WSCN_LIVE_NEWS_TIMEOUT_SEC",
        "WSCN_LIVE_NEWS_FALLBACK_NEWSNOW",
        "WSCN_LIVE_NEWS_BASE_URL",
        "WALLSTREETCN_CALENDAR_ENABLED",
        "WALLSTREETCN_CALENDAR_IMPORTANT_SCORE",
        "WALLSTREETCN_CALENDAR_TIMEOUT",
        "WALLSTREETCN_CALENDAR_BASE_URL",
        "NEWS_INTEL_AUTO_FETCH_ENABLED",
        "NEWS_INTEL_RETENTION_DAYS",
        "NEWS_INTEL_MAX_ITEMS_PER_SOURCE",
        "NEWS_INTEL_FETCH_TIMEOUT_SEC",
        "NEWSNOW_BASE_URL",
    )
    _BOOLEAN_KEYS = (
        "WSCN_LIVE_NEWS_ENABLED",
        "WSCN_LIVE_NEWS_FALLBACK_NEWSNOW",
        "WALLSTREETCN_CALENDAR_ENABLED",
        "NEWS_INTEL_AUTO_FETCH_ENABLED",
    )
    _NUMERIC_BOUNDS = {
        "WSCN_LIVE_NEWS_FETCH_INTERVAL_SEC": (0, 86400),
        "WSCN_LIVE_NEWS_IMPORTANT_SCORE": (1, 10),
        "WSCN_LIVE_NEWS_DEFAULT_LIMIT": (1, 100),
        "WSCN_LIVE_NEWS_TIMEOUT_SEC": (1.0, 30.0),
        "WALLSTREETCN_CALENDAR_IMPORTANT_SCORE": (0, 10),
        "WALLSTREETCN_CALENDAR_TIMEOUT": (1.0, 30.0),
        "NEWS_INTEL_RETENTION_DAYS": (1, 365),
        "NEWS_INTEL_MAX_ITEMS_PER_SOURCE": (1, 200),
        "NEWS_INTEL_FETCH_TIMEOUT_SEC": (1.0, 30.0),
    }
    _HELP_KEY_GROUPS = {
        "settings.data_source.live_news": (
            "WSCN_LIVE_NEWS_ENABLED",
            "WSCN_LIVE_NEWS_FETCH_INTERVAL_SEC",
            "WSCN_LIVE_NEWS_IMPORTANT_SCORE",
            "WSCN_LIVE_NEWS_DEFAULT_LIMIT",
            "WSCN_LIVE_NEWS_TIMEOUT_SEC",
            "WSCN_LIVE_NEWS_FALLBACK_NEWSNOW",
            "WSCN_LIVE_NEWS_BASE_URL",
        ),
        "settings.data_source.live_calendar": (
            "WALLSTREETCN_CALENDAR_ENABLED",
            "WALLSTREETCN_CALENDAR_IMPORTANT_SCORE",
            "WALLSTREETCN_CALENDAR_TIMEOUT",
            "WALLSTREETCN_CALENDAR_BASE_URL",
        ),
        "settings.data_source.news_intel": (
            "NEWS_INTEL_AUTO_FETCH_ENABLED",
            "NEWS_INTEL_RETENTION_DAYS",
            "NEWS_INTEL_MAX_ITEMS_PER_SOURCE",
            "NEWS_INTEL_FETCH_TIMEOUT_SEC",
        ),
        "settings.data_source.newsnow": ("NEWSNOW_BASE_URL",),
    }
    _URL_DEFAULTS = {
        "WSCN_LIVE_NEWS_BASE_URL": "https://api-one.wallstcn.com",
        "WALLSTREETCN_CALENDAR_BASE_URL": "https://api-one-wscn.awtmt.com",
        "NEWSNOW_BASE_URL": "https://newsnow.busiyi.world",
    }

    @staticmethod
    def _build_config(overrides: dict):
        """在清空环境变量（`.env` 指向不存在路径）的前提下从环境变量构建 Config。

        注意：必须走 ``_load_from_env()``，它是环境变量解析入口；直接 ``Config()``
        只会拿到 dataclass 静态默认值，无法验证 clamp / 去尾斜杠行为。
        """
        import os
        from unittest.mock import patch

        from src.config import Config

        preserved = {
            key: os.environ[key]
            for key in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "PYTHONPATH", "VIRTUAL_ENV")
            if key in os.environ
        }
        preserved["ENV_FILE"] = "/nonexistent/hermesx-test.env"
        preserved.update(overrides)
        with patch.dict(os.environ, preserved, clear=True):
            return Config._load_from_env()

    def test_fields_are_explicitly_registered(self) -> None:
        declared = WEB_SETTINGS_UNREGISTERED_KEYS
        for key in self._FIELD_KEYS:
            field = get_field_definition(key)
            self.assertEqual(field["category"], "data_source", key)
            self.assertNotEqual(
                field["display_order"],
                9000,
                f"{key} 必须是 _FIELD_DEFINITIONS 中的正式字段，不能依赖自动推断",
            )
            self.assertTrue(field.get("help_key"), f"{key} 缺少 help_key")
            self.assertTrue(field.get("examples"), f"{key} 缺少 examples")
            self.assertTrue(field.get("docs"), f"{key} 缺少 docs")
            self.assertNotIn(key, declared, f"{key} 注册后必须从声明表移除")

    def test_help_keys_grouped_by_capability(self) -> None:
        for help_key, keys in self._HELP_KEY_GROUPS.items():
            for key in keys:
                self.assertEqual(
                    get_field_definition(key)["help_key"],
                    help_key,
                    f"{key} 的 help_key 应与同族字段一致",
                )

    def test_boolean_fields_use_switch_control(self) -> None:
        for key in self._BOOLEAN_KEYS:
            field = get_field_definition(key)
            self.assertEqual(field["data_type"], "boolean", key)
            self.assertEqual(field["ui_control"], "switch", key)
            self.assertIn(field["default_value"], ("true", "false"), key)

    def test_numeric_bounds_match_runtime_clamping(self) -> None:
        # parse_env_int/parse_env_float 会对越界值做 clamp；设置页的 min/max
        # 必须与之一致，否则用户保存的值会在运行时被静默改写。
        for key, (low, high) in self._NUMERIC_BOUNDS.items():
            validation = get_field_definition(key)["validation"]
            self.assertEqual(float(validation["min"]), float(low), f"{key}.min")
            self.assertEqual(float(validation["max"]), float(high), f"{key}.max")

            attribute = key.lower()
            overflow = self._build_config({key: str(high * 3 + 100)})
            self.assertEqual(
                float(getattr(overflow, attribute)), float(high),
                f"{key} 超过上限时运行时应 clamp 到 registry max",
            )
            underflow = self._build_config({key: str(low - 100)})
            self.assertEqual(
                float(getattr(underflow, attribute)), float(low),
                f"{key} 低于下限时运行时应 clamp 到 registry min",
            )

    def test_url_fields_strip_trailing_slash(self) -> None:
        for key, expected in self._URL_DEFAULTS.items():
            self.assertEqual(get_field_definition(key)["default_value"], expected, key)
            # 运行时会对末尾斜杠做 rstrip，填 https://host// 后应归一为 https://host
            config = self._build_config({key: "https://example.com//"})
            self.assertEqual(getattr(config, key.lower()), "https://example.com", key)


class TestP3BotFieldsRegistered(unittest.TestCase):
    """批次 P3：机器人与飞书事件订阅字段必须是正式注册字段。

    这一批的判定标准不是“键属于通知分类”，而是“运行时存在读取方”：
    每个注册键都要能在 ``src/config/settings.py`` 之外找到消费它的代码。

    因此这里同时锁定三件事：

    * 已注册字段的形态、help_key 分组与默认值；
    * 重启边界（分发器单例 / Stream 建连时读取的键标 restart_required，
      按请求或按通知实例读取的键不标）；
    * 无读取方的键不得注册，只能留在 pending 声明表里。
    """

    _FIELD_KEYS = (
        "BOT_ENABLED",
        "BOT_COMMAND_PREFIX",
        "BOT_ADMIN_USERS",
        "FEISHU_VERIFICATION_TOKEN",
        "FEISHU_ENCRYPT_KEY",
        "FEISHU_MAX_BYTES",
        "FEISHU_SEND_AS_FILE",
        "FEISHU_FOLDER_TOKEN",
        "EMAIL_SENDER_NAME",
    )
    _DISPLAY_ORDERS = {
        "BOT_ENABLED": 71,
        "BOT_COMMAND_PREFIX": 72,
        "BOT_ADMIN_USERS": 73,
        "FEISHU_VERIFICATION_TOKEN": 74,
        "FEISHU_ENCRYPT_KEY": 75,
        "FEISHU_MAX_BYTES": 76,
        "FEISHU_SEND_AS_FILE": 77,
        "FEISHU_FOLDER_TOKEN": 78,
        "EMAIL_SENDER_NAME": 79,
    }
    _HELP_KEY_GROUPS = {
        "settings.notification.bot_runtime": (
            "BOT_ENABLED",
            "BOT_COMMAND_PREFIX",
            "BOT_ADMIN_USERS",
        ),
        "settings.notification.feishu_event_security": (
            "FEISHU_VERIFICATION_TOKEN",
            "FEISHU_ENCRYPT_KEY",
        ),
        "settings.notification.feishu_delivery": (
            "FEISHU_MAX_BYTES",
            "FEISHU_SEND_AS_FILE",
            "FEISHU_FOLDER_TOKEN",
        ),
    }
    # 飞书事件订阅凭证：与群 Webhook 签名密钥同类，必须以密码控件隐藏。
    _CREDENTIAL_KEYS = ("FEISHU_VERIFICATION_TOKEN", "FEISHU_ENCRYPT_KEY")
    # 这些键在运行时只在“一次性构造”时读取，保存后必须重启：
    # - BOT_COMMAND_PREFIX / BOT_ADMIN_USERS -> bot.dispatcher.get_dispatcher()
    #   单例首次构建时读取，且没有生产代码调用 reset_dispatcher()
    # - FEISHU_VERIFICATION_TOKEN / FEISHU_ENCRYPT_KEY -> Stream 客户端建连时读取
    _RESTART_BOUNDARY_KEYS = (
        "BOT_COMMAND_PREFIX",
        "BOT_ADMIN_USERS",
        "FEISHU_VERIFICATION_TOKEN",
        "FEISHU_ENCRYPT_KEY",
    )
    # 这些键按请求 / 按通知实例读取，保存后下一次即生效，不得标 restart。
    _HOT_RELOAD_KEYS = (
        "BOT_ENABLED",
        "FEISHU_MAX_BYTES",
        "FEISHU_SEND_AS_FILE",
        "FEISHU_FOLDER_TOKEN",
        "EMAIL_SENDER_NAME",
    )
    # 无读取方：bot/platforms/ 下没有企业微信 / Telegram 适配器，
    # DISCORD_BOT_STATUS 全仓没有消费代码。注册它们只会造出“能保存但没人读”
    # 的字段，所以必须继续留在 WEB_SETTINGS_PENDING_EXPOSURE。
    _NO_CONSUMER_KEYS = (
        "WECOM_CORPID",
        "WECOM_TOKEN",
        "WECOM_ENCODING_AES_KEY",
        "WECOM_AGENT_ID",
        "TELEGRAM_WEBHOOK_SECRET",
        "DISCORD_BOT_STATUS",
    )
    _ROOT = Path(__file__).resolve().parents[1]

    @staticmethod
    def _build_config(overrides: dict):
        """从环境变量构建 Config，隔离本机 `.env`。

        必须走 ``_load_from_env()``：直接 ``Config()`` 只拿 dataclass 静态默认值，
        看不到列表切分、bool 解析和数值 clamp。
        """
        import os
        from unittest.mock import patch

        from src.config import Config

        preserved = {
            key: os.environ[key]
            for key in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "PYTHONPATH", "VIRTUAL_ENV")
            if key in os.environ
        }
        preserved["ENV_FILE"] = "/nonexistent/hermesx-test.env"
        preserved.update(overrides)
        with patch.dict(os.environ, preserved, clear=True):
            return Config._load_from_env()

    def test_fields_are_explicitly_registered(self) -> None:
        registered = set(get_registered_field_keys())
        for key in self._FIELD_KEYS:
            field = get_field_definition(key)
            self.assertEqual(field["category"], "notification", key)
            self.assertEqual(field["display_order"], self._DISPLAY_ORDERS[key], key)
            self.assertTrue(field.get("help_key"), f"{key} 缺少 help_key")
            self.assertTrue(field.get("examples"), f"{key} 缺少 examples")
            self.assertTrue(field.get("docs"), f"{key} 缺少 docs")
            self.assertTrue(field.get("description"), f"{key} 缺少 description")
            self.assertNotIn(key, WEB_SETTINGS_UNREGISTERED_KEYS, f"{key} 注册后必须从声明表移除")
            self.assertIn(key, registered, key)

    def test_help_keys_grouped_by_capability(self) -> None:
        for help_key, keys in self._HELP_KEY_GROUPS.items():
            for key in keys:
                self.assertEqual(
                    get_field_definition(key)["help_key"],
                    help_key,
                    f"{key} 的 help_key 应与同族字段一致",
                )
        # EMAIL_SENDER_NAME 复用既有邮件分组，不新建同义 help_key
        self.assertEqual(
            get_field_definition("EMAIL_SENDER_NAME")["help_key"],
            "settings.notification.email",
        )

    def test_credentials_use_password_control_and_ids_do_not(self) -> None:
        for key in self._CREDENTIAL_KEYS:
            field = get_field_definition(key)
            self.assertTrue(field["is_sensitive"], f"{key} 应标为敏感字段")
            self.assertEqual(field["ui_control"], "password", f"{key} 必须用密码控件")
        for key in ("FEISHU_FOLDER_TOKEN", "BOT_ADMIN_USERS", "BOT_COMMAND_PREFIX"):
            field = get_field_definition(key)
            self.assertFalse(field["is_sensitive"], f"{key} 是标识/名单，不是密钥")

    def test_restart_boundary_matches_runtime_read_path(self) -> None:
        for key in self._RESTART_BOUNDARY_KEYS:
            self.assertIn(
                "restart_required",
                get_field_definition(key).get("warning_codes", []),
                f"{key} 在一次性构造时读取，必须提醒重启",
            )
        for key in self._HOT_RELOAD_KEYS:
            self.assertNotIn(
                "restart_required",
                get_field_definition(key).get("warning_codes", []),
                f"{key} 按请求/按实例读取，不该误导用户重启",
            )

        # 上面的提醒只在“保存链路不会重置分发器”时成立。若将来接上重置，
        # 这条断言会失败，提醒同步去掉 BOT_* 的 restart_required。
        save_path = (self._ROOT / "src/application/runtime/system_config_service.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("reset_dispatcher", save_path)

    def test_no_consumer_keys_stay_declared_but_unregistered(self) -> None:
        registered = set(get_registered_field_keys())
        for key in self._NO_CONSUMER_KEYS:
            self.assertNotIn(key, registered, f"{key} 无运行时读取方，不得注册到设置页")
            self.assertIn(key, WEB_SETTINGS_PENDING_EXPOSURE, f"{key} 必须留在 pending 声明表")

    def test_numeric_bound_matches_runtime_clamping(self) -> None:
        validation = get_field_definition("FEISHU_MAX_BYTES")["validation"]
        self.assertEqual(float(validation["min"]), 1.0)
        # 运行时只收下限，不收上限：registry 不能多出一个 max 而把可用值锁窄。
        self.assertNotIn("max", validation)
        clamped = self._build_config({"FEISHU_MAX_BYTES": "0"})
        self.assertEqual(clamped.feishu_max_bytes, 1)
        default = self._build_config({})
        self.assertEqual(default.feishu_max_bytes, 20000)

    def test_defaults_match_runtime_parsing(self) -> None:
        config = self._build_config({})
        self.assertTrue(config.bot_enabled)
        self.assertEqual(config.bot_command_prefix, "/")
        self.assertEqual(config.bot_admin_users, [])
        self.assertFalse(config.feishu_send_as_file)
        self.assertEqual(config.email_sender_name, "HermesX股票分析助手")
        self.assertIsNone(config.feishu_verification_token)

        # 逗号分隔名单：运行时去空白、丢空项，与 array 字段的保存形态一致。
        split = self._build_config({"BOT_ADMIN_USERS": "ou_a, ou_b ,, "})
        self.assertEqual(split.bot_admin_users, ["ou_a", "ou_b"])

        # 两个开关的 bool 解析口径并不相同，这里把差异固定住：
        # BOT_ENABLED 走 .lower() == 'true'（大小写不敏感，但 '1' / 'yes' 不算开启），
        # FEISHU_SEND_AS_FILE 走 in ('true', '1', 'yes')。
        self.assertFalse(self._build_config({"BOT_ENABLED": "false"}).bot_enabled)
        self.assertFalse(self._build_config({"BOT_ENABLED": "1"}).bot_enabled)
        self.assertTrue(self._build_config({"BOT_ENABLED": "TRUE"}).bot_enabled)
        self.assertTrue(self._build_config({"FEISHU_SEND_AS_FILE": "1"}).feishu_send_as_file)

    def test_schema_response_includes_p3_fields(self) -> None:
        schema = build_schema_response()
        notification = next(
            (cat for cat in schema["categories"] if cat["category"] == "notification"),
            None,
        )
        self.assertIsNotNone(notification, "notification category missing")
        field_keys = {field["key"] for field in notification["fields"]}
        for key in self._FIELD_KEYS:
            self.assertIn(key, field_keys)


class TestP4PortfolioRiskFieldsRegistered(unittest.TestCase):
    """批次 P4：组合与风险字段必须是正式注册字段。

    沿用 P3 的入库标准：只注册“运行时确有读取方”的键。这 6 个键在
    ``src/config/settings.py`` 之外全部有消费代码：阈值与窗口由
    ``PortfolioRiskService.get_risk_report()`` 组装，开关由
    ``PortfolioService.refresh_fx_rates()`` 读取。

    这批字段与 P3 的区别在于“不只是展示默认值”：阈值会进入风险报告并参与
    持仓告警规则的触发判定，所以这里额外把接近阈值的乘法语义固定住。
    """

    _RISK_KEYS = (
        "PORTFOLIO_RISK_CONCENTRATION_ALERT_PCT",
        "PORTFOLIO_RISK_DRAWDOWN_ALERT_PCT",
        "PORTFOLIO_RISK_STOP_LOSS_ALERT_PCT",
        "PORTFOLIO_RISK_STOP_LOSS_NEAR_RATIO",
        "PORTFOLIO_RISK_LOOKBACK_DAYS",
    )
    _FX_KEY = "PORTFOLIO_FX_UPDATE_ENABLED"
    _FIELD_KEYS = _RISK_KEYS + (_FX_KEY,)
    _DISPLAY_ORDERS = {
        "PORTFOLIO_RISK_CONCENTRATION_ALERT_PCT": 60,
        "PORTFOLIO_RISK_DRAWDOWN_ALERT_PCT": 61,
        "PORTFOLIO_RISK_STOP_LOSS_ALERT_PCT": 62,
        "PORTFOLIO_RISK_STOP_LOSS_NEAR_RATIO": 63,
        "PORTFOLIO_RISK_LOOKBACK_DAYS": 64,
        "PORTFOLIO_FX_UPDATE_ENABLED": 65,
    }
    # 数值字段运行时只传了 minimum，没有上限：registry 多写一个 max 就会把
    # 用户可用区间锁窄，并与 clamp 行为不一致。
    _NUMERIC_BOUNDS = {
        "PORTFOLIO_RISK_CONCENTRATION_ALERT_PCT": 0.0,
        "PORTFOLIO_RISK_DRAWDOWN_ALERT_PCT": 0.0,
        "PORTFOLIO_RISK_STOP_LOSS_ALERT_PCT": 0.0,
        "PORTFOLIO_RISK_STOP_LOSS_NEAR_RATIO": 0.0,
        "PORTFOLIO_RISK_LOOKBACK_DAYS": 1,
    }
    _ROOT = Path(__file__).resolve().parents[1]

    @staticmethod
    def _build_config(overrides: dict):
        """从环境变量构建 Config，隔离本机 `.env`。

        必须走 ``_load_from_env()``：直接 ``Config()`` 只拿 dataclass 静态默认值，
        看不到数值 clamp 和 bool 解析。
        """
        import os
        from unittest.mock import patch

        from src.config import Config

        preserved = {
            key: os.environ[key]
            for key in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "PYTHONPATH", "VIRTUAL_ENV")
            if key in os.environ
        }
        preserved["ENV_FILE"] = "/nonexistent/hermesx-test.env"
        preserved.update(overrides)
        with patch.dict(os.environ, preserved, clear=True):
            return Config._load_from_env()

    def test_fields_are_explicitly_registered(self) -> None:
        registered = set(get_registered_field_keys())
        for key in self._FIELD_KEYS:
            field = get_field_definition(key)
            self.assertEqual(field["category"], "system", key)
            self.assertEqual(field["display_order"], self._DISPLAY_ORDERS[key], key)
            self.assertTrue(field.get("help_key"), f"{key} 缺少 help_key")
            self.assertTrue(field.get("examples"), f"{key} 缺少 examples")
            self.assertTrue(field.get("docs"), f"{key} 缺少 docs")
            self.assertTrue(field.get("description"), f"{key} 缺少 description")
            self.assertNotIn(key, WEB_SETTINGS_PENDING_EXPOSURE, f"{key} 注册后必须从 pending 表移除")
            self.assertIn(key, registered, key)

    def test_no_new_frontend_category_is_introduced(self) -> None:
        """本批复用 system 分类，不新增前端 portfolio 分类。

        前端 SystemConfigCategory 是闭合 union，新增分类要同步改 union、
        icon map 和 3 个 locale 的分类标题。如果将来确实要拆出来，这个断言
        会提醒作者一并处理客户端兼容面。
        """
        schema = build_schema_response()
        self.assertEqual(len(schema["categories"]), 8)
        types_file = (self._ROOT / "apps/hrs-web/src/types/systemConfig.ts").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("'portfolio'", types_file)

    def test_help_keys_grouped_by_capability(self) -> None:
        for key in self._RISK_KEYS:
            self.assertEqual(
                get_field_definition(key)["help_key"],
                "settings.system.portfolio_risk",
                f"{key} 的 help_key 应与同族阈值字段一致",
            )
        # 汇率刷新是独立能力（接口行为而非告警灵敏度），不塞进同一 help_key。
        self.assertEqual(
            get_field_definition(self._FX_KEY)["help_key"],
            "settings.system.portfolio_fx",
        )

    def test_numeric_bounds_match_runtime_clamping(self) -> None:
        for key, minimum in self._NUMERIC_BOUNDS.items():
            validation = get_field_definition(key)["validation"]
            self.assertEqual(float(validation["min"]), float(minimum), key)
            self.assertNotIn("max", validation, f"{key} 运行时不收上限，registry 不得多写 max")

        clamped = self._build_config(
            {
                "PORTFOLIO_RISK_CONCENTRATION_ALERT_PCT": "-5",
                "PORTFOLIO_RISK_STOP_LOSS_NEAR_RATIO": "-1",
                "PORTFOLIO_RISK_LOOKBACK_DAYS": "0",
            }
        )
        self.assertEqual(clamped.portfolio_risk_concentration_alert_pct, 0.0)
        self.assertEqual(clamped.portfolio_risk_stop_loss_near_ratio, 0.0)
        self.assertEqual(clamped.portfolio_risk_lookback_days, 1)

    def test_defaults_match_runtime_parsing(self) -> None:
        config = self._build_config({})
        self.assertEqual(config.portfolio_risk_concentration_alert_pct, 35.0)
        self.assertEqual(config.portfolio_risk_drawdown_alert_pct, 15.0)
        self.assertEqual(config.portfolio_risk_stop_loss_alert_pct, 10.0)
        self.assertEqual(config.portfolio_risk_stop_loss_near_ratio, 0.8)
        self.assertEqual(config.portfolio_risk_lookback_days, 180)
        self.assertTrue(config.portfolio_fx_update_enabled)
        # 本批字段的 registry 默认值单独对一次，不只依赖全局默认值守卫。
        for key, expected in (
            ("PORTFOLIO_RISK_CONCENTRATION_ALERT_PCT", "35.0"),
            ("PORTFOLIO_RISK_DRAWDOWN_ALERT_PCT", "15.0"),
            ("PORTFOLIO_RISK_STOP_LOSS_ALERT_PCT", "10.0"),
            ("PORTFOLIO_RISK_STOP_LOSS_NEAR_RATIO", "0.8"),
            ("PORTFOLIO_RISK_LOOKBACK_DAYS", "180"),
            ("PORTFOLIO_FX_UPDATE_ENABLED", "true"),
        ):
            self.assertEqual(get_field_definition(key)["default_value"], expected, key)

        # 开关走 .lower() == 'true'：大小写不敏感，但 '1' / 'yes' 不算开启，
        # 与 FEISHU_SEND_AS_FILE 的口径不同。
        self.assertTrue(self._build_config({"PORTFOLIO_FX_UPDATE_ENABLED": "TRUE"}).portfolio_fx_update_enabled)
        self.assertFalse(self._build_config({"PORTFOLIO_FX_UPDATE_ENABLED": "1"}).portfolio_fx_update_enabled)
        self.assertFalse(self._build_config({"PORTFOLIO_FX_UPDATE_ENABLED": "yes"}).portfolio_fx_update_enabled)

        # 非法数值不会报错，而是回退默认值：设置页不能把错填变成启动失败。
        self.assertEqual(
            self._build_config({"PORTFOLIO_RISK_LOOKBACK_DAYS": "abc"}).portfolio_risk_lookback_days,
            180,
        )

    def test_thresholds_are_consumed_by_risk_report(self) -> None:
        """注册的不是死键：阈值从 Config 进入风险报告，并参与止损接近判定。"""
        source = (self._ROOT / "src/application/portfolio/portfolio_risk_service.py").read_text(encoding="utf-8")
        for attr in (
            "portfolio_risk_concentration_alert_pct",
            "portfolio_risk_drawdown_alert_pct",
            "portfolio_risk_stop_loss_alert_pct",
            "portfolio_risk_stop_loss_near_ratio",
            "portfolio_risk_lookback_days",
        ):
            self.assertIn(f'getattr(self.config, "{attr}"', source, f"{attr} 应仍被风险报告读取")

        snapshot = {
            "accounts": [
                {
                    "account_id": 1,
                    "positions": [
                        {"symbol": "600519", "avg_cost": 100.0, "last_price": 93.0},
                        {"symbol": "000001", "avg_cost": 100.0, "last_price": 91.0},
                    ],
                }
            ]
        }
        thresholds = {
            "stop_loss_alert_pct": 10.0,
            "stop_loss_near_ratio": 0.8,
        }
        from src.application.portfolio.portfolio_risk_service import PortfolioRiskService

        result = PortfolioRiskService._build_stop_loss(snapshot, thresholds)
        # near 阈值 = 10.0 × 0.8 = 8.0：亏 7% 不入选，亏 9% 入选但未跌破。
        self.assertEqual(result["near_count"], 1)
        self.assertEqual(result["triggered_count"], 0)
        self.assertEqual(result["items"][0]["symbol"], "000001")
        self.assertEqual(result["items"][0]["near_threshold_pct"], 8.0)

        tightened = PortfolioRiskService._build_stop_loss(
            snapshot,
            {"stop_loss_alert_pct": 10.0, "stop_loss_near_ratio": 0.5},
        )
        self.assertEqual(tightened["near_count"], 2)

    def test_fields_take_effect_without_restart(self) -> None:
        """读取时刻是按实例构造 / 按调用，保存链路会重置 Config 单例。"""
        for key in self._FIELD_KEYS:
            self.assertNotIn(
                "restart_required",
                get_field_definition(key).get("warning_codes", []),
                f"{key} 不需要重启，不该提醒用户重启",
            )

        # 下面的“不重启”只在风险服务负按请求构造时成立：若将来改成模块级
        # 单例或依赖注入缓存，这条断言会失败，提醒同步补 restart_required。
        endpoint_source = (
            self._ROOT / "api/v1/endpoints/portfolio.py"
        ).read_text(encoding="utf-8")
        self.assertIn("    service = PortfolioRiskService()", endpoint_source)
        risk_source = (
            self._ROOT / "src/application/portfolio/portfolio_risk_service.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("_risk_service_instance", risk_source)
        fx_source = (self._ROOT / "src/application/portfolio/portfolio_service.py").read_text(encoding="utf-8")
        self.assertIn("        config = get_config()", fx_source)

    def test_schema_response_includes_p4_fields(self) -> None:
        schema = build_schema_response()
        system = next(
            (cat for cat in schema["categories"] if cat["category"] == "system"),
            None,
        )
        self.assertIsNotNone(system, "system category missing")
        fields = system["fields"]
        field_keys = {field["key"] for field in fields}
        for key in self._FIELD_KEYS:
            self.assertIn(key, field_keys)
        # 本批字段排在 system 分类末尾，不打乱既有定时/服务/调试字段顺序。
        p4_orders = [field["display_order"] for field in fields if field["key"] in self._FIELD_KEYS]
        legacy_orders = [
            field["display_order"]
            for field in fields
            if field["key"] not in self._FIELD_KEYS
        ]
        self.assertGreaterEqual(min(p4_orders), max(legacy_orders))


class TestP5ReportImageAndWechatFormFieldsRegistered(unittest.TestCase):
    """批次 P5：报告转图片与企业微信消息形态字段必须是正式注册字段。

    入库标准沿用 P3/P4：只注册运行时确有读取方的键。本批 5 个键的读取点
    全部在实例构造或调用时：转图三键由 ``NotificationService.__init__`` / 每次
    转图调用（``src/infrastructure/reporting/img_render.py``）读取，企业微信两键由 ``WechatSender.__init__``
    读取，因此不标 ``restart_required``。

    同批故意不入库的两个 Vision 键另有原因（归属冲突 / 无行为读取方），下面
    把它们停在 pending 固定下来，避免下一批“顺手注册”。
    """

    _MD2IMG_KEYS = (
        "MARKDOWN_TO_IMAGE_CHANNELS",
        "MARKDOWN_TO_IMAGE_MAX_CHARS",
        "MD2IMG_ENGINE",
    )
    _WECHAT_KEYS = (
        "WECHAT_MSG_TYPE",
        "WECHAT_MAX_BYTES",
    )
    _FIELD_KEYS = _WECHAT_KEYS + _MD2IMG_KEYS
    _DISPLAY_ORDERS = {
        "WECHAT_MSG_TYPE": 80,
        "WECHAT_MAX_BYTES": 81,
        "MARKDOWN_TO_IMAGE_CHANNELS": 82,
        "MARKDOWN_TO_IMAGE_MAX_CHARS": 83,
        "MD2IMG_ENGINE": 84,
    }
    # 两个数值字段运行时只传了 minimum，没有上限：registry 多写 max 就会
    # 把用户可用区间锁窄，并与 clamp 行为不一致。
    _NUMERIC_BOUNDS = {
        "WECHAT_MAX_BYTES": 1,
        "MARKDOWN_TO_IMAGE_MAX_CHARS": 1,
    }
    # 下拉选项必须等于运行时真正接受的值集，不然后来加的“合法值”会被 enum 拦住。
    _SELECT_OPTIONS = {
        "WECHAT_MSG_TYPE": ["markdown", "text"],
        "MD2IMG_ENGINE": ["wkhtmltoimage", "markdown-to-file"],
    }
    _REMAINING_PENDING = ("VISION_MODEL", "VISION_PROVIDER_PRIORITY")
    _ROOT = Path(__file__).resolve().parents[1]

    @staticmethod
    def _build_config(overrides: dict):
        """从环境变量构建 Config，隔离本机 `.env`。

        必须走 ``_load_from_env()``：直接 ``Config()`` 只拿 dataclass 静态默认值，
        看不到“WECHAT_MAX_BYTES 默认值跟随消息类型”这类解析分支。
        """
        import os
        from unittest.mock import patch

        from src.config import Config

        preserved = {
            key: os.environ[key]
            for key in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "PYTHONPATH", "VIRTUAL_ENV")
            if key in os.environ
        }
        preserved["ENV_FILE"] = "/nonexistent/hermesx-test.env"
        preserved.update(overrides)
        with patch.dict(os.environ, preserved, clear=True):
            return Config._load_from_env()

    def test_fields_are_explicitly_registered(self) -> None:
        registered = set(get_registered_field_keys())
        for key in self._FIELD_KEYS:
            field = get_field_definition(key)
            self.assertEqual(field["category"], "notification", key)
            self.assertEqual(field["display_order"], self._DISPLAY_ORDERS[key], key)
            self.assertTrue(field.get("help_key"), f"{key} 缺少 help_key")
            self.assertTrue(field.get("examples"), f"{key} 缺少 examples")
            self.assertTrue(field.get("docs"), f"{key} 缺少 docs")
            self.assertTrue(field.get("description"), f"{key} 缺少 description")
            self.assertNotIn(key, WEB_SETTINGS_PENDING_EXPOSURE, f"{key} 注册后必须从 pending 表移除")
            self.assertIn(key, registered, key)

    def test_help_keys_grouped_by_capability(self) -> None:
        """两个能力各自一个 help_key，不塞进已有的飞书 / 聊天机器人组。"""
        for key in self._WECHAT_KEYS:
            self.assertEqual(
                get_field_definition(key)["help_key"],
                "settings.notification.wechat_delivery",
                key,
            )
        for key in self._MD2IMG_KEYS:
            self.assertEqual(
                get_field_definition(key)["help_key"],
                "settings.notification.markdown_to_image",
                key,
            )

    def test_select_options_match_runtime_accepted_values(self) -> None:
        """下拉选项是运行时的取值集，且保存校验会拿到自动补齐的 enum。"""
        for key, values in self._SELECT_OPTIONS.items():
            field = get_field_definition(key)
            self.assertEqual(field["ui_control"], "select", key)
            self.assertEqual(field["data_type"], "string", key)
            self.assertEqual([option["value"] for option in field["options"]], values, key)
            self.assertEqual(field["validation"]["enum"], values, f"{key} 的 enum 应由 options 自动派生")

    def test_numeric_bounds_match_runtime_clamping(self) -> None:
        for key, minimum in self._NUMERIC_BOUNDS.items():
            validation = get_field_definition(key)["validation"]
            self.assertEqual(float(validation["min"]), float(minimum), key)
            self.assertNotIn("max", validation, f"{key} 运行时不收上限，registry 不得多写 max")

        clamped = self._build_config(
            {"WECHAT_MAX_BYTES": "0", "MARKDOWN_TO_IMAGE_MAX_CHARS": "-1"}
        )
        self.assertEqual(clamped.wechat_max_bytes, 1)
        self.assertEqual(clamped.markdown_to_image_max_chars, 1)

    def test_defaults_match_runtime_parsing(self) -> None:
        config = self._build_config({})
        self.assertEqual(config.wechat_msg_type, "markdown")
        self.assertEqual(config.wechat_max_bytes, 4000)
        self.assertEqual(config.markdown_to_image_channels, [])
        self.assertEqual(config.markdown_to_image_max_chars, 15000)
        self.assertEqual(config.md2img_engine, "wkhtmltoimage")
        for key, expected in (
            ("WECHAT_MSG_TYPE", "markdown"),
            ("WECHAT_MAX_BYTES", "4000"),
            ("MARKDOWN_TO_IMAGE_CHANNELS", ""),
            ("MARKDOWN_TO_IMAGE_MAX_CHARS", "15000"),
            ("MD2IMG_ENGINE", "wkhtmltoimage"),
        ):
            self.assertEqual(get_field_definition(key)["default_value"], expected, key)

    def test_runtime_parsing_semantics_locked(self) -> None:
        """把注册文案声称的四个解析行为固定成用例，防止文案与实现分叉。

        1. WECHAT_MAX_BYTES 不填时默认值跟消息类型走（text 2048）；
        2. text 模式下发送侧还会把上限压到 2000 字节；
        3. 消息类型只做大写归一，引擎非法值回落 wkhtmltoimage；
        4. 渠道列表会去空、去空白并转小写。
        """
        self.assertEqual(self._build_config({"WECHAT_MSG_TYPE": "text"}).wechat_max_bytes, 2048)
        self.assertEqual(
            self._build_config({"WECHAT_MSG_TYPE": "TEXT", "WECHAT_MAX_BYTES": "3000"}).wechat_max_bytes,
            3000,
        )
        self.assertEqual(self._build_config({"WECHAT_MSG_TYPE": "TEXT"}).wechat_msg_type, "text")
        # 非法值不报错也不直接取 2048 以外的默认：发送侧把非 markdown 归为 markdown 行为。
        self.assertEqual(self._build_config({"WECHAT_MSG_TYPE": "news"}).wechat_msg_type, "news")
        self.assertEqual(self._build_config({"MD2IMG_ENGINE": "puppeteer"}).md2img_engine, "wkhtmltoimage")
        self.assertEqual(
            self._build_config({"MARKDOWN_TO_IMAGE_CHANNELS": " Telegram , WECHAT ,,"}).markdown_to_image_channels,
            ["telegram", "wechat"],
        )

        from src.infrastructure.notification.senders.wechat_sender import WechatSender

        sender = WechatSender(
            self._build_config(
                {
                    "WECHAT_WEBHOOK_URL": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test",
                    "WECHAT_MSG_TYPE": "text",
                    "WECHAT_MAX_BYTES": "9000",
                }
            )
        )
        captured: list = []

        def _capture(content, **kwargs):
            captured.append(content)
            return True

        sender._send_wechat_message = _capture
        long_content = "\n\n".join(f"### 股票 {index}\n\n{'内容' * 40}\n\n---" for index in range(40))
        self.assertTrue(sender.send_to_wechat(long_content))
        # 发送时刻的硬约束：text 下取 min(配置值, 2000)，因此配置写 9000
        # 也不会让分片突破 2000 字节（企业微信 text 单条限 2048）。
        self.assertGreater(len(captured), 1)
        for chunk in captured:
            self.assertLessEqual(len(chunk.encode("utf-8")), 2000)

        markdown_sender = WechatSender(
            self._build_config(
                {
                    "WECHAT_WEBHOOK_URL": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test",
                    "WECHAT_MAX_BYTES": "9000",
                }
            )
        )
        markdown_chunks: list = []
        markdown_sender._send_wechat_message = lambda content, **kwargs: (markdown_chunks.append(content), True)[1]
        markdown_sender._send_wechat_chunked = lambda content, max_bytes: (markdown_chunks.append(max_bytes), True)[1]
        self.assertTrue(markdown_sender.send_to_wechat(long_content))
        # 同样配置下 markdown 不叠加 2000 约束，直接用配置值分批。
        self.assertEqual(markdown_chunks, [9000])

    def test_fields_are_consumed_at_runtime(self) -> None:
        """注册的不是死键：五个属性在运行时代码里确有读取方。"""
        notification_source = (self._ROOT / "src/application/notification/notification.py").read_text(encoding="utf-8")
        self.assertIn("getattr(config, 'markdown_to_image_channels', [])", notification_source)
        self.assertIn("config, 'markdown_to_image_max_chars', 15000", notification_source)

        md2img_source = (self._ROOT / "src/infrastructure/reporting/img_render.py").read_text(encoding="utf-8")
        self.assertIn('getattr(get_config(), "md2img_engine"', md2img_source)

        wechat_source = (
            self._ROOT / "src/infrastructure/notification/senders/wechat_sender.py"
        ).read_text(encoding="utf-8")
        self.assertIn("getattr(config, 'wechat_max_bytes', 4000)", wechat_source)
        self.assertIn("getattr(config, 'wechat_msg_type', 'markdown')", wechat_source)

    def test_fields_take_effect_without_restart(self) -> None:
        """读取时刻是实例构造 / 按调用，且通知服务不缓存单例。"""
        for key in self._FIELD_KEYS:
            self.assertNotIn(
                "restart_required",
                get_field_definition(key).get("warning_codes", []),
                f"{key} 不需要重启，不该提醒用户重启",
            )

        # 下面的“不重启”只在通知服务每次新建时成立：若将来改成模块级单例
        # 或依赖注入缓存，这条断言会失败，提醒同步补 restart_required。
        notification_source = (self._ROOT / "src/application/notification/notification.py").read_text(encoding="utf-8")
        self.assertIn("    return NotificationService()", notification_source)
        self.assertNotIn("_notification_service_instance", notification_source)

    def test_remaining_vision_keys_stay_pending(self) -> None:
        """本批故意不入库的两个 Vision 键必须留在 pending，且仍未注册。

        VISION_MODEL 的写入归属在「AI 模型接入」通道编辑器，注册会变成一键两面；
        VISION_PROVIDER_PRIORITY 除 `Config.validate()` 的告警文案外无行为读取方。
        两者都要先定调才能入库，不得在后续批次里直接当普通卡片注册。
        """
        registered = set(get_registered_field_keys())
        for key in self._REMAINING_PENDING:
            self.assertIn(key, WEB_SETTINGS_PENDING_EXPOSURE, f"{key} 应仍在 pending 表")
            self.assertEqual(WEB_SETTINGS_PENDING_EXPOSURE[key], "P5", key)
            self.assertNotIn(key, registered, f"{key} 归属/行为未定，不得先注册")
        # 归属冲突不会因为“注册了”而自然消失：通用卡片列表仍只按隐藏集过滤。
        settings_source = (self._ROOT / "apps/hrs-web/src/pages/SettingsPage.tsx").read_text(encoding="utf-8")
        self.assertIn("VISION_MODEL", settings_source)

    def test_schema_response_includes_p5_fields(self) -> None:
        schema = build_schema_response()
        notification = next(
            (cat for cat in schema["categories"] if cat["category"] == "notification"),
            None,
        )
        self.assertIsNotNone(notification, "notification category missing")
        fields = notification["fields"]
        field_keys = {field["key"] for field in fields}
        for key in self._FIELD_KEYS:
            self.assertIn(key, field_keys)
        # 本批字段排在 notification 分类末尾，不打乱已有渠道/机器人字段顺序。
        p5_orders = [field["display_order"] for field in fields if field["key"] in self._FIELD_KEYS]
        legacy_orders = [
            field["display_order"]
            for field in fields
            if field["key"] not in self._FIELD_KEYS
        ]
        self.assertGreaterEqual(min(p5_orders), max(legacy_orders))
        # 下拉选项随 schema 下发，前端才能渲染中文标签。
        for key, values in self._SELECT_OPTIONS.items():
            field = next(item for item in fields if item["key"] == key)
            self.assertEqual([option["value"] for option in field["options"]], values, key)


class TestP6LlmChannelSwitchStaysPending(unittest.TestCase):
    """批次 P6 结论：`LLM_ANSPIRE_ENABLED` 不入库，继续留在 pending。

    它不是“还没来得及注册的普通开关”，而是两个条件同时命中：
    1. 写入归属已被「LLM 渠道编辑器」接管：前端把 `LLM_<渠道>_ENABLED` 当编辑器
       草稿命名空间（`isLlmChannelEditorDraftKey` 对任何 `LLM_` 前缀都返回 true），
       编辑器自己负责读回与写回；再注册就是和 P5 的 `VISION_MODEL` 同类的一键两面。
    2. 它只在 `LLM_CHANNELS` 里真的有个名叫 `anspire` 的渠道时才影响行为（已由
       `Config._load_from_env()` 实测）；其他情况下注册等于开放一个默认无效开关。
    """

    _KEY = "LLM_ANSPIRE_ENABLED"
    _EDITOR_OWNED_PENDING = ("VISION_MODEL", "VISION_PROVIDER_PRIORITY", "LLM_ANSPIRE_ENABLED")
    _ROOT = Path(__file__).resolve().parents[1]
    _ANSPIRE_KEY = "akey12345678"

    @staticmethod
    def _build_config(overrides: dict):
        """从环境变量构建 Config，隔离本机 `.env`（同批次 P5 口径）。"""
        import os
        from unittest.mock import patch

        from src.config import Config

        preserved = {
            key: os.environ[key]
            for key in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "PYTHONPATH", "VIRTUAL_ENV")
            if key in os.environ
        }
        preserved["ENV_FILE"] = "/nonexistent/hermesx-test.env"
        preserved.update(overrides)
        with patch.dict(os.environ, preserved, clear=True):
            return Config._load_from_env()

    def _settings_page_source(self) -> str:
        return (self._ROOT / "apps/hrs-web/src/pages/SettingsPage.tsx").read_text(encoding="utf-8")

    def test_key_stays_pending_and_unregistered(self) -> None:
        registered = set(get_registered_field_keys())
        self.assertIn(self._KEY, WEB_SETTINGS_PENDING_EXPOSURE)
        self.assertEqual(WEB_SETTINGS_PENDING_EXPOSURE[self._KEY], "P6")
        self.assertNotIn(self._KEY, registered, f"{self._KEY} 归属未定，不得先注册")
        self.assertNotIn(self._KEY, WEB_SETTINGS_HIDDEN_FROM_UI, "pending 和 hidden 不能同时写同一个键")

    def test_key_matches_frontend_channel_editor_namespace(self) -> None:
        """前端把本键算作编辑器命名空间：一旦注册，卡片会被编辑器口径静默过滤。

        取源码里的两处渠道状态键正则（模块级 `LLM_CHANNEL_STATUS_KEY_PATTERN` 与
        ai_model 过滤用的 `LLM_CHANNEL_KEY_RE`）都跑一遗：两处任一改了写法都要被发现。
        """
        source = self._settings_page_source()
        patterns = re.findall(
            r"const (?:LLM_CHANNEL_STATUS_KEY_PATTERN|LLM_CHANNEL_KEY_RE) = /(.+)/;", source
        )
        self.assertEqual(len(patterns), 2, f"预期两处渠道状态键正则，实际 {len(patterns)} 处")
        for body in patterns:
            self.assertRegex(self._KEY, body)
        # 通用卡片列表对 `LLM_` 前缀一律当编辑器草稿键，这层过滤不依赖注册表。
        self.assertIn("normalized.startsWith('LLM_')", source)

    def test_channel_editor_already_reads_and_writes_this_key(self) -> None:
        """编辑器已把这个键当自己的草稿读写，不需要也不应该再多一张卡片。"""
        editor = (
            self._ROOT / "apps/hrs-web/src/components/settings/LLMChannelEditor.tsx"
        ).read_text(encoding="utf-8")
        self.assertIn("`LLM_${upperName}_ENABLED`", editor, "编辑器读回渠道开关的写法已变，需重评归属")
        self.assertIn("updates.push({ key: `${prefix}_ENABLED`", editor, "编辑器写回渠道开关的写法已变，需重评归属")

    def test_runtime_effect_requires_an_anspire_channel(self) -> None:
        """行为回归：没配名叫 anspire 的渠道时，本开关完全不生效。

        这正是批次 P3 确立的入库标准要避免的“能填但默认无效”：如果把它当普通
        布尔卡片开放，绝大多数部署形态下用户看到的是一个怎么拨都没反应的开关。
        """
        base = {"ANSPIRE_API_KEYS": self._ANSPIRE_KEY}
        # 1) 未配 LLM_CHANNELS：走了“一键 OpenAI 兼容”兼容路径，开关无效。
        inert = self._build_config({**base, self._KEY: "false"})
        self.assertEqual(inert.openai_api_keys, [self._ANSPIRE_KEY])
        # 2) 配了名叫 anspire 的渠道：开关才真的关掉 Anspire 作为大模型密钥的复用。
        effective = self._build_config({**base, "LLM_CHANNELS": "anspire", self._KEY: "false"})
        self.assertEqual(effective.openai_api_keys, [])
        # 3) 同名渠道且不填本键：回退到 ANSPIRE_LLM_ENABLED（默认 true）。
        fallback = self._build_config({**base, "LLM_CHANNELS": "anspire"})
        self.assertEqual(fallback.openai_api_keys, [self._ANSPIRE_KEY])
        # 4) 配了别的渠道：依旧无效。
        other = self._build_config({**base, "LLM_CHANNELS": "gemini", self._KEY: "false"})
        self.assertEqual(other.openai_api_keys, [self._ANSPIRE_KEY])

    def test_editor_owned_keys_remain_pending_together(self) -> None:
        """P1–P6 配置暴露批次收口：剩下因“归属/行为未定”而不入库的键全部仍在 pending。"""
        registered = set(get_registered_field_keys())
        for key in self._EDITOR_OWNED_PENDING:
            self.assertIn(key, WEB_SETTINGS_PENDING_EXPOSURE, f"{key} 应从 pending 表丢了")
            self.assertNotIn(key, registered, f"{key} 需先定调才能注册")


# 设置页卡片标题 / 描述走前端中文表（systemConfigI18n.ts 的 fieldTitleMap /
# fieldDescriptionMap），未命中时回退到后端英文 title/description。下面这批
# 字段在本轮配置批次之前就没有中文条目，属于已登记的存量飘移（中文界面
# 会看到英文卡片）。把它固定成只能收缩的 backlog：新批次注册字段时必须同时
# 补中文标题与描述，不得再往这里加名字。
_ZH_UI_LOCALIZATION_BACKLOG = frozenset({
    "AGENT_SKILL_CONCURRENCY", "ALPHASIFT_ENABLED", "ALPHASIFT_INSTALL_SPEC", "ALPHAVANTAGE_API_KEY",
    "ANTHROPIC_API_KEY", "ANTHROPIC_API_KEYS", "ANTHROPIC_MAX_TOKENS", "ANTHROPIC_MODEL",
    "ANTHROPIC_TEMPERATURE", "CODESEARCH_DATA_SOURCE", "CODESEARCH_FALLBACK_ENABLED",
    "CODESEARCH_SOURCE_PRIORITY", "DEEPSEEK_API_KEYS", "FEISHU_CHAT_ID", "FEISHU_DOMAIN",
    "FEISHU_RECEIVE_ID_TYPE", "FINNHUB_API_KEY", "GEMINI_API_KEYS", "GEMINI_MODEL_FALLBACK",
    "KLINE_DATA_SOURCE", "KLINE_FALLBACK_ENABLED", "KLINE_SOURCE_PRIORITY", "LIMITPOOL_DATA_SOURCE",
    "LIMITPOOL_FALLBACK_ENABLED", "LIMITPOOL_SOURCE_PRIORITY", "LONGBRIDGE_ACCESS_TOKEN",
    "LONGBRIDGE_APP_KEY", "LONGBRIDGE_APP_SECRET", "LONGBRIDGE_OAUTH_CLIENT_ID", "NEWSNOW_BASE_URL",
    "NEWS_INTEL_AUTO_FETCH_ENABLED", "NEWS_INTEL_FETCH_TIMEOUT_SEC", "NEWS_INTEL_MAX_ITEMS_PER_SOURCE",
    "NEWS_INTEL_RETENTION_DAYS", "OPENAI_API_KEYS", "OPENAI_TEMPERATURE", "OPENAI_VISION_MODEL",
    "SECTOR_DATA_SOURCE", "SECTOR_FALLBACK_ENABLED", "SECTOR_SOURCE_PRIORITY", "SOCIAL_SENTIMENT_API_KEY",
    "SOCIAL_SENTIMENT_API_URL", "STOCKDB_BASE_URL", "STOCKDB_CACHE_TTL_SEC", "STOCKDB_COOLDOWN_SEC",
    "STOCKDB_ENABLED", "STOCKDB_MAX_ROWS", "STOCKDB_TIMEOUT_MS", "STOCKINFO_DATA_SOURCE",
    "STOCKINFO_FALLBACK_ENABLED", "STOCKINFO_SOURCE_PRIORITY", "STOCKSDK_BRIDGE_ENTRY", "STOCKSDK_ENABLED",
    "STOCKSDK_KLINE_FALLBACK", "STOCKSDK_NODE_BIN", "STOCKSDK_RATE_LIMIT_RPS", "STOCKSDK_TIMEOUT_MS",
    "WALLSTREETCN_CALENDAR_BASE_URL", "WALLSTREETCN_CALENDAR_ENABLED",
    "WALLSTREETCN_CALENDAR_IMPORTANT_SCORE", "WALLSTREETCN_CALENDAR_TIMEOUT", "WSCN_LIVE_NEWS_BASE_URL",
    "WSCN_LIVE_NEWS_DEFAULT_LIMIT", "WSCN_LIVE_NEWS_ENABLED", "WSCN_LIVE_NEWS_FALLBACK_NEWSNOW",
    "WSCN_LIVE_NEWS_FETCH_INTERVAL_SEC", "WSCN_LIVE_NEWS_IMPORTANT_SCORE", "WSCN_LIVE_NEWS_TIMEOUT_SEC",
})


class TestWebUiFieldLocalizationCoverage(unittest.TestCase):
    """每个已注册字段必须在前端中文表里，或在只能收缩的存量名单里。"""

    _ROOT = Path(__file__).resolve().parents[1]
    _I18N_TS = _ROOT / "apps/hrs-web/src/utils/systemConfigI18n.ts"
    _MAP_NAMES = ("fieldTitleMap", "fieldDescriptionMap")

    def _localized_keys(self, map_name: str) -> set:
        """抽取 ``const <map_name>: Record<...> = {...}`` 的顶层键。

        只匹配块内两空格缩进的 ``KEY:`` 行，避免把嵌套的选项标签当成字段名。
        """
        source = self._I18N_TS.read_text(encoding="utf-8")
        start = source.index(f"const {map_name}")
        end = source.index("\n};", start)
        return set(re.findall(r"^  ([A-Z0-9_]+):", source[start:end], re.M))

    def test_title_and_description_tables_share_the_same_keys(self) -> None:
        title, description = (self._localized_keys(name) for name in self._MAP_NAMES)
        self.assertEqual(
            title,
            description,
            "中文标题表与描述表键集不一致，只补一边会造成标题中文 / 描述英文的混排",
        )

    def test_registered_fields_are_localized_or_in_backlog(self) -> None:
        localized = self._localized_keys("fieldTitleMap")
        missing = set(get_registered_field_keys()) - localized - _ZH_UI_LOCALIZATION_BACKLOG
        self.assertEqual(
            missing,
            set(),
            "新注册字段必须同时补 fieldTitleMap / fieldDescriptionMap，不得加进存量名单",
        )

    def test_backlog_entries_are_still_unlocalized_and_registered(self) -> None:
        """存量名单只允许收缩：补上中文或删掉字段后都要同步从名单里移掉。"""
        registered = set(get_registered_field_keys())
        self.assertTrue(
            _ZH_UI_LOCALIZATION_BACKLOG <= registered,
            f"存量名单含未注册键: {sorted(_ZH_UI_LOCALIZATION_BACKLOG - registered)}",
        )
        already_done = _ZH_UI_LOCALIZATION_BACKLOG & self._localized_keys("fieldTitleMap")
        self.assertEqual(
            already_done,
            set(),
            "这些键已在前端中文表里，应从存量名单删掉；留着会让日后新增的同名缺口被当成存量",
        )

    def test_batch_p3_fields_are_localized(self) -> None:
        localized = self._localized_keys("fieldTitleMap")
        for key in TestP3BotFieldsRegistered._FIELD_KEYS:
            self.assertIn(key, localized, f"{key} 在中文设置页会回退成英文卡片标题")

    def test_batch_p4_fields_are_localized(self) -> None:
        localized = self._localized_keys("fieldTitleMap")
        for key in TestP4PortfolioRiskFieldsRegistered._FIELD_KEYS:
            self.assertIn(key, localized, f"{key} 在中文设置页会回退成英文卡片标题")


if __name__ == "__main__":
    unittest.main()
