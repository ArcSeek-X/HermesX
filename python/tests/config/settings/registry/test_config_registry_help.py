"""Tests for config registry help."""

from tests.config.settings._config_registry_support import (
    _TestP3BotFieldsRegisteredFixture as TestP3BotFieldsRegistered,
    _TestP4PortfolioRiskFieldsRegisteredFixture as TestP4PortfolioRiskFieldsRegistered,
    _TestSensitiveFieldsUsePasswordControlFixture,
    _TestSettingsHelpContractFixture,
    _TestSettingsHelpMetadataFixture,
    _TestWebUiFieldLocalizationCoverageFixture,
    _ZH_UI_LOCALIZATION_BACKLOG,
    build_schema_response,
    get_field_definition,
    get_registered_field_keys,
    unittest,
)


class TestSettingsHelpMetadata(_TestSettingsHelpMetadataFixture, unittest.TestCase):
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


class TestSettingsHelpContract(_TestSettingsHelpContractFixture, unittest.TestCase):
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


class TestSensitiveFieldsUsePasswordControl(_TestSensitiveFieldsUsePasswordControlFixture, unittest.TestCase):
    def test_all_sensitive_fields_use_password(self):
        schema = build_schema_response()
        violations = []
        for cat in schema["categories"]:
            for field in cat["fields"]:
                if field.get("is_sensitive") and field.get("ui_control") != "password":
                    violations.append(field["key"])
        self.assertEqual(violations, [],
                         f"Sensitive fields with non-password ui_control: {violations}")


class TestWebUiFieldLocalizationCoverage(_TestWebUiFieldLocalizationCoverageFixture, unittest.TestCase):
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
