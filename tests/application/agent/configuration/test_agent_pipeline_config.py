"""Tests for agent pipeline config."""

from tests.application.agent._agent_pipeline_support import (
    Any,
    Dict,
    MagicMock,
    SimpleNamespace,
    _TestAgentConfigFixture,
    importlib,
    os,
    patch,
    sys,
    types,
    unittest,
)


class TestAgentConfig(_TestAgentConfigFixture, unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    @patch('src.config.settings.load_dotenv')
    def test_default_agent_config(self, _mock_dotenv):
        """Agent mode should be disabled by default."""
        from src.config import AGENT_MAX_STEPS_DEFAULT, Config
        Config._instance = None
        config = Config._load_from_env()
        self.assertEqual(config.agent_litellm_model, "")
        self.assertFalse(config.agent_mode)
        self.assertEqual(config.agent_max_steps, AGENT_MAX_STEPS_DEFAULT)
        self.assertEqual(config.agent_skills, [])
        self.assertEqual(config.agent_skill_concurrency, 3)

    @patch.dict(os.environ, {
        'AGENT_MODE': 'true',
        'AGENT_MAX_STEPS': '15',
        'AGENT_SKILLS': 'dragon_head,shrink_pullback,volume_breakout',
        'AGENT_SKILL_CONCURRENCY': '4',
    }, clear=True)
    def test_agent_config_from_env(self):
        """Agent config should be loaded from environment."""
        from src.config import Config
        Config._instance = None
        config = Config._load_from_env()
        self.assertTrue(config.agent_mode)
        self.assertEqual(config.agent_max_steps, 15)
        self.assertEqual(config.agent_skills, ['dragon_head', 'shrink_pullback', 'volume_breakout'])
        self.assertEqual(config.agent_skill_concurrency, 4)

    @patch.dict(os.environ, {'AGENT_SKILL_CONCURRENCY': '9'}, clear=True)
    def test_agent_skill_concurrency_is_clamped(self):
        """Agent skill concurrency should stay within the supported 1-4 range."""
        from src.config import Config
        Config._instance = None
        config = Config._load_from_env()
        self.assertEqual(config.agent_skill_concurrency, 4)

    @patch.dict(os.environ, {'AGENT_MODE': 'false'}, clear=True)
    def test_agent_mode_disabled(self):
        """Explicitly disabled agent mode."""
        from src.config import Config
        Config._instance = None
        config = Config._load_from_env()
        self.assertFalse(config.agent_mode)

    @patch.dict(os.environ, {'AGENT_SKILLS': ''}, clear=True)
    def test_empty_skills_list(self):
        """Empty AGENT_SKILLS should produce empty list."""
        from src.config import Config
        Config._instance = None
        config = Config._load_from_env()
        self.assertEqual(config.agent_skills, [])

    @patch.dict(os.environ, {'AGENT_SKILLS': '  dragon_head , shrink_pullback  '}, clear=True)
    def test_skills_whitespace_handling(self):
        """Skills should have whitespace trimmed."""
        from src.config import Config
        Config._instance = None
        config = Config._load_from_env()
        self.assertEqual(config.agent_skills, ['dragon_head', 'shrink_pullback'])

    @patch.dict(os.environ, {'AGENT_LITELLM_MODEL': 'gpt-4o-mini'}, clear=True)
    def test_agent_is_available_when_agent_primary_model_is_configured(self):
        """Agent availability auto-detection should use effective Agent primary model."""
        from src.config import Config
        Config._instance = None
        config = Config._load_from_env()
        self.assertEqual(config.agent_litellm_model, 'openai/gpt-4o-mini')
        self.assertTrue(config.is_agent_available())

    def test_agent_models_to_try_inherit_legacy_provider_models(self):
        """Legacy provider key/model envs should still produce a non-empty Agent model try list."""
        from src.config import Config, get_effective_agent_models_to_try

        test_cases = [
            (
                {
                    "GEMINI_API_KEY": "gemini-test-key",
                    "GEMINI_MODEL": "gemini-2.5-flash",
                    "AGENT_LITELLM_MODEL": "",
                },
                ["gemini/gemini-2.5-flash", "gemini/gemini-3-flash-preview"],
            ),
            (
                {
                    "OPENAI_API_KEY": "sk-test-value",
                    "OPENAI_MODEL": "gpt-4o-mini",
                    "AGENT_LITELLM_MODEL": "",
                },
                ["openai/gpt-4o-mini"],
            ),
            (
                {
                    "ANTHROPIC_API_KEY": "anthropic-test-key",
                    "ANTHROPIC_MODEL": "claude-3-5-sonnet-20241022",
                    "AGENT_LITELLM_MODEL": "",
                },
                ["anthropic/claude-3-5-sonnet-20241022"],
            ),
        ]

        with patch("src.config.settings.setup_env"), patch.object(Config, "parse_litellm_yaml", return_value=[]):
            for env, expected_models in test_cases:
                with self.subTest(expected_models=expected_models), patch.dict(os.environ, env, clear=True):
                    Config._instance = None
                    config = Config._load_from_env()
                    self.assertEqual(get_effective_agent_models_to_try(config), expected_models)

        Config._instance = None

    def test_build_agent_executor_does_not_mutate_llm_route_config(self) -> None:
        """Agent factory should not rewrite model/base_url/runtime routing fields."""
        provided_config = SimpleNamespace(
            agent_arch="single",
            agent_skills=["bull_trend"],
            agent_max_steps="10",
            agent_orchestrator_timeout_s="120",
            litellm_model="openai/gpt-5",
            agent_litellm_model="anthropic/claude-3-7-sonnet-20250219",
            openai_base_url="https://api.openai.com/v1",
        )
        captured: Dict[str, Any] = {}

        def _mock_llm_adapter(cfg):
            captured["cfg"] = cfg
            return MagicMock()

        fake_llm_module = types.ModuleType("src.infrastructure.agent_runtime.llm_adapter")
        fake_llm_module.LLMToolAdapter = _mock_llm_adapter

        fake_executor_module = types.ModuleType("src.application.agent.executor")
        fake_executor_cls = MagicMock(return_value=MagicMock())
        fake_executor_module.AgentExecutor = fake_executor_cls

        skill_manager = MagicMock()
        skill_manager.list_skills.return_value = [
            SimpleNamespace(
                name="bull_trend",
                display_name="bull_trend",
                description="bull_trend desc",
                instructions="测试指令",
                default_active=True,
                default_router=True,
                default_priority=100,
                user_invocable=True,
                source="builtin",
            )
        ]
        skill_manager.get_skill_instructions.return_value = "测试指令"

        with patch.dict(sys.modules, {
            "litellm": MagicMock(),
            "src.infrastructure.agent_runtime.llm_adapter": fake_llm_module,
            "src.application.agent.executor": fake_executor_module,
        }):
            factory_module = importlib.import_module("src.application.agent.factory")
            bootstrap_agent_module = importlib.import_module("src.bootstrap.agent")
            with patch.object(factory_module, "get_skill_manager", return_value=skill_manager), \
                 patch.object(factory_module, "get_tool_registry", return_value=MagicMock()):
                bootstrap_agent_module.build_agent_executor(provided_config)

        adapter_cfg = captured.get("cfg")
        self.assertIs(adapter_cfg, provided_config)
        self.assertEqual(provided_config.agent_max_steps, "10")
        self.assertEqual(provided_config.agent_orchestrator_timeout_s, "120")
        self.assertEqual(provided_config.litellm_model, "openai/gpt-5")
        self.assertEqual(provided_config.agent_litellm_model, "anthropic/claude-3-7-sonnet-20250219")
        self.assertEqual(provided_config.openai_base_url, "https://api.openai.com/v1")
        fake_executor_cls.assert_called_once()
        kwargs = fake_executor_cls.call_args.kwargs
        self.assertEqual(kwargs["max_steps"], 10)
        self.assertEqual(kwargs["timeout_seconds"], 120)

    def test_build_agent_executor_multi_arch_does_not_mutate_llm_route_config(self) -> None:
        """Multi-arch path should keep provider/base_url/runtime fields unchanged."""
        provided_config = SimpleNamespace(
            agent_arch="multi",
            agent_skills=["bull_trend"],
            agent_max_steps="10",
            agent_orchestrator_timeout_s="120",
            litellm_model="openai/gpt-5",
            agent_litellm_model="anthropic/claude-3-7-sonnet-20250219",
            openai_base_url="https://api.openai.com/v1",
            agent_orchestrator_mode="standard",
        )
        captured: Dict[str, Any] = {}

        def _mock_llm_adapter(cfg):
            captured["cfg"] = cfg
            return MagicMock()

        fake_llm_module = types.ModuleType("src.infrastructure.agent_runtime.llm_adapter")
        fake_llm_module.LLMToolAdapter = _mock_llm_adapter

        fake_orchestrator_module = types.ModuleType("src.application.agent.orchestrator")
        fake_orchestrator_cls = MagicMock(return_value=MagicMock())
        fake_orchestrator_module.AgentOrchestrator = fake_orchestrator_cls

        skill_manager = MagicMock()
        skill_manager.list_skills.return_value = [
            SimpleNamespace(
                name="bull_trend",
                display_name="bull_trend",
                description="bull_trend desc",
                instructions="测试指令",
                default_active=True,
                default_router=True,
                default_priority=100,
                user_invocable=True,
                source="builtin",
            )
        ]
        skill_manager.get_skill_instructions.return_value = "测试指令"

        with patch.dict(sys.modules, {
            "litellm": MagicMock(),
            "src.infrastructure.agent_runtime.llm_adapter": fake_llm_module,
            "src.application.agent.orchestrator": fake_orchestrator_module,
            "src.application.agent.executor": MagicMock(),
        }):
            factory_module = importlib.import_module("src.application.agent.factory")
            bootstrap_agent_module = importlib.import_module("src.bootstrap.agent")
            with patch.object(factory_module, "get_skill_manager", return_value=skill_manager), \
                 patch.object(factory_module, "get_tool_registry", return_value=MagicMock()):
                bootstrap_agent_module.build_agent_executor(provided_config)

        adapter_cfg = captured.get("cfg")
        self.assertIs(adapter_cfg, provided_config)
        self.assertEqual(provided_config.agent_max_steps, "10")
        self.assertEqual(provided_config.agent_orchestrator_timeout_s, "120")
        self.assertEqual(provided_config.litellm_model, "openai/gpt-5")
        self.assertEqual(provided_config.agent_litellm_model, "anthropic/claude-3-7-sonnet-20250219")
        self.assertEqual(provided_config.openai_base_url, "https://api.openai.com/v1")
        fake_orchestrator_cls.assert_called_once()
        kwargs = fake_orchestrator_cls.call_args.kwargs
        self.assertEqual(kwargs["max_steps"], 10)
        self.assertIs(kwargs["config"], provided_config)

    def test_invalid_numeric_config_values_fallback_to_defaults_with_warning(self) -> None:
        """Invalid agent_max_steps / agent_orchestrator_timeout_s should fallback and emit warning."""
        provided_config = SimpleNamespace(
            agent_arch="single",
            agent_skills=["bull_trend"],
            agent_max_steps="invalid-steps",
            agent_orchestrator_timeout_s="invalid-timeout",
            litellm_model="openai/gpt-5",
            agent_litellm_model="anthropic/claude-3-7-sonnet-20250219",
            openai_base_url="https://api.openai.com/v1",
        )
        captured: Dict[str, Any] = {}

        def _mock_llm_adapter(cfg):
            captured["cfg"] = cfg
            return MagicMock()

        fake_llm_module = types.ModuleType("src.infrastructure.agent_runtime.llm_adapter")
        fake_llm_module.LLMToolAdapter = _mock_llm_adapter

        fake_executor_module = types.ModuleType("src.application.agent.executor")
        fake_executor_cls = MagicMock(return_value=MagicMock())
        fake_executor_module.AgentExecutor = fake_executor_cls

        skill_manager = MagicMock()
        skill_manager.list_skills.return_value = [
            SimpleNamespace(
                name="bull_trend",
                display_name="bull_trend",
                description="bull_trend desc",
                instructions="测试指令",
                default_active=True,
                default_router=True,
                default_priority=100,
                user_invocable=True,
                source="builtin",
            )
        ]
        skill_manager.get_skill_instructions.return_value = "测试指令"

        with self.assertLogs("src.application.agent.factory", level="WARNING") as logs:
            with patch.dict(sys.modules, {
                "litellm": MagicMock(),
                "src.infrastructure.agent_runtime.llm_adapter": fake_llm_module,
                "src.application.agent.executor": fake_executor_module,
            }):
                factory_module = importlib.import_module("src.application.agent.factory")
                bootstrap_agent_module = importlib.import_module("src.bootstrap.agent")
                with patch.object(factory_module, "get_skill_manager", return_value=skill_manager), \
                     patch.object(factory_module, "get_tool_registry", return_value=MagicMock()):
                    bootstrap_agent_module.build_agent_executor(provided_config)

        adapter_cfg = captured.get("cfg")
        self.assertIs(adapter_cfg, provided_config)
        self.assertEqual(provided_config.litellm_model, "openai/gpt-5")
        self.assertEqual(provided_config.agent_litellm_model, "anthropic/claude-3-7-sonnet-20250219")
        self.assertEqual(provided_config.openai_base_url, "https://api.openai.com/v1")

        log_output = "\n".join(logs.output)
        self.assertIn("[AgentFactory] Invalid value for agent_max_steps", log_output)
        self.assertIn("[AgentFactory] Invalid value for agent_orchestrator_timeout_s", log_output)

        kwargs = fake_executor_cls.call_args.kwargs
        from src.config import AGENT_MAX_STEPS_DEFAULT
        self.assertEqual(kwargs["max_steps"], AGENT_MAX_STEPS_DEFAULT)
        self.assertEqual(kwargs["timeout_seconds"], 0)
