"""Tests for system config notifications."""

from tests.application.runtime._system_config_service_support import (
    Config,
    SystemConfigService,
    _SystemConfigServiceTestCaseFixture,
    patch,
    unittest,
)


class SystemConfigServiceTestCase(_SystemConfigServiceTestCaseFixture, unittest.TestCase):
    def test_validate_reports_invalid_feishu_webhook_url(self) -> None:
        validation = self.service.validate(
            items=[{"key": "FEISHU_WEBHOOK_URL", "value": "feishu-hook-without-scheme"}]
        )
        self.assertFalse(validation["valid"])
        self.assertTrue(any(issue["code"] == "invalid_url" for issue in validation["issues"]))

    def test_validate_reports_ntfy_url_without_topic(self) -> None:
        validation = self.service.validate(
            items=[{"key": "NTFY_URL", "value": "https://ntfy.sh"}]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(
            any(
                issue["key"] == "NTFY_URL" and issue["code"] == "invalid_ntfy_url"
                for issue in validation["issues"]
            )
        )

    def test_validate_reports_gotify_url_with_message_endpoint(self) -> None:
        validation = self.service.validate(
            items=[{"key": "GOTIFY_URL", "value": "https://gotify.example/message"}]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(
            any(
                issue["key"] == "GOTIFY_URL" and issue["code"] == "invalid_gotify_url"
                for issue in validation["issues"]
            )
        )

    def test_validate_reports_invalid_notification_quiet_hours(self) -> None:
        validation = self.service.validate(
            items=[{"key": "NOTIFICATION_QUIET_HOURS", "value": "9:00-18:00"}]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(
            any(
                issue["key"] == "NOTIFICATION_QUIET_HOURS"
                and issue["code"] == "invalid_format"
                for issue in validation["issues"]
            )
        )

    def test_validate_reports_invalid_notification_timezone(self) -> None:
        validation = self.service.validate(
            items=[{"key": "NOTIFICATION_TIMEZONE", "value": "Mars/Olympus"}]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(
            any(
                issue["key"] == "NOTIFICATION_TIMEZONE"
                and issue["code"] == "invalid_timezone"
                for issue in validation["issues"]
            )
        )

    def test_validate_reports_invalid_notification_min_severity(self) -> None:
        validation = self.service.validate(
            items=[{"key": "NOTIFICATION_MIN_SEVERITY", "value": "notice"}]
        )

        self.assertFalse(validation["valid"])
        self.assertTrue(
            any(
                issue["key"] == "NOTIFICATION_MIN_SEVERITY"
                and issue["code"] == "invalid_enum"
                for issue in validation["issues"]
            )
        )

    def test_validate_warns_when_feishu_app_credentials_are_used_without_webhook(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "FEISHU_APP_ID", "value": "cli_xxx"},
                {"key": "FEISHU_APP_SECRET", "value": "secret_xxx"},
            ]
        )
        self.assertTrue(validation["valid"])
        issue = next(
            issue
            for issue in validation["issues"]
            if issue["code"] == "feishu_mode_mismatch"
            and issue["severity"] == "warning"
        )
        self.assertEqual(issue["key"], "FEISHU_CHAT_ID")
        self.assertIn("FEISHU_CHAT_ID", issue["message"])
        self.assertIn("static notification:", issue["expected"])
        self.assertIn("event subscription:", issue["expected"])

    def test_validate_no_warning_when_feishu_cloud_doc_credentials_without_webhook(self) -> None:
        validation = self.service.validate(
            items=[
                {"key": "FEISHU_APP_ID", "value": "cli_xxx"},
                {"key": "FEISHU_APP_SECRET", "value": "secret_xxx"},
                {"key": "FEISHU_FOLDER_TOKEN", "value": "folder_xxx"},
            ]
        )
        self.assertTrue(validation["valid"])
        self.assertFalse(
            any(
                issue["code"] == "feishu_mode_mismatch"
                and issue["severity"] == "warning"
                for issue in validation["issues"]
            )
        )

    @patch.object(SystemConfigService, "_reload_runtime_singletons")
    def test_update_escapes_custom_webhook_template_and_runtime_reads_literals(
        self,
        _mock_reload_runtime_singletons,
    ) -> None:
        template = '{"title":$title_json,"content":$content_json}'

        response = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[{"key": "CUSTOM_WEBHOOK_BODY_TEMPLATE", "value": template}],
            reload_now=True,
        )

        self.assertTrue(response["success"])
        self.assertIn(
            'CUSTOM_WEBHOOK_BODY_TEMPLATE={"title":$$title_json,"content":$$content_json}\n',
            self.env_path.read_text(encoding="utf-8"),
        )
        self.assertEqual(Config.get_instance().custom_webhook_body_template, template)

        items = {
            item["key"]: item
            for item in self.service.get_config(include_schema=True)["items"]
        }
        self.assertEqual(items["CUSTOM_WEBHOOK_BODY_TEMPLATE"]["value"], template)

    @patch.object(SystemConfigService, "_reload_runtime_singletons")
    def test_update_escapes_braced_custom_webhook_template_and_runtime_reads_literals(
        self,
        _mock_reload_runtime_singletons,
    ) -> None:
        template = '{"content":${content_json}}'

        response = self.service.update(
            config_version=self.manager.get_config_version(),
            items=[{"key": "CUSTOM_WEBHOOK_BODY_TEMPLATE", "value": template}],
            reload_now=True,
        )

        self.assertTrue(response["success"])
        self.assertIn(
            'CUSTOM_WEBHOOK_BODY_TEMPLATE={"content":$${content_json}}\n',
            self.env_path.read_text(encoding="utf-8"),
        )
        self.assertEqual(Config.get_instance().custom_webhook_body_template, template)

        items = {
            item["key"]: item
            for item in self.service.get_config(include_schema=True)["items"]
        }
        self.assertEqual(items["CUSTOM_WEBHOOK_BODY_TEMPLATE"]["value"], template)
