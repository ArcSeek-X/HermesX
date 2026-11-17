# -*- coding: utf-8 -*-
"""通知渲染纯规则（notification 领域，W5.6）。

W5.6 把「意图/发送编排」与「文本渲染」分开：本模块承接原
``src/application/notification/notification.py`` 里**不依赖 service 状态**的格式化
助手——数值/金额/百分比/股数格式化、股票名 Markdown 转义、狙击点前缀剥离、阶段决策
区块与策略综合区块的拼装、数据源显示名映射。

边界说明：

- 只做「值 → 文本」与「列表追加」，不读 config、不发请求、不改 service 状态。
- 文案标签由调用方注入（``labels`` / ``report_language``），本模块只经
  ``src.domain.shared.report_language`` 取本地化纯函数。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.domain.shared.report_language import (
    get_report_labels,
    localize_conflict_severity,
    localize_consensus_level,
    localize_strategy_conflict_description,
    localize_strategy_signal,
    localize_strategy_skill,
    localize_strategy_synthesis_summary,
    normalize_report_language,
    normalize_strategy_synthesis_payload,
    strategy_invalid_opinion_count,
)

CURRENCY_SUFFIX: Dict[str, str] = {
    "USD": "美元",
    "HKD": "港元",
    "CNY": "元",
    "RMB": "元",
    "CNH": "元",
    "TWD": "新台币",  # 台股 (TWSE/TPEx) 以新台币计价，避免与 A 股「元」(人民币) 混淆
}

SOURCE_DISPLAY_NAMES: Dict[str, Dict[str, str]] = {
    "tencent": {"zh": "腾讯财经", "en": "Tencent Finance"},
    "akshare_em": {"zh": "东方财富", "en": "Eastmoney"},
    "akshare_sina": {"zh": "新浪财经", "en": "Sina Finance"},
    "akshare_qq": {"zh": "腾讯财经", "en": "Tencent Finance"},
    "efinance": {"zh": "东方财富(efinance)", "en": "Eastmoney (efinance)"},
    "tushare": {"zh": "Tushare Pro", "en": "Tushare Pro"},
    "sina": {"zh": "新浪财经", "en": "Sina Finance"},
    "stooq": {"zh": "Stooq", "en": "Stooq"},
    "longbridge": {"zh": "长桥", "en": "Longbridge"},
    "fallback": {"zh": "降级兜底", "en": "Fallback"},
}

SNIPER_VALUE_PREFIXES: tuple = (
    "理想买入点：",
    "次优买入点：",
    "止损位：",
    "目标位：",
    "理想买入点:",
    "次优买入点:",
    "止损位:",
    "目标位:",
    "Ideal Entry:",
    "Secondary Entry:",
    "Stop Loss:",
    "Target:",
)


def safe_float(value: Any) -> Optional[float]:
    """尽力转 float；兼容 ``"3.2%"`` 与 ``"1,234"`` 形态，失败返回 None。"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    text = str(value).strip().replace(",", "")
    if text.endswith("%"):
        text = text[:-1].strip()
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def format_strategy_skill_items(items: Any, report_language: str = "zh") -> str:
    """把技能条目渲染为 ``技能/信号/置信度`` 用「、」连接的文本。"""
    none_text = get_report_labels(report_language).get("none_label", "None")
    if not isinstance(items, list):
        return none_text
    formatted: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        skill_id = str(item.get("skill_id") or "").strip()
        signal = str(item.get("signal") or "").strip()
        confidence = item.get("confidence")
        if not skill_id:
            continue
        suffix = f"/{localize_strategy_signal(signal, report_language)}" if signal else ""
        if isinstance(confidence, (int, float)):
            suffix += f"/{confidence:.0%}"
        formatted.append(f"{localize_strategy_skill(skill_id, report_language)}{suffix}")
    return "、".join(formatted) if formatted else none_text


