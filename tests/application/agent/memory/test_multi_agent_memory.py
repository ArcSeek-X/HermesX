"""Tests for multi agent memory."""

from tests.application.agent._multi_agent_support import (
    AgentContext,
    AgentOpinion,
    MagicMock,
    SimpleNamespace,
    _TestAgentMemoryFixture,
    _TestBaseAgentMemoryIntegrationFixture,
    json,
    patch,
    unittest,
)


class TestAgentMemory(_TestAgentMemoryFixture, unittest.TestCase):
    def test_disabled_returns_neutral(self):
        from src.application.agent.memory import AgentMemory
        mem = AgentMemory(enabled=False)
        cal = mem.get_calibration("technical")
        self.assertFalse(cal.calibrated)
        self.assertAlmostEqual(cal.calibration_factor, 1.0)

    def test_disabled_weights_all_equal(self):
        from src.application.agent.memory import AgentMemory
        mem = AgentMemory(enabled=False)
        weights = mem.compute_strategy_weights(["a", "b", "c"])
        self.assertEqual(weights, {"a": 1.0, "b": 1.0, "c": 1.0})

    def test_calibrate_confidence_passthrough_when_disabled(self):
        from src.application.agent.memory import AgentMemory
        mem = AgentMemory(enabled=False)
        self.assertAlmostEqual(mem.calibrate_confidence("tech", 0.75), 0.75)

    def test_get_stock_history_reads_orm_records(self):
        from src.application.agent.memory import AgentMemory

        record = SimpleNamespace(
            created_at=SimpleNamespace(date=lambda: SimpleNamespace(isoformat=lambda: "2026-03-01")),
            raw_result=json.dumps({"decision_type": "buy", "current_price": 1880.0}),
            sentiment_score=72,
            operation_advice="买入",
        )
        db = MagicMock()
        db.get_analysis_history.return_value = [record]

        with patch("src.application.agent.memory._get_history_repo", return_value=db):
            mem = AgentMemory(enabled=True)
            history = mem.get_stock_history("600519", limit=1)

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].signal, "buy")
        self.assertEqual(history[0].price_at_analysis, 1880.0)

    def test_configure_agent_memory_wires_database_manager_adapter(self):
        """W4.2: bootstrap.configure_agent_memory 以 DatabaseManager 门面装配 AgentMemory seam。"""
        from src.application.agent import memory as mem_mod
        from src.bootstrap.agent import configure_agent_memory

        sentinel = object()
        with patch(
            "src.bootstrap.agent.DatabaseManager.get_instance", return_value=sentinel
        ), patch.object(mem_mod, "set_history_repo") as mock_set:
            configure_agent_memory()
        mock_set.assert_called_once_with(sentinel)


class TestBaseAgentMemoryIntegration(_TestBaseAgentMemoryIntegrationFixture, unittest.TestCase):
    def test_memory_context_is_injected(self):
        entry = SimpleNamespace(
            date="2026-03-01",
            signal="buy",
            sentiment_score=72,
            price_at_analysis=1880.0,
            outcome_5d=0.03,
            outcome_20d=None,
            was_correct=True,
        )
        memory = MagicMock(enabled=True)
        memory.get_stock_history.return_value = [entry]
        agent = self._make_agent(memory)

        ctx = AgentContext(query="test", stock_code="600519")
        injected = agent._inject_cached_data(ctx)

        self.assertIn("Memory: recent analysis history", injected)
        self.assertIn("signal=buy", injected)

    def test_market_phase_meta_is_not_injected_as_prefetched_data(self):
        memory = MagicMock(enabled=False)
        agent = self._make_agent(memory)
        ctx = AgentContext(query="test", stock_code="600519")
        ctx.meta["market_phase_context"] = {"phase": "intraday"}
        ctx.meta["market_structure_context"] = {
            "market_theme_context": {"status": "ok"},
            "stock_market_position": {"status": "ok"},
        }
        ctx.meta["analysis_context_pack_summary"] = "\n## 分析上下文包摘要\n- 数据块状态：行情 available\n"
        ctx.set_data("realtime_quote", {"price": 1880.0})

        injected = agent._inject_cached_data(ctx)

        self.assertIn("[Pre-fetched: realtime_quote]", injected)
        self.assertNotIn("market_phase_context", injected)
        self.assertNotIn("[Pre-fetched: market_phase_context]", injected)
        self.assertNotIn("market_structure_context", injected)
        self.assertNotIn("[Pre-fetched: market_structure_context]", injected)
        self.assertNotIn("analysis_context_pack_summary", injected)
        self.assertNotIn("[Pre-fetched: analysis_context_pack_summary]", injected)
        self.assertNotIn("分析上下文包摘要", injected)

    def test_memory_calibration_updates_confidence(self):
        memory = MagicMock(enabled=True)
        memory.get_stock_history.return_value = []
        memory.get_calibration.return_value = SimpleNamespace(
            calibrated=True,
            calibration_factor=0.5,
            total_samples=40,
        )
        agent = self._make_agent(memory)
        ctx = AgentContext(query="test", stock_code="600519")

        loop_result = SimpleNamespace(
            success=True,
            content='{"signal":"buy","confidence":0.8,"reasoning":"ok"}',
            total_tokens=12,
            tool_calls_log=[],
            models_used=["test/model"],
        )
        with patch("src.application.agent.agents.base_agent.run_agent_loop", return_value=loop_result):
            result = agent.run(ctx)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.opinion)
        self.assertAlmostEqual(result.opinion.confidence, 0.4)
        self.assertEqual(result.meta["memory_calibration"]["factor"], 0.5)
        memory.calibrate_confidence.assert_not_called()

    def test_strategy_memory_calibration_uses_strategy_factor(self):
        from src.application.agent.agents.base_agent import BaseAgent

        class DummyStrategyAgent(BaseAgent):
            agent_name = "strategy_chan_theory"

            def system_prompt(self, ctx):
                return "system"

            def build_user_message(self, ctx):
                return "user"

            def post_process(self, ctx, raw_text):
                return AgentOpinion(agent_name=self.agent_name, signal="buy", confidence=0.8, reasoning=raw_text)

        memory = MagicMock(enabled=True)
        memory.get_stock_history.return_value = []
        memory.get_calibration.return_value = SimpleNamespace(
            calibrated=True,
            calibration_factor=0.5,
            total_samples=40,
        )

        with patch("src.application.agent.agents.base_agent.AgentMemory.from_config", return_value=memory):
            agent = DummyStrategyAgent(tool_registry=MagicMock(), llm_adapter=MagicMock())
        ctx = AgentContext(query="test", stock_code="600519")

        loop_result = SimpleNamespace(
            success=True,
            content='{"signal":"buy","confidence":0.8,"reasoning":"ok"}',
            total_tokens=12,
            tool_calls_log=[],
            models_used=["test/model"],
        )
        with patch("src.application.agent.agents.base_agent.run_agent_loop", return_value=loop_result):
            result = agent.run(ctx)

        self.assertTrue(result.success)
        self.assertAlmostEqual(result.opinion.confidence, 0.4)
        memory.get_calibration.assert_called_once_with(
            agent_name="strategy_chan_theory",
            stock_code="600519",
            skill_id="chan_theory",
        )
