"""Tests for agent pipeline skills."""

from tests.application.agent._agent_pipeline_support import (
    MagicMock,
    _TestPipelineSkillRegistrationFixture,
    _TestSkillActivationFixture,
    _builtin_strategy_names,
    patch,
    unittest,
)


class TestPipelineSkillRegistration(_TestPipelineSkillRegistrationFixture, unittest.TestCase):
    def test_load_builtin_strategies(self):
        """SkillManager.load_builtin_strategies() should load all YAML strategies."""
        from src.application.agent.skills.base import SkillManager

        skill_manager = SkillManager()
        expected = _builtin_strategy_names()
        count = skill_manager.load_builtin_strategies()
        self.assertEqual(count, len(expected))

        skills = skill_manager.list_skills()
        self.assertEqual(len(skills), len(expected))

        names = {s.name for s in skills}
        self.assertEqual(names, expected)

        # All should be disabled by default
        active = skill_manager.list_active_skills()
        self.assertEqual(len(active), 0)

        # All should have source='builtin'
        for s in skills:
            self.assertEqual(s.source, "builtin")


class TestSkillActivation(_TestSkillActivationFixture, unittest.TestCase):
    def test_skills_default_disabled(self):
        """After registration, skills should be disabled by default."""
        from src.application.agent.skills.base import SkillManager, Skill

        manager = SkillManager()
        # Create a fresh Skill with default enabled=False
        test_skill = Skill(
            name="test_disabled",
            display_name="Test",
            description="test",
            instructions="test",
        )
        manager.register(test_skill)
        active = manager.list_active_skills()
        self.assertEqual(len(active), 0, "Skills should be disabled by default")

    def test_activate_all(self):
        """activate(['all']) should enable all registered skills."""
        from src.application.agent.skills.base import SkillManager, Skill

        manager = SkillManager()
        # Create test skills instead of importing deleted Python modules
        skill1 = Skill(name="dragon_head", display_name="龙头策略",
                       description="test", instructions="test")
        skill2 = Skill(name="shrink_pullback", display_name="缩量回踩",
                       description="test", instructions="test")
        manager.register(skill1)
        manager.register(skill2)
        manager.activate(["all"])
        active = manager.list_active_skills()
        self.assertEqual(len(active), 2)

    def test_activate_specific(self):
        """activate with specific names should only enable those."""
        from src.application.agent.skills.base import SkillManager, Skill

        manager = SkillManager()
        skill1 = Skill(name="dragon_head", display_name="龙头策略",
                       description="test", instructions="test")
        skill2 = Skill(name="shrink_pullback", display_name="缩量回踩",
                       description="test", instructions="test")
        skill3 = Skill(name="volume_breakout", display_name="放量突破",
                       description="test", instructions="test")
        manager.register(skill1)
        manager.register(skill2)
        manager.register(skill3)
        manager.activate(["dragon_head"])
        active = manager.list_active_skills()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].name, "dragon_head")

    def test_empty_config_uses_primary_default_skill(self):
        """Empty agent_skills config should activate the primary default skill only."""
        from src.application.agent.skills.base import SkillManager
        from src.application.agent.skills.defaults import get_default_active_skill_ids

        skill_manager = SkillManager()
        count = skill_manager.load_builtin_strategies()
        self.assertEqual(count, len(_builtin_strategy_names()), "Should load all built-in strategies from YAML")

        default_ids = get_default_active_skill_ids(skill_manager.list_skills())
        self.assertEqual(default_ids, ["bull_trend"])
        skill_manager.activate(default_ids)

        active = skill_manager.list_active_skills()
        self.assertEqual([skill.name for skill in active], ["bull_trend"])

    def test_sentiment_score_parsed_from_dashboard(self):
        """Verify _agent_result_to_analysis_result handles non-numeric sentiment_score."""
        with patch('src.application.analysis.pipeline.get_config') as mock_config, \
             patch('src.application.analysis.pipeline.build_pipeline_persistence_port'), \
             patch('src.application.analysis.pipeline.build_stock_data_port', return_value=MagicMock()), \
             patch('src.application.analysis.pipeline.GeminiAnalyzer'), \
             patch('src.application.analysis.pipeline.NotificationService'), \
             patch('src.application.analysis.pipeline.SearchService'):

            mock_cfg = MagicMock()
            mock_cfg.max_workers = 2
            mock_cfg.agent_mode = True
            mock_cfg.agent_max_steps = 10
            mock_cfg.agent_skills = []
            mock_cfg.bocha_api_keys = []
            mock_cfg.tavily_api_keys = []
            mock_cfg.brave_api_keys = []
            mock_cfg.serpapi_keys = []
            mock_cfg.searxng_base_urls = []
            mock_cfg.searxng_public_instances_enabled = False
            mock_cfg.news_max_age_days = 7
            mock_cfg.enable_realtime_quote = True
            mock_cfg.enable_chip_distribution = True
            mock_cfg.realtime_source_priority = []
            mock_cfg.save_context_snapshot = False
            mock_config.return_value = mock_cfg

            from src.application.analysis.pipeline import StockAnalysisPipeline
            from src.application.agent.executor import AgentResult
            from src.domain.shared.enums import ReportType
            pipeline = StockAnalysisPipeline(config=mock_cfg)

            # Dashboard with "80分" instead of 80
            agent_result = AgentResult(
                success=True,
                content="{}",
                dashboard={
                    "stock_name": "TestCo",
                    "sentiment_score": "80分",
                    "trend_prediction": "看多",
                    "operation_advice": "买入",
                    "decision_type": "buy",
                },
                provider="gemini",
            )

            result = pipeline._agent_result_to_analysis_result(
                agent_result, "600519", "TestCo", ReportType.SIMPLE, "q1"
            )
            self.assertEqual(result.sentiment_score, 80)
