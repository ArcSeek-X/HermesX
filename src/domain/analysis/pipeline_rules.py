# -*- coding: utf-8 -*-
"""分析流水线纯规则（analysis 领域，W5.2）。

承接原 ``src/application/analysis/pipeline.py`` 中**无 IO、无 service 状态**的判定与
兜底取值助手：Agent 字段占位判定与建议提取、趋势兜底（评分/标签/信号/决策/止损）、
摘要兜底、股票名占位判定、整数解析、量比与均线状态描述、持久化上下文清洗、日期归一、
符号检索变体。

边界说明：

- 入参一律用 duck typing（``Any``）读取属性/键，不 import application 层的
  ``AnalysisResult`` / ``TrendAnalysisResult``，保持 domain 只向内依赖。
- 只返回新值或新 dict，不改写调用方对象；对象字段回写仍留在 pipeline。
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from src.domain.market.stock_codes import is_bse_code, normalize_stock_code
from src.domain.shared.report_language import (
    get_placeholder_text,
    localize_operation_advice,
    localize_trend_prediction,
)

_AGENT_PLACEHOLDER_TEXTS = {"未知", "待补充", "数据缺失", "无"}
_AGENT_PLACEHOLDER_TEXT_LOWER = {"n/a", "na", "none", "null", "unknown", "tbd"}

_TREND_SIGNAL_DECISION = {
    "strong_buy": "buy",
    "buy": "buy",
    "hold": "hold",
    "wait": "hold",
    "sell": "sell",
    "strong_sell": "sell",
}

_RUNTIME_PROMPT_CONTEXT_KEYS = (
    "market_phase_context",
    "portfolio_context",
    "analysis_context_pack",
    "analysis_context_pack_summary",
    "daily_market_context_summary",
)


def is_agent_placeholder_text(text: str) -> bool:
    """Agent 文本是否为占位符（N/A、未知、数据缺失等）。"""
    if not text:
        return True
    return text.lower() in _AGENT_PLACEHOLDER_TEXT_LOWER or text in _AGENT_PLACEHOLDER_TEXTS


def extract_advice_text_from_dict(raw_advice: dict) -> str:
    """从 Agent 的 position_advice 结构中取第一条非占位建议文本。"""
    for field in ("has_position", "no_position"):
        if isinstance(raw_advice.get(field), str):
            text = raw_advice[field].strip()
            if not is_agent_placeholder_text(text):
                return text

    for value in raw_advice.values():
        if isinstance(value, str):
            text = value.strip()
            if not is_agent_placeholder_text(text):
                return text

    return ""


def is_agent_field_missing(
    value: Any,
    *,
    scalar: bool = False,
    allow_dict: bool = False,
    expect_text: bool = False,
) -> bool:
    """判定 Agent 返回字段是否缺失（区分标量/字典/列表与文本期望）。"""
    if scalar and isinstance(value, dict):
        if not allow_dict or not value:
            return True
        return not extract_advice_text_from_dict(value)
    if value is None:
        return True
    if expect_text and scalar:
        if not isinstance(value, str):
            return True
    if isinstance(value, str):
        text = value.strip()
        return is_agent_placeholder_text(text)
    if isinstance(value, dict):
        if scalar:
            return not allow_dict
        return not value
    if scalar and isinstance(value, (list, tuple, set)):
        return True
    return False


def trend_score_fallback(trend_result: Any) -> Optional[int]:
    """趋势评分兜底：仅在为正整数时采用。"""
    if trend_result is None:
        return None
    try:
        score = int(getattr(trend_result, "signal_score", 0))
    except (TypeError, ValueError):
        return None
    return score if score > 0 else None


def trend_label_fallback(trend_result: Any, report_language: str = "zh") -> str:
    """趋势结论兜底：英文需要本地化，其它语言直取枚举值/文本。"""
    if trend_result is None:
        return ""
    trend_status = getattr(trend_result, "trend_status", None)
    value = getattr(trend_status, "value", None) or str(trend_status or "").strip()
    if report_language != "en":
        return value
    return localize_trend_prediction(value, report_language)


def trend_signal_fallback(trend_result: Any, report_language: str = "zh") -> str:
    """买卖信号兜底：统一走操作建议本地化。"""
    if trend_result is None:
        return ""
    buy_signal = getattr(trend_result, "buy_signal", None)
    value = getattr(buy_signal, "value", None) or str(buy_signal or "").strip()
    return localize_operation_advice(value, report_language)


def trend_decision_fallback(trend_result: Any) -> Optional[str]:
    """把趋势买卖信号枚举映射为决策类型（buy/hold/sell）。"""
    if trend_result is None:
        return None
    signal_name = getattr(getattr(trend_result, "buy_signal", None), "name", "")
    return _TREND_SIGNAL_DECISION.get(str(signal_name or "").lower())


def stop_loss_fallback_from_trend(trend_result: Any, report_language: str) -> Any:
    """止损兜底：优先取首个支撑位，缺数据时返回本地化占位文案。"""
    levels = getattr(trend_result, "support_levels", None) if trend_result else None
    if levels:
        return levels[0]
    return get_placeholder_text(report_language)


def summary_fallback_from_result(result: Any, report_language: str) -> str:
    """由趋势结论与操作建议拼装摘要兜底；两者缺一返回空串。"""
    trend = (getattr(result, "trend_prediction", "") or "").strip()
    advice = (getattr(result, "operation_advice", "") or "").strip()
    if trend and advice:
        if report_language == "en":
            return f"Trend view: {trend}; action advice: {advice}."
        if report_language == "ko":
            return f"추세 결론: {trend}; 대응 전략: {advice}."
        return f"趋势结论：{trend}；操作建议：{advice}。"
    return ""


def is_placeholder_stock_name(name: str, code: str) -> bool:
    """股票名是否缺失或形如占位（空、等于代码、以「股票」开头、含 Unknown）。"""
    if not name:
        return True
    normalized = str(name).strip()
    if not normalized:
        return True
    if normalized == code:
        return True
    if normalized.startswith("股票"):
        return True
    if "Unknown" in normalized:
        return True
    return False


def safe_int(value: Any, default: int = 50) -> int:
    """安全转 int：字符串取首个整数片段，失败返回默认值。"""
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+", value)
        if match:
            return int(match.group())
    return default


def describe_volume_ratio(volume_ratio: float) -> str:
    """量比描述（量比 = 当前成交量 / 过去 5 日平均成交量）。"""
    if volume_ratio < 0.5:
        return "极度萎缩"
    elif volume_ratio < 0.8:
        return "明显萎缩"
    elif volume_ratio < 1.2:
        return "正常"
    elif volume_ratio < 2.0:
        return "温和放量"
    elif volume_ratio < 3.0:
        return "明显放量"
    else:
        return "巨量"


def compute_ma_status(close: float, ma5: float, ma10: float, ma20: float) -> str:
    """由价格与均线值判定均线排列状态（口径与 storage._analyze_ma_status 一致）。"""
    close = close or 0
    ma5 = ma5 or 0
    ma10 = ma10 or 0
    ma20 = ma20 or 0
    if close > ma5 > ma10 > ma20 > 0:
        return "多头排列 📈"
    elif close < ma5 < ma10 < ma20 and ma20 > 0:
        return "空头排列 📉"
    elif close > ma5 and ma5 > ma10:
        return "短期向好 🔼"
    elif close < ma5 and ma5 < ma10:
        return "短期走弱 🔽"
    else:
        return "震荡整理 ↔️"


def without_runtime_prompt_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """返回浅拷贝并剔除仅用于 Prompt 的运行时上下文（公开概览单独渲染）。"""
    sanitized = dict(context)
    for key in _RUNTIME_PROMPT_CONTEXT_KEYS:
        sanitized.pop(key, None)
    enhanced_context = sanitized.get("enhanced_context")
    if isinstance(enhanced_context, dict):
        enhanced_context = dict(enhanced_context)
        enhanced_context.pop("daily_market_context_summary", None)
        sanitized["enhanced_context"] = enhanced_context
    return sanitized


def safe_to_dict(value: Any) -> Optional[Dict[str, Any]]:
    """尽力把对象转成 dict；无 ``to_dict`` / ``__dict__`` 或失败返回 None。"""
    if value is None:
        return None
    if hasattr(value, "to_dict"):
        try:
            return value.to_dict()
        except Exception:
            return None
    if hasattr(value, "__dict__"):
        try:
            return dict(value.__dict__)
        except Exception:
            return None
    return None


def coerce_daily_market_context_date(value: Any) -> Optional[date]:
    """把 datetime/date/ISO 字符串归一为 date；其它类型返回 None。"""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def symbol_scope_lookup_values(code: str, market: str) -> List[str]:
    """返回持久化智能上下文检索可接受的代码拼写变体（含港股/沪深北交易所形式）。"""
    raw = str(code or "").strip()
    normalized = normalize_stock_code(raw) if raw else ""
    values: List[str] = []
    seen: set = set()

    def add(value: str) -> None:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            values.append(text)

    def add_case_variants(value: str) -> None:
        text = str(value or "").strip()
        if not text:
            return
        add(text)
        add(text.upper())
        add(text.lower())

    add_case_variants(normalized)
    add_case_variants(raw)

    normalized_upper = normalized.upper()
    if normalized_upper.startswith("HK") and normalized_upper[2:].isdigit():
        digits = normalized_upper[2:]
        trimmed_digits = digits.lstrip("0") or digits
        add_case_variants(normalized_upper)
        add_case_variants(digits)
        add_case_variants(trimmed_digits)
        add_case_variants(f"HK{trimmed_digits}")
        add_case_variants(f"{trimmed_digits}.HK")
        add_case_variants(f"{digits}.HK")
        return values

    if (market or "").strip().lower() != "cn":
        return values
    if not (normalized.isdigit() and len(normalized) == 6):
        return values

    raw_upper = raw.upper()
    exchange = ""
    if raw_upper.startswith(("SH", "SS")) or raw_upper.endswith((".SH", ".SS")):
        exchange = "SH"
    elif raw_upper.startswith("SZ") or raw_upper.endswith(".SZ"):
        exchange = "SZ"
    elif raw_upper.startswith("BJ") or raw_upper.endswith(".BJ"):
        exchange = "BJ"
    elif is_bse_code(normalized):
        exchange = "BJ"
    elif normalized.startswith(("5", "6", "9")):
        exchange = "SH"
    else:
        exchange = "SZ"

    add_case_variants(f"{exchange}{normalized}")
    add_case_variants(f"{exchange}.{normalized}")
    add_case_variants(f"{normalized}.{exchange}")
    if exchange == "SH":
        add_case_variants(f"SS.{normalized}")
        add_case_variants(f"{normalized}.SS")
    return values