def append_strategy_synthesis_block(
    lines: List[str],
    strategy_synthesis: Any,
    labels: Dict[str, str],
    report_language: str,
) -> None:
    """就地追加「策略综合」小节（无有效载荷时不追加）。"""
    strategy_synthesis = normalize_strategy_synthesis_payload(strategy_synthesis)
    if not strategy_synthesis:
        return
    confidence = strategy_synthesis.get("confidence")
    confidence_text = f"{confidence:.0%}" if isinstance(confidence, (int, float)) else "N/A"
    lines.extend([
        f"### 🧩 {labels['strategy_synthesis_heading']}",
        "",
        (
            f"- {labels['strategy_final_signal_label']}: "
            f"{localize_strategy_signal(strategy_synthesis.get('final_signal', 'N/A'), report_language)} | "
            f"{labels['strategy_consensus_level_label']}: "
            f"{localize_consensus_level(strategy_synthesis.get('consensus_level', 'N/A'), report_language)} | "
            f"{labels['strategy_conflict_label']}: "
            f"{localize_conflict_severity(strategy_synthesis.get('conflict_severity', 'none'), report_language)} "
            f"({strategy_synthesis.get('conflict_count', 0)}) | "
            f"{labels['strategy_confidence_label']}: {confidence_text}"
        ),
    ])
    summary = localize_strategy_synthesis_summary(strategy_synthesis, report_language)
    if summary:
        lines.append(f"- {labels['strategy_summary_label']}: {summary}")
    lines.append(
        f"- {labels['strategy_supporting_skills_label']}: "
        f"{format_strategy_skill_items(strategy_synthesis.get('supporting_skills'), report_language)}"
    )
    lines.append(
        f"- {labels['strategy_opposing_skills_label']}: "
        f"{format_strategy_skill_items(strategy_synthesis.get('opposing_skills'), report_language)}"
    )
    invalid_opinion_count = strategy_invalid_opinion_count(strategy_synthesis)
    if invalid_opinion_count:
        invalid_label = labels.get("strategy_invalid_opinions_label", "")
        if invalid_label:
            lines.append(f"- {invalid_label.format(count=invalid_opinion_count)}")
    for conflict in (strategy_synthesis.get("conflicts") or [])[:3]:
        if isinstance(conflict, dict) and conflict.get("conflict_type"):
            participants = conflict.get("participants") or []
            participant_text = "、".join(localize_strategy_skill(participant, report_language) for participant in participants)
            suffix = f"（{participant_text}）" if participant_text else ""
            lines.append(
                f"- {localize_conflict_severity(conflict.get('severity', 'medium'), report_language)}: "
                f"{localize_strategy_conflict_description(conflict.get('conflict_type'), report_language)}{suffix}"
            )
    lines.append("")


def escape_markdown_name(name: str) -> str:
    """转义股票名里的 Markdown 星号（``*ST`` → ``\\*ST``）；空值原样返回。"""
    return name.replace("*", r"\*") if name else name


def clean_sniper_value(value: Any) -> str:
    """归一狙击点取值并剥离冗余标签前缀。"""
    if value is None:
        return "N/A"
    if isinstance(value, (int, float)):
        return str(value)
    if not isinstance(value, str):
        return str(value)
    if not value or value == "N/A":
        return value
    for prefix in SNIPER_VALUE_PREFIXES:
        if value.startswith(prefix):
            return value[len(prefix):]
    return value


def phase_decision_list(value: Any) -> List[str]:
    """把阶段决策的列表字段归一为非空字符串列表。"""
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def phase_decision_has_content(phase_decision: Dict[str, Any]) -> bool:
    """阶段决策是否有任何可渲染内容。"""
    text_keys = (
        "action_window",
        "immediate_action",
        "next_check_time",
        "confidence_reason",
    )
    if any(str(phase_decision.get(key) or "").strip() for key in text_keys):
        return True
    return bool(
        phase_decision_list(phase_decision.get("watch_conditions"))
        or phase_decision_list(phase_decision.get("data_limitations"))
    )


