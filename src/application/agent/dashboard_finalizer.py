"""Build an Agent dashboard from opinions without executing agents or accessing runtime state."""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from src.application.agent.dashboard_payload import sanitize_agent_dashboard_payload
from src.application.agent.protocols import AgentContext, normalize_decision_signal
from src.application.agent.risk_override import RiskOverrideApplication
from typing import Any, Dict

logger = logging.getLogger("src.application.agent.orchestrator")


def finalize_dashboard_payload(payload: Optional[Dict[str, Any]], ctx: AgentContext) -> Optional[Dict[str, Any]]:
    """Derive the downstream dashboard shape from the post-risk signal."""
    payload = sanitize_agent_dashboard_payload(dict(payload or {}))
    meaningful_data_keys = (
        "realtime_quote",
        "daily_history",
        "chip_distribution",
        "trend_result",
        "news_context",
        "intel_opinion",
        "fundamental_context",
    )
    has_meaningful_context = any((ctx.get_data(key) is not None for key in meaningful_data_keys))
    if not payload and (not ctx.opinions) and (not has_meaningful_context):
        return None
    base_opinion = select_base_opinion(ctx)
    application = ctx.meta.get("risk_override_application")
    risk_applied = isinstance(application, RiskOverrideApplication) and application.applied
    decision_type = (
        application.post_risk_signal.value
        if risk_applied
        else normalize_decision_signal(
            payload.get("decision_type") or (base_opinion.signal if base_opinion else "hold")
        )
    )
    confidence = float(base_opinion.confidence if base_opinion is not None else 0.5)
    sentiment_score = payload.get("sentiment_score")
    try:
        sentiment_score = int(sentiment_score)
    except (TypeError, ValueError):
        sentiment_score = _estimate_sentiment_score(decision_type, confidence)
    if risk_applied:
        sentiment_score = _adjust_sentiment_score(sentiment_score, decision_type)
    dashboard_block = payload.get("dashboard")
    if not isinstance(dashboard_block, dict):
        dashboard_block = {}
    else:
        dashboard_block = dict(dashboard_block)
        dashboard_block.pop("strategy_synthesis", None)
    core = dashboard_block.get("core_conclusion")
    if not isinstance(core, dict):
        core = {}
    else:
        core = dict(core)
    intelligence = dashboard_block.get("intelligence")
    if not isinstance(intelligence, dict):
        intelligence = {}
    else:
        intelligence = dict(intelligence)
    battle = dashboard_block.get("battle_plan")
    if not isinstance(battle, dict):
        battle = {}
    else:
        battle = dict(battle)
    analysis_summary = _first_non_empty_text(
        payload.get("analysis_summary"), core.get("one_sentence"), getattr(base_opinion, "reasoning", "")
    )
    if not analysis_summary:
        analysis_summary = f"多 Agent 未生成完整仪表盘，当前按{_signal_to_operation(decision_type)}处理。"
    if risk_applied:
        transition_prefix = f"[风控下调: {application.from_signal.value} -> {application.post_risk_signal.value}]"
        if not analysis_summary.startswith(transition_prefix):
            analysis_summary = f"{transition_prefix} {analysis_summary}"
    analysis_summary = _truncate_text(analysis_summary, 220)
    trend_prediction = _first_non_empty_text(
        payload.get("trend_prediction"),
        (getattr(base_opinion, "raw_data", {}) or {}).get("trend_summary") if base_opinion is not None else "",
    )
    if not trend_prediction:
        technical = latest_opinion(ctx, {"technical"})
        tech_raw = technical.raw_data if technical and isinstance(technical.raw_data, dict) else {}
        ma_alignment = tech_raw.get("ma_alignment")
        trend_score = tech_raw.get("trend_score")
        if ma_alignment or trend_score is not None:
            trend_prediction = (
                f"技术面{ma_alignment or 'neutral'}，趋势评分 {(trend_score if trend_score is not None else 'N/A')}"
            )
        else:
            trend_prediction = "待结合更多阶段结果确认"
    operation_advice_raw = payload.get("operation_advice")
    if risk_applied:
        pre_risk_advice = _normalize_operation_advice_value(operation_advice_raw, application.from_signal.value)
        operation_advice = _adjust_operation_advice(pre_risk_advice, decision_type)
    else:
        operation_advice = _normalize_operation_advice_value(operation_advice_raw, decision_type)
    existing_position = core.get("position_advice")
    if risk_applied:
        position_advice = _post_risk_position_advice(decision_type)
    else:
        position_advice = dict(existing_position) if isinstance(existing_position, dict) else {}
        if isinstance(operation_advice_raw, dict):
            no_position = _first_non_empty_text(
                operation_advice_raw.get("no_position"), operation_advice_raw.get("empty_position")
            )
            has_position = _first_non_empty_text(
                operation_advice_raw.get("has_position"), operation_advice_raw.get("holding_position")
            )
            if no_position and "no_position" not in position_advice:
                position_advice["no_position"] = no_position
            if has_position and "has_position" not in position_advice:
                position_advice["has_position"] = has_position
        defaults = _default_position_advice(decision_type)
        position_advice.setdefault("no_position", defaults["no_position"])
        position_advice.setdefault("has_position", defaults["has_position"])
    key_levels = collect_key_levels(ctx, payload, dashboard_block)
    sniper = battle.get("sniper_points")
    if not isinstance(sniper, dict):
        sniper = {}
    else:
        sniper = dict(sniper)
    ideal_buy = _pick_first_level(
        sniper.get("ideal_buy"),
        key_levels.get("ideal_buy_if_valuation_improves"),
        key_levels.get("ideal_buy"),
        key_levels.get("support"),
        key_levels.get("immediate_support"),
    )
    sniper["ideal_buy"] = ideal_buy if ideal_buy is not None else "N/A"
    secondary_buy = _coerce_level_value(sniper.get("secondary_buy"))
    if secondary_buy is None:
        secondary_buy = _pick_first_level(
            key_levels.get("secondary_buy"), key_levels.get("support"), key_levels.get("immediate_support")
        )
    if _level_values_equal(secondary_buy, sniper.get("ideal_buy")):
        secondary_buy = None
    sniper["secondary_buy"] = secondary_buy if secondary_buy is not None else "N/A"
    sniper.setdefault(
        "stop_loss", key_levels.get("stop_loss") or key_levels.get("strong_support_stop_loss") or "待补充"
    )
    sniper.setdefault(
        "take_profit",
        key_levels.get("take_profit")
        or key_levels.get("next_breakout_target")
        or key_levels.get("current_resistance")
        or key_levels.get("resistance")
        or "N/A",
    )
    risk_alerts = collect_risk_alerts(ctx, intelligence)
    positive_catalysts = collect_positive_catalysts(ctx, intelligence)
    latest_news = _extract_latest_news_title(intelligence)
    if not intelligence.get("risk_alerts"):
        intelligence["risk_alerts"] = risk_alerts
    if positive_catalysts and (not intelligence.get("positive_catalysts")):
        intelligence["positive_catalysts"] = positive_catalysts
    if latest_news and (not intelligence.get("latest_news")):
        intelligence["latest_news"] = latest_news
    one_sentence = _first_non_empty_text(core.get("one_sentence"), analysis_summary)
    if risk_applied and (not one_sentence.startswith(transition_prefix)):
        one_sentence = f"{transition_prefix} {one_sentence}"
    core["one_sentence"] = _truncate_text(one_sentence, 60)
    if not core.get("time_sensitivity"):
        core["time_sensitivity"] = "本周内"
    if risk_applied or not core.get("signal_type"):
        core["signal_type"] = _signal_to_signal_type(decision_type)
    core["position_advice"] = position_advice
    battle["sniper_points"] = sniper
    if "action_checklist" not in battle:
        battle["action_checklist"] = []
    position_strategy = battle.get("position_strategy")
    if risk_applied:
        position_strategy = dict(position_strategy) if isinstance(position_strategy, dict) else {}
        position_strategy["suggested_position"] = _default_position_size(decision_type)
        position_strategy["entry_plan"] = position_advice["no_position"]
        position_strategy.setdefault("risk_control", f"止损参考：{sniper.get('stop_loss', '待补充')}")
        battle["position_strategy"] = position_strategy
    elif not isinstance(position_strategy, dict) or not position_strategy:
        battle["position_strategy"] = {
            "suggested_position": _default_position_size(decision_type),
            "entry_plan": position_advice["no_position"],
            "risk_control": f"止损参考 {sniper.get('stop_loss', '待补充')}",
        }
    data_perspective = dashboard_block.get("data_perspective")
    if not isinstance(data_perspective, dict):
        data_perspective = {}
    if not data_perspective:
        built_data_perspective = build_data_perspective(ctx, key_levels)
        if built_data_perspective:
            data_perspective = built_data_perspective
    if data_perspective:
        dashboard_block["data_perspective"] = data_perspective
    strategy_synthesis = collect_strategy_synthesis(ctx, dashboard_block)
    if strategy_synthesis:
        dashboard_block["strategy_synthesis"] = strategy_synthesis
    dashboard_block["core_conclusion"] = core
    dashboard_block["intelligence"] = intelligence
    dashboard_block["battle_plan"] = battle
    key_points = payload.get("key_points")
    if not isinstance(key_points, list) or not key_points:
        key_points = [
            _truncate_text(op.reasoning, 120)
            for op in ctx.opinions
            if isinstance(op.reasoning, str) and op.reasoning.strip()
        ][:5]
    risk_warning = _first_non_empty_text(
        payload.get("risk_warning"), "；".join(risk_alerts[:3]), getattr(latest_opinion(ctx, {"risk"}), "reasoning", "")
    )
    if not risk_warning:
        risk_warning = "暂无额外风险提示"
    if risk_applied:
        risk_opinion = latest_opinion(ctx, {"risk"})
        risk_raw = risk_opinion.raw_data if risk_opinion and isinstance(risk_opinion.raw_data, dict) else {}
        risk_warning = merge_risk_warning(risk_warning, risk_raw, ctx.risk_flags, decision_type)
    payload["stock_name"] = _first_non_empty_text(payload.get("stock_name"), ctx.stock_name, ctx.stock_code)
    payload["sentiment_score"] = sentiment_score
    payload["trend_prediction"] = trend_prediction
    payload["operation_advice"] = operation_advice
    payload["decision_type"] = decision_type
    payload["confidence_level"] = _confidence_label(confidence)
    payload["analysis_summary"] = analysis_summary
    payload["key_points"] = key_points
    payload["risk_warning"] = risk_warning
    payload["dashboard"] = dashboard_block
    if risk_applied:
        for opinion in reversed(ctx.opinions):
            if opinion.agent_name == "decision":
                opinion.signal = decision_type
                opinion.reasoning = analysis_summary
                opinion.raw_data = payload
                break
    return payload


