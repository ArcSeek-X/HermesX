# -*- coding: utf-8 -*-
# 本文件主要测试：测试大盘分析器生成文本相关功能
"""Tests for Analyzer.generate_text() and the market_analyzer bypass fix.

Covers:
- generate_text() returns the LLM response on success
- generate_text() returns None and logs on ordinary failures
- generation backend configuration errors propagate explicitly
- market_analyzer calls generate_text(), not private analyzer attributes
- Any provider configuration (Gemini / Anthropic / OpenAI / LLM_CHANNELS)
  does NOT trigger AttributeError (regression guard for the old bypass bug)
"""
import json
import sys
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# Stub heavy dependencies before project imports
for _mod in ("litellm", "google.generativeai", "google.genai", "anthropic"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import pytest

from src.application.analysis import analyzer as analyzer_module
from src.bootstrap.analyzer import configure_analyzer_runtime
from src.bootstrap.generation import configure_generation_runtime

# 顶层装配 Analyzer LLM 运行时端口（§4.3 A2；T5f configure_system_config_runtime 同型）：
# litellm Router/completion/no-proxy 外调簇已下沉 infra 适配器，用例经 seam 消费，未装配即 fail-fast。
configure_analyzer_runtime()
# 生成链路端口（R2-A3）：后端工厂 / 参数归一 / usage / provider cache 外调簇同型下沉。
configure_generation_runtime()


def _usage_port():
    """返回已装配的生成链路用量遥测端口（用例统一 patch 其 ``persist``）。"""

    return analyzer_module._get_generation_usage_port()


@pytest.fixture(autouse=True)
def _llm_usage_hmac_env(monkeypatch):
    monkeypatch.setenv("LLM_USAGE_HMAC_SECRET", "test-usage-hmac-secret")
    monkeypatch.setenv("LLM_USAGE_HMAC_KEY_VERSION", "test-v1")


def _assert_usage_contains(usage, expected):
    for key, value in expected.items():
        assert usage[key] == value
    assert usage["normalized_prompt_tokens"] == expected.get("prompt_tokens")
    assert usage["normalized_completion_tokens"] == expected.get("completion_tokens")
    assert usage["normalized_total_tokens"] == expected.get("total_tokens")
    assert usage["provider_usage_json"]
    assert usage["messages_hmac"] and len(usage["messages_hmac"]) == 64
    assert usage["hmac_key_version"] == "test-v1"


def _assert_no_provider_usage_hmac_only(usage):
    assert "prompt_tokens" not in usage
    assert usage["messages_hmac"] and len(usage["messages_hmac"]) == 64
    assert usage["hmac_key_version"] == "test-v1"


_OPENAI_COMPATIBILITY_PAYLOAD_FIXTURES = [
    # Repro case 1 (Issue #1279): OpenAI-compatible provider message.content is None while text is in content_blocks.
    (
        "openai/cpa-compatible",
        {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "content_blocks": [
                            {"type": "text", "text": "block "},
                            {"type": "text", "text": "response"},
                        ],
                    },
                }
            ],
            "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
        },
        "block response",
    ),
    # Repro case 2: OpenAI-compatible provider returns message.content as list-of-blocks.
    (
        "openai/list-content-provider",
        {
            "choices": [
                {
                    "message": {
                        "content": [
                            {"type": "text", "text": "list "},
                            {"type": "text", "text": "response"},
                        ],
                    },
                }
            ],
            "usage": {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7},
        },
        "list response",
    ),
    # Repro case 3 (Issue #2013): MiniMax reasoning and final text share
    # content_blocks.  Only the final text may reach the strict JSON parser.
    (
        "openai/MiniMax-M3",
        {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "content_blocks": [
                            {"type": "reasoning", "text": "I should analyze the stock first."},
                            {"type": "text", "text": '{"sentiment_score": 72}'},
                        ],
                    },
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        },
        '{"sentiment_score": 72}',
    ),
]


# ---------------------------------------------------------------------------
# Analyzer.generate_text()
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# market_analyzer uses generate_text(), not private attributes
# ---------------------------------------------------------------------------


class _TestAnalyzerGenerateTextFixture:
    def _make_analyzer(self):
        """Return a minimally configured GeminiAnalyzer with _call_litellm mocked."""
        with patch("src.application.analysis.analyzer.get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.litellm_model = "gemini/gemini-2.0-flash"
            cfg.litellm_fallback_models = []
            cfg.gemini_api_keys = ["sk-gemini-testkey-1234"]
            cfg.anthropic_api_keys = []
            cfg.openai_api_keys = []
            cfg.deepseek_api_keys = []
            cfg.llm_model_list = []
            cfg.openai_base_url = None
            cfg.generation_backend = "litellm"
            cfg.generation_fallback_backend = "litellm"
            mock_cfg.return_value = cfg
            from src.application.analysis.analyzer import GeminiAnalyzer
            analyzer = GeminiAnalyzer.__new__(GeminiAnalyzer)
            analyzer._router = None
            analyzer._litellm_available = True
            analyzer._config_override = cfg
            return analyzer


class _TestMarketAnalyzerBypassFixFixture:
    def _make_market_analyzer_with_mock_generate_text(self, return_value="复盘报告"):
        """Return a MarketAnalyzer whose embedded Analyzer.generate_text is mocked."""
        from src.domain.market.profile import CN_PROFILE
        from src.domain.market.strategy import get_market_strategy_blueprint

        with patch("src.application.analysis.analyzer.get_config") as mock_cfg, \
             patch("src.application.market.market_analyzer.get_config") as mock_cfg2:
            cfg = MagicMock()
            cfg.litellm_model = "gemini/gemini-2.0-flash"
            cfg.litellm_fallback_models = []
            cfg.gemini_api_keys = ["sk-gemini-testkey-1234"]
            cfg.anthropic_api_keys = []
            cfg.openai_api_keys = []
            cfg.deepseek_api_keys = []
            cfg.llm_model_list = []
            cfg.openai_base_url = None
            cfg.market_review_region = "cn"
            cfg.market_review_color_scheme = "green_up"
            cfg.report_language = "zh"
            cfg.generation_backend = "litellm"
            cfg.generation_fallback_backend = "litellm"
            mock_cfg.return_value = cfg
            mock_cfg2.return_value = cfg

            from src.application.analysis.analyzer import GeminiAnalyzer
            from src.application.market.market_analyzer import MarketAnalyzer

            analyzer = GeminiAnalyzer.__new__(GeminiAnalyzer)
            analyzer._router = None
            analyzer._litellm_available = True
            analyzer._config_override = cfg
            analyzer.generate_text = MagicMock(return_value=return_value)

            ma = MarketAnalyzer.__new__(MarketAnalyzer)
            ma.analyzer = analyzer
            ma.config = cfg
            ma.profile = CN_PROFILE
            ma.strategy = get_market_strategy_blueprint("cn")
            ma.region = "cn"
            return ma


class _AnalyzerRuntimePortWiringTestCaseFixture:
    """§4.3 拆分 A2 后的端口装配链路回归：bootstrap 绑定 seam、None 幂等、未装配 fail-fast。"""


class _TestGenerationUsagePersistPortFixture:
    """用量遥测写侧端口回归：adapter 委托 ``src.storage``，标签参数逐字透传。"""

