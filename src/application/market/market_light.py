# -*- coding: utf-8 -*-
"""Market Light snapshot use case for structured alerts（市场域）。

分层说明：本用例为函数式模块。`load_previous_snapshot` 通过注入的
:class:`MarketLightSnapshotRepositoryPort` 读取历史快照，不直接依赖
``src.storage`` 或具体仓储实现——与同域 limit_pool / sector 一致，只依赖 端口。
具体 :class:`~src.infrastructure.persistence.repositories.analysis_repository.AnalysisRepository` 由
``src.bootstrap.market.build_market_light_snapshot_repository`` 装配，调用方注入。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from src.application.market.ports import MarketLightSnapshotRepositoryPort
from src.application.market.market_analyzer import MarketAnalyzer
from src.domain.market.light import MarketLightSnapshot


logger = logging.getLogger(__name__)

MARKET_LIGHT_REGIONS = frozenset({"cn", "hk", "us", "jp", "kr"})
MARKET_LIGHT_ALERT_REGIONS = frozenset({"cn", "hk", "us"})


def normalize_market_region(region: str) -> str:
    value = str(region or "").strip().lower()
    if value not in MARKET_LIGHT_REGIONS:
        raise ValueError(f"market target must be one of cn, hk, us, jp, kr: {region}")
    return value


def normalize_market_alert_region(region: str) -> str:
    value = str(region or "").strip().lower()
    if value not in MARKET_LIGHT_ALERT_REGIONS:
        raise ValueError(f"market alert target must be one of cn, hk, us: {region}")
    return value


def build_current_snapshot(region: str) -> Dict[str, Any]:
    """Build the current structured Market Light snapshot without LLM review."""

    normalized_region = normalize_market_region(region)
    analyzer = MarketAnalyzer(region=normalized_region)
    overview = analyzer.get_market_overview()
    return analyzer.build_market_light_snapshot(overview)


def load_previous_snapshot(
    region: str,
    *,
    before_trade_date: str,
    repository: MarketLightSnapshotRepositoryPort,
    limit: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Load the latest persisted Market Light snapshot before ``before_trade_date``.

    Legacy market-review history rows without ``market_light_snapshots[region]`` are
    skipped while scanning newer rows.
    """

    normalized_region = normalize_market_region(region)
    cutoff = str(before_trade_date or "").strip()
    if not cutoff:
        return None

    best_trade_date: Optional[str] = None
    best_snapshot: Optional[Dict[str, Any]] = None
    invalid_target_error: Optional[Exception] = None

    for row_id, raw_context_snapshot in repository.iter_market_review_snapshot_payloads(
        limit=limit
    ):
        snapshot = _extract_region_snapshot(raw_context_snapshot, normalized_region)
        if snapshot is None:
            continue
        trade_date = str(snapshot.get("trade_date") or "").strip()
        if not trade_date or trade_date >= cutoff:
            continue
        if best_trade_date is None or trade_date > best_trade_date:
            best_trade_date = trade_date
            best_snapshot = None
            invalid_target_error = None
        elif trade_date < best_trade_date:
            continue
        try:
            candidate = MarketLightSnapshot.model_validate(snapshot).model_dump()
        except Exception as exc:
            logger.warning(
                "invalid persisted market light snapshot: row_id=%s region=%s trade_date=%s error=%s",
                row_id,
                normalized_region,
                trade_date,
                exc,
            )
            if best_snapshot is None:
                invalid_target_error = exc
            continue
        if best_snapshot is None:
            best_snapshot = candidate

    if best_snapshot is not None:
        return best_snapshot
    if best_trade_date is not None and invalid_target_error is not None:
        raise ValueError(
            f"invalid persisted market light snapshot for {normalized_region} on {best_trade_date}"
        ) from invalid_target_error
    return None


def _extract_region_snapshot(raw_context_snapshot: Any, region: str) -> Optional[Dict[str, Any]]:
    if not raw_context_snapshot:
        return None
    try:
        payload = (
            json.loads(raw_context_snapshot)
            if isinstance(raw_context_snapshot, str)
            else raw_context_snapshot
        )
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    snapshots = payload.get("market_light_snapshots")
    if not isinstance(snapshots, dict):
        return None
    snapshot = snapshots.get(region)
    return snapshot if isinstance(snapshot, dict) else None
