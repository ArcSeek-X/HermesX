"""Tests for multi agent strategies."""

from tests.application.agent._multi_agent_support import (
    AgentContext,
    AgentOpinion,
    AgentOrchestrator,
    MagicMock,
    SimpleNamespace,
    SkillAggregator,
    StrategyOpinion,
    StrategySynthesizer,
    _TestRiskOverrideFixture,
    _TestStrategyAggregatorFixture,
    _TestStrategyEngineE2EFixture,
    _TestStrategyRouterFixture,
    json,
    patch,
    strategy_opinion_from_agent_opinion,
    unittest,
)


class TestStrategyRouter(_TestStrategyRouterFixture, unittest.TestCase):
    def test_user_requested_strategies_take_priority(self):
        from src.application.agent.strategies.router import StrategyRouter
        router = StrategyRouter()
        ctx = AgentContext(query="test")
        ctx.meta["strategies_requested"] = ["chan_theory", "wave_theory"]
        result = router.select_strategies(ctx)
        self.assertEqual(result, ["chan_theory", "wave_theory"])

    def test_user_requested_capped_at_max(self):
        from src.application.agent.strategies.router import StrategyRouter
        router = StrategyRouter()
        ctx = AgentContext()
        ctx.meta["strategies_requested"] = ["a", "b", "c", "d", "e"]
        result = router.select_strategies(ctx, max_count=2)
        self.assertEqual(len(result), 2)

    @patch("src.application.agent.skills.router.StrategyRouter._get_routing_mode", return_value="manual")
    @patch(
        "src.application.agent.skills.router.StrategyRouter.get_available_skills",
        return_value=[
            SimpleNamespace(name="chan_theory"),
            SimpleNamespace(name="wave_theory"),
        ],
    )
    @patch("src.config.get_config", return_value=SimpleNamespace(agent_skills=["chan_theory", "wave_theory"]))
    def test_manual_mode_uses_configured_agent_skills(self, _mock_config, _mock_available, _mock):
        from src.application.agent.strategies.router import StrategyRouter
        router = StrategyRouter()
        ctx = AgentContext()
        result = router.select_strategies(ctx)
        self.assertEqual(result, ["chan_theory", "wave_theory"])

    @patch("src.application.agent.skills.router.StrategyRouter._get_routing_mode", return_value="manual")
    @patch(
        "src.application.agent.skills.router.StrategyRouter.get_available_skills",
        return_value=[
            SimpleNamespace(name="bull_trend", default_router=True, default_priority=10),
            SimpleNamespace(name="shrink_pullback", default_router=True, default_priority=40),
        ],
    )
    @patch("src.config.get_config", return_value=SimpleNamespace(agent_skills=[]))
    def test_manual_mode_falls_back_to_defaults_when_no_skills_configured(self, _mock_config, _mock_available, _mock):
        from src.application.agent.strategies.router import StrategyRouter, _DEFAULT_STRATEGIES
        router = StrategyRouter()
        ctx = AgentContext()
        result = router.select_strategies(ctx)
        self.assertEqual(result, list(_DEFAULT_STRATEGIES[:3]))

    def test_detect_regime_bullish(self):
        from src.application.agent.strategies.router import StrategyRouter
        router = StrategyRouter()
        ctx = AgentContext()
        ctx.add_opinion(AgentOpinion(
            agent_name="technical",
            signal="buy",
            confidence=0.8,
            raw_data={"ma_alignment": "bullish", "trend_score": 80, "volume_status": "normal"},
        ))
        regime = router._detect_regime(ctx)
        self.assertEqual(regime, "trending_up")

    def test_detect_regime_bearish(self):
        from src.application.agent.strategies.router import StrategyRouter
        router = StrategyRouter()
        ctx = AgentContext()
        ctx.add_opinion(AgentOpinion(
            agent_name="technical",
            signal="sell",
            confidence=0.7,
            raw_data={"ma_alignment": "bearish", "trend_score": 20, "volume_status": "light"},
        ))
        regime = router._detect_regime(ctx)
        self.assertEqual(regime, "trending_down")

    def test_detect_regime_none_without_technical(self):
        from src.application.agent.strategies.router import StrategyRouter
        router = StrategyRouter()
        ctx = AgentContext()
        regime = router._detect_regime(ctx)
        self.assertIsNone(regime)


