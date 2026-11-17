# -*- coding: utf-8 -*-
"""W5.2 下沉到 domain 的流水线纯规则回归。

覆盖 `src/domain/analysis/pipeline_rules.py`：这些判定与兜底助手原先内联在
近 4k 行的 `pipeline.py` 里，只能通过构造 `StockAnalysisPipeline` 间接测试。
这里锁定迁移前的口径——Agent 占位判定与建议提取、趋势五类兜底、摘要多语言、
股票名占位、整数解析、量比/均线分档、持久化上下文裁剪、日期归一、符号检索
变体，并确认 domain 侧不依赖 application / infrastructure / config / bootstrap。

注意：`pipeline.py` 仍保留同名薄委托方法，因此这些断言同时是它们的契约来源。
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from pathlib import Path
from types import SimpleNamespace

from src.domain.analysis.pipeline_rules import (
    coerce_daily_market_context_date,
    compute_ma_status,
    describe_volume_ratio,
    extract_advice_text_from_dict,
    is_agent_field_missing,
    is_agent_placeholder_text,
    is_placeholder_stock_name,
    safe_int,
    safe_to_dict,
    stop_loss_fallback_from_trend,
    summary_fallback_from_result,
    symbol_scope_lookup_values,
    trend_decision_fallback,
    trend_label_fallback,
    trend_score_fallback,
    trend_signal_fallback,
    without_runtime_prompt_context,
)


class _TrendStatus(Enum):
    BULLISH = "bullish"


class _BuySignal(Enum):
    STRONG_BUY = "强烈买入"


def _trend(**overrides):
    payload = {
        "signal_score": 72,
        "trend_status": _TrendStatus.BULLISH,
        "buy_signal": _BuySignal.STRONG_BUY,
        "support_levels": [12.3],
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


# --------------------------------------------------------------------------- #
# Agent 字段占位判定
# --------------------------------------------------------------------------- #


def test_placeholder_text_matches_known_tokens_only():
    assert is_agent_placeholder_text("") is True
    assert is_agent_placeholder_text("N/A") is True
    assert is_agent_placeholder_text("none") is True
    assert is_agent_placeholder_text("未知") is True
    assert is_agent_placeholder_text("数据缺失") is True
    # 未 strip：带前缀空格的占位符不算占位（由调用方先 strip）
    assert is_agent_placeholder_text(" N/A") is False
    assert is_agent_placeholder_text("暂无数据") is False


def test_extract_advice_text_prefers_matching_position_branch():
    assert extract_advice_text_from_dict({"has_position": "  持有  ", "no_position": "观望"}) == "持有"
    assert extract_advice_text_from_dict({"has_position": "N/A", "no_position": "观望"}) == "观望"
    assert extract_advice_text_from_dict({"has_position": "无", "no_position": "TBD"}) == ""
    assert extract_advice_text_from_dict({}) == ""


def test_is_agent_field_missing_distinguishes_scalar_and_collections():
    assert is_agent_field_missing(None) is True
    assert is_agent_field_missing("") is True
    assert is_agent_field_missing("未知", scalar=True, expect_text=True) is True
    # scalar + expect_text 时非字符串视为缺失
    assert is_agent_field_missing(72, scalar=True, expect_text=True) is True
    assert is_agent_field_missing(72) is False
    # scalar 下 dict 默认视为缺失，除非 allow_dict 且能取到建议文本
    assert is_agent_field_missing({"has_position": "持有"}, scalar=True) is True
    assert is_agent_field_missing({"has_position": "持有"}, scalar=True, allow_dict=True) is False
    assert is_agent_field_missing({"has_position": "N/A"}, scalar=True, allow_dict=True) is True
    # scalar 下列表一律缺失；非 scalar 的空列表不算缺失（由上层判空）
    assert is_agent_field_missing([], scalar=True) is True
    assert is_agent_field_missing([]) is False


# --------------------------------------------------------------------------- #
# 趋势兜底
# --------------------------------------------------------------------------- #


def test_trend_score_fallback_only_accepts_positive_int():
    assert trend_score_fallback(None) is None
    assert trend_score_fallback(_trend(signal_score=0)) is None
    assert trend_score_fallback(_trend(signal_score=-8)) is None
    assert trend_score_fallback(_trend(signal_score="abc")) is None
    assert trend_score_fallback(_trend(signal_score="66")) == 66


def test_trend_label_fallback_returns_enum_value_verbatim_outside_en():
    # 非 en 语言直取枚举值，不做二次本地化
    assert trend_label_fallback(_trend(), "zh") == "bullish"
    assert trend_label_fallback(_trend(), "ko") == "bullish"
    assert trend_label_fallback(_trend(), "en") == "Bullish"
    assert trend_label_fallback(None, "zh") == ""


def test_trend_signal_fallback_localizes_operation_advice():
    assert trend_signal_fallback(_trend(), "zh") == "强烈买入"
    assert trend_signal_fallback(_trend(), "en") == "Strong Buy"
    assert trend_signal_fallback(None, "zh") == ""


def test_trend_decision_fallback_maps_enum_name():
    assert trend_decision_fallback(_trend()) == "buy"
    assert trend_decision_fallback(_trend(buy_signal=None)) is None
    assert trend_decision_fallback(None) is None


def test_stop_loss_fallback_prefers_first_support_level():
    assert stop_loss_fallback_from_trend(_trend(), "zh") == 12.3
    assert stop_loss_fallback_from_trend(_trend(support_levels=[]), "zh") == "待补充"
    assert stop_loss_fallback_from_trend(None, "en") == "TBD"


def test_summary_fallback_requires_both_trend_and_advice():
    result = SimpleNamespace(trend_prediction="看多", operation_advice="买入")
    assert summary_fallback_from_result(result, "zh") == "趋势结论：看多；操作建议：买入。"
    assert summary_fallback_from_result(result, "en") == "Trend view: 看多; action advice: 买入."
    assert summary_fallback_from_result(result, "ko") == "추세 결론: 看多; 대응 전략: 买入."

    only_trend = SimpleNamespace(trend_prediction="看多", operation_advice="  ")
    assert summary_fallback_from_result(only_trend, "zh") == ""


# --------------------------------------------------------------------------- #
# 基础取值助手
# --------------------------------------------------------------------------- #


def test_is_placeholder_stock_name_detects_common_placeholders():
    assert is_placeholder_stock_name("", "600519") is True
    assert is_placeholder_stock_name("   ", "600519") is True
    assert is_placeholder_stock_name("600519", "600519") is True
    assert is_placeholder_stock_name("股票600519", "600519") is True
    assert is_placeholder_stock_name("Unknown Corp", "AAPL") is True
    assert is_placeholder_stock_name("贵州茅台", "600519") is False


def test_safe_int_parses_first_integer_fragment():
    assert safe_int(None) == 50
    assert safe_int(5) == 5
    assert safe_int(3.9) == 3
    assert safe_int("abc") == 50
    assert safe_int("  123  ") == 123
    # 负数与百分号：取首个整数片段，小数部分截断
    assert safe_int("-8.5%") == -8
    assert safe_int("评分 66 分") == 66
    assert safe_int("abc", default=7) == 7


def test_describe_volume_ratio_boundaries():
    cases = [
        (0.0, "极度萎缩"),
        (0.49, "极度萎缩"),
        (0.5, "明显萎缩"),
        (0.79, "明显萎缩"),
        (0.8, "正常"),
        (1.19, "正常"),
        (1.2, "温和放量"),
        (1.99, "温和放量"),
        (2.0, "明显放量"),
        (2.99, "明显放量"),
        (3.0, "巨量"),
    ]
    for volume_ratio, expected in cases:
        assert describe_volume_ratio(volume_ratio) == expected


def test_compute_ma_status_all_branches():
    assert compute_ma_status(10, 9, 8, 7) == "多头排列 📈"
    assert compute_ma_status(7, 8, 9, 10) == "空头排列 📉"
    assert compute_ma_status(10, 9, 8.5, 12) == "短期向好 🔼"
    assert compute_ma_status(8, 9, 9.5, 9.2) == "短期走弱 🔽"
    assert compute_ma_status(0, 0, 0, 0) == "震荡整理 ↔️"
    # None 视为 0，不抛异常
    assert compute_ma_status(None, None, None, None) == "震荡整理 ↔️"


# --------------------------------------------------------------------------- #
# 持久化上下文 / 日期
# --------------------------------------------------------------------------- #


def test_without_runtime_prompt_context_drops_runtime_keys_without_mutation():
    source = {
        "stock_code": "600519",
        "market_phase_context": {"phase": "open"},
        "portfolio_context": {"positions": []},
        "analysis_context_pack": "pack",
        "analysis_context_pack_summary": "summary",
        "daily_market_context_summary": "daily",
        "enhanced_context": {
            "news": ["n1"],
            "daily_market_context_summary": "nested",
        },
    }

    sanitized = without_runtime_prompt_context(source)

    for key in (
        "market_phase_context",
        "portfolio_context",
        "analysis_context_pack",
        "analysis_context_pack_summary",
        "daily_market_context_summary",
    ):
        assert key not in sanitized
    assert sanitized["stock_code"] == "600519"
    assert sanitized["enhanced_context"] == {"news": ["n1"]}
    # 原 dict（含嵌套）不被改写
    assert source["daily_market_context_summary"] == "daily"
    assert source["enhanced_context"]["daily_market_context_summary"] == "nested"


def test_safe_to_dict_handles_to_dict_dunder_and_failures():
    assert safe_to_dict(None) is None
    assert safe_to_dict(SimpleNamespace(a=1)) == {"a": 1}
    assert safe_to_dict({"a": 1}) is None  # dict 无 to_dict/__dict__

    class _Broken:
        def to_dict(self):
            raise RuntimeError("boom")

    assert safe_to_dict(_Broken()) is None

    class _Payload:
        def to_dict(self):
            return {"x": 1}

    assert safe_to_dict(_Payload()) == {"x": 1}


def test_coerce_daily_market_context_date_normalizes_inputs():
    assert coerce_daily_market_context_date(datetime(2026, 10, 24, 15, 30)) == date(2026, 10, 24)
    assert coerce_daily_market_context_date(date(2026, 10, 24)) == date(2026, 10, 24)
    assert coerce_daily_market_context_date("2026-10-24T15:30:00") == date(2026, 10, 24)
    assert coerce_daily_market_context_date("2026-10-24") == date(2026, 10, 24)
    assert coerce_daily_market_context_date("2026-13-01") is None
    assert coerce_daily_market_context_date(20261024) is None


# --------------------------------------------------------------------------- #
# 符号检索变体
# --------------------------------------------------------------------------- #


def test_symbol_scope_lookup_values_covers_hk_spellings():
    values = symbol_scope_lookup_values("HK00700", "hk")
    for expected in ("HK00700", "hk00700", "00700", "700", "HK700", "00700.HK"):
        assert expected in values
    assert len(values) == len(set(values))

    # 无 HK 前缀的裸 5 位港股代码在 hk 市场下不臆造交易所变体
    assert symbol_scope_lookup_values("00700", "hk") == ["00700"]


def test_symbol_scope_lookup_values_covers_cn_exchange_forms():
    sh = symbol_scope_lookup_values("600519", "cn")
    for expected in ("600519", "SH600519", "SH.600519", "600519.SH", "600519.SS", "SS.600519"):
        assert expected in sh
    assert len(sh) == len(set(sh))

    sz = symbol_scope_lookup_values("000001", "cn")
    assert "SZ000001" in sz
    assert "000001.SZ" in sz
    assert not any(value.startswith("SS") for value in sz)

    # 北交所代码走 BJ 变体
    bj = symbol_scope_lookup_values("920748", "cn")
    assert "BJ920748" in bj
    assert "920748.BJ" in bj

    # 非 cn 市场不追加 A 股交易所拼写
    assert symbol_scope_lookup_values("600519", "us") == ["600519"]


# --------------------------------------------------------------------------- #
# 分层守卫
# --------------------------------------------------------------------------- #


def test_pipeline_rules_module_stays_in_domain_layer():
    source = Path("src/domain/analysis/pipeline_rules.py").read_text(encoding="utf-8")
    for forbidden in (
        "src.application",
        "src.infrastructure",
        "src.config",
        "src.bootstrap",
    ):
        assert forbidden not in source
