"""Tests for agent pipeline factory."""

from tests.application.agent._agent_pipeline_support import (
    SimpleNamespace,
    _TestAgentFactorySkillBaselineFixture,
    unittest,
)


class TestAgentFactorySkillBaseline(_TestAgentFactorySkillBaselineFixture, unittest.TestCase):
    def test_explicit_request_disables_default_skill_policy(self):
        config = SimpleNamespace(
            agent_arch="single",
            agent_skills=[],
            agent_max_steps=10,
            agent_orchestrator_timeout_s=600,
        )
        kwargs, skill_manager = self._run_factory_case(
            config,
            request_skills=["chan_theory"],
            skill_catalog=[
                self._make_skill("bull_trend", default_active=True, default_priority=10),
                self._make_skill("chan_theory", default_priority=20),
            ],
            instructions="chan_theory instructions",
        )

        self.assertEqual(kwargs["default_skill_policy"], "")
        self.assertFalse(kwargs["use_legacy_default_prompt"])
        skill_manager.activate.assert_called_once_with(["chan_theory"])

    def test_configured_skills_disable_default_skill_policy(self):
        config = SimpleNamespace(
            agent_arch="single",
            agent_skills=["wave_theory"],
            agent_max_steps=10,
            agent_orchestrator_timeout_s=600,
        )
        kwargs, skill_manager = self._run_factory_case(
            config,
            request_skills=None,
            skill_catalog=[
                self._make_skill("bull_trend", default_active=True, default_priority=10),
                self._make_skill("wave_theory", default_priority=20),
            ],
            instructions="wave_theory instructions",
        )

        self.assertEqual(kwargs["default_skill_policy"], "")
        self.assertFalse(kwargs["use_legacy_default_prompt"])
        skill_manager.activate.assert_called_once_with(["wave_theory"])

    def test_implicit_default_run_keeps_default_skill_policy(self):
        config = SimpleNamespace(
            agent_arch="single",
            agent_skills=[],
            agent_max_steps=10,
            agent_orchestrator_timeout_s=600,
        )
        kwargs, skill_manager = self._run_factory_case(
            config,
            request_skills=None,
            skill_catalog=[self._make_skill("bull_trend", default_active=True, default_priority=10)],
            instructions="bull_trend instructions",
        )

        self.assertIn("严进策略", kwargs["default_skill_policy"])
        self.assertTrue(kwargs["use_legacy_default_prompt"])
        skill_manager.activate.assert_called_once_with(["bull_trend"])

    def test_explicit_empty_request_falls_back_to_primary_default_skill(self):
        config = SimpleNamespace(
            agent_arch="single",
            agent_skills=[],
            agent_max_steps=10,
            agent_orchestrator_timeout_s=600,
        )
        kwargs, skill_manager = self._run_factory_case(
            config,
            request_skills=[],
            skill_catalog=[
                self._make_skill("bull_trend", default_active=True, default_priority=10),
                self._make_skill("chan_theory", default_priority=20),
            ],
            instructions="bull_trend instructions",
        )

        self.assertIn("严进策略", kwargs["default_skill_policy"])
        self.assertTrue(kwargs["use_legacy_default_prompt"])
        skill_manager.activate.assert_called_once_with(["bull_trend"])

    def test_explicit_primary_default_skill_uses_skill_aware_prompt_mode(self):
        config = SimpleNamespace(
            agent_arch="single",
            agent_skills=[],
            agent_max_steps=10,
            agent_orchestrator_timeout_s=600,
        )
        kwargs, skill_manager = self._run_factory_case(
            config,
            request_skills=["bull_trend"],
            skill_catalog=[
                self._make_skill("bull_trend", default_active=True, default_priority=10),
                self._make_skill("chan_theory", default_priority=20),
            ],
            instructions="bull_trend instructions",
        )

        self.assertEqual(kwargs["default_skill_policy"], "")
        self.assertFalse(kwargs["use_legacy_default_prompt"])
        skill_manager.activate.assert_called_once_with(["bull_trend"])

    def test_invalid_configured_skills_fall_back_to_primary_default_skill(self):
        config = SimpleNamespace(
            agent_arch="single",
            agent_skills=["missing_skill"],
            agent_max_steps=10,
            agent_orchestrator_timeout_s=600,
        )
        kwargs, skill_manager = self._run_factory_case(
            config,
            request_skills=None,
            skill_catalog=[
                self._make_skill("bull_trend", default_active=True, default_priority=10),
                self._make_skill("chan_theory", default_priority=20),
            ],
            instructions="bull_trend instructions",
        )

        self.assertIn("严进策略", kwargs["default_skill_policy"])
        self.assertTrue(kwargs["use_legacy_default_prompt"])
        skill_manager.activate.assert_called_once_with(["bull_trend"])

    def test_custom_default_skill_does_not_use_legacy_bull_prompt(self):
        config = SimpleNamespace(
            agent_arch="single",
            agent_skills=[],
            agent_max_steps=10,
            agent_orchestrator_timeout_s=600,
        )
        kwargs, skill_manager = self._run_factory_case(
            config,
            request_skills=None,
            skill_catalog=[
                self._make_skill("custom_default", default_active=True, default_priority=10),
                self._make_skill("bull_trend", default_priority=20),
            ],
            instructions="custom_default instructions",
        )

        self.assertEqual(kwargs["default_skill_policy"], "")
        self.assertFalse(kwargs["use_legacy_default_prompt"])
        skill_manager.activate.assert_called_once_with(["custom_default"])

    def test_custom_bull_trend_override_does_not_use_legacy_prompt(self):
        config = SimpleNamespace(
            agent_arch="single",
            agent_skills=[],
            agent_max_steps=10,
            agent_orchestrator_timeout_s=600,
        )
        kwargs, skill_manager = self._run_factory_case(
            config,
            request_skills=None,
            skill_catalog=[
                self._make_skill(
                    "bull_trend",
                    default_active=True,
                    default_priority=10,
                    source="/tmp/custom-skills/bull_trend.yaml",
                ),
            ],
            instructions="custom bull_trend instructions",
        )

        self.assertEqual(kwargs["default_skill_policy"], "")
        self.assertFalse(kwargs["use_legacy_default_prompt"])
        skill_manager.activate.assert_called_once_with(["bull_trend"])
