# -*- coding: utf-8 -*-
"""回测仓储读写路径与领域记录双向映射（0.35b/0.35c）的回归锁定。

锁定两个契约：
- 读：仓储读方法在会话内把 ORM 映射为领域记录后返回，字段值逐一一致；
- 写（0.35c）：仓储写方法接受领域记录，内部转 ORM 后落库，读回仍为记录且值一致；
  并源码级锁定 ``backtest_service`` 不再引用 ``persistence.models``（防回潮）。

该测试直接受 SQLAlchemy / ORM 约束（仓储层集成测试），不受架构守卫限制。
"""

import inspect
import os
import tempfile
import unittest
from datetime import date, datetime

from src.config import Config
from src.domain.backtest import BacktestResultRecord, BacktestSummaryRecord
from src.infrastructure.persistence.repositories.backtest_repository import BacktestRepository
from src.application.backtest.service import BacktestService
from src.storage import DatabaseManager
from src.infrastructure.persistence.models.analysis import (
    AnalysisHistory,
    BacktestResult,
    BacktestSummary,
)


class BacktestRepoRecordMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._db_path = os.path.join(self._temp_dir.name, "test_repo_read.db")
        self._original_env = {
            key: os.environ.get(key)
            for key in ("ENV_FILE", "DATABASE_PATH")
        }
        self._env_path = os.path.join(self._temp_dir.name, ".env")
        with open(self._env_path, "w", encoding="utf-8") as env_file:
            env_file.write("STOCK_LIST=600519\n")
        os.environ["ENV_FILE"] = self._env_path
        os.environ["DATABASE_PATH"] = self._db_path

        Config._instance = None
        DatabaseManager.reset_instance()
        self.db = DatabaseManager.get_instance()
        self.repo = BacktestRepository(self.db)

        with self.db.get_session() as session:
            analysis = AnalysisHistory(
                query_id="q1",
                code="600519",
                name="贵州茅台",
                report_type="simple",
                sentiment_score=80,
                operation_advice="买入",
                trend_prediction="看多",
                analysis_summary="t",
                created_at=datetime(2024, 1, 1),
                context_snapshot='{"enhanced_context": {"date": "2024-01-01"}}',
            )
            session.add(analysis)
            session.flush()
            session.add(
                BacktestResult(
                    analysis_history_id=analysis.id,
                    code="600519",
                    analysis_date=date(2024, 1, 1),
                    eval_window_days=3,
                    engine_version="v1",
                    eval_status="completed",
                    evaluated_at=datetime(2024, 1, 5, 10, 30, 0),
                    operation_advice="买入",
                    position_recommendation="long",
                    start_price=100.0,
                    end_close=106.0,
                    max_high=111.0,
                    min_low=99.0,
                    stock_return_pct=6.0,
                    direction_expected="up",
                    direction_correct=True,
                    outcome="win",
                    stop_loss=95.0,
                    take_profit=110.0,
                    hit_stop_loss=False,
                    hit_take_profit=True,
                    first_hit="take_profit",
                    first_hit_date=date(2024, 1, 2),
                    first_hit_trading_days=1,
                    simulated_entry_price=100.0,
                    simulated_exit_price=110.0,
                    simulated_exit_reason="take_profit",
                    simulated_return_pct=10.0,
                )
            )
            session.add(
                BacktestSummary(
                    scope="stock",
                    code="600519",
                    eval_window_days=3,
                    engine_version="v1",
                    computed_at=datetime(2024, 1, 6),
                    total_evaluations=2,
                    completed_count=2,
                    win_count=1,
                    loss_count=1,
                    direction_accuracy_pct=50.0,
                    win_rate_pct=50.0,
                    avg_stock_return_pct=3.0,
                    advice_breakdown_json='{"买入": 2}',
                    diagnostics_json='{"k": 1}',
                )
            )
            session.commit()

    def tearDown(self) -> None:
        for key, value in self._original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        Config._instance = None
        DatabaseManager.reset_instance()
        self._temp_dir.cleanup()

    def test_list_results_returns_domain_records(self):
        rows = self.repo.list_results(
            code="600519",
            eval_window_days=3,
            engine_version="v1",
        )
        self.assertEqual(len(rows), 1)
        record = rows[0]
        self.assertIsInstance(record, BacktestResultRecord)
        self.assertNotIsInstance(record, BacktestResult)
        # 字段值逐一映射正确
        self.assertEqual(record.code, "600519")
        self.assertEqual(record.analysis_date, date(2024, 1, 1))
        self.assertEqual(record.eval_status, "completed")
        self.assertEqual(record.start_price, 100.0)
        self.assertEqual(record.end_close, 106.0)
        self.assertEqual(record.stock_return_pct, 6.0)
        self.assertTrue(record.direction_correct)
        self.assertTrue(record.hit_take_profit)
        self.assertEqual(record.first_hit, "take_profit")
        self.assertEqual(record.first_hit_date, date(2024, 1, 2))
        self.assertEqual(record.simulated_return_pct, 10.0)

    def test_list_results_for_recompute_returns_domain_records(self):
        rows = self.repo.list_results_for_recompute(
            code="600519",
            eval_window_days=3,
            engine_version="v1",
        )
        self.assertEqual(len(rows), 1)
        self.assertIsInstance(rows[0], BacktestResultRecord)

    def test_get_results_paginated_maps_first_column_to_record(self):
        rows, total = self.repo.get_results_paginated(
            code="600519",
            eval_window_days=3,
            engine_version="v1",
            days=None,
            offset=0,
            limit=10,
        )
        self.assertEqual(total, 1)
        result, stock_name, trend_prediction, _created_at, context_snapshot, _raw, _rt, _score = rows[0]
        self.assertIsInstance(result, BacktestResultRecord)
        self.assertEqual(result.simulated_exit_reason, "take_profit")
        # 其余 analysis 列保持原值
        self.assertEqual(stock_name, "贵州茅台")
        self.assertEqual(trend_prediction, "看多")
        self.assertIn("enhanced_context", context_snapshot)

    def test_get_results_with_context_batch_maps_record(self):
        rows = self.repo.get_results_with_context_batch(
            code="600519",
            eval_window_days=3,
            engine_version="v1",
            days=None,
            offset=0,
            limit=10,
        )
        self.assertEqual(len(rows), 1)
        self.assertIsInstance(rows[0][0], BacktestResultRecord)

    def test_list_results_with_context_maps_record(self):
        rows = self.repo.list_results_with_context(
            code="600519",
            eval_window_days=3,
            engine_version="v1",
        )
        self.assertEqual(len(rows), 1)
        result, context_snapshot = rows[0]
        self.assertIsInstance(result, BacktestResultRecord)
        self.assertIn("enhanced_context", context_snapshot)

    def test_get_summary_returns_domain_record(self):
        summary = self.repo.get_summary(
            scope="stock",
            code="600519",
            eval_window_days=3,
            engine_version="v1",
        )
        self.assertIsInstance(summary, BacktestSummaryRecord)
        self.assertNotIsInstance(summary, BacktestSummary)
        self.assertEqual(summary.total_evaluations, 2)
        self.assertEqual(summary.win_rate_pct, 50.0)
        self.assertEqual(summary.advice_breakdown_json, '{"买入": 2}')
        self.assertEqual(summary.diagnostics_json, '{"k": 1}')

    def test_get_summary_returns_none_when_absent(self):
        self.assertIsNone(
            self.repo.get_summary(
                scope="stock",
                code="000001",
                eval_window_days=3,
                engine_version="v1",
            )
        )

    def test_save_results_batch_accepts_records_and_round_trips(self):
        """0.35c：写方法入参改领域记录，落库后读回仍为记录且字段值一致。"""
        with self.db.get_session() as session:
            analysis = session.query(AnalysisHistory).filter_by(code="600519").one()
            analysis_id = analysis.id

        record = BacktestResultRecord(
            analysis_history_id=analysis_id,
            code="600519",
            analysis_date=date(2024, 2, 1),
            eval_window_days=5,
            engine_version="v2",
            eval_status="completed",
            evaluated_at=datetime(2024, 2, 10, 8, 0, 0),
            operation_advice="买入",
            position_recommendation="long",
            start_price=200.0,
            end_close=210.0,
            stock_return_pct=5.0,
            direction_expected="up",
            direction_correct=True,
            outcome="win",
            simulated_return_pct=5.0,
        )
        saved = self.repo.save_results_batch([record])
        self.assertEqual(saved, 1)

        rows = self.repo.list_results(
            code="600519",
            eval_window_days=5,
            engine_version="v2",
        )
        self.assertEqual(len(rows), 1)
        read_back = rows[0]
        self.assertIsInstance(read_back, BacktestResultRecord)
        self.assertEqual(read_back.start_price, 200.0)
        self.assertEqual(read_back.eval_status, "completed")
        self.assertEqual(read_back.analysis_date, date(2024, 2, 1))
        self.assertTrue(read_back.direction_correct)

    def test_upsert_summary_inserts_and_updates_from_record(self):
        """0.35c：upsert 入参改记录；新增分支转 ORM 插入，更新分支按属性回写同值语义。"""
        record = BacktestSummaryRecord(
            scope="stock",
            code="000001",
            eval_window_days=3,
            engine_version="v1",
            computed_at=datetime(2024, 1, 1),
            total_evaluations=1,
            completed_count=1,
            win_rate_pct=100.0,
            advice_breakdown_json='{"买入": 1}',
            diagnostics_json='{}',
        )
        self.repo.upsert_summary(record)
        stored = self.repo.get_summary(
            scope="stock", code="000001", eval_window_days=3, engine_version="v1",
        )
        self.assertIsInstance(stored, BacktestSummaryRecord)
        self.assertEqual(stored.total_evaluations, 1)
        self.assertEqual(stored.win_rate_pct, 100.0)

        record.total_evaluations = 2
        record.completed_count = 2
        record.win_rate_pct = 50.0
        self.repo.upsert_summary(record)
        with self.db.get_session() as session:
            count = session.query(BacktestSummary).filter_by(
                scope="stock", code="000001", eval_window_days=3, engine_version="v1",
            ).count()
        self.assertEqual(count, 1)
        updated = self.repo.get_summary(
            scope="stock", code="000001", eval_window_days=3, engine_version="v1",
        )
        self.assertEqual(updated.total_evaluations, 2)
        self.assertEqual(updated.win_rate_pct, 50.0)

    def test_service_has_no_persistence_models_coupling(self):
        """源码级防回潮：``backtest_service`` 不再 import/构造持久化模型。"""
        source = inspect.getsource(BacktestService)
        self.assertNotIn("from src.infrastructure.persistence.models", source)
        self.assertNotIn("BacktestResult(", source)
        self.assertNotIn("BacktestSummary(", source)
        # 写路径已改走领域记录
        self.assertIn("BacktestResultRecord(", source)
        self.assertIn("return BacktestSummaryRecord(", source)


if __name__ == "__main__":
    unittest.main()
