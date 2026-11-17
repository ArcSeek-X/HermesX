"""Tests for analysis history contracts."""

from tests.application.history._analysis_history_support import (
    AnalysisHistory,
    AnalysisResult,
    _AnalysisHistoryTestCaseFixture,
    get_stock_bar,
    unittest,
)


class AnalysisHistoryTestCase(_AnalysisHistoryTestCaseFixture, unittest.TestCase):
    def test_distinct_stock_bar_excludes_market_review_records_by_default(self) -> None:
        """The stock bar aggregation should not mix MARKET into ordinary stock entries."""
        stock_result = self._build_result()
        market_result = AnalysisResult(
            code="MARKET",
            name="大盘复盘",
            sentiment_score=50,
            trend_prediction="大盘复盘",
            operation_advice="查看复盘",
            analysis_summary="大盘复盘摘要",
        )

        self.assertGreater(
            self.db.save_analysis_history(
                result=stock_result,
                query_id="query_stock_bar_stock",
                report_type="detailed",
                news_content="个股正文",
                context_snapshot=None,
                save_snapshot=False,
            ),
            0,
        )
        self.assertGreater(
            self.db.save_analysis_history(
                result=market_result,
                query_id="query_stock_bar_market",
                report_type="market_review",
                news_content="大盘复盘正文",
                context_snapshot=None,
                save_snapshot=False,
            ),
            0,
        )

        records = self.db.get_distinct_stocks_from_history(limit=10)

        self.assertEqual([record.code for record in records], ["600519"])

    def test_stock_bar_item_derives_action_fields_from_legacy_advice(self) -> None:
        if get_stock_bar is None:
            self.skipTest("fastapi is not installed in this test environment")

        result = self._build_result()
        result.operation_advice = "不建议买入"

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_stock_bar_action",
            report_type="detailed",
            news_content="个股正文",
            context_snapshot=None,
            save_snapshot=False,
        )
        self.assertGreater(saved, 0)

        response = get_stock_bar(
            start_date=None,
            end_date=None,
            limit=10,
            service=self._history_service(),
        )

        self.assertEqual(len(response.items), 1)
        self.assertEqual(response.items[0].operation_advice, "不建议买入")
        self.assertEqual(response.items[0].action, "avoid")
        self.assertEqual(response.items[0].action_label, "回避")

    def test_stock_bar_item_aligns_score_and_legacy_advice(self) -> None:
        if get_stock_bar is None:
            self.skipTest("fastapi is not installed in this test environment")

        result = self._build_result()
        result.operation_advice = "持有"
        result.sentiment_score = 78

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_stock_bar_score_align",
            report_type="detailed",
            news_content="个股正文",
            context_snapshot=None,
            save_snapshot=False,
        )
        self.assertGreater(saved, 0)

        response = get_stock_bar(
            start_date=None,
            end_date=None,
            limit=10,
            service=self._history_service(),
        )

        self.assertEqual(len(response.items), 1)
        self.assertEqual(response.items[0].operation_advice, "持有")
        self.assertEqual(response.items[0].sentiment_score, 78)
        self.assertEqual(response.items[0].action, "buy")
        self.assertEqual(response.items[0].action_label, "买入")

    def test_stock_bar_item_falls_back_to_raw_result_summary_fields(self) -> None:
        if get_stock_bar is None:
            self.skipTest("fastapi is not installed in this test environment")

        result = self._build_result()
        result.operation_advice = "Hold"
        result.report_language = "en"

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_stock_bar_raw_fallback",
            report_type="detailed",
            news_content="stock report",
            context_snapshot=None,
            save_snapshot=False,
        )
        self.assertGreater(saved, 0)

        with self.db.session_scope() as session:
            row = session.query(AnalysisHistory).filter(
                AnalysisHistory.query_id == "query_stock_bar_raw_fallback"
            ).first()
            self.assertIsNotNone(row)
            row.sentiment_score = None
            row.operation_advice = None

        response = get_stock_bar(
            start_date=None,
            end_date=None,
            limit=10,
            service=self._history_service(),
        )

        self.assertEqual(len(response.items), 1)
        self.assertEqual(response.items[0].sentiment_score, 78)
        self.assertEqual(response.items[0].operation_advice, "Hold")
        self.assertEqual(response.items[0].action, "buy")
        self.assertEqual(response.items[0].action_label, "Buy")
