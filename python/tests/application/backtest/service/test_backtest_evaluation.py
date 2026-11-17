"""Tests for backtest evaluation."""

from tests.application.backtest._backtest_service_support import (
    _BacktestServiceTestCaseFixture,
    unittest,
)


class BacktestServiceTestCase(_BacktestServiceTestCaseFixture, unittest.TestCase):
    def test_force_semantics(self) -> None:
        service = self._service()

        stats1 = service.run_backtest(code="600519", force=False, eval_window_days=3, min_age_days=0, limit=10)
        self.assertEqual(stats1["saved"], 1)
        self.assertEqual(self._count_results(), 1)

        # Non-force should be idempotent
        stats2 = service.run_backtest(code="600519", force=False, eval_window_days=3, min_age_days=0, limit=10)
        self.assertEqual(stats2["saved"], 0)
        self.assertEqual(self._count_results(), 1)
        self.assertEqual(stats2["diagnostics"]["empty_reason"], "no_new_results")
        self.assertIn("历史分析记录已存在", stats2["message"] or "")

        # Force should replace existing result without unique constraint errors
        stats3 = service.run_backtest(code="600519", force=True, eval_window_days=3, min_age_days=0, limit=10)
        self.assertEqual(stats3["saved"], 1)
        self.assertEqual(self._count_results(), 1)
