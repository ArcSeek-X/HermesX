# -*- coding: utf-8 -*-
# 本文件主要测试：测试多智能体相关功能
"""
Tests for the multi-agent architecture modules.

Covers:
- _extract_stock_code: Chinese boundary, HK, US, common word filtering
- AgentContext / AgentOpinion / StageResult protocol basics
- AgentOrchestrator: pipeline execution, mode selection, error handling
- StrategyRouter: regime detection, manual mode, user override
- StrategyAggregator: weighted consensus, empty input
- PortfolioAgent.post_process: JSON parsing via try_parse_json
"""

import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

# Keep test runnable when optional LLM deps are missing
try:
    import litellm  # noqa: F401
except ModuleNotFoundError:
    sys.modules["litellm"] = MagicMock()

from src.application.agent.orchestrator import _extract_stock_code, _COMMON_WORDS, AgentOrchestrator
from src.application.agent.protocols import (
    AgentContext,
    AgentOpinion,
    AgentRunStats,
    Signal,
    StageResult,
    StageStatus,
    StrategyOpinion,
    normalize_strategy_signal,
    is_valid_strategy_signal,
)
from src.application.agent.skills.synthesis import (
    strategy_opinion_from_agent_opinion,
    StrategySynthesizer,
)
from src.application.agent.skills.aggregator import SkillAggregator
from src.application.agent.stock_scope import StockScope, resolve_stock_scope
from src.config import AGENT_MAX_STEPS_DEFAULT, Config
from src.infrastructure.persistence.repositories.conversation_repo import ConversationRepository
from src.storage import DatabaseManager


# ============================================================
# _extract_stock_code
# ============================================================


# ============================================================
# Stock scope resolution
# ============================================================


# ============================================================
# Protocol dataclasses
# ============================================================


# ============================================================
# Legacy StrategyRouter Compatibility
# ============================================================


# ============================================================
# StrategyAggregator
# ============================================================


# ============================================================
# PortfolioAgent.post_process
# ============================================================


# ============================================================
# AgentOrchestrator (with mocked sub-agents)
# ============================================================


# ============================================================
# EventMonitor serialization
# ============================================================


# ============================================================
# AgentMemory
# ============================================================


# ============================================================
# ResearchCommand timeout guard
# ============================================================


# ============================================================
# ResearchAgent filtered registry & API endpoint
# ============================================================


class _TestExtractStockCodeFixture:
    """Validate stock code extraction from free text."""


class _TestStockScopeResolutionFixture:
    """Validate chat stock-scope state transitions."""


class _TestAgentContextFixture:
    """Test AgentContext helpers."""


class _TestAgentOpinionFixture:
    """Test AgentOpinion clamping and signal parsing."""


class _TestAgentRunStatsFixture:
    """Test AgentRunStats aggregation."""


class _TestStrategyRouterFixture:
    """Test the legacy StrategyRouter alias for SkillRouter."""


class _TestStrategyAggregatorFixture:
    """Test StrategyAggregator consensus logic."""


class _TestPortfolioAgentPostProcessFixture:
    """Test PortfolioAgent.post_process uses try_parse_json correctly."""
    def _make_agent(self):
        from src.application.agent.agents.portfolio_agent import PortfolioAgent
        mock_registry = MagicMock()
        mock_adapter = MagicMock()
        return PortfolioAgent(tool_registry=mock_registry, llm_adapter=mock_adapter)


class _TestDecisionAgentPostProcessFixture:
    """Test DecisionAgent dashboard normalization behaviour."""


class _TestIntelAgentPostProcessFixture:
    """Test IntelAgent JSON parsing and context caching behaviour."""


class _TestOrchestratorModesFixture:
    """Test that _build_agent_chain returns the right agents for each mode."""
    def _make_orchestrator(self, mode="standard"):
        from src.application.agent.orchestrator import AgentOrchestrator
        mock_registry = MagicMock()
        mock_adapter = MagicMock()
        return AgentOrchestrator(
            tool_registry=mock_registry,
            llm_adapter=mock_adapter,
            mode=mode,
        )


