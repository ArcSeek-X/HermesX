"""Tests for notification signals."""

from tests.application.notification._notification_support import (
    AnalysisResult,
    NotificationBuilder,
    NotificationService,
    _TestNotificationServiceReportGenerationFixture,
    _make_config,
    mock,
    unittest,
)


class TestNotificationServiceReportGeneration(_TestNotificationServiceReportGenerationFixture, unittest.TestCase):
    def test_signal_metadata_uses_resolved_eight_state_action(self):
        service = NotificationService()
        cases = [
            ("avoid", "Avoid", 90, ("Avoid", "🟡", "hold")),
            ("add", "Add", 50, ("Add", "🟢", "buy")),
            ("alert", "Alert", 85, ("Alert", "🔴", "sell")),
        ]

        for action, action_label, score, expected in cases:
            with self.subTest(action=action):
                result = AnalysisResult(
                    code="AAPL",
                    name="Apple",
                    sentiment_score=score,
                    trend_prediction="Neutral",
                    operation_advice="Hold",
                    report_language="en",
                    action=action,
                    action_label=action_label,
                )

                self.assertEqual(service._get_signal_level(result), expected)

    def test_build_stock_summary_uses_resolved_eight_state_action(self):
        summary = NotificationBuilder.build_stock_summary(
            [
                AnalysisResult(
                    code="AVOID",
                    name="Avoid Corp",
                    sentiment_score=90,
                    trend_prediction="Neutral",
                    operation_advice="Avoid",
                    report_language="en",
                    action="avoid",
                    action_label="Avoid",
                ),
                AnalysisResult(
                    code="ALERT",
                    name="Alert Corp",
                    sentiment_score=85,
                    trend_prediction="Neutral",
                    operation_advice="Alert",
                    report_language="en",
                    action="alert",
                    action_label="Alert",
                ),
                AnalysisResult(
                    code="ADD",
                    name="Add Corp",
                    sentiment_score=50,
                    trend_prediction="Neutral",
                    operation_advice="Add",
                    report_language="en",
                    action="add",
                    action_label="Add",
                ),
            ]
        )

        self.assertIn("🟡 Avoid Corp(AVOID): Avoid | Score 90", summary)
        self.assertIn("🔴 Alert Corp(ALERT): Alert | Score 85", summary)
        self.assertIn("🟢 Add Corp(ADD): Add | Score 50", summary)
        self.assertNotIn("Buy | Score 50", summary)
        self.assertNotIn("Strong Buy", summary)

    @mock.patch("src.application.notification.notification.get_config")
    def test_related_boards_drops_signal_columns_when_no_sector_data(
        self, mock_get_config: mock.MagicMock
    ):
        """HK/US lack 板块涨跌榜 — drop status / change_pct columns entirely."""
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="AAPL",
            name="Apple Inc.",
            sentiment_score=64,
            trend_prediction="震荡",
            operation_advice="观望",
            analysis_summary="观望等待 AI 兑现节奏。",
        )
        result.fundamental_context = {
            "earnings": {"status": "ok", "data": {
                "financial_report": {
                    "report_date": "2026-03-31",
                    "revenue": 1.11e11,
                    "currency": "USD",
                },
            }},
            "growth": {"status": "ok", "data": {"revenue_yoy": 16.60}},
            "belong_boards": [
                {"name": "Technology", "type": "行业"},
                {"name": "Consumer Electronics", "type": "概念"},
            ],
        }

        out = service.generate_single_stock_report(result)

        self.assertIn("关联板块", out)
        self.assertIn("Technology / Consumer Electronics", out)
        self.assertIn("Technology", out)
        self.assertIn("Consumer Electronics", out)
        # When no sector ranking data is available, drop the 4-col layout.
        self.assertNotIn("板块表现", out)
        self.assertNotIn("板块涨跌幅", out)
        # And no table/type noise either.
        self.assertNotIn("| 板块 | 类型 |", out)
        self.assertNotIn("| -- | -- |", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_related_boards_ignores_matching_signal_without_change_pct(
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
            "boards": {"status": "ok", "data": {
                "top": [{"name": "白酒"}],
                "bottom": [],
            }},
            "belong_boards": [
                {"name": "白酒", "code": "BK0596", "type": "行业"},
            ],
        }

        out = service.generate_single_stock_report(result)

        self.assertIn("关联板块", out)
        self.assertIn("白酒", out)
        self.assertNotIn("| 白酒 | 行业 |", out)
        self.assertNotIn("领涨", out)
        self.assertNotIn("板块涨跌幅", out)
