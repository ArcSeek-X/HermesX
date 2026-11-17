# -*- coding: utf-8 -*-
"""Capture immutable, low-sensitivity skill opinion samples.

捕获不可变、低敏感度的技能意见样本。负责校验并存持久化样本；
（事后收益评估不在本服务职责内，由 skill_opinion_outcome_service 负责）。
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from src.application.agent.protocols import normalize_strategy_signal
from src.application.agent.runtime_facts import SkillOpinionFact
from src.application.decision.ports import (
    SkillOpinionSampleRepositoryPort,
    get_skill_opinion_sample_repository,
)


SKILL_OPINION_SAMPLE_SCHEMA_VERSION = "skill-opinion-sample-v1"
_QUALITY_LEVELS = frozenset({"good", "usable", "limited", "poor"})


class SkillOpinionSampleService:
    """Validate and persist samples; outcome evaluation is intentionally out of scope."""

    def __init__(
        self,
        db_manager: Optional[Any] = None,
        repo: Optional[SkillOpinionSampleRepositoryPort] = None,
    ):
        """构造服务：持有（或默认创建）样本仓储。"""
        self.repo = repo or get_skill_opinion_sample_repository(db_manager)

    def persist(
        self,
        *,
        analysis_history_id: int,
        stock_code: str,
        opinions: Iterable[SkillOpinionFact],
        data_quality_level: Optional[str] = None,
    ) -> int:
        """校验并持久化技能意见样本：归一化 history_id/stock_code/skill_id/signal/confidence，去重插入缺失样本并返回插入数。"""
        try:
            normalized_history_id = int(analysis_history_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("analysis_history_id must be a positive integer") from exc
        if isinstance(analysis_history_id, bool) or normalized_history_id <= 0:
            raise ValueError("analysis_history_id must be a positive integer")
        normalized_code = str(stock_code or "").strip()
        if not normalized_code:
            raise ValueError("stock_code is required")
        if len(normalized_code) > 16:
            raise ValueError("stock_code exceeds 16 characters")

        quality = str(data_quality_level or "").strip().lower()
        if quality not in _QUALITY_LEVELS:
            quality = None

        rows = []
        for opinion in opinions:
            skill_id = str(opinion.skill_id or "").strip()
            signal, invalid, _ = normalize_strategy_signal(opinion.signal)
            if not skill_id or invalid:
                raise ValueError("skill opinion requires a valid skill_id and signal")
            if len(skill_id) > 128:
                raise ValueError("skill_id exceeds 128 characters")
            if isinstance(opinion.confidence, bool):
                raise ValueError("skill opinion confidence must be numeric")
            try:
                confidence = float(opinion.confidence)
            except (OverflowError, TypeError, ValueError) as exc:
                raise ValueError("skill opinion confidence must be numeric") from exc
            if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
                raise ValueError("skill opinion confidence must be between 0 and 1")
            rows.append(
                {
                    "analysis_history_id": normalized_history_id,
                    "stock_code": normalized_code,
                    "skill_id": skill_id,
                    "skill_version": _optional_text(opinion.skill_version, 64),
                    "signal": signal,
                    "confidence": confidence,
                    "horizon": _optional_text(opinion.horizon, 16),
                    "data_quality_level": quality,
                    "opinion_created_at": _timestamp_to_datetime(opinion.observed_at),
                    "sample_schema_version": SKILL_OPINION_SAMPLE_SCHEMA_VERSION,
                }
            )
        return self.repo.insert_missing(rows) if rows else 0


def _optional_text(value: object, max_length: int) -> Optional[str]:
    """将值安全化为最多 max_length 的字符串；空白/空返回 None。"""
    text = str(value or "").strip()
    return text[:max_length] if text else None


def _timestamp_to_datetime(value: Optional[float]) -> Optional[datetime]:
    """将正有限时间戳转为无时区的 UTC datetime；非法或越界返回 None。"""
    if value is None:
        return None
    try:
        timestamp = float(value)
        if not math.isfinite(timestamp) or timestamp <= 0:
            return None
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(tzinfo=None)
    except (OverflowError, OSError, TypeError, ValueError):
        return None