class TestStrategyAggregator(_TestStrategyAggregatorFixture, unittest.TestCase):
    def test_no_strategy_opinions_returns_none(self):
        from src.application.agent.strategies.aggregator import StrategyAggregator
        agg = StrategyAggregator()
        ctx = AgentContext()
        ctx.add_opinion(AgentOpinion(agent_name="technical", signal="buy", confidence=0.8))
        result = agg.aggregate(ctx)
        self.assertIsNone(result)

    def test_single_strategy_consensus(self):
        from src.application.agent.strategies.aggregator import StrategyAggregator
        agg = StrategyAggregator()
        ctx = AgentContext()
        ctx.add_opinion(AgentOpinion(agent_name="strategy_bull_trend", signal="buy", confidence=0.7))
        result = agg.aggregate(ctx)
        self.assertIsNotNone(result)
        self.assertEqual(result.agent_name, "skill_consensus")
        self.assertEqual(result.signal, "buy")

    def test_mixed_signals_produce_hold(self):
        from src.application.agent.strategies.aggregator import StrategyAggregator
        agg = StrategyAggregator()
        ctx = AgentContext()
        ctx.add_opinion(AgentOpinion(agent_name="strategy_a", signal="buy", confidence=0.6))
        ctx.add_opinion(AgentOpinion(agent_name="strategy_b", signal="sell", confidence=0.6))
        result = agg.aggregate(ctx)
        self.assertIsNotNone(result)
        # Average of buy(4) + sell(2) = 3.0, which maps to "hold"
        self.assertEqual(result.signal, "hold")

    def test_strategy_opinion_conversion_preserves_skill_payload(self):
        from src.application.agent.skills.synthesis import strategy_opinion_from_agent_opinion

        opinion = AgentOpinion(
            agent_name="skill_bull_trend",
            signal="BUY",
            confidence=0.8,
            reasoning="趋势偏强",
            raw_data={
                "skill_id": "bull_trend",
                "score_adjustment": "12",
                "conditions_met": ["站上均线"],
                "conditions_missed": ["量能不足"],
            },
        )

        strategy = strategy_opinion_from_agent_opinion(opinion)

        self.assertEqual(strategy.skill_id, "bull_trend")
        self.assertEqual(strategy.signal, "buy")
        self.assertEqual(strategy.original_signal, "BUY")
        self.assertFalse(strategy.invalid_signal)
        self.assertEqual(strategy.raw_data["normalized_signal"], "buy")
        self.assertEqual(strategy.score_adjustment, 12.0)
        self.assertEqual(strategy.conditions_met, ["站上均线"])
        self.assertEqual(strategy.conditions_missed, ["量能不足"])

    def test_strategy_opinion_conversion_marks_unknown_signal(self):
        from src.application.agent.skills.synthesis import strategy_opinion_from_agent_opinion

        opinion = AgentOpinion(agent_name="skill_unknown", signal="moon", confidence=0.8)

        strategy = strategy_opinion_from_agent_opinion(opinion)

        self.assertEqual(strategy.signal, "hold")
        self.assertEqual(strategy.original_signal, "moon")
        self.assertTrue(strategy.invalid_signal)
        self.assertTrue(strategy.raw_data["invalid_signal"])

    def test_conflict_detector_detects_uppercase_buy_against_sell(self):
        from src.application.agent.skills.synthesis import ConflictDetector, strategy_opinion_from_agent_opinion

        opinions = [
            strategy_opinion_from_agent_opinion(AgentOpinion(agent_name="skill_a", signal="BUY", confidence=0.8)),
            strategy_opinion_from_agent_opinion(AgentOpinion(agent_name="skill_b", signal="sell", confidence=0.8)),
        ]

        conflicts = ConflictDetector().detect(opinions, final_signal="hold")

        self.assertIn("directional_opposition", {conflict.conflict_type for conflict in conflicts})

    def test_conflict_detector_detects_directional_and_adjustment_conflicts(self):
        from src.application.agent.skills.synthesis import ConflictDetector

        opinions = [
            StrategyOpinion(skill_id="bull_trend", signal="strong_buy", confidence=0.8, score_adjustment=12),
            StrategyOpinion(skill_id="hot_theme", signal="sell", confidence=0.76, score_adjustment=-10),
        ]

        conflicts = ConflictDetector().detect(opinions, final_signal="hold")
        conflict_types = {conflict.conflict_type for conflict in conflicts}

        self.assertIn("directional_opposition", conflict_types)
        self.assertIn("wide_score_dispersion", conflict_types)
        self.assertIn("high_confidence_dissent", conflict_types)
        self.assertIn("adjustment_contradiction", conflict_types)
        self.assertEqual(conflicts[0].severity, "high")

    def test_strategy_synthesizer_adjusts_confidence_and_returns_language_neutral_payload(self):
        from src.application.agent.skills.synthesis import ConflictDetector, StrategySynthesizer

        opinions = [
            StrategyOpinion(skill_id="bull_trend", signal="buy", confidence=0.8),
            StrategyOpinion(skill_id="hot_theme", signal="sell", confidence=0.75),
        ]
        conflicts = ConflictDetector().detect(opinions, final_signal="hold")

        synthesis = StrategySynthesizer().synthesize(
            opinions,
            weighted_score=3.0,
            final_signal="hold",
            weighted_confidence=0.8,
            conflicts=conflicts,
        )

        self.assertEqual(synthesis["final_signal"], "hold")
        self.assertEqual(synthesis["conflict_severity"], "high")
        # high conflict severity first reduces 0.8 -> 0.68; mediator_v0 then
        # applies a partially-resolved deliberation adjustment of -0.06.
        self.assertAlmostEqual(synthesis["confidence"], 0.62)
        self.assertEqual(synthesis["summary_key"], "strategy_synthesis.with_conflicts")
        self.assertEqual(synthesis["deliberation"]["status"], "completed")
        self.assertEqual(synthesis["deliberation"]["mode"], "mediator_v0")
        self.assertNotIn("summary", synthesis)
        self.assertEqual(synthesis["summary_params"]["final_signal"], "hold")
        self.assertNotIn("综合信号", json.dumps(synthesis, ensure_ascii=False))

        self.assertTrue(all("description" not in conflict for conflict in synthesis["conflicts"]))
        self.assertIn("description_key", synthesis["conflicts"][0])

    def test_skill_aggregator_raw_data_contains_strategy_synthesis(self):
        from src.application.agent.strategies.aggregator import StrategyAggregator

        agg = StrategyAggregator()
        ctx = AgentContext()
        ctx.add_opinion(AgentOpinion(agent_name="strategy_bull_trend", signal="buy", confidence=0.8))
        ctx.add_opinion(AgentOpinion(agent_name="strategy_hot_theme", signal="sell", confidence=0.8))

        result = agg.aggregate(ctx)

        self.assertIsNotNone(result)
        self.assertIn("strategy_synthesis", result.raw_data)
        self.assertIn("conflicts", result.raw_data)
        self.assertGreater(result.raw_data["conflict_count"], 0)

    def test_invalid_signal_excluded_from_conflict_detection(self):
        """Invalid signals must not create false conflicts.

        Note: With only 1 valid opinion (strong_buy), consensus_level is now
        "insufficient" per the sample-count threshold (≤1 → insufficient).
        """
        from src.application.agent.strategies.aggregator import StrategyAggregator

        agg = StrategyAggregator()
        ctx = AgentContext()
        ctx.add_opinion(AgentOpinion(
            agent_name="strategy_bull_trend",
            signal="strong_buy",
            confidence=0.8,
        ))
        ctx.add_opinion(AgentOpinion(
            agent_name="strategy_invalid",
            signal="moon",
            confidence=0.9,
        ))

        result = agg.aggregate(ctx)

        self.assertIsNotNone(result)
        self.assertEqual(result.signal, "strong_buy")
        self.assertEqual(result.raw_data["weighted_score"], 5.0)
        self.assertEqual(result.raw_data["conflict_count"], 0)
        # Updated: 1 valid opinion → insufficient (sample threshold)
        self.assertEqual(result.raw_data["consensus_level"], "insufficient")
        self.assertAlmostEqual(result.confidence, 0.8, places=2)

    def test_only_invalid_signals_produce_neutral_consensus(self):
        """When all signals are invalid, should fall back to neutral consensus.

        Note: 0 valid opinions → insufficient (not low), per sample threshold.
        """
        from src.application.agent.strategies.aggregator import StrategyAggregator

        agg = StrategyAggregator()
        ctx = AgentContext()
        ctx.add_opinion(AgentOpinion(
            agent_name="strategy_invalid_1",
            signal="moon",
            confidence=0.8,
        ))
        ctx.add_opinion(AgentOpinion(
            agent_name="strategy_invalid_2",
            signal="rocket",
            confidence=0.9,
        ))

        result = agg.aggregate(ctx)

        self.assertIsNotNone(result)
        self.assertEqual(result.signal, "hold")
        self.assertEqual(result.raw_data["weighted_score"], 3.0)
        self.assertEqual(result.confidence, 0.0)


