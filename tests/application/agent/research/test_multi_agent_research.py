"""Tests for multi agent research."""

from tests.application.agent._multi_agent_support import (
    AsyncMock,
    MagicMock,
    SimpleNamespace,
    _TestResearchAgentFilteredRegistryFixture,
    _TestResearchCommandTimeoutFixture,
    patch,
    unittest,
)


class TestResearchCommandTimeout(_TestResearchCommandTimeoutFixture, unittest.TestCase):
    def test_research_timeout_returns_timeout_response(self):
        """Timed-out research results should surface the timeout response text."""
        from bot.commands.research import ResearchCommand
        from src.domain.notification.bot_message import BotMessage

        cmd = ResearchCommand()

        msg = MagicMock(spec=BotMessage)
        msg.platform = "test"
        msg.user_id = "u1"

        config = SimpleNamespace(
            agent_deep_research_budget=30000,
            agent_deep_research_timeout=0.01,  # 10ms — will trigger timeout
            litellm_model="test-model",
            agent_mode=True,
        )

        with patch("bot.commands.research.get_config", return_value=config), \
             patch("src.application.agent.factory.get_tool_registry", return_value=MagicMock()), \
             patch("src.infrastructure.agent_runtime.llm_adapter.LLMToolAdapter", return_value=MagicMock()), \
             patch("src.application.agent.research.ResearchAgent.research", return_value=SimpleNamespace(
                 success=False,
                 report="",
                 sub_questions=["q"],
                 findings_count=1,
                 total_tokens=100,
                 duration_s=0.01,
                 error="Deep research timed out after 0.01s",
                 timed_out=True,
             )):
            response = cmd.execute(msg, ["600519"])

        self.assertIn("超时", response.text)

    def test_research_recognizes_five_letter_us_ticker(self):
        from bot.commands.research import ResearchCommand
        from src.domain.notification.bot_message import BotMessage

        cmd = ResearchCommand()
        msg = MagicMock(spec=BotMessage)
        msg.platform = "test"
        msg.user_id = "u1"

        result = SimpleNamespace(
            success=True,
            report="ok",
            sub_questions=["q"],
            findings_count=1,
            total_tokens=100,
            duration_s=1.0,
            error=None,
            timed_out=False,
        )
        captured = {}

        def _capture_research(query, context=None, timeout_seconds=None):
            captured["query"] = query
            captured["context"] = context
            captured["timeout_seconds"] = timeout_seconds
            return result

        config = SimpleNamespace(
            agent_deep_research_budget=30000,
            agent_deep_research_timeout=1,
            litellm_model="test-model",
            agent_mode=True,
        )

        with patch("bot.commands.research.get_config", return_value=config), \
             patch("src.application.agent.factory.get_tool_registry", return_value=MagicMock()), \
             patch("src.infrastructure.agent_runtime.llm_adapter.LLMToolAdapter", return_value=MagicMock()), \
             patch("src.application.agent.research.ResearchAgent.research", side_effect=_capture_research):
            response = cmd.execute(msg, ["googl", "风险"])

        self.assertIn("Deep Research Report", response.text)
        self.assertEqual(captured["context"], {"stock_code": "GOOGL", "stock_name": ""})
        self.assertEqual(captured["timeout_seconds"], 1)
        self.assertTrue(captured["query"].startswith("[Stock: GOOGL]"))


