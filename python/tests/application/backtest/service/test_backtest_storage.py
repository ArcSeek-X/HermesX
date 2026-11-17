"""Tests for backtest storage."""

from tests.application.backtest._backtest_service_support import (
    AnalysisHistory,
    _BacktestServiceTestCaseFixture,
    date,
    json,
    unittest,
)


class BacktestServiceTestCase(_BacktestServiceTestCaseFixture, unittest.TestCase):
    def test_get_recent_evaluations_prefers_persisted_raw_action(self) -> None:
        service = self._service()

        with self.db.get_session() as session:
            history = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == "q1").one()
            history.operation_advice = "持有观察"
            history.raw_result = json.dumps(
                {
                    "operation_advice": "持有观察",
                    "action": "watch",
                    "action_label": "观望",
                    "guardrail_reason": "市场风险较高，建议观望",
                },
                ensure_ascii=False,
            )
            result = self._make_backtest_result(
                analysis_history_id=history.id,
                analysis_date=date(2024, 1, 1),
                eval_window_days=1,
            )
            result.operation_advice = "持有观察"
            result.position_recommendation = "long"
            session.add(result)
            session.commit()

        data = service.get_recent_evaluations(
            code="600519",
            eval_window_days=1,
            limit=10,
            page=1,
        )

        self.assertEqual(data["total"], 1)
        item = data["items"][0]
        self.assertEqual(item["operation_advice"], "持有观察")
        self.assertEqual(item["action"], "watch")
        self.assertEqual(item["action_label"], "观望")
        self.assertEqual(item["position_recommendation"], "long")
