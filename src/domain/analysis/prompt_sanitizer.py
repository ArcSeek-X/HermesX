# -*- coding: utf-8 -*-
"""Prompt 侧趋势清洗纯规则（analysis 领域，W5.1）。

承接原 ``src/application/analysis/analyzer.py`` 中的趋势方向推断与「送进 Prompt 前
的一致性清洗」：识别多头/空头结构、剔除与主判断直接冲突的理由、对大倍量信号降权。

边界说明：

- 只在**派生的副本**上做清洗，返回新 dict；不改写运行时 trend 对象，也不触达
  provider / config / infra。
- 否定词判定（「未形成上升趋势」「不是空头而是多头排列」）属纯文本规则，一并下沉，
  便于独立回归。
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

from src.domain.analysis.chip_rules import safe_float

BULLISH_TREND_HINTS: Tuple[str, ...] = (
    "多头排列",
    "持续上涨",
    "趋势向上",
    "上升趋势",
    "向上发散",
    "bullish",
    "uptrend",
)
WEAK_BULLISH_TREND_HINTS: Tuple[str, ...] = ("弱势多头",)
BEARISH_TREND_HINTS: Tuple[str, ...] = (
    "空头排列",
    "持续下跌",
    "趋势向下",
    "下降趋势",
    "向下发散",
    "bearish",
    "downtrend",
)
WEAK_BEARISH_TREND_HINTS: Tuple[str, ...] = ("弱势空头",)
NEGATION_TOKENS: Tuple[str, ...] = (
    "不是",
    "并非",
    "并未",
    "没有",
    "尚不",
    "尚未",
    "未",
    "无",
    "不属",
    "非",
    "not ",
    "no ",
)
NEGATION_BREAK_CHARS: Tuple[str, ...] = (",", ".", ";", ":", "!", "?", "，", "。", "；", "：", "！", "？", "\n")
NEGATION_LOOKBACK_CHARS = 16
NEGATION_MAX_GAP_CHARS = 8
NEGATION_SCOPE_BREAK_TOKENS: Tuple[str, ...] = (
    "而是",
    "但是",
    "但",
    "反而",
    "反倒",
    "转为",
    "转成",
    "改为",
    "改成",
    " but ",
    " instead ",
    " rather ",
)
SINGLE_CHAR_NEGATION_GAP_PREFIXES: Tuple[str, ...] = (
    "形成",
    "出现",
    "进入",
    "转为",
    "转成",
    "构成",
    "呈现",
    "显示",
    "属于",
    "是",
    "有",
    "能",
    "见",
    "站",
    "守",
    "破",
)


def normalize_prompt_reason_items(items: Any) -> List[str]:
    """把 prompt reason/risk 项归一为非空字符串列表；非 list 直接返回空列表。"""
    if not isinstance(items, list):
        return []
    normalized: List[str] = []
    for item in items:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def contains_trend_hint(text: str, hints: Tuple[str, ...]) -> bool:
    """文本是否包含**未被否定**的强趋势提示词。"""
    lowered = text.strip().lower()

    def _has_negation_scope_break(gap: str) -> bool:
        normalized_gap = gap.lower()
        for token in NEGATION_SCOPE_BREAK_TOKENS:
            token_index = normalized_gap.find(token)
            if token_index > 0:
                return True
        return False

    def _is_valid_negation_gap(token: str, gap: str) -> bool:
        if not gap:
            return True
        if token not in {"未", "无", "非"}:
            return True
        return any(gap.startswith(prefix) for prefix in SINGLE_CHAR_NEGATION_GAP_PREFIXES)

    def _is_negated_match(index: int) -> bool:
        prefix = lowered[max(0, index - NEGATION_LOOKBACK_CHARS):index]
        for token in NEGATION_TOKENS:
            token_index = prefix.rfind(token)
            if token_index < 0:
                continue
            gap = prefix[token_index + len(token):]
            if any(char in gap for char in NEGATION_BREAK_CHARS):
                continue
            stripped_gap = gap.strip()
            if len(stripped_gap) > NEGATION_MAX_GAP_CHARS:
                continue
            if _has_negation_scope_break(stripped_gap):
                continue
            if not _is_valid_negation_gap(token, stripped_gap):
                continue
            return True
        return False

    for hint in hints:
        keyword = hint.lower()
        start = 0
        while True:
            index = lowered.find(keyword, start)
            if index < 0:
                break
            if not _is_negated_match(index):
                return True
            start = index + len(keyword)
    return False


def infer_trend_direction(trend: Dict[str, Any]) -> str:
    """由 trend_status 与 ma_alignment 推断最终趋势方向（bullish/bearish/neutral）。"""
    combined = " ".join(
        str(trend.get(key, "")).strip()
        for key in ("trend_status", "ma_alignment")
        if str(trend.get(key, "")).strip()
    )
    if not combined:
        return "neutral"
    lowered = combined.lower()
    normalized = lowered.replace(" ", "")
    has_bullish = (
        contains_trend_hint(combined, BULLISH_TREND_HINTS + WEAK_BULLISH_TREND_HINTS)
        or "ma5>ma10>ma20" in normalized
        or (
            "ma5>ma10" in normalized
            and any(pattern in normalized for pattern in ("ma10≤ma20", "ma10<=ma20"))
        )
    )
    has_bearish = (
        contains_trend_hint(combined, BEARISH_TREND_HINTS + WEAK_BEARISH_TREND_HINTS)
        or "ma5<ma10<ma20" in normalized
        or (
            "ma5<ma10" in normalized
            and any(pattern in normalized for pattern in ("ma10≥ma20", "ma10>=ma20"))
        )
    )
    if has_bullish and not has_bearish:
        return "bullish"
    if has_bearish and not has_bullish:
        return "bearish"
    return "neutral"


def filter_conflicting_trend_items(items: List[str], conflict_hints: Tuple[str, ...]) -> List[str]:
    """剔除与最终趋势方向直接冲突的理由项。"""
    return [item for item in items if not contains_trend_hint(item, conflict_hints)]


def sanitize_trend_analysis_for_prompt(
    trend: Any,
    *,
    volume_change_ratio: Any = None,
) -> Dict[str, Any]:
    """在派生副本上清洗仅用于 Prompt 的趋势提示，不改动运行时/provider 配置。"""
    trend_dict = dict(trend) if isinstance(trend, dict) else {}
    signal_reasons = normalize_prompt_reason_items(trend_dict.get("signal_reasons"))
    risk_factors = normalize_prompt_reason_items(trend_dict.get("risk_factors"))
    prompt_notes: List[str] = []
    trend_direction = infer_trend_direction(trend_dict)

    if trend_direction == "bearish":
        filtered_signal_reasons = filter_conflicting_trend_items(
            signal_reasons,
            BULLISH_TREND_HINTS + WEAK_BULLISH_TREND_HINTS,
        )
        if len(filtered_signal_reasons) != len(signal_reasons):
            prompt_notes.append("当前技术结构偏空，已剔除与空头主判断直接冲突的看多结构理由。")
        signal_reasons = filtered_signal_reasons
        prompt_notes.append(
            "若新闻、业绩或政策催化偏多，只能表述为“事件先行、技术待确认”或“基本面偏多，但技术面尚未确认”，严禁写成确定性买点。"
        )
    elif trend_direction == "bullish":
        filtered_signal_reasons = filter_conflicting_trend_items(
            signal_reasons,
            BEARISH_TREND_HINTS + WEAK_BEARISH_TREND_HINTS,
        )
        if len(filtered_signal_reasons) != len(signal_reasons):
            prompt_notes.append("当前技术结构偏多，已剔除与多头主判断直接冲突的空头结构理由。")
        signal_reasons = filtered_signal_reasons
        filtered_risk_factors = filter_conflicting_trend_items(
            risk_factors,
            BEARISH_TREND_HINTS + WEAK_BEARISH_TREND_HINTS,
        )
        if len(filtered_risk_factors) != len(risk_factors):
            prompt_notes.append("当前技术结构偏多，已剔除与多头主判断直接冲突的空头结构风险表述。")
        risk_factors = filtered_risk_factors

    parsed_volume_change = safe_float(volume_change_ratio, default=math.nan)
    if math.isfinite(parsed_volume_change) and parsed_volume_change > 10:
        prompt_notes.append(
            f"成交量较昨日变化约 {parsed_volume_change:.2f} 倍，可能存在异常数据或一次性冲量；量能信号必须降权解读，不能机械视为强确认。"
        )

    trend_dict["signal_reasons"] = signal_reasons
    trend_dict["risk_factors"] = risk_factors
    trend_dict["prompt_consistency_notes"] = prompt_notes
    trend_dict["prompt_trend_direction"] = trend_direction
    return trend_dict
