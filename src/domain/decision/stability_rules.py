# -*- coding: utf-8 -*-
"""决策稳定化纯规则（decision 领域，W5.1）。

本模块承接原 ``src/application/analysis/analyzer.py`` 里的**决策稳定化取值助手**：
体积很小的纯函数（dict/标量进出），把它们从 4.8k 行的编排文件里剥离出来，
让风险短语判定、资金流方向判定与数值归一规则可独立测试。

边界说明：

- 只做取值、归一与判定，**不改写** ``AnalysisResult`` 上的任何字段——字段回写
  与文案替换属编排职责，仍留在 analyzer。
- 文案本地化经 ``src.domain.shared.report_language``（domain 内部依赖），
  不出现 application / config / infra 依赖。
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, Optional


RISK_WARNING_PLACEHOLDER_TEXTS = frozenset(
    {
        "",
        "n/a",
        "na",
        "none",
        "null",
        "unknown",
        "tbd",
        "暂无",
        "待补充",
        "数据缺失",
        "未知",
        "无",
    }
)

STRUCTURAL_RISK_PHRASE_HINTS = (
    "重大利空",
    "重大风险",
    "关键风险",
    "减持",
    "高位减持",
    "退市",
    "退市风险",
    "停牌",
    "重大问询",
    "处罚",
    "限售",
    "违规",
    "违规风险",
    "诉讼",
    "问询",
    "监管",
    "财务",
    "审计",
    "爆雷",
    "暴雷",
    "违约",
    "违约风险",
    "流动性危机",
    "债务",
    "清算",
    "破产",
    "重大变脸",
    "major risk",
    "material adverse",
    "suspension",
    "delisting",
    "regulatory",
    "downgrade",
    "liquidity",
    "default",
)

CAPITAL_FLOW_UNAVAILABLE_STATUS = frozenset(
    {
        "not_supported",
        "not supported",
        "unsupported",
        "unavailable",
        "not_available",
        "not available",
        "none",
        "na",
        "n/a",
        "null",
        "missing",
    }
)


def is_meaningful_text(value: Any) -> bool:
    """文本非空且不是占位符（N/A、暂无、数据缺失等）。"""
    text = str(value).strip() if value is not None else ""
    if not text:
        return False
    return text.strip().lower() not in RISK_WARNING_PLACEHOLDER_TEXTS


def is_significant_structural_risk(value: Any) -> bool:
    """是否为「重大结构性风险」表述（命中风险短语，或同时含「重大」与「风险」）。"""
    text = str(value or "").strip()
    if not is_meaningful_text(text):
        return False

    normalized = text.lower()
    if any(keyword in normalized for keyword in STRUCTURAL_RISK_PHRASE_HINTS):
        return True

    return "重大" in text and "风险" in normalized


def as_dict_for_decision_guard(value: Any) -> Dict[str, Any]:
    """尽量把 dict / 带 ``to_dict`` 的对象 / 普通对象转为 dict；失败返回空 dict。"""
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        try:
            converted = value.to_dict()
            return converted if isinstance(converted, dict) else {}
        except Exception:
            return {}
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return {}


def first_list_value(value: Any) -> Any:
    """列表/元组取首元素；其它类型原样返回（空容器的原样返回行为保持不变）。"""
    if isinstance(value, (list, tuple)) and value:
        return value[0]
    return value


def coerce_numeric_value(value: Any) -> Optional[float]:
    """把数值 / 带千分位的文本转成 float；布尔、非有限值与占位符返回 None。"""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        if math.isfinite(float(value)):
            return float(value)
        return None
    text = str(value).replace(",", "").replace("，", "").strip()
    if not text or text.upper() in {"N/A", "NA", "NONE", "NULL"}:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def first_numeric_value(*values: Any) -> Optional[float]:
    """按顺序取首个可解析为 float 的值；嵌套列表/元组递归展开。"""
    for value in values:
        if isinstance(value, (list, tuple)):
            nested = first_numeric_value(*value)
            if nested is not None:
                return nested
            continue
        numeric = coerce_numeric_value(value)
        if numeric is not None:
            return numeric
    return None


def capital_flow_bias_with_status(
    fundamental_context: Optional[Dict[str, Any]],
) -> tuple[str, str]:
    """资金流方向判定：返回 ``(bias, reason)``。

    bias ∈ ``inflow`` / ``outflow`` / ``neutral`` / ``unavailable``；
    reason 为可审计的判定原因（``ok``、``conflict_or_missing``、
    ``capital_flow_block_missing`` 等）。
    """
    if not isinstance(fundamental_context, dict):
        return "unavailable", "invalid_context"
    block = fundamental_context.get("capital_flow")
    if not isinstance(block, dict):
        return "unavailable", "capital_flow_block_missing"
    status = str(block.get("status") or "").strip().lower()
    normalized_status = status.replace("-", " ").replace("_", " ").strip()
    if (
        normalized_status in CAPITAL_FLOW_UNAVAILABLE_STATUS
        or "not supported" in normalized_status
    ):
        return "unavailable", status or "not_supported"
    data = block.get("data") if isinstance(block.get("data"), dict) else block
    stock_flow = data.get("stock_flow") if isinstance(data, dict) else None
    if not isinstance(stock_flow, dict) or not stock_flow:
        return "unavailable", "empty_stock_flow"

    def _flow_direction(value: Optional[float]) -> Optional[str]:
        if value is None or value == 0:
            return None
        return "inflow" if value > 0 else "outflow"

    numeric_values = [
        coerce_numeric_value(stock_flow.get("main_net_inflow")),
        coerce_numeric_value(stock_flow.get("inflow_5d")),
        coerce_numeric_value(stock_flow.get("inflow_10d")),
    ]
    if all(value is None for value in numeric_values):
        return "unavailable", "missing_or_na_flow_fields"

    ordered_signals = [_flow_direction(value) for value in numeric_values]
    directions = {signal for signal in ordered_signals if signal is not None}
    if not directions or len(directions) > 1:
        return "neutral", "conflict_or_missing"
    for signal in ordered_signals:
        if signal is not None:
            return signal, "ok"
    return "neutral", "neutral"


def capital_flow_bias(fundamental_context: Optional[Dict[str, Any]]) -> str:
    """资金流方向（只取 ``capital_flow_bias_with_status`` 的 bias）。"""
    return capital_flow_bias_with_status(fundamental_context)[0]
