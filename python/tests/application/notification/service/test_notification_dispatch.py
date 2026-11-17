"""Tests for notification dispatch."""

from tests.application.notification._notification_support import (
    AnalysisResult,
    NotificationChannel,
    NotificationService,
    _TestNotificationServiceReportGenerationFixture,
    _TestNotificationServiceSendToMethodsFixture,
    _attach_decision_signal_summary,
    _make_config,
    _make_dingtalk_message,
    _make_feishu_message,
    _make_response,
    _make_telegram_message,
    mock,
    unittest,
)


class TestNotificationServiceSendToMethods(_TestNotificationServiceSendToMethodsFixture, unittest.TestCase):
    @mock.patch("src.application.notification.notification.get_config")
    def test_no_channels_service_unavailable_and_send_returns_false(self, mock_get_config):
        mock_get_config.return_value = _make_config()

        service = NotificationService()

        self.assertFalse(service.is_available())
        result = service.send("test content")
        self.assertFalse(result)

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_astrbot_via_notification_service(self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock):
        cfg = _make_config(astrbot_url="https://astrbot.example")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200)

        service = NotificationService()
        self.assertIn(NotificationChannel.ASTRBOT, service.get_available_channels())

        ok = service.send("astrbot content")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_custom_webhook_via_notification_service(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(custom_webhook_urls=["https://example.com/webhook"])
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200)

        service = NotificationService()
        self.assertIn(NotificationChannel.CUSTOM, service.get_available_channels())

        ok = service.send("custom content")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.application.notification.notification.get_config")
    def test_send_isolates_channel_exceptions(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            wechat_webhook_url="https://wechat.example/hook",
            custom_webhook_urls=["https://example.com/webhook"],
        )
        mock_get_config.return_value = cfg

        service = NotificationService()
        self.assertIn(NotificationChannel.WECHAT, service.get_available_channels())
        self.assertIn(NotificationChannel.CUSTOM, service.get_available_channels())

        with mock.patch.object(service, "send_to_wechat", side_effect=RuntimeError("boom")), \
             mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom:
            ok = service.send("content")

        self.assertTrue(ok)
        mock_custom.assert_called_once_with("content")

    @mock.patch("src.application.notification.notification.get_config")
    def test_send_with_results_reports_per_channel_attempts(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            wechat_webhook_url="https://wechat.example/hook",
            custom_webhook_urls=["https://example.com/webhook"],
        )
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch.object(service, "send_to_wechat", side_effect=RuntimeError("token=secret-token failed")), \
             mock.patch.object(service, "send_to_custom", return_value=True):
            result = service.send_with_results("content")

        self.assertTrue(result.dispatched)
        self.assertTrue(result.success)
        self.assertEqual(result.status, "partial_failed")
        by_channel = {item.channel: item for item in result.channel_results}
        self.assertFalse(by_channel["wechat"].success)
        self.assertEqual(by_channel["wechat"].error_code, "exception")
        self.assertNotIn("secret-token", by_channel["wechat"].diagnostics)
        self.assertTrue(by_channel["custom"].success)

    @mock.patch("src.application.notification.notification.get_config")
    def test_send_with_results_reports_route_no_channel(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            custom_webhook_urls=["https://example.com/webhook"],
            notification_report_channels=["unknown-route-channel"],
        )
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom:
            result = service.send_with_results("content", route_type="report")

        self.assertFalse(result.dispatched)
        self.assertFalse(result.success)
        self.assertEqual(result.status, "no_channel")
        self.assertEqual(result.channel_results, [])
        mock_custom.assert_not_called()

    @mock.patch("src.application.notification.notification.get_config")
    def test_send_route_empty_keeps_all_configured_channels(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            wechat_webhook_url="https://wechat.example/hook",
            custom_webhook_urls=["https://example.com/webhook"],
        )
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch.object(service, "send_to_wechat", return_value=True) as mock_wechat, \
             mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom:
            ok = service.send("content", route_type="report")

        self.assertTrue(ok)
        mock_wechat.assert_called_once_with("content")
        mock_custom.assert_called_once_with("content")

    @mock.patch("src.application.notification.notification.get_config")
    def test_send_report_route_filters_static_channels(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            wechat_webhook_url="https://wechat.example/hook",
            custom_webhook_urls=["https://example.com/webhook"],
            notification_report_channels=["custom"],
        )
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch.object(service, "send_to_wechat", return_value=True) as mock_wechat, \
             mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom:
            ok = service.send("content", route_type="report")

        self.assertTrue(ok)
        mock_wechat.assert_not_called()
        mock_custom.assert_called_once_with("content")

    @mock.patch("src.application.notification.notification.get_config")
    def test_send_route_with_no_matching_channel_does_not_fallback(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            custom_webhook_urls=["https://example.com/webhook"],
            notification_report_channels=["unknown-route-channel"],
        )
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom:
            ok = service.send("content", route_type="report")

        self.assertFalse(ok)
        mock_custom.assert_not_called()

    @mock.patch("src.application.notification.notification.get_config")
    def test_send_to_context_is_not_limited_by_route(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            custom_webhook_urls=["https://example.com/webhook"],
            notification_report_channels=["telegram"],
        )
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch.object(service, "send_to_context", return_value=True) as mock_context, \
             mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom:
            ok = service.send("content", route_type="report")

        self.assertTrue(ok)
        mock_context.assert_called_once_with("content")
        mock_custom.assert_not_called()

    @mock.patch("src.application.notification.notification.get_config")
    def test_feishu_context_response_skips_static_webhook(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            feishu_webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/test-token",
            feishu_app_id="cli_test",
            feishu_app_secret="app-secret",
        )
        mock_get_config.return_value = cfg
        service = NotificationService(source_message=_make_feishu_message())

        with mock.patch.object(service, "_send_feishu_stream_reply", return_value=True) as mock_reply, \
             mock.patch.object(service, "send_to_feishu", return_value=True) as mock_webhook:
            result = service.send_with_results("content", route_type="report")

        self.assertTrue(result.dispatched)
        self.assertTrue(result.success)
        self.assertEqual(result.status, "sent")
        self.assertEqual([item.channel for item in result.channel_results], ["__context__"])
        mock_reply.assert_called_once_with("chat-1", "content")
        mock_webhook.assert_not_called()

    @mock.patch("src.application.notification.notification.get_config")
    def test_feishu_context_failure_does_not_fallback_to_static_webhook(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            feishu_webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/test-token",
            feishu_app_id="cli_test",
            feishu_app_secret="app-secret",
        )
        mock_get_config.return_value = cfg
        service = NotificationService(source_message=_make_feishu_message())

        with mock.patch.object(service, "_send_feishu_stream_reply", return_value=False), \
             mock.patch.object(service, "send_to_feishu", return_value=True) as mock_webhook:
            result = service.send_with_results("content", route_type="report")

        self.assertTrue(result.dispatched)
        self.assertFalse(result.success)
        self.assertEqual(result.status, "all_failed")
        self.assertEqual([item.channel for item in result.channel_results], ["__context__"])
        mock_webhook.assert_not_called()

    @mock.patch("src.application.notification.notification.get_config")
    def test_dingtalk_context_response_skips_static_webhook(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            feishu_webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/test-token",
            dingtalk_app_key="dingtalk-key",
            dingtalk_app_secret="dingtalk-secret",
            wechat_webhook_url="https://wechat.example/hook",
        )
        mock_get_config.return_value = cfg
        service = NotificationService(source_message=_make_dingtalk_message())

        with mock.patch.object(service, "_send_dingtalk_chunked", return_value=True) as mock_dingtalk, \
             mock.patch.object(service, "send_to_wechat", return_value=True) as mock_wechat:
            result = service.send_with_results("content", route_type="report")

        self.assertTrue(result.dispatched)
        self.assertTrue(result.success)
        self.assertEqual([item.channel for item in result.channel_results], ["__context__"])
        mock_dingtalk.assert_called_once_with("https://oapi.dingtalk.com/robot/sendBySession?session=abc123", "content", max_bytes=20000)
        mock_wechat.assert_not_called()

    @mock.patch("src.application.notification.notification.get_config")
    def test_telegram_context_response_skips_static_webhook(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            telegram_bot_token="TOKEN",
            telegram_chat_id="123456",
            wechat_webhook_url="https://wechat.example/hook",
        )
        mock_get_config.return_value = cfg
        service = NotificationService(source_message=_make_telegram_message())

        with mock.patch.object(service, "send_to_telegram", return_value=True) as mock_telegram, \
             mock.patch.object(service, "send_to_wechat", return_value=True) as mock_wechat:
            result = service.send_with_results("content", route_type="report")

        self.assertTrue(result.dispatched)
        self.assertTrue(result.success)
        self.assertEqual([item.channel for item in result.channel_results], ["__context__"])
        mock_telegram.assert_called_once_with("content", chat_id="100200300")
        mock_wechat.assert_not_called()

    @mock.patch("src.application.notification.notification.get_config")
    def test_feishu_webhook_still_sends_without_source_context(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            feishu_webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/test-token",
            feishu_app_id="cli_test",
            feishu_app_secret="app-secret",
        )
        mock_get_config.return_value = cfg
        service = NotificationService()

        with mock.patch.object(service, "send_to_feishu", return_value=True) as mock_webhook:
            result = service.send_with_results("content", route_type="report")

        self.assertTrue(result.dispatched)
        self.assertTrue(result.success)
        self.assertEqual([item.channel for item in result.channel_results], ["feishu"])
        mock_webhook.assert_called_once_with("content")

    @mock.patch("src.application.notification.notification.get_config")
    def test_feishu_send_as_file_route_report_calls_send_feishu_file(self, mock_get_config):
        """When FEISHU_SEND_AS_FILE=true and route_type=report, use file sending."""
        cfg = _make_config(
            feishu_webhook_url="https://feishu.example/hook",
            feishu_send_as_file=True,
        )
        mock_get_config.return_value = cfg
        service = NotificationService()
        with mock.patch.object(service, "send_feishu_file", return_value=True) as mock_file, \
             mock.patch.object(service, "save_report_to_file", return_value="/tmp/report.md"):
            result = service.send_with_results("report content", route_type="report")
        self.assertTrue(result.success)
        mock_file.assert_called_once()

    @mock.patch("src.application.notification.notification.get_config")
    def test_feishu_send_as_file_route_alert_calls_send_to_feishu(self, mock_get_config):
        """When FEISHU_SEND_AS_FILE=true but route_type=alert, use text sending."""
        cfg = _make_config(
            feishu_webhook_url="https://feishu.example/hook",
            feishu_send_as_file=True,
        )
        mock_get_config.return_value = cfg
        service = NotificationService()
        with mock.patch.object(service, "send_to_feishu", return_value=True) as mock_text, \
             mock.patch.object(service, "save_report_to_file") as mock_save:
            result = service.send_with_results("alert content", route_type="alert")
        self.assertTrue(result.success)
        mock_text.assert_called_once_with("alert content")
        mock_save.assert_not_called()

    @mock.patch("src.application.notification.notification.get_config")
    def test_feishu_send_as_file_route_none_uses_text(self, mock_get_config):
        """When FEISHU_SEND_AS_FILE=true and route_type=None, use text (not file)."""
        cfg = _make_config(
            feishu_webhook_url="https://feishu.example/hook",
            feishu_send_as_file=True,
        )
        mock_get_config.return_value = cfg
        service = NotificationService()
        with mock.patch.object(service, "send_to_feishu", return_value=True) as mock_text, \
             mock.patch.object(service, "save_report_to_file") as mock_save:
            result = service.send_with_results("report content")
        self.assertTrue(result.success)
        mock_text.assert_called_once_with("report content")
        mock_save.assert_not_called()

    @mock.patch("src.application.notification.notification.get_config")
    def test_feishu_send_as_file_false_uses_text_even_for_report(self, mock_get_config):
        """When FEISHU_SEND_AS_FILE=false (default), report still uses text."""
        cfg = _make_config(
            feishu_webhook_url="https://feishu.example/hook",
            feishu_send_as_file=False,
        )
        mock_get_config.return_value = cfg
        service = NotificationService()
        with mock.patch.object(service, "send_to_feishu", return_value=True) as mock_text, \
             mock.patch.object(service, "save_report_to_file") as mock_save:
            result = service.send_with_results("report content", route_type="report")
        self.assertTrue(result.success)
        mock_text.assert_called_once_with("report content")
        mock_save.assert_not_called()

    @mock.patch("src.application.notification.notification.get_config")
    def test_feishu_send_as_file_alert_does_not_leak_into_other_channels(self, mock_get_config):
        """FEISHU_SEND_AS_FILE only affects Feishu, not other channels."""
        cfg = _make_config(
            feishu_webhook_url="https://feishu.example/hook",
            custom_webhook_urls=["https://example.com/hook"],
            feishu_send_as_file=True,
        )
        mock_get_config.return_value = cfg
        service = NotificationService()
        with mock.patch.object(service, "send_feishu_file", return_value=True) as mock_file, \
             mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom, \
             mock.patch.object(service, "save_report_to_file", return_value="/tmp/report.md"):
            result = service.send_with_results("content", route_type="report")
        self.assertTrue(result.success)
        mock_file.assert_called_once()
        mock_custom.assert_called_once_with("content")

    @mock.patch("src.application.notification.notification.get_config")
    def test_feishu_send_as_file_system_error_uses_text(self, mock_get_config):
        """FEISHU_SEND_AS_FILE does not activate for system_error routes."""
        cfg = _make_config(
            feishu_webhook_url="https://feishu.example/hook",
            feishu_send_as_file=True,
        )
        mock_get_config.return_value = cfg
        service = NotificationService()
        with mock.patch.object(service, "send_to_feishu", return_value=True) as mock_text, \
             mock.patch.object(service, "save_report_to_file") as mock_save:
            result = service.send_with_results("error", route_type="system_error")
        self.assertTrue(result.success)
        mock_text.assert_called_once_with("error")
        mock_save.assert_not_called()

    @mock.patch("src.application.notification.notification.get_config")
    def test_send_dedup_suppresses_static_channels_after_success(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            custom_webhook_urls=["https://example.com/webhook"],
            notification_dedup_ttl_seconds=60,
        )
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom:
            self.assertTrue(service.send("content at 12:00", route_type="report", dedup_key="report:aggregate:simple:600519"))
            self.assertFalse(service.send("content at 12:01", route_type="report", dedup_key="report:aggregate:simple:600519"))

        mock_custom.assert_called_once_with("content at 12:00")

    @mock.patch("src.application.notification.notification.get_config")
    def test_send_releases_noise_reservation_when_static_channels_fail(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            custom_webhook_urls=["https://example.com/webhook"],
            notification_dedup_ttl_seconds=60,
        )
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch.object(service, "send_to_custom", side_effect=[False, True]) as mock_custom:
            self.assertFalse(
                service.send(
                    "content at 12:00",
                    route_type="report",
                    dedup_key="report:aggregate:simple:600519",
                )
            )
            self.assertTrue(
                service.send(
                    "content at 12:01",
                    route_type="report",
                    dedup_key="report:aggregate:simple:600519",
                )
            )

        self.assertEqual(mock_custom.call_count, 2)

    @mock.patch("src.application.notification.notification.get_config")
    def test_send_to_context_is_not_limited_by_noise_controls(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            custom_webhook_urls=["https://example.com/webhook"],
            notification_dedup_ttl_seconds=60,
        )
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch.object(service, "send_to_context", return_value=True) as mock_context, \
             mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom:
            self.assertTrue(service.send("content at 12:00", route_type="report", dedup_key="report:aggregate:simple:600519"))
            self.assertTrue(service.send("content at 12:01", route_type="report", dedup_key="report:aggregate:simple:600519"))

        self.assertEqual(mock_context.call_count, 2)
        mock_custom.assert_called_once_with("content at 12:00")

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_discord_via_notification_service_with_webhook(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(discord_webhook_url="https://discord.example/webhook")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(204)

        service = NotificationService()
        self.assertIn(NotificationChannel.DISCORD, service.get_available_channels())

        ok = service.send("discord content")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_discord_via_notification_service_with_bot(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(discord_bot_token="TOKEN", discord_main_channel_id="123")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200)

        service = NotificationService()
        self.assertIn(NotificationChannel.DISCORD, service.get_available_channels())

        ok = service.send("discord content")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("src.infrastructure.notification.senders.discord_sender.time.sleep", return_value=None)
    @mock.patch("requests.post")
    def test_send_to_discord_via_notification_service_with_bot_requires_chunking(
        self,
        mock_post: mock.MagicMock,
        _mock_sleep: mock.MagicMock,
        mock_get_config: mock.MagicMock,
    ):
        cfg = _make_config(
            discord_bot_token="TOKEN",
            discord_main_channel_id="123",
            discord_max_words=2000,
        )
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200)

        service = NotificationService()
        self.assertIn(NotificationChannel.DISCORD, service.get_available_channels())

        ok = service.send("A" * 6000)

        self.assertTrue(ok)
        self.assertAlmostEqual(mock_post.call_count, 4, delta=1)


