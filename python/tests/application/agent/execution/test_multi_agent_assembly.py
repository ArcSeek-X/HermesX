"""Tests for multi agent assembly."""

from tests.application.agent._multi_agent_support import (
    AgentContext,
    AgentOpinion,
    MagicMock,
    StageStatus,
    StockScope,
    _TestBaseAgentMessageAssemblyFixture,
    _TestDecisionAgentChatModeFixture,
    _TestTechnicalAgentSkillPolicyFixture,
    patch,
    unittest,
)


class TestDecisionAgentChatMode(_TestDecisionAgentChatModeFixture, unittest.TestCase):
    def test_post_process_stores_free_form_response(self):
        from src.application.agent.agents.decision_agent import DecisionAgent

        agent = DecisionAgent(tool_registry=MagicMock(), llm_adapter=MagicMock())
        ctx = AgentContext(query="帮我总结一下", stock_code="600519")
        ctx.meta["response_mode"] = "chat"
        ctx.add_opinion(AgentOpinion(agent_name="technical", signal="buy", confidence=0.8, reasoning="趋势偏强"))

        opinion = agent.post_process(ctx, "建议继续观察量价配合，分批参与。")

        self.assertIsNotNone(opinion)
        self.assertEqual(ctx.get_data("final_response_text"), "建议继续观察量价配合，分批参与。")
        self.assertIsNone(ctx.get_data("final_dashboard"))
        self.assertEqual(opinion.signal, "buy")

    def test_decision_agent_prompt_requires_phase_decision(self):
        from src.application.agent.agents.decision_agent import DecisionAgent

        agent = DecisionAgent(tool_registry=MagicMock(), llm_adapter=MagicMock())
        prompt = agent.system_prompt(AgentContext(query="分析 600519", stock_code="600519"))

        self.assertIn("phase_decision", prompt)
        self.assertIn("watch_conditions", prompt)
        self.assertIn("data_limitations", prompt)
        self.assertIn("confidence_level", prompt)


class TestTechnicalAgentSkillPolicy(_TestTechnicalAgentSkillPolicyFixture, unittest.TestCase):
    def test_prompt_omits_legacy_default_policy_when_explicit_skill_selected(self):
        from src.application.agent.agents.technical_agent import TechnicalAgent

        agent = TechnicalAgent(
            tool_registry=MagicMock(),
            llm_adapter=MagicMock(),
            skill_instructions="### 技能 1: 缠论",
            technical_skill_policy="",
        )
        prompt = agent.system_prompt(AgentContext(query="分析 600519", stock_code="600519"))

        self.assertNotIn("Bias from MA5 < 2%", prompt)
        self.assertIn("### 技能 1: 缠论", prompt)

    def test_prompt_includes_legacy_default_policy_for_implicit_default_run(self):
        from src.application.agent.agents.technical_agent import TechnicalAgent
        from src.application.agent.skills.defaults import TECHNICAL_SKILL_RULES_EN

        agent = TechnicalAgent(
            tool_registry=MagicMock(),
            llm_adapter=MagicMock(),
            skill_instructions="### 技能 1: 默认多头趋势",
            technical_skill_policy=TECHNICAL_SKILL_RULES_EN,
        )
        prompt = agent.system_prompt(AgentContext(query="分析 600519", stock_code="600519"))

        self.assertIn("Bias from MA5 < 2%", prompt)
        self.assertIn("### 技能 1: 默认多头趋势", prompt)


class TestBaseAgentMessageAssembly(_TestBaseAgentMessageAssemblyFixture, unittest.TestCase):
    def test_build_messages_includes_conversation_history(self):
        agent = self._make_agent()
        ctx = AgentContext(query="hello")
        ctx.meta["conversation_history"] = [
            {"role": "user", "content": "old question"},
            {"role": "assistant", "content": "old answer"},
        ]

        messages = agent._build_messages(ctx)

        self.assertEqual(messages[1], {"role": "user", "content": "old question"})
        self.assertEqual(messages[2], {"role": "assistant", "content": "old answer"})
        self.assertEqual(messages[-1], {"role": "user", "content": "current turn"})

    def test_build_messages_injects_market_phase_before_cached_data(self):
        agent = self._make_agent()
        ctx = AgentContext(query="hello", stock_code="600519")
        ctx.meta["market_phase_context"] = {
            "market": "cn",
            "phase": "intraday",
            "market_local_time": "2026-03-27T10:00:00+08:00",
            "effective_daily_bar_date": "2026-03-26",
            "is_partial_bar": True,
            "minutes_to_close": 300,
        }
        ctx.meta["analysis_context_pack_summary"] = "\n## 分析上下文包摘要\n- 数据块状态：行情 available\n"
        ctx.set_data("realtime_quote", {"price": 1880.0})

        messages = agent._build_messages(ctx)

        phase_indexes = [
            idx for idx, message in enumerate(messages)
            if "市场阶段上下文" in message.get("content", "")
        ]
        cached_indexes = [
            idx for idx, message in enumerate(messages)
            if "[Pre-fetched: realtime_quote]" in message.get("content", "")
        ]
        pack_indexes = [
            idx for idx, message in enumerate(messages)
            if "分析上下文包摘要" in message.get("content", "")
        ]
        self.assertEqual(len(phase_indexes), 1)
        self.assertEqual(len(pack_indexes), 1)
        self.assertEqual(len(cached_indexes), 1)
        self.assertLess(phase_indexes[0], pack_indexes[0])
        self.assertLess(pack_indexes[0], cached_indexes[0])
        phase_message = messages[phase_indexes[0]]
        self.assertEqual(phase_message["role"], "user")
        self.assertIn("盘中", phase_message["content"])
        self.assertIn("不得当作完整日线复盘", phase_message["content"])
        self.assertNotIn("market_phase_context", phase_message["content"])
        self.assertNotIn("is_partial_bar", phase_message["content"])
        pack_message = messages[pack_indexes[0]]
        self.assertEqual(pack_message["role"], "user")
        self.assertNotIn("analysis_context_pack_summary", pack_message["content"])

    def test_run_passes_stock_scope_from_context_meta_to_shared_runner(self):
        from src.application.agent.runner import RunLoopResult

        agent = self._make_agent()
        ctx = AgentContext(query="hello", stock_code="600519")
        ctx.meta["stock_scope"] = StockScope(
            expected_stock_code="600519",
            allowed_stock_codes={"600519"},
        )

        with patch(
            "src.application.agent.agents.base_agent.run_agent_loop",
            return_value=RunLoopResult(success=True, content="ok"),
        ) as run_loop:
            result = agent.run(ctx)

        self.assertEqual(result.status, StageStatus.COMPLETED)
        self.assertIs(run_loop.call_args.kwargs["stock_scope"], ctx.meta["stock_scope"])
