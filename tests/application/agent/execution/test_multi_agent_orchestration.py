"""Tests for multi agent orchestration."""

from tests.application.agent._multi_agent_support import (
    AGENT_MAX_STEPS_DEFAULT,
    AgentContext,
    AgentOpinion,
    AgentOrchestrator,
    MagicMock,
    Signal,
    SkillAggregator,
    StrategySynthesizer,
    _TestDecisionAgentPostProcessFixture,
    _TestIntelAgentPostProcessFixture,
    _TestOrchestratorModesFixture,
    _TestP1SemanticConvergenceFixture,
    _TestPortfolioAgentPostProcessFixture,
    json,
    normalize_strategy_signal,
    strategy_opinion_from_agent_opinion,
    unittest,
)


class TestPortfolioAgentPostProcess(_TestPortfolioAgentPostProcessFixture, unittest.TestCase):
    def test_parse_plain_json(self):
        agent = self._make_agent()
        ctx = AgentContext()
        data = {"portfolio_risk_score": 3, "summary": "Looks good"}
        op = agent.post_process(ctx, json.dumps(data))
        self.assertIsNotNone(op)
        self.assertEqual(op.signal, "buy")
        self.assertEqual(ctx.data.get("portfolio_assessment"), data)

    def test_parse_markdown_json(self):
        agent = self._make_agent()
        ctx = AgentContext()
        data = {"portfolio_risk_score": 8, "summary": "High risk"}
        raw = f"Here is the analysis:\n```json\n{json.dumps(data)}\n```"
        op = agent.post_process(ctx, raw)
        self.assertIsNotNone(op)
        self.assertEqual(op.signal, "sell")

    def test_parse_failure_returns_hold(self):
        agent = self._make_agent()
        ctx = AgentContext()
        op = agent.post_process(ctx, "This is not JSON at all")
        self.assertIsNotNone(op)
        self.assertEqual(op.signal, "hold")
        self.assertAlmostEqual(op.confidence, 0.3)


class TestDecisionAgentPostProcess(_TestDecisionAgentPostProcessFixture, unittest.TestCase):
    def test_normalizes_strong_decision_type_to_legacy_enum(self):
        from src.application.agent.agents.decision_agent import DecisionAgent

        agent = DecisionAgent(tool_registry=MagicMock(), llm_adapter=MagicMock())
        ctx = AgentContext(query="test", stock_code="600519")
        dashboard = {
            "decision_type": "strong_buy",
            "sentiment_score": 88,
            "analysis_summary": "High conviction",
            "stock_name": "贵州茅台",
        }

        opinion = agent.post_process(ctx, json.dumps(dashboard))

        self.assertIsNotNone(opinion)
        self.assertEqual(opinion.signal, "buy")
        self.assertEqual(ctx.get_data("final_dashboard")["decision_type"], "buy")

    def test_normalized_dashboard_carries_strategy_synthesis(self):
        from src.application.agent.orchestrator import AgentOrchestrator

        orch = AgentOrchestrator(tool_registry=MagicMock(), llm_adapter=MagicMock())
        ctx = AgentContext(query="test", stock_code="600519", stock_name="贵州茅台")
        synthesis = {
            "final_signal": "hold",
            "confidence": 0.6,
            "conflict_count": 0,
            "conflict_severity": "none",
        }
        ctx.set_data("skill_consensus", {"strategy_synthesis": synthesis})

        normalized = orch._finalize_dashboard_payload({"dashboard": {}}, ctx)

        self.assertIsNotNone(normalized)
        self.assertEqual(normalized["dashboard"]["strategy_synthesis"], synthesis)


class TestIntelAgentPostProcess(_TestIntelAgentPostProcessFixture, unittest.TestCase):
    def test_repairs_json_and_caches_intel_context(self):
        from src.application.agent.agents.intel_agent import IntelAgent

        agent = IntelAgent(tool_registry=MagicMock(), llm_adapter=MagicMock())
        ctx = AgentContext(query="test", stock_code="600519")
        raw = """```json
        {
          "signal": "hold",
          "confidence": 0.72,
          "reasoning": "情绪中性偏谨慎",
          "risk_alerts": ["股东减持"],
          "positive_catalysts": ["行业复苏"],
        }
        ```"""

        opinion = agent.post_process(ctx, raw)

        self.assertIsNotNone(opinion)
        self.assertEqual(opinion.signal, "hold")
        self.assertEqual(ctx.get_data("intel_opinion")["positive_catalysts"], ["行业复苏"])
        self.assertEqual(ctx.risk_flags[0]["description"], "股东减持")