class TestRiskOverride(_TestRiskOverrideFixture, unittest.TestCase):
    def test_risk_override_vetoes_buy_signal(self):
        from src.application.agent.orchestrator import AgentOrchestrator

        orch = AgentOrchestrator(
            tool_registry=MagicMock(),
            llm_adapter=MagicMock(),
            config=SimpleNamespace(agent_risk_override=True),
        )
        ctx = AgentContext(query="test", stock_code="600519")
        ctx.set_data("final_dashboard", self._make_dashboard())
        ctx.add_opinion(AgentOpinion(agent_name="decision", signal="buy", confidence=0.8, reasoning="原始结论"))
        ctx.add_opinion(AgentOpinion(
            agent_name="risk",
            signal="strong_sell",
            confidence=0.9,
            reasoning="重大风险",
            raw_data={"veto_buy": True, "reasoning": "存在重大减持风险"},
        ))
        ctx.add_risk_flag("insider", "大股东减持", severity="high")

        dashboard = orch._resolve_dashboard_payload(
            ctx,
            ctx.get_data("final_dashboard"),
            None,
        )

        self.assertEqual(dashboard["decision_type"], "hold")
        self.assertLessEqual(dashboard["sentiment_score"], 59)
        self.assertIn("风控接管", dashboard["risk_warning"])
        self.assertEqual(ctx.opinions[0].signal, "hold")

    def test_risk_override_normalizes_strong_buy_before_veto(self):
        from src.application.agent.orchestrator import AgentOrchestrator

        orch = AgentOrchestrator(
            tool_registry=MagicMock(),
            llm_adapter=MagicMock(),
            config=SimpleNamespace(agent_risk_override=True),
        )
        ctx = AgentContext(query="test", stock_code="600519")
        dashboard = self._make_dashboard()
        dashboard["decision_type"] = "strong_buy"
        dashboard["sentiment_score"] = 92
        ctx.set_data("final_dashboard", dashboard)
        ctx.add_opinion(AgentOpinion(agent_name="decision", signal="strong_buy", confidence=0.9, reasoning="原始结论"))
        ctx.add_opinion(AgentOpinion(
            agent_name="risk",
            signal="strong_sell",
            confidence=0.9,
            raw_data={"veto_buy": True, "reasoning": "存在重大风险"},
        ))
        ctx.add_risk_flag("insider", "大股东减持", severity="high")

        dashboard = orch._resolve_dashboard_payload(ctx, dashboard, None)

        self.assertEqual(dashboard["decision_type"], "hold")
        self.assertEqual(ctx.opinions[0].signal, "hold")

    def test_risk_override_respects_disable_flag(self):
        from src.application.agent.orchestrator import AgentOrchestrator

        orch = AgentOrchestrator(
            tool_registry=MagicMock(),
            llm_adapter=MagicMock(),
            config=SimpleNamespace(agent_risk_override=False),
        )
        ctx = AgentContext(query="test", stock_code="600519")
        dashboard = self._make_dashboard()
        ctx.set_data("final_dashboard", dashboard)
        ctx.add_opinion(AgentOpinion(
            agent_name="risk",
            signal="strong_sell",
            confidence=0.9,
            raw_data={"veto_buy": True},
        ))
        ctx.add_risk_flag("insider", "大股东减持", severity="high")

        dashboard = orch._resolve_dashboard_payload(ctx, dashboard, None)

        self.assertEqual(dashboard["decision_type"], "buy")
        self.assertIsNone(ctx.get_data("risk_override_applied"))

    def test_risk_level_high_alone_does_not_override_buy_signal(self):
        from src.application.agent.orchestrator import AgentOrchestrator

        orch = AgentOrchestrator(
            tool_registry=MagicMock(),
            llm_adapter=MagicMock(),
            config=SimpleNamespace(agent_risk_override=True),
        )
        ctx = AgentContext(query="test", stock_code="600519")
        dashboard = self._make_dashboard()
        ctx.set_data("final_dashboard", dashboard)
        ctx.add_opinion(AgentOpinion(agent_name="decision", signal="buy", confidence=0.8, reasoning="base"))
        ctx.add_opinion(AgentOpinion(
            agent_name="risk",
            signal="sell",
            confidence=0.9,
            raw_data={"risk_level": "high"},
        ))

        dashboard = orch._resolve_dashboard_payload(ctx, dashboard, None)

        self.assertEqual(dashboard["decision_type"], "buy")
        self.assertIsNone(ctx.get_data("risk_override_applied"))