class _TestOrchestratorExecutionFixture:
    """Test main orchestrator execution paths."""
    @staticmethod
    def _make_orchestrator(config=None):
        from src.application.agent.orchestrator import AgentOrchestrator
        return AgentOrchestrator(
            tool_registry=MagicMock(),
            llm_adapter=MagicMock(),
            config=config,
        )
    @staticmethod
    def _stage_result(name, status=StageStatus.COMPLETED, error=None, raw_text="ok"):
        result = StageResult(stage_name=name, status=status, error=error)
        result.meta["raw_text"] = raw_text
        result.meta["models_used"] = ["test/model"]
        return result
    @staticmethod
    def _decision_agent():
        from src.application.agent.agents.decision_agent import DecisionAgent

        return DecisionAgent(tool_registry=MagicMock(), llm_adapter=MagicMock())
    @staticmethod
    def _dashboard_json(decision_type="buy"):
        return json.dumps({
            "stock_name": "Test Stock",
            "sentiment_score": 72,
            "trend_prediction": "up",
            "operation_advice": "buy",
            "decision_type": decision_type,
            "confidence_level": "Medium",
            "dashboard": {
                "phase_decision": {
                    "phase_context": "regular",
                    "action_window": "now",
                    "immediate_action": "watch",
                    "watch_conditions": [],
                    "next_check_time": "next session",
                    "confidence_reason": "test fixture",
                    "data_limitations": [],
                },
                "core_conclusion": {
                    "one_sentence": "test decision",
                    "signal_type": "buy",
                    "position_advice": {
                        "no_position": "watch",
                        "has_position": "hold",
                    },
                },
            },
            "analysis_summary": "test summary",
            "key_points": ["technical fixture"],
            "risk_warning": "",
        }, ensure_ascii=False)
    class _OpinionStage:
        def __init__(
            self,
            agent_name,
            *,
            signal="hold",
            confidence=0.5,
            reasoning="fixture opinion",
            raw_data=None,
        ):
            self.agent_name = agent_name
            self.signal = signal
            self.confidence = confidence
            self.reasoning = reasoning
            self.raw_data = raw_data or {}

        def run(self, ctx, progress_callback=None, timeout_seconds=None):
            ctx.add_opinion(AgentOpinion(
                agent_name=self.agent_name,
                signal=self.signal,
                confidence=self.confidence,
                reasoning=self.reasoning,
                raw_data=self.raw_data,
            ))
            result = StageResult(stage_name=self.agent_name, status=StageStatus.COMPLETED)
            result.meta["raw_text"] = self.reasoning
            result.meta["models_used"] = ["test/model"]
            return result
    class _FailedStage:
        def __init__(self, agent_name, error="stage failed"):
            self.agent_name = agent_name
            self.error = error

        def run(self, ctx, progress_callback=None, timeout_seconds=None):
            result = StageResult(
                stage_name=self.agent_name,
                status=StageStatus.FAILED,
                error=self.error,
            )
            result.meta["raw_text"] = ""
            result.meta["models_used"] = ["test/model"]
            return result
    def _make_config_with_sub_agent_timeouts(self, **kwargs):
        """Return a SimpleNamespace config with sub-agent timeout fields."""
        defaults = {
            "agent_orchestrator_timeout_s": 0,
            "agent_technical_agent_timeout_s": 0,
            "agent_intel_agent_timeout_s": 0,
            "agent_risk_agent_timeout_s": 0,
            "agent_decision_agent_timeout_s": 0,
            "agent_portfolio_agent_timeout_s": 0,
            "agent_skill_agent_timeout_s": 0,
            "agent_risk_override": True,
        }
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)


class _TestDecisionAgentChatModeFixture:
    """Test DecisionAgent chat-mode output path."""


class _TestTechnicalAgentSkillPolicyFixture:
    """TechnicalAgent should only receive the legacy trend baseline for implicit/default runs."""


class _TestBaseAgentMessageAssemblyFixture:
    """Test BaseAgent message assembly helpers."""
    @staticmethod
    def _make_agent():
        from src.application.agent.agents.base_agent import BaseAgent

        class DummyAgent(BaseAgent):
            agent_name = "dummy"

            def system_prompt(self, ctx: AgentContext) -> str:
                return "system"

            def build_user_message(self, ctx: AgentContext) -> str:
                return "current turn"

        return DummyAgent(tool_registry=MagicMock(), llm_adapter=MagicMock())


class _TestEventMonitorFixture:
    """Test EventMonitor serialize/deserialize round-trip."""


class _TestEventMonitorAsyncFixture:
    """Test async EventMonitor checks offload blocking fetches."""


class _TestEventMonitorConfigIntegrationFixture:
    """Test config-driven EventMonitor construction."""


class _TestAgentMemoryFixture:
    """Test AgentMemory disabled mode."""


class _TestBaseAgentMemoryIntegrationFixture:
    """Test BaseAgent hooks for memory injection and calibration."""
    @staticmethod
    def _make_agent(memory):
        from src.application.agent.agents.base_agent import BaseAgent

        class DummyAgent(BaseAgent):
            agent_name = "technical"

            def system_prompt(self, ctx):
                return "system"

            def build_user_message(self, ctx):
                return "user"

            def post_process(self, ctx, raw_text):
                return AgentOpinion(agent_name="technical", signal="buy", confidence=0.8, reasoning=raw_text)

        with patch("src.application.agent.agents.base_agent.AgentMemory.from_config", return_value=memory):
            return DummyAgent(tool_registry=MagicMock(), llm_adapter=MagicMock())


class _TestRiskOverrideFixture:
    """Test orchestrator-level risk override integration."""
    def _make_dashboard(self):
        return {
            "decision_type": "buy",
            "sentiment_score": 76,
            "operation_advice": "买入",
            "analysis_summary": "原始结论",
            "risk_warning": "原风险提示",
            "dashboard": {
                "core_conclusion": {
                    "one_sentence": "可以参与",
                    "signal_type": "🟢买入信号",
                    "position_advice": {
                        "no_position": "分批买入",
                        "has_position": "继续持有",
                    },
                }
            },
        }


class _TestResearchCommandTimeoutFixture:
    """Verify that ResearchCommand respects the configured timeout."""


class _TestResearchAgentFilteredRegistryFixture:
    """Test that ResearchAgent._filtered_registry delegates to BaseAgent's implementation."""


class _TestP1SemanticConvergenceFixture:
    """覆盖 PR reviewer 提出的 5 个 P1 阻断项的端到端入口测试"""


class _TestStrategyEngineE2EFixture:
    """E2E tests exercising StrategyEngine as the authoritative pipeline facade."""
    def _make_orchestrator(self):
        return AgentOrchestrator(
            tool_registry=MagicMock(),
            llm_adapter=MagicMock(),
            mode="specialist",
        )