def collect_strategy_synthesis(ctx: AgentContext, dashboard_block: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    consensus_data = ctx.get_data("skill_consensus")
    if isinstance(consensus_data, dict):
        synthesis = consensus_data.get("strategy_synthesis")
        if isinstance(synthesis, dict) and synthesis:
            return synthesis
        raw_data = consensus_data.get("raw_data")
        if isinstance(raw_data, dict):
            synthesis = raw_data.get("strategy_synthesis")
            if isinstance(synthesis, dict) and synthesis:
                return synthesis
    for opinion in reversed(ctx.opinions):
        if getattr(opinion, "agent_name", "") != "skill_consensus":
            continue
        raw_data = opinion.raw_data if isinstance(opinion.raw_data, dict) else {}
        synthesis = raw_data.get("strategy_synthesis")
        if isinstance(synthesis, dict) and synthesis:
            return synthesis
    return None


def collect_key_levels(ctx: AgentContext, payload: Dict[str, Any], dashboard_block: Dict[str, Any]) -> Dict[str, Any]:
    """Collect key price levels from dashboard payloads and agent opinions."""
    levels: Dict[str, Any] = {}

    def absorb(source: Any) -> None:
        if not isinstance(source, dict):
            return
        for key, value in source.items():
            normalized = _coerce_level_value(value)
            if normalized is not None and key not in levels:
                levels[key] = normalized

    absorb(payload.get("key_levels"))
    absorb(dashboard_block.get("key_levels"))
    for opinion in reversed(ctx.opinions):
        absorb(getattr(opinion, "key_levels", {}))
        raw = opinion.raw_data if isinstance(opinion.raw_data, dict) else {}
        absorb(raw.get("key_levels"))
    return levels


def build_data_perspective(ctx: AgentContext, key_levels: Dict[str, Any]) -> Dict[str, Any]:
    """Build a lightweight data_perspective block from cached market data."""
    realtime = ctx.get_data("realtime_quote")
    chip = ctx.get_data("chip_distribution")
    trend = ctx.get_data("trend_result")
    technical = latest_opinion(ctx, {"technical"})
    tech_raw = technical.raw_data if technical and isinstance(technical.raw_data, dict) else {}
    trend_dict = trend if isinstance(trend, dict) else {}
    data_perspective: Dict[str, Any] = {}
    ma_alignment = tech_raw.get("ma_alignment")
    trend_score = tech_raw.get("trend_score")
    if ma_alignment or trend_score is not None:
        data_perspective["trend_status"] = {
            "ma_alignment": ma_alignment or "N/A",
            "trend_score": trend_score if trend_score is not None else "N/A",
            "is_bullish": str(ma_alignment).lower() == "bullish",
        }

    def _bias_label(bias):
        if not isinstance(bias, (int, float)):
            return ""
        if bias > 5:
            return "超买"
        elif bias > 2:
            return "偏高"
        elif bias < -5:
            return "超卖"
        elif bias < -2:
            return "偏低"
        return "中性"

    def _r(val, n=2):
        """Round numeric values for display."""
        return round(val, n) if isinstance(val, (int, float)) else val

    def _pick(primary_dict, primary_key, fallback_dict, fallback_key, default="N/A"):
        """Pick first non-None value, avoiding falsy-zero trap."""
        v = primary_dict.get(primary_key)
        if v is not None:
            return v
        v2 = fallback_dict.get(fallback_key, default)
        return v2 if v2 is not None else default

    if isinstance(realtime, dict) or trend_dict:
        data_perspective["price_position"] = {
            "current_price": _r(_pick(trend_dict, "current_price", realtime or {}, "price")),
            "ma5": _r(_pick(trend_dict, "ma5", tech_raw, "ma5")),
            "ma10": _r(_pick(trend_dict, "ma10", tech_raw, "ma10")),
            "ma20": _r(_pick(trend_dict, "ma20", tech_raw, "ma20")),
            "bias_ma5": _r(_pick(trend_dict, "bias_ma5", tech_raw, "bias_ma5")),
            "bias_status": _bias_label(trend_dict.get("bias_ma5")) or tech_raw.get("bias_status", "N/A"),
            "support_level": key_levels.get("support") or key_levels.get("immediate_support") or "N/A",
            "resistance_level": key_levels.get("resistance") or key_levels.get("current_resistance") or "N/A",
        }
        data_perspective["volume_analysis"] = {
            "volume_ratio": (realtime or {}).get("volume_ratio", "N/A"),
            "turnover_rate": (realtime or {}).get("turnover_rate", "N/A"),
            "volume_status": trend_dict.get("volume_status") or tech_raw.get("volume_status", "N/A"),
            "volume_meaning": tech_raw.get("reasoning", "") if tech_raw else "",
        }
    if isinstance(chip, dict):
        concentration = chip.get("concentration_90")
        if concentration is None:
            concentration = chip.get("concentration")
        data_perspective["chip_structure"] = {
            "profit_ratio": chip.get("profit_ratio", "N/A"),
            "avg_cost": chip.get("avg_cost", "N/A"),
            "concentration": concentration if concentration is not None else "N/A",
            "chip_health": chip.get("chip_health", "一般"),
        }
    return data_perspective


def collect_risk_alerts(ctx: AgentContext, intelligence: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []

    def absorb(values: Any) -> None:
        if not isinstance(values, list):
            return
        for item in values:
            text = ""
            if isinstance(item, str):
                text = item.strip()
            elif isinstance(item, dict):
                text = str(item.get("description") or item.get("title") or "").strip()
            if text and text not in alerts:
                alerts.append(text)

    absorb(intelligence.get("risk_alerts"))
    intel = latest_opinion(ctx, {"intel"})
    intel_raw = intel.raw_data if intel and isinstance(intel.raw_data, dict) else {}
    absorb(intel_raw.get("risk_alerts"))
    risk = latest_opinion(ctx, {"risk"})
    risk_raw = risk.raw_data if risk and isinstance(risk.raw_data, dict) else {}
    absorb(risk_raw.get("flags"))
    for flag in ctx.risk_flags:
        description = str(flag.get("description", "")).strip()
        if description and description not in alerts:
            alerts.append(description)
    return alerts[:8]


def collect_positive_catalysts(ctx: AgentContext, intelligence: Dict[str, Any]) -> List[str]:
    catalysts: List[str] = []

    def absorb(values: Any) -> None:
        if not isinstance(values, list):
            return
        for item in values:
            text = str(item).strip()
            if text and text not in catalysts:
                catalysts.append(text)

    absorb(intelligence.get("positive_catalysts"))
    intel = latest_opinion(ctx, {"intel"})
    intel_raw = intel.raw_data if intel and isinstance(intel.raw_data, dict) else {}
    absorb(intel_raw.get("positive_catalysts"))
    return catalysts[:8]


def latest_opinion(ctx: AgentContext, names: set[str]) -> Optional[Any]:
    for opinion in reversed(ctx.opinions):
        if opinion.agent_name in names:
            return opinion
    return None


def select_base_opinion(ctx: AgentContext) -> Optional[Any]:
    preferred_groups = ({"decision"}, {"skill_consensus", "strategy_consensus"}, {"technical"}, {"intel"}, {"risk"})
    for names in preferred_groups:
        opinion = latest_opinion(ctx, names)
        if opinion is not None:
            return opinion
    if ctx.opinions:
        return ctx.opinions[-1]
    return None


def merge_risk_warning(
    existing_warning: Any, risk_raw: Dict[str, Any], risk_flags: List[Dict[str, Any]], signal: str
) -> str:
    """Build a concise risk warning after a forced downgrade."""
    warnings: List[str] = []
    if isinstance(existing_warning, str) and existing_warning.strip():
        warnings.append(existing_warning.strip())
    if isinstance(risk_raw.get("reasoning"), str) and risk_raw["reasoning"].strip():
        warnings.append(risk_raw["reasoning"].strip())
    for flag in risk_flags[:3]:
        description = str(flag.get("description", "")).strip()
        severity = str(flag.get("severity", "")).lower()
        if description:
            warnings.append(f"[{severity or 'risk'}] {description}")
    prefix = f"风控接管：最终信号已下调为 {signal}。"
    merged = " ".join(dict.fromkeys([prefix] + warnings))
    return merged[:500]


def _adjust_sentiment_score(score: int, signal: str) -> int:
    """Clamp sentiment score into the target band for the overridden signal."""
    bands = {
        "buy": (60, 79),
        "hold": (40, 59),
        "sell": (0, 39),
    }
    low, high = bands.get(signal, (0, 100))
    return max(low, min(high, score))


def _adjust_operation_advice(advice: str, signal: str) -> str:
    """Normalize action wording to the overridden decision signal."""
    mapping = {
        "buy": "买入",
        "hold": "观望",
        "sell": "减仓/卖出",
    }
    if signal not in mapping:
        return advice
    if advice == mapping[signal]:
        return advice
    return f"{mapping[signal]}（原建议已被风控下调）"


def _signal_to_operation(signal: str) -> str:
    mapping = {
        "buy": "买入",
        "hold": "观望",
        "sell": "减仓/卖出",
    }
    return mapping.get(signal, "观望")


def _signal_to_signal_type(signal: str) -> str:
    mapping = {
        "buy": "🟢买入信号",
        "hold": "🟡持有观望",
        "sell": "🔴卖出信号",
    }
    return mapping.get(signal, "⚠️风险警告")


def _default_position_advice(signal: str) -> Dict[str, str]:
    mapping = {
        "buy": {
            "no_position": "可结合支撑位分批试仓，避免一次性追高。",
            "has_position": "可继续持有，回踩关键位不破再考虑加仓。",
        },
        "hold": {
            "no_position": "暂不追高，等待更清晰的入场条件。",
            "has_position": "以观察为主，跌破止损位再执行风控。",
        },
        "sell": {
            "no_position": "暂不参与，等待风险充分释放。",
            "has_position": "优先控制回撤，按计划减仓或离场。",
        },
    }
    return mapping.get(signal, mapping["hold"])


def _post_risk_position_advice(signal: str) -> Dict[str, str]:
    """Return authoritative position advice after an applied risk transition."""
    mapping = {
        "hold": {
            "no_position": "风险未解除前先观望，等待更清晰的入场条件。",
            "has_position": "谨慎持有并收紧止损，待风险缓解后再考虑加仓。",
        },
        "sell": {
            "no_position": "风险明显偏高，暂不新开仓。",
            "has_position": "优先控制回撤，建议减仓或退出高风险仓位。",
        },
    }
    return dict(mapping.get(signal, _default_position_advice(signal)))


def _default_position_size(signal: str) -> str:
    mapping = {
        "buy": "轻仓试仓",
        "hold": "控制仓位",
        "sell": "降仓防守",
    }
    return mapping.get(signal, "控制仓位")


def _normalize_operation_advice_value(value: Any, signal: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return _signal_to_operation(signal)


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.75:
        return "高"
    if confidence >= 0.45:
        return "中"
    return "低"


def _estimate_sentiment_score(signal: str, confidence: float) -> int:
    confidence = max(0.0, min(1.0, float(confidence)))
    bands = {
        "buy": (65, 79),
        "hold": (45, 59),
        "sell": (20, 39),
    }
    low, high = bands.get(signal, (45, 59))
    return int(round(low + (high - low) * confidence))


def _coerce_level_value(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    text = str(value).replace(",", "").replace("，", "").strip()
    if not text or text.upper() == "N/A" or text in {"-", "—"}:
        return None
    try:
        return round(float(text), 2)
    except ValueError:
        return text


def _pick_first_level(*values: Any) -> Any:
    for value in values:
        normalized = _coerce_level_value(value)
        if normalized is not None:
            return normalized
    return None


def _level_values_equal(left: Any, right: Any) -> bool:
    left_normalized = _coerce_level_value(left)
    right_normalized = _coerce_level_value(right)
    return left_normalized is not None and right_normalized is not None and left_normalized == right_normalized


def _first_non_empty_text(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _truncate_text(text: Any, limit: int) -> str:
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "…"


def _extract_latest_news_title(intelligence: Dict[str, Any]) -> str:
    key_news = intelligence.get("key_news")
    if isinstance(key_news, list):
        for item in key_news:
            if isinstance(item, dict):
                title = str(item.get("title", "")).strip()
                if title:
                    return title
    latest_news = intelligence.get("latest_news")
    if isinstance(latest_news, str) and latest_news.strip():
        return latest_news.strip()
    return ""
