"""Tests for agent pipeline results flow."""

from tests.application.agent._agent_pipeline_support import (
    _TestAgentResultConversionFixture,
    json,
    unittest,
)


class TestAgentResultConversion(_TestAgentResultConversionFixture, unittest.TestCase):
    def test_convert_success_dashboard(self):
        """Successful AgentResult should produce a valid AnalysisResult."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.domain.shared.enums import ReportType

        dashboard = {
            "stock_name": "贵州茅台",
            "sentiment_score": 80,
            "trend_prediction": "看多",
            "operation_advice": "持有",
            "decision_type": "hold",
            "confidence_level": "高",
            "dashboard": {"core_conclusion": {"one_sentence": "看好"}},
            "analysis_summary": "Testing",
            "key_points": "Strong",
            "risk_warning": "High valuation",
            "buy_reason": "Leader",
            "trend_analysis": "Upward",
            "technical_analysis": "Bullish MACD",
            "ma_analysis": "Golden cross",
            "volume_analysis": "Healthy volume",
            "pattern_analysis": "Cup and handle",
            "fundamental_analysis": "Strong revenue",
            "sector_position": "Liquor leader",
            "company_highlights": "Brand value",
            "news_summary": "Recent news",
            "market_sentiment": "Optimistic",
            "hot_topics": "Baijiu",
            "short_term_outlook": "Bullish",
            "medium_term_outlook": "Stable",
        }

        agent_result = AgentResult(
            success=True,
            content=json.dumps(dashboard),
            dashboard=dashboard,
            tool_calls_log=[{"step": 1, "tool": "echo", "success": True}],
            total_steps=3,
            total_tokens=500,
            provider="gemini",
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result, "600519", "贵州茅台", ReportType.SIMPLE, "q123"
        )

        self.assertIsNotNone(result)
        self.assertTrue(result.success)
        self.assertEqual(result.code, "600519")
        self.assertEqual(result.name, "贵州茅台")
        self.assertEqual(result.sentiment_score, 80)
        self.assertEqual(result.trend_prediction, "看多")
        self.assertEqual(result.decision_type, "hold")
        self.assertIn("agent:gemini", result.data_sources)
        self.assertIsNotNone(result.dashboard)

    def test_convert_preserves_top_level_phase_decision_with_nested_dashboard(self):
        """Agent top-level phase_decision should survive nested dashboard unwrapping."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.domain.shared.enums import ReportType

        dashboard = {
            "stock_name": "贵州茅台",
            "sentiment_score": 80,
            "trend_prediction": "看多",
            "operation_advice": "持有",
            "decision_type": "hold",
            "confidence_level": "中",
            "phase_decision": {
                "phase_context": {"phase": "intraday", "market": "cn"},
                "action_window": "盘中跟踪",
                "immediate_action": "等待确认",
                "watch_conditions": ["放量突破"],
                "next_check_time": "14:30",
                "confidence_reason": "等待确认",
                "data_limitations": [],
            },
            "dashboard": {"core_conclusion": {"one_sentence": "看好"}},
            "analysis_summary": "Testing",
        }

        agent_result = AgentResult(
            success=True,
            content=json.dumps(dashboard),
            dashboard=dashboard,
            provider="gemini",
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result, "600519", "贵州茅台", ReportType.SIMPLE, "q-phase"
        )

        self.assertEqual(result.dashboard["phase_decision"]["phase_context"]["phase"], "intraday")
        self.assertEqual(result.dashboard["phase_decision"]["watch_conditions"], ["放量突破"])

    def test_convert_agent_dashboard_preserves_explicit_action(self):
        """Explicit Agent action is display taxonomy; decision_type remains the legacy bridge."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.domain.shared.enums import ReportType

        agent_result = AgentResult(
            success=True,
            content="{}",
            dashboard={
                "sentiment_score": 52,
                "trend_prediction": "震荡",
                "operation_advice": "持有观察",
                "decision_type": "hold",
                "action": "watch",
                "analysis_summary": "等待确认",
            },
            provider="gemini",
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result, "600519", "贵州茅台", ReportType.SIMPLE, "q-action"
        )
        raw_result = result.to_dict()

        self.assertEqual(result.operation_advice, "持有观察")
        self.assertEqual(result.decision_type, "hold")
        self.assertEqual(result.action, "watch")
        self.assertEqual(result.action_label, "观望")
        self.assertEqual(raw_result["action"], "watch")
        self.assertEqual(raw_result["action_label"], "观望")

    def test_final_action_refresh_preserves_explicit_action_when_advice_is_unchanged(self):
        """Pre-save refresh must not overwrite an explicit Agent action without a final advice rewrite."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.domain.shared.enums import ReportType

        agent_result = AgentResult(
            success=True,
            content="{}",
            dashboard={
                "sentiment_score": 52,
                "trend_prediction": "震荡",
                "operation_advice": "持有观察",
                "decision_type": "hold",
                "action": "watch",
                "analysis_summary": "等待确认",
            },
            provider="gemini",
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result, "600519", "贵州茅台", ReportType.SIMPLE, "q-action-preserve"
        )
        previous_operation_advice = result.operation_advice

        pipeline._refresh_decision_action_for_final_result(
            result,
            report_type=ReportType.SIMPLE.value,
            previous_operation_advice=previous_operation_advice,
        )
        raw_result = result.to_dict()

        self.assertEqual(result.operation_advice, "持有观察")
        self.assertEqual(result.action, "watch")
        self.assertEqual(result.action_label, "观望")
        self.assertEqual(raw_result["action"], "watch")
        self.assertEqual(raw_result["action_label"], "观望")

    def test_final_action_refresh_ignores_stale_pre_guardrail_action(self):
        """Post-processing can rewrite advice; refreshed action must follow the final advice."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.domain.shared.enums import ReportType

        agent_result = AgentResult(
            success=True,
            content="{}",
            dashboard={
                "sentiment_score": 68,
                "trend_prediction": "震荡",
                "operation_advice": "买入",
                "decision_type": "buy",
                "action": "buy",
                "analysis_summary": "等待确认",
            },
            provider="gemini",
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result, "600519", "贵州茅台", ReportType.SIMPLE, "q-action-refresh"
        )
        previous_operation_advice = result.operation_advice
        result.operation_advice = "持有观察"
        result.decision_type = "hold"

        pipeline._refresh_decision_action_for_final_result(
            result,
            report_type=ReportType.SIMPLE.value,
            previous_operation_advice=previous_operation_advice,
        )

        self.assertEqual(result.action, "hold")
        self.assertEqual(result.action_label, "持有")

    def test_convert_empty_dashboard_backfills_local_trend_dashboard(self):
        """Empty Agent dashboard should still produce an integrity-ready local fallback dashboard."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.application.analysis.analyzer import check_content_integrity
        from src.domain.shared.enums import ReportType
        from src.domain.analysis.stock_analyzer import BuySignal, TrendAnalysisResult, TrendStatus

        agent_result = AgentResult(
            success=True,
            content="{}",
            dashboard={},
            provider="gemini",
        )
        trend_result = TrendAnalysisResult(
            code="600519",
            trend_status=TrendStatus.BULL,
            buy_signal=BuySignal.BUY,
            signal_score=68,
            support_levels=[112.3],
            risk_factors=["跌破 MA20 需止损"],
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result,
            "600519",
            "贵州茅台",
            ReportType.SIMPLE,
            "q-empty-dashboard",
            trend_result=trend_result,
        )

        ok, missing = check_content_integrity(result)
        self.assertTrue(ok, missing)
        self.assertEqual(result.sentiment_score, 68)
        self.assertEqual(result.analysis_summary, "趋势结论：多头排列；操作建议：买入。")
        self.assertEqual(result.dashboard["sentiment_score"], 68)
        self.assertEqual(result.dashboard["core_conclusion"]["one_sentence"], result.analysis_summary)
        self.assertEqual(result.dashboard["intelligence"]["risk_alerts"], ["跌破 MA20 需止损"])
        self.assertEqual(result.dashboard["battle_plan"]["sniper_points"]["stop_loss"], 112.3)

    def test_convert_empty_top_level_advice_uses_nested_dashboard_advice(self):
        """Empty top-level advice dict should not block nested dashboard fallback."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.domain.shared.enums import ReportType

        agent_result = AgentResult(
            success=True,
            content="{}",
            dashboard={
                "operation_advice": {},
                "dashboard": {
                    "operation_advice": "减仓",
                    "trend_prediction": "看空",
                    "sentiment_score": 42,
                },
            },
            provider="gemini",
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result,
            "600519",
            "贵州茅台",
            ReportType.SIMPLE,
            "q-nested-advice",
        )

        self.assertEqual(result.operation_advice, "减仓")
        self.assertEqual(result.decision_type, "sell")
        self.assertEqual(result.dashboard["operation_advice"], "减仓")

    def test_convert_placeholder_top_level_advice_uses_nested_dashboard_advice(self):
        """Placeholder advice dict should not block nested dashboard fallback."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.domain.shared.enums import ReportType

        agent_result = AgentResult(
            success=True,
            content="{}",
            dashboard={
                "operation_advice": {
                    "has_position": "待补充",
                    "no_position": "TBD",
                },
                "dashboard": {
                    "operation_advice": "减仓",
                    "trend_prediction": "看空",
                    "sentiment_score": 42,
                },
            },
            provider="gemini",
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result,
            "600519",
            "贵州茅台",
            ReportType.SIMPLE,
            "q-placeholder-advice",
        )

        self.assertEqual(result.operation_advice, "减仓")
        self.assertEqual(result.decision_type, "sell")
        self.assertEqual(result.dashboard["operation_advice"], "减仓")

    def test_convert_malformed_top_level_summary_uses_nested_dashboard_summary(self):
        """Malformed top-level analysis_summary should not block nested dashboard fallback."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.domain.shared.enums import ReportType

        agent_result = AgentResult(
            success=True,
            content="{}",
            dashboard={
                "analysis_summary": [],
                "dashboard": {
                    "analysis_summary": "AI 已给出的摘要",
                    "trend_prediction": "看多",
                    "operation_advice": "持有",
                    "sentiment_score": 73,
                },
            },
            provider="gemini",
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result,
            "600519",
            "贵州茅台",
            ReportType.SIMPLE,
            "q-nested-summary",
        )

        self.assertEqual(result.analysis_summary, "AI 已给出的摘要")
        self.assertEqual(result.dashboard["analysis_summary"], "AI 已给出的摘要")

    def test_convert_non_string_summary_falls_back_to_nested_or_local_summary(self):
        """Non-string analysis_summary should trigger fallback to nested summary or local fallback."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.domain.shared.enums import ReportType

        for raw_summary in (0, False):
            agent_result = AgentResult(
                success=True,
                content="{}",
                dashboard={
                    "analysis_summary": raw_summary,
                    "trend_prediction": "看多",
                    "dashboard": {
                        "analysis_summary": "AI 已给出的摘要",
                    },
                    "operation_advice": "持有",
                    "sentiment_score": 73,
                },
                provider="gemini",
            )

            result = pipeline._agent_result_to_analysis_result(
                agent_result,
                "600519",
                "贵州茅台",
                ReportType.SIMPLE,
                f"q-summary-non-string-{raw_summary}",
            )

            self.assertEqual(result.analysis_summary, "AI 已给出的摘要")
            self.assertEqual(result.dashboard["analysis_summary"], "AI 已给出的摘要")

    def test_convert_malformed_scalar_fields_fallback_to_trend_result(self):
        """Malformed non-scalar scalar fields should not be treated as valid values."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.domain.shared.enums import ReportType
        from src.domain.analysis.stock_analyzer import BuySignal, TrendAnalysisResult, TrendStatus

        agent_result = AgentResult(
            success=True,
            content="{}",
            dashboard={
                "sentiment_score": {"value": ""},
                "trend_prediction": [],
                "operation_advice": [],
                "decision_type": {},
            },
            provider="gemini",
        )
        trend_result = TrendAnalysisResult(
            code="600519",
            trend_status=TrendStatus.BULL,
            buy_signal=BuySignal.BUY,
            signal_score=66,
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result,
            "600519",
            "贵州茅台",
            ReportType.SIMPLE,
            "q-malformed-scalars",
            trend_result=trend_result,
        )

        self.assertEqual(result.sentiment_score, 66)
        self.assertEqual(result.trend_prediction, "多头排列")
        self.assertEqual(result.operation_advice, "买入")
        self.assertEqual(result.decision_type, "buy")
        self.assertEqual(result.dashboard["sentiment_score"], 66)
        self.assertEqual(result.dashboard["trend_prediction"], "多头排列")
        self.assertEqual(result.dashboard["operation_advice"], "买入")

    def test_convert_empty_dashboard_backfills_localized_trend_fallback_for_en(self):
        """English reports should keep trend/advice fallback values localized."""
        pipeline = self._make_pipeline()
        pipeline.config.report_language = "en"

        from src.application.agent.executor import AgentResult
        from src.domain.shared.enums import ReportType
        from src.domain.analysis.stock_analyzer import BuySignal, TrendAnalysisResult, TrendStatus

        agent_result = AgentResult(
            success=True,
            content="{}",
            dashboard={},
            provider="gemini",
        )
        trend_result = TrendAnalysisResult(
            code="600519",
            trend_status=TrendStatus.BULL,
            buy_signal=BuySignal.BUY,
            signal_score=70,
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result,
            "600519",
            "贵州茅台",
            ReportType.SIMPLE,
            "q-en-fallback",
            trend_result=trend_result,
        )

        self.assertEqual(result.report_language, "en")
        self.assertEqual(result.trend_prediction, "Bullish")
        self.assertEqual(result.operation_advice, "Buy")
        self.assertEqual(
            result.analysis_summary,
            "Trend view: Bullish; action advice: Buy.",
        )
        self.assertEqual(result.dashboard["trend_prediction"], "Bullish")
        self.assertEqual(result.dashboard["operation_advice"], "Buy")
        self.assertEqual(
            result.dashboard["core_conclusion"]["one_sentence"],
            "Trend view: Bullish; action advice: Buy.",
        )

    def test_convert_non_dict_advice_conflict_keeps_advice_decision(self):
        """Conflict between trend fallback and explicit non-dict advice should keep advice decision."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.domain.shared.enums import ReportType
        from src.domain.analysis.stock_analyzer import BuySignal, TrendAnalysisResult, TrendStatus

        agent_result = AgentResult(
            success=True,
            content="{}",
            dashboard={
                "sentiment_score": 65,
                "trend_prediction": "看空",
                "operation_advice": "减仓",
            },
            provider="gemini",
        )
        trend_result = TrendAnalysisResult(
            code="600519",
            trend_status=TrendStatus.BULL,
            buy_signal=BuySignal.BUY,
            signal_score=70,
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result,
            "600519",
            "贵州茅台",
            ReportType.SIMPLE,
            "q-advice-vs-trend",
            trend_result=trend_result,
        )

        self.assertEqual(result.operation_advice, "减仓")
        self.assertEqual(result.decision_type, "sell")

    def test_convert_risk_alerts_string_placeholder_uses_local_risk_factors(self):
        """String-like placeholder risk alerts should be replaced with local trend risk factors."""
        pipeline = self._make_pipeline()

        from src.application.agent.executor import AgentResult
        from src.application.analysis.analyzer import check_content_integrity
        from src.domain.shared.enums import ReportType
        from src.domain.analysis.stock_analyzer import BuySignal, TrendAnalysisResult, TrendStatus

        agent_result = AgentResult(
            success=True,
            content="{}",
            dashboard={
                "dashboard": {
                    "core_conclusion": {"one_sentence": "AI 已给出的核心结论"},
                    "intelligence": {"risk_alerts": "待补充"},
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
            risk_factors=["涨幅过快", "回撤放大"],
        )

        result = pipeline._agent_result_to_analysis_result(
            agent_result,
            "600519",
            "贵州茅台",
            ReportType.SIMPLE,
            "q-risk-alerts-string-placeholder",
            trend_result=trend_result,
        )

        ok, missing = check_content_integrity(result)
        self.assertTrue(ok, missing)
        self.assertEqual(result.dashboard["intelligence"]["risk_alerts"], ["涨幅过快", "回撤放大"])
