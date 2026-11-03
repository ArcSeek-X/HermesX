"""Tests for notification contracts."""

from tests.application.notification._notification_support import (
    AnalysisResult,
    NotificationChannel,
    NotificationService,
    _TestNotificationServiceReportGenerationFixture,
    _TestNotificationServiceSendToMethodsFixture,
    _make_config,
    mock,
    unittest,
)


class TestNotificationServiceSendToMethods(_TestNotificationServiceSendToMethodsFixture, unittest.TestCase):
    @mock.patch("src.application.notification.notification.get_config")
    def test_send_alert_and_system_error_routes_filter_independently(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            wechat_webhook_url="https://wechat.example/hook",
            custom_webhook_urls=["https://example.com/webhook"],
            notification_alert_channels=["wechat"],
            notification_system_error_channels=["custom"],
        )
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch.object(service, "send_to_wechat", return_value=True) as mock_wechat, \
             mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom:
            self.assertTrue(service.send("alert", route_type="alert"))
            self.assertTrue(service.send("system", route_type="system_error"))

        mock_wechat.assert_called_once_with("alert")
        mock_custom.assert_called_once_with("system")

    @mock.patch("src.application.notification.notification.get_config")
    def test_noise_check_failure_does_not_block_static_send(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(custom_webhook_urls=["https://example.com/webhook"])
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch("src.application.notification.noise._evaluate_notification_noise", side_effect=RuntimeError("boom")), \
             mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom:
            ok = service.send("content", route_type="report")

        self.assertTrue(ok)
        mock_custom.assert_called_once_with("content")


class TestNotificationServiceReportGeneration(_TestNotificationServiceReportGenerationFixture, unittest.TestCase):
    @mock.patch("src.application.notification.notification.get_config")
    def test_related_boards_uses_concept_rankings_for_concept_boards(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
        )
        result.fundamental_context = {
            "boards": {"status": "ok", "data": {
                "top": [{"name": "白酒", "change_pct": 2.31}],
                "bottom": [],
            }},
            "concept_boards": {"status": "ok", "data": {
                "top": [],
                "bottom": [{"name": "白酒", "change_pct": -3.2}],
            }},
            "belong_boards": [{"name": "白酒", "type": "概念"}],
        }

        out = service.generate_single_stock_report(result)

        self.assertIn("关联板块", out)
        self.assertIn("- 白酒 (概念板块 领跌 -3.20%)", out)
        self.assertNotIn("| 白酒 | 概念 |", out)
        self.assertNotIn("+2.31%", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_related_boards_without_type_infers_concepts_and_keeps_unknowns(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
        )
        result.fundamental_context = {
            "earnings": {"status": "ok", "data": {}},
            "growth": {"status": "ok", "data": {}},
            "belong_boards": [
                {"name": "白酒Ⅲ"},
                {"name": "白酒Ⅱ"},
                {"name": "食品饮料"},
                {"name": "贵州板块"},
                {"name": "酿酒概念"},
            ],
        }

        out = service.generate_single_stock_report(result)

        self.assertIn("关联板块", out)
        self.assertIn("白酒Ⅲ / 白酒Ⅱ / 食品饮料 / 贵州板块 / 酿酒概念", out)
        self.assertNotIn("| 板块 | 类型 |", out)
        self.assertNotIn("| 白酒Ⅲ | N/A |", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_dividend_currency_falls_back_to_financial_when_missing(
        self, mock_get_config: mock.MagicMock
    ):
        """A-share AkShare payload has no dividend.currency — fall back to financial_report.currency."""
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
        )
        result.fundamental_context = {
            "earnings": {
                "status": "ok",
                "data": {
                    "financial_report": {"report_date": "2026-03-31", "revenue": 4.5e10},
                    "dividend": {
                        "events": [{"event_date": "2025-06-20", "ex_dividend_date": "2025-06-20"}],
                        "ttm_event_count": 1,
                        "ttm_cash_dividend_per_share": 27.6,
                    },
                },
            },
        }

        out = service.generate_single_stock_report(result)

        # Without explicit dividend currency, default to 元 (matches AkShare A-share semantics).
        self.assertIn("27.6000 元", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_history_compare_context_uses_cache(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(report_history_compare_n=3)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
            query_id="q-1",
        )

        with mock.patch(
            "src.application.history.comparison.get_signal_changes_batch",
            return_value={"600519": []},
        ) as mock_batch:
            first = service._get_history_compare_context([result])
            second = service._get_history_compare_context([result])

        self.assertEqual(first, {"history_by_code": {"600519": []}})
        self.assertEqual(second, {"history_by_code": {"600519": []}})
        mock_batch.assert_called_once()

    @mock.patch("src.application.notification.notification.get_config")
    def test_gotify_without_token_is_not_available(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(gotify_url="https://gotify.example")

        service = NotificationService()

        self.assertNotIn(NotificationChannel.GOTIFY, service.get_available_channels())
        self.assertFalse(service.is_available())

    @mock.patch("src.application.notification.notification.get_config")
    def test_gotify_blank_token_is_not_available(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(
            gotify_url="https://gotify.example",
            gotify_token="   ",
        )

        service = NotificationService()

        self.assertNotIn(NotificationChannel.GOTIFY, service.get_available_channels())
        self.assertFalse(service.is_available())

    @mock.patch("src.application.notification.notification.get_config")
    def test_gotify_message_endpoint_is_not_available(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(
            gotify_url="https://gotify.example/message",
            gotify_token="secret-token",
        )

        service = NotificationService()

        self.assertNotIn(NotificationChannel.GOTIFY, service.get_available_channels())
        self.assertFalse(service.is_available())

    @mock.patch("src.application.notification.notification.get_config")
    def test_ntfy_url_without_topic_is_not_available(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(ntfy_url="https://ntfy.sh")

        service = NotificationService()

        self.assertNotIn(NotificationChannel.NTFY, service.get_available_channels())
        self.assertFalse(service.is_available())

    @mock.patch("src.application.notification.notification.get_config")
    def test_ntfy_url_with_unsupported_scheme_is_not_available(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(ntfy_url="ntfy://ntfy.sh/hrs-topic")

        service = NotificationService()

        self.assertNotIn(NotificationChannel.NTFY, service.get_available_channels())
        self.assertFalse(service.is_available())
