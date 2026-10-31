# -*- coding: utf-8 -*-
"""AlphaSift 热点详情载荷形状兼容规则（纯 dict 操作，无 IO）。

新旧热点详情消费方保持同一形状：``stocks`` / ``leader_stocks`` / ``stock_count``
三字段的互相回填与嵌套摘要提取。
"""

from __future__ import annotations

from typing import Any, Dict, List


def _extract_nested_hotspot_leader_stocks(payload: Dict[str, Any]) -> List[Any]:
    for key in ("summary_detail", "summary"):
        summary = payload.get(key)
        if not isinstance(summary, dict):
            continue
        leader_stocks = summary.get("leader_stocks")
        if isinstance(leader_stocks, list) and leader_stocks:
            return leader_stocks
    return []


def _ensure_hotspot_detail_compat_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Keep old and new AlphaSift hotspot detail consumers on the same shape."""
    stocks = payload.get("stocks")
    leader_stocks = payload.get("leader_stocks")
    if not isinstance(stocks, list):
        stocks = []
    if not isinstance(leader_stocks, list) or not leader_stocks:
        nested_leader_stocks = _extract_nested_hotspot_leader_stocks(payload)
        leader_stocks = nested_leader_stocks or (leader_stocks if isinstance(leader_stocks, list) else [])
    if not stocks and leader_stocks:
        stocks = leader_stocks
    if not leader_stocks and stocks:
        leader_stocks = stocks
    payload["stocks"] = stocks
    payload["leader_stocks"] = leader_stocks
    payload["stock_count"] = len(stocks)
    return payload