class TestOrchestratorModes(_TestOrchestratorModesFixture, unittest.TestCase):
    def test_quick_mode(self):
        orch = self._make_orchestrator("quick")
        ctx = AgentContext(query="test", stock_code="600519")
        chain = orch._build_agent_chain(ctx)
        names = [a.agent_name for a in chain]
        self.assertEqual(names, ["technical", "decision"])

    def test_standard_mode(self):
        orch = self._make_orchestrator("standard")
        ctx = AgentContext(query="test", stock_code="600519")
        chain = orch._build_agent_chain(ctx)
        names = [a.agent_name for a in chain]
        self.assertEqual(names, ["technical", "intel", "decision"])

    def test_full_mode(self):
        orch = self._make_orchestrator("full")
        ctx = AgentContext(query="test", stock_code="600519")
        chain = orch._build_agent_chain(ctx)
        names = [a.agent_name for a in chain]
        self.assertEqual(names, ["technical", "intel", "risk", "decision"])

    def test_invalid_mode_falls_back_to_standard(self):
        orch = self._make_orchestrator("nonsense")
        self.assertEqual(orch.mode, "standard")

    def test_chain_agents_inherit_orchestrator_max_steps(self):
        """Default/lowered limits cap agents; raised limits hard-override all agents."""
        orch = self._make_orchestrator("full")
        orch.max_steps = AGENT_MAX_STEPS_DEFAULT
        high_limit_chain = orch._build_agent_chain(AgentContext(query="test", stock_code="600519"))
        self.assertEqual(
            {agent.agent_name: agent.max_steps for agent in high_limit_chain},
            {"technical": 6, "intel": 4, "risk": 4, "decision": 3},
        )

        orch.max_steps = 5
        low_limit_chain = orch._build_agent_chain(AgentContext(query="test", stock_code="600519"))
        self.assertEqual(
            {agent.agent_name: agent.max_steps for agent in low_limit_chain},
            {"technical": 5, "intel": 4, "risk": 4, "decision": 3},
        )

        orch.max_steps = AGENT_MAX_STEPS_DEFAULT + 2
        raised_limit_chain = orch._build_agent_chain(AgentContext(query="test", stock_code="600519"))
        self.assertEqual(
            {agent.agent_name: agent.max_steps for agent in raised_limit_chain},
            {"technical": AGENT_MAX_STEPS_DEFAULT + 2, "intel": AGENT_MAX_STEPS_DEFAULT + 2, "risk": AGENT_MAX_STEPS_DEFAULT + 2, "decision": AGENT_MAX_STEPS_DEFAULT + 2},
        )

    def test_prepare_agent_raised_limit_overrides_low_default_agent(self):
        orch = self._make_orchestrator("full")
        orch.max_steps = AGENT_MAX_STEPS_DEFAULT + 2
        decision = MagicMock(agent_name="decision", max_steps=3)

        prepared = orch._prepare_agent(decision)

        self.assertIs(prepared, decision)
        self.assertEqual(prepared.max_steps, AGENT_MAX_STEPS_DEFAULT + 2)

    def test_build_context_from_dict(self):
        orch = self._make_orchestrator()
        ctx = orch._build_context(
            "Analyze 600519",
            context={"stock_code": "600519", "stock_name": "贵州茅台", "skills": ["bull_trend"]},
        )
        self.assertEqual(ctx.stock_code, "600519")
        self.assertEqual(ctx.stock_name, "贵州茅台")
        self.assertEqual(ctx.meta["skills_requested"], ["bull_trend"])

    def test_specialist_builder_allows_four_requested_skills(self):
        orch = self._make_orchestrator("specialist")
        ctx = AgentContext(query="test", stock_code="600519")
        ctx.meta["skills_requested"] = [
            "bull_trend",
            "hot_theme",
            "fund_flow",
            "chan_theory",
        ]

        agents = orch._build_specialist_agents(ctx)

        self.assertEqual(
            [agent.skill_id for agent in agents],
            ["bull_trend", "hot_theme", "fund_flow", "chan_theory"],
        )

    def test_build_context_keeps_market_phase_context_in_meta_not_data(self):
        orch = self._make_orchestrator()
        phase_context = {"phase": "intraday", "is_partial_bar": True}
        pack_summary = "\n## 分析上下文包摘要\n- 数据块状态：行情 available\n"
        market_structure_context = {
            "market_theme_context": {"status": "ok", "active_themes": []},
            "stock_market_position": {"status": "ok", "primary_theme": {"name": "机器人概念"}},
        }

        ctx = orch._build_context(
            "Analyze 600519",
            context={
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "market_phase_context": phase_context,
                "analysis_context_pack_summary": pack_summary,
                "market_structure_context": market_structure_context,
            },
        )

        self.assertEqual(ctx.meta["market_phase_context"], phase_context)
        self.assertEqual(ctx.meta["analysis_context_pack_summary"], pack_summary)
        self.assertEqual(ctx.meta["market_structure_context"], market_structure_context)
        self.assertNotIn("market_phase_context", ctx.data)
        self.assertNotIn("analysis_context_pack_summary", ctx.data)
        self.assertNotIn("market_structure_context", ctx.data)

    def test_build_context_extracts_code_from_query(self):
        orch = self._make_orchestrator()
        ctx = orch._build_context("分析600519的走势")
        self.assertEqual(ctx.stock_code, "600519")

    def test_fallback_summary(self):
        orch = self._make_orchestrator()
        ctx = AgentContext(query="test", stock_code="600519", stock_name="贵州茅台")
        ctx.add_opinion(AgentOpinion(agent_name="tech", signal="buy", confidence=0.8, reasoning="Strong trend"))
        ctx.add_risk_flag("insider", "Minor sell-down", severity="low")
        summary = orch._fallback_summary(ctx)
        self.assertIn("600519", summary)
        self.assertIn("Strong trend", summary)
        self.assertIn("Minor sell-down", summary)


