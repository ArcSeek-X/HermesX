# -*- coding: utf-8 -*-
"""LLM 用量用例的行为回归。

锁定迁移前 ``api/v1/endpoints/usage.py`` 里直连 ``DatabaseManager`` 时的时间窗语义与读模型形状。
"""

import unittest
from datetime import datetime
from typing import Any, Dict, List

from src.application.usage import UsageService


class RecordingUsageRepository:
    """记录调用参数，并返回可控数据的假仓储。"""

    def __init__(self, summary: Dict[str, Any] | None = None, records: List[Dict[str, Any]] | None = None) -> None:
        self.summary = summary or {}
        self.records = records or []
        self.summary_calls: List[tuple] = []
        self.record_calls: List[tuple] = []

    def get_llm_usage_summary(self, from_dt, to_dt):
        self.summary_calls.append((from_dt, to_dt))
        return self.summary

    def get_llm_usage_records(self, from_dt, to_dt, limit=50):
        self.record_calls.append((from_dt, to_dt, limit))
        return self.records


_NOW = datetime(2026, 6, 11, 9, 30, 0)


def _service(repository: RecordingUsageRepository) -> UsageService:
    return UsageService(repository, now=lambda: _NOW)


class UsageServicePeriodTestCase(unittest.TestCase):
    def test_today_window_starts_at_midnight(self):
        repository = RecordingUsageRepository()
        payload = _service(repository).get_summary("today")

        self.assertEqual(payload["period"], "today")
        self.assertEqual(payload["from_date"], "2026-06-11")
        self.assertEqual(payload["to_date"], "2026-06-11")
        self.assertEqual(repository.summary_calls, [(datetime(2026, 6, 11, 0, 0, 0), _NOW)])

    def test_month_window_starts_at_first_day(self):
        repository = RecordingUsageRepository()
        payload = _service(repository).get_summary("month")

        self.assertEqual(payload["from_date"], "2026-06-01")
        self.assertEqual(repository.summary_calls, [(datetime(2026, 6, 1, 0, 0, 0), _NOW)])

    def test_all_window_uses_fixed_lower_bound(self):
        repository = RecordingUsageRepository()
        payload = _service(repository).get_summary("all")

        self.assertEqual(payload["from_date"], "2000-01-01")
        self.assertEqual(repository.summary_calls, [(datetime(2000, 1, 1), _NOW)])

    def test_unknown_period_falls_back_to_month(self):
        repository = RecordingUsageRepository()
        payload = _service(repository).get_summary("week")

        self.assertEqual(payload["period"], "month")
        self.assertEqual(payload["from_date"], "2026-06-01")


class UsageServicePayloadTestCase(unittest.TestCase):
    def test_summary_fills_defaults_when_repository_returns_empty(self):
        payload = _service(RecordingUsageRepository(summary={})).get_summary("month")

        self.assertEqual(payload["total_calls"], 0)
        self.assertEqual(payload["total_prompt_tokens"], 0)
        self.assertEqual(payload["total_completion_tokens"], 0)
        self.assertEqual(payload["total_tokens"], 0)
        self.assertEqual(payload["by_call_type"], [])
        self.assertEqual(payload["by_model"], [])

    def test_summary_keeps_repository_breakdowns(self):
        summary = {
            "total_calls": 3,
            "total_prompt_tokens": 10,
            "total_completion_tokens": 20,
            "total_tokens": 30,
            "by_call_type": [{"call_type": "analysis", "calls": 3, "total_tokens": 30}],
            "by_model": [{"model": "openai/gpt-test", "calls": 3, "total_tokens": 30}],
        }
        payload = _service(RecordingUsageRepository(summary=summary)).get_summary("month")

        self.assertEqual(payload["total_tokens"], 30)
        self.assertEqual(payload["by_call_type"][0]["call_type"], "analysis")
        self.assertEqual(payload["by_model"][0]["model"], "openai/gpt-test")

    def test_dashboard_serializes_called_at_and_reuses_the_same_window(self):
        repository = RecordingUsageRepository(
            records=[
                {"id": 7, "called_at": datetime(2026, 6, 11, 8, 0, 0), "total_tokens": 60},
                {"id": 8, "called_at": None, "total_tokens": 0},
            ]
        )
        payload = _service(repository).get_dashboard("today", 10)

        self.assertEqual(payload["recent_calls"][0]["called_at"], "2026-06-11T08:00:00")
        self.assertEqual(payload["recent_calls"][1]["called_at"], "")
        self.assertEqual(repository.record_calls, [(datetime(2026, 6, 11, 0, 0, 0), _NOW, 10)])
        self.assertEqual(repository.summary_calls, [(datetime(2026, 6, 11, 0, 0, 0), _NOW)])


if __name__ == "__main__":
    unittest.main()
