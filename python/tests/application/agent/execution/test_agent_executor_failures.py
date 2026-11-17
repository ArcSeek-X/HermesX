"""Tests for agent executor failures."""

from tests.application.agent._agent_executor_support import (
    AgentExecutor,
    LLMResponse,
    MagicMock,
    SAMPLE_DASHBOARD,
    SimpleNamespace,
    ToolCall,
    _TestAgentExecutorFixture,
    _make_mock_adapter,
    _make_registry_with_echo,
    json,
    patch,
    run_agent_loop,
    time,
    unittest,
)


class TestAgentExecutor(_TestAgentExecutorFixture, unittest.TestCase):
    def test_persist_provider_trace_logs_save_failure_without_failing_chat(self):
        registry = _make_registry_with_echo()
        adapter = _make_mock_adapter()
        executor = AgentExecutor(registry, adapter, max_steps=2)
        messages = [
            {"role": "user", "content": "question"},
            {
                "role": "assistant",
                "content": "checking",
                "_trace_provider": "deepseek",
                "_trace_model": "deepseek/deepseek-chat",
                "reasoning_content": "r1",
                "tool_calls": [{"id": "call_1", "name": "echo", "arguments": {"message": "x"}}],
            },
            {"role": "tool", "tool_call_id": "call_1", "content": "tool-result"},
        ]
        db = SimpleNamespace(save_agent_provider_turn=MagicMock(side_effect=RuntimeError("db down")))

        with patch(
            "src.application.agent.provider_trace._get_default_db_factory",
            return_value=lambda: db,
        ):
            with self.assertLogs("src.application.agent.executor", level="WARNING") as logs:
                executor._persist_provider_trace(
                    session_id="executor-trace-fail-open",
                    run_id="run-1",
                    messages=messages,
                    baseline_len=1,
                    user_message_id=10,
                    assistant_message_id=11,
                )

        self.assertIn("Provider trace persistence failed", "\n".join(logs.output))

    def test_model_trace_skips_error_provider(self):
        """Error provider placeholder should not appear in model trace."""
        registry = _make_registry_with_echo()
        adapter = _make_mock_adapter()
        adapter.call_with_tools.return_value = LLMResponse(
            content="llm failed",
            tool_calls=[],
            usage={"total_tokens": 3},
            provider="error",
            model="",
        )

        executor = AgentExecutor(registry, adapter, max_steps=2)
        result = executor.run("Analyze 600519")

        self.assertFalse(result.success)
        self.assertEqual(result.model, "")

    def test_timeout_budget_aborts_single_agent_loop(self):
        """Single-agent executor should stop once the configured timeout budget is exhausted."""
        registry = _make_registry_with_echo()
        adapter = _make_mock_adapter()

        def _slow_llm(*_args, **_kwargs):
            time.sleep(0.03)
            return LLMResponse(
                content=json.dumps(SAMPLE_DASHBOARD, ensure_ascii=False),
                tool_calls=[],
                usage={"total_tokens": 10},
                provider="openai",
            )

        adapter.call_with_tools.side_effect = _slow_llm

        executor = AgentExecutor(registry, adapter, max_steps=2, timeout_seconds=0.01)
        result = executor.run("Analyze 600519")

        self.assertFalse(result.success)
        self.assertIn("timed out", (result.error or "").lower())

    def test_llm_call_receives_remaining_timeout_budget(self):
        """LLM tool calls should receive the remaining wall-clock budget."""
        registry = _make_registry_with_echo()
        adapter = _make_mock_adapter()
        captured = {}

        def _capture_timeout(*_args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")
            return LLMResponse(
                content=json.dumps(SAMPLE_DASHBOARD, ensure_ascii=False),
                tool_calls=[],
                usage={"total_tokens": 10},
                provider="openai",
            )

        adapter.call_with_tools.side_effect = _capture_timeout

        executor = AgentExecutor(registry, adapter, max_steps=2, timeout_seconds=1.0)
        with patch("src.application.agent.runner.time.time", return_value=1000.0):
            result = executor.run("Analyze 600519")

        self.assertTrue(result.success)
        self.assertIsNotNone(captured.get("timeout"))
        self.assertGreater(captured["timeout"], 0.0)
        self.assertLessEqual(captured["timeout"], 1.0)

    def test_min_step_budget_skips_followup_llm_call(self):
        """When step>0 and remaining budget is too small, no extra LLM call should be made."""
        registry = _make_registry_with_echo()
        adapter = _make_mock_adapter()
        adapter.call_with_tools.return_value = LLMResponse(
            content="Need one tool first.",
            tool_calls=[ToolCall(id="echo_1", name="echo", arguments={"message": "hello"})],
            usage={"total_tokens": 10},
            provider="openai",
        )

        with patch(
            "src.application.agent.runner._remaining_timeout_seconds",
            side_effect=[9.0, 9.0, 7.5, 7.5],
        ):
            result = run_agent_loop(
                messages=[
                    {"role": "system", "content": "system"},
                    {"role": "user", "content": "Analyze"},
                ],
                tool_registry=registry,
                llm_adapter=adapter,
                max_steps=3,
                max_wall_clock_seconds=10.0,
            )

        self.assertFalse(result.success)
        self.assertIn("insufficient budget", (result.error or "").lower())
        self.assertEqual(adapter.call_with_tools.call_count, 1)
        self.assertEqual(len(result.tool_calls_log), 1)
        self.assertEqual(result.total_steps, 1)
