"""Tests for agent pipeline results context."""

from tests.application.agent._agent_pipeline_support import (
    _TestAgentResultConversionFixture,
    unittest,
)


class TestAgentResultConversion(_TestAgentResultConversionFixture, unittest.TestCase):
    def test_convert_placeholder_dashboard_is_completed_from_local_context(self):
        """Placeholder dashboard blocks should be completed without falling back to neutral defaults."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.application.analysis.analyzer import check_content_integrity
        from src.domain.shared.enums import ReportType
        from src.domain.analysis.stock_analyzer import BuySignal, TrendAnalysisResult, TrendStatus

        agent_result = AgentResult(
            success=True,
            content="{}",
            dashboard={
                "stock_name": "贵州茅台",
                "dashboard": {
                    "core_conclusion": {"one_sentence": "待补充"},
                    "intelligence": {},
                    "battle_plan": {"sniper_points": {"stop_loss": ""}},
                },
            },
            provider="gemini",
        )
        trend_result = TrendAnalysisResult(
            code="600519",
            trend_status=TrendStatus.BULL,
            buy_signal=BuySignal.BUY,
            signal_score=62,
            risk_factors=["趋势跌破支撑需减仓"],
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result,
            "600519",
            "贵州茅台",
            ReportType.SIMPLE,
            "q-placeholder-dashboard",
            trend_result=trend_result,
        )

        ok, missing = check_content_integrity(result)
        self.assertTrue(ok, missing)
        self.assertEqual(result.sentiment_score, 62)
        self.assertEqual(result.dashboard["sentiment_score"], 62)
        self.assertEqual(result.dashboard["core_conclusion"]["one_sentence"], result.analysis_summary)
        self.assertEqual(result.dashboard["intelligence"]["risk_alerts"], ["趋势跌破支撑需减仓"])
        self.assertEqual(result.dashboard["battle_plan"]["sniper_points"]["stop_loss"], "待补充")

    def test_convert_uses_dashboard_stock_name_when_input_is_placeholder(self):
        """When input name is placeholder-like, prefer dashboard stock_name."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.domain.shared.enums import ReportType

        agent_result = AgentResult(
            success=True,
            content="{}",
            dashboard={
                "stock_name": "科创芯片ETF",
                "sentiment_score": 75,
                "trend_prediction": "震荡偏多",
                "operation_advice": "持有",
                "decision_type": "hold",
            },
            provider="gemini",
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result, "588200", "股票588200", ReportType.SIMPLE, "q-placeholder"
        )
        self.assertEqual(result.name, "科创芯片ETF")

    def test_convert_keeps_input_stock_name_when_valid(self):
        """When input name is already valid, do not overwrite with dashboard value."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.domain.shared.enums import ReportType

        agent_result = AgentResult(
            success=True,
            content="{}",
            dashboard={
                "stock_name": "错误名称",
                "sentiment_score": 70,
                "trend_prediction": "看多",
                "operation_advice": "持有",
                "decision_type": "hold",
            },
            provider="gemini",
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result, "600519", "贵州茅台", ReportType.SIMPLE, "q-valid"
        )
        self.assertEqual(result.name, "贵州茅台")
