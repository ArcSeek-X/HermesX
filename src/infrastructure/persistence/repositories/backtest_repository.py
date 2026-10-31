# -*- coding: utf-8 -*-
"""Backtest repository.

Provides database access helpers for backtest tables.

端口实现：本类满足 :class:`src.application.backtest.ports.BacktestRepositoryPort`，由
``bootstrap.backtest`` 注入回测用例；于 P3/P4 持久化收口 PP-6 从
``src/repositories/backtest_repo.py`` 下沉到本包，类名保持不变。
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import and_, delete, desc, func, or_, select

from src.domain.backtest.engine import OVERALL_SENTINEL_CODE
from src.application.quote.stock_code_utils import resolve_daily_stock_identity

from src.storage import DatabaseManager
from src.domain.analysis.analysis_context_snapshot import (
    parse_analysis_date_from_snapshot as _parse_analysis_date_from_snapshot,
)
from src.domain.backtest import BacktestResultRecord, BacktestSummaryRecord
from src.infrastructure.persistence.models.analysis import AnalysisHistory, BacktestResult, BacktestSummary

logger = logging.getLogger(__name__)

MARKET_REVIEW_REPORT_TYPE = "market_review"
BacktestResultContextRow = Tuple[
    BacktestResult,
    Optional[str],
    Optional[str],
    Optional[datetime],
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[int],
]


def _to_result_record(row: BacktestResult) -> BacktestResultRecord:
    """ORM -> 领域记录（读路径）。须在会话内调用，避免惰性加载失效。"""
    return BacktestResultRecord(
        id=row.id,
        analysis_history_id=row.analysis_history_id,
        code=row.code,
        analysis_date=row.analysis_date,
        eval_window_days=row.eval_window_days,
        engine_version=row.engine_version,
        eval_status=row.eval_status,
        evaluated_at=row.evaluated_at,
        operation_advice=row.operation_advice,
        position_recommendation=row.position_recommendation,
        start_price=row.start_price,
        end_close=row.end_close,
        max_high=row.max_high,
        min_low=row.min_low,
        stock_return_pct=row.stock_return_pct,
        direction_expected=row.direction_expected,
        direction_correct=row.direction_correct,
        outcome=row.outcome,
        stop_loss=row.stop_loss,
        take_profit=row.take_profit,
        hit_stop_loss=row.hit_stop_loss,
        hit_take_profit=row.hit_take_profit,
        first_hit=row.first_hit,
        first_hit_date=row.first_hit_date,
        first_hit_trading_days=row.first_hit_trading_days,
        simulated_entry_price=row.simulated_entry_price,
        simulated_exit_price=row.simulated_exit_price,
        simulated_exit_reason=row.simulated_exit_reason,
        simulated_return_pct=row.simulated_return_pct,
    )


def _to_summary_record(row: BacktestSummary) -> BacktestSummaryRecord:
    """ORM -> 领域记录（读路径）。须在会话内调用，避免惰性加载失效。"""
    return BacktestSummaryRecord(
        id=row.id,
        scope=row.scope,
        code=row.code,
        eval_window_days=row.eval_window_days,
        engine_version=row.engine_version,
        computed_at=row.computed_at,
        total_evaluations=row.total_evaluations,
        completed_count=row.completed_count,
        insufficient_count=row.insufficient_count,
        long_count=row.long_count,
        cash_count=row.cash_count,
        win_count=row.win_count,
        loss_count=row.loss_count,
        neutral_count=row.neutral_count,
        direction_accuracy_pct=row.direction_accuracy_pct,
        win_rate_pct=row.win_rate_pct,
        neutral_rate_pct=row.neutral_rate_pct,
        avg_stock_return_pct=row.avg_stock_return_pct,
        avg_simulated_return_pct=row.avg_simulated_return_pct,
        stop_loss_trigger_rate=row.stop_loss_trigger_rate,
        take_profit_trigger_rate=row.take_profit_trigger_rate,
        ambiguous_rate=row.ambiguous_rate,
        avg_days_to_first_hit=row.avg_days_to_first_hit,
        advice_breakdown_json=row.advice_breakdown_json,
        diagnostics_json=row.diagnostics_json,
    )


def _map_context_row(row: tuple) -> tuple:
    """上下文联合查询行 (BacktestResult, *analysis_cols) -> (Record, *analysis_cols)。"""
    return (_to_result_record(row[0]),) + tuple(row[1:])


def _to_result_orm(record: BacktestResultRecord) -> BacktestResult:
    """领域记录 -> ORM（写路径）。

    按 ``BacktestResult.__table__`` 当前列集动态取属性构造 ORM 新行：领域记录
    字段集合与 ORM 列严格一致由 ``tests/test_backtest_domain_records.py`` 锁死，
    未来加列时若记录未同步会先在该契约测试上失败，不会静默漏写。
    """
    values = {col: getattr(record, col) for col in BacktestResult.__table__.columns.keys()}
    return BacktestResult(**values)


def _to_summary_orm(record: BacktestSummaryRecord) -> BacktestSummary:
    """领域记录 -> ORM（写路径，仅用于新增分支；更新分支按属性回写到已有序行）。"""
    values = {col: getattr(record, col) for col in BacktestSummary.__table__.columns.keys()}
    return BacktestSummary(**values)


class BacktestRepository:
    """DB access layer for backtesting."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager.get_instance()

    def get_candidates(
        self,
        *,
        code: Optional[str],
        min_age_days: int,
        limit: int,
        offset: int = 0,
        eval_window_days: int,
        engine_version: str,
        force: bool,
    ) -> List[AnalysisHistory]:
        """Return AnalysisHistory rows eligible for backtest."""
        cutoff_dt = datetime.now() - timedelta(days=min_age_days)

        with self.db.get_session() as session:
            conditions = [AnalysisHistory.created_at <= cutoff_dt]
            if code:
                conditions.extend(self._build_code_conditions(AnalysisHistory.code, code))
            conditions.append(
                or_(
                    AnalysisHistory.report_type.is_(None),
                    AnalysisHistory.report_type != MARKET_REVIEW_REPORT_TYPE,
                )
            )

            query = select(AnalysisHistory).where(and_(*conditions))

            if not force:
                existing_ids = select(BacktestResult.analysis_history_id).where(
                    and_(
                        BacktestResult.eval_window_days == eval_window_days,
                        BacktestResult.engine_version == engine_version,
                    )
                )
                query = query.where(AnalysisHistory.id.not_in(existing_ids))

            query = query.order_by(desc(AnalysisHistory.created_at)).offset(offset).limit(limit)
            rows = session.execute(query).scalars().all()
            return list(rows)

    def align_existing_result_dates(
        self,
        *,
        code: Optional[str],
        min_age_days: int,
        eval_window_days: int,
        engine_version: str,
        analysis_date_from: Optional[date],
        analysis_date_to: Optional[date],
    ) -> int:
        """Align legacy result dates to their linked analysis snapshot date.

        Older backtest rows may have stored the trading/start daily date instead
        of the historical analysis snapshot date. When a date-filtered run skips
        already-existing rows, those legacy rows would remain invisible to the
        same date-filtered result query. Updating the stored result date keeps
        rerun and query semantics aligned without inserting duplicate rows.
        """
        cutoff_dt = datetime.now() - timedelta(days=min_age_days)

        with self.db.get_session() as session:
            conditions = [
                AnalysisHistory.created_at <= cutoff_dt,
                BacktestResult.eval_window_days == eval_window_days,
                BacktestResult.engine_version == engine_version,
                or_(
                    AnalysisHistory.report_type.is_(None),
                    AnalysisHistory.report_type != MARKET_REVIEW_REPORT_TYPE,
                ),
            ]
            if code:
                conditions.extend(self._build_code_conditions(AnalysisHistory.code, code))

            rows = session.execute(
                select(BacktestResult, AnalysisHistory)
                .join(AnalysisHistory, AnalysisHistory.id == BacktestResult.analysis_history_id)
                .where(and_(*conditions))
            ).all()

            updated = 0
            for result, analysis in rows:
                analysis_date = self.parse_analysis_date_from_snapshot(analysis.context_snapshot)
                if analysis_date is None and analysis.created_at is not None:
                    analysis_date = analysis.created_at.date()
                if analysis_date is None:
                    continue
                if analysis_date_from is not None and analysis_date < analysis_date_from:
                    continue
                if analysis_date_to is not None and analysis_date > analysis_date_to:
                    continue
                if result.analysis_date != analysis_date:
                    result.analysis_date = analysis_date
                    updated += 1

            if updated:
                session.commit()
            return updated

    def save_result(self, result: BacktestResultRecord) -> None:
        with self.db.get_session() as session:
            session.add(_to_result_orm(result))
            session.commit()

    def save_results_batch(self, results: List[BacktestResultRecord], *, replace_existing: bool = False) -> int:
        if not results:
            return 0

        with self.db.get_session() as session:
            try:
                if replace_existing:
                    analysis_ids = sorted({r.analysis_history_id for r in results if r.analysis_history_id is not None})
                    key_pairs = sorted({(r.eval_window_days, r.engine_version) for r in results})

                    if analysis_ids and key_pairs:
                        for window_days, engine_version in key_pairs:
                            session.execute(
                                delete(BacktestResult).where(
                                    and_(
                                        BacktestResult.analysis_history_id.in_(analysis_ids),
                                        BacktestResult.eval_window_days == window_days,
                                        BacktestResult.engine_version == engine_version,
                                    )
                                )
                            )

                session.add_all([_to_result_orm(record) for record in results])
                session.commit()
                return len(results)
            except Exception as exc:
                session.rollback()
                logger.error(f"批量保存回测结果失败: {exc}")
                raise

    def get_results_paginated(
        self,
        *,
        code: Optional[str],
        eval_window_days: Optional[int] = None,
        engine_version: Optional[str] = None,
        analysis_date_from: Optional[date] = None,
        analysis_date_to: Optional[date] = None,
        days: Optional[int],
        offset: int,
        limit: int,
    ) -> Tuple[List[BacktestResultContextRow], int]:  # rows carry BacktestResultRecord
        with self.db.get_session() as session:
            conditions = self._build_result_conditions(
                code=code,
                eval_window_days=eval_window_days,
                engine_version=engine_version,
                analysis_date_from=analysis_date_from,
                analysis_date_to=analysis_date_to,
                days=days,
            )

            where_clause = and_(*conditions) if conditions else True

            total = session.execute(
                select(func.count(BacktestResult.id))
                .select_from(BacktestResult)
                .join(AnalysisHistory, AnalysisHistory.id == BacktestResult.analysis_history_id)
                .where(where_clause)
            ).scalar() or 0
            rows = session.execute(
                select(
                    BacktestResult,
                    AnalysisHistory.name,
                    AnalysisHistory.trend_prediction,
                    AnalysisHistory.created_at,
                    AnalysisHistory.context_snapshot,
                    AnalysisHistory.raw_result,
                    AnalysisHistory.report_type,
                    AnalysisHistory.sentiment_score,
                )
                .join(AnalysisHistory, AnalysisHistory.id == BacktestResult.analysis_history_id)
                .where(where_clause)
                .order_by(desc(BacktestResult.analysis_date), desc(BacktestResult.evaluated_at))
                .offset(offset)
                .limit(limit)
            ).all()
            return [_map_context_row(row) for row in rows], int(total)

    def get_results_with_context_batch(
        self,
        *,
        code: Optional[str],
        eval_window_days: Optional[int] = None,
        engine_version: Optional[str] = None,
        analysis_date_from: Optional[date] = None,
        analysis_date_to: Optional[date] = None,
        days: Optional[int],
        offset: int,
        limit: int,
    ) -> List[BacktestResultContextRow]:  # rows carry BacktestResultRecord
        """Return result rows plus AnalysisHistory.context_snapshot for dynamic filtering."""
        with self.db.get_session() as session:
            conditions = self._build_result_conditions(
                code=code,
                eval_window_days=eval_window_days,
                engine_version=engine_version,
                analysis_date_from=analysis_date_from,
                analysis_date_to=analysis_date_to,
                days=days,
            )
            where_clause = and_(*conditions) if conditions else True
            rows = session.execute(
                select(
                    BacktestResult,
                    AnalysisHistory.name,
                    AnalysisHistory.trend_prediction,
                    AnalysisHistory.created_at,
                    AnalysisHistory.context_snapshot,
                    AnalysisHistory.raw_result,
                    AnalysisHistory.report_type,
                    AnalysisHistory.sentiment_score,
                )
                .join(AnalysisHistory, AnalysisHistory.id == BacktestResult.analysis_history_id)
                .where(where_clause)
                .order_by(desc(BacktestResult.analysis_date), desc(BacktestResult.evaluated_at))
                .offset(offset)
                .limit(limit)
            ).all()
            return [_map_context_row(row) for row in rows]

    def list_results_with_context(
        self,
        *,
        code: Optional[str],
        eval_window_days: Optional[int] = None,
        engine_version: Optional[str] = None,
        analysis_date_from: Optional[date] = None,
        analysis_date_to: Optional[date] = None,
        days: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Tuple["BacktestResultRecord", Optional[str]]]:
        with self.db.get_session() as session:
            conditions = self._build_result_conditions(
                code=code,
                eval_window_days=eval_window_days,
                engine_version=engine_version,
                analysis_date_from=analysis_date_from,
                analysis_date_to=analysis_date_to,
                days=days,
            )
            where_clause = and_(*conditions) if conditions else True
            query = (
                select(BacktestResult, AnalysisHistory.context_snapshot)
                .join(AnalysisHistory, AnalysisHistory.id == BacktestResult.analysis_history_id)
                .where(where_clause)
                .order_by(desc(BacktestResult.analysis_date), desc(BacktestResult.evaluated_at))
            )
            if limit is not None:
                query = query.limit(limit)
            rows = session.execute(query).all()
            return [(_to_result_record(row[0]), row[1]) for row in rows]

    def count_results(
        self,
        *,
        code: Optional[str],
        eval_window_days: Optional[int] = None,
        engine_version: Optional[str] = None,
        analysis_date_from: Optional[date] = None,
        analysis_date_to: Optional[date] = None,
        days: Optional[int] = None,
    ) -> int:
        """Return the number of matching BacktestResult rows without loading them."""
        with self.db.get_session() as session:
            conditions = self._build_result_conditions(
                code=code,
                eval_window_days=eval_window_days,
                engine_version=engine_version,
                analysis_date_from=analysis_date_from,
                analysis_date_to=analysis_date_to,
                days=days,
            )
            where_clause = and_(*conditions) if conditions else True
            count = session.execute(
                select(func.count(BacktestResult.id))
                .select_from(BacktestResult)
                .where(where_clause)
            ).scalar() or 0
            return int(count)

    def list_results_for_recompute(
        self,
        *,
        code: Optional[str],
        eval_window_days: int,
        engine_version: str,
    ) -> List[BacktestResultRecord]:
        """Return raw rows for summary recomputation.

        ``BacktestService._recompute_summaries`` used to open its own session and
        build ``select``/``and_`` expressions directly, which kept ``sqlalchemy``
        in the service layer and reached into ``_build_code_conditions`` across
        the layer boundary. ``code=None`` means the overall scope (no code
        filtering), matching the previous overall-scope query.
        """
        with self.db.get_session() as session:
            conditions: List[object] = [
                BacktestResult.eval_window_days == eval_window_days,
                BacktestResult.engine_version == engine_version,
            ]
            if code:
                conditions.extend(self._build_code_conditions(BacktestResult.code, code))
            rows = session.execute(
                select(BacktestResult).where(and_(*conditions))
            ).scalars().all()
            return [_to_result_record(row) for row in rows]

    def list_results(
        self,
        *,
        code: Optional[str],
        eval_window_days: Optional[int] = None,
        engine_version: Optional[str] = None,
        analysis_date_from: Optional[date] = None,
        analysis_date_to: Optional[date] = None,
        days: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[BacktestResultRecord]:
        with self.db.get_session() as session:
            conditions = self._build_result_conditions(
                code=code,
                eval_window_days=eval_window_days,
                engine_version=engine_version,
                analysis_date_from=analysis_date_from,
                analysis_date_to=analysis_date_to,
                days=days,
            )
            where_clause = and_(*conditions) if conditions else True
            query = (
                select(BacktestResult)
                .where(where_clause)
                .order_by(desc(BacktestResult.analysis_date), desc(BacktestResult.evaluated_at))
            )
            if limit is not None:
                query = query.limit(limit)
            rows = session.execute(query).scalars().all()
            return [_to_result_record(row) for row in rows]

    def upsert_summary(self, summary: BacktestSummaryRecord) -> None:
        """Insert or replace summary row by unique key."""
        with self.db.get_session() as session:
            existing = session.execute(
                select(BacktestSummary)
                .where(
                    and_(
                        BacktestSummary.scope == summary.scope,
                        BacktestSummary.code == summary.code,
                        BacktestSummary.eval_window_days == summary.eval_window_days,
                        BacktestSummary.engine_version == summary.engine_version,
                    )
                )
                .limit(1)
            ).scalar_one_or_none()

            if existing:
                for attr in (
                    "computed_at",
                    "total_evaluations",
                    "completed_count",
                    "insufficient_count",
                    "long_count",
                    "cash_count",
                    "win_count",
                    "loss_count",
                    "neutral_count",
                    "direction_accuracy_pct",
                    "win_rate_pct",
                    "neutral_rate_pct",
                    "avg_stock_return_pct",
                    "avg_simulated_return_pct",
                    "stop_loss_trigger_rate",
                    "take_profit_trigger_rate",
                    "ambiguous_rate",
                    "avg_days_to_first_hit",
                    "advice_breakdown_json",
                    "diagnostics_json",
                ):
                    setattr(existing, attr, getattr(summary, attr))
                session.commit()
                return

            session.add(_to_summary_orm(summary))
            session.commit()

    def get_summary(
        self,
        *,
        scope: str,
        code: Optional[str],
        eval_window_days: Optional[int] = None,
        engine_version: str,
    ) -> Optional[BacktestSummaryRecord]:
        with self.db.get_session() as session:
            conditions = [
                BacktestSummary.scope == scope,
                BacktestSummary.engine_version == engine_version,
            ]
            if code:
                conditions.extend(self._build_code_conditions(BacktestSummary.code, code))
            if eval_window_days is not None:
                conditions.append(BacktestSummary.eval_window_days == eval_window_days)

            row = session.execute(
                select(BacktestSummary)
                .where(and_(*conditions))
                .order_by(desc(BacktestSummary.computed_at))
                .limit(1)
            ).scalar_one_or_none()
            return _to_summary_record(row) if row is not None else None

    @staticmethod
    def parse_analysis_date_from_snapshot(context_snapshot: Optional[str]) -> Optional[date]:
        """兼容入口：解析实现已下沉到
        :func:`src.domain.analysis.analysis_context_snapshot.parse_analysis_date_from_snapshot`。"""
        return _parse_analysis_date_from_snapshot(context_snapshot)

    def get_distinct_eval_windows(
        self,
        *,
        code: Optional[str],
        engine_version: Optional[str] = None,
        analysis_date_from: Optional[date] = None,
        analysis_date_to: Optional[date] = None,
    ) -> List[int]:
        """Return sorted distinct eval_window_days for matching results."""
        with self.db.get_session() as session:
            conditions = self._build_result_conditions(
                code=code,
                eval_window_days=None,
                engine_version=engine_version,
                analysis_date_from=analysis_date_from,
                analysis_date_to=analysis_date_to,
                days=None,
            )
            where_clause = and_(*conditions) if conditions else True
            rows = session.execute(
                select(BacktestResult.eval_window_days)
                .where(where_clause)
                .distinct()
                .order_by(BacktestResult.eval_window_days)
            ).scalars().all()
            return [int(w) for w in rows if w is not None]

    @staticmethod
    def _build_result_conditions(
        *,
        code: Optional[str],
        eval_window_days: Optional[int],
        engine_version: Optional[str],
        analysis_date_from: Optional[date],
        analysis_date_to: Optional[date],
        days: Optional[int],
    ) -> List[object]:
        conditions = []
        if code:
            conditions.extend(BacktestRepository._build_code_conditions(BacktestResult.code, code))
        if eval_window_days is not None:
            conditions.append(BacktestResult.eval_window_days == eval_window_days)
        if engine_version:
            conditions.append(BacktestResult.engine_version == engine_version)
        if analysis_date_from is not None:
            conditions.append(BacktestResult.analysis_date >= analysis_date_from)
        if analysis_date_to is not None:
            conditions.append(BacktestResult.analysis_date <= analysis_date_to)
        if days:
            cutoff = datetime.now() - timedelta(days=int(days))
            conditions.append(BacktestResult.evaluated_at >= cutoff)
        return conditions

    @staticmethod
    def _build_code_conditions(column, code: str) -> List[object]:
        if not code:
            return []

        raw_code = str(code).strip()
        if raw_code.lower() == OVERALL_SENTINEL_CODE.lower():
            raw_code = OVERALL_SENTINEL_CODE
        else:
            raw_code = raw_code.upper()

        if raw_code == OVERALL_SENTINEL_CODE:
            candidates = [OVERALL_SENTINEL_CODE]
        else:
            identity = resolve_daily_stock_identity(raw_code)
            candidates = list(identity.code_candidates) if identity is not None else []
        if not candidates:
            return [column.in_([])]

        if len(candidates) == 1:
            return [column == candidates[0]]

        unique = list(dict.fromkeys(candidates))
        return [or_(*[column == candidate for candidate in unique])]