class TestResearchAgentFilteredRegistry(_TestResearchAgentFilteredRegistryFixture, unittest.TestCase):
    def test_filtered_registry_delegates_to_base(self):
        from src.application.agent.research import ResearchAgent
        from src.application.agent.tools.registry import ToolRegistry

        registry = ToolRegistry()
        fake_tool = MagicMock()
        fake_tool.name = "search_stock_news"
        registry.register(fake_tool)

        llm_adapter = MagicMock()
        agent = ResearchAgent(tool_registry=registry, llm_adapter=llm_adapter)

        filtered = agent._filtered_registry()
        self.assertIsInstance(filtered, ToolRegistry)
        self.assertIsNotNone(filtered.get("search_stock_news"))

    def test_decompose_query_uses_shared_adapter(self):
        from src.application.agent.research import ResearchAgent

        llm_adapter = MagicMock()
        llm_adapter.call_text.return_value = SimpleNamespace(
            provider="gemini",
            content='{"questions":["Q1","Q2"]}',
            usage={"total_tokens": 42},
        )
        agent = ResearchAgent(tool_registry=MagicMock(), llm_adapter=llm_adapter)

        result = agent._decompose_query("分析 600519", {"stock_code": "600519"})

        self.assertEqual(result["questions"], ["Q1", "Q2"])
        llm_adapter.call_text.assert_called_once()

    def test_synthesise_report_uses_shared_adapter(self):
        from src.application.agent.research import ResearchAgent

        llm_adapter = MagicMock()
        llm_adapter.call_text.return_value = SimpleNamespace(
            provider="gemini",
            content="Final research report",
            usage={"total_tokens": 88},
        )
        agent = ResearchAgent(tool_registry=MagicMock(), llm_adapter=llm_adapter)

        result = agent._synthesise_report(
            "分析 600519",
            [{"question": "Q1", "content": "A1"}],
            {"stock_code": "600519"},
        )

        self.assertEqual(result["content"], "Final research report")
        llm_adapter.call_text.assert_called_once()

    def test_research_marks_synthesis_fallback_as_failure(self):
        from src.application.agent.research import ResearchAgent

        agent = ResearchAgent(tool_registry=MagicMock(), llm_adapter=MagicMock())
        with patch.object(agent, "_decompose_query", return_value={"questions": ["Q1"], "tokens": 3}), \
             patch.object(agent, "_research_sub_question", return_value={"summary": "done", "tokens": 7}), \
             patch.object(agent, "_synthesise_report", return_value={"content": "fallback", "tokens": 5, "error": "boom"}):
            result = agent.research("分析 600519")

        self.assertFalse(result.success)
        self.assertEqual(result.error, "boom")

    def test_research_sub_question_marks_budget_guard_as_timeout(self):
        from src.application.agent.research import ResearchAgent

        agent = ResearchAgent(tool_registry=MagicMock(), llm_adapter=MagicMock())
        with patch("src.application.agent.research.run_agent_loop", return_value=SimpleNamespace(
            success=False,
            content="",
            total_tokens=7,
            error="Agent step skipped due to insufficient budget: 3.0s remaining, minimum 8.0s required",
        )):
            result = agent._research_sub_question(
                "Q1",
                {},
                0,
                timeout_seconds=10,
            )

        self.assertFalse(result["success"])
        self.assertTrue(result["timed_out"])
        self.assertIn("insufficient budget", (result["error"] or "").lower())
        self.assertEqual(result["tokens"], 7)

    def test_research_returns_timeout_result_when_overall_deadline_is_exceeded(self):
        import time as _time
        from src.application.agent.research import ResearchAgent

        agent = ResearchAgent(tool_registry=MagicMock(), llm_adapter=MagicMock())

        def _slow_sub_question(*args, **kwargs):
            _time.sleep(0.02)
            return {"question": "Q1", "content": "done", "tokens": 7, "success": True}

        with patch.object(agent, "_decompose_query", return_value={"questions": ["Q1"], "tokens": 3}), \
             patch.object(agent, "_research_sub_question", side_effect=_slow_sub_question):
            result = agent.research("分析 600519", timeout_seconds=0.01)

        self.assertFalse(result.success)
        self.assertTrue(result.timed_out)
        self.assertIn("timed out", result.error)


class TestAgentResearchEndpoint(unittest.IsolatedAsyncioTestCase):
    async def test_agent_research_returns_timeout_response(self):
        from api.v1.endpoints.agent import ResearchRequest, agent_research

        config = SimpleNamespace(
            litellm_model="gemini/test-model",
            agent_deep_research_budget=30000,
            agent_deep_research_timeout=1,
            is_agent_available=lambda: True,
        )

        research_result = AsyncMock(return_value=SimpleNamespace(
            success=False,
            report="",
            sub_questions=[],
            findings_count=0,
            total_tokens=0,
            duration_s=1.0,
            error="Deep research timed out after 1s",
            timed_out=True,
        ))

        with (
            patch("api.v1.endpoints.agent.get_config", return_value=config),
            patch("api.v1.endpoints.agent._run_research_in_background", new=research_result),
            patch("src.application.agent.factory.get_tool_registry", return_value=MagicMock()),
            patch("src.infrastructure.agent_runtime.llm_adapter.LLMToolAdapter", return_value=MagicMock()),
        ):
            response = await agent_research(ResearchRequest(question="600519 风险"))

        self.assertFalse(response.success)
        self.assertIn("timed out", response.error)
