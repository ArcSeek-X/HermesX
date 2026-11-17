"""Tests for analysis history reports."""

from tests.application.history._analysis_history_support import (
    AnalysisHistory,
    AnalysisResult,
    DecisionSignalRecord,
    HistoryService,
    MagicMock,
    _AnalysisHistoryTestCaseFixture,
    _HistoryItemSchemaNegativeSentimentTestFixture,
    get_history_detail,
    unittest,
)


class AnalysisHistoryTestCase(_AnalysisHistoryTestCaseFixture, unittest.TestCase):
    def test_get_latest_analysis_history_id_filters_by_report_type_and_latest_record(self) -> None:
        """按 query/code/report_type 返回最新真实历史主键。"""
        for report_type in ("simple", "full", "simple"):
            saved = self.db.save_analysis_history(
                result=self._build_result(),
                query_id="query_latest_id",
                report_type=report_type,
                news_content="新闻摘要",
                context_snapshot=None,
                save_snapshot=False,
            )
            self.assertGreater(saved, 0)

        simple_id = self.db.get_latest_analysis_history_id(
            query_id="query_latest_id",
            code="600519",
            report_type="simple",
        )
        full_id = self.db.get_latest_analysis_history_id(
            query_id="query_latest_id",
            code="600519",
            report_type="full",
        )

        self.assertIsNotNone(simple_id)
        self.assertIsNotNone(full_id)
        self.assertGreater(simple_id, full_id)

    def test_get_latest_analysis_history_id_requires_report_type(self) -> None:
        """report_type 是必传参数，避免误取同 query/code 的其他报告。"""
        with self.assertRaises(TypeError):
            self.db.get_latest_analysis_history_id(query_id="query", code="600519")

    def test_history_markdown_localizes_english_report_and_placeholder_name(self) -> None:
        """History markdown should preserve report_language for English reports."""
        result = AnalysisResult(
            code="AAPL",
            name="股票AAPL",
            sentiment_score=78,
            trend_prediction="Bullish",
            operation_advice="Buy",
            analysis_summary="Momentum remains constructive.",
            report_language="en",
            dashboard={
                "core_conclusion": {
                    "one_sentence": "Favor buying on pullbacks.",
                    "position_advice": {
                        "no_position": "Open a starter position.",
                        "has_position": "Hold and trail the stop.",
                    },
                },
                "intelligence": {
                    "risk_alerts": [],
                },
                "battle_plan": {
                    "sniper_points": {
                        "ideal_buy": "180-182",
                        "stop_loss": "172",
                        "take_profit": "195",
                    }
                },
            },
        )

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_english_markdown_001",
            report_type="full",
            news_content="news",
            context_snapshot=None,
            save_snapshot=False,
        )
        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(
                AnalysisHistory.query_id == "query_english_markdown_001"
            ).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            record_id = row.id

        markdown = HistoryService(self.db).get_markdown_report(str(record_id))

        self.assertIsNotNone(markdown)
        self.assertIn("Stock Analysis Report", markdown)
        self.assertIn("Core Conclusion", markdown)
        self.assertIn("Unnamed Stock (AAPL)", markdown)
        self.assertNotIn("核心结论", markdown)

    def test_history_markdown_signal_metadata_uses_explicit_avoid_action(self) -> None:
        result = AnalysisResult(
            code="AAPL",
            name="Apple",
            sentiment_score=90,
            trend_prediction="Bullish",
            operation_advice="Hold",
            analysis_summary="Risk remains elevated.",
            report_language="en",
            action="avoid",
            action_label="Avoid",
        )

        markdown = HistoryService(self.db)._generate_single_stock_markdown(
            result,
            MagicMock(created_at=None),
        )

        self.assertIn("**🟡 Avoid** | Bullish", markdown)
        self.assertNotIn("Strong Buy", markdown)

    def test_history_markdown_handles_legacy_strategy_synthesis_shapes(self) -> None:
        service = HistoryService(self.db)
        record = MagicMock(created_at=None)

        for malformed in ("bad-shape", ["bad-shape"], 42, True):
            result = AnalysisResult(
                code="600519",
                name="贵州茅台",
                sentiment_score=50,
                trend_prediction="震荡",
                operation_advice="观望",
                report_language="zh",
                dashboard={
                    "core_conclusion": {"one_sentence": "测试"},
                    "intelligence": {},
                    "battle_plan": {},
                    "strategy_synthesis": malformed,
                },
            )

            markdown = service._generate_single_stock_markdown(result, record)

            self.assertNotIn("多策略综合", markdown)

        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=50,
            trend_prediction="震荡",
            operation_advice="观望",
            report_language="zh",
            dashboard={
                "core_conclusion": {"one_sentence": "测试"},
                "intelligence": {},
                "battle_plan": {},
                "strategy_synthesis": {
                    "final_signal": "hold",
                    "consensus_level": "insufficient",
                    "conflict_severity": "none",
                    "conflict_count": 0,
                    "supporting_skills": "bad-shape",
                    "opposing_skills": ["bad-shape"],
                    "conflicts": "bad-shape",
                    "summary_params": {"invalid_opinion_count": "3"},
                },
            },
        )

        markdown = service._generate_single_stock_markdown(result, record)

        self.assertIn("多策略综合", markdown)
        self.assertIn("另有 3 个策略解析失败", markdown)

    def test_history_markdown_returns_persisted_market_review_report(self) -> None:
        """Market review history should return the saved Markdown without rebuilding a stock report."""
        result = AnalysisResult(
            code="MARKET",
            name="大盘复盘",
            sentiment_score=50,
            trend_prediction="大盘复盘",
            operation_advice="查看复盘",
            analysis_summary="今日大盘复盘",
            raw_response="# 🎯 大盘复盘\n\n## 今日大盘\n\n复盘正文",
        )

        saved = self.db.save_analysis_history(
            result=result,
            query_id="market_review_query_001",
            report_type="market_review",
            news_content="## 今日大盘\n\n复盘正文",
            context_snapshot=None,
            save_snapshot=False,
        )
        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(
                AnalysisHistory.query_id == "market_review_query_001"
            ).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            record_id = row.id

        markdown = HistoryService(self.db).get_markdown_report(str(record_id))

        self.assertEqual(markdown, "# 🎯 大盘复盘\n\n## 今日大盘\n\n复盘正文")

    def test_history_markdown_collapses_unavailable_chip_structure(self) -> None:
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
            dashboard={
                "data_perspective": {
                    "chip_structure": {
                        "profit_ratio": "数据缺失，无法判断",
                        "avg_cost": "数据缺失，无法判断",
                        "concentration": "数据缺失，无法判断",
                        "chip_health": "数据缺失，无法判断",
                    }
                }
            },
        )

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_chip_unavailable_001",
            report_type="full",
            news_content="news",
            context_snapshot=None,
            save_snapshot=False,
        )
        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(
                AnalysisHistory.query_id == "query_chip_unavailable_001"
            ).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            record_id = row.id

        markdown = HistoryService(self.db).get_markdown_report(str(record_id))

        self.assertIsNotNone(markdown)
        self.assertIn("**筹码**: 筹码分布未启用或数据源暂不可用，未纳入筹码判断。", markdown)
        self.assertEqual(markdown.count("数据缺失，无法判断"), 0)

    def test_history_detail_returns_persisted_market_review_report(self) -> None:
        """Market review detail should surface the saved recap content for Web history clicks."""
        if get_history_detail is None:
            self.skipTest("fastapi is not installed in this test environment")

        report_content = "# 🎯 大盘复盘\n\n## 今日大盘\n\n复盘正文"
        result = AnalysisResult(
            code="MARKET",
            name="大盘复盘",
            sentiment_score=50,
            trend_prediction="大盘复盘",
            operation_advice="查看复盘",
            analysis_summary="今日大盘复盘",
            raw_response=report_content,
        )

        saved = self.db.save_analysis_history(
            result=result,
            query_id="market_review_query_detail_001",
            report_type="market_review",
            news_content="## 今日大盘\n\n复盘正文",
            context_snapshot=None,
            save_snapshot=False,
        )
        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(
                AnalysisHistory.query_id == "market_review_query_detail_001"
            ).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            record_id = row.id

        report = get_history_detail(str(record_id), service=self._history_service())

        self.assertEqual(report.meta.report_type, "market_review")
        self.assertEqual(report.summary.analysis_summary, report_content)
        self.assertIsNone(report.summary.action)
        self.assertIsNone(report.summary.action_label)
        self.assertEqual(report.details.news_content, report_content)

    def test_history_markdown_uses_safe_bias_emoji_for_english_status(self) -> None:
        """English bias status should keep the correct non-risk emoji in markdown."""
        result = AnalysisResult(
            code="AAPL",
            name="股票AAPL",
            sentiment_score=80,
            trend_prediction="Bullish",
            operation_advice="Buy",
            analysis_summary="Momentum remains constructive.",
            report_language="en",
            dashboard={
                "data_perspective": {
                    "price_position": {
                        "current_price": 190.5,
                        "ma5": 188.0,
                        "ma10": 184.5,
                        "ma20": 179.2,
                        "bias_ma5": 1.33,
                        "bias_status": "Safe",
                        "support_level": 184.5,
                        "resistance_level": 195.0,
                    }
                }
            },
        )

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_english_markdown_bias_001",
            report_type="full",
            news_content="news",
            context_snapshot=None,
            save_snapshot=False,
        )
        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(
                AnalysisHistory.query_id == "query_english_markdown_bias_001"
            ).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            record_id = row.id

        markdown = HistoryService(self.db).get_markdown_report(str(record_id))

        self.assertIsNotNone(markdown)
        self.assertIn("✅Safe", markdown)
        self.assertNotIn("🚨Safe", markdown)

    def test_delete_analysis_history_records_keeps_manual_signal_with_same_report_id(self) -> None:
        """source_report_id 是弱引用，真实 history 删除不应误删 manual/pre-report 信号。"""
        record_id = self._save_history("query_delete_manual_collision")

        with self.db.session_scope() as session:
            session.add(DecisionSignalRecord(
                stock_code="600519",
                stock_name="贵州茅台",
                market="cn",
                source_type="analysis",
                source_report_id=record_id,
                trace_id="trace-delete-analysis-bound",
                market_phase="intraday",
                trigger_source="api",
                action="buy",
                action_label="买入",
                reason="history-bound signal",
                plan_quality="minimal",
                status="active",
            ))
            session.add(DecisionSignalRecord(
                stock_code="600519",
                stock_name="贵州茅台",
                market="cn",
                source_type="manual",
                source_report_id=record_id,
                trace_id="trace-delete-manual-weak-ref",
                market_phase="intraday",
                trigger_source="api",
                action="watch",
                action_label="观望",
                reason="manual signal with caller-supplied report id",
                plan_quality="minimal",
                status="active",
            ))

        deleted = self.db.delete_analysis_history_records([record_id])
        self.assertEqual(deleted, 1)

        with self.db.get_session() as session:
            self.assertEqual(
                session.query(DecisionSignalRecord).filter(
                    DecisionSignalRecord.trace_id == "trace-delete-analysis-bound"
                ).count(),
                0,
            )
            self.assertEqual(
                session.query(DecisionSignalRecord).filter(
                    DecisionSignalRecord.trace_id == "trace-delete-manual-weak-ref"
                ).count(),
                1,
            )


