# -*- coding: utf-8 -*-
# 本文件主要测试：测试智能体执行器相关功能
"""
Tests for AgentExecutor with mocked LLM adapter.

Covers:
- ReAct loop: tool-calling → result feedback → final answer
- Dashboard JSON parsing (markdown blocks, raw JSON, json_repair)
- Max step limit
- Tool execution error handling
- _serialize_tool_result for various types
- _build_user_message formatting
"""

import json
import time
import unittest
import sys
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# Keep this test runnable when optional LLM runtime deps are not installed.
try:
    import litellm  # noqa: F401
except ModuleNotFoundError:
    sys.modules["litellm"] = MagicMock()

from src.application.agent.executor import (
    AGENT_SYSTEM_PROMPT,
    LEGACY_DEFAULT_AGENT_SYSTEM_PROMPT,
    AgentExecutor,
    AgentResult,
)
from src.infrastructure.agent_runtime.llm_adapter import LLMResponse, ToolCall
from src.application.agent.runner import parse_dashboard_json, run_agent_loop, serialize_tool_result
from src.application.agent.stock_scope import StockScope, resolve_stock_scope
from src.application.agent.tools.registry import ToolRegistry, ToolDefinition, ToolParameter
from src.application.reporting.context_pack_prompt import format_analysis_context_pack_prompt_section
from src.config import Config
from src.infrastructure.agent_runtime.usage_telemetry_provider import UsageTelemetryAdapter
from src.infrastructure.generation.usage import normalize_litellm_usage
from src.infrastructure.persistence.repositories.conversation_repo import ConversationRepository
from src.application.analysis.analysis_context_builder import (
    AnalysisContextBuilder,
    PipelineAnalysisArtifacts,
)
from src.storage import DatabaseManager


# ============================================================
# Helpers
# ============================================================

def _make_registry_with_echo():
    """Create a registry with a simple echo tool."""
    registry = ToolRegistry()
    tool = ToolDefinition(
        name="echo",
        description="Echoes back the input",
        parameters=[
            ToolParameter(name="message", type="string", description="Message to echo"),
        ],
        handler=lambda message: {"echo": message},
    )
    registry.register(tool)
    return registry


def _make_stock_registry(executed_calls):
    """Create a registry with stock-scoped and non-stock tools."""
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="get_realtime_quote",
            description="Gets realtime quote",
            parameters=[
                ToolParameter(name="stock_code", type="string", description="Stock code"),
            ],
            handler=lambda stock_code: executed_calls.append(("quote", stock_code)) or {"stock_code": stock_code},
        )
    )
    registry.register(
        ToolDefinition(
            name="search_stock_news",
            description="Searches stock news",
            parameters=[
                ToolParameter(name="stock_code", type="string", description="Stock code"),
                ToolParameter(name="stock_name", type="string", description="Stock name"),
            ],
            handler=lambda stock_code, stock_name: executed_calls.append(("news", stock_code, stock_name)) or {
                "stock_code": stock_code,
                "stock_name": stock_name,
            },
        )
    )
    registry.register(
        ToolDefinition(
            name="echo",
            description="Echoes back the input",
            parameters=[
                ToolParameter(name="message", type="string", description="Message to echo"),
            ],
            handler=lambda message: executed_calls.append(("echo", message)) or {"echo": message},
        )
    )
    return registry


def _make_mock_adapter():
    """Create a MagicMock LLMToolAdapter."""
    adapter = MagicMock()
    return adapter


def _build_analysis_context_pack_summary(
    *,
    realtime_quote=None,
    fundamental_context=None,
) -> str:
    artifacts = PipelineAnalysisArtifacts(
        code="600519",
        stock_name="贵州茅台",
        market="cn",
        phase=None,
        base_context={
            "today": {"close": 1880.0},
            "yesterday": {"close": 1870.0},
            "date": "2026-03-26",
        },
        enhanced_context={},
        realtime_quote=realtime_quote
        if realtime_quote is not None
        else {"price": 1880.0, "source": "mock_quote"},
        trend_result={"trend_status": "available"},
        chip_data={"source": "mock_chip", "date": "2026-03-26"},
        fundamental_context=fundamental_context
        if fundamental_context is not None
        else {
            "status": "ok",
            "coverage": {"valuation": "ok"},
            "source_chain": [{"provider": "fundamental_pipeline"}],
        },
        news_context="新闻摘要",
        news_result_count=1,
        metadata={"trigger_source": "api"},
    )
    return format_analysis_context_pack_prompt_section(
        AnalysisContextBuilder.build(artifacts),
        report_language="zh",
    )


SAMPLE_DASHBOARD = {
    "stock_name": "贵州茅台",
    "sentiment_score": 75,
    "trend_prediction": "看多",
    "operation_advice": "持有",
    "decision_type": "hold",
    "confidence_level": "中",
    "dashboard": {
        "core_conclusion": {
            "one_sentence": "茅台近期震荡走强",
            "signal_type": "🟡持有观望",
        },
    },
    "analysis_summary": "Overall bullish trend",
    "key_points": "Strong revenue growth",
    "risk_warning": "High valuation",
    "buy_reason": "Sector leader",
    "trend_analysis": "Upward trend",
    "technical_analysis": "MACD golden cross",
}


# ============================================================
# AgentExecutor Tests
# ============================================================


# ============================================================
# Dashboard parsing
# ============================================================


# ============================================================
# Serialization
# ============================================================


# ============================================================
# User message builder
# ============================================================


# ============================================================
# AgentResult dataclass
# ============================================================


class _TestAgentExecutorFixture:
    """Test the ReAct loop logic."""


class _TestDashboardParsingFixture:
    """Test parse_dashboard_json with various input formats."""


class _TestSerializeToolResultFixture:
    """Test serialize_tool_result for various types."""


class _TestBuildUserMessageFixture:
    """Test _build_user_message formatting."""
    def setUp(self):
        self.executor = AgentExecutor(
            ToolRegistry(), _make_mock_adapter(), max_steps=1
        )


class _TestAgentResultFixture:
    """Test AgentResult defaults."""

