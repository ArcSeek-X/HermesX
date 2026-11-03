"""Tests for agent pipeline analysis."""

from tests.application.agent._agent_pipeline_support import (
    MagicMock,
    SimpleNamespace,
    _TestAnalyzeWithAgentStockNameFixture,
    patch,
    unittest,
)


class TestAnalyzeWithAgentStockName(_TestAnalyzeWithAgentStockNameFixture, unittest.TestCase):
    def test_analyze_with_agent_keeps_high_score_hold_action_consistent_across_outputs(self):
        """A high-score hold may align to buy, and every public output must use that action."""
        with patch('src.application.analysis.pipeline.get_config') as mock_config, \
             patch('src.application.analysis.pipeline.build_pipeline_persistence_port'), \
             patch('src.application.analysis.pipeline.build_stock_data_port', return_value=MagicMock()), \
             patch('src.application.analysis.pipeline.GeminiAnalyzer'), \
             patch('src.application.analysis.pipeline.NotificationService'), \
             patch('src.application.analysis.pipeline.SearchService'), \
             patch('src.bootstrap.agent.build_agent_executor') as mock_build_executor:

            mock_cfg = MagicMock()
            mock_cfg.max_workers = 2
            mock_cfg.agent_mode = True
            mock_cfg.agent_max_steps = 10
            mock_cfg.agent_skills = []
            mock_cfg.bocha_api_keys = []
            mock_cfg.tavily_api_keys = []
            mock_cfg.brave_api_keys = []
            mock_cfg.serpapi_keys = []
            mock_cfg.searxng_base_urls = []
            mock_cfg.searxng_public_instances_enabled = False
            mock_cfg.news_max_age_days = 7
            mock_cfg.enable_realtime_quote = True
            mock_cfg.enable_chip_distribution = True
            mock_cfg.realtime_source_priority = []
            mock_cfg.save_context_snapshot = False
            mock_cfg.report_language = "zh"
            mock_config.return_value = mock_cfg

            from src.application.agent.executor import AgentResult
            from src.application.agent.runtime_facts import AgentRuntimeFacts, BaseAgentOpinionFact
            from src.application.analysis.pipeline import StockAnalysisPipeline
            from src.domain.shared.enums import ReportType
            from src.application.decision.decision_signal_extractor import (
                build_decision_signal_payload_from_report,
            )

            pipeline = StockAnalysisPipeline(config=mock_cfg)
            pipeline.search_service.is_available = False
            pipeline.db.save_analysis_history.return_value = 2044
            pipeline._extract_decision_signal_after_history_save = MagicMock()

            agent_result = AgentResult(
                success=True,
                content="{}",
                dashboard={
                    "stock_name": "贵州茅台",
                    "sentiment_score": 80,
                    "trend_prediction": "看多",
                    "operation_advice": "持有",
                    "decision_type": "hold",
                    "analysis_summary": "高分但模型建议持有。",
                },
                provider="gemini",
                runtime_facts=AgentRuntimeFacts(
                    base_agent_opinions=(
                        BaseAgentOpinionFact(
                            agent="technical",
                            signal="buy",
                            confidence=0.8,
                        ),
                    ),
                ),
            )
            mock_executor = MagicMock()
            mock_executor.run.return_value = agent_result
            mock_build_executor.return_value = mock_executor

            result = pipeline._analyze_with_agent(
                code="600519",
                report_type=ReportType.SIMPLE,
                query_id="q-review-hold-to-buy",
                stock_name="贵州茅台",
                realtime_quote=None,
                chip_data=None,
            )

            self.assertIsNotNone(result)
            self.assertEqual(result.decision_type, "hold")
            self.assertEqual(result.action, "buy")
            self.assertEqual(result.action_label, "买入")

            explanation = result.dashboard["agent_disagreement_explanation"]
            self.assertNotIn("final_signal", explanation)
            self.assertEqual(explanation["pipeline_start_action"], "buy")
            self.assertEqual(explanation["final_adjustments"], [])
            self.assertEqual(explanation["final_action"], "buy")

            saved_result = pipeline.db.save_analysis_history.call_args.kwargs["result"]
            self.assertIs(saved_result, result)
            self.assertEqual(saved_result.action, "buy")
            self.assertEqual(
                saved_result.dashboard["agent_disagreement_explanation"]["final_action"],
                "buy",
            )

            signal_result = (
                pipeline._extract_decision_signal_after_history_save.call_args.kwargs["result"]
            )
            self.assertIs(signal_result, result)
            signal_payload = build_decision_signal_payload_from_report(
                signal_result,
                source_report_id=2044,
                trace_id="q-review-hold-to-buy",
                query_source="test",
                report_type="simple",
                profile_source="auto_default",
            )
            self.assertIsNotNone(signal_payload)
            self.assertEqual(signal_payload["action"], "buy")
            self.assertEqual(signal_payload["metadata"]["decision_type"], "hold")

    def test_analyze_with_agent_keeps_ambiguous_action_fail_closed_across_outputs(self):
        """Ambiguous advice must not gain an action through Pipeline ordering."""
        with patch('src.application.analysis.pipeline.get_config') as mock_config, \
             patch('src.application.analysis.pipeline.build_pipeline_persistence_port'), \
             patch('src.application.analysis.pipeline.build_stock_data_port', return_value=MagicMock()), \
             patch('src.application.analysis.pipeline.GeminiAnalyzer'), \
             patch('src.application.analysis.pipeline.NotificationService'), \
             patch('src.application.analysis.pipeline.SearchService'), \
             patch('src.bootstrap.agent.build_agent_executor') as mock_build_executor:

            mock_cfg = MagicMock()
            mock_cfg.max_workers = 2
            mock_cfg.agent_mode = True
            mock_cfg.agent_max_steps = 10
            mock_cfg.agent_skills = []
            mock_cfg.bocha_api_keys = []
            mock_cfg.tavily_api_keys = []
            mock_cfg.brave_api_keys = []
            mock_cfg.serpapi_keys = []
            mock_cfg.searxng_base_urls = []
            mock_cfg.searxng_public_instances_enabled = False
            mock_cfg.news_max_age_days = 7
            mock_cfg.enable_realtime_quote = True
            mock_cfg.enable_chip_distribution = True
            mock_cfg.realtime_source_priority = []
            mock_cfg.save_context_snapshot = False
            mock_cfg.report_language = "zh"
            mock_config.return_value = mock_cfg

            from src.application.agent.executor import AgentResult
            from src.application.agent.runtime_facts import AgentRuntimeFacts, BaseAgentOpinionFact
            from src.application.analysis.pipeline import StockAnalysisPipeline
            from src.domain.shared.enums import ReportType
            from src.application.decision.decision_signal_extractor import (
                build_decision_signal_payload_from_report,
            )

            pipeline = StockAnalysisPipeline(config=mock_cfg)
            pipeline.search_service.is_available = False
            pipeline.db.save_analysis_history.return_value = 2044
            pipeline._extract_decision_signal_after_history_save = MagicMock()

            agent_result = AgentResult(
                success=True,
                content="{}",
                dashboard={
                    "stock_name": "贵州茅台",
                    "sentiment_score": 82,
                    "trend_prediction": "看多",
                    "operation_advice": "买盘增强，继续观察",
                    "decision_type": "buy",
                    "analysis_summary": "方向偏多，但操作建议仍需观察。",
                },
                provider="gemini",
                runtime_facts=AgentRuntimeFacts(
                    base_agent_opinions=(
                        BaseAgentOpinionFact(
                            agent="technical",
                            signal="buy",
                            confidence=0.8,
                        ),
                    ),
                ),
            )
            mock_executor = MagicMock()
            mock_executor.run.return_value = agent_result
            mock_build_executor.return_value = mock_executor

            result = pipeline._analyze_with_agent(
                code="600519",
                report_type=ReportType.SIMPLE,
                query_id="q-review-ambiguous-action",
                stock_name="贵州茅台",
                realtime_quote=None,
                chip_data=None,
            )

            self.assertIsNotNone(result)
            self.assertEqual(result.decision_type, "buy")
            self.assertIsNone(result.action)
            self.assertIsNone(result.action_label)
            self.assertNotIn("agent_disagreement_explanation", result.dashboard)

            saved_result = pipeline.db.save_analysis_history.call_args.kwargs["result"]
            self.assertIs(saved_result, result)
            self.assertIsNone(saved_result.action)
            self.assertNotIn("agent_disagreement_explanation", saved_result.dashboard)

            signal_result = (
                pipeline._extract_decision_signal_after_history_save.call_args.kwargs["result"]
            )
            self.assertIs(signal_result, result)
            signal_payload = build_decision_signal_payload_from_report(
                signal_result,
                source_report_id=2044,
                trace_id="q-review-ambiguous-action",
                query_source="test",
                report_type="simple",
                profile_source="auto_default",
            )
            self.assertIsNone(signal_payload)

    def test_analyze_with_agent_uses_resolved_name_for_news_persistence(self):
        """Should use resolved stock name from dashboard for search and DB persistence."""
        with patch('src.application.analysis.pipeline.get_config') as mock_config, \
             patch('src.application.analysis.pipeline.build_pipeline_persistence_port'), \
             patch('src.application.analysis.pipeline.build_stock_data_port', return_value=MagicMock()), \
             patch('src.application.analysis.pipeline.GeminiAnalyzer'), \
             patch('src.application.analysis.pipeline.NotificationService'), \
             patch('src.application.analysis.pipeline.SearchService'), \
             patch('src.bootstrap.agent.build_agent_executor') as mock_build_executor, \
             patch('src.application.agent.executor.AgentExecutor.run') as mock_agent_run:

            mock_cfg = MagicMock()
            mock_cfg.max_workers = 2
            mock_cfg.agent_mode = True
            mock_cfg.agent_max_steps = 10
            mock_cfg.agent_skills = []
            mock_cfg.bocha_api_keys = []
            mock_cfg.tavily_api_keys = []
            mock_cfg.brave_api_keys = []
            mock_cfg.serpapi_keys = []
            mock_cfg.searxng_base_urls = []
            mock_cfg.searxng_public_instances_enabled = False
            mock_cfg.news_max_age_days = 7
            mock_cfg.enable_realtime_quote = True
            mock_cfg.enable_chip_distribution = True
            mock_cfg.realtime_source_priority = []
            mock_cfg.save_context_snapshot = False
            mock_config.return_value = mock_cfg

            from src.application.analysis.pipeline import StockAnalysisPipeline
            from src.application.agent.executor import AgentResult
            from src.domain.shared.enums import ReportType
            pipeline = StockAnalysisPipeline(config=mock_cfg)

            agent_result = AgentResult(
                success=True,
                content="{}",
                dashboard={
                    "stock_name": "科创芯片ETF",
                    "sentiment_score": 78,
                    "trend_prediction": "震荡偏多",
                    "operation_advice": "持有",
                    "decision_type": "hold",
                },
                provider="gemini",
            )
            mock_executor = MagicMock()
            mock_executor.run.return_value = agent_result
            mock_build_executor.return_value = mock_executor
            mock_agent_run.return_value = agent_result

            news_response = MagicMock()
            news_response.success = True
            news_response.results = [{"title": "test"}]
            news_response.query = "test query"
            pipeline.search_service.is_available = True
            pipeline.search_service.search_stock_news.return_value = news_response

            result = pipeline._analyze_with_agent(
                code="588200",
                report_type=ReportType.SIMPLE,
                query_id="q-news",
                stock_name="股票588200",
                realtime_quote=None,
                chip_data=None
            )

            self.assertIsNotNone(result)
            self.assertEqual(result.name, "科创芯片ETF")
            pipeline.search_service.search_stock_news.assert_called_once_with(
                stock_code="588200",
                stock_name="科创芯片ETF",
                max_results=5
            )
            pipeline.db.save_news_intel.assert_called_once()
            saved_kwargs = pipeline.db.save_news_intel.call_args.kwargs
            self.assertEqual(saved_kwargs["name"], "科创芯片ETF")

    def test_analyze_with_agent_keeps_dashboard_top_level_fields_after_stability(self):
        """Decision stability downgrade in agent flow should sync dashboard and top-level decision fields."""
        with patch('src.application.analysis.pipeline.get_config') as mock_config, \
             patch('src.application.analysis.pipeline.build_pipeline_persistence_port'), \
             patch('src.application.analysis.pipeline.build_stock_data_port', return_value=MagicMock()), \
             patch('src.application.analysis.pipeline.GeminiAnalyzer'), \
             patch('src.application.analysis.pipeline.NotificationService'), \
             patch('src.application.analysis.pipeline.SearchService'), \
             patch('src.bootstrap.agent.build_agent_executor') as mock_build_executor:

            mock_cfg = MagicMock()
            mock_cfg.max_workers = 2
            mock_cfg.agent_mode = True
            mock_cfg.agent_max_steps = 10
            mock_cfg.agent_skills = []
            mock_cfg.bocha_api_keys = []
            mock_cfg.tavily_api_keys = []
            mock_cfg.brave_api_keys = []
            mock_cfg.serpapi_keys = []
            mock_cfg.searxng_base_urls = []
            mock_cfg.searxng_public_instances_enabled = False
            mock_cfg.news_max_age_days = 7
            mock_cfg.enable_realtime_quote = True
            mock_cfg.enable_chip_distribution = True
            mock_cfg.realtime_source_priority = []
            mock_cfg.save_context_snapshot = False
            mock_cfg.report_language = "zh"
            mock_cfg.agent_orchestrator_timeout_s = 600
            mock_config.return_value = mock_cfg

            from src.application.analysis.pipeline import StockAnalysisPipeline
            from src.application.agent.executor import AgentResult
            from src.application.agent.risk_override import RiskOverrideApplication
            from src.application.agent.runtime_facts import AgentRuntimeFacts, BaseAgentOpinionFact
            from src.domain.shared.enums import ReportType
            from src.domain.analysis.stock_analyzer import TrendAnalysisResult, TrendStatus, BuySignal
            pipeline = StockAnalysisPipeline(config=mock_cfg)

            agent_result = AgentResult(
                success=True,
                content="{}",
                dashboard={
                    "sentiment_score": 30,
                    "trend_prediction": "震荡",
                    "operation_advice": "卖出",
                    "decision_type": "sell",
                    "analysis_summary": "原始建议",
                    "dashboard": {
                        "core_conclusion": {"one_sentence": "初始结论"},
                    },
                },
                provider="gemini",
                runtime_facts=AgentRuntimeFacts(
                    base_agent_opinions=(
                        BaseAgentOpinionFact(
                            agent="technical",
                            signal="sell",
                            confidence=0.8,
                        ),
                    ),
                    risk_override_application=RiskOverrideApplication(
                        evidence_present=False,
                        override_enabled=True,
                        trigger="none",
                        applied=False,
                        reason="no_risk_evidence",
                        post_risk_signal="sell",
                    ),
                ),
            )
            mock_executor = MagicMock()
            mock_executor.run.return_value = agent_result
            mock_build_executor.return_value = mock_executor
            pipeline.db.save_analysis_history.return_value = 1
            pipeline._extract_decision_signal_after_history_save = MagicMock()

            trend_result = TrendAnalysisResult(
                code="002812",
                trend_status=TrendStatus.BULL,
                buy_signal=BuySignal.SELL,
                signal_score=30,
                support_levels=[30.0],
                resistance_levels=[34.0],
            )
            fundamental_context = {
                "capital_flow": {
                    "status": "ok",
                    "data": {
                        "stock_flow": {
                            "main_net_inflow": 800_000,
                        }
                    },
                }
            }

            result = pipeline._analyze_with_agent(
                code="002812",
                report_type=ReportType.SIMPLE,
                query_id="q-agent-stability",
                stock_name="恩捷股份",
                realtime_quote={"price": 30.4, "change_pct": -2.1},
                chip_data=None,
                fundamental_context=fundamental_context,
                trend_result=trend_result,
            )

            self.assertIsNotNone(result)
            self.assertEqual(result.decision_type, "hold")
            self.assertEqual(result.operation_advice, "洗盘观察")
            self.assertEqual(result.dashboard.get("decision_type"), "hold")
            self.assertEqual(result.dashboard.get("operation_advice"), "洗盘观察")
            self.assertEqual(result.dashboard.get("sentiment_score"), result.sentiment_score)
            explanation = result.dashboard["agent_disagreement_explanation"]
            self.assertEqual(explanation["risk_control"]["post_risk_signal"], "sell")
            self.assertNotIn("final_signal", explanation)
            self.assertEqual(explanation["final_action"], result.action)
            self.assertEqual(
                explanation["final_adjustments"],
                [
                    {
                        "source": "structure_and_fundamentals",
                        "from_action": "sell",
                        "to_action": result.action,
                    }
                ],
            )
            saved_result = pipeline.db.save_analysis_history.call_args.kwargs["result"]
            self.assertIs(saved_result, result)
            signal_result = (
                pipeline._extract_decision_signal_after_history_save.call_args.kwargs["result"]
            )
            self.assertIs(signal_result, result)
            self.assertEqual(signal_result.action, explanation["final_action"])
            from src.application.decision.decision_signal_extractor import (
                build_decision_signal_payload_from_report,
            )
            signal_payload = build_decision_signal_payload_from_report(
                result,
                source_report_id=1,
                trace_id="q-agent-stability",
                query_source="test",
                report_type="simple",
                profile_source="auto_default",
            )
            self.assertIsNotNone(signal_payload)
            self.assertEqual(signal_payload["action"], explanation["final_action"])
            self.assertEqual(signal_payload["action"], result.action)

    def test_analyze_with_agent_phase_integrity_fills_missing_phase_decision(self):
        """Agent weak integrity should enforce phase_decision when phase context exists."""
        with patch('src.application.analysis.pipeline.get_config') as mock_config, \
             patch('src.application.analysis.pipeline.build_pipeline_persistence_port'), \
             patch('src.application.analysis.pipeline.build_stock_data_port', return_value=MagicMock()), \
             patch('src.application.analysis.pipeline.GeminiAnalyzer'), \
             patch('src.application.analysis.pipeline.NotificationService'), \
             patch('src.application.analysis.pipeline.SearchService'), \
             patch('src.bootstrap.agent.build_agent_executor') as mock_build_executor:

            mock_cfg = MagicMock()
            mock_cfg.max_workers = 2
            mock_cfg.agent_mode = True
            mock_cfg.agent_max_steps = 10
            mock_cfg.agent_skills = []
            mock_cfg.bocha_api_keys = []
            mock_cfg.tavily_api_keys = []
            mock_cfg.brave_api_keys = []
            mock_cfg.serpapi_keys = []
            mock_cfg.searxng_base_urls = []
            mock_cfg.searxng_public_instances_enabled = False
            mock_cfg.news_max_age_days = 7
            mock_cfg.enable_realtime_quote = True
            mock_cfg.enable_chip_distribution = True
            mock_cfg.realtime_source_priority = []
            mock_cfg.save_context_snapshot = False
            mock_cfg.report_language = "zh"
            mock_cfg.report_integrity_enabled = True
            mock_cfg.agent_orchestrator_timeout_s = 600
            mock_config.return_value = mock_cfg

            from src.application.agent.executor import AgentResult
            from src.application.analysis.analyzer import check_content_integrity
            from src.application.analysis.pipeline import StockAnalysisPipeline
            from src.domain.shared.enums import ReportType

            pipeline = StockAnalysisPipeline(config=mock_cfg)
            pipeline.search_service.is_available = False
            pipeline._ensure_agent_history = MagicMock()
            pipeline._build_analysis_context_pack_outputs = MagicMock(
                return_value=(
                    "",
                    {
                        "blocks": [],
                        "data_quality": {"limitations": []},
                    },
                )
            )

            agent_result = AgentResult(
                success=True,
                content="{}",
                dashboard={
                    "sentiment_score": 62,
                    "trend_prediction": "震荡",
                    "operation_advice": "减仓",
                    "decision_type": "sell",
                    "confidence_level": "中",
                    "analysis_summary": "盘中风险偏高",
                    "dashboard": {
                        "core_conclusion": {"one_sentence": "盘中风险偏高"},
                        "intelligence": {"risk_alerts": []},
                    },
                },
                provider="gemini",
            )
            mock_executor = MagicMock()
            mock_executor.run.return_value = agent_result
            mock_build_executor.return_value = mock_executor

            phase_context = {
                "phase": "intraday",
                "market": "cn",
                "market_local_time": "2026-06-02T10:30:00+08:00",
            }
            phase_summary = {
                **phase_context,
                "is_trading_day": True,
                "is_market_open_now": True,
                "is_partial_bar": True,
                "warnings": [],
            }

            result = pipeline._analyze_with_agent(
                code="600519",
                report_type=ReportType.SIMPLE,
                query_id="q-agent-phase-integrity",
                stock_name="贵州茅台",
                realtime_quote=None,
                chip_data=None,
                market_phase_context=phase_context,
                market_phase_summary=phase_summary,
            )

            self.assertIsNotNone(result)
            ok, missing = check_content_integrity(result, require_phase_decision=True)
            self.assertTrue(ok, missing)
            phase_decision = result.dashboard["phase_decision"]
            self.assertEqual(phase_decision["phase_context"]["phase"], "intraday")
            self.assertEqual(phase_decision["action_window"], "模型未提供阶段化行动窗口")
            self.assertEqual(phase_decision["immediate_action"], "模型未提供阶段化即时动作")
            self.assertEqual(phase_decision["watch_conditions"], [])
            self.assertEqual(phase_decision["next_check_time"], "模型未提供下一次检查点")
            self.assertEqual(phase_decision["confidence_reason"], "模型未提供阶段化置信度理由")

    def test_analyze_with_agent_explains_daily_market_softening_before_risk(self):
        """A partial result produced before risk must retain its Pipeline start signal."""
        with patch('src.application.analysis.pipeline.get_config') as mock_config, \
             patch('src.application.analysis.pipeline.build_pipeline_persistence_port'), \
             patch('src.application.analysis.pipeline.build_stock_data_port', return_value=MagicMock()), \
             patch('src.application.analysis.pipeline.GeminiAnalyzer'), \
             patch('src.application.analysis.pipeline.NotificationService'), \
             patch('src.application.analysis.pipeline.SearchService'), \
             patch('src.application.analysis.pipeline.stabilize_decision_with_structure'), \
             patch('src.bootstrap.agent.build_agent_executor') as mock_build_executor:

            mock_cfg = MagicMock()
            mock_cfg.max_workers = 2
            mock_cfg.agent_mode = True
            mock_cfg.agent_max_steps = 10
            mock_cfg.agent_skills = []
            mock_cfg.bocha_api_keys = []
            mock_cfg.tavily_api_keys = []
            mock_cfg.brave_api_keys = []
            mock_cfg.serpapi_keys = []
            mock_cfg.searxng_base_urls = []
            mock_cfg.searxng_public_instances_enabled = False
            mock_cfg.news_max_age_days = 7
            mock_cfg.enable_realtime_quote = True
            mock_cfg.enable_chip_distribution = True
            mock_cfg.realtime_source_priority = []
            mock_cfg.save_context_snapshot = False
            mock_cfg.report_language = "en"
            mock_cfg.report_integrity_enabled = False
            mock_config.return_value = mock_cfg

            from datetime import date

            from src.application.agent.executor import AgentResult
            from src.application.agent.runtime_facts import AgentRuntimeFacts, BaseAgentOpinionFact
            from src.application.analysis.pipeline import StockAnalysisPipeline
            from src.domain.shared.enums import ReportType
            from src.application.market.daily_market_context import DailyMarketContext

            pipeline = StockAnalysisPipeline(config=mock_cfg)
            pipeline.search_service.is_available = False
            pipeline.db.save_analysis_history.return_value = 1
            pipeline._extract_decision_signal_after_history_save = MagicMock()

            agent_result = AgentResult(
                success=True,
                content="{}",
                dashboard={
                    "sentiment_score": 82,
                    "trend_prediction": "bullish",
                    "operation_advice": "Buy now.",
                    "decision_type": "buy",
                    "confidence_level": "high",
                    "analysis_summary": "Strong stock signal.",
                    "dashboard": {
                        "core_conclusion": {
                            "one_sentence": "Buy now and add aggressively.",
                            "position_advice": {
                                "no_position": "Buy now.",
                                "has_position": "Add position.",
                            },
                        },
                        "battle_plan": {
                            "position_strategy": {
                                "suggested_position": "Full position",
                                "entry_plan": "Buy the breakout",
                                "risk_control": "Add on pullback",
                            }
                        },
                    },
                },
                provider="gemini",
                runtime_facts=AgentRuntimeFacts(
                    base_agent_opinions=(
                        BaseAgentOpinionFact(
                            agent="technical",
                            signal="buy",
                            confidence=0.82,
                        ),
                    ),
                    risk_override_application=None,
                ),
            )
            mock_executor = MagicMock()
            mock_executor.run.return_value = agent_result
            mock_build_executor.return_value = mock_executor

            result = pipeline._analyze_with_agent(
                code="AAPL",
                report_type=ReportType.SIMPLE,
                query_id="q-agent-daily-final",
                stock_name="Apple",
                realtime_quote=None,
                chip_data=None,
                daily_market_context=DailyMarketContext(
                    region="us",
                    trade_date=date(2026, 7, 19),
                    summary="High risk and risk-off; remain conservative.",
                    risk_tags=["high_risk", "conservative"],
                    source="test",
                ),
            )

            self.assertIsNotNone(result)
            explanation = result.dashboard["agent_disagreement_explanation"]
            self.assertEqual(result.decision_type, "hold")
            self.assertEqual(explanation["risk_control"]["reason"], "not_evaluated")
            self.assertEqual(explanation["risk_control"]["post_risk_signal"], "buy")
            self.assertNotIn("final_signal", explanation)
            self.assertEqual(explanation["final_action"], result.action)
            self.assertEqual(
                explanation["final_adjustments"],
                [
                    {
                        "source": "daily_market_context",
                        "from_action": "buy",
                        "to_action": result.action,
                    }
                ],
            )
            signal_result = (
                pipeline._extract_decision_signal_after_history_save.call_args.kwargs["result"]
            )
            self.assertEqual(signal_result.action, explanation["final_action"])
            from src.application.decision.decision_signal_extractor import (
                build_decision_signal_payload_from_report,
            )
            signal_payload = build_decision_signal_payload_from_report(
                result,
                source_report_id=1,
                trace_id="q-agent-daily-final",
                query_source="test",
                report_type="simple",
                profile_source="auto_default",
            )
            self.assertIsNotNone(signal_payload)
            self.assertEqual(signal_payload["action"], explanation["final_action"])
            self.assertEqual(signal_payload["action"], result.action)

    def test_analyze_with_agent_preserves_chip_structure_when_prefetch_missing(self):
        """Agent tool chip metrics should not be cleared when prefetch chip_data is unavailable."""
        with patch('src.application.analysis.pipeline.get_config') as mock_config, \
             patch('src.application.analysis.pipeline.build_pipeline_persistence_port'), \
             patch('src.application.analysis.pipeline.build_stock_data_port', return_value=MagicMock()), \
             patch('src.application.analysis.pipeline.GeminiAnalyzer'), \
             patch('src.application.analysis.pipeline.NotificationService'), \
             patch('src.application.analysis.pipeline.SearchService'), \
             patch('src.bootstrap.agent.build_agent_executor') as mock_build_executor:

            mock_cfg = MagicMock()
            mock_cfg.max_workers = 2
            mock_cfg.agent_mode = True
            mock_cfg.agent_max_steps = 10
            mock_cfg.agent_skills = []
            mock_cfg.bocha_api_keys = []
            mock_cfg.tavily_api_keys = []
            mock_cfg.brave_api_keys = []
            mock_cfg.serpapi_keys = []
            mock_cfg.searxng_base_urls = []
            mock_cfg.searxng_public_instances_enabled = False
            mock_cfg.news_max_age_days = 7
            mock_cfg.enable_realtime_quote = True
            mock_cfg.enable_chip_distribution = True
            mock_cfg.realtime_source_priority = []
            mock_cfg.save_context_snapshot = False
            mock_cfg.report_language = "zh"
            mock_cfg.report_integrity_enabled = False
            mock_cfg.agent_orchestrator_timeout_s = 600
            mock_config.return_value = mock_cfg

            from src.application.analysis.pipeline import StockAnalysisPipeline
            from src.application.agent.executor import AgentResult
            from src.domain.shared.enums import ReportType
            pipeline = StockAnalysisPipeline(config=mock_cfg)
            pipeline.search_service.is_available = False

            agent_result = AgentResult(
                success=True,
                content="{}",
                dashboard={
                    "sentiment_score": 70,
                    "trend_prediction": "震荡",
                    "operation_advice": "持有",
                    "decision_type": "hold",
                    "dashboard": {
                        "data_perspective": {
                            "chip_structure": {
                                "profit_ratio": "52.0%",
                                "avg_cost": 1850.0,
                                "concentration": "0.00%",
                                "chip_health": "健康",
                            }
                        }
                    },
                },
                provider="gemini",
            )
            mock_executor = MagicMock()
            mock_executor.run.return_value = agent_result
            mock_build_executor.return_value = mock_executor

            result = pipeline._analyze_with_agent(
                code="600519",
                report_type=ReportType.SIMPLE,
                query_id="q-agent-chip",
                stock_name="贵州茅台",
                realtime_quote=None,
                chip_data=None,
            )

            self.assertIsNotNone(result)
            dp = result.dashboard["data_perspective"]
            self.assertEqual(dp["chip_structure"]["concentration"], "0.00%")
            self.assertNotIn("chip_unavailable_reason", dp)

    def test_analyze_with_agent_history_context_includes_diagnostic_snapshot(self):
        """Agent 分析入库存档时应保留 diagnostics 快照，避免历史诊断返回 unknown。"""
        with patch('src.application.analysis.pipeline.get_config') as mock_config, \
             patch('src.application.analysis.pipeline.build_pipeline_persistence_port'), \
             patch('src.application.analysis.pipeline.build_stock_data_port', return_value=MagicMock()), \
             patch('src.application.analysis.pipeline.GeminiAnalyzer'), \
             patch('src.application.analysis.pipeline.NotificationService'), \
             patch('src.application.analysis.pipeline.SearchService'), \
             patch('src.application.analysis.pipeline.fill_price_position_if_needed'), \
             patch('src.application.analysis.pipeline.stabilize_decision_with_structure'), \
             patch('src.application.analysis.pipeline.current_diagnostic_snapshot') as mock_diagnostic_snapshot:

            mock_cfg = MagicMock()
            mock_cfg.max_workers = 2
            mock_cfg.agent_mode = True
            mock_cfg.agent_max_steps = 10
            mock_cfg.agent_skills = []
            mock_cfg.bocha_api_keys = []
            mock_cfg.tavily_api_keys = []
            mock_cfg.anspire_api_keys = []
            mock_cfg.brave_api_keys = []
            mock_cfg.serpapi_keys = []
            mock_cfg.searxng_base_urls = []
            mock_cfg.searxng_public_instances_enabled = False
            mock_cfg.news_max_age_days = 7
            mock_cfg.enable_realtime_quote = True
            mock_cfg.enable_chip_distribution = True
            mock_cfg.realtime_source_priority = []
            mock_cfg.save_context_snapshot = True
            mock_cfg.report_language = "zh"
            mock_cfg.report_integrity_enabled = False
            mock_config.return_value = mock_cfg

            from src.application.agent.runtime_facts import AgentRuntimeFacts, SkillOpinionFact
            from src.application.analysis.pipeline import StockAnalysisPipeline
            from src.domain.shared.enums import ReportType

            pipeline = StockAnalysisPipeline(config=mock_cfg)
            pipeline.search_service.is_available = False
            pipeline._ensure_agent_history = MagicMock()
            pipeline._agent_result_to_analysis_result = MagicMock(
                return_value=SimpleNamespace(
                    success=True,
                    code="588200",
                    name="科创芯片ETF",
                    model_used="agent-model",
                    sentiment_score=70,
                    operation_advice="持有",
                    trend_prediction="震荡",
                    analysis_summary="测试摘要",
                )
            )

            mock_executor = MagicMock()
            mock_executor.run.return_value = SimpleNamespace(
                success=True,
                provider="agent-provider",
                runtime_facts=AgentRuntimeFacts(
                    skill_opinions=(
                        SkillOpinionFact(
                            skill_id="alpha",
                            signal="buy",
                            confidence=0.7,
                        ),
                    ),
                ),
                dashboard={"stock_name": "科创芯片ETF"},
            )
            with patch('src.bootstrap.agent.build_agent_executor', return_value=mock_executor):
                mock_diagnostic_snapshot.return_value = {"trace_id": "trace-1391", "query_id": "q-1391"}
                pipeline.db.save_analysis_history = MagicMock(return_value=1)
                pipeline._persist_skill_opinion_samples_after_history_save = MagicMock()

                result = pipeline._analyze_with_agent(
                    code="588200",
                    report_type=ReportType.SIMPLE,
                    query_id="q-1391",
                    stock_name="科创芯片ETF",
                    realtime_quote=None,
                    chip_data=None,
                )

            self.assertIsNotNone(result)
            call_kwargs = pipeline.db.save_analysis_history.call_args.kwargs
            history_context = call_kwargs["context_snapshot"]
            self.assertIn("diagnostics", history_context)
            self.assertEqual(history_context["diagnostics"]["trace_id"], "trace-1391")
            self.assertEqual(history_context["stock_name"], "科创芯片ETF")
            pipeline._persist_skill_opinion_samples_after_history_save.assert_called_once()
            sample_kwargs = (
                pipeline._persist_skill_opinion_samples_after_history_save.call_args.kwargs
            )
            self.assertIs(
                sample_kwargs["runtime_facts"],
                mock_executor.run.return_value.runtime_facts,
            )
            self.assertEqual(sample_kwargs["analysis_history_id"], 1)
            self.assertEqual(sample_kwargs["stock_code"], "588200")
            self.assertEqual(
                sample_kwargs["analysis_context_pack_overview"]["data_quality"]["level"],
                "poor",
            )