class HistoryItemSchemaNegativeSentimentTest(_HistoryItemSchemaNegativeSentimentTestFixture, unittest.TestCase):
    def test_report_summary_negative_sentiment_score_does_not_raise(self) -> None:
        """ReportSummary.sentiment_score should also accept negative values from legacy DB rows."""
        if self.ReportSummary is None:
            self.skipTest("fastapi / pydantic not installed in this test environment")

        summary = self.ReportSummary(sentiment_score=-22)
        self.assertEqual(summary.sentiment_score, -22)

    def test_report_summary_out_of_range_high_sentiment_score_does_not_raise(self) -> None:
        """ReportSummary.sentiment_score should also accept scores above 100 from legacy data."""
        if self.ReportSummary is None:
            self.skipTest("fastapi / pydantic not installed in this test environment")

        summary = self.ReportSummary(sentiment_score=150)
        self.assertEqual(summary.sentiment_score, 150)

    def test_report_summary_none_sentiment_score_is_allowed(self) -> None:
        """ReportSummary.sentiment_score=None should still be valid (optional field)."""
        if self.ReportSummary is None:
            self.skipTest("fastapi / pydantic not installed in this test environment")

        summary = self.ReportSummary(sentiment_score=None)
        self.assertIsNone(summary.sentiment_score)
