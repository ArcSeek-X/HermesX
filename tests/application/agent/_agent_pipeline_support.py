# -*- coding: utf-8 -*-
# 本文件主要测试：测试智能体流水线相关功能
"""
Tests for agent-mode pipeline integration.

Covers:
- Config: agent_mode, agent_max_steps, agent_skills fields
- _analyze_with_agent method
- _agent_result_to_analysis_result conversion
- YAML strategy loading (load_builtin_strategies)
"""

import json
import importlib
import types
import unittest
import sys
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from tests.support.stubs.litellm_stub import ensure_litellm_stub

ensure_litellm_stub()

from tests.support.paths import get_repo_root


def _builtin_strategy_names() -> set[str]:
    strategies_dir = get_repo_root() / "strategies"
    return {path.stem for path in strategies_dir.glob("*.yaml")}


# ============================================================
# Config tests
# ============================================================


# ============================================================
# AgentResult to AnalysisResult conversion
# ============================================================


# ============================================================
# Skill registration in pipeline
# ============================================================


# ============================================================
# Pipeline dual-path routing
# ============================================================


# ============================================================
# Agent construction chain (real objects, mocked LLM)
# ============================================================


# ============================================================
# _safe_int tests
# ============================================================


# ============================================================
# Skill activation semantics
# ============================================================


class _TestAgentConfigFixture:
    """Test agent-related configuration fields load correctly."""


class _TestAgentFactorySkillBaselineFixture:
    """Ensure explicit skill selection does not silently re-apply the default bull-trend baseline."""
    @staticmethod
    def _make_skill(
        name: str,
        *,
        default_active: bool = False,
        default_priority: int = 100,
        source: str = "builtin",
    ):
        return SimpleNamespace(
            name=name,
            display_name=name,
            description=f"{name} desc",
            instructions=f"{name} instructions",
            default_active=default_active,
            default_router=default_active,
            default_priority=default_priority,
            user_invocable=True,
            source=source,
        )
    def _run_factory_case(self, config, *, request_skills, skill_catalog, instructions):
        skill_manager = MagicMock()
        skill_manager.list_skills.return_value = skill_catalog
        skill_manager.get_skill_instructions.return_value = instructions

        fake_llm_module = types.ModuleType("src.infrastructure.agent_runtime.llm_adapter")
        fake_llm_module.LLMToolAdapter = MagicMock(return_value=MagicMock())
        fake_executor_module = types.ModuleType("src.application.agent.executor")
        fake_executor_cls = MagicMock(return_value=MagicMock())
        fake_executor_module.AgentExecutor = fake_executor_cls

        with patch.dict(sys.modules, {
            "litellm": MagicMock(),
            "src.infrastructure.agent_runtime.llm_adapter": fake_llm_module,
            "src.application.agent.executor": fake_executor_module,
        }):
            factory_module = importlib.import_module("src.application.agent.factory")
            bootstrap_agent_module = importlib.import_module("src.bootstrap.agent")

            with patch.object(factory_module, "get_skill_manager", return_value=skill_manager), \
                 patch.object(factory_module, "get_tool_registry", return_value=MagicMock()):
                bootstrap_agent_module.build_agent_executor(config, skills=request_skills)

        return fake_executor_cls.call_args.kwargs, skill_manager


class _TestAgentResultConversionFixture:
    """Test _agent_result_to_analysis_result without spinning up the full pipeline."""
    def _make_pipeline(self):
        """Create a minimal StockAnalysisPipeline with mocked dependencies."""
        # We need to import and mock carefully to avoid touching real services
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
            mock_cfg.agent_orchestrator_timeout_s = 0
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
            pipeline = StockAnalysisPipeline(config=mock_cfg)
            return pipeline


class _TestPipelineSkillRegistrationFixture:
    """Test built-in strategies load from YAML via SkillManager."""


class _TestPipelineRoutingFixture:
    """Test that analyze_stock routes to agent mode when config.agent_mode is True."""


class _TestAnalyzeWithAgentStockNameFixture:
    """Test stock-name handling in _analyze_with_agent."""


class _TestAgentConstructionChainFixture:
    """Test that the agent construction chain wires up correctly."""


class _TestSafeIntFixture:
    """Test the _safe_int helper for robust sentiment_score parsing."""
    def _get_safe_int(self):
        """Get reference to StockAnalysisPipeline._safe_int static method."""
        with patch('src.application.analysis.pipeline.get_config') as mock_config, \
             patch('src.application.analysis.pipeline.build_pipeline_persistence_port'), \
             patch('src.application.analysis.pipeline.build_stock_data_port', return_value=MagicMock()), \
             patch('src.application.analysis.pipeline.GeminiAnalyzer'), \
             patch('src.application.analysis.pipeline.NotificationService'), \
             patch('src.application.analysis.pipeline.SearchService'):

            mock_cfg = MagicMock()
            mock_cfg.max_workers = 2
            mock_cfg.agent_mode = False
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
            from src.application.analysis.agent_result_mapper import AgentResultMapper
        return AgentResultMapper.safe_int


class _TestSkillActivationFixture:
    """Test that skill activation follows the correct semantics."""

