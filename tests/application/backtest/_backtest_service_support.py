# -*- coding: utf-8 -*-
# 本文件主要测试：测试backtest服务相关功能
"""Integration tests for backtest service and repository.

These tests run against a temporary SQLite DB (same approach as other tests)
and validate idempotency/force semantics, result field correctness,
summary creation, and query methods.
"""

import json
import os
import tempfile
import unittest
from datetime import date, datetime
from unittest.mock import patch

import pandas as pd

from src.config import Config
from src.domain.backtest.engine import OVERALL_SENTINEL_CODE
from src.infrastructure.persistence.repositories.backtest_repository import BacktestRepository
from src.infrastructure.persistence.repositories.stock_repository import StockRepository
from src.application.backtest.service import BacktestService
from src.storage import DatabaseManager
from src.infrastructure.persistence.models.analysis import AnalysisHistory, BacktestResult, BacktestSummary
from src.infrastructure.persistence.models.market_data import StockDaily


def _phase_snapshot(
    analysis_date: date,
    *,
    phase: str,
    market: str,
    effective_date: date | str | None = None,
    trigger_source: str | None = None,
) -> str:
    summary = {"phase": phase, "market": market}
    if effective_date is not None:
        summary["effective_daily_bar_date"] = (
            effective_date.isoformat()
            if isinstance(effective_date, date)
            else str(effective_date)
        )
    if trigger_source is not None:
        summary["trigger_source"] = trigger_source
    return json.dumps(
        {
            "enhanced_context": {"date": analysis_date.isoformat()},
            "market_phase_summary": summary,
        }
    )


class _RecordingDailyRefill:
    """``DailyBarRefillPort`` 的测试替身，记录调用参数并可控抛错。"""

    def __init__(self, raise_exc=None):
        self.calls = []
        self._raise = raise_exc

    def refill(self, *, code, start_date, end_date, days):
        self.calls.append(
            {"code": code, "start_date": start_date, "end_date": end_date, "days": days}
        )
        if self._raise is not None:
            raise self._raise


