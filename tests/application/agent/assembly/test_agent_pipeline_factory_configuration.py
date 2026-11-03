"""Tests for agent pipeline factory configuration."""

from tests.application.agent._agent_pipeline_support import (
    MagicMock,
    _TestAgentConstructionChainFixture,
    patch,
    unittest,
)


class TestAgentConstructionChain(_TestAgentConstructionChainFixture, unittest.TestCase):
    def test_llm_adapter_accepts_config(self):
        """LLMToolAdapter should accept an optional config parameter."""
        mock_cfg = MagicMock()
        mock_cfg.gemini_api_key = ""
        mock_cfg.anthropic_api_key = ""
        mock_cfg.openai_api_key = ""
        mock_cfg.openai_base_url = ""
        mock_cfg.openai_model = ""

        from src.infrastructure.agent_runtime.llm_adapter import LLMToolAdapter
        adapter = LLMToolAdapter(config=mock_cfg)
        self.assertIsNotNone(adapter)

    @patch("src.infrastructure.agent_runtime.llm_adapter.Router")
    def test_llm_adapter_call_completion_uses_effective_agent_models_order(self, _mock_router):
        """call_completion should use Agent effective model chain in order."""
        mock_cfg = MagicMock()
        mock_cfg.agent_litellm_model = "gpt-4o-mini"
        mock_cfg.litellm_model = "gemini/gemini-2.5-flash"
        mock_cfg.litellm_fallback_models = ["openai/gpt-4o-mini", "anthropic/claude-3-5-sonnet-20241022"]
        mock_cfg.llm_model_list = []
        mock_cfg.llm_temperature = 0.7
        mock_cfg.gemini_api_keys = []
        mock_cfg.anthropic_api_keys = []
        mock_cfg.openai_api_keys = []
        mock_cfg.deepseek_api_keys = []
        mock_cfg.openai_base_url = None

        from src.infrastructure.agent_runtime.llm_adapter import LLMToolAdapter
        adapter = LLMToolAdapter(config=mock_cfg)

        calls = []

        def fake_call(_messages, _tools, model, **_kwargs):
            calls.append(model)
            if model == "openai/gpt-4o-mini":
                raise RuntimeError("primary failed")
            return MagicMock(content="ok")

        adapter._call_litellm_model = MagicMock(side_effect=fake_call)

        result = adapter.call_completion(messages=[{"role": "user", "content": "hi"}], tools=[])

        self.assertEqual(calls, ["openai/gpt-4o-mini", "anthropic/claude-3-5-sonnet-20241022"])
        self.assertEqual(result.content, "ok")
