# -*- coding: utf-8 -*-
"""W5.1 下沉到 domain 的三簇纯规则回归。

覆盖 `src/domain/decision/stability_rules.py`、`src/domain/analysis/chip_rules.py`
与 `src/domain/analysis/prompt_sanitizer.py`：这些函数原先内联在 4.8k 行的
`analyzer.py` 里，只能通过导入 analyzer 间接测试。这里锁定迁移前的判定口径
（占位符剔除、千分位解析、资金流冲突、否定词与转折句、筹码健康度分层、
Prompt 清洗只改派生副本），并确认 domain 侧不依赖 application / infrastructure。
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from src.domain.analysis.chip_rules import (
    build_chip_structure,
    coerce_chip_metric,
    derive_chip_health,
    has_meaningful_chip_data,
    safe_float,
)
from src.domain.analysis.prompt_sanitizer import (
    BULLISH_TREND_HINTS,
    contains_trend_hint,
    infer_trend_direction,
    sanitize_trend_analysis_for_prompt,
)
from src.domain.decision.stability_rules import (
    as_dict_for_decision_guard,
    capital_flow_bias,
    capital_flow_bias_with_status,
    coerce_numeric_value,
    first_list_value,
    first_numeric_value,
    is_meaningful_text,
    is_significant_structural_risk,
)

_DOMAIN_DIR = Path(__file__).resolve().parents[1] / "src" / "domain"


# ---------- decision/stability_rules ----------


def test_is_meaningful_text_rejects_placeholders() -> None:
    assert is_meaningful_text("减持风险") is True
    for placeholder in ("", "  ", "N/A", "None", "暂无", "数据缺失"):
        assert is_meaningful_text(placeholder) is False


def test_is_significant_structural_risk_matches_phrases_and_generic_form() -> None:
    assert is_significant_structural_risk("大股东高位减持") is True
    assert is_significant_structural_risk("存在退市风险") is True
    assert is_significant_structural_risk("重大风险待披露") is True
    assert is_significant_structural_risk("行业景气度下滑") is False
    assert is_significant_structural_risk(None) is False


def test_as_dict_for_decision_guard_handles_dict_objects_and_failures() -> None:
    assert as_dict_for_decision_guard({"a": 1}) == {"a": 1}

    class _WithToDict:
        def to_dict(self):
            return {"b": 2}

    class _BrokenToDict:
        def to_dict(self):
            raise RuntimeError("boom")

    class _Plain:
        def __init__(self) -> None:
            self.c = 3

    assert as_dict_for_decision_guard(_WithToDict()) == {"b": 2}
    assert as_dict_for_decision_guard(_BrokenToDict()) == {}
    assert as_dict_for_decision_guard(_Plain()) == {"c": 3}
    assert as_dict_for_decision_guard("text") == {}


def test_first_list_value_unwraps_only_non_empty_sequences() -> None:
    assert first_list_value([1, 2]) == 1
    assert first_list_value((3,)) == 3
    assert first_list_value([]) == []
    assert first_list_value("abc") == "abc"


def test_coerce_numeric_value_parses_thousands_and_rejects_placeholders() -> None:
    assert coerce_numeric_value("1,234.5万") == pytest.approx(1234.5)
    assert coerce_numeric_value("-3.2%") == pytest.approx(-3.2)
    assert coerce_numeric_value(7) == pytest.approx(7.0)
    for value in (True, None, "N/A", "", math.inf, math.nan):
        assert coerce_numeric_value(value) is None


def test_first_numeric_value_flattens_nested_sequences() -> None:
    assert first_numeric_value(None, ["N/A", ("2,000",)], 3) == pytest.approx(2000.0)
    assert first_numeric_value(None, "暂无") is None


def test_capital_flow_bias_with_status_reports_each_reason() -> None:
    assert capital_flow_bias_with_status(None) == ("unavailable", "invalid_context")
    assert capital_flow_bias_with_status({}) == ("unavailable", "capital_flow_block_missing")
    assert capital_flow_bias_with_status({"capital_flow": {"status": "not_supported"}}) == (
        "unavailable",
        "not_supported",
    )
    assert capital_flow_bias_with_status({"capital_flow": {"status": "ok", "data": {}}}) == (
        "unavailable",
        "empty_stock_flow",
    )
    assert capital_flow_bias_with_status(
        {"capital_flow": {"status": "ok", "data": {"stock_flow": {"main_net_inflow": "N/A"}}}}
    ) == ("unavailable", "missing_or_na_flow_fields")


def test_capital_flow_bias_prefers_unanimous_direction_and_flags_conflict() -> None:
    inflow = {
        "capital_flow": {
            "status": "ok",
            "data": {"stock_flow": {"main_net_inflow": "1,200万", "inflow_5d": 300, "inflow_10d": 0}},
        }
    }
    conflict = {
        "capital_flow": {
            "status": "ok",
            "data": {"stock_flow": {"main_net_inflow": 100, "inflow_5d": -50}},
        }
    }
    assert capital_flow_bias(inflow) == "inflow"
    assert capital_flow_bias(conflict) == "neutral"
    assert capital_flow_bias_with_status(conflict)[1] == "conflict_or_missing"


# ---------- analysis/chip_rules ----------


def test_safe_float_and_coerce_chip_metric_keep_missing_vs_zero() -> None:
    assert safe_float("2.5") == pytest.approx(2.5)
    assert safe_float("bad", default=-1.0) == pytest.approx(-1.0)
    assert safe_float(math.nan, default=-1.0) == pytest.approx(-1.0)
    assert coerce_chip_metric("0") == pytest.approx(0.0)
    assert coerce_chip_metric("N/A") is None
    assert coerce_chip_metric(math.nan) is None


def test_derive_chip_health_layers() -> None:
    assert derive_chip_health(0.95, 0.10) == "警惕"  # 获利盘极高
    assert derive_chip_health(0.50, 0.25) == "警惕"  # 筹码分散
    assert derive_chip_health(0.50, 0.10) == "健康"  # 集中且获利适中
    assert derive_chip_health(0.20, 0.20) == "一般"


def test_has_meaningful_chip_data_accepts_object_and_dict_with_fallback_key() -> None:
    class _Chip:
        avg_cost = 10.0
        concentration_90 = 0.12
        concentration_70 = 0.08

    assert has_meaningful_chip_data(_Chip()) is True
    assert has_meaningful_chip_data({"avg_cost": 10.0, "concentration": 0.12}) is True
    assert has_meaningful_chip_data({"avg_cost": 0, "concentration_90": 0.12}) is False
    assert has_meaningful_chip_data({"avg_cost": 10.0, "concentration_90": "N/A"}) is False
    assert has_meaningful_chip_data(None) is False


def test_build_chip_structure_formats_metrics_and_passes_language() -> None:
    built = build_chip_structure({"profit_ratio": 0.5123, "avg_cost": 9.8, "concentration_90": 0.1234})
    assert built == {
        "profit_ratio": "51.2%",
        "avg_cost": 9.8,
        "concentration": "12.34%",
        "chip_health": "健康",
    }
    assert build_chip_structure({"avg_cost": 0, "concentration_90": 0.2})["avg_cost"] == "N/A"

    captured: dict = {}

    def _spy_derive(profit_ratio, concentration_90, language):
        captured["args"] = (profit_ratio, concentration_90, language)
        return "spy"

    assert (
        build_chip_structure({"profit_ratio": 0.4, "avg_cost": 5, "concentration_90": 0.1}, "en", derive=_spy_derive)[
            "chip_health"
        ]
        == "spy"
    )
    assert captured["args"] == (pytest.approx(0.4), pytest.approx(0.1), "en")


# ---------- analysis/prompt_sanitizer ----------


def test_contains_trend_hint_respects_negation_and_contrast() -> None:
    assert contains_trend_hint("尚未形成上升趋势", BULLISH_TREND_HINTS) is False
    assert contains_trend_hint("非常明显的多头排列", BULLISH_TREND_HINTS) is True
    assert contains_trend_hint("不是空头而是多头排列", BULLISH_TREND_HINTS) is True
    assert contains_trend_hint("未转为上升趋势", BULLISH_TREND_HINTS) is False


def test_infer_trend_direction_covers_hints_ma_order_and_neutral() -> None:
    assert infer_trend_direction({"trend_status": "弱势多头", "ma_alignment": "MA5>MA10 但 MA10≤MA20"}) == "bullish"
    assert infer_trend_direction({"trend_status": "空头排列"}) == "bearish"
    assert infer_trend_direction({"trend_status": "未形成上升趋势", "ma_alignment": "当前非多头排列"}) == "neutral"
    assert infer_trend_direction({}) == "neutral"


def test_sanitize_trend_analysis_for_prompt_returns_derived_copy_only() -> None:
    original = {
        "trend_status": "空头排列",
        "signal_reasons": ["上升趋势初现", "跌破支撑"],
        "risk_factors": ["空头排列明确"],
    }
    sanitized = sanitize_trend_analysis_for_prompt(original, volume_change_ratio=12.4)

    assert sanitized is not original
    assert original == {
        "trend_status": "空头排列",
        "signal_reasons": ["上升趋势初现", "跌破支撑"],
        "risk_factors": ["空头排列明确"],
    }
    assert sanitized["prompt_trend_direction"] == "bearish"
    assert sanitized["signal_reasons"] == ["跌破支撑"]
    notes = sanitized["prompt_consistency_notes"]
    assert any("看多结构理由" in note for note in notes)
    assert any("量能信号必须降权" in note for note in notes)


def test_sanitize_trend_analysis_for_prompt_ignores_small_volume_change() -> None:
    sanitized = sanitize_trend_analysis_for_prompt({"trend_status": "多头排列"}, volume_change_ratio=3)
    assert sanitized["prompt_consistency_notes"] == []


def test_domain_rules_do_not_import_outer_layers() -> None:
    forbidden = ("src.application", "src.infrastructure", "src.config", "src.bootstrap")
    for name in ("decision/stability_rules.py", "analysis/chip_rules.py", "analysis/prompt_sanitizer.py"):
        source = (_DOMAIN_DIR / name).read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source, f"{name} 不应依赖 {token}"
