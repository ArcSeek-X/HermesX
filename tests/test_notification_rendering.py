# -*- coding: utf-8 -*-
"""`src/domain/notification/rendering.py` 的纯渲染回归（W5.6）。

W5.6 把通知层的「值 → 文本」与区块拼装从 `NotificationService` 剥离到 domain 后，
这里锁定迁移前口径：币种后缀与亿/万阈值、NaN 与占位符兜底、股票名只转义星号、
狙击点前缀剥离、阶段决策内容判定、数据源显示名语言回退、策略综合区块的
「无有效载荷不追加」。用例不实例化 service、不读 config、不发请求。
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from src.domain.notification.rendering import (
    append_phase_decision_block,
    append_strategy_synthesis_block,
    clean_sniper_value,
    escape_markdown_name,
    format_amount_cn,
    format_net_shares,
    format_per_share,
    format_percent,
    format_strategy_skill_items,
    format_text,
    phase_decision_has_content,
    phase_decision_list,
    safe_float,
    source_display_name,
)
from src.domain.shared.report_language import get_report_labels


def test_safe_float_handles_percent_thousands_and_garbage() -> None:
    assert safe_float("3.2%") == pytest.approx(3.2)
    assert safe_float("1,234") == pytest.approx(1234.0)
    assert safe_float(7) == pytest.approx(7.0)
    for value in (None, "", "  ", "N/A", "abc"):
        assert safe_float(value) is None


def test_format_amount_cn_thresholds_sign_and_currency() -> None:
    assert format_amount_cn(3.6e8) == "3.60 亿元"
    assert format_amount_cn(-1.2e4, "HKD") == "-1.20 万港元"
    assert format_amount_cn(5678) == "5678 元"
    assert format_amount_cn(1e8, "usd") == "1.00 亿美元"
    assert format_amount_cn(1e8, "TWD") == "1.00 亿新台币"
    for value in (None, "N/A", math.nan, "x"):
        assert format_amount_cn(value) == "N/A"


def test_format_percent_per_share_and_text() -> None:
    assert format_percent("12.345") == "12.35%"
    assert format_percent(None) == "N/A"
    assert format_per_share(1.23456, "USD") == "1.2346 美元"
    assert format_per_share(math.nan) == "N/A"
    assert format_text(None) == "N/A"
    assert format_text("  ") == "N/A"
    assert format_text("贵州茅台") == "贵州茅台"


def test_format_net_shares_thresholds_and_sign() -> None:
    assert format_net_shares(2.5e8) == "+2.50 亿股"
    assert format_net_shares(-3e4) == "-3.00 万股"
    assert format_net_shares(0) == "0 股"
    assert format_net_shares("N/A") == "N/A"


def test_escape_markdown_name_only_escapes_asterisks() -> None:
    assert escape_markdown_name("*ST 海航") == r"\*ST 海航"
    assert escape_markdown_name("A_B") == "A_B"
    assert escape_markdown_name("") == ""


def test_clean_sniper_value_strips_label_prefixes() -> None:
    assert clean_sniper_value("理想买入点：12.30") == "12.30"
    # 原实现只剥离前缀、不做 strip，保留英文前缀后的前导空格，此处锁定该口径
    assert clean_sniper_value("Stop Loss: 9.80") == " 9.80"
    assert clean_sniper_value(12.3) == "12.3"
    assert clean_sniper_value(None) == "N/A"
    assert clean_sniper_value("N/A") == "N/A"
    assert clean_sniper_value("12.30") == "12.30"


def test_phase_decision_helpers() -> None:
    assert phase_decision_list([" a ", "", None, 3]) == ["a", "None", "3"]
    assert phase_decision_list("not-a-list") == []
    assert phase_decision_has_content({"action_window": "明日开盘"}) is True
    assert phase_decision_has_content({"watch_conditions": ["放量"]}) is True
    assert phase_decision_has_content({"watch_conditions": [], "data_limitations": []}) is False


def test_append_phase_decision_block_skips_empty_and_renders_content() -> None:
    labels = get_report_labels("zh")
    skipped: list[str] = []
    append_phase_decision_block(skipped, {"phase_decision": {}}, labels)
    assert skipped == []

    lines: list[str] = []
    append_phase_decision_block(
        lines,
        {
            "phase_decision": {
                "action_window": "明日开盘",
                "immediate_action": "观察",
                "next_check_time": "10:00",
                "confidence_reason": "量能确认",
                "watch_conditions": ["放量突破"],
                "data_limitations": ["缺北向资金"],
            }
        },
        labels,
    )
    rendered = "\n".join(lines)
    assert labels["phase_decision_heading"] in rendered
    assert "- 放量突破" in rendered
    assert "- 缺北向资金" in rendered


def test_source_display_name_maps_and_falls_back() -> None:
    assert source_display_name("tencent", "zh") == "腾讯财经"
    assert source_display_name("tencent", "en") == "Tencent Finance"
    assert source_display_name("unknown-source", "zh") == "unknown-source"
    assert source_display_name(None, "zh") == "N/A"


def test_format_strategy_skill_items_renders_signal_and_confidence() -> None:
    items = [{"skill_id": "trend_following", "signal": "buy", "confidence": 0.75}, {"skill_id": ""}]
    rendered = format_strategy_skill_items(items, "zh")
    assert "/" in rendered and "75%" in rendered
    assert format_strategy_skill_items(None, "zh") == get_report_labels("zh").get("none_label", "None")


def test_append_strategy_synthesis_block_skips_empty_payload() -> None:
    labels = get_report_labels("zh")
    lines: list[str] = []
    append_strategy_synthesis_block(lines, None, labels, "zh")
    assert lines == []


def test_append_strategy_synthesis_block_renders_sections() -> None:
    labels = get_report_labels("zh")
    lines: list[str] = []
    append_strategy_synthesis_block(
        lines,
        {
            "final_signal": "buy",
            "consensus_level": "high",
            "conflict_severity": "none",
            "conflict_count": 0,
            "confidence": 0.8,
            "supporting_skills": [{"skill_id": "trend_following", "signal": "buy"}],
            "opposing_skills": [],
            "conflicts": [],
        },
        labels,
        "zh",
    )
    rendered = "\n".join(lines)
    assert labels["strategy_synthesis_heading"] in rendered
    assert labels["strategy_supporting_skills_label"] in rendered
    assert lines[-1] == ""


def test_rendering_module_does_not_import_outer_layers() -> None:
    source = (
        Path(__file__).resolve().parents[1] / "src" / "domain" / "notification" / "rendering.py"
    ).read_text(encoding="utf-8")
    for token in ("src.application", "src.infrastructure", "src.config", "src.bootstrap"):
        assert token not in source