def append_phase_decision_block(
    report_lines: List[str],
    dashboard: Dict[str, Any],
    labels: Dict[str, str],
) -> None:
    """就地追加「阶段决策」小节（无内容时跳过）。"""
    phase_decision = dashboard.get("phase_decision") if dashboard else None
    if not isinstance(phase_decision, dict):
        return
    if not phase_decision_has_content(phase_decision):
        return

    watch_conditions = phase_decision_list(phase_decision.get("watch_conditions"))
    data_limitations = phase_decision_list(phase_decision.get("data_limitations"))

    report_lines.extend([
        f"### 🛡️ {labels['phase_decision_heading']}",
        "",
        f"| {labels['action_window_label']} | {labels['immediate_action_label']} | {labels['next_check_time_label']} |",
        "|---------|---------|---------|",
        f"| {phase_decision.get('action_window') or 'N/A'} | "
        f"{phase_decision.get('immediate_action') or 'N/A'} | "
        f"{phase_decision.get('next_check_time') or 'N/A'} |",
        "",
    ])

    if watch_conditions:
        report_lines.append(f"**{labels['watch_conditions_label']}**:")
        for condition in watch_conditions:
            report_lines.append(f"- {condition}")
        report_lines.append("")

    confidence_reason = str(phase_decision.get("confidence_reason") or "").strip()
    if confidence_reason:
        report_lines.extend([
            f"**{labels['confidence_reason_label']}**: {confidence_reason}",
            "",
        ])

    if data_limitations:
        report_lines.append(f"**{labels['data_limitations_label']}**:")
        for limitation in data_limitations:
            report_lines.append(f"- {limitation}")
        report_lines.append("")


def format_amount_cn(value: Any, currency: Optional[str] = None) -> str:
    """金额按 亿/万 缩写并附币种；非数值或 NaN 返回 N/A。"""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if amount != amount:  # NaN
        return "N/A"
    sign = "-" if amount < 0 else ""
    abs_amount = abs(amount)
    suffix = CURRENCY_SUFFIX.get((currency or "").upper(), "元")
    if abs_amount >= 1e8:
        return f"{sign}{abs_amount / 1e8:.2f} 亿{suffix}"
    if abs_amount >= 1e4:
        return f"{sign}{abs_amount / 1e4:.2f} 万{suffix}"
    return f"{sign}{abs_amount:.0f} {suffix}"


def format_percent(value: Any) -> str:
    """百分比保留两位小数；非数值返回 N/A。"""
    try:
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return "N/A"


def format_per_share(value: Any, currency: Optional[str] = None) -> str:
    """每股金额保留四位小数并附币种；非数值或 NaN 返回 N/A。"""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if amount != amount:  # NaN
        return "N/A"
    suffix = CURRENCY_SUFFIX.get((currency or "").upper(), "元")
    return f"{amount:.4f} {suffix}"


def format_text(value: Any) -> str:
    """文本兜底：None / 空白统一为 N/A。"""
    if value is None:
        return "N/A"
    text = str(value).strip()
    return text if text else "N/A"


def format_net_shares(value: Any) -> str:
    """机构净买卖量按 万股/亿股 缩写并带符号；非数值或 NaN 返回 N/A。"""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if amount != amount:  # NaN
        return "N/A"
    sign = "+" if amount > 0 else ("-" if amount < 0 else "")
    abs_amount = abs(amount)
    if abs_amount >= 1e8:
        return f"{sign}{abs_amount / 1e8:.2f} 亿股"
    if abs_amount >= 1e4:
        return f"{sign}{abs_amount / 1e4:.2f} 万股"
    return f"{sign}{abs_amount:.0f} 股"


def source_display_name(source: Any, language: Optional[str]) -> str:
    """实时数据源显示名；未知数据源原样返回。"""
    raw_source = str(source or "N/A")
    mapping = SOURCE_DISPLAY_NAMES.get(raw_source)
    if not mapping:
        return raw_source
    return mapping[normalize_report_language(language)]
