"""Tests for multi agent orchestration results."""

from tests.application.agent._multi_agent_support import (
    _TestOrchestratorExecutionFixture,
    patch,
    unittest,
)


class TestOrchestratorExecution(_TestOrchestratorExecutionFixture, unittest.TestCase):
    def test_run_wraps_orchestrator_result(self):
        from src.application.agent.orchestrator import OrchestratorResult

        orch = self._make_orchestrator()
        fake_result = OrchestratorResult(success=True, content="done", total_steps=2, total_tokens=11, model="x")
        with patch.object(orch, "_execute_pipeline", return_value=fake_result):
            result = orch.run("Analyze 600519")

        self.assertTrue(result.success)
        self.assertEqual(result.content, "done")
        self.assertEqual(result.total_steps, 2)