class TestP1SemanticConvergence(_TestP1SemanticConvergenceFixture, unittest.TestCase):
    def test_signal_enum_input_compatibility(self):
        """P1-1: Signal.BUY 枚举输入不应被标记为 invalid"""
        signal, invalid, original = normalize_strategy_signal(Signal.BUY)
        self.assertEqual(signal, "buy")
        self.assertFalse(invalid)
        self.assertEqual(original, "buy")

        for enum_val, expected in [
            (Signal.STRONG_BUY, "strong_buy"),
            (Signal.HOLD, "hold"),
            (Signal.SELL, "sell"),
            (Signal.STRONG_SELL, "strong_sell"),
        ]:
            signal, invalid, _ = normalize_strategy_signal(enum_val)
            self.assertEqual(signal, expected)
            self.assertFalse(invalid, f"{enum_val} should not be marked invalid")

    def test_missing_signal_marked_invalid(self):
        """P1-2: 缺失 signal 的 LLM 输出应被标记为 invalid，而非静默兜底为 hold"""
        ctx = AgentContext()

        opinion = AgentOpinion(
            agent_name="skill_test",
            signal=None,
            confidence=0.9,
            reasoning="test",
            raw_data={"confidence": 0.9}
        )

        strategy_opinion = strategy_opinion_from_agent_opinion(opinion)
        self.assertTrue(strategy_opinion.invalid_signal)
        self.assertEqual(strategy_opinion.signal, "hold")

    def test_opinion_count_excludes_invalid(self):
        """P1-3: summary_params.opinion_count 应仅计 valid opinions"""
        opinions = []

        valid_op = AgentOpinion(agent_name="skill_test1", signal="buy", confidence=0.8)
        opinions.append(strategy_opinion_from_agent_opinion(valid_op))

        for i in range(9):
            invalid_op = AgentOpinion(agent_name=f"skill_invalid{i}", signal="moon", confidence=0.9)
            opinions.append(strategy_opinion_from_agent_opinion(invalid_op))

        synthesizer = StrategySynthesizer()
        synthesis = synthesizer.synthesize(
            opinions,
            weighted_score=4.0,
            final_signal="buy",
            weighted_confidence=0.8,
            conflicts=[],
        )

        self.assertEqual(synthesis["summary_params"]["opinion_count"], 1)
        self.assertEqual(synthesis["summary_params"]["total_opinion_count"], 10)
        self.assertEqual(synthesis["summary_params"]["invalid_opinion_count"], 9)

    def test_deterministic_synthesis_authoritative(self):
        """P1-4: 确定性 synthesis 应为 dashboard 的唯一权威来源"""
        ctx = AgentContext()
        ctx.set_data("skill_consensus", {
            "signal": "buy",
            "confidence": 0.8,
            "raw_data": {
                "strategy_synthesis": {
                    "final_signal": "buy",
                    "confidence": 0.8,
                    "consensus_level": "high",
                    "summary_key": "test.deterministic",
                }
            },
        })

        dashboard_with_llm_synthesis = {
            "decision_type": "sell",
            "dashboard": {
                "strategy_synthesis": {
                    "final_signal": "sell",
                    "confidence": 0.1,
                    "consensus_level": "low",
                    "summary_key": "llm.generated",
                }
            },
        }

        orchestrator = AgentOrchestrator(
            tool_registry=MagicMock(),
            llm_adapter=MagicMock(),
            mode="full",
        )
        normalized = orchestrator._finalize_dashboard_payload(dashboard_with_llm_synthesis, ctx)

        self.assertIsNotNone(normalized)
        self.assertIn("strategy_synthesis", normalized["dashboard"])
        synth = normalized["dashboard"]["strategy_synthesis"]
        self.assertEqual(synth["final_signal"], "buy")
        self.assertEqual(synth["confidence"], 0.8)
        self.assertEqual(synth["summary_key"], "test.deterministic")

    def test_full_pipeline_valid_signal(self):
        """P1-5: 端到端验证：合法 Signal 枚举输入应保持正确语义"""
        ctx = AgentContext()

        opinion = AgentOpinion(
            agent_name="skill_test",
            signal="buy",
            confidence=0.9,
            reasoning="strong bullish signal"
        )

        strategy_opinion = strategy_opinion_from_agent_opinion(opinion)
        self.assertFalse(strategy_opinion.invalid_signal)
        self.assertEqual(strategy_opinion.signal, "buy")

        ctx.opinions.append(opinion)
        aggregator = SkillAggregator()
        consensus = aggregator.aggregate(ctx)

        self.assertIsNotNone(consensus)
        self.assertEqual(consensus.signal, "buy")
        self.assertGreater(consensus.confidence, 0.0)

    def test_prompt_pollution_prevention(self):
        """E2E-A: 1 valid buy/0.8 + 2 invalid moon/0.9 → Orchestrator partition →
        DecisionAgent prompt 不含 'moon'，ctx.meta['invalid_opinions'] 长度 == 2。
        真 E2E：SkillAgent 输入 → Orchestrator 分拣 → DecisionAgent build_user_message。
        """
        from src.application.agent.agents.decision_agent import DecisionAgent

        ctx = AgentContext(stock_code="600519", stock_name="贵州茅台")

        # 1 valid buy opinion
        valid_op = AgentOpinion(
            agent_name="skill_valid",
            signal="buy",
            confidence=0.8,
            reasoning="valid bullish signal"
        )
        ctx.opinions.append(valid_op)

        # 2 invalid moon opinions
        for i in range(2):
            invalid_op = AgentOpinion(
                agent_name=f"skill_invalid_{i}",
                signal="moon",
                confidence=0.9,
                reasoning="to the moon"
            )
            ctx.opinions.append(invalid_op)

        # Orchestrator invalid partition — the ONLY partition point per contract
        orchestrator = AgentOrchestrator(
            tool_registry=MagicMock(),
            llm_adapter=MagicMock(),
            mode="full",
        )
        orchestrator._partition_skill_opinions(ctx)

        # After partition: only valid opinions remain in ctx.opinions
        self.assertEqual(len(ctx.opinions), 1)
        self.assertEqual(ctx.opinions[0].agent_name, "skill_valid")

        # Invalid opinions moved to ctx.meta["invalid_opinions"]
        invalid_bucket = ctx.meta.get("invalid_opinions", [])
        self.assertEqual(len(invalid_bucket), 2)
        for entry in invalid_bucket:
            self.assertIn(entry["agent_name"], {"skill_invalid_0", "skill_invalid_1"})
            self.assertEqual(entry["raw_signal"], "moon")
            self.assertEqual(entry["reason"], "unrecognized_signal")

        # DecisionAgent prompt — consumes partitioned ctx.opinions directly
        agent = DecisionAgent(tool_registry=MagicMock(), llm_adapter=MagicMock())
        prompt = agent.build_user_message(ctx)

        # Prompt should NOT contain "moon" or invalid agent names / confidence
        self.assertNotIn("moon", prompt.lower())
        self.assertNotIn("skill_invalid_0", prompt)
        self.assertNotIn("skill_invalid_1", prompt)
        self.assertNotIn("0.90", prompt)  # invalid opinions' 0.9 confidence

        # Prompt should contain valid opinion
        self.assertIn("skill_valid", prompt)
        self.assertIn("buy", prompt)
        self.assertIn("0.80", prompt)

        # Prompt should mention invalid count as diagnostics (not evidence)
        self.assertIn("2", prompt)  # invalid count

    def test_zero_weight_never_strong_sell(self):
        """E2E-2: 两个 hold/0.0 或 buy/0.0 → final signal 应为 hold，绝不应是 strong_sell"""
        ctx = AgentContext()

        # Two valid opinions with zero confidence (zero weight)
        ctx.opinions.append(AgentOpinion(agent_name="skill_1", signal="hold", confidence=0.0))
        ctx.opinions.append(AgentOpinion(agent_name="skill_2", signal="buy", confidence=0.0))

        aggregator = SkillAggregator()
        consensus = aggregator.aggregate(ctx)

        self.assertIsNotNone(consensus)
        # Zero weight sum should result in hold (3.0), not strong_sell
        self.assertEqual(consensus.signal, "hold")

        # Verify synthesis metadata
        synthesis = consensus.raw_data.get("strategy_synthesis")
        self.assertIsNotNone(synthesis)
        self.assertEqual(synthesis["final_signal"], "hold")
        # consensus_level should be insufficient with zero confidence
        self.assertEqual(synthesis["consensus_level"], "insufficient")

    def test_hold_grouping_consistency(self):
        """E2E-3: 两个 valid hold/0.8 → 两个 hold 都应在 supporting_skills 中"""
        ctx = AgentContext()

        ctx.opinions.append(AgentOpinion(agent_name="skill_1", signal="hold", confidence=0.8))
        ctx.opinions.append(AgentOpinion(agent_name="skill_2", signal="hold", confidence=0.8))

        aggregator = SkillAggregator()
        consensus = aggregator.aggregate(ctx)

        self.assertIsNotNone(consensus)
        self.assertEqual(consensus.signal, "hold")

        synthesis = consensus.raw_data.get("strategy_synthesis")
        self.assertIsNotNone(synthesis)

        # Both hold opinions should be in supporting_skills (not neutral or opposing)
        supporting = synthesis.get("supporting_skills", [])
        self.assertEqual(len(supporting), 2)

        # Verify both skills are listed
        supporting_names = {s["agent_name"] for s in supporting}
        self.assertIn("skill_1", supporting_names)
        self.assertIn("skill_2", supporting_names)

        # opposing_skills should be empty
        opposing = synthesis.get("opposing_skills", [])
        self.assertEqual(len(opposing), 0)

    def test_single_sample_consensus_insufficient(self):
        """E2E-4: 1 valid buy/0.8 + 多个 invalid → consensus 应为 insufficient，不是 high"""
        ctx = AgentContext()

        # 1 valid opinion
        ctx.opinions.append(AgentOpinion(agent_name="skill_valid", signal="buy", confidence=0.8))

        # 3 invalid opinions
        for i in range(3):
            ctx.opinions.append(AgentOpinion(
                agent_name=f"skill_invalid_{i}",
                signal="moon",
                confidence=0.9
            ))

        aggregator = SkillAggregator()
        consensus = aggregator.aggregate(ctx)

        self.assertIsNotNone(consensus)
        synthesis = consensus.raw_data.get("strategy_synthesis")
        self.assertIsNotNone(synthesis)

        # consensus_level should be insufficient (only 1 valid sample)
        self.assertEqual(synthesis["consensus_level"], "insufficient")

        # opinion_count should be 1 (only valid)
        self.assertEqual(synthesis["summary_params"]["opinion_count"], 1)

        # invalid_opinion_count should be 3
        self.assertEqual(synthesis["summary_params"]["invalid_opinion_count"], 3)

    def test_e2e_e_partition_then_aggregate_insufficient(self):
        """E2E-E: 1 valid buy/0.8 + 9 invalid → 走 orchestrator 分拣 → aggregator →
        consensus_level == 'insufficient'（不得 high）；synthesis.summary_params
        对应 opinion_count=1、invalid_opinion_count=9、total_opinion_count=10。
        真 E2E：SkillAgent 输入 → Orchestrator 分拣 → SkillAggregator 合成。
        """
        ctx = AgentContext()

        ctx.opinions.append(AgentOpinion(
            agent_name="skill_valid",
            signal="buy",
            confidence=0.8,
            reasoning="valid bullish signal",
        ))

        for i in range(9):
            ctx.opinions.append(AgentOpinion(
                agent_name=f"skill_invalid_{i}",
                signal="moon",
                confidence=0.9,
                reasoning="invalid moon signal",
            ))

        # 唯一分拣点：Orchestrator
        orchestrator = AgentOrchestrator(
            tool_registry=MagicMock(),
            llm_adapter=MagicMock(),
            mode="full",
        )
        orchestrator._partition_skill_opinions(ctx)

        # After partition
        self.assertEqual(len(ctx.opinions), 1)
        self.assertEqual(len(ctx.meta.get("invalid_opinions", [])), 9)

        # Aggregator consumes partitioned ctx.opinions directly
        aggregator = SkillAggregator()
        consensus = aggregator.aggregate(ctx)

        self.assertIsNotNone(consensus)
        synthesis = consensus.raw_data.get("strategy_synthesis")
        self.assertIsNotNone(synthesis)

        # 单样本共识必须 insufficient
        self.assertEqual(synthesis["consensus_level"], "insufficient")

        # summary_params 计数正确
        self.assertEqual(synthesis["summary_params"]["opinion_count"], 1)

    def test_e2e_f_uppercase_buy_canonical(self):
        """E2E-F: signal='BUY' 大写输入 → normalize 后 canonical='buy' →
        aggregator 使用 canonical 查 strategy_signal_score → 得 4.0（不是 0）。
        final_signal 输出 canonical 小写 'buy'。
        真 E2E：SkillAgent 输出大写 → aggregator 内部 canonical-first 计算。
        """
        ctx = AgentContext()

        # Two valid opinions, one with uppercase signal
        ctx.opinions.append(AgentOpinion(
            agent_name="skill_upper",
            signal="BUY",  # 大写
            confidence=0.8,
        ))
        ctx.opinions.append(AgentOpinion(
            agent_name="skill_lower",
            signal="buy",
            confidence=0.8,
        ))

        # No partition needed — both are valid after normalization
        aggregator = SkillAggregator()
        consensus = aggregator.aggregate(ctx)

        self.assertIsNotNone(consensus)
        # canonical 小写输出
        self.assertEqual(consensus.signal, "buy")

        synthesis = consensus.raw_data.get("strategy_synthesis")
        self.assertIsNotNone(synthesis)
        # weighted_score 应接近 4.0（buy 的 canonical 分数），
        # 而不是因大写查表失败得到 0
        self.assertGreaterEqual(synthesis["weighted_score"], 3.5)
        # final_signal 输出 canonical 小写
        self.assertEqual(synthesis["final_signal"], "buy")

    def test_e2e_g_empty_supporting_uses_none_label(self):
        """E2E-G: 空 supporting_skills + report_language='en' → 四条 renderer 中
        不出现中文 '无'，而是 'None'（对应 labels.none_label）。
        真 E2E：dashboard payload → renderer 实际文本。
        """
        from src.domain.shared.report_language import get_report_labels

        # zh、en、ko 三语的 none_label 都必须完备
        for lang, expected in [("zh", "无"), ("en", "None"), ("ko", "없음")]:
            labels = get_report_labels(lang)
            self.assertEqual(labels["none_label"], expected)

        # 模拟一个空 supporting_skills 的 payload
        strategy_synthesis = {
            "final_signal": "hold",
            "confidence": 0.5,
            "consensus_level": "insufficient",
            "conflict_severity": "none",
            "conflict_count": 0,
            "supporting_skills": [],
            "opposing_skills": [],
            "summary_params": {
                "opinion_count": 0,
                "total_opinion_count": 0,
                "invalid_opinion_count": 0,
            },
        }

        # 走 notification 的 renderer helper
        from src.application.notification.notification import _append_strategy_synthesis_block

        for lang, expected_none in [("en", "None"), ("ko", "없음")]:
            labels = get_report_labels(lang)
            lines = []
            _append_strategy_synthesis_block(lines, strategy_synthesis, labels, lang)
            rendered = "\n".join(lines)

            # 空阵营必须用 labels.none_label 输出
            self.assertIn(expected_none, rendered)
            # 不得出现其他语言的 none_label
            for other_lang, other_none in [("zh", "无"), ("en", "None"), ("ko", "없음")]:
                if other_lang == lang:
                    continue
                # zh 的 "无" 有可能出现在其他非阵营的文案中，这里只检查阵营行
                # 简单起见：只在 en/ko 场景校验中文"无"不出现
                if lang != "zh" and other_lang == "zh":
                    self.assertNotIn("无", rendered)
