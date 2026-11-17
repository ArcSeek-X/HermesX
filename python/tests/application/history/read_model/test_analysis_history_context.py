"""Tests for analysis history context."""

from tests.application.history._analysis_history_support import (
    AnalysisHistory,
    AnalysisResult,
    HistoryService,
    _AnalysisHistoryTestCaseFixture,
    _analysis_context_pack_overview,
    _market_phase_summary,
    get_history_detail,
    json,
    patch,
    unittest,
)


class AnalysisHistoryTestCase(_AnalysisHistoryTestCaseFixture, unittest.TestCase):
    def test_save_analysis_history_with_snapshot(self) -> None:
        """保存历史记录并写入上下文快照"""
        result = self._build_result()
        result.dashboard = {
            "battle_plan": {
                "sniper_points": {
                    "ideal_buy": "理想买入点：125.5元",
                    "secondary_buy": "120",
                    "stop_loss": "止损位：110元",
                    "take_profit": "目标位：150.0元",
                }
            }
        }
        context_snapshot = {"enhanced_context": {"code": "600519"}}

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_001",
            report_type="simple",
            news_content="新闻摘要",
            context_snapshot=context_snapshot,
            save_snapshot=True
        )

        self.assertGreater(saved, 0)

        history = self.db.get_analysis_history(code="600519", days=7, limit=10)
        self.assertEqual(len(history), 1)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            self.assertEqual(row.query_id, "query_001")
            self.assertIsNotNone(row.context_snapshot)
            self.assertEqual(row.ideal_buy, 125.5)
            self.assertEqual(row.secondary_buy, 120.0)
            self.assertEqual(row.stop_loss, 110.0)
            self.assertEqual(row.take_profit, 150.0)

    def test_history_display_rebuilds_market_phase_summary_for_legacy_cn_snapshot(self) -> None:
        result = self._build_result()
        result.code = "005930"
        result.name = "Samsung Electronics"
        persisted_phase_summary = {
            **_market_phase_summary(),
            "phase": "postmarket",
            "market_local_time": "2026-01-01T10:00:00+08:00",
            "session_date": "2026-01-01",
            "effective_daily_bar_date": "2025-12-31",
            "is_market_open_now": False,
            "is_partial_bar": False,
            "minutes_to_open": 900,
            "minutes_to_close": None,
            "trigger_source": "scheduled_job",
            "analysis_intent": "postmarket",
            "warnings": ["legacy_snapshot"],
        }

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_kr_legacy_snapshot",
            report_type="simple",
            news_content="news",
            context_snapshot={"market_phase_summary": persisted_phase_summary},
            save_snapshot=True,
        )
        self.assertGreater(saved, 0)

        service = HistoryService(self.db)
        with patch("src.application.history.read_model.resolve_index_stock_code", return_value="005930.KS"):
            items = service.get_history_list(page=1, limit=5)["items"]

        self.assertEqual(items[0]["stock_code"], "005930.KS")
        rebuilt = items[0]["market_phase_summary"]
        self.assertIsNotNone(rebuilt)
        self.assertEqual(rebuilt["market"], "kr")
        self.assertEqual(rebuilt["market_local_time"], "2026-01-01T11:00:00+09:00")
        self.assertEqual(rebuilt["effective_daily_bar_date"], "2025-12-30")
        self.assertIsNone(rebuilt["minutes_to_open"])

    def test_save_analysis_history_without_snapshot(self) -> None:
        """关闭快照保存时不写入 context_snapshot"""
        result = self._build_result()

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_002",
            report_type="simple",
            news_content="新闻摘要",
            context_snapshot={"foo": "bar"},
            save_snapshot=False
        )

        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            self.assertIsNone(row.context_snapshot)

    def test_update_analysis_history_diagnostics_preserves_snapshot_fields(self) -> None:
        """通知发送后补写 diagnostics 时，不应覆盖已有上下文字段。"""
        saved = self.db.save_analysis_history(
            result=self._build_result(),
            query_id="query_diag_patch",
            report_type="simple",
            news_content="新闻摘要",
            context_snapshot={
                "enhanced_context": {"code": "600519"},
                "diagnostics": {
                    "trace_id": "trace-1",
                    "query_id": "query_diag_patch",
                    "stock_code": "600519",
                    "notification_runs": [],
                },
            },
            save_snapshot=True,
        )
        self.assertGreater(saved, 0)

        updated = self.db.update_analysis_history_diagnostics(
            query_id="query_diag_patch",
            code="600519",
            notification_runs=[
                {
                    "channel": "report",
                    "status": "success",
                    "success": True,
                }
            ],
        )

        self.assertEqual(updated, 1)
        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(
                AnalysisHistory.query_id == "query_diag_patch"
            ).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            snapshot = json.loads(row.context_snapshot or "{}")
            self.assertEqual(snapshot["enhanced_context"]["code"], "600519")
            notification_run = snapshot["diagnostics"]["notification_runs"][-1]
            self.assertEqual(notification_run["status"], "success")
            self.assertEqual(notification_run["trace_id"], "trace-1")

    def test_history_detail_uses_fundamental_snapshot_fallback_when_context_missing(self) -> None:
        """When context_snapshot is disabled, detail API should fallback to fundamental_snapshot."""
        if get_history_detail is None:
            self.skipTest("fastapi is not installed in this test environment")

        result = self._build_result()
        query_id = "query_fundamental_fallback_001"
        saved = self.db.save_analysis_history(
            result=result,
            query_id=query_id,
            report_type="simple",
            news_content="新闻摘要",
            context_snapshot=None,
            save_snapshot=False,
        )
        self.assertGreater(saved, 0)

        self.db.save_fundamental_snapshot(
            query_id=query_id,
            code="600519",
            payload={
                "belong_boards": [{"name": "白酒", "type": "行业"}],
                "boards": {
                    "data": {
                        "top": [{"name": "白酒", "change_pct": 2.6}],
                        "bottom": [],
                    }
                },
                "concept_boards": {
                    "data": {
                        "top": [{"name": "机器人概念", "change_pct": 4.2}],
                        "bottom": [],
                    }
                },
                "earnings": {
                    "data": {
                        "financial_report": {"report_date": "2025-12-31", "revenue": 1000},
                        "dividend": {"ttm_dividend_yield_pct": 2.6, "ttm_cash_dividend_per_share": 1.3},
                    }
                }
            },
        )

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == query_id).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            record_id = row.id

        report = get_history_detail(str(record_id), service=self._history_service())
        self.assertEqual(report.details.financial_report["report_date"], "2025-12-31")
        self.assertEqual(report.details.dividend_metrics["ttm_dividend_yield_pct"], 2.6)
        self.assertEqual(report.details.belong_boards, [{"name": "白酒", "type": "行业"}])
        self.assertEqual(report.details.sector_rankings["top"][0]["name"], "白酒")
        self.assertEqual(report.details.concept_rankings["top"][0]["name"], "机器人概念")

    def test_history_detail_uses_raw_code_for_legacy_jp_kr_fundamental_snapshot(self) -> None:
        """Legacy bare JP/KR history rows should display suffixes but read snapshots by stored code."""
        if get_history_detail is None:
            self.skipTest("fastapi is not installed in this test environment")

        result = self._build_result()
        result.code = "005930"
        result.name = "Samsung Electronics"
        query_id = "query_kr_raw_fundamental_fallback"
        saved = self.db.save_analysis_history(
            result=result,
            query_id=query_id,
            report_type="simple",
            news_content="news",
            context_snapshot=None,
            save_snapshot=False,
        )
        self.assertGreater(saved, 0)

        self.db.save_fundamental_snapshot(
            query_id=query_id,
            code="005930",
            payload={
                "earnings": {
                    "data": {
                        "financial_report": {"report_date": "2025-12-31", "revenue": 1000},
                        "dividend": {"ttm_dividend_yield_pct": 2.6},
                    }
                }
            },
        )

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == query_id).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            record_id = row.id

        with patch("src.application.history.read_model.resolve_index_stock_code", return_value="005930.KS"):
            report = get_history_detail(str(record_id), service=self._history_service())

        self.assertEqual(report.meta.stock_code, "005930.KS")
        self.assertEqual(report.details.financial_report["report_date"], "2025-12-31")
        self.assertEqual(report.details.dividend_metrics["ttm_dividend_yield_pct"], 2.6)

    def test_history_detail_preserves_unavailable_board_rankings_state(self) -> None:
        """Failed board ranking blocks should remain unavailable in detail response."""
        if get_history_detail is None:
            self.skipTest("fastapi is not installed in this test environment")

        query_id = "query_fundamental_failed_boards_001"
        saved = self.db.save_analysis_history(
            result=self._build_result(),
            query_id=query_id,
            report_type="simple",
            news_content="新闻摘要",
            context_snapshot=None,
            save_snapshot=False,
        )
        self.assertGreater(saved, 0)

        fallback_fundamental = {
            "belong_boards": [{"name": "白酒", "type": "行业"}],
            "boards": {
                "status": "failed",
                "data": {},
            },
        }
        saved_snapshot = self.db.save_fundamental_snapshot(
            query_id=query_id,
            code="600519",
            payload=fallback_fundamental,
        )
        self.assertGreater(saved_snapshot, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == query_id).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            record_id = row.id

        report = get_history_detail(str(record_id), service=self._history_service())
        self.assertEqual(report.details.belong_boards, [{"name": "白酒", "type": "行业"}])
        self.assertIsNone(report.details.sector_rankings)

    def test_history_detail_returns_null_fundamental_fields_when_snapshot_absent(self) -> None:
        """Detail API should keep new fields nullable when no context/fundamental snapshot exists."""
        if get_history_detail is None:
            self.skipTest("fastapi is not installed in this test environment")

        query_id = "query_fundamental_fallback_002"
        saved = self.db.save_analysis_history(
            result=self._build_result(),
            query_id=query_id,
            report_type="simple",
            news_content="新闻摘要",
            context_snapshot=None,
            save_snapshot=False,
        )
        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == query_id).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            record_id = row.id

        report = get_history_detail(str(record_id), service=self._history_service())
        self.assertIsNone(report.details.financial_report)
        self.assertIsNone(report.details.dividend_metrics)
        self.assertEqual(report.details.belong_boards, [])
        self.assertIsNone(report.details.sector_rankings)

    def test_history_detail_returns_empty_related_boards_for_non_cn(self) -> None:
        if get_history_detail is None:
            self.skipTest("fastapi is not installed in this test environment")

        result = AnalysisResult(
            code="AAPL",
            name="Apple",
            sentiment_score=65,
            trend_prediction="Bullish",
            operation_advice="Hold",
            analysis_summary="US stock test",
        )
        query_id = "query_non_cn_board_001"
        saved = self.db.save_analysis_history(
            result=result,
            query_id=query_id,
            report_type="simple",
            news_content="news",
            context_snapshot=None,
            save_snapshot=False,
        )
        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == query_id).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            record_id = row.id

        report = get_history_detail(str(record_id), service=self._history_service())
        self.assertEqual(report.details.belong_boards, [])
        self.assertIsNone(report.details.sector_rankings)

    def test_history_detail_reads_agent_snapshot_related_boards_shape(self) -> None:
        """Agent-mode snapshots store fundamental_context/realtime_quote at the top level."""
        if get_history_detail is None:
            self.skipTest("fastapi is not installed in this test environment")

        context_snapshot = {
            "fundamental_context": {
                "belong_boards": [{"name": "白酒", "type": "行业"}],
                "boards": {
                    "data": {
                        "top": [{"name": "白酒", "change_pct": 2.8}],
                        "bottom": [],
                    }
                },
            },
            "realtime_quote": {
                "price": 1888.0,
                "change_pct": 1.56,
            },
        }
        query_id = "query_agent_snapshot_boards_001"
        saved = self.db.save_analysis_history(
            result=self._build_result(),
            query_id=query_id,
            report_type="simple",
            news_content="新闻摘要",
            context_snapshot=context_snapshot,
            save_snapshot=True,
        )
        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == query_id).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            record_id = row.id

        report = get_history_detail(str(record_id), service=self._history_service())
        self.assertEqual(report.meta.current_price, 1888.0)
        self.assertEqual(report.meta.change_pct, 1.56)
        self.assertEqual(report.details.belong_boards, [{"name": "白酒", "type": "行业"}])
        self.assertEqual(report.details.sector_rankings["top"][0]["name"], "白酒")

    def test_history_detail_returns_overview_and_sanitizes_snapshot(self) -> None:
        """History detail exposes the public overview separately from raw snapshot JSON."""
        if get_history_detail is None:
            self.skipTest("fastapi is not installed in this test environment")

        overview = _analysis_context_pack_overview()
        phase_summary = _market_phase_summary()
        query_id = "query_context_pack_overview_001"
        saved = self.db.save_analysis_history(
            result=self._build_result(),
            query_id=query_id,
            report_type="simple",
            news_content="新闻摘要",
            context_snapshot={
                "enhanced_context": {"code": "600519"},
                "analysis_context_pack_overview": overview,
                "market_phase_summary": {
                    **phase_summary,
                    "market_phase_context": {"raw": True},
                },
            },
            save_snapshot=True,
        )
        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == query_id).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            record_id = row.id

        report = get_history_detail(str(record_id), service=self._history_service())
        self.assertEqual(
            report.details.analysis_context_pack_overview.metadata.trigger_source,
            "api",
        )
        self.assertEqual(
            report.details.analysis_context_pack_overview.data_quality.overall_score,
            100,
        )
        self.assertIsNotNone(report.meta.market_phase_summary)
        self.assertEqual(report.meta.market_phase_summary.phase, "intraday")
        self.assertEqual(report.meta.market_phase_summary.minutes_to_close, 300)
        self.assertEqual(report.details.analysis_context_pack_overview.metadata.news_result_count, 2)
        self.assertNotIn(
            "analysis_context_pack_overview",
            report.details.context_snapshot,
        )
        self.assertNotIn(
            "market_phase_summary",
            report.details.context_snapshot,
        )

    def test_history_detail_handles_missing_overview_when_snapshot_disabled(self) -> None:
        """SAVE_CONTEXT_SNAPSHOT=false style records should not require an overview."""
        if get_history_detail is None:
            self.skipTest("fastapi is not installed in this test environment")

        query_id = "query_context_pack_snapshot_disabled_001"
        saved = self.db.save_analysis_history(
            result=self._build_result(),
            query_id=query_id,
            report_type="simple",
            news_content="新闻摘要",
            context_snapshot={
                "enhanced_context": {"code": "600519"},
                "analysis_context_pack_overview": _analysis_context_pack_overview(),
            },
            save_snapshot=False,
        )
        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == query_id).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            record_id = row.id
            self.assertIsNone(row.context_snapshot)

        report = get_history_detail(str(record_id), service=self._history_service())
        self.assertIsNone(report.meta.market_phase_summary)
        self.assertIsNone(report.details.analysis_context_pack_overview)
        self.assertIsNone(report.details.context_snapshot)

    def test_history_detail_restores_market_structure_from_raw_result_without_snapshot(self) -> None:
        """SAVE_CONTEXT_SNAPSHOT=false should still expose market_structure saved in raw_result."""
        if get_history_detail is None:
            self.skipTest("fastapi is not installed in this test environment")

        market_structure = {
            "schema_version": "market-structure-v1",
            "status": "partial",
            "market": "cn",
            "market_theme_context": {
                "schema_version": "market-theme-v1",
                "status": "partial",
                "market": "cn",
                "active_themes": [{"name": "机器人概念"}],
            },
            "stock_market_position": {
                "schema_version": "stock-market-position-v1",
                "status": "partial",
                "stock_code": "300024",
                "market": "cn",
                "primary_theme": {"name": "机器人概念"},
            },
        }
        result = self._build_result()
        result.market_structure_context = market_structure
        query_id = "query_market_structure_snapshot_disabled_001"
        saved = self.db.save_analysis_history(
            result=result,
            query_id=query_id,
            report_type="simple",
            news_content="新闻摘要",
            context_snapshot={"market_structure_context": {"ignored": True}},
            save_snapshot=False,
        )
        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == query_id).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            self.assertIsNone(row.context_snapshot)
            record_id = row.id

        report = get_history_detail(str(record_id), service=self._history_service())
        self.assertIsNone(report.details.context_snapshot)
        self.assertEqual(
            report.details.market_structure["market_theme_context"]["active_themes"][0]["name"],
            "机器人概念",
        )
        self.assertEqual(
            report.details.raw_result["market_structure_context"]["market_theme_context"]["active_themes"][0]["name"],
            "机器人概念",
        )
        self.assertNotIn(
            "raw_result",
            report.details.raw_result,
        )
