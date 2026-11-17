"""Tests for backtest contracts."""

from tests.application.backtest._backtest_service_support import (
    AnalysisHistory,
    BacktestRepository,
    BacktestResult,
    StockDaily,
    _BacktestDailyRefillSeamTestsFixture,
    _BacktestServiceTestCaseFixture,
    _RecordingDailyRefill,
    _phase_snapshot,
    date,
    datetime,
    json,
    patch,
    unittest,
)


class BacktestServiceTestCase(_BacktestServiceTestCaseFixture, unittest.TestCase):
    def test_run_backtest_rejects_invalid_eval_window_days_at_entry(self) -> None:
        service = self._service()

        for value in (0, -1, 1.5, True, "1"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "positive integer"):
                    service.run_backtest(
                        code="600519",
                        eval_window_days=value,
                        min_age_days=0,
                    )

    def test_run_backtest_accepts_dotted_exchange_prefix_and_filters_analysis_date_range(self) -> None:
        service = self._service()

        stats = service.run_backtest(
            code="SH.600519",
            force=False,
            eval_window_days=3,
            min_age_days=0,
            analysis_date_from=date(2024, 1, 1),
            analysis_date_to=date(2024, 1, 1),
            limit=10,
        )

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["saved"], 1)
        self.assertEqual(stats["completed"], 1)
        self.assertIsNone(stats["message"])
        self.assertEqual(stats["diagnostics"]["code"], "600519")
        self.assertEqual(stats["diagnostics"]["analysis_date_from"], "2024-01-01")
        self.assertEqual(stats["diagnostics"]["analysis_date_to"], "2024-01-01")

        data = service.get_recent_evaluations(code="SH.600519", eval_window_days=3, limit=10, page=1)
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["code"], "600519")

        summary = service.get_summary(scope="stock", code="SH.600519", eval_window_days=3)
        self.assertIsNotNone(summary)
        self.assertEqual(summary["code"], "600519")
        self.assertEqual(summary["completed_count"], 1)

    def test_run_backtest_keeps_dotted_cn_code_match_when_analysis_history_is_dotted(self) -> None:
        self._seed_analysis(
            query_id="q_dot_cn",
            code="600519.SH",
            analysis_date=date(2024, 1, 2),
            created_at=datetime(2024, 1, 2, 0, 0, 0),
            operation_advice="买入",
            trend_prediction="看多",
            start_close=100.0,
            forward_bars=[
                StockDaily(code="600519.SH", date=date(2024, 1, 3), high=111.0, low=100.0, close=105.0),
                StockDaily(code="600519.SH", date=date(2024, 1, 4), high=108.0, low=102.0, close=106.0),
                StockDaily(code="600519.SH", date=date(2024, 1, 5), high=109.0, low=102.0, close=107.0),
            ],
        )

        service = self._service()
        stats = service.run_backtest(
            code="600519.SH",
            force=False,
            eval_window_days=3,
            min_age_days=0,
            analysis_date_from=date(2024, 1, 2),
            analysis_date_to=date(2024, 1, 2),
            limit=10,
        )

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["saved"], 1)
        self.assertEqual(stats["completed"], 1)

        data = service.get_recent_evaluations(code="600519.SH", eval_window_days=3, limit=10, page=1)
        self.assertEqual(data["items"][0]["code"], "600519.SH")

        summary = service.get_summary(scope="stock", code="600519.SH", eval_window_days=3)
        self.assertIsNotNone(summary)
        self.assertEqual(summary["code"], "600519")

    def test_run_backtest_matches_compact_ss_alias_after_request_normalization(self) -> None:
        self._seed_analysis(
            query_id="q_compact_history_ss",
            code="SS600519",
            analysis_date=date(2024, 2, 20),
            created_at=datetime(2024, 2, 20, 0, 0, 0),
            operation_advice="买入",
            trend_prediction="看多",
            start_close=100.0,
            forward_bars=[
                StockDaily(code="SS600519", date=date(2024, 2, 21), high=102.0, low=99.0, close=101.0),
                StockDaily(code="SS600519", date=date(2024, 2, 22), high=104.0, low=100.0, close=103.0),
            ],
        )

        service = self._service()
        stats = service.run_backtest(
            code="SS600519",
            force=False,
            eval_window_days=2,
            min_age_days=0,
            analysis_date_from=date(2024, 2, 20),
            analysis_date_to=date(2024, 2, 20),
            limit=10,
        )

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["saved"], 1)
        self.assertEqual(stats["completed"], 1)

        data = service.get_recent_evaluations(code="SS600519", eval_window_days=2, limit=10, page=1)
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["code"], "SS600519")

    def test_get_candidates_does_not_match_invalid_a_share_hk_cross_input(self) -> None:
        repo = BacktestRepository(self.db)
        matches = repo.get_candidates(
            code="600519.HK",
            min_age_days=0,
            limit=10,
            eval_window_days=3,
            engine_version="v1",
            force=True,
        )

        self.assertEqual(len(matches), 0)

    def test_run_backtest_uses_exact_expected_start_across_code_aliases(self) -> None:
        with self.db.get_session() as session:
            session.add(
                AnalysisHistory(
                    query_id="q_newest_complete_window",
                    code="600519.SH",
                    name="贵州茅台",
                    report_type="simple",
                    sentiment_score=60,
                    operation_advice="买入",
                    trend_prediction="看多",
                    analysis_summary="prefer complete bare-code daily window",
                    stop_loss=None,
                    take_profit=None,
                    created_at=datetime(2024, 1, 7, 0, 0, 0),
                    context_snapshot=_phase_snapshot(
                        date(2024, 1, 7),
                        phase="non_trading",
                        market="cn",
                        effective_date=date(2024, 1, 5),
                    ),
                )
            )
            session.add_all(
                [
                    StockDaily(
                        code="600519.SH",
                        date=date(2024, 1, 2),
                        open=50.0,
                        high=50.0,
                        low=50.0,
                        close=50.0,
                    ),
                    StockDaily(
                        code="600519",
                        date=date(2024, 1, 5),
                        open=100.0,
                        high=100.0,
                        low=100.0,
                        close=100.0,
                    ),
                    StockDaily(
                        code="600519",
                        date=date(2024, 1, 8),
                        open=105.0,
                        high=106.0,
                        low=99.0,
                        close=105.0,
                    ),
                ]
            )
            session.commit()

        service = self._service()
        with patch(
            "src.application.quote.stock_daily_start_resolver.resolve_historical_daily_bar_date",
            return_value=date(2024, 1, 5),
        ) as resolve_historical_date:
            stats = service.run_backtest(
                code="600519.SH",
                force=False,
                eval_window_days=1,
                min_age_days=0,
                analysis_date_from=date(2024, 1, 7),
                analysis_date_to=date(2024, 1, 7),
                limit=10,
            )

        resolve_historical_date.assert_called_once_with(
            "cn",
            date(2024, 1, 5),
            "postmarket",
        )
        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["insufficient"], 0)
        with self.db.get_session() as session:
            result = (
                session.query(BacktestResult)
                .filter(BacktestResult.code == "600519.SH")
                .one()
            )
            self.assertEqual(result.eval_status, "completed")
            self.assertEqual(result.start_price, 100.0)
            self.assertEqual(result.end_close, 105.0)

    def test_run_backtest_supports_us_suffix_code_shape_when_run_with_suffix(self) -> None:
        self._seed_analysis(
            query_id="q_aapl",
            code="AAPL.US",
            analysis_date=date(2024, 1, 3),
            created_at=datetime(2024, 1, 3, 0, 0, 0),
            operation_advice="买入",
            trend_prediction="看多",
            start_close=100.0,
            forward_bars=[
                StockDaily(code="AAPL.US", date=date(2024, 1, 4), high=101.0, low=95.0, close=96.0),
            ],
            market="us",
        )

        service = self._service()
        stats = service.run_backtest(
            code="AAPL.US",
            force=False,
            eval_window_days=1,
            min_age_days=0,
            analysis_date_from=date(2024, 1, 3),
            analysis_date_to=date(2024, 1, 3),
            limit=10,
        )

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["saved"], 1)

        data = service.get_recent_evaluations(code="AAPL.US", eval_window_days=1, limit=10, page=1)
        self.assertEqual(data["items"][0]["code"], "AAPL.US")
        self.assertEqual(data["items"][0]["analysis_date"], "2024-01-03")

    def test_run_backtest_preserves_supported_us_index_identity(self) -> None:
        self._seed_analysis(
            query_id="q_nasdaq",
            code="NASDAQ",
            analysis_date=date(2024, 1, 5),
            created_at=datetime(2024, 1, 5, 0, 0, 0),
            operation_advice="买入",
            trend_prediction="看多",
            start_close=100.0,
            forward_bars=[
                StockDaily(
                    code="NASDAQ",
                    date=date(2024, 1, 8),
                    high=103.0,
                    low=99.0,
                    close=102.0,
                ),
            ],
            phase="postmarket",
            market="us",
        )

        service = self._service()
        stats = service.run_backtest(
            code="NASDAQ",
            force=False,
            eval_window_days=1,
            min_age_days=0,
            analysis_date_from=date(2024, 1, 5),
            analysis_date_to=date(2024, 1, 5),
            limit=10,
        )

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["completed"], 1)
        data = service.get_recent_evaluations(
            code="NASDAQ",
            eval_window_days=1,
            limit=10,
            page=1,
        )
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["code"], "NASDAQ")

    def test_us_code_queries_match_legacy_results_without_rerun(self) -> None:
        with self.db.get_session() as session:
            bare_history = AnalysisHistory(
                query_id="q_legacy_aapl_bare",
                code="AAPL",
                name="Apple",
                report_type="simple",
                sentiment_score=60,
                operation_advice="买入",
                trend_prediction="看多",
                analysis_summary="legacy bare result",
                created_at=datetime(2024, 1, 10, 0, 0, 0),
                context_snapshot=json.dumps({"enhanced_context": {"date": "2024-01-10"}}),
            )
            suffix_history = AnalysisHistory(
                query_id="q_legacy_aapl_suffix",
                code="AAPL.US",
                name="Apple",
                report_type="simple",
                sentiment_score=60,
                operation_advice="买入",
                trend_prediction="看多",
                analysis_summary="legacy suffix result",
                created_at=datetime(2024, 1, 11, 0, 0, 0),
                context_snapshot=json.dumps({"enhanced_context": {"date": "2024-01-11"}}),
            )
            session.add_all([bare_history, suffix_history])
            session.flush()
            session.add_all(
                [
                    BacktestResult(
                        analysis_history_id=bare_history.id,
                        code="AAPL",
                        analysis_date=date(2024, 1, 10),
                        eval_window_days=1,
                        engine_version="v1",
                        eval_status="completed",
                        evaluated_at=datetime(2024, 1, 20, 0, 0, 0),
                        operation_advice="买入",
                        position_recommendation="long",
                        start_price=100.0,
                        end_close=103.0,
                        stock_return_pct=3.0,
                        direction_expected="up",
                        direction_correct=True,
                        outcome="win",
                        simulated_return_pct=3.0,
                    ),
                    BacktestResult(
                        analysis_history_id=suffix_history.id,
                        code="AAPL.US",
                        analysis_date=date(2024, 1, 11),
                        eval_window_days=1,
                        engine_version="v1",
                        eval_status="completed",
                        evaluated_at=datetime(2024, 1, 21, 0, 0, 0),
                        operation_advice="买入",
                        position_recommendation="long",
                        start_price=103.0,
                        end_close=105.0,
                        stock_return_pct=1.94,
                        direction_expected="up",
                        direction_correct=True,
                        outcome="win",
                        simulated_return_pct=1.94,
                    ),
                ]
            )
            session.commit()

        service = self._service()
        suffix_query = service.get_recent_evaluations(
            code="AAPL.US",
            eval_window_days=1,
            limit=10,
            page=1,
            analysis_date_from=date(2024, 1, 10),
            analysis_date_to=date(2024, 1, 10),
        )
        self.assertEqual(suffix_query["total"], 1)
        self.assertEqual(suffix_query["items"][0]["code"], "AAPL")

        suffix_summary = service.get_summary(
            scope="stock",
            code="AAPL.US",
            eval_window_days=1,
            analysis_date_from=date(2024, 1, 10),
            analysis_date_to=date(2024, 1, 10),
        )
        self.assertIsNotNone(suffix_summary)
        assert suffix_summary is not None
        self.assertEqual(suffix_summary["code"], "AAPL")
        self.assertEqual(suffix_summary["total_evaluations"], 1)

        bare_query = service.get_recent_evaluations(
            code="AAPL",
            eval_window_days=1,
            limit=10,
            page=1,
            analysis_date_from=date(2024, 1, 11),
            analysis_date_to=date(2024, 1, 11),
        )
        self.assertEqual(bare_query["total"], 1)
        self.assertEqual(bare_query["items"][0]["code"], "AAPL.US")

        bare_summary = service.get_summary(
            scope="stock",
            code="AAPL",
            eval_window_days=1,
            analysis_date_from=date(2024, 1, 11),
            analysis_date_to=date(2024, 1, 11),
        )
        self.assertIsNotNone(bare_summary)
        assert bare_summary is not None
        self.assertEqual(bare_summary["code"], "AAPL")
        self.assertEqual(bare_summary["total_evaluations"], 1)

    def test_date_filtered_rerun_aligns_legacy_result_date_when_new_candidates_process(self) -> None:
        with self.db.get_session() as session:
            legacy_history = AnalysisHistory(
                query_id="q-legacy-result-date-mixed",
                code="000006",
                name="测试股票",
                report_type="simple",
                sentiment_score=60,
                operation_advice="买入",
                trend_prediction="看多",
                analysis_summary="legacy result stores fallback trading date in mixed rerun",
                stop_loss=None,
                take_profit=None,
                created_at=datetime(2024, 1, 7, 0, 0, 0),
                context_snapshot='{"enhanced_context": {"date": "2024-01-07"}}',
            )
            new_history = AnalysisHistory(
                query_id="q-new-result-date-mixed",
                code="000006",
                name="测试股票",
                report_type="simple",
                sentiment_score=62,
                operation_advice="买入",
                trend_prediction="看多",
                analysis_summary="new matching analysis should not prevent legacy alignment",
                stop_loss=None,
                take_profit=None,
                created_at=datetime(2024, 1, 7, 1, 0, 0),
                context_snapshot='{"enhanced_context": {"date": "2024-01-07"}}',
            )
            session.add_all([legacy_history, new_history])
            session.flush()
            legacy_history_id = legacy_history.id
            session.add(
                BacktestResult(
                    analysis_history_id=legacy_history_id,
                    code="000006",
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
            session.add_all(
                [
                    StockDaily(
                        code="000006",
                        date=date(2024, 1, 7),
                        open=10.0,
                        high=10.0,
                        low=10.0,
                        close=10.0,
                    ),
                    StockDaily(code="000006", date=date(2024, 1, 8), high=10.6, low=9.9, close=10.5),
                ]
            )
            session.commit()

        service = self._service()
        stats = service.run_backtest(
            code="000006",
            force=False,
            eval_window_days=1,
            min_age_days=0,
            analysis_date_from=date(2024, 1, 7),
            analysis_date_to=date(2024, 1, 7),
            limit=10,
        )

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["saved"], 1)
        self.assertEqual(stats["diagnostics"]["aligned_existing_result_dates"], 1)
        with self.db.get_session() as session:
            legacy_result = (
                session.query(BacktestResult)
                .filter(BacktestResult.analysis_history_id == legacy_history_id)
                .one()
            )
            self.assertEqual(legacy_result.analysis_date, date(2024, 1, 7))

        data = service.get_recent_evaluations(
            code="000006",
            eval_window_days=1,
            limit=10,
            page=1,
            analysis_date_from=date(2024, 1, 7),
            analysis_date_to=date(2024, 1, 7),
        )
        self.assertEqual(data["total"], 2)
        self.assertEqual({item["analysis_date"] for item in data["items"]}, {"2024-01-07"})

    def test_run_backtest_pages_candidates_before_analysis_date_filter(self) -> None:
        with self.db.get_session() as session:
            for index in range(5):
                session.add(
                    AnalysisHistory(
                        query_id=f"q-newer-outside-date-{index}",
                        code=f"00010{index}",
                        name="测试股票",
                        report_type="simple",
                        sentiment_score=50,
                        operation_advice="持有",
                        trend_prediction="震荡",
                        analysis_summary="newer created_at but outside analysis date range",
                        stop_loss=None,
                        take_profit=None,
                        created_at=datetime(2024, 2, 10, index, 0, 0),
                        context_snapshot=json.dumps({"enhanced_context": {"date": "2024-02-01"}}),
                    )
                )
            session.commit()

        service = self._service()
        stats = service.run_backtest(
            code=None,
            force=False,
            eval_window_days=3,
            min_age_days=0,
            analysis_date_from=date(2024, 1, 1),
            analysis_date_to=date(2024, 1, 1),
            limit=1,
        )

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["completed"], 1)
        self.assertIsNone(stats["message"])
        with self.db.get_session() as session:
            result = session.query(BacktestResult).one()
            self.assertEqual(result.code, "600519")
            self.assertEqual(result.analysis_date, date(2024, 1, 1))

    def test_run_backtest_reports_no_matching_candidates(self) -> None:
        service = self._service()

        stats = service.run_backtest(
            code="600519",
            force=False,
            eval_window_days=3,
            min_age_days=0,
            analysis_date_from=date(2024, 2, 1),
            analysis_date_to=date(2024, 2, 2),
            limit=10,
        )

        self.assertEqual(stats["processed"], 0)
        self.assertEqual(stats["saved"], 0)
        self.assertEqual(stats["diagnostics"]["empty_reason"], "no_matching_analysis")
        self.assertIn("未找到符合条件的历史分析记录", stats["message"])

    def test_result_fields_correct(self) -> None:
        """Verify BacktestResult row contains correct evaluation values."""
        result = self._run_and_get_result()

        self.assertEqual(result.eval_status, "completed")
        self.assertEqual(result.code, "600519")
        self.assertEqual(result.analysis_date, date(2024, 1, 1))
        self.assertEqual(result.operation_advice, "买入")
        self.assertEqual(result.position_recommendation, "long")
        self.assertEqual(result.direction_expected, "up")

        # Prices
        self.assertAlmostEqual(result.start_price, 100.0)
        self.assertAlmostEqual(result.end_close, 107.0)
        self.assertAlmostEqual(result.stock_return_pct, 7.0)

        # Direction & outcome
        self.assertEqual(result.outcome, "win")
        self.assertTrue(result.direction_correct)

        # Target hits -- day2 high=111 >= take_profit=110
        self.assertTrue(result.hit_take_profit)
        self.assertFalse(result.hit_stop_loss)
        self.assertEqual(result.first_hit, "take_profit")
        self.assertEqual(result.first_hit_trading_days, 1)
        self.assertEqual(result.first_hit_date, date(2024, 1, 2))

        # Simulated execution
        self.assertAlmostEqual(result.simulated_entry_price, 100.0)
        self.assertAlmostEqual(result.simulated_exit_price, 110.0)
        self.assertEqual(result.simulated_exit_reason, "take_profit")
        self.assertAlmostEqual(result.simulated_return_pct, 10.0)

    def test_get_recent_evaluations(self) -> None:
        """Verify get_recent_evaluations returns correct paginated results."""
        service = self._service()
        service.run_backtest(code="600519", force=False, eval_window_days=3, min_age_days=0, limit=10)

        data = service.get_recent_evaluations(code="600519", limit=10, page=1)
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["limit"], 10)
        self.assertEqual(len(data["items"]), 1)

        item = data["items"][0]
        self.assertEqual(item["code"], "600519")
        self.assertEqual(item["outcome"], "win")
        self.assertEqual(item["direction_expected"], "up")
        self.assertTrue(item["direction_correct"])

    def test_get_recent_evaluations_aligns_neutral_advice_with_score(self) -> None:
        service = self._service()
        with self.db.get_session() as session:
            history = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == "q1").one()
            history.operation_advice = "持有"
            history.sentiment_score = 78
            history.raw_result = None
            result = self._make_backtest_result(
                analysis_history_id=history.id,
                analysis_date=date(2024, 1, 1),
                eval_window_days=1,
            )
            result.operation_advice = "持有"
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
        self.assertEqual(item["operation_advice"], "持有")
        self.assertEqual(item["action"], "buy")
        self.assertEqual(item["action_label"], "买入")

    def test_get_recent_evaluations_supports_tracking_fields_and_analysis_date_filters(self) -> None:
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

        data = service.get_recent_evaluations(
            code="600519",
            eval_window_days=1,
            limit=10,
            page=1,
            analysis_date_from=date(2024, 1, 10),
            analysis_date_to=date(2024, 1, 10),
        )
        self.assertEqual(data["total"], 1)
        item = data["items"][0]
        self.assertEqual(item["stock_name"], "贵州茅台")
        self.assertEqual(item["trend_prediction"], "看多")
        self.assertEqual(item["actual_movement"], "down")
        self.assertAlmostEqual(item["actual_return_pct"], -4.0)
        self.assertFalse(item["direction_correct"])

    def test_run_backtest_includes_null_report_type_records(self) -> None:
        with self.db.get_session() as session:
            session.add(
                AnalysisHistory(
                    query_id="q-null-report-type",
                    code="000858",
                    name="五粮液",
                    report_type=None,
                    sentiment_score=60,
                    operation_advice="持有",
                    trend_prediction="震荡",
                    analysis_summary="legacy null report_type row",
                    stop_loss=None,
                    take_profit=None,
                    created_at=datetime(2024, 1, 3, 0, 0, 0),
                    context_snapshot='{"enhanced_context": {"date": "2024-01-03"}}',
                )
            )
            session.add_all(
                [
                    StockDaily(code="000858", date=date(2024, 1, 3), open=12.0, high=12.8, low=11.5, close=12.2),
                    StockDaily(code="000858", date=date(2024, 1, 4), open=12.2, high=13.0, low=12.0, close=12.6),
                    StockDaily(code="000858", date=date(2024, 1, 5), open=12.6, high=12.9, low=11.9, close=12.4),
                ]
            )
            session.commit()

        service = self._service()
        stats = service.run_backtest(code=None, force=False, eval_window_days=3, min_age_days=0, limit=10)
        self.assertGreaterEqual(stats["processed"], 2)
        self.assertGreaterEqual(stats["saved"], 2)
        with self.db.get_session() as session:
            self.assertEqual(
                session.query(BacktestResult).filter(BacktestResult.code == "000858").count(),
                1,
            )