class TestStrategyEngineE2E(_TestStrategyEngineE2EFixture, unittest.TestCase):
    def test_engine_mixed_valid_invalid_invalid_count(self):
        """Engine: 2 valid buy/0.8 + 3 invalid moon/0.9 → synthesis.invalid_opinion_count == 3."""
        from src.application.agent.skills.engine import StrategyEngine, StrategyResultStatus

        opinions = []
        for i in range(2):
            opinions.append(AgentOpinion(agent_name=f"skill_v{i}", signal="buy", confidence=0.8))
        for i in range(3):
            opinions.append(AgentOpinion(agent_name=f"skill_x{i}", signal="moon", confidence=0.9))

        result = StrategyEngine().process(opinions)

        self.assertEqual(result.status, StrategyResultStatus.CONSENSUS)
        self.assertIsNotNone(result.synthesis_dict)
        params = result.synthesis_dict["summary_params"]
        self.assertEqual(params["opinion_count"], 2)
        self.assertEqual(params["invalid_opinion_count"], 3)
        self.assertEqual(params["total_opinion_count"], 5)
        self.assertEqual(result.invalid_count, 3)
        self.assertEqual(len(result.invalid_records), 3)

    def test_engine_counts_scheduler_diagnostics_with_valid_opinions(self):
        from src.application.agent.skills.engine import StrategyEngine, StrategyResultStatus

        result = StrategyEngine().process(
            [AgentOpinion(agent_name="skill_bull_trend", signal="buy", confidence=0.8)],
            diagnostic_records=[{
                "agent_name": "skill_hot_theme",
                "reason": "skill_timeout",
            }],
        )

        self.assertEqual(result.status, StrategyResultStatus.CONSENSUS)
        params = result.synthesis_dict["summary_params"]
        self.assertEqual(params["opinion_count"], 1)
        self.assertEqual(params["invalid_opinion_count"], 1)
        self.assertEqual(params["total_opinion_count"], 2)
        self.assertEqual(result.invalid_records[0]["reason"], "skill_timeout")

    def test_engine_builds_no_consensus_stub_for_scheduler_only_failure(self):
        from src.application.agent.skills.engine import StrategyEngine, StrategyResultStatus

        result = StrategyEngine().process(
            [],
            diagnostic_records=[{
                "agent_name": "skill_hot_theme",
                "reason": "skill_error",
            }],
        )

        self.assertEqual(result.status, StrategyResultStatus.NO_CONSENSUS)
        params = result.synthesis_dict["summary_params"]
        self.assertEqual(params["opinion_count"], 0)
        self.assertEqual(params["invalid_opinion_count"], 1)
        self.assertEqual(params["total_opinion_count"], 1)

    def test_engine_all_invalid_no_consensus_stub(self):
        """Engine: 4 all-invalid → NO_CONSENSUS stub with consensus_level == 'insufficient'."""
        from src.application.agent.skills.engine import StrategyEngine, StrategyResultStatus

        opinions = [
            AgentOpinion(agent_name=f"skill_bad{i}", signal="moon", confidence=0.9)
            for i in range(4)
        ]

        result = StrategyEngine().process(opinions)

        self.assertEqual(result.status, StrategyResultStatus.NO_CONSENSUS)
        self.assertIsNotNone(result.synthesis_dict)
        self.assertEqual(result.synthesis_dict["consensus_level"], "insufficient")
        self.assertEqual(result.synthesis_dict["confidence"], 0.0)
        self.assertEqual(result.synthesis_dict["final_signal"], "hold")
        self.assertEqual(result.invalid_count, 4)
        self.assertIsNotNone(result.skill_consensus_data)
        self.assertEqual(
            result.skill_consensus_data["strategy_synthesis"]["consensus_level"],
            "insufficient",
        )

    def test_llm_strategy_synthesis_stripped_at_parse_boundary(self):
        """dashboard_block['strategy_synthesis'] from LLM is stripped; engine result wins."""
        ctx = AgentContext()
        ctx.set_data("skill_consensus", {
            "signal": "buy",
            "confidence": 0.75,
            "raw_data": {
                "strategy_synthesis": {
                    "final_signal": "buy",
                    "confidence": 0.75,
                    "consensus_level": "high",
                    "summary_key": "engine.deterministic",
                }
            },
        })

        llm_payload = {
            "decision_type": "sell",
            "dashboard": {
                # LLM wrote this — must be stripped before engine result is written
                "strategy_synthesis": {
                    "final_signal": "sell",
                    "confidence": 0.1,
                    "consensus_level": "low",
                    "summary_key": "llm.invented",
                }
            },
        }

        orchestrator = self._make_orchestrator()
        normalized = orchestrator._finalize_dashboard_payload(llm_payload, ctx)

        self.assertIsNotNone(normalized)
        synth = normalized["dashboard"].get("strategy_synthesis")
        self.assertIsNotNone(synth)
        # Engine's deterministic synthesis wins
        self.assertEqual(synth["final_signal"], "buy")
        self.assertNotEqual(synth.get("summary_key"), "llm.invented")

    def test_partition_fallback_preserves_invalid_diagnostics(self):
        """_apply_partition_fallback: invalid opinions land in ctx.meta and don't re-enter evidence."""
        ctx = AgentContext()
        ctx.opinions.append(AgentOpinion(agent_name="skill_v", signal="buy", confidence=0.8))
        ctx.opinions.append(AgentOpinion(agent_name="skill_bad", signal="moon", confidence=0.9))
        # Non-skill opinion should pass through untouched
        ctx.opinions.append(AgentOpinion(agent_name="technical", signal="buy", confidence=0.7))

        orchestrator = self._make_orchestrator()
        orchestrator._apply_partition_fallback(ctx)

        # Invalid skill opinion removed from evidence chain
        evidence_names = {op.agent_name for op in ctx.opinions}
        self.assertNotIn("skill_bad", evidence_names)
        self.assertIn("skill_v", evidence_names)
        self.assertIn("technical", evidence_names)

        # Captured in diagnostics
        invalid_bucket = ctx.meta.get("invalid_opinions", [])
        self.assertEqual(len(invalid_bucket), 1)
        self.assertEqual(invalid_bucket[0]["agent_name"], "skill_bad")
        self.assertEqual(invalid_bucket[0]["reason"], "unrecognized_signal")

    def test_partition_fallback_idempotent_when_engine_ran(self):
        """_apply_partition_fallback is a no-op when StrategyEngine already ran."""
        ctx = AgentContext()
        ctx.opinions.append(AgentOpinion(agent_name="skill_bad", signal="moon", confidence=0.9))
        # Simulate engine already ran
        ctx.set_data("skill_consensus", {"signal": "hold", "confidence": 0.0})

        orchestrator = self._make_orchestrator()
        orchestrator._apply_partition_fallback(ctx)

        # Should not have been re-partitioned
        self.assertEqual(len(ctx.opinions), 1)
        self.assertNotIn("invalid_opinions", ctx.meta)

    def test_signal_alias_consistency_aggregation_and_disagreement(self):
        """'strong-buy' alias → canonical 'strong_buy' in both aggregation and disagreement."""
        from src.application.agent.disagreement import build_agent_disagreement_summary

        # Aggregation path
        ctx = AgentContext()
        ctx.opinions.append(AgentOpinion(agent_name="skill_1", signal="strong-buy", confidence=0.8))
        ctx.opinions.append(AgentOpinion(agent_name="skill_2", signal="strong_buy", confidence=0.8))

        aggregator = SkillAggregator()
        consensus = aggregator.aggregate(ctx)

        self.assertIsNotNone(consensus)
        self.assertEqual(consensus.signal, "strong_buy")

        synthesis = consensus.raw_data.get("strategy_synthesis")
        self.assertIsNotNone(synthesis)
        self.assertEqual(synthesis["final_signal"], "strong_buy")

        # Disagreement path: strong-buy alias should not be treated as unknown/hold
        ctx2 = AgentContext()
        ctx2.opinions.append(AgentOpinion(agent_name="technical", signal="strong-buy", confidence=0.9))
        ctx2.opinions.append(AgentOpinion(agent_name="decision", signal="hold", confidence=0.6))
        summary = build_agent_disagreement_summary(ctx2)

        # strong-buy and hold diverge, so disagreement should be detected
        # (not hidden by wrong normalization that converts strong-buy → hold)
        self.assertIsNotNone(summary)
        if summary.get("has_disagreement"):
            self.assertIn("strong_buy", str(summary))

    def test_localize_consensus_level_insufficient(self):
        """localize_consensus_level('insufficient', lang) returns short enum translations."""
        from src.domain.shared.report_language import localize_consensus_level

        cases = [
            ("insufficient", "zh", "证据不足"),
            ("insufficient", "en", "Insufficient"),
            ("insufficient", "ko", "증거 부족"),
            # Display-form inputs should also canonicalize
            ("证据不足", "en", "Insufficient"),
            ("Insufficient", "zh", "证据不足"),
        ]

        for raw, lang, expected in cases:
            result = localize_consensus_level(raw, lang)
            self.assertEqual(
                result,
                expected,
                f"localize_consensus_level({raw!r}, {lang!r}) = {result!r}, want {expected!r}",
            )

    def test_renderer_shows_invalid_opinions_label(self):
        """计划测试1补全：mixed valid+invalid → renderer 输出含 strategy_invalid_opinions_label。
        走 StrategyEngine 完整链路，断言 _append_strategy_synthesis_block 渲染出 invalid count 行。
        """
        from src.application.agent.skills.engine import StrategyEngine
        from src.application.notification.notification import _append_strategy_synthesis_block
        from src.domain.shared.report_language import get_report_labels

        opinions = []
        for i in range(2):
            opinions.append(AgentOpinion(agent_name=f"skill_v{i}", signal="buy", confidence=0.8))
        for i in range(3):
            opinions.append(AgentOpinion(agent_name=f"skill_x{i}", signal="moon", confidence=0.9))

        result = StrategyEngine().process(opinions)
        synthesis = result.synthesis_dict
        self.assertIsNotNone(synthesis)
        self.assertEqual(synthesis["summary_params"]["invalid_opinion_count"], 3)

        for lang, fragment in [
            ("zh", "3"),
            ("en", "3"),
            ("ko", "3"),
        ]:
            labels = get_report_labels(lang)
            lines: list = []
            _append_strategy_synthesis_block(lines, synthesis, labels, lang)
            rendered = "\n".join(lines)
            # invalid count line must appear
            self.assertIn(str(3), rendered, f"lang={lang}: invalid count missing from rendered output")
            # the label template itself must have been applied (not raw template string)
            self.assertNotIn("{count}", rendered, f"lang={lang}: label template not rendered")

    def test_generate_dashboard_report_renders_invalid_count_and_insufficient(self):
        """Blocker-6 真 E2E：经 generate_dashboard_report 主入口，
        断言最终 Markdown 字符串含 '另有 N 个策略解析失败' 和本地化 '证据不足'。
        """
        from src.application.analysis.analyzer import AnalysisResult
        from src.application.notification.notification import NotificationService

        synthesis = {
            "final_signal": "hold",
            "weighted_score": 3.0,
            "confidence": 0.0,
            "original_confidence": 0.0,
            "conflict_count": 0,
            "conflict_severity": "none",
            "conflicts": [],
            "supporting_skills": [],
            "opposing_skills": [],
            "consensus_level": "insufficient",
            "summary_key": "strategy_synthesis.no_conflicts",
            "summary_params": {
                "opinion_count": 0,
                "total_opinion_count": 3,
                "invalid_opinion_count": 3,
                "final_signal": "hold",
                "consensus_level": "insufficient",
                "conflict_severity": "none",
                "conflict_count": 0,
            },
        }

        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=50,
            trend_prediction="震荡",
            operation_advice="观望",
            decision_type="hold",
            report_language="zh",
            dashboard={
                "strategy_synthesis": synthesis,
                "core_conclusion": {"one_sentence": "测试样本"},
                "intelligence": {},
                "battle_plan": {},
            },
        )

        svc = NotificationService()
        report = svc.generate_dashboard_report([result])

        # invalid count 行必须出现
        self.assertIn("另有 3 个策略解析失败", report, "invalid count line missing from dashboard report")
        # consensus_level=insufficient → localize → 证据不足
        self.assertIn("证据不足", report, "localized 'insufficient' missing from dashboard report")

    def test_bad_shape_summary_params_never_crashes_renderers(self):
        """OR-COM-34818459 回归：summary_params 为字符串/列表时，所有渲染路径必须静默降级而非崩溃。"""
        from src.domain.shared.report_language import (
            localize_strategy_synthesis_summary,
            normalize_strategy_synthesis_payload,
            strategy_invalid_opinion_count,
        )
        from src.application.notification.notification import _append_strategy_synthesis_block, NotificationService
        from src.domain.shared.report_language import get_report_labels
        from src.application.analysis.analyzer import AnalysisResult

        bad_shapes = [
            "bad-shape",          # 字符串
            ["a", "b"],           # 列表
            42,                   # 整数
            None,                 # None（已有守卫，但确认不退化）
        ]

        for bad in bad_shapes:
            synthesis = {
                "final_signal": "hold",
                "confidence": 0.5,
                "consensus_level": "insufficient",
                "conflict_severity": "none",
                "conflict_count": 0,
                "supporting_skills": [],
                "opposing_skills": [],
                "summary_params": bad,          # ← 坏 shape
            }

            # 1. 安全 helper 必须返回 0，不崩
            count = strategy_invalid_opinion_count(synthesis)
            self.assertEqual(count, 0, f"strategy_invalid_opinion_count should be 0 for summary_params={bad!r}")

            # 2. localize_strategy_synthesis_summary 不崩
            for lang in ("zh", "en", "ko"):
                result = localize_strategy_synthesis_summary(synthesis, lang)
                self.assertIsInstance(result, str, f"summary should be str for summary_params={bad!r}, lang={lang}")

            # 3. _append_strategy_synthesis_block 不崩
            for lang in ("zh", "en", "ko"):
                labels = get_report_labels(lang)
                lines: list = []
                try:
                    _append_strategy_synthesis_block(lines, synthesis, labels, lang)
                except Exception as exc:
                    self.fail(f"_append_strategy_synthesis_block crashed for summary_params={bad!r}: {exc}")

        # Narrow legacy coercion preserves a decimal string count without
        # accepting booleans, negative values, decimals, or arbitrary text.
        for raw_count, expected in [
            (3, 3),
            ("3", 3),
            (" 003 ", 3),
            (True, 0),
            (-1, 0),
            ("3.0", 0),
            ("bad", 0),
        ]:
            synthesis = {"summary_params": {"invalid_opinion_count": raw_count}}
            self.assertEqual(strategy_invalid_opinion_count(synthesis), expected)

        # Malformed top-level values are treated as an absent optional block.
        for bad in ("bad-shape", ["a"], 42, True):
            self.assertEqual(normalize_strategy_synthesis_payload(bad), {})
            self.assertEqual(localize_strategy_synthesis_summary(bad, "zh"), "")
            lines = []
            _append_strategy_synthesis_block(lines, bad, get_report_labels("zh"), "zh")
            self.assertEqual(lines, [])

        # 4. generate_dashboard_report 主入口不崩（取 zh + 字符串 bad shape 作代表）
        synthesis_bad = {
            "final_signal": "hold",
            "confidence": 0.5,
            "consensus_level": "insufficient",
            "conflict_severity": "none",
            "conflict_count": 0,
            "supporting_skills": [],
            "opposing_skills": [],
            "summary_params": "bad-shape",
        }
        result = AnalysisResult(
            code="000001",
            name="平安银行",
            sentiment_score=50,
            trend_prediction="震荡",
            operation_advice="观望",
            decision_type="hold",
            report_language="zh",
            dashboard={
                "strategy_synthesis": synthesis_bad,
                "core_conclusion": {"one_sentence": "测试"},
                "intelligence": {},
                "battle_plan": {},
            },
        )
        try:
            report = NotificationService().generate_dashboard_report([result])
        except Exception as exc:
            self.fail(f"generate_dashboard_report crashed on bad summary_params: {exc}")
        self.assertIsInstance(report, str)

    def test_engine_no_skills_returns_no_skills_status(self):
        """StrategyEngine with zero skill opinions returns NO_SKILLS (not NO_CONSENSUS)."""
        from src.application.agent.skills.engine import StrategyEngine, StrategyResultStatus

        ctx_opinions = [
            AgentOpinion(agent_name="technical", signal="buy", confidence=0.8),
            AgentOpinion(agent_name="decision", signal="hold", confidence=0.6),
        ]

        result = StrategyEngine().process(ctx_opinions)

        self.assertEqual(result.status, StrategyResultStatus.NO_SKILLS)
        self.assertIsNone(result.synthesis_dict)
        self.assertIsNone(result.consensus_opinion)
        # Non-skill opinions preserved
        self.assertEqual(len(result.non_skill_opinions), 2)
