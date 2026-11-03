"""Tests for backtest summaries."""

from tests.application.backtest._backtest_service_support import (
    AnalysisHistory,
    BacktestResult,
    BacktestService,
    BacktestSummary,
    OVERALL_SENTINEL_CODE,
    StockDaily,
    _BacktestServiceTestCaseFixture,
    _phase_snapshot,
    date,
    datetime,
    patch,
    unittest,
)


class BacktestServiceTestCase(_BacktestServiceTestCaseFixture, unittest.TestCase):
    def test_run_backtest_matches_compact_prefixed_analysis_history_with_canonical_query(self) -> None:
        with self.db.get_session() as session:
            session.add(
                AnalysisHistory(
                    query_id="q_compact_history_sh",
                    code="SH600519",
                    name="贵州茅台",
                    report_type="simple",
                    sentiment_score=60,
                    operation_advice="买入",
                    trend_prediction="看多",
                    analysis_summary="compact history code with canonical query",
                    stop_loss=None,
                    take_profit=None,
                    created_at=datetime(2024, 2, 15, 0, 0, 0),
                    context_snapshot=_phase_snapshot(
                        date(2024, 2, 15),
                        phase="postmarket",
                        market="cn",
                        effective_date=date(2024, 2, 15),
                    ),
                )
            )
            session.add(
                StockDaily(
                    code="SH600519",
                    date=date(2024, 2, 15),
                    open=100.0,
                    high=100.0,
                    low=100.0,
                    close=100.0,
                )
            )
            session.add_all(
                [
                    StockDaily(code="SH600519", date=date(2024, 2, 16), high=102.0, low=99.0, close=101.0),
                    StockDaily(code="SH600519", date=date(2024, 2, 17), high=104.0, low=100.0, close=103.0),
                ]
            )
            session.commit()

        service = self._service()
        stats = service.run_backtest(
            code="600519",
            force=False,
            eval_window_days=2,
            min_age_days=0,
            analysis_date_from=date(2024, 2, 15),
            analysis_date_to=date(2024, 2, 15),
            limit=10,
        )

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["saved"], 1)
        self.assertEqual(stats["completed"], 1)

        data = service.get_recent_evaluations(code="SH600519", eval_window_days=2, limit=10, page=1)
        self.assertEqual(data["total"], 1)

    def test_run_backtest_matches_compact_bj_code_shape_with_no_prefix_query(self) -> None:
        with self.db.get_session() as session:
            session.add(
                AnalysisHistory(
                    query_id="q_compact_history_bj",
                    code="BJ920748",
                    name="可转债",
                    report_type="simple",
                    sentiment_score=60,
                    operation_advice="买入",
                    trend_prediction="看多",
                    analysis_summary="BJ compact history code without query prefix",
                    stop_loss=None,
                    take_profit=None,
                    created_at=datetime(2024, 4, 1, 0, 0, 0),
                    context_snapshot=_phase_snapshot(
                        date(2024, 4, 1),
                        phase="postmarket",
                        market="cn",
                        effective_date=date(2024, 4, 1),
                    ),
                )
            )
            session.add(
                StockDaily(
                    code="BJ920748",
                    date=date(2024, 4, 1),
                    open=200.0,
                    high=200.0,
                    low=200.0,
                    close=200.0,
                )
            )
            session.add_all(
                [
                    StockDaily(code="BJ920748", date=date(2024, 4, 2), high=210.0, low=198.0, close=205.0),
                    StockDaily(code="BJ920748", date=date(2024, 4, 3), high=215.0, low=202.0, close=210.0),
                ]
            )
            session.commit()

        service = self._service()
        stats = service.run_backtest(
            code="920748",
            force=False,
            eval_window_days=2,
            min_age_days=0,
            analysis_date_from=date(2024, 4, 1),
            analysis_date_to=date(2024, 4, 1),
            limit=10,
        )

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["saved"], 1)
        self.assertEqual(stats["completed"], 1)

        data = service.get_recent_evaluations(code="BJ920748", eval_window_days=2, limit=10, page=1)
        self.assertEqual(data["total"], 1)

    def test_get_summary_rejects_explicit_wrong_a_share_market(self) -> None:
        service = self._service()
        for invalid_code in ("600519.SZ", "SH000001", "000001.SH", "920748.SH", "SH920748"):
            with self.subTest(invalid_code=invalid_code):
                with self.assertRaisesRegex(ValueError, "非法股票代码格式"):
                    service.get_summary(
                        scope="stock",
                        code=invalid_code,
                        eval_window_days=3,
                        analysis_date_from=date(2024, 1, 1),
                        analysis_date_to=date(2024, 1, 1),
                    )

    def test_run_backtest_supports_dotted_hk_prefix_query_shape(self) -> None:
        with self.db.get_session() as session:
            session.add(
                AnalysisHistory(
                    query_id="q_hk_query_dot",
                    code="HK01810",
                    name="恒生指数成份股",
                    report_type="simple",
                    sentiment_score=60,
                    operation_advice="买入",
                    trend_prediction="看多",
                    analysis_summary="HK prefixed history with dotted query",
                    stop_loss=None,
                    take_profit=None,
                    created_at=datetime(2024, 1, 1, 0, 0, 0),
                    context_snapshot=_phase_snapshot(
                        date(2024, 1, 1),
                        phase="postmarket",
                        market="hk",
                        effective_date=date(2024, 1, 1),
                    ),
                )
            )
            session.add(
                StockDaily(
                    code="HK01810",
                    date=date(2024, 1, 1),
                    open=90.0,
                    high=90.0,
                    low=90.0,
                    close=90.0,
                )
            )
            session.add_all(
                [
                    StockDaily(
                        code="HK01810",
                        date=date(2024, 1, 2),
                        high=92.0,
                        low=88.0,
                        close=91.0,
                    ),
                ]
            )
            session.commit()

        service = self._service()
        stats = service.run_backtest(
            code="HK.01810",
            force=False,
            eval_window_days=1,
            min_age_days=0,
            analysis_date_from=date(2024, 1, 1),
            analysis_date_to=date(2024, 1, 1),
            limit=10,
        )
        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["saved"], 1)
        self.assertEqual(stats["completed"], 1)

        results = service.get_recent_evaluations(
            code="HK.01810",
            eval_window_days=1,
            limit=10,
            page=1,
            analysis_date_from=date(2024, 1, 1),
            analysis_date_to=date(2024, 1, 1),
        )
        self.assertEqual(results["total"], 1)

        summary = service.get_summary(
            scope="stock",
            code="HK.01810",
            eval_window_days=1,
            analysis_date_from=date(2024, 1, 1),
            analysis_date_to=date(2024, 1, 1),
        )
        self.assertIsNotNone(summary)
        self.assertEqual(summary["code"], "01810")

    def test_summaries_created_after_run(self) -> None:
        """Verify both overall and per-stock BacktestSummary rows are created."""
        service = self._service()
        service.run_backtest(code="600519", force=False, eval_window_days=3, min_age_days=0, limit=10)

        with self.db.get_session() as session:
            # Overall summary uses sentinel code
            overall = session.query(BacktestSummary).filter(
                BacktestSummary.scope == "overall",
                BacktestSummary.code == OVERALL_SENTINEL_CODE,
            ).first()
            self.assertIsNotNone(overall)
            self.assertEqual(overall.total_evaluations, 1)
            self.assertEqual(overall.completed_count, 1)
            self.assertEqual(overall.win_count, 1)
            self.assertEqual(overall.loss_count, 0)
            self.assertAlmostEqual(overall.win_rate_pct, 100.0)

            # Stock-level summary
            stock = session.query(BacktestSummary).filter(
                BacktestSummary.scope == "stock",
                BacktestSummary.code == "600519",
            ).first()
            self.assertIsNotNone(stock)
            self.assertEqual(stock.total_evaluations, 1)
            self.assertEqual(stock.completed_count, 1)
            self.assertEqual(stock.win_count, 1)

    def test_get_summary_overall_returns_sentinel_as_none(self) -> None:
        """Verify get_summary translates __overall__ sentinel back to None."""
        service = self._service()
        service.run_backtest(code="600519", force=False, eval_window_days=3, min_age_days=0, limit=10)

        summary = service.get_summary(scope="overall", code=None)
        self.assertIsNotNone(summary)
        self.assertIsNone(summary["code"])
        self.assertEqual(summary["scope"], "overall")
        self.assertEqual(summary["win_count"], 1)

    def test_agent_learning_summary_helpers_keep_skill_rollups_neutral_until_supported(self) -> None:
        service = self._service()
        service.run_backtest(code="600519", force=False, eval_window_days=3, min_age_days=0, limit=10)

        global_summary = service.get_global_summary(eval_window_days=3)
        stock_summary = service.get_stock_summary("600519", eval_window_days=3)
        skill_summary = service.get_skill_summary("bull_trend", eval_window_days=3)
        strategy_summary = service.get_strategy_summary("bull_trend", eval_window_days=3)

        self.assertIsNotNone(global_summary)
        self.assertEqual(global_summary["total_evaluations"], 1)
        self.assertAlmostEqual(global_summary["win_rate"], 1.0)
        self.assertAlmostEqual(global_summary["direction_accuracy"], 1.0)
        self.assertAlmostEqual(global_summary["avg_return"], 0.10)

        self.assertIsNotNone(stock_summary)
        self.assertEqual(stock_summary["code"], "600519")
        self.assertAlmostEqual(stock_summary["win_rate"], 1.0)

        self.assertIsNone(skill_summary)
        self.assertIsNone(strategy_summary)

    def test_get_summary_supports_analysis_date_range(self) -> None:
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
        )

        service = self._service()
        service.run_backtest(code="600519", force=False, eval_window_days=1, min_age_days=0, limit=20)

        summary = service.get_summary(
            scope="stock",
            code="600519",
            eval_window_days=1,
            analysis_date_from=date(2024, 1, 10),
            analysis_date_to=date(2024, 1, 10),
        )
        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertEqual(summary["total_evaluations"], 1)
        self.assertEqual(summary["completed_count"], 1)
        self.assertEqual(summary["win_count"], 0)
        self.assertEqual(summary["loss_count"], 1)
        self.assertAlmostEqual(summary["direction_accuracy_pct"], 0.0)

    def test_get_summary_date_range_filters_to_single_window_and_engine(self) -> None:
        service = self._service()
        service.run_backtest(code="600519", force=False, eval_window_days=3, min_age_days=0, limit=10)

        with self.db.get_session() as session:
            base_result = session.query(BacktestResult).filter(
                BacktestResult.code == "600519",
                BacktestResult.eval_window_days == 3,
                BacktestResult.engine_version == "v1",
            ).one()
            session.add_all([
                BacktestResult(
                    analysis_history_id=base_result.analysis_history_id,
                    code=base_result.code,
                    analysis_date=base_result.analysis_date,
                    eval_window_days=1,
                    engine_version="v1",
                    eval_status="completed",
                    evaluated_at=datetime(2024, 1, 5, 0, 0, 0),
                    operation_advice="买入",
                    position_recommendation="long",
                    start_price=100.0,
                    end_close=96.0,
                    stock_return_pct=-4.0,
                    direction_expected="up",
                    direction_correct=False,
                    outcome="loss",
                    simulated_return_pct=-4.0,
                ),
                BacktestResult(
                    analysis_history_id=base_result.analysis_history_id,
                    code=base_result.code,
                    analysis_date=base_result.analysis_date,
                    eval_window_days=3,
                    engine_version="v2",
                    eval_status="completed",
                    evaluated_at=datetime(2024, 1, 6, 0, 0, 0),
                    operation_advice="买入",
                    position_recommendation="long",
                    start_price=100.0,
                    end_close=96.0,
                    stock_return_pct=-4.0,
                    direction_expected="up",
                    direction_correct=False,
                    outcome="loss",
                    simulated_return_pct=-4.0,
                ),
            ])
            session.commit()

        rows = service.repo.list_results(
            code="600519",
            eval_window_days=3,
            engine_version="v1",
            analysis_date_from=date(2024, 1, 1),
            analysis_date_to=date(2024, 1, 1),
        )
        self.assertEqual(len(rows), 1)

        evaluations = service.get_recent_evaluations(
            code="600519",
            eval_window_days=3,
            limit=10,
            page=1,
            analysis_date_from=date(2024, 1, 1),
            analysis_date_to=date(2024, 1, 1),
        )
        self.assertEqual(evaluations["total"], 1)
        self.assertEqual(len(evaluations["items"]), 1)
        self.assertEqual(evaluations["items"][0]["engine_version"], "v1")
        self.assertEqual(evaluations["items"][0]["operation_advice"], "买入")
        self.assertEqual(evaluations["items"][0]["action"], "buy")
        self.assertEqual(evaluations["items"][0]["action_label"], "买入")
        self.assertEqual(evaluations["items"][0]["position_recommendation"], "long")

        # Without explicit eval_window_days, summary infers the smallest
        # window from matched rows (window=1 in this dataset) instead of
        # falling back to the config default.
        summary_inferred = service.get_summary(
            scope="stock",
            code="600519",
            analysis_date_from=date(2024, 1, 1),
            analysis_date_to=date(2024, 1, 1),
        )
        self.assertIsNotNone(summary_inferred)
        assert summary_inferred is not None
        self.assertEqual(summary_inferred["eval_window_days"], 1)
        self.assertEqual(summary_inferred["engine_version"], "v1")
        self.assertEqual(summary_inferred["total_evaluations"], 1)
        self.assertEqual(summary_inferred["completed_count"], 1)
        self.assertEqual(summary_inferred["win_count"], 0)
        self.assertEqual(summary_inferred["loss_count"], 1)
        self.assertAlmostEqual(summary_inferred["direction_accuracy_pct"], 0.0)

        # With explicit eval_window_days=3, summary filters to that window only.
        summary_explicit = service.get_summary(
            scope="stock",
            code="600519",
            eval_window_days=3,
            analysis_date_from=date(2024, 1, 1),
            analysis_date_to=date(2024, 1, 1),
        )
        self.assertIsNotNone(summary_explicit)
        assert summary_explicit is not None
        self.assertEqual(summary_explicit["eval_window_days"], 3)
        self.assertEqual(summary_explicit["engine_version"], "v1")
        self.assertEqual(summary_explicit["total_evaluations"], 1)
        self.assertEqual(summary_explicit["completed_count"], 1)
        self.assertEqual(summary_explicit["win_count"], 1)
        self.assertEqual(summary_explicit["loss_count"], 0)
        self.assertAlmostEqual(summary_explicit["direction_accuracy_pct"], 100.0)

    def test_get_summary_date_range_rejects_excessive_row_counts(self) -> None:
        service = self._service()
        service.run_backtest(code="600519", force=False, eval_window_days=3, min_age_days=0, limit=10)

        with patch.object(BacktestService, "MAX_DYNAMIC_SUMMARY_ROWS", 0):
            with self.assertRaisesRegex(ValueError, "Date-filtered summary matches too many rows"):
                service.get_summary(
                    scope="stock",
                    code="600519",
                    analysis_date_from=date(2024, 1, 1),
                    analysis_date_to=date(2024, 1, 1),
                )

    def test_get_summary_phase_filter_cap_uses_phase_candidate_message(self) -> None:
        service = self._service()
        service.run_backtest(code="600519", force=False, eval_window_days=3, min_age_days=0, limit=10)

        with patch.object(BacktestService, "MAX_DYNAMIC_SUMMARY_ROWS", 0):
            with self.assertRaisesRegex(ValueError, "Phase-filtered summary candidate set matches too many rows"):
                service.get_summary(
                    scope="stock",
                    code="600519",
                    analysis_phase="intraday",
                )

    def test_phase_filter_without_window_matches_summary_window(self) -> None:
        service = self._service()
        service.run_backtest(code="600519", force=False, eval_window_days=3, min_age_days=0, limit=10)

        with self.db.get_session() as session:
            base_result = session.query(BacktestResult).filter(
                BacktestResult.code == "600519",
                BacktestResult.eval_window_days == 3,
                BacktestResult.engine_version == "v1",
            ).one()
            session.add(
                BacktestResult(
                    analysis_history_id=base_result.analysis_history_id,
                    code=base_result.code,
                    analysis_date=base_result.analysis_date,
                    eval_window_days=1,
                    engine_version="v1",
                    eval_status="completed",
                    evaluated_at=datetime(2024, 1, 5, 0, 0, 0),
                    operation_advice="买入",
                    position_recommendation="long",
                    start_price=100.0,
                    end_close=96.0,
                    stock_return_pct=-4.0,
                    direction_expected="up",
                    direction_correct=False,
                    outcome="loss",
                    simulated_return_pct=-4.0,
                )
            )
            session.commit()

        evaluations = service.get_recent_evaluations(
            code="600519",
            limit=10,
            page=1,
            analysis_phase="premarket",
        )
        self.assertEqual(evaluations["total"], 1)
        self.assertEqual(evaluations["items"][0]["eval_window_days"], 1)

        summary = service.get_summary(
            scope="stock",
            code="600519",
            analysis_phase="premarket",
        )
        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertEqual(summary["eval_window_days"], 1)
        self.assertEqual(summary["total_evaluations"], 1)

    def test_phase_filter_rejects_values_outside_public_query_contract(self) -> None:
        service = self._service()

        with self.assertRaisesRegex(ValueError, "analysis_phase must be one of"):
            service.get_recent_evaluations(code=None, analysis_phase="lunch_break")

        with self.assertRaisesRegex(ValueError, "analysis_phase must be one of"):
            service.get_summary(code=None, scope="overall", analysis_phase="banana")

    def test_multi_stock_summaries(self) -> None:
        """Verify separate summaries for multiple stocks + correct overall aggregate."""
        old_created_at = datetime(2024, 1, 1, 0, 0, 0)

        with self.db.get_session() as session:
            # Second stock with sell advice -- price drops (win for cash/down)
            session.add(
                AnalysisHistory(
                    query_id="q2",
                    code="000001",
                    name="平安银行",
                    report_type="simple",
                    sentiment_score=30,
                    operation_advice="卖出",
                    trend_prediction="看空",
                    analysis_summary="test2",
                    stop_loss=None,
                    take_profit=None,
                    created_at=old_created_at,
                    context_snapshot=_phase_snapshot(
                        date(2024, 1, 1),
                        phase="postmarket",
                        market="cn",
                        effective_date=date(2024, 1, 1),
                    ),
                )
            )
            session.add(
                StockDaily(code="000001", date=date(2024, 1, 1), open=10.0, high=10.2, low=9.8, close=10.0)
            )
            session.add_all([
                StockDaily(code="000001", date=date(2024, 1, 2), high=10.0, low=9.5, close=9.6),
                StockDaily(code="000001", date=date(2024, 1, 3), high=9.7, low=9.3, close=9.4),
                StockDaily(code="000001", date=date(2024, 1, 4), high=9.5, low=9.0, close=9.1),
            ])
            session.commit()

        service = self._service()
        stats = service.run_backtest(code=None, force=False, eval_window_days=3, min_age_days=0, limit=10)
        self.assertEqual(stats["saved"], 2)
        self.assertEqual(stats["completed"], 2)

        with self.db.get_session() as session:
            # Each stock has its own summary
            s1 = session.query(BacktestSummary).filter(
                BacktestSummary.scope == "stock", BacktestSummary.code == "600519"
            ).first()
            s2 = session.query(BacktestSummary).filter(
                BacktestSummary.scope == "stock", BacktestSummary.code == "000001"
            ).first()
            self.assertIsNotNone(s1)
            self.assertIsNotNone(s2)
            self.assertEqual(s1.win_count, 1)
            self.assertEqual(s2.win_count, 1)

            # Overall aggregates both
            overall = session.query(BacktestSummary).filter(
                BacktestSummary.scope == "overall",
                BacktestSummary.code == OVERALL_SENTINEL_CODE,
            ).first()
            self.assertIsNotNone(overall)
            self.assertEqual(overall.total_evaluations, 2)
            self.assertEqual(overall.completed_count, 2)
            self.assertEqual(overall.win_count, 2)
