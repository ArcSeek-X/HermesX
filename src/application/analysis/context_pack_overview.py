# -*- coding: utf-8 -*-
"""Low-sensitivity public overview for Issue #1389 AnalysisContextPack P4.

面向 Issue #1389 的 AnalysisContextPack（P4 版）低敏感公开概览层。
把内部分析上下文包投影成可对外暴露的概览（主体/各数据块状态/计数/数据质量/告警），
并对所有可能外泄的字段做脱敏与类型安全裁剪；提供从上下文快照提取/剔除公开概览的辅助函数。
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any, Dict, List, Optional

from src.application.reporting.context_pack_prompt import (
    SENSITIVE_MARKERS,
    analysis_context_pack_to_dict,
    get_analysis_context_pack_block_labels,
    iter_analysis_context_pack_block_keys,
)
from src.application.market.phase_summary import MARKET_PHASE_SUMMARY_KEY
from src.domain.analysis.context_pack import ContextFieldStatus


ANALYSIS_CONTEXT_PACK_OVERVIEW_KEY = "analysis_context_pack_overview"
_ALL_STATUSES = tuple(status.value for status in ContextFieldStatus)
_DATA_QUALITY_BLOCK_KEYS = {"quote", "daily_bars", "technical", "news", "fundamentals", "chip"}
logger = logging.getLogger(__name__)


def render_analysis_context_pack_overview(
    pack: Any,
    *,
    report_language: str = "zh",
) -> Optional[Dict[str, Any]]:
    """Project an AnalysisContextPack into a public, low-sensitivity overview."""
    try:
        payload = analysis_context_pack_to_dict(pack)
        subject = payload.get("subject")
        blocks = payload.get("blocks")
        if not isinstance(subject, Mapping) or not isinstance(blocks, Mapping):
            return None

        labels = get_analysis_context_pack_block_labels(report_language)
        overview_blocks: List[Dict[str, Any]] = []
        counts = {status: 0 for status in _ALL_STATUSES}

        for key in iter_analysis_context_pack_block_keys(blocks):
            block = blocks.get(key)
            if not isinstance(block, Mapping):
                continue
            status = _safe_status(block.get("status"))
            if status is None:
                continue

            counts[status] += 1
            overview_blocks.append(
                {
                    "key": _safe_text(key),
                    "label": labels.get(key, _safe_text(key)),
                    "status": status,
                    "source": _first_non_empty(
                        block.get("source"),
                        _first_item_field(block.get("items"), "source"),
                    ),
                    "warnings": _list_strings(block.get("warnings")),
                    "missing_reasons": _item_missing_reasons(block.get("items")),
                }
            )

        if not overview_blocks:
            return None

        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {}
        return {
            "pack_version": _safe_text(payload.get("pack_version")) or "1.0",
            "created_at": _safe_text(payload.get("created_at")) or None,
            "subject": {
                "code": _safe_text(subject.get("code")),
                "stock_name": _safe_text(subject.get("stock_name")) or None,
                "market": _safe_text(subject.get("market")) or None,
            },
            "blocks": overview_blocks,
            "counts": counts,
            "data_quality": _sanitize_data_quality(payload.get("data_quality")),
            "warnings": _list_strings(_nested(payload, "data_quality", "warnings")),
            "metadata": {
                "trigger_source": _safe_text(metadata.get("trigger_source")) or None,
                "news_result_count": _safe_int(metadata.get("news_result_count")),
            },
        }
    except Exception as exc:
        logger.debug("render analysis context pack overview failed: %s", exc, exc_info=True)
        return None


def extract_analysis_context_pack_overview(context_snapshot: Any) -> Optional[Dict[str, Any]]:
    """Extract the persisted public overview from a context snapshot."""
    snapshot = _as_mapping(context_snapshot)
    if not snapshot:
        return None
    overview = snapshot.get(ANALYSIS_CONTEXT_PACK_OVERVIEW_KEY)
    if not isinstance(overview, Mapping):
        return None
    return _sanitize_persisted_overview(overview)


def sanitize_context_snapshot_for_api(context_snapshot: Any) -> Any:
    """Return a context snapshot without separately exposed public summary fields."""
    snapshot = _as_mapping(context_snapshot)
    if snapshot is not None:
        sanitized = dict(snapshot)
        sanitized.pop(ANALYSIS_CONTEXT_PACK_OVERVIEW_KEY, None)
        sanitized.pop(MARKET_PHASE_SUMMARY_KEY, None)
        sanitized.pop("daily_market_context_summary", None)
        sanitized.pop("portfolio_context", None)
        enhanced_context = sanitized.get("enhanced_context")
        if isinstance(enhanced_context, Mapping):
            safe_enhanced_context = dict(enhanced_context)
            safe_enhanced_context.pop("daily_market_context_summary", None)
            safe_enhanced_context.pop("portfolio_context", None)
            sanitized["enhanced_context"] = safe_enhanced_context
        return sanitized
    return context_snapshot


def _as_mapping(value: Any) -> Optional[Mapping[str, Any]]:
    """将值规范为 Mapping：已为 Mapping 直接返回；字符串尝试 JSON 解析为对象（否则 None）；其余返回 None。"""
    if isinstance(value, Mapping):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError, ValueError):
            return None
        return parsed if isinstance(parsed, Mapping) else None
    return None


def _sanitize_persisted_overview(overview: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """校验并清洗已持久化的公开概览：要求 subject 为 Mapping、blocks 为列表且含合法 key/status，重建标准化概览（含可选 data_quality）；不合法则返回 None。"""
    subject = overview.get("subject")
    blocks = overview.get("blocks")
    if not isinstance(subject, Mapping) or not isinstance(blocks, list):
        return None

    subject_code = _safe_text(subject.get("code"))
    if not subject_code:
        return None

    overview_blocks: List[Dict[str, Any]] = []
    counts = {status: 0 for status in _ALL_STATUSES}
    for block in blocks:
        if not isinstance(block, Mapping):
            return None

        key = _safe_text(block.get("key"))
        status = _safe_status(block.get("status"))
        if not key or status is None:
            return None

        counts[status] += 1
        overview_blocks.append(
            {
                "key": key,
                "label": _safe_text(block.get("label")) or key,
                "status": status,
                "source": _safe_text(block.get("source")) or None,
                "warnings": _list_strings(block.get("warnings")),
                "missing_reasons": _list_strings(block.get("missing_reasons"), limit=3),
            }
        )

    if not overview_blocks:
        return None

    metadata = overview.get("metadata") if isinstance(overview.get("metadata"), Mapping) else {}
    sanitized = {
        "pack_version": _safe_text(overview.get("pack_version")) or "1.0",
        "created_at": _safe_text(overview.get("created_at")) or None,
        "subject": {
            "code": subject_code,
            "stock_name": _safe_text(subject.get("stock_name")) or None,
            "market": _safe_text(subject.get("market")) or None,
        },
        "blocks": overview_blocks,
        "counts": counts,
        "warnings": _list_strings(overview.get("warnings")),
        "metadata": {
            "trigger_source": _safe_text(metadata.get("trigger_source")) or None,
            "news_result_count": _safe_int(metadata.get("news_result_count")),
        },
    }
    if "data_quality" in overview:
        sanitized["data_quality"] = _sanitize_data_quality(overview.get("data_quality"))
    return sanitized


def _sanitize_data_quality(value: Any) -> Optional[Dict[str, Any]]:
    """清洗数据质量片段：取 overall_score（0–100 整数）、level、block_scores（仅限已知块键）与 limitations（截断 5 条），非 Mapping 返回 None。"""
    if not isinstance(value, Mapping):
        return None
    return {
        "overall_score": _safe_score(value.get("overall_score")),
        "level": _safe_quality_level(value.get("level")),
        "block_scores": _safe_block_scores(value.get("block_scores")),
        "limitations": _list_strings(value.get("limitations"), limit=5),
    }


def _safe_status(value: Any) -> Optional[str]:
    """将值安全化为合法的 ContextFieldStatus 字符串；经 _safe_text 脱敏后不在枚举集合内则返回 None。"""
    text = _safe_text(value)
    return text if text in _ALL_STATUSES else None


def _safe_quality_level(value: Any) -> Optional[str]:
    """将值安全化为合法的质量等级（good/usable/limited/poor）；非集合内返回 None。"""
    text = _safe_text(value)
    return text if text in {"good", "usable", "limited", "poor"} else None


def _safe_score(value: Any) -> Optional[int]:
    """安全化为 0–100 的整数分数；bool 或非 int 或越界返回 None。"""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if 0 <= value <= 100:
        return value
    return None


def _safe_block_scores(value: Any) -> Dict[str, int]:
    """清洗各块得分：仅保留键属于已知数据质量块（quote/daily_bars/...）且分值合法的整数字典。"""
    if not isinstance(value, Mapping):
        return {}
    result: Dict[str, int] = {}
    for key, score in value.items():
        text_key = _safe_text(key)
        safe_score = _safe_score(score)
        if text_key in _DATA_QUALITY_BLOCK_KEYS and safe_score is not None:
            result[text_key] = safe_score
    return result


def _safe_text(value: Any) -> str:
    """安全化为字符串：None/空返回空串；若含敏感标记（SENSITIVE_MARKERS）则返回 [REDACTED]，否则返回去空白文本。"""
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    lowered = text.lower()
    if any(marker in lowered for marker in SENSITIVE_MARKERS):
        return "[REDACTED]"
    return text


def _list_strings(value: Any, *, limit: int = 5) -> List[str]:
    """将列表元素安全化为去重字符串列表，最多保留 limit 条（默认 5），跳过空值与已出现项。"""
    if not isinstance(value, list):
        return []
    result: List[str] = []
    for item in value:
        text = _safe_text(item)
        if text and text not in result:
            result.append(text)
    return result[:limit]


def _first_non_empty(*values: Any) -> Optional[str]:
    """返回首个经 _safe_text 后非空的值；全部为空返回 None。"""
    for value in values:
        text = _safe_text(value)
        if text:
            return text
    return None


def _first_item_field(items: Any, field: str) -> Optional[str]:
    """从 items（Mapping）各条目中取首个字段 field 的非空安全化文本；非 Mapping 或全空返回 None。"""
    if not isinstance(items, Mapping):
        return None
    for item in items.values():
        if not isinstance(item, Mapping):
            continue
        value = _safe_text(item.get(field))
        if value:
            return value
    return None


def _item_missing_reasons(items: Any) -> List[str]:
    """收集各条目中的 missing_reason（去重、安全化），最多返回前 3 条。"""
    if not isinstance(items, Mapping):
        return []
    reasons: List[str] = []
    for item in items.values():
        if not isinstance(item, Mapping):
            continue
        reason = _safe_text(item.get("missing_reason"))
        if reason and reason not in reasons:
            reasons.append(reason)
    return reasons[:3]


def _nested(value: Any, *keys: str) -> Any:
    """按 keys 链逐层取嵌套值；任一层非 Mapping 则返回 None。"""
    current = value
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _safe_int(value: Any) -> Optional[int]:
    """安全化为 int（bool 视为非法返回 None）；非 int 返回 None。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None
