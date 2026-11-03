"""Tests for backtest phases."""

from tests.application.backtest._backtest_service_support import (
    AnalysisHistory,
    BacktestRepository,
    BacktestResult,
    BacktestService,
    StockDaily,
    _BacktestServiceTestCaseFixture,
    _phase_snapshot,
    date,
    datetime,
    json,
    patch,
    unittest,
)


class BacktestServiceTestCase(_BacktestServiceTestCaseFixture, unittest.TestCase):
    def test_get_candidates_does_not_match_explicit_wrong_a_share_market(self) -> None:
        repo = BacktestRepository(self.db)
        for invalid_code in ("600519.SZ", "SH000001", "000001.SH", "920748.SH", "SH920748"):
            with self.subTest(invalid_code=invalid_code):
                matches = repo.get_candidates(
                    code=invalid_code,
                    min_age_days=0,
                    limit=10,
                    eval_window_days=3,
                    engine_version="v1",
                    force=True,
                )
                self.assertEqual(matches, [])

    def test_run_backtest_rejects_invalid_market_suffix_length_input(self) -> None:
        service = self._service()
        with self.assertRaisesRegex(ValueError, "非法股票代码格式"):
            service.run_backtest(
                code="600519.HK",
                force=False,
                eval_window_days=3,
                min_age_days=0,
                analysis_date_from=date(2024, 1, 1),
                analysis_date_to=date(2024, 1, 1),
                limit=10,
            )

    def test_run_backtest_rejects_explicit_wrong_a_share_market(self) -> None:
        service = self._service()
        for invalid_code in ("600519.SZ", "SH000001", "000001.SH", "920748.SH", "SH920748"):
            with self.subTest(invalid_code=invalid_code):
                with self.assertRaisesRegex(ValueError, "非法股票代码格式"):
                    service.run_backtest(
                        code=invalid_code,
                        force=False,
                        eval_window_days=3,
                        min_age_days=0,
                        analysis_date_from=date(2024, 1, 1),
                        analysis_date_to=date(2024, 1, 1),
                        limit=10,
                    )

    def test_get_recent_evaluations_rejects_explicit_wrong_a_share_market(self) -> None:
        service = self._service()
        for invalid_code in ("600519.SZ", "SH000001", "000001.SH", "920748.SH", "SH920748"):
            with self.subTest(invalid_code=invalid_code):
                with self.assertRaisesRegex(ValueError, "非法股票代码格式"):
                    service.get_recent_evaluations(
                        code=invalid_code,
                        eval_window_days=3,
                        limit=10,
                        page=1,
                        analysis_date_from=date(2024, 1, 1),
                        analysis_date_to=date(2024, 1, 1),
                    )

    def test_run_backtest_rebuilds_legacy_cn_snapshot_for_jp_history(self) -> None:
        legacy_snapshot = json.dumps(
            {
                "enhanced_context": {"date": "2026-01-01"},
                "market_phase_summary": {
                    "market": "cn",
                    "phase": "postmarket",
                    "market_local_time": "2026-01-01T10:00:00+08:00",
                    "session_date": "2026-01-01",
                    "effective_daily_bar_date": "2025-12-31",
                    "is_trading_day": True,
                    "is_market_open_now": False,
                    "is_partial_bar": False,
                    "trigger_source": "scheduled_job",
                    "analysis_intent": "postmarket",
                    "warnings": ["legacy_snapshot"],
                },
            }
        )
        with self.db.get_session() as session:
            session.add(
                AnalysisHistory(
                    query_id="q_jp_legacy_cn_snapshot",
                    code="7203.T",
                    name="Toyota",
                    report_type="simple",
                    sentiment_score=60,
                    operation_advice="买入",
                    trend_prediction="看多",
                    analysis_summary="legacy CN phase snapshot",
                    stop_loss=None,
                    take_profit=None,
                    created_at=datetime(2026, 1, 1, 0, 0, 0),
                    context_snapshot=legacy_snapshot,
                )
            )
            session.add_all(
                [
                    StockDaily(
                        code="7203.T",
                        date=date(2025, 12, 30),
                        open=100.0,
                        high=100.0,
                        low=100.0,
                        close=100.0,
                    ),
                    StockDaily(
                        code="7203.T",
                        date=date(2026, 1, 5),
                        open=105.0,
                        high=106.0,
                        low=104.0,
                        close=105.0,
                    ),
                ]
            )
            session.commit()

        service = self._service()
        with patch.object(service, "_try_fill_daily_data") as refill:
            stats = service.run_backtest(
                code="7203.T",
                force=False,
                eval_window_days=1,
                min_age_days=0,
                analysis_date_from=date(2026, 1, 1),
                analysis_date_to=date(2026, 1, 1),
                limit=10,
            )

        refill.assert_not_called()
        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["insufficient"], 0)
        with self.db.get_session() as session:
            result = (
                session.query(BacktestResult)
                .filter(BacktestResult.code == "7203.T")
                .one()
            )
            self.assertEqual(result.eval_status, "completed")
            self.assertEqual(result.analysis_date, date(2026, 1, 1))
            self.assertEqual(result.start_price, 100.0)
            self.assertEqual(result.end_close, 105.0)

    def test_run_backtest_filters_by_snapshot_analysis_date_not_created_at(self) -> None:
        with self.db.get_session() as session:
            session.add(
                AnalysisHistory(
                    query_id="q-created-at-mismatch",
                    code="000003",
                    name="测试股票",
                    report_type="simple",
                    sentiment_score=60,
                    operation_advice="买入",
                    trend_prediction="看多",
                    analysis_summary="created_at differs from analysis date",
                    stop_loss=None,
                    take_profit=None,
                    created_at=datetime(2024, 1, 10, 0, 0, 0),
                    context_snapshot=_phase_snapshot(
                        date(2024, 1, 1),
                        phase="postmarket",
                        market="cn",
                        effective_date=date(2024, 1, 1),
                    ),
                )
            )
            session.add(
                StockDaily(code="000003", date=date(2024, 1, 1), open=10.0, high=10.0, low=10.0, close=10.0)
            )
            session.add_all(
                [
                    StockDaily(code="000003", date=date(2024, 1, 2), high=10.5, low=9.8, close=10.2),
                    StockDaily(code="000003", date=date(2024, 1, 3), high=10.8, low=10.1, close=10.5),
                    StockDaily(code="000003", date=date(2024, 1, 4), high=11.0, low=10.4, close=10.8),
                ]
            )
            session.commit()

        service = self._service()
        stats = service.run_backtest(
            code="000003",
            force=False,
            eval_window_days=3,
            min_age_days=0,
            analysis_date_from=date(2024, 1, 1),
            analysis_date_to=date(2024, 1, 1),
            limit=10,
        )

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["completed"], 1)
        with self.db.get_session() as session:
            result = session.query(BacktestResult).filter(BacktestResult.code == "000003").one()
            self.assertEqual(result.analysis_date, date(2024, 1, 1))

    def test_date_filtered_rerun_aligns_legacy_result_date_to_snapshot_date(self) -> None:
        with self.db.get_session() as session:
            history = AnalysisHistory(
                query_id="q-legacy-result-date",
                code="000005",
                name="测试股票",
                report_type="simple",
                sentiment_score=60,
                operation_advice="买入",
                trend_prediction="看多",
                analysis_summary="legacy result stores fallback trading date",
                stop_loss=None,
                take_profit=None,
                created_at=datetime(2024, 1, 7, 0, 0, 0),
                context_snapshot='{"enhanced_context": {"date": "2024-01-07"}}',
            )
            session.add(history)
            session.flush()
            session.add(
                BacktestResult(
                    analysis_history_id=history.id,
                    code="000005",
                    analysis_date=date(2024, 1, 5),
                    eval_window_days=1,
                    engine_version="v1",
                    eval_status="completed",
                    evaluated_at=datetime(2024, 1, 8, 0, 0, 0),
                    operation_advice="买入",
                    position_recommendation="long",
                    start_price=10.0,
                    end_close=10.5,
                    stock_return_pct=5.0,
                    direction_expected="up",
                    direction_correct=True,
                    outcome="win",
                    simulated_return_pct=5.0,
                )
            )
            session.commit()

        service = self._service()
        stats = service.run_backtest(
            code="000005",
            force=False,
            eval_window_days=1,
            min_age_days=0,
            analysis_date_from=date(2024, 1, 7),
            analysis_date_to=date(2024, 1, 7),
            limit=10,
        )

        self.assertEqual(stats["processed"], 0)
        self.assertEqual(stats["saved"], 0)
        self.assertEqual(stats["diagnostics"]["empty_reason"], "no_new_results")
        self.assertEqual(stats["diagnostics"]["aligned_existing_result_dates"], 1)
        with self.db.get_session() as session:
            result = session.query(BacktestResult).filter(BacktestResult.code == "000005").one()
            self.assertEqual(result.analysis_date, date(2024, 1, 7))

        data = service.get_recent_evaluations(
            code="000005",
            eval_window_days=1,
            limit=10,
            page=1,
            analysis_date_from=date(2024, 1, 7),
            analysis_date_to=date(2024, 1, 7),
        )
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["analysis_date"], "2024-01-07")

    def test_phase_filter_results_allows_exact_dynamic_cap(self) -> None:
        service = self._service()
        phase_snapshot = json.dumps({"market_phase_summary": {"phase": "intraday", "market": "cn"}})
        raw_result = json.dumps(
            {
                "operation_advice": "持有观察",
                "action": "watch",
                "action_label": "观望",
                "guardrail_reason": "模型判定观望，保留原始动作",
            },
            ensure_ascii=False,
        )
        rows = [
            (
                self._make_backtest_result(analysis_history_id=idx + 1, analysis_date=date(2024, 1, idx + 1)),
                "贵州茅台",
                "看多",
                datetime(2024, 1, idx + 1, 0, 0, 0),
                phase_snapshot,
                raw_result,
                "simple",
                78,
            )
            for idx in range(2)
        ]

        class RepoStub:
            def get_results_with_context_batch(self, **kwargs):
                offset = int(kwargs["offset"])
                limit = int(kwargs["limit"])
                return rows[offset: offset + limit]

        service.repo = RepoStub()

        with patch.object(BacktestService, "MAX_DYNAMIC_SUMMARY_ROWS", 2):
            data = service.get_recent_evaluations(
                code="600519",
                eval_window_days=1,
                limit=10,
                page=1,
                analysis_phase="intraday",
            )

        self.assertEqual(data["total"], 2)
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["items"][0]["action"], "watch")
        self.assertEqual(data["items"][0]["action_label"], "观望")

    def test_phase_filter_buckets_detailed_internal_phases(self) -> None:
        self._seed_analysis(
            query_id="q2",
            analysis_date=date(2024, 1, 10),
            created_at=datetime(2024, 1, 10, 0, 0, 0),
            operation_advice="买入",
            trend_prediction="看多",
            start_close=100.0,
            forward_bars=[
                StockDaily(code="600519", date=date(2024, 1, 11), high=101.0, low=95.0, close=96.0),
            ],
            phase="lunch_break",
        )
        self._seed_analysis(
            query_id="q3",
            analysis_date=date(2024, 1, 12),
            created_at=datetime(2024, 1, 12, 0, 0, 0),
            operation_advice="买入",
            trend_prediction="看多",
            start_close=100.0,
            forward_bars=[
                StockDaily(code="600519", date=date(2024, 1, 13), high=101.0, low=95.0, close=96.0),
            ],
            phase="closing_auction",
        )
        self._seed_analysis(
            query_id="q4",
            analysis_date=date(2024, 1, 14),
            created_at=datetime(2024, 1, 14, 0, 0, 0),
            operation_advice="买入",
            trend_prediction="看多",
            start_close=100.0,
            forward_bars=[
                StockDaily(code="600519", date=date(2024, 1, 15), high=101.0, low=95.0, close=96.0),
            ],
            phase="non_trading",
        )

        service = self._service()
        service.run_backtest(code="600519", force=False, eval_window_days=1, min_age_days=0, limit=20)

        intraday = service.get_recent_evaluations(
            code="600519",
            eval_window_days=1,
            limit=10,
            page=1,
            analysis_phase="intraday",
        )
        self.assertEqual(intraday["total"], 2)
        self.assertEqual(
            {item["market_phase_summary"]["phase"] for item in intraday["items"]},
            {"lunch_break", "closing_auction"},
        )
        self.assertTrue(all(item["market_phase"] == "intraday" for item in intraday["items"]))

        unknown = service.get_recent_evaluations(
            code="600519",
            eval_window_days=1,
            limit=10,
            page=1,
            analysis_phase="unknown",
        )
        self.assertEqual(unknown["total"], 1)
        self.assertEqual(unknown["items"][0]["market_phase"], "unknown")
        self.assertEqual(unknown["items"][0]["market_phase_summary"]["phase"], "non_trading")

    def test_run_backtest_excludes_market_review_records(self) -> None:
        with self.db.get_session() as session:
            session.add(
                AnalysisHistory(
                    query_id="q-market-review",
                    code="MARKET",
                    name="大盘复盘",
                    report_type="market_review",
                    sentiment_score=50,
                    operation_advice="查看复盘",
                    trend_prediction="大盘复盘",
                    analysis_summary="market review summary",
                    stop_loss=None,
                    take_profit=None,
                    created_at=datetime(2024, 1, 3, 0, 0, 0),
                    context_snapshot='{"enhanced_context": {"date": "2024-01-03"}}',
                )
            )
            session.commit()

        service = self._service()
        stats = service.run_backtest(code=None, force=False, eval_window_days=3, min_age_days=0, limit=10)

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["saved"], 1)
        self.assertEqual(self._count_results(), 1)
        with self.db.get_session() as session:
            self.assertEqual(
                session.query(BacktestResult).filter(BacktestResult.code == "MARKET").count(),
                0,
            )
