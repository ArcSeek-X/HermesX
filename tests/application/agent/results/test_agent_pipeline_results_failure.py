"""Tests for agent pipeline results failure."""

from tests.application.agent._agent_pipeline_support import (
    _TestAgentResultConversionFixture,
    unittest,
)


class TestAgentResultConversion(_TestAgentResultConversionFixture, unittest.TestCase):
    def test_convert_failed_dashboard(self):
        """Failed AgentResult should produce a minimal AnalysisResult."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.domain.shared.enums import ReportType

        agent_result = AgentResult(
            success=False,
            content="",
            dashboard=None,
            error="Max steps exceeded",
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result, "600519", "贵州茅台", ReportType.SIMPLE, "q123"
        )

        self.assertIsNotNone(result)
        self.assertFalse(result.success)
        self.assertEqual(result.sentiment_score, 50)
        self.assertEqual(result.operation_advice, "观望")
        self.assertIn("Max steps exceeded", result.error_message)

    def test_final_action_refresh_keeps_ambiguous_action_fail_closed(self):
        """Pipeline refresh must not invent an action outside the shared resolver."""
        pipeline = self._make_pipeline()

        from src.application.analysis.analyzer import AnalysisResult
        from src.domain.shared.enums import ReportType
        from src.application.decision.decision_signal_extractor import (
            build_decision_signal_payload_from_report,
        )

        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=82,
            trend_prediction="看多",
            operation_advice="买盘增强，继续观察",
            decision_type="buy",
            action=None,
        )

        direct_payload = build_decision_signal_payload_from_report(
            result,
            trace_id="q-ambiguous-direct",
            query_source="test",
            report_type="simple",
            profile_source="auto_default",
        )
        pipeline._refresh_decision_action_for_final_result(
            result,
            report_type=ReportType.SIMPLE.value,
            previous_operation_advice=result.operation_advice,
        )
        refreshed_payload = build_decision_signal_payload_from_report(
            result,
            trace_id="q-ambiguous-refreshed",
            query_source="test",
            report_type="simple",
            profile_source="auto_default",
        )

        self.assertIsNone(result.action)
        self.assertIsNone(result.action_label)
        self.assertIsNone(direct_payload)
        self.assertIsNone(refreshed_payload)

    def test_convert_invalid_dashboard_preserves_local_trend_result(self):
        """Invalid Agent dashboard should not erase already-computed trend data."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.domain.shared.enums import ReportType
        from src.domain.analysis.stock_analyzer import BuySignal, TrendAnalysisResult, TrendStatus

        agent_result = AgentResult(
            success=True,
            content="LLM returned text but no dashboard JSON",
            dashboard=None,
            provider="ollama",
        )
        trend_result = TrendAnalysisResult(
            code="600519",
            trend_status=TrendStatus.BULL,
            buy_signal=BuySignal.BUY,
            signal_score=64,
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result,
            "600519",
            "贵州茅台",
            ReportType.SIMPLE,
            "q-trend-fallback",
            trend_result=trend_result,
        )

        self.assertIsNotNone(result)
        self.assertTrue(result.success)
        self.assertEqual(result.sentiment_score, 64)
        self.assertEqual(result.trend_prediction, "多头排列")
        self.assertEqual(result.operation_advice, "买入")
        self.assertEqual(result.decision_type, "buy")
        self.assertIn("trend:fallback", result.data_sources)

    def test_convert_dict_operation_advice_missing_decision_type_preserves_buy_signal(self):
        """When operation_advice is dict without decision_type, preserve dict-derived buy/sell hint."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.domain.shared.enums import ReportType

        agent_result = AgentResult(
            success=True,
            content="{}",
            dashboard={
                "operation_advice": {
                    "has_position": "买入",
                    "no_position": "观望",
                },
                "trend_prediction": "看多",
                "sentiment_score": 74,
            },
            provider="ollama",
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result,
            "600519",
            "贵州茅台",
            ReportType.SIMPLE,
            "q-dict-advice",
        )

        self.assertEqual(result.operation_advice, "买入")
        self.assertEqual(result.decision_type, "buy")

    def test_convert_missing_decision_type_preserves_conditional_hold_advice(self):
        """Condition-hold wording should remain hold when decision_type is not provided."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.domain.shared.enums import ReportType
        from src.domain.analysis.stock_analyzer import BuySignal, TrendAnalysisResult, TrendStatus

        agent_result = AgentResult(
            success=True,
            content="{}",
            dashboard={
                "operation_advice": "不跌破支撑位继续持有",
                "sentiment_score": 72,
            },
            provider="gemini",
        )
        trend_result = TrendAnalysisResult(
            code="600519",
            trend_status=TrendStatus.BULL,
            buy_signal=BuySignal.STRONG_BUY,
            signal_score=78,
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result,
            "600519",
            "贵州茅台",
            ReportType.SIMPLE,
            "q-conditional-hold-advice",
            trend_result=trend_result,
        )

        self.assertEqual(result.operation_advice, "不跌破支撑位继续持有")
        self.assertEqual(result.decision_type, "hold")

    def test_convert_partial_dashboard_uses_trend_fallback_for_missing_scalars(self):
        """Partial Agent dashboards should keep AI fields while filling missing scalars locally."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.domain.shared.enums import ReportType
        from src.domain.analysis.stock_analyzer import BuySignal, TrendAnalysisResult, TrendStatus

        agent_result = AgentResult(
            success=True,
            content="{}",
            dashboard={
                "stock_name": "贵州茅台",
                "dashboard": {
                    "core_conclusion": {"one_sentence": "AI 已给出的核心结论"},
                    "intelligence": {"risk_alerts": ["AI 风险"]},
                    "battle_plan": {"sniper_points": {"take_profit": "120元"}},
                },
            },
            provider="gemini",
        )
        trend_result = TrendAnalysisResult(
            code="600519",
            trend_status=TrendStatus.BULL,
            buy_signal=BuySignal.BUY,
            signal_score=66,
            support_levels=[108.5],
            risk_factors=["跌破 MA20"],
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result,
            "600519",
            "贵州茅台",
            ReportType.SIMPLE,
            "q-partial-dashboard",
            trend_result=trend_result,
        )

        self.assertEqual(result.sentiment_score, 66)
        self.assertEqual(result.trend_prediction, "多头排列")
        self.assertEqual(result.operation_advice, "买入")
        self.assertEqual(result.decision_type, "buy")
        self.assertEqual(result.dashboard["sentiment_score"], 66)
        self.assertEqual(result.dashboard["operation_advice"], "买入")
        self.assertEqual(result.dashboard["core_conclusion"]["one_sentence"], "AI 已给出的核心结论")
        self.assertEqual(result.dashboard["intelligence"]["risk_alerts"], ["AI 风险"])
        self.assertEqual(result.dashboard["battle_plan"]["sniper_points"]["stop_loss"], 108.5)
        self.assertIn("trend:fallback", result.data_sources)

    def test_convert_invalid_dashboard_normalizes_strong_trend_decision_type(self):
        """Fallback preserves strong advice text while keeping stable decision_type values."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.domain.shared.enums import ReportType
        from src.domain.analysis.stock_analyzer import BuySignal, TrendAnalysisResult, TrendStatus

        cases = [
            (BuySignal.STRONG_BUY, "buy", "强烈买入"),
            (BuySignal.STRONG_SELL, "sell", "强烈卖出"),
        ]

        for buy_signal, expected_decision, expected_advice in cases:
            with self.subTest(buy_signal=buy_signal):
                agent_result = AgentResult(
                    success=True,
                    content="LLM returned text but no dashboard JSON",
                    dashboard=None,
                    provider="ollama",
                )
                trend_result = TrendAnalysisResult(
                    code="600519",
                    trend_status=TrendStatus.BULL,
                    buy_signal=buy_signal,
                    signal_score=80,
                )

                result = pipeline._agent_result_to_analysis_result(
                    agent_result,
                    "600519",
                    "贵州茅台",
                    ReportType.SIMPLE,
                    "q-trend-fallback",
                    trend_result=trend_result,
                )

                self.assertEqual(result.operation_advice, expected_advice)
                self.assertEqual(result.decision_type, expected_decision)
