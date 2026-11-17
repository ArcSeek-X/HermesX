# -*- coding: utf-8 -*-
"""环境变量解析与档位归一化助手（W5.3）。

从 ``settings.py`` 拆出的低层解析函数：布尔/整数/浮点解析（带钳制与告警）、
TickFlow 复权方式与提示词缓存诊断级别归一、新闻窗口策略、Agent 上下文压缩
档位预设。这里不读 ``.env``、不持有 ``Config`` 状态，只把「原始值 -> 规范值」
的规则集中在一处；``settings.Config`` 初始化时按需组合调用。

``_FALSEY_ENV_VALUES`` / ``PROMPT_CACHE_DIAGNOSTICS_LEVELS`` 等取值域是本模块与
``registry.py`` 的共同事实源，由 ``settings`` 继续对外转发导出。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_FALSEY_ENV_VALUES = {"0", "false", "no", "off"}
PROMPT_CACHE_DIAGNOSTICS_LEVELS = {"off", "basic", "debug"}
TICKFLOW_KLINE_ADJUST_VALUES = {"none", "forward", "backward", "forward_additive", "backward_additive"}
NEWS_STRATEGY_WINDOWS: Dict[str, int] = {
    "ultra_short": 1,
    "short": 3,
    "medium": 7,
    "long": 30,
}

# 归一化 TickFlow 日 K 线复权方式，非法值回退为 none
def normalize_tickflow_kline_adjust(value: Optional[str]) -> str:
    """Normalize TickFlow daily K-line adjustment mode."""
    normalized = (value or "none").strip().lower()
    if normalized in TICKFLOW_KLINE_ADJUST_VALUES:
        return normalized
    logger.warning(
        "Invalid TICKFLOW_KLINE_ADJUST=%r; falling back to none",
        value,
    )
    return "none"


# 解析提示词缓存诊断级别（off/basic/debug），非法回退 off
def parse_prompt_cache_diagnostics_level(value: Optional[str]) -> str:
    """Parse prompt-cache diagnostics level with a conservative fallback."""
    normalized = (value or "off").strip().lower()
    if normalized in PROMPT_CACHE_DIAGNOSTICS_LEVELS:
        return normalized
    logger.warning(
        "Invalid LLM_PROMPT_CACHE_DIAGNOSTICS_LEVEL=%r; falling back to off",
        value,
    )
    return "off"


NEWS_STRATEGY_WINDOWS: Dict[str, int] = {
    "ultra_short": 1,
    "short": 3,
    "medium": 7,
    "long": 30,
}


# Agent 可见聊天历史压缩档位预设（冻结 dataclass，值不可变）
@dataclass(frozen=True)
class AgentContextCompressionPreset:
    """Preset values for visible chat history compression."""

    trigger_tokens: int
    protected_turns: int
    summary_target_tokens: int
    # P1 reserves this budget for future prompt-size controls; it is not
    # enforced by the current rolling-summary state table.
    history_budget_tokens: int


AGENT_CONTEXT_COMPRESSION_DEFAULT_PROFILE = "balanced"
AGENT_CONTEXT_COMPRESSION_PROFILES: Dict[str, AgentContextCompressionPreset] = {
    "cost": AgentContextCompressionPreset(
        trigger_tokens=6000,
        protected_turns=2,
        summary_target_tokens=900,
        history_budget_tokens=4000,
    ),
    "balanced": AgentContextCompressionPreset(
        trigger_tokens=12000,
        protected_turns=4,
        summary_target_tokens=1500,
        history_budget_tokens=8000,
    ),
    "long_context_raw_first": AgentContextCompressionPreset(
        trigger_tokens=24000,
        protected_turns=6,
        summary_target_tokens=2600,
        history_budget_tokens=14000,
    ),
}


# 将环境变量字符串解析为布尔值（支持常见真假写法），空值用默认值
def parse_env_bool(value: Optional[str], default: bool = False) -> bool:
    """Parse common truthy/falsey environment-style values."""
    if value is None:
        return default
    normalized = value.strip().lower()
    if not normalized:
        return default
    return normalized not in _FALSEY_ENV_VALUES


# 将环境变量字符串解析为整数，越界自动裁剪并告警回退
def parse_env_int(
    value: Optional[str],
    default: int,
    *,
    field_name: str,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None,
) -> int:
    """Parse an integer env value with warning + fallback semantics."""
    raw_value = value
    if raw_value is None or not str(raw_value).strip():
        parsed = int(default)
    else:
        try:
            parsed = int(str(raw_value).strip())
        except (TypeError, ValueError):
            logger.warning(
                "%s=%r is not a valid integer; falling back to %s",
                field_name,
                raw_value,
                default,
            )
            parsed = int(default)

    if minimum is not None and parsed < minimum:
        logger.warning(
            "%s=%r is below minimum %s; clamping to %s",
            field_name,
            parsed,
            minimum,
            minimum,
        )
        parsed = minimum
    if maximum is not None and parsed > maximum:
        logger.warning(
            "%s=%r is above maximum %s; clamping to %s",
            field_name,
            parsed,
            maximum,
            maximum,
        )
        parsed = maximum
    return parsed


# 将环境变量字符串解析为浮点数，越界自动裁剪并告警回退
def parse_env_float(
    value: Optional[str],
    default: float,
    *,
    field_name: str,
    minimum: Optional[float] = None,
    maximum: Optional[float] = None,
) -> float:
    """Parse a float env value with warning + fallback semantics."""
    raw_value = value
    if raw_value is None or not str(raw_value).strip():
        parsed = float(default)
    else:
        try:
            parsed = float(str(raw_value).strip())
        except (TypeError, ValueError):
            logger.warning(
                "%s=%r is not a valid number; falling back to %s",
                field_name,
                raw_value,
                default,
            )
            parsed = float(default)

    if minimum is not None and parsed < minimum:
        logger.warning(
            "%s=%r is below minimum %s; clamping to %s",
            field_name,
            parsed,
            minimum,
            minimum,
        )
        parsed = minimum
    if maximum is not None and parsed > maximum:
        logger.warning(
            "%s=%r is above maximum %s; clamping to %s",
            field_name,
            parsed,
            maximum,
            maximum,
        )
        parsed = maximum
    return parsed


# 归一化新闻窗口策略档位（ultra_short/short/medium/long），非法回退 short
def normalize_news_strategy_profile(value: Optional[str]) -> str:
    """Normalize news strategy profile to known values."""
    candidate = (value or "short").strip().lower()
    return candidate if candidate in NEWS_STRATEGY_WINDOWS else "short"


# 综合策略档位与全局最大时效，计算实际生效的新闻窗口天数
def resolve_news_window_days(news_max_age_days: int, news_strategy_profile: Optional[str]) -> int:
    """Resolve effective news window days from profile and global max-age."""
    profile = normalize_news_strategy_profile(news_strategy_profile)
    profile_days = NEWS_STRATEGY_WINDOWS.get(profile, NEWS_STRATEGY_WINDOWS["short"])
    return max(1, min(max(1, int(news_max_age_days)), profile_days))


# 归一化 Agent 上下文压缩档位，非法回退 balanced
def normalize_agent_context_compression_profile(value: Optional[str]) -> str:
    """Normalize visible-chat context compression profile values."""
    candidate = (value or AGENT_CONTEXT_COMPRESSION_DEFAULT_PROFILE).strip().lower()
    if candidate in AGENT_CONTEXT_COMPRESSION_PROFILES:
        return candidate
    logger.warning(
        "Invalid AGENT_CONTEXT_COMPRESSION_PROFILE=%r; falling back to %s",
        value,
        AGENT_CONTEXT_COMPRESSION_DEFAULT_PROFILE,
    )
    return AGENT_CONTEXT_COMPRESSION_DEFAULT_PROFILE


# 取指定压缩档位对应的预设参数（触发阈值/保护轮次等），默认 balanced
def get_agent_context_compression_preset(profile: Optional[str]) -> AgentContextCompressionPreset:
    """Return the preset for a normalized profile, falling back to balanced."""
    normalized = normalize_agent_context_compression_profile(profile)
    return AGENT_CONTEXT_COMPRESSION_PROFILES[normalized]


# 解析压缩相关整数，空/非法/越界时回退到预设默认值
def parse_agent_context_compression_int(
    value: Optional[str],
    default: int,
    *,
    field_name: str,
    minimum: int,
    maximum: int,
) -> int:
    """Parse compression integers; empty/invalid/out-of-range values follow preset defaults."""
    raw_value = value
    if raw_value is None or not str(raw_value).strip():
        return int(default)
    try:
        parsed = int(str(raw_value).strip())
    except (TypeError, ValueError):
        logger.warning(
            "%s=%r is not a valid integer; falling back to preset default %s",
            field_name,
            raw_value,
            default,
        )
        return int(default)
    if parsed < minimum or parsed > maximum:
        logger.warning(
            "%s=%r is outside supported range [%s, %s]; falling back to preset default %s",
            field_name,
            parsed,
            minimum,
            maximum,
            default,
        )
        return int(default)
    return parsed
