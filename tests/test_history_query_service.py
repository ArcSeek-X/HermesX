# -*- coding: utf-8 -*-
"""``HistoryQueryService`` 的用例层回归测试。

覆盖切片边界内搬出端点的三块逻辑：按代码分批删除、个股栏归一化去重、
Markdown 生成失败的错误语义转换；其余读模型字段重建由
``tests/test_analysis_history.py`` 从服务层与端点层双路径覆盖。
"""

from __future__ import annotations

import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from src.application.history import (
    HistoryMarkdownGenerationError,
    HistoryQueryService,
    HistoryValidationError,
)
from src.application.history.read_model import MarkdownReportGenerationError


class _RecordingRepository:
    """按调用顺序记录查询参数的最小仓储替身。"""

    def __init__(self, records=None) -> None:
        self.records = list(records or [])
        self.paginated_calls = []
        self.deleted_batches = []
        self.distinct_calls = []
        self.news_calls = []

    def get_analysis_history_paginated(
        self,
        code=None,
        report_type=None,
        start_date=None,
        end_date=None,
        offset=0,
        limit=20,
    ):
        self.paginated_calls.append(
            {
                "code": code,
                "report_type": report_type,
                "start_date": start_date,
                "end_date": end_date,
                "offset": offset,
                "limit": limit,
            }
        )
        return self.records[:limit], len(self.records)

    def delete_analysis_history_records(self, record_ids):
        self.deleted_batches.append(list(record_ids))
        existing = {record.id for record in self.records}
        removed = [record_id for record_id in record_ids if record_id in existing]
        self.records = [record for record in self.records if record.id not in removed]
        return len(removed)

    def get_distinct_stocks_from_history(self, start_date=None, end_date=None, limit=200):
        self.distinct_calls.append(
            {"start_date": start_date, "end_date": end_date, "limit": limit}
        )
        return self.records[:limit]

    def get_latest_fundamental_snapshot(self, query_id, code):
        return None

    def get_news_intel_by_query_id(self, query_id, limit=20):
        self.news_calls.append({"query_id": query_id, "limit": limit})
        return []

    def get_recent_news(self, code, days=7, limit=20):
        return []

    def get_analysis_history_by_id(self, record_id):
        return None

    def get_latest_analysis_by_query_id(self, query_id, *, code=None, report_type=None):
        return None

    def get_analysis_history(self, code=None, query_id=None, days=30, limit=50, exclude_query_id=None):
        return []


class _SuffixLessNormalizer:
    """去掉交易所后缀并大写，用来断言归一化去重键。"""

    def normalize(self, stock_code: str) -> str:
        return str(stock_code or "").strip().upper().split(".")[0]


def _history_record(record_id: int, code: str, *, created_at=None) -> SimpleNamespace:
    return SimpleNamespace(
        id=record_id,
        query_id=f"query-{record_id}",
        code=code,
        name="测试股份",
        report_type="detailed",
        trend_prediction=None,
        analysis_summary=None,
        sentiment_score=None,
        operation_advice=None,
        raw_result=None,
        context_snapshot=None,
        created_at=created_at or datetime(2026, 6, 11, 9, 30),
    )


class HistoryQueryServiceDeleteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = _RecordingRepository(
            [_history_record(record_id, "600519") for record_id in (1, 2, 3)]
        )
        self.service = HistoryQueryService(
            repository=self.repository,
            code_normalizer=_SuffixLessNormalizer(),
        )

    def test_delete_by_code_rejects_blank_code_before_querying(self) -> None:
        with self.assertRaises(HistoryValidationError) as raised:
            self.service.delete_by_code("   ")

        self.assertEqual(raised.exception.error_code, "invalid_request")
        self.assertEqual(self.repository.paginated_calls, [])
        self.assertEqual(self.repository.deleted_batches, [])

    def test_delete_by_code_drains_every_batch(self) -> None:
        with patch("src.application.history.service._DELETE_BY_CODE_BATCH_SIZE", 2):
            deleted = self.service.delete_by_code("600519")

        self.assertEqual(deleted, 3)
        self.assertEqual(self.repository.deleted_batches, [[1, 2], [3]])

    def test_delete_records_forwards_keys_to_the_repository(self) -> None:
        deleted = self.service.delete_records([1, 2])

        self.assertEqual(deleted, 2)
        self.assertEqual(self.repository.deleted_batches, [[1, 2]])


class HistoryQueryServiceStockBarTest(unittest.TestCase):
    def test_stock_bar_keeps_latest_record_per_normalized_code(self) -> None:
        repository = _RecordingRepository(
            [
                SimpleNamespace(**_history_record(1, "002460").__dict__),
                SimpleNamespace(**_history_record(3, "002460.SZ").__dict__),
                SimpleNamespace(**_history_record(2, "600519").__dict__),
            ]
        )
        service = HistoryQueryService(
            repository=repository,
            code_normalizer=_SuffixLessNormalizer(),
        )

        items = service.list_stock_bar(limit=50)

        self.assertEqual([item["id"] for item in items], [3, 2])
        # 归一化去重会收缩结果，因此向上游多取三倍（上限 500）。
        self.assertEqual(repository.distinct_calls[0]["limit"], 150)
        self.assertTrue(all(item["analysis_count"] == 3 for item in items))

    def test_stock_bar_truncates_to_requested_limit(self) -> None:
        repository = _RecordingRepository(
            [_history_record(record_id, f"60000{record_id}") for record_id in range(1, 6)]
        )
        service = HistoryQueryService(
            repository=repository,
            code_normalizer=_SuffixLessNormalizer(),
        )

        items = service.list_stock_bar(limit=2)

        self.assertEqual(len(items), 2)


class HistoryQueryServiceMarkdownTest(unittest.TestCase):
    def test_markdown_generation_error_is_mapped_to_a_domain_error(self) -> None:
        service = HistoryQueryService(
            repository=_RecordingRepository(),
            code_normalizer=_SuffixLessNormalizer(),
        )

        with patch(
            "src.application.history.service.HistoryService.get_markdown_report",
            side_effect=MarkdownReportGenerationError("rows corrupted", record_id="7"),
        ):
            with self.assertRaises(HistoryMarkdownGenerationError) as raised:
                service.get_markdown("7")

        self.assertEqual(raised.exception.error_code, "generation_failed")
        self.assertEqual(raised.exception.message, "rows corrupted")

    def test_markdown_returns_none_for_missing_records(self) -> None:
        service = HistoryQueryService(
            repository=_RecordingRepository(),
            code_normalizer=_SuffixLessNormalizer(),
        )

        with patch(
            "src.application.history.service.HistoryService.get_markdown_report",
            return_value=None,
        ):
            self.assertIsNone(service.get_markdown("404"))


if __name__ == "__main__":
    unittest.main()