class BacktestDailyRefillSeamTests(_BacktestDailyRefillSeamTestsFixture, unittest.TestCase):
    def test_try_fill_delegates_to_port_with_expected_window(self):
        refill = _RecordingDailyRefill()
        service = self._service(refill)
        service._try_fill_daily_data(
            code="600514", analysis_date=date(2024, 1, 5), eval_window_days=3
        )
        self.assertEqual(len(refill.calls), 1)
        call = refill.calls[0]
        self.assertEqual(call["code"], "600514")
        self.assertEqual(call["start_date"], "2024-01-05")
        # end_date = analysis_date + timedelta(days=max(3*2, 30)) == +30d
        self.assertEqual(call["end_date"], "2024-02-04")
        self.assertEqual(call["days"], 6)

    def test_try_fill_skips_blank_code(self):
        refill = _RecordingDailyRefill()
        service = self._service(refill)
        service._try_fill_daily_data(
            code="   ", analysis_date=date(2024, 1, 5), eval_window_days=1
        )
        self.assertEqual(refill.calls, [])

    def test_bootstrap_factory_wires_infrastructure_adapter(self):
        # 缺省装配已从 application 层移除，改由 bootstrap 装配口显式注入数据源适配器。
        from src.bootstrap.backtest import build_backtest_service

        from src.infrastructure.providers.backtest_daily_refill import (
            DataProviderDailyBarRefill,
        )

        service = build_backtest_service()
        self.assertIsInstance(service.daily_refill, DataProviderDailyBarRefill)

    def test_backtest_service_has_no_data_provider_coupling(self):
        import inspect

        import src.application.backtest.service as bs

        source = inspect.getsource(bs)
        self.assertNotIn("from data_provider", source)
        self.assertNotIn("DataFetcherManager", source)
        self.assertNotIn("self.db.save_daily_data", source)
        self.assertIn("self.daily_refill.refill(", source)
