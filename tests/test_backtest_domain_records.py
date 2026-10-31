# -*- coding: utf-8 -*-
"""回测领域记录（DTO）与持久化 ORM 模型的字段契约锁定。

核心护栏：领域记录的字段集合必须覆盖 ORM 列（防未来给 ``BacktestResult`` /
``BacktestSummary`` 加列后领域/仓储映射漏字段）。用 SQLAlchemy
``__table__.columns.keys()`` 动态取列名比对，而非硬编码清单，避免手工漂移。
"""

import unittest
from dataclasses import fields

from src.domain.backtest import BacktestResultRecord, BacktestSummaryRecord
from src.infrastructure.persistence.models.analysis import (
    BacktestResult,
    BacktestSummary,
)


def _record_field_names(record_cls):
    return {f.name for f in fields(record_cls)}


class BacktestDomainRecordsTests(unittest.TestCase):
    def test_result_record_covers_all_orm_columns(self):
        orm_columns = set(BacktestResult.__table__.columns.keys())
        record_fields = _record_field_names(BacktestResultRecord)
        missing = orm_columns - record_fields
        self.assertEqual(
            missing,
            set(),
            f"BacktestResultRecord 缺少 ORM 列字段: {sorted(missing)}",
        )

    def test_summary_record_covers_all_orm_columns(self):
        orm_columns = set(BacktestSummary.__table__.columns.keys())
        record_fields = _record_field_names(BacktestSummaryRecord)
        missing = orm_columns - record_fields
        self.assertEqual(
            missing,
            set(),
            f"BacktestSummaryRecord 缺少 ORM 列字段: {sorted(missing)}",
        )

    def test_record_fields_do_not_exceed_orm_columns(self):
        # 领域记录不应凭空多出 ORM 没有的字段（否则映射会出现语义空洞）。
        self.assertEqual(
            _record_field_names(BacktestResultRecord),
            set(BacktestResult.__table__.columns.keys()),
        )
        self.assertEqual(
            _record_field_names(BacktestSummaryRecord),
            set(BacktestSummary.__table__.columns.keys()),
        )

    def test_result_record_partial_construction_defaults(self):
        record = BacktestResultRecord(analysis_history_id=7, code="600519")
        self.assertEqual(record.id, None)
        self.assertEqual(record.analysis_history_id, 7)
        self.assertEqual(record.code, "600519")
        # 对齐 ORM 列默认
        self.assertEqual(record.eval_window_days, 10)
        self.assertEqual(record.engine_version, "v1")
        self.assertEqual(record.eval_status, "pending")
        self.assertEqual(record.start_price, None)
        self.assertEqual(record.simulated_return_pct, None)

    def test_summary_record_construction_and_count_defaults(self):
        record = BacktestSummaryRecord(scope="overall", code=None)
        self.assertEqual(record.scope, "overall")
        self.assertEqual(record.total_evaluations, 0)
        self.assertEqual(record.completed_count, 0)
        self.assertEqual(record.win_count, 0)
        self.assertEqual(record.advice_breakdown_json, None)

    def test_records_are_dataclass_equality_value_based(self):
        a = BacktestResultRecord(analysis_history_id=1, code="600519")
        b = BacktestResultRecord(analysis_history_id=1, code="600519")
        self.assertEqual(a, b)
        self.assertNotEqual(a, BacktestResultRecord(analysis_history_id=2, code="600519"))


if __name__ == "__main__":
    unittest.main()
