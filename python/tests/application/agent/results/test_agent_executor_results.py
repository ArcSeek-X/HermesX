"""Tests for agent executor results."""

from tests.application.agent._agent_executor_support import (
    AgentExecutor,
    AgentResult,
    LLMResponse,
    SAMPLE_DASHBOARD,
    _TestAgentExecutorFixture,
    _TestAgentResultFixture,
    _TestDashboardParsingFixture,
    _make_mock_adapter,
    _make_registry_with_echo,
    json,
    parse_dashboard_json,
    unittest,
)


class TestAgentExecutor(_TestAgentExecutorFixture, unittest.TestCase):
    def test_simple_text_response(self):
        """Agent returns text immediately (no tool calls) with JSON dashboard."""
        registry = _make_registry_with_echo()
        adapter = _make_mock_adapter()

        # LLM returns a text response with the dashboard JSON
        adapter.call_with_tools.return_value = LLMResponse(
            content=json.dumps(SAMPLE_DASHBOARD, ensure_ascii=False),
            tool_calls=[],
            usage={"total_tokens": 100},
            provider="openai",
        )

        executor = AgentExecutor(registry, adapter, max_steps=5)
        result = executor.run("Analyze 600519")

        self.assertTrue(result.success)
        self.assertIsNotNone(result.dashboard)
        self.assertEqual(result.dashboard["sentiment_score"], 75)
        self.assertEqual(result.total_steps, 1)
        self.assertEqual(result.provider, "openai")
        self.assertEqual(len(result.tool_calls_log), 0)

    def test_error_provider_preserves_failure_reason_in_agent_result(self):
        """LLM adapter error responses must surface as failed Agent results, not final answers."""
        registry = _make_registry_with_echo()
        adapter = _make_mock_adapter()
        adapter.call_with_tools.return_value = LLMResponse(
            content="No LLM configured. Please set LITELLM_MODEL, LLM_CHANNELS, or provider API keys before using Agent.",
            tool_calls=[],
            usage={"total_tokens": 1},
            provider="error",
            model="",
        )

        executor = AgentExecutor(registry, adapter, max_steps=2)
        result = executor.run("Analyze 600519")

        self.assertFalse(result.success)
        self.assertEqual(result.content, "")
        self.assertEqual(
            result.error,
            "No LLM configured. Please set LITELLM_MODEL, LLM_CHANNELS, or provider API keys before using Agent.",
        )
        self.assertEqual(result.total_steps, 1)
        self.assertEqual(result.total_tokens, 1)
        self.assertEqual(result.model, "")


class TestDashboardParsing(_TestDashboardParsingFixture, unittest.TestCase):
    def test_parse_markdown_json_block(self):
        content = f"Here is my analysis:\n```json\n{json.dumps(SAMPLE_DASHBOARD)}\n```\nDone."
        result = parse_dashboard_json(content)
        self.assertIsNotNone(result)
        self.assertEqual(result["sentiment_score"], 75)

    def test_parse_raw_json(self):
        content = json.dumps(SAMPLE_DASHBOARD)
        result = parse_dashboard_json(content)
        self.assertIsNotNone(result)

    def test_parse_json_in_text(self):
        content = f"Let me present: {json.dumps(SAMPLE_DASHBOARD)} — that's all."
        result = parse_dashboard_json(content)
        self.assertIsNotNone(result)

    def test_parse_empty_content(self):
        self.assertIsNone(parse_dashboard_json(""))
        self.assertIsNone(parse_dashboard_json(None))

    def test_parse_no_json(self):
        self.assertIsNone(parse_dashboard_json("This is just plain text with no JSON"))


class TestAgentResult(_TestAgentResultFixture, unittest.TestCase):
    def test_defaults(self):
        r = AgentResult()
        self.assertFalse(r.success)
        self.assertEqual(r.content, "")
        self.assertIsNone(r.dashboard)
        self.assertEqual(r.tool_calls_log, [])
        self.assertEqual(r.total_steps, 0)
        self.assertEqual(r.total_tokens, 0)
        self.assertIsNone(r.error)
