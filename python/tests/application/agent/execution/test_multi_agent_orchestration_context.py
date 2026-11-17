"""Tests for multi agent orchestration context."""

from tests.application.agent._multi_agent_support import (
    _TestOrchestratorExecutionFixture,
    patch,
    unittest,
)


class TestOrchestratorExecution(_TestOrchestratorExecutionFixture, unittest.TestCase):
    def test_chat_loads_prior_history_into_context(self):
        from src.application.agent.orchestrator import OrchestratorResult

        orch = self._make_orchestrator()
        history = [
            {"role": "user", "content": "之前的问题"},
            {"role": "assistant", "content": "之前的回答"},
        ]
        captured = {}

        def fake_execute(ctx, parse_dashboard=False, progress_callback=None):
            captured["history"] = ctx.meta.get("conversation_history")
            return OrchestratorResult(success=True, content="assistant reply")

        with patch.object(orch, "_execute_pipeline", side_effect=fake_execute):
            with patch("src.application.agent.orchestrator.build_visible_chat_history", return_value=history):
                with patch("src.application.agent.conversation.conversation_manager.get_or_create"):
                    with patch("src.application.agent.conversation.conversation_manager.add_message"):
                        orch.chat("hello", "session-1")

        self.assertEqual(captured["history"], history)

    def test_chat_resolves_scope_and_stores_it_for_multi_agent_chain(self):
        from src.application.agent.orchestrator import OrchestratorResult

        orch = self._make_orchestrator()
        captured = {}

        def fake_execute(ctx, parse_dashboard=False, progress_callback=None):
            captured["ctx"] = ctx
            return OrchestratorResult(success=True, content="assistant reply")

        with patch.object(orch, "_execute_pipeline", side_effect=fake_execute):
            with patch("src.application.agent.orchestrator.build_visible_chat_history", return_value=[]):
                with patch("src.application.agent.conversation.conversation_manager.get_or_create"):
                    with patch("src.application.agent.conversation.conversation_manager.add_message"):
                        orch.chat(
                            "换成 AAPL 看看",
                            "session-1",
                            context={
                                "stock_code": "600519",
                                "stock_name": "匿名标的",
                                "previous_analysis_summary": {"summary": "old"},
                            },
                        )

        ctx = captured["ctx"]
        self.assertEqual(ctx.stock_code, "AAPL")
        self.assertEqual(ctx.stock_name, "")
        self.assertNotIn("previous_analysis_summary", ctx.meta)
        self.assertEqual(ctx.meta["stock_scope"].mode, "switch")
        self.assertEqual(ctx.meta["stock_scope"].expected_stock_code, "AAPL")
