"""Tests for config registry reports."""

from tests.config.settings._config_registry_support import (
    _TestReportDisplayFieldsRegisteredFixture,
    build_schema_response,
    get_field_definition,
    unittest,
)


class TestReportDisplayFieldsRegistered(_TestReportDisplayFieldsRegisteredFixture, unittest.TestCase):
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