class TestNotificationServiceReportGeneration(_TestNotificationServiceReportGenerationFixture, unittest.TestCase):
    @mock.patch("src.application.notification.notification.get_config")
    def test_generate_wechat_dashboard_omits_decision_signal_excerpt_fallback(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        result = _attach_decision_signal_summary(AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
        ))

        for summary_only in (True, False):
            service = NotificationService()
            service._report_summary_only = summary_only
            out = service.generate_wechat_dashboard([result])
            self.assertNotIn("AI 决策信号", out)
            self.assertNotIn("理由: 技术面走弱", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_generate_wechat_summary_omits_decision_signal_excerpt(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = _attach_decision_signal_summary(AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
        ))

        out = service.generate_wechat_summary([result])

        self.assertNotIn("AI 决策信号", out)
        self.assertNotIn("动作: 卖出", out)

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("smtplib.SMTP_SSL")
    def test_send_to_email_via_notification_service(
        self, mock_smtp_ssl: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(
            email_sender="user@qq.com",
            email_password="PASS",
            email_receivers=["default@example.com"],
        )
        mock_get_config.return_value = cfg

        service = NotificationService()
        self.assertIn(NotificationChannel.EMAIL, service.get_available_channels())

        ok = service.send("email content")

        self.assertTrue(ok)
        mock_smtp_ssl.assert_called_once()
        mock_smtp_ssl.return_value.send_message.assert_called_once()

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("smtplib.SMTP_SSL")
    def test_send_to_email_with_stock_group_routing(
        self, mock_smtp_ssl: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(
            email_sender="user@qq.com",
            email_password="PASS",
            email_receivers=["default@example.com"],
            stock_email_groups=[(["000001", "600519"], ["group@example.com"])],
        )
        mock_get_config.return_value = cfg

        service = NotificationService()
        self.assertIn(NotificationChannel.EMAIL, service.get_available_channels())

        server = mock_smtp_ssl.return_value

        ok = service.send("content", email_stock_codes=["000001"])

        self.assertTrue(ok)
        mock_smtp_ssl.assert_called_once()
        server.send_message.assert_called_once()
        msg = server.send_message.call_args[0][0]
        self.assertIn("group@example.com", msg["To"])

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_feishu_via_notification_service(self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock):
        cfg = _make_config(feishu_webhook_url="https://feishu.example")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200, {"code": 0})

        service = NotificationService()
        self.assertIn(NotificationChannel.FEISHU, service.get_available_channels())

        ok = service.send("hello feishu")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_feishu_via_notification_service_requires_chunking(self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock):
        cfg = _make_config(feishu_webhook_url="https://feishu.example", feishu_max_bytes=2000)
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200, {"code": 0})

        service = NotificationService()
        self.assertIn(NotificationChannel.FEISHU, service.get_available_channels())

        ok = service.send("A" * 6000)

        self.assertTrue(ok)
        self.assertAlmostEqual(mock_post.call_count, 4, delta=1)

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_gotify_via_notification_service(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(gotify_url="https://gotify.example", gotify_token="secret-token")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200)

        service = NotificationService()
        self.assertIn(NotificationChannel.GOTIFY, service.get_available_channels())

        ok = service.send("gotify content")

        self.assertTrue(ok)
        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args.args[0], "https://gotify.example/message")
        self.assertEqual(mock_post.call_args.kwargs["headers"]["X-Gotify-Key"], "secret-token")
        self.assertEqual(mock_post.call_args.kwargs["json"]["message"], "gotify content")
        self.assertEqual(
            mock_post.call_args.kwargs["json"]["extras"]["client::display"]["contentType"],
            "text/markdown",
        )

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_gotify_does_not_trigger_markdown_to_image(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(
            gotify_url="https://gotify.example",
            gotify_token="secret-token",
            markdown_to_image_channels=["gotify"],
        )
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200)

        service = NotificationService()
        with mock.patch("src.infrastructure.reporting.img_render.markdown_to_image", return_value=b"png") as mock_md2img:
            ok = service.send("gotify content")

        self.assertTrue(ok)
        mock_md2img.assert_not_called()
        mock_post.assert_called_once()

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_ntfy_via_notification_service(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(ntfy_url="https://ntfy.sh/hrs-topic")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200)

        service = NotificationService()
        self.assertIn(NotificationChannel.NTFY, service.get_available_channels())

        ok = service.send("ntfy content")

        self.assertTrue(ok)
        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args.args[0], "https://ntfy.sh")
        self.assertEqual(mock_post.call_args.kwargs["json"]["topic"], "hrs-topic")

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_ntfy_does_not_trigger_markdown_to_image(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(
            ntfy_url="https://ntfy.sh/hrs-topic",
            markdown_to_image_channels=["ntfy"],
        )
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200)

        service = NotificationService()
        with mock.patch("src.infrastructure.reporting.img_render.markdown_to_image", return_value=b"png") as mock_md2img:
            ok = service.send("ntfy content")

        self.assertTrue(ok)
        mock_md2img.assert_not_called()
        mock_post.assert_called_once()

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_pushover_via_notification_service(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(
            pushover_user_key="USER",
            pushover_api_token="TOKEN",
        )
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200, {"status": 1})

        service = NotificationService()
        self.assertIn(NotificationChannel.PUSHOVER, service.get_available_channels())

        ok = service.send("pushover content")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_pushplus_via_notification_service(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(pushplus_token="TOKEN")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200, {"code": 200})

        service = NotificationService()
        self.assertIn(NotificationChannel.PUSHPLUS, service.get_available_channels())

        ok = service.send("pushplus content")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.infrastructure.notification.senders.pushplus_sender.time.sleep")
    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_pushplus_via_notification_service_requires_chunking(
        self,
        mock_post: mock.MagicMock,
        mock_get_config: mock.MagicMock,
        _mock_sleep: mock.MagicMock,
    ):
        cfg = _make_config(pushplus_token="TOKEN")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200, {"code": 200})

        service = NotificationService()
        self.assertIn(NotificationChannel.PUSHPLUS, service.get_available_channels())

        ok = service.send("A" * 25000)

        self.assertTrue(ok)
        self.assertGreaterEqual(mock_post.call_count, 2)

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_slack_via_notification_service_with_webhook(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(slack_webhook_url="https://hooks.slack.com/services/T/B/xxx")
        mock_get_config.return_value = cfg
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.text = "ok"
        mock_post.return_value = resp

        service = NotificationService()
        self.assertIn(NotificationChannel.SLACK, service.get_available_channels())

        ok = service.send("slack content")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_slack_via_notification_service_with_bot(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(slack_bot_token="xoxb-test", slack_channel_id="C123")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200, {"ok": True})

        service = NotificationService()
        self.assertIn(NotificationChannel.SLACK, service.get_available_channels())

        ok = service.send("slack bot content")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_serverchan3_via_notification_service(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(serverchan3_sendkey="SCTKEY")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200, {"code": 0})

        service = NotificationService()
        self.assertIn(NotificationChannel.SERVERCHAN3, service.get_available_channels())

        ok = service.send("serverchan content")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_telegram_via_notification_service(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(telegram_bot_token="TOKEN", telegram_chat_id="123")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200, {"ok": True})

        service = NotificationService()
        self.assertIn(NotificationChannel.TELEGRAM, service.get_available_channels())

        ok = service.send("hello telegram")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_wechat_via_notification_service(self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock):
        cfg = _make_config(wechat_webhook_url="https://wechat.example")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200, {"errcode": 0})

        service = NotificationService()
        self.assertIn(NotificationChannel.WECHAT, service.get_available_channels())

        ok = service.send("hello wechat")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_wechat_via_notification_service_requires_chunking(self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock):
        cfg = _make_config(wechat_webhook_url="https://wechat.example", wechat_max_bytes=2000)
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200, {"errcode": 0})

        service = NotificationService()
        self.assertIn(NotificationChannel.WECHAT, service.get_available_channels())

        ok = service.send("A" * 6000)

        self.assertTrue(ok)
        self.assertAlmostEqual(mock_post.call_count, 4, delta=1)
