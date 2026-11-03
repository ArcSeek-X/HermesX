"""Tests for config registry generation."""

from tests.config.settings._config_registry_support import (
    SCHEMA_VERSION,
    WEB_SETTINGS_HIDDEN_FROM_UI,
    WEB_SETTINGS_PENDING_EXPOSURE,
    _TestP6LlmChannelSwitchStaysPendingFixture,
    build_schema_response,
    get_field_definition,
    get_registered_field_keys,
    re,
    unittest,
)


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


class TestP6LlmChannelSwitchStaysPending(_TestP6LlmChannelSwitchStaysPendingFixture, unittest.TestCase):
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