class _BacktestServiceTestCaseFixture:
    def _service(self, daily_refill=None):
        # 用例层只接收端口对象；这里用真实仓储绑定测试库复现原 BacktestService(db) 的行为。
        return BacktestService(
            backtest_repository=BacktestRepository(self.db),
            stock_repository=StockRepository(self.db),
            daily_refill=daily_refill,
        )
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._db_path = os.path.join(self._temp_dir.name, "test_backtest_service.db")
        self._original_env = {
            key: os.environ.get(key)
            for key in (
                "ENV_FILE",
                "DATABASE_PATH",
                "BACKTEST_EVAL_WINDOW_DAYS",
            )
        }
        self._env_path = os.path.join(self._temp_dir.name, ".env")
        with open(self._env_path, "w", encoding="utf-8") as env_file:
            env_file.write("STOCK_LIST=600519,000001\n")

        os.environ["ENV_FILE"] = self._env_path
        os.environ["DATABASE_PATH"] = self._db_path
        os.environ["BACKTEST_EVAL_WINDOW_DAYS"] = "3"

        Config._instance = None
        DatabaseManager.reset_instance()
        self.db = DatabaseManager.get_instance()

        # Ensure analysis is old enough for default min_age_days=14
        old_created_at = datetime(2024, 1, 1, 0, 0, 0)

        with self.db.get_session() as session:
            session.add(
                AnalysisHistory(
                    query_id="q1",
                    code="600519",
                    name="贵州茅台",
                    report_type="simple",
                    sentiment_score=80,
                    operation_advice="买入",
                    trend_prediction="看多",
                    analysis_summary="test",
                    stop_loss=95.0,
                    take_profit=110.0,
                    created_at=old_created_at,
                    context_snapshot=_phase_snapshot(
                        date(2024, 1, 1),
                        phase="premarket",
                        market="cn",
                        effective_date=date(2024, 1, 1),
                        trigger_source="api",
                    ),
                )
            )

            # Analysis day close
            session.add(
                StockDaily(
                    code="600519",
                    date=date(2024, 1, 1),
                    open=100.0,
                    high=101.0,
                    low=99.0,
                    close=100.0,
                )
            )

            # Forward bars (3 days) that hit take-profit on day1
            session.add_all(
                [
                    StockDaily(code="600519", date=date(2024, 1, 2), high=111.0, low=100.0, close=105.0),
                    StockDaily(code="600519", date=date(2024, 1, 3), high=108.0, low=103.0, close=106.0),
                    StockDaily(code="600519", date=date(2024, 1, 4), high=109.0, low=104.0, close=107.0),
                ]
            )
            session.commit()
    def _seed_analysis(
        self,
        *,
        query_id: str,
        code: str = "600519",
        analysis_date: date,
        created_at: datetime,
        operation_advice: str,
        trend_prediction: str,
        start_close: float,
        forward_bars: list[StockDaily],
        phase: str = "intraday",
        market: str = "cn",
        include_effective_date: bool = True,
    ) -> None:
        with self.db.get_session() as session:
            session.add(
                AnalysisHistory(
                    query_id=query_id,
                    code=code,
                    name="贵州茅台",
                    report_type="simple",
                    sentiment_score=60,
                    operation_advice=operation_advice,
                    trend_prediction=trend_prediction,
                    analysis_summary="extra-test",
                    stop_loss=None,
                    take_profit=None,
                    created_at=created_at,
                    context_snapshot=_phase_snapshot(
                        analysis_date,
                        phase=phase,
                        market=market,
                        effective_date=analysis_date if include_effective_date else None,
                        trigger_source="api",
                    ),
                )
            )
            session.add(
                StockDaily(
                    code=code,
                    date=analysis_date,
                    open=start_close,
                    high=start_close,
                    low=start_close,
                    close=start_close,
                )
            )
            session.add_all([
                StockDaily(
                    code=code,
                    date=bar.date,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                ) for bar in forward_bars
            ])
            session.commit()
    def _seed_legacy_offshore_analysis(
        self,
        *,
        query_id: str,
        code: str,
        market: str,
        analysis_date: date,
        start_close: float,
        forward_date: date,
        end_close: float,
        include_effective_date: bool = True,
    ) -> None:
        self._seed_analysis(
            query_id=query_id,
            code=code,
            analysis_date=analysis_date,
            created_at=datetime.combine(analysis_date, datetime.min.time()),
            operation_advice="买入",
            trend_prediction="看多",
            start_close=start_close,
            forward_bars=[
                StockDaily(
                    code=code,
                    date=forward_date,
                    open=end_close,
                    high=end_close + 1,
                    low=end_close - 1,
                    close=end_close,
                )
            ],
            phase="postmarket",
            market=market,
            include_effective_date=include_effective_date,
        )
    def tearDown(self) -> None:
        Config._instance = None
        DatabaseManager.reset_instance()
        for key, value in self._original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._temp_dir.cleanup()
    def _count_results(self) -> int:
        with self.db.get_session() as session:
            return session.query(BacktestResult).count()
    def _make_backtest_result(
        self,
        *,
        analysis_history_id: int,
        analysis_date: date,
        eval_window_days: int = 1,
        engine_version: str = "v1",
    ) -> BacktestResult:
        return BacktestResult(
            analysis_history_id=analysis_history_id,
            code="600519",
            analysis_date=analysis_date,
            eval_window_days=eval_window_days,
            engine_version=engine_version,
            eval_status="completed",
            evaluated_at=datetime(2024, 1, 20, 0, 0, 0),
            operation_advice="买入",
            position_recommendation="long",
            start_price=100.0,
            end_close=101.0,
            stock_return_pct=1.0,
            direction_expected="up",
            direction_correct=True,
            outcome="win",
            simulated_return_pct=1.0,
        )
    def _run_and_get_result(self) -> BacktestResult:
        """Helper: run backtest and return the single BacktestResult row."""
        service = self._service()
        service.run_backtest(code="600519", force=False, eval_window_days=3, min_age_days=0, limit=10)
        with self.db.get_session() as session:
            return session.query(BacktestResult).one()


class _BacktestDailyRefillSeamTestsFixture:
    """回测日线补数编排归位到 ``DailyBarRefillPort`` 的契约锁定。"""
    def _service(self, refill):
        from unittest.mock import MagicMock

        # 注入 daily_refill 后 _try_fill_daily_data 不触库；两个仓储端口仅为占位。
        return BacktestService(
            backtest_repository=MagicMock(),
            stock_repository=MagicMock(),
            daily_refill=refill,
        )

