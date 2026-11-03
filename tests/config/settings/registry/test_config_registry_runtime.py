"""Tests for config registry runtime."""

from tests.config.settings._config_registry_support import (
    _TestIssue1512SettingsFieldsFixture,
    _TestMarketReviewFieldsRegisteredFixture,
    build_schema_response,
    get_field_definition,
    re,
    unittest,
)


class TestAlphaSiftFieldsRegistered(unittest.TestCase):
    def test_install_spec_is_sensitive(self):
        field = get_field_definition("ALPHASIFT_INSTALL_SPEC")

        self.assertTrue(field["is_sensitive"])
        self.assertEqual(field["ui_control"], "password")


class TestScheduleTimesFieldRegistered(unittest.TestCase):
    def test_schedule_times_pattern_accepts_documented_empty_fallback(self):
        field = get_field_definition("SCHEDULE_TIMES")
        pattern = re.compile(field["validation"]["pattern"])

        self.assertIsNotNone(pattern.fullmatch(""))
        self.assertIsNotNone(pattern.fullmatch("   "))
        self.assertIsNotNone(pattern.fullmatch("09:20,12:30,15:10"))
        self.assertIsNone(pattern.fullmatch("09:20,"))
        self.assertIsNone(pattern.fullmatch("25:70"))


class TestIssue1512SettingsFields(_TestIssue1512SettingsFieldsFixture, unittest.TestCase):
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


class TestMarketReviewFieldsRegistered(_TestMarketReviewFieldsRegisteredFixture, unittest.TestCase):
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
