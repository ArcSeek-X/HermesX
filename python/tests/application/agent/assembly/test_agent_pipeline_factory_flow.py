"""Tests for agent pipeline factory flow."""

from tests.application.agent._agent_pipeline_support import (
    MagicMock,
    SimpleNamespace,
    _TestAgentConstructionChainFixture,
    patch,
    unittest,
)


class TestAgentConstructionChain(_TestAgentConstructionChainFixture, unittest.TestCase):
    def test_llm_adapter_no_args(self):
        """LLMToolAdapter should also work with no arguments (uses get_config)."""
        with patch('src.infrastructure.agent_runtime.llm_adapter.get_config') as mock_get_config:
            mock_cfg = MagicMock()
            mock_cfg.gemini_api_key = ""
            mock_cfg.anthropic_api_key = ""
            mock_cfg.openai_api_key = ""
            mock_cfg.openai_base_url = ""
            mock_cfg.openai_model = ""
            mock_get_config.return_value = mock_cfg

            from src.infrastructure.agent_runtime.llm_adapter import LLMToolAdapter
            adapter = LLMToolAdapter()
            self.assertIsNotNone(adapter)

    def test_full_construction_chain(self):
        """Test ToolRegistry + SkillManager + LLMToolAdapter + AgentExecutor wiring."""
        from src.application.agent.tools.registry import ToolRegistry, ToolDefinition, ToolParameter
        from src.application.agent.skills.base import SkillManager, Skill
        from src.infrastructure.agent_runtime.llm_adapter import LLMToolAdapter
        from src.application.agent.executor import AgentExecutor

        # Build registry with a dummy tool
        registry = ToolRegistry()

        def dummy_handler(x: str) -> str:
            return f"echo {x}"

        dummy_tool = ToolDefinition(
            name="dummy_echo",
            description="A test tool for echoing input.",
            category="test",
            parameters=[ToolParameter(name="x", type="string", description="input string", required=True)],
            handler=dummy_handler,
        )
        registry.register(dummy_tool)

        # Build skill manager with a fresh skill instance (avoid module singleton state)
        skill_manager = SkillManager()
        test_skill = Skill(
            name="test_skill",
            display_name="测试策略",
            description="A test skill",
            instructions="Test instructions for analysis.",
            category="trend",
            core_rules=[1, 2],
        )
        skill_manager.register(test_skill)
        skill_manager.activate(["test_skill"])
        instructions = skill_manager.get_skill_instructions()
        self.assertIn("测试策略", instructions)

        # Build LLM adapter with mocked config (no real API keys)
        mock_cfg = MagicMock()
        mock_cfg.gemini_api_key = ""
        mock_cfg.anthropic_api_key = ""
        mock_cfg.openai_api_key = ""
        mock_cfg.openai_base_url = ""
        mock_cfg.openai_model = ""
        adapter = LLMToolAdapter(config=mock_cfg)

        # Build executor
        executor = AgentExecutor(
            tool_registry=registry,
            llm_adapter=adapter,
            skill_instructions=instructions,
            max_steps=3,
        )
        self.assertEqual(executor.max_steps, 3)
        self.assertIsNotNone(executor.tool_registry)
        self.assertIsNotNone(executor.llm_adapter)

    @patch("src.infrastructure.agent_runtime.llm_adapter.Router")
    def test_llm_adapter_normalizes_kimi_k26_temperature(self, _mock_router):
        """Agent direct LiteLLM calls should not send unsupported temperatures to Kimi K2.6."""
        mock_cfg = SimpleNamespace(
            agent_litellm_model="",
            litellm_model="openai/kimi-k2.6",
            litellm_fallback_models=[],
            llm_model_list=[],
            llm_temperature=0.2,
            gemini_api_keys=[],
            anthropic_api_keys=[],
            openai_api_keys=[],
            deepseek_api_keys=[],
            openai_base_url=None,
        )

        from src.infrastructure.agent_runtime.llm_adapter import LLMToolAdapter
        adapter = LLMToolAdapter(config=mock_cfg)
        adapter._router = None
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="agent ok",
                        tool_calls=[],
                    )
                )
            ],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
        )

        with patch("src.infrastructure.agent_runtime.llm_adapter.litellm.completion", return_value=response) as mock_completion:
            result = adapter._call_litellm_model(
                [{"role": "user", "content": "hi"}],
                [],
                "openai/kimi-k2.6",
                temperature=0.2,
            )

        self.assertEqual(result.content, "agent ok")
        self.assertEqual(mock_completion.call_args.kwargs["temperature"], 1.0)

    @patch("src.infrastructure.agent_runtime.llm_adapter.Router")
    def test_llm_adapter_normalizes_kimi_k26_temperature_for_yaml_alias(self, _mock_router):
        """Agent direct LiteLLM calls should normalize through routed YAML aliases."""
        mock_cfg = SimpleNamespace(
            agent_litellm_model="",
            litellm_model="kimi_router",
            litellm_fallback_models=[],
            llm_model_list=[
                {
                    "model_name": "kimi_router",
                    "litellm_params": {"model": "openai/kimi-k2.6"},
                }
            ],
            llm_temperature=0.2,
            gemini_api_keys=[],
            anthropic_api_keys=[],
            openai_api_keys=[],
            deepseek_api_keys=[],
            openai_base_url=None,
        )

        from src.infrastructure.agent_runtime.llm_adapter import LLMToolAdapter
        adapter = LLMToolAdapter(config=mock_cfg)
        adapter._router = None
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="agent ok",
                        tool_calls=[],
                    )
                )
            ],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
        )

        with patch("src.infrastructure.agent_runtime.llm_adapter.litellm.completion", return_value=response) as mock_completion:
            result = adapter._call_litellm_model(
                [{"role": "user", "content": "hi"}],
                [],
                "kimi_router",
                temperature=0.2,
            )

        self.assertEqual(result.content, "agent ok")
        self.assertEqual(mock_completion.call_args.kwargs["temperature"], 1.0)

    @patch("src.infrastructure.agent_runtime.llm_adapter.Router")
    def test_llm_adapter_normalizes_kimi_k26_temperature_for_non_thinking_yaml_alias(self, _mock_router):
        """Agent direct LiteLLM calls should honor non-thinking Kimi YAML overrides."""
        mock_cfg = SimpleNamespace(
            agent_litellm_model="",
            litellm_model="kimi_router",
            litellm_fallback_models=[],
            llm_model_list=[
                {
                    "model_name": "kimi_router",
                    "litellm_params": {
                        "model": "openai/kimi-k2.6",
                        "extra_body": {"thinking": {"type": "disabled"}},
                    },
                }
            ],
            llm_temperature=0.2,
            gemini_api_keys=[],
            anthropic_api_keys=[],
            openai_api_keys=[],
            deepseek_api_keys=[],
            openai_base_url=None,
        )

        from src.infrastructure.agent_runtime.llm_adapter import LLMToolAdapter
        adapter = LLMToolAdapter(config=mock_cfg)
        adapter._router = None
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="agent ok",
                        tool_calls=[],
                    )
                )
            ],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
        )

        with patch("src.infrastructure.agent_runtime.llm_adapter.litellm.completion", return_value=response) as mock_completion:
            result = adapter._call_litellm_model(
                [{"role": "user", "content": "hi"}],
                [],
                "kimi_router",
                temperature=0.2,
            )

        self.assertEqual(result.content, "agent ok")
        self.assertEqual(mock_completion.call_args.kwargs["temperature"], 0.6)

    @patch("src.infrastructure.agent_runtime.llm_adapter.Router")
    def test_llm_adapter_omits_temperature_for_gpt5_family(self, _mock_router):
        """Agent direct LiteLLM calls should omit temperature for strict default-temperature models."""
        mock_cfg = SimpleNamespace(
            agent_litellm_model="",
            litellm_model="openai/gpt5.5-ferr",
            litellm_fallback_models=[],
            llm_model_list=[],
            llm_temperature=0.2,
            gemini_api_keys=[],
            anthropic_api_keys=[],
            openai_api_keys=[],
            deepseek_api_keys=[],
            openai_base_url=None,
        )

        from src.infrastructure.agent_runtime.llm_adapter import LLMToolAdapter
        adapter = LLMToolAdapter(config=mock_cfg)
        adapter._router = None
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="agent ok",
                        tool_calls=[],
                    )
                )
            ],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
        )

        with patch("src.infrastructure.agent_runtime.llm_adapter.litellm.completion", return_value=response) as mock_completion:
            result = adapter._call_litellm_model(
                [{"role": "user", "content": "hi"}],
                [],
                "openai/gpt5.5-ferr",
                temperature=0.2,
            )

        self.assertEqual(result.content, "agent ok")
        self.assertNotIn("temperature", mock_completion.call_args.kwargs)

    @patch("src.infrastructure.agent_runtime.llm_adapter.Router")
    def test_llm_adapter_recovers_from_unsupported_temperature(self, _mock_router):
        """Agent direct LiteLLM calls should retry once with a request-scoped parameter repair."""
        from src.infrastructure.generation.generation_params import clear_litellm_generation_param_recovery_cache

        clear_litellm_generation_param_recovery_cache()
        mock_cfg = SimpleNamespace(
            agent_litellm_model="",
            litellm_model="openai/custom-temp-locked-agent",
            litellm_fallback_models=[],
            llm_model_list=[],
            llm_temperature=0.2,
            gemini_api_keys=[],
            anthropic_api_keys=[],
            openai_api_keys=[],
            deepseek_api_keys=[],
            openai_base_url=None,
        )

        from src.infrastructure.agent_runtime.llm_adapter import LLMToolAdapter
        adapter = LLMToolAdapter(config=mock_cfg)
        adapter._router = None
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="agent ok",
                        tool_calls=[],
                    )
                )
            ],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
        )

        with patch("src.infrastructure.agent_runtime.llm_adapter.litellm.completion") as mock_completion:
            mock_completion.side_effect = [
                RuntimeError("Unsupported parameter: temperature is not supported"),
                response,
            ]
            result = adapter._call_litellm_model(
                [{"role": "user", "content": "hi"}],
                [],
                "openai/custom-temp-locked-agent",
                temperature=0.2,
            )

        self.assertEqual(result.content, "agent ok")
        self.assertEqual(mock_completion.call_args_list[0].kwargs["temperature"], 0.2)
        self.assertNotIn("temperature", mock_completion.call_args_list[1].kwargs)

    @patch("src.infrastructure.agent_runtime.llm_adapter.Router")
    def test_llm_adapter_legacy_router_recovery_cache_is_scoped_to_endpoint(self, mock_router):
        """Legacy multi-key Router recoveries should not leak across base URLs."""
        from src.infrastructure.generation.generation_params import clear_litellm_generation_param_recovery_cache

        clear_litellm_generation_param_recovery_cache()
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="agent ok",
                        tool_calls=[],
                    )
                )
            ],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
        )
        strict_router = MagicMock()
        flex_router = MagicMock()
        strict_router.completion.side_effect = [
            RuntimeError("Unsupported parameter: temperature is not supported"),
            response,
        ]
        flex_router.completion.return_value = response
        mock_router.side_effect = [strict_router, flex_router]

        strict_cfg = SimpleNamespace(
            agent_litellm_model="",
            litellm_model="openai/shared-model",
            litellm_fallback_models=[],
            llm_model_list=[],
            llm_temperature=0.2,
            gemini_api_keys=[],
            anthropic_api_keys=[],
            openai_api_keys=["sk-strict-key-1", "sk-strict-key-2"],
            deepseek_api_keys=[],
            openai_base_url="https://strict.example/v1",
        )
        flex_cfg = SimpleNamespace(
            agent_litellm_model="",
            litellm_model="openai/shared-model",
            litellm_fallback_models=[],
            llm_model_list=[],
            llm_temperature=0.2,
            gemini_api_keys=[],
            anthropic_api_keys=[],
            openai_api_keys=["sk-flex-key-1", "sk-flex-key-2"],
            deepseek_api_keys=[],
            openai_base_url="https://flex.example/v1",
        )

        from src.infrastructure.agent_runtime.llm_adapter import LLMToolAdapter

        strict_adapter = LLMToolAdapter(config=strict_cfg)
        strict_result = strict_adapter._call_litellm_model(
            [{"role": "user", "content": "hi"}],
            [],
            "openai/shared-model",
            temperature=0.2,
        )
        flex_adapter = LLMToolAdapter(config=flex_cfg)
        flex_result = flex_adapter._call_litellm_model(
            [{"role": "user", "content": "hi"}],
            [],
            "openai/shared-model",
            temperature=0.2,
        )

        self.assertEqual(strict_result.content, "agent ok")
        self.assertEqual(flex_result.content, "agent ok")
        self.assertEqual(strict_router.completion.call_args_list[0].kwargs["temperature"], 0.2)
        self.assertNotIn("temperature", strict_router.completion.call_args_list[1].kwargs)
        self.assertEqual(flex_router.completion.call_args.kwargs["temperature"], 0.2)

    @patch("src.infrastructure.agent_runtime.llm_adapter.Router")
    def test_llm_adapter_fallback_does_not_leak_kimi_fixed_temperature(self, _mock_router):
        """Non-Kimi fallbacks should keep the requested temperature after a Kimi failure."""
        mock_cfg = SimpleNamespace(
            agent_litellm_model="",
            litellm_model="openai/kimi-k2.6",
            litellm_fallback_models=["openai/gpt-4o-mini"],
            llm_model_list=[],
            llm_temperature=0.2,
            gemini_api_keys=[],
            anthropic_api_keys=[],
            openai_api_keys=[],
            deepseek_api_keys=[],
            openai_base_url=None,
        )

        from src.infrastructure.agent_runtime.llm_adapter import LLMToolAdapter
        adapter = LLMToolAdapter(config=mock_cfg)
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="fallback ok",
                        tool_calls=[],
                    )
                )
            ],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
        )
        temperatures = []

        def fake_completion(**kwargs):
            temperatures.append((kwargs["model"], kwargs["temperature"]))
            if kwargs["model"] == "openai/kimi-k2.6":
                raise RuntimeError("primary failed")
            return response

        with patch("src.infrastructure.agent_runtime.llm_adapter.litellm.completion", side_effect=fake_completion):
            result = adapter.call_completion(
                messages=[{"role": "user", "content": "hi"}],
                tools=[],
                temperature=0.2,
            )

        self.assertEqual(result.content, "fallback ok")
        self.assertEqual(
            temperatures,
            [("openai/kimi-k2.6", 1.0), ("openai/gpt-4o-mini", 0.2)],
        )

    @patch("src.infrastructure.agent_runtime.llm_adapter.Router")
    def test_llm_adapter_reports_rate_limit_suffix_when_any_fallback_hit_limit(self, _mock_router):
        """Final error should note earlier rate limiting even if the last error differs."""
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

        class FakeRateLimitError(Exception):
            pass

        class FakeContextWindowExceededError(Exception):
            pass

        def fake_call(_messages, _tools, model, **_kwargs):
            if model == "openai/gpt-4o-mini":
                raise FakeRateLimitError("rate limited")
            raise FakeContextWindowExceededError("window exceeded")

        adapter._call_litellm_model = MagicMock(side_effect=fake_call)

        with patch("src.infrastructure.agent_runtime.llm_adapter.litellm.RateLimitError", FakeRateLimitError), \
             patch(
                 "src.infrastructure.agent_runtime.llm_adapter.litellm.ContextWindowExceededError",
                 FakeContextWindowExceededError,
             ), \
             patch("src.infrastructure.agent_runtime.llm_adapter.time.sleep") as mock_sleep:
            result = adapter.call_completion(messages=[{"role": "user", "content": "hi"}], tools=[])

        self.assertEqual(result.provider, "error")
        self.assertIn("All LLM models failed (rate-limit encountered during fallback).", result.content)
        self.assertIn("window exceeded", result.content)
        mock_sleep.assert_not_called()
