# -*- coding: utf-8 -*-
"""Shared sanitization for model-authored Agent dashboard payloads.

对模型生成的 Agent dashboard 载荷做统一清洗，移除留给确定性后处理的保留字段。
"""

from __future__ import annotations

from typing import Any, Dict


# 模型不应自行填写、留给确定性后处理的保留字段名
RESERVED_EXPLANATION_FIELD = "agent_disagreement_explanation"


def sanitize_agent_dashboard_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Remove fields reserved for deterministic post-processing.

    Both supported forged locations are removed at the shared LLM dashboard
    boundary.  The input mapping and nested dashboard mapping are not mutated.

    删除保留给确定性后处理的字段（顶层与嵌套 dashboard 两处都清），
    不改动入参映射，返回新 dict。
    """
    sanitized = dict(payload)
    sanitized.pop(RESERVED_EXPLANATION_FIELD, None)

    nested = sanitized.get("dashboard")
    if isinstance(nested, dict):
        nested = dict(nested)
        nested.pop(RESERVED_EXPLANATION_FIELD, None)
        sanitized["dashboard"] = nested
    return sanitized


__all__ = ["RESERVED_EXPLANATION_FIELD", "sanitize_agent_dashboard_payload"]
