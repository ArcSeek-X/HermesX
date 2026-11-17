"""Tests for agent pipeline factory context."""

from tests.application.agent._agent_pipeline_support import (
    MagicMock,
    _TestAgentConstructionChainFixture,
    patch,
    unittest,
)


class TestAgentConstructionChain(_TestAgentConstructionChainFixture, unittest.TestCase):
    @patch("src.infrastructure.agent_runtime.llm_adapter.Router")
    def test_llm_adapter_context_window_error_skips_sleep(self, _mock_router):
        """Context-window errors should continue fallback immediately without backoff."""
        mock_cfg = MagicMock()
        mock_cfg.agent_litellm_model = "gpt-4o-mini"
        mock_cfg.litellm_model = None
        mock_cfg.litellm_fallback_models = ["anthropic/claude-3-5-sonnet-20241022"]
        mock_cfg.llm_model_list = []
        mock_cfg.llm_temperature = 0.7
        mock_cfg.gemini_api_keys = []
        mock_cfg.anthropic_api_keys = []
        mock_cfg.openai_api_keys = []
        mock_cfg.deepseek_api_keys = []
        mock_cfg.openai_base_url = None

        from src.infrastructure.agent_runtime.llm_adapter import LLMToolAdapter
        adapter = LLMToolAdapter(config=mock_cfg)

        class FakeContextWindowExceededError(Exception):
            pass

        def fake_call(_messages, _tools, model, **_kwargs):
            if model == "openai/gpt-4o-mini":
                raise FakeContextWindowExceededError("window exceeded")
            return MagicMock(content="ok")

        adapter._call_litellm_model = MagicMock(side_effect=fake_call)

        with patch(
            "src.infrastructure.agent_runtime.llm_adapter.litellm.ContextWindowExceededError",
            FakeContextWindowExceededError,
        ), patch("src.infrastructure.agent_runtime.llm_adapter.time.sleep") as mock_sleep:
            result = adapter.call_completion(messages=[{"role": "user", "content": "hi"}], tools=[])

        self.assertEqual(result.content, "ok")
        mock_sleep.assert_not_called()
