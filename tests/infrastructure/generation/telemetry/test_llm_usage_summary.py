"""Tests for llm usage summary."""

from tests.infrastructure.generation.telemetry._llm_usage_support import (
    _TestGetLLMUsageSummaryFixture,
    datetime,
    unittest,
)


class TestGetLLMUsageSummary(_TestGetLLMUsageSummaryFixture, unittest.TestCase):
    def test_total_calls_and_tokens(self):
        from_dt, to_dt = self._today_range()
        result = self.db.get_llm_usage_summary(from_dt, to_dt)
        self.assertEqual(result["total_calls"], 5)
        # 3*300 + 2*150 = 900 + 300 = 1200
        self.assertEqual(result["total_tokens"], 1200)

    def test_by_call_type(self):
        from_dt, to_dt = self._today_range()
        result = self.db.get_llm_usage_summary(from_dt, to_dt)
        by_type = {r["call_type"]: r for r in result["by_call_type"]}
        self.assertIn("analysis", by_type)
        self.assertIn("agent", by_type)
        self.assertEqual(by_type["analysis"]["calls"], 3)
        self.assertEqual(by_type["analysis"]["total_tokens"], 900)
        self.assertEqual(by_type["agent"]["calls"], 2)
        self.assertEqual(by_type["agent"]["total_tokens"], 300)

    def test_by_model(self):
        from_dt, to_dt = self._today_range()
        result = self.db.get_llm_usage_summary(from_dt, to_dt)
        by_model = {r["model"]: r for r in result["by_model"]}
        self.assertEqual(by_model["gemini/gemini-2.5-flash"]["calls"], 3)
        self.assertEqual(by_model["openai/gpt-4o"]["calls"], 2)

    def test_token_totals_include_prompt_completion_and_model_peak(self):
        from_dt, to_dt = self._today_range()
        result = self.db.get_llm_usage_summary(from_dt, to_dt)
        self.assertEqual(result["total_prompt_tokens"], 400)
        self.assertEqual(result["total_completion_tokens"], 800)
        by_model = {r["model"]: r for r in result["by_model"]}
        self.assertEqual(by_model["gemini/gemini-2.5-flash"]["prompt_tokens"], 300)
        self.assertEqual(by_model["gemini/gemini-2.5-flash"]["completion_tokens"], 600)
        self.assertEqual(by_model["gemini/gemini-2.5-flash"]["max_total_tokens"], 300)

    def test_get_llm_usage_records_returns_recent_rows_with_limit(self):
        from_dt, to_dt = self._today_range()
        rows = self.db.get_llm_usage_records(from_dt, to_dt, limit=2)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["called_at"] >= from_dt for row in rows))
        self.assertIn(rows[0]["call_type"], {"analysis", "agent"})
        self.assertIn("prompt_tokens", rows[0])
        self.assertIn("completion_tokens", rows[0])

    def test_empty_range_returns_zeros(self):
        future = datetime(2099, 1, 1)
        result = self.db.get_llm_usage_summary(future, future)
        self.assertEqual(result["total_calls"], 0)
        self.assertEqual(result["total_tokens"], 0)
        self.assertEqual(result["by_call_type"], [])
        self.assertEqual(result["by_model"], [])
