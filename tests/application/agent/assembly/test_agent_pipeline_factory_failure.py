"""Tests for agent pipeline factory failure."""

from tests.application.agent._agent_pipeline_support import (
    MagicMock,
    SimpleNamespace,
    _TestAgentConstructionChainFixture,
    patch,
    unittest,
)


class TestAgentConstructionChain(_TestAgentConstructionChainFixture, unittest.TestCase):
    @patch("src.infrastructure.agent_runtime.llm_adapter.Router")
    def test_llm_adapter_recomputes_timeout_for_each_fallback_attempt(self, _mock_router):
        """Each fallback model attempt should receive only the remaining timeout budget."""
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

        timeouts = []

        def fake_call(_messages, _tools, model, **kwargs):
            timeouts.append((model, kwargs.get("timeout")))
            if model == "openai/gpt-4o-mini":
                raise RuntimeError("primary failed")
            return MagicMock(content="ok")

        adapter._call_litellm_model = MagicMock(side_effect=fake_call)

        with patch("src.infrastructure.agent_runtime.llm_adapter.time.time", side_effect=[0.0, 0.0, 7.0, 7.0]):
            result = adapter.call_completion(
                messages=[{"role": "user", "content": "hi"}],
                tools=[],
                timeout=10.0,
            )

        self.assertEqual(result.content, "ok")
        self.assertEqual(timeouts[0], ("openai/gpt-4o-mini", 10.0))
        self.assertEqual(timeouts[1], ("anthropic/claude-3-5-sonnet-20241022", 3.0))

    @patch("src.infrastructure.agent_runtime.llm_adapter.Router")
    def test_llm_adapter_rate_limit_backoff_is_bounded_by_remaining_timeout(self, _mock_router):
        """Rate-limit backoff should sleep, but never longer than the remaining timeout budget."""
        mock_cfg = MagicMock()
        mock_cfg.agent_litellm_model = "gpt-4o-mini"
        mock_cfg.litellm_model = None
        mock_cfg.litellm_fallback_models = ["openai/gpt-4.1-mini"]
        mock_cfg.llm_model_list = []
        mock_cfg.llm_temperature = 0.7
        mock_cfg.gemini_api_keys = []
        mock_cfg.anthropic_api_keys = []
        mock_cfg.openai_api_keys = []
        mock_cfg.deepseek_api_keys = []
        mock_cfg.openai_base_url = None

        from src.infrastructure.agent_runtime.llm_adapter import LLMToolAdapter
        adapter = LLMToolAdapter(config=mock_cfg)

        class FakeRateLimitError(Exception):
            pass

        timeouts = []
        sleep_calls = []
        clock = {"value": 0.0}

        def fake_time():
            return clock["value"]

        def fake_sleep(seconds):
            sleep_calls.append(seconds)
            clock["value"] += seconds

        def fake_call(_messages, _tools, model, **kwargs):
            timeouts.append((model, kwargs.get("timeout")))
            if model == "openai/gpt-4o-mini":
                clock["value"] += 8.0
                raise FakeRateLimitError("rate limited")
            return MagicMock(content="ok")

        adapter._call_litellm_model = MagicMock(side_effect=fake_call)

        with patch("src.infrastructure.agent_runtime.llm_adapter.litellm.RateLimitError", FakeRateLimitError), \
             patch("src.infrastructure.agent_runtime.llm_adapter.logger.warning"), \
             patch("src.infrastructure.agent_runtime.llm_adapter.time.time", side_effect=fake_time), \
             patch("src.infrastructure.agent_runtime.llm_adapter.time.sleep", side_effect=fake_sleep) as mock_sleep:
            result = adapter.call_completion(
                messages=[{"role": "user", "content": "hi"}],
                tools=[],
                timeout=10.0,
            )

        self.assertEqual(result.content, "ok")
        self.assertEqual(timeouts[0], ("openai/gpt-4o-mini", 10.0))
        self.assertEqual(timeouts[1][0], "openai/gpt-4.1-mini")
        expected_backoff = min(2.0, 8.0 * 0.1 + 0.5)
        expected_next_timeout = 10.0 - (8.0 + expected_backoff)
        self.assertAlmostEqual(timeouts[1][1], expected_next_timeout)
        mock_sleep.assert_called_once()
        self.assertAlmostEqual(mock_sleep.call_args.args[0], expected_backoff)
        self.assertAlmostEqual(sleep_calls[0], expected_backoff)
        self.assertAlmostEqual(clock["value"], 8.0 + expected_backoff)

    @patch("src.infrastructure.agent_runtime.llm_adapter.Router")
    def test_llm_adapter_reports_missing_configuration_without_generic_none_error(self, _mock_router):
        """Missing Agent model config should return a stable, actionable error message."""
        mock_cfg = SimpleNamespace(
            agent_litellm_model="",
            litellm_model="",
            litellm_fallback_models=[],
            llm_model_list=[],
            llm_temperature=0.7,
            gemini_api_keys=[],
            anthropic_api_keys=[],
            openai_api_keys=[],
            deepseek_api_keys=[],
            openai_base_url=None,
        )

        from src.infrastructure.agent_runtime.llm_adapter import LLMToolAdapter
        adapter = LLMToolAdapter(config=mock_cfg)

        result = adapter.call_completion(messages=[{"role": "user", "content": "hi"}], tools=[])

        self.assertEqual(result.provider, "error")
        self.assertEqual(
            result.content,
            "No LLM configured. Please set LITELLM_MODEL, LLM_CHANNELS, or provider API keys before using Agent.",
        )
