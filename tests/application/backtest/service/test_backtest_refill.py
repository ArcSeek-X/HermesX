"""Tests for backtest refill."""

from tests.application.backtest._backtest_service_support import (
    AnalysisHistory,
    BacktestRepository,
    BacktestResult,
    BacktestService,
    StockDaily,
    _BacktestDailyRefillSeamTestsFixture,
    _BacktestServiceTestCaseFixture,
    _RecordingDailyRefill,
    _phase_snapshot,
    date,
    datetime,
    json,
    patch,
    pd,
    unittest,
)


class BacktestServiceTestCase(_BacktestServiceTestCaseFixture, unittest.TestCase):
    def test_kr_suffix_filter_reaches_legacy_bare_history(self) -> None:
        self._seed_legacy_offshore_analysis(
            query_id="q_kr_legacy_bare_filter",
            code="005930",
            market="kr",
            analysis_date=date(2024, 10, 2),
            start_close=100.0,
            forward_date=date(2024, 10, 4),
            end_close=105.0,
        )

        candidates = BacktestRepository(self.db).get_candidates(
            code="005930.KS",
            min_age_days=0,
            limit=10,
            eval_window_days=1,
            engine_version="v1",
            force=True,
        )

        self.assertEqual(
            [candidate.query_id for candidate in candidates],
            ["q_kr_legacy_bare_filter"],
        )

    def test_jp_suffix_filter_reaches_legacy_bare_history(self) -> None:
        self._seed_legacy_offshore_analysis(
            query_id="q_jp_legacy_bare_filter",
            code="7203",
            market="jp",
            analysis_date=date(2024, 10, 1),
            start_close=200.0,
            forward_date=date(2024, 10, 2),
            end_close=210.0,
        )

        candidates = BacktestRepository(self.db).get_candidates(
            code="7203.T",
            min_age_days=0,
            limit=10,
            eval_window_days=1,
            engine_version="v1",
            force=True,
        )

        self.assertEqual(
            [candidate.query_id for candidate in candidates],
            ["q_jp_legacy_bare_filter"],
        )

    def test_unfiltered_rerun_uses_persisted_market_for_legacy_jp_kr_bare_codes(
        self,
    ) -> None:
        self._seed_legacy_offshore_analysis(
            query_id="q_jp_legacy_bare_rerun",
            code="7203",
            market="jp",
            analysis_date=date(2024, 10, 1),
            start_close=200.0,
            forward_date=date(2024, 10, 2),
            end_close=210.0,
            include_effective_date=False,
        )
        self._seed_legacy_offshore_analysis(
            query_id="q_kr_legacy_bare_rerun",
            code="005930",
            market="kr",
            analysis_date=date(2024, 10, 2),
            start_close=100.0,
            forward_date=date(2024, 10, 4),
            end_close=105.0,
            include_effective_date=False,
        )

        service = self._service()
        with patch.object(service, "_try_fill_daily_data") as refill:
            stats = service.run_backtest(
                code=None,
                force=False,
                eval_window_days=1,
                min_age_days=0,
                analysis_date_from=date(2024, 10, 1),
                analysis_date_to=date(2024, 10, 2),
                limit=10,
            )

        refill.assert_not_called()
        self.assertEqual(stats["processed"], 2)
        self.assertEqual(stats["completed"], 2)
        self.assertEqual(stats["insufficient"], 0)
        with self.db.get_session() as session:
            results = {
                result.code: result
                for result in session.query(BacktestResult)
                .filter(BacktestResult.code.in_(["7203", "005930"]))
                .all()
            }

        self.assertEqual(results["7203"].analysis_date, date(2024, 10, 1))
        self.assertEqual(results["7203"].start_price, 200.0)
        self.assertEqual(results["005930"].analysis_date, date(2024, 10, 2))
        self.assertEqual(results["005930"].start_price, 100.0)

    def test_unfiltered_rerun_rebuilds_legacy_cn_snapshot_for_indexed_bare_jp_code(
        self,
    ) -> None:
        self._seed_legacy_offshore_analysis(
            query_id="q_jp_legacy_cn_bare_rerun",
            code="7203",
            market="cn",
            analysis_date=date(2024, 10, 1),
            start_close=200.0,
            forward_date=date(2024, 10, 2),
            end_close=210.0,
            include_effective_date=False,
        )
        with self.db.get_session() as session:
            analysis = (
                session.query(AnalysisHistory)
                .filter(AnalysisHistory.query_id == "q_jp_legacy_cn_bare_rerun")
                .one()
            )
            snapshot = json.loads(analysis.context_snapshot)
            snapshot["market_phase_summary"].update(
                {
                    "market_local_time": "2024-10-01T16:00:00+08:00",
                    "session_date": "2024-10-01",
                    "effective_daily_bar_date": "2024-10-01",
                }
            )
            analysis.context_snapshot = json.dumps(snapshot)
            session.commit()

        service = self._service()
        with patch.object(service, "_try_fill_daily_data") as refill:
            stats = service.run_backtest(
                code=None,
                force=False,
                eval_window_days=1,
                min_age_days=0,
                analysis_date_from=date(2024, 10, 1),
                analysis_date_to=date(2024, 10, 1),
                limit=10,
            )

        refill.assert_not_called()
        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["insufficient"], 0)
        with self.db.get_session() as session:
            result = (
                session.query(BacktestResult)
                .filter(BacktestResult.code == "7203")
                .one()
            )

        self.assertEqual(result.analysis_date, date(2024, 10, 1))
        self.assertEqual(result.start_price, 200.0)

    def test_canonical_hk_query_does_not_backtest_legacy_bare_jp_collision(
        self,
    ) -> None:
        self._seed_legacy_offshore_analysis(
            query_id="q_jp_legacy_bare_hk_collision",
            code="8035",
            market="jp",
            analysis_date=date(2024, 10, 1),
            start_close=200.0,
            forward_date=date(2024, 10, 2),
            end_close=210.0,
        )

        repo_candidates = BacktestRepository(self.db).get_candidates(
            code="08035.HK",
            min_age_days=0,
            limit=10,
            eval_window_days=1,
            engine_version="v1",
            force=True,
        )
        stats = self._service().run_backtest(
            code="08035.HK",
            force=False,
            eval_window_days=1,
            min_age_days=0,
            analysis_date_from=date(2024, 10, 1),
            analysis_date_to=date(2024, 10, 1),
            limit=10,
        )

        self.assertEqual(repo_candidates, [])
        self.assertEqual(stats["processed"], 0)
        self.assertEqual(stats["saved"], 0)
        with self.db.get_session() as session:
            self.assertEqual(
                session.query(BacktestResult)
                .filter(BacktestResult.code == "8035")
                .count(),
                0,
            )

    def test_run_backtest_uses_bare_daily_bars_and_summary_for_compact_ss_history(self) -> None:
        with self.db.get_session() as session:
            session.add(
                AnalysisHistory(
                    query_id="q_compact_ss_history_bare_daily",
                    code="SS600519",
                    name="贵州茅台",
                    report_type="simple",
                    sentiment_score=60,
                    operation_advice="买入",
                    trend_prediction="看多",
                    analysis_summary="compact ss history with bare daily data",
                    stop_loss=None,
                    take_profit=None,
                    created_at=datetime(2024, 2, 25, 0, 0, 0),
                    context_snapshot=_phase_snapshot(
                        date(2024, 2, 25),
                        phase="postmarket",
                        market="cn",
                        effective_date=date(2024, 2, 25),
                    ),
                )
            )
            session.add(
                StockDaily(
                    code="600519",
                    date=date(2024, 2, 25),
                    open=100.0,
                    high=100.0,
                    low=100.0,
                    close=100.0,
                )
            )
            session.add(
                StockDaily(code="600519", date=date(2024, 2, 26), high=104.0, low=99.0, close=103.0)
            )
            session.commit()

        service = self._service()
        stats = service.run_backtest(
            code="600519",
            force=False,
            eval_window_days=1,
            min_age_days=0,
            analysis_date_from=date(2024, 1, 1),
            analysis_date_to=date(2024, 2, 25),
            limit=10,
        )

        self.assertEqual(stats["processed"], 2)
        self.assertEqual(stats["saved"], 2)
        self.assertEqual(stats["completed"], 2)
        self.assertEqual(stats["insufficient"], 0)

        summary = service.get_summary(scope="stock", code="600519", eval_window_days=1)
        self.assertIsNotNone(summary)
        self.assertEqual(summary["code"], "600519")
        self.assertEqual(summary["total_evaluations"], 2)

        matched = service.get_recent_evaluations(
            code="600519",
            eval_window_days=1,
            limit=10,
            page=1,
            analysis_date_from=date(2024, 1, 1),
            analysis_date_to=date(2024, 2, 25),
        )
        self.assertEqual({row["code"] for row in matched["items"]}, {"600519", "SS600519"})

    def test_run_backtest_uses_compact_forward_bars_when_analysis_history_is_bare_code(self) -> None:
        with self.db.get_session() as session:
            session.add(
                AnalysisHistory(
                    query_id="q_compact_forward_sh",
                    code="600519",
                    name="贵州茅台",
                    report_type="simple",
                    sentiment_score=60,
                    operation_advice="买入",
                    trend_prediction="看多",
                    analysis_summary="bare history with compact forward bars",
                    stop_loss=None,
                    take_profit=None,
                    created_at=datetime(2024, 3, 1, 0, 0, 0),
                    context_snapshot=_phase_snapshot(
                        date(2024, 3, 1),
                        phase="postmarket",
                        market="cn",
                        effective_date=date(2024, 3, 1),
                    ),
                )
            )
            session.add(
                StockDaily(
                    code="SH600519",
                    date=date(2024, 3, 1),
                    open=110.0,
                    high=110.0,
                    low=110.0,
                    close=110.0,
                )
            )
            session.add_all(
                [
                    StockDaily(code="SH600519", date=date(2024, 3, 2), high=112.0, low=109.0, close=111.0),
                    StockDaily(code="SH600519", date=date(2024, 3, 3), high=113.0, low=110.0, close=112.0),
                ]
            )
            session.commit()

        service = self._service()
        stats = service.run_backtest(
            code="600519",
            force=False,
            eval_window_days=2,
            min_age_days=0,
            analysis_date_from=date(2024, 3, 1),
            analysis_date_to=date(2024, 3, 1),
            limit=10,
        )

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["saved"], 1)
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["insufficient"], 0)

    def test_run_backtest_bare_code_query_matches_dotted_history_records(self) -> None:
        self._seed_analysis(
            query_id="q_match_dot",
            code="600519.SH",
            analysis_date=date(2024, 2, 1),
            created_at=datetime(2024, 2, 1, 0, 0, 0),
            operation_advice="买入",
            trend_prediction="看多",
            start_close=100.0,
            forward_bars=[
                StockDaily(code="600519.SH", date=date(2024, 2, 2), high=101.0, low=95.0, close=96.0),
            ],
        )

        service = self._service()
        stats = service.run_backtest(
            code="600519",
            force=False,
            eval_window_days=1,
            min_age_days=0,
            analysis_date_from=date(2024, 1, 1),
            analysis_date_to=date(2024, 2, 1),
            limit=20,
        )

        self.assertEqual(stats["processed"], 2)
        self.assertEqual(stats["saved"], 2)
        self.assertEqual(stats["completed"], 2)
        summary = service.get_summary(scope="stock", code="600519", eval_window_days=1)
        self.assertIsNotNone(summary)
        self.assertEqual(summary["code"], "600519")
        self.assertEqual(summary["total_evaluations"], 2)
        self.assertEqual(summary["completed_count"], 2)

        matched = service.get_recent_evaluations(
            code="600519",
            eval_window_days=1,
            limit=20,
            page=1,
            analysis_date_from=date(2024, 1, 1),
            analysis_date_to=date(2024, 2, 1),
        )
        self.assertEqual({row["code"] for row in matched["items"]}, {"600519", "600519.SH"})

    def test_run_backtest_uses_bare_daily_bars_for_dotted_history_record(self) -> None:
        with self.db.get_session() as session:
            session.add(
                AnalysisHistory(
                    query_id="q_dot_history_bare_daily",
                    code="600519.SH",
                    name="贵州茅台",
                    report_type="simple",
                    sentiment_score=60,
                    operation_advice="买入",
                    trend_prediction="看多",
                    analysis_summary="dotted history with bare daily data",
                    stop_loss=None,
                    take_profit=None,
                    created_at=datetime(2024, 2, 5, 0, 0, 0),
                    context_snapshot=_phase_snapshot(
                        date(2024, 2, 5),
                        phase="postmarket",
                        market="cn",
                        effective_date=date(2024, 2, 5),
                    ),
                )
            )
            session.add(
                StockDaily(
                    code="600519",
                    date=date(2024, 2, 5),
                    open=100.0,
                    high=100.0,
                    low=100.0,
                    close=100.0,
                )
            )
            session.add(
                StockDaily(code="600519", date=date(2024, 2, 6), high=106.0, low=99.0, close=105.0)
            )
            session.commit()

        service = self._service()
        stats = service.run_backtest(
            code="600519",
            force=False,
            eval_window_days=1,
            min_age_days=0,
            analysis_date_from=date(2024, 2, 5),
            analysis_date_to=date(2024, 2, 5),
            limit=10,
        )

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["saved"], 1)
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["insufficient"], 0)

        with self.db.get_session() as session:
            result = session.query(BacktestResult).filter(BacktestResult.code == "600519.SH").one()
            self.assertEqual(result.analysis_date, date(2024, 2, 5))
            self.assertEqual(result.start_price, 100.0)
            self.assertEqual(result.end_close, 105.0)

    def test_run_backtest_does_not_mix_start_and_forward_bars_across_code_shapes(self) -> None:
        with self.db.get_session() as session:
            session.add(
                AnalysisHistory(
                    query_id="q_shape_split",
                    code="600518",
                    name="贵州茅台",
                    report_type="simple",
                    sentiment_score=60,
                    operation_advice="买入",
                    trend_prediction="看多",
                    analysis_summary="split code shape with start on dotted daily",
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
            session.add(
                StockDaily(
                    code="600518.SH",
                    date=date(2024, 1, 5),
                    open=100.0,
                    high=100.0,
                    low=100.0,
                    close=100.0,
                )
            )
            session.add_all(
                [
                    StockDaily(code="600518", date=date(2024, 1, 8), high=106.0, low=99.0, close=105.0),
                    StockDaily(code="600518", date=date(2024, 1, 9), high=110.0, low=100.0, close=108.0),
                ]
            )
            session.commit()

        service = self._service()
        with patch.object(service, "_try_fill_daily_data"):
            stats = service.run_backtest(
                code="600518",
                force=False,
                eval_window_days=2,
                min_age_days=0,
                analysis_date_from=date(2024, 1, 7),
                analysis_date_to=date(2024, 1, 7),
                limit=10,
            )

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["saved"], 1)
        self.assertEqual(stats["completed"], 0)
        self.assertEqual(stats["insufficient"], 1)

        with self.db.get_session() as session:
            result = session.query(BacktestResult).filter(BacktestResult.code == "600518").one()
            self.assertEqual(result.analysis_date, date(2024, 1, 7))
            self.assertIsNone(result.start_price)
            self.assertIsNone(result.end_close)

    def test_run_backtest_replays_legacy_non_session_effective_date_from_local_bars(
        self,
    ) -> None:
        self._seed_analysis(
            query_id="q_legacy_non_session_effective_date",
            code="600520",
            analysis_date=date(2024, 1, 1),
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            operation_advice="买入",
            trend_prediction="看多",
            start_close=100.0,
            forward_bars=[
                StockDaily(
                    code="600520",
                    date=date(2024, 1, 2),
                    high=102.0,
                    low=99.0,
                    close=101.0,
                ),
                StockDaily(
                    code="600520",
                    date=date(2024, 1, 3),
                    high=103.0,
                    low=100.0,
                    close=102.0,
                ),
                StockDaily(
                    code="600520",
                    date=date(2024, 1, 4),
                    high=104.0,
                    low=101.0,
                    close=103.0,
                ),
            ],
            phase="postmarket",
        )

        service = self._service()
        with patch.object(service, "_try_fill_daily_data") as refill:
            stats = service.run_backtest(
                code="600520",
                force=False,
                eval_window_days=3,
                min_age_days=0,
                analysis_date_from=date(2024, 1, 1),
                analysis_date_to=date(2024, 1, 1),
                limit=10,
            )

        refill.assert_not_called()
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["insufficient"], 0)
        with self.db.get_session() as session:
            result = (
                session.query(BacktestResult)
                .filter(BacktestResult.code == "600520")
                .one()
            )
            self.assertEqual(result.eval_status, "completed")
            self.assertEqual(result.start_price, 100.0)
            self.assertEqual(result.end_close, 103.0)

    def test_run_backtest_refills_from_authoritative_start_date(self) -> None:
        requested = []

        class ControlledDataFetcherManager:
            def get_daily_data(
                self,
                stock_code,
                start_date=None,
                end_date=None,
                days=30,
            ):
                requested.append(
                    {
                        "stock_code": stock_code,
                        "start_date": start_date,
                        "end_date": end_date,
                        "days": days,
                    }
                )
                return (
                    pd.DataFrame(
                        [
                            {
                                "date": date(2024, 1, 5),
                                "open": 100.0,
                                "high": 100.0,
                                "low": 100.0,
                                "close": 100.0,
                                "volume": 1000,
                            },
                            {
                                "date": date(2024, 1, 8),
                                "open": 105.0,
                                "high": 106.0,
                                "low": 99.0,
                                "close": 105.0,
                                "volume": 1000,
                            },
                        ]
                    ),
                    "ControlledFetcher",
                )

        with self.db.get_session() as session:
            session.add(
                AnalysisHistory(
                    query_id="q_refill_expected_start",
                    code="600514.SH",
                    name="Test Stock",
                    report_type="simple",
                    sentiment_score=60,
                    operation_advice="buy",
                    trend_prediction="bullish",
                    analysis_summary="refill from authoritative start",
                    created_at=datetime(2024, 1, 8, 8, 0, 0),
                    context_snapshot=_phase_snapshot(
                        date(2024, 1, 8),
                        phase="premarket",
                        market="cn",
                        effective_date=date(2024, 1, 5),
                    ),
                )
            )
            session.commit()

        from src.infrastructure.providers.backtest_daily_refill import (
            DataProviderDailyBarRefill,
        )

        service = self._service(daily_refill=DataProviderDailyBarRefill(self.db))
        with patch(
            "data_provider.base.DataFetcherManager",
            ControlledDataFetcherManager,
        ):
            stats = service.run_backtest(
                code="600514.SH",
                force=False,
                eval_window_days=1,
                min_age_days=0,
                analysis_date_from=date(2024, 1, 8),
                analysis_date_to=date(2024, 1, 8),
                limit=10,
            )

        self.assertEqual(len(requested), 1)
        self.assertEqual(requested[0]["stock_code"], "600514")
        self.assertEqual(requested[0]["start_date"], "2024-01-05")
        self.assertEqual(stats["completed"], 1)
        with self.db.get_session() as session:
            result = (
                session.query(BacktestResult)
                .filter(BacktestResult.code == "600514.SH")
                .one()
            )
            self.assertEqual(result.eval_status, "completed")
            self.assertEqual(result.start_price, 100.0)
            self.assertEqual(result.end_close, 105.0)

    def test_run_backtest_rejects_all_stale_daily_window_candidates(self) -> None:
        with self.db.get_session() as session:
            session.add(
                AnalysisHistory(
                    query_id="q_all_stale_daily_windows",
                    code="600517.SH",
                    name="Test Stock",
                    report_type="simple",
                    sentiment_score=60,
                    operation_advice="buy",
                    trend_prediction="bullish",
                    analysis_summary="reject all stale daily windows",
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
                        code="600517.SH",
                        date=date(2020, 1, 2),
                        open=50.0,
                        high=50.0,
                        low=50.0,
                        close=50.0,
                    ),
                    StockDaily(
                        code="600517.SH",
                        date=date(2024, 1, 8),
                        open=55.0,
                        high=55.0,
                        low=55.0,
                        close=55.0,
                    ),
                    StockDaily(
                        code="600517",
                        date=date(2021, 1, 4),
                        open=60.0,
                        high=60.0,
                        low=60.0,
                        close=60.0,
                    ),
                    StockDaily(
                        code="600517",
                        date=date(2024, 1, 9),
                        open=65.0,
                        high=65.0,
                        low=65.0,
                        close=65.0,
                    ),
                ]
            )
            session.commit()

        service = self._service()
        with patch.object(service, "_try_fill_daily_data"):
            stats = service.run_backtest(
                code="600517.SH",
                force=False,
                eval_window_days=1,
                min_age_days=0,
                analysis_date_from=date(2024, 1, 7),
                analysis_date_to=date(2024, 1, 7),
                limit=10,
            )

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["completed"], 0)
        self.assertEqual(stats["insufficient"], 1)
        with self.db.get_session() as session:
            result = (
                session.query(BacktestResult)
                .filter(BacktestResult.code == "600517.SH")
                .one()
            )
            self.assertEqual(result.eval_status, "insufficient_data")
            self.assertEqual(result.analysis_date, date(2024, 1, 7))
            self.assertIsNone(result.start_price)
            self.assertIsNone(result.end_close)
            self.assertIsNone(result.stock_return_pct)

    def test_run_backtest_us_suffix_query_matches_bare_history_and_summary(self) -> None:
        self._seed_analysis(
            query_id="q_aapl_bare_history",
            code="AAPL",
            analysis_date=date(2024, 1, 6),
            created_at=datetime(2024, 1, 6, 0, 0, 0),
            operation_advice="买入",
            trend_prediction="看多",
            start_close=100.0,
            forward_bars=[
                StockDaily(code="AAPL", date=date(2024, 1, 7), high=104.0, low=99.0, close=103.0),
            ],
            market="us",
        )

        service = self._service()
        stats = service.run_backtest(
            code="AAPL.US",
            force=False,
            eval_window_days=1,
            min_age_days=0,
            analysis_date_from=date(2024, 1, 6),
            analysis_date_to=date(2024, 1, 6),
            limit=10,
        )

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["saved"], 1)
        self.assertEqual(stats["completed"], 1)

        data = service.get_recent_evaluations(
            code="AAPL.US",
            eval_window_days=1,
            limit=10,
            page=1,
            analysis_date_from=date(2024, 1, 6),
            analysis_date_to=date(2024, 1, 6),
        )
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["code"], "AAPL")

        summary = service.get_summary(scope="stock", code="AAPL.US", eval_window_days=1)
        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertEqual(summary["code"], "AAPL")
        self.assertEqual(summary["completed_count"], 1)

    def test_run_backtest_bare_us_query_matches_us_suffix_history_and_summary(self) -> None:
        self._seed_analysis(
            query_id="q_aapl_suffix_history",
            code="AAPL.US",
            analysis_date=date(2024, 1, 8),
            created_at=datetime(2024, 1, 8, 0, 0, 0),
            operation_advice="买入",
            trend_prediction="看多",
            start_close=100.0,
            forward_bars=[
                StockDaily(code="AAPL.US", date=date(2024, 1, 9), high=104.0, low=99.0, close=103.0),
            ],
            market="us",
        )

        service = self._service()
        stats = service.run_backtest(
            code="AAPL",
            force=False,
            eval_window_days=1,
            min_age_days=0,
            analysis_date_from=date(2024, 1, 8),
            analysis_date_to=date(2024, 1, 8),
            limit=10,
        )

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["saved"], 1)
        self.assertEqual(stats["completed"], 1)

        data = service.get_recent_evaluations(
            code="AAPL",
            eval_window_days=1,
            limit=10,
            page=1,
            analysis_date_from=date(2024, 1, 8),
            analysis_date_to=date(2024, 1, 8),
        )
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["code"], "AAPL.US")

        summary = service.get_summary(scope="stock", code="AAPL", eval_window_days=1)
        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertEqual(summary["code"], "AAPL.US")
        self.assertEqual(summary["completed_count"], 1)

    def test_run_backtest_reaches_legacy_bare_hk_rows_from_supported_aliases(self) -> None:
        with self.db.get_session() as session:
            session.add(
                AnalysisHistory(
                    query_id="q_hk_history_dot",
                    code="1810",
                    name="恒生指数成份股",
                    report_type="simple",
                    sentiment_score=60,
                    operation_advice="买入",
                    trend_prediction="看多",
                    analysis_summary="HK history is dotted, daily is canonical",
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
                    code="1810",
                    date=date(2024, 1, 1),
                    open=100.0,
                    high=100.0,
                    low=100.0,
                    close=100.0,
                )
            )
            session.add(
                StockDaily(
                    code="1810",
                    date=date(2024, 1, 2),
                    high=102.0,
                    low=95.0,
                    close=101.0,
                )
            )
            session.commit()

        service = self._service()
        stats = service.run_backtest(
            code="01810",
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

        for alias in ("1810", "01810", "1810.HK", "HK.01810"):
            data = service.get_recent_evaluations(
                code=alias,
                eval_window_days=1,
                limit=10,
                page=1,
            )
            self.assertEqual(data["total"], 1)
            self.assertEqual(data["items"][0]["code"], "1810")

            summary = service.get_summary(
                scope="stock",
                code=alias,
                eval_window_days=1,
            )
            self.assertIsNotNone(summary)
            assert summary is not None
            self.assertEqual(summary["completed_count"], 1)

    def test_run_backtest_matches_hk_daily_shape_variants_for_prefixed_history(self) -> None:
        with self.db.get_session() as session:
            session.add(
                AnalysisHistory(
                    query_id="q_hk_history_prefixed",
                    code="HK01810",
                    name="恒生指数成份股",
                    report_type="simple",
                    sentiment_score=60,
                    operation_advice="买入",
                    trend_prediction="看多",
                    analysis_summary="HK history is prefixed, daily is dotted",
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
                    code="01810.HK",
                    date=date(2024, 1, 1),
                    open=120.0,
                    high=120.0,
                    low=120.0,
                    close=120.0,
                )
            )
            session.add(
                StockDaily(
                    code="01810.HK",
                    date=date(2024, 1, 2),
                    high=122.0,
                    low=118.0,
                    close=121.0,
                )
            )
            session.commit()

        service = self._service()
        stats = service.run_backtest(
            code="01810",
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

        data = service.get_recent_evaluations(code="01810.HK", eval_window_days=1, limit=10, page=1)
        self.assertEqual(data["total"], 1)

        query_by_prefixed = service.get_recent_evaluations(code="HK01810", eval_window_days=1, limit=10, page=1)
        self.assertEqual(query_by_prefixed["total"], 1)

    def test_run_backtest_persists_snapshot_date_when_start_daily_falls_back(self) -> None:
        with self.db.get_session() as session:
            session.add(
                AnalysisHistory(
                    query_id="q-non-trading-analysis-date",
                    code="000004",
                    name="测试股票",
                    report_type="simple",
                    sentiment_score=60,
                    operation_advice="买入",
                    trend_prediction="看多",
                    analysis_summary="snapshot date is a non-trading day",
                    stop_loss=None,
                    take_profit=None,
                    created_at=datetime(2024, 1, 7, 0, 0, 0),
                    context_snapshot=_phase_snapshot(
                        date(2024, 1, 7),
                        phase="non_trading",
                        market="cn",
                    ),
                )
            )
            session.add(
                StockDaily(code="000004", date=date(2024, 1, 5), open=10.0, high=10.0, low=10.0, close=10.0)
            )
            session.add(
                StockDaily(code="000004", date=date(2024, 1, 8), open=10.0, high=10.7, low=9.8, close=10.5)
            )
            session.commit()

        service = self._service()
        stats = service.run_backtest(
            code="000004",
            force=False,
            eval_window_days=1,
            min_age_days=0,
            analysis_date_from=date(2024, 1, 7),
            analysis_date_to=date(2024, 1, 7),
            limit=10,
        )

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["saved"], 1)
        self.assertEqual(stats["completed"], 1)
        with self.db.get_session() as session:
            result = session.query(BacktestResult).filter(BacktestResult.code == "000004").one()
            self.assertEqual(result.analysis_date, date(2024, 1, 7))
            self.assertAlmostEqual(result.start_price, 10.0)
            self.assertAlmostEqual(result.end_close, 10.5)

        data = service.get_recent_evaluations(
            code="000004",
            eval_window_days=1,
            limit=10,
            page=1,
            analysis_date_from=date(2024, 1, 7),
            analysis_date_to=date(2024, 1, 7),
        )
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["analysis_date"], "2024-01-07")

        summary = service.get_summary(
            scope="stock",
            code="000004",
            eval_window_days=1,
            analysis_date_from=date(2024, 1, 7),
            analysis_date_to=date(2024, 1, 7),
        )
        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertEqual(summary["total_evaluations"], 1)
        self.assertEqual(summary["completed_count"], 1)

    def test_run_backtest_reports_insufficient_daily_data(self) -> None:
        with self.db.get_session() as session:
            session.add(
                AnalysisHistory(
                    query_id="q-insufficient",
                    code="000002",
                    name="万科A",
                    report_type="simple",
                    sentiment_score=60,
                    operation_advice="买入",
                    trend_prediction="看多",
                    analysis_summary="insufficient daily bars",
                    stop_loss=None,
                    take_profit=None,
                    created_at=datetime(2024, 1, 1, 0, 0, 0),
                    context_snapshot=_phase_snapshot(
                        date(2024, 1, 1),
                        phase="postmarket",
                        market="cn",
                        effective_date=date(2024, 1, 1),
                    ),
                )
            )
            session.add(
                StockDaily(code="000002", date=date(2024, 1, 1), open=10.0, high=10.0, low=10.0, close=10.0)
            )
            session.commit()

        service = self._service()
        with patch.object(BacktestService, "_try_fill_daily_data", return_value=None):
            stats = service.run_backtest(code="000002", force=False, eval_window_days=3, min_age_days=0, limit=10)

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["saved"], 1)
        self.assertEqual(stats["completed"], 0)
        self.assertEqual(stats["insufficient"], 1)
        self.assertEqual(stats["diagnostics"]["empty_reason"], "insufficient_daily_data")
        self.assertIn("可用日线行情不足", stats["message"])

    def test_phase_filter_overfetches_before_pagination_and_updates_summary_breakdown(self) -> None:
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
            phase="intraday",
        )

        service = self._service()
        service.run_backtest(code="600519", force=False, eval_window_days=1, min_age_days=0, limit=20)

        intraday = service.get_recent_evaluations(
            code="600519",
            eval_window_days=1,
            limit=1,
            page=1,
            analysis_phase="intraday",
        )
        self.assertEqual(intraday["total"], 1)
        self.assertEqual(len(intraday["items"]), 1)
        self.assertEqual(intraday["items"][0]["market_phase"], "intraday")
        self.assertEqual(intraday["items"][0]["market_phase_summary"]["phase"], "intraday")

        premarket = service.get_recent_evaluations(
            code="600519",
            eval_window_days=1,
            limit=1,
            page=1,
            analysis_phase="premarket",
        )
        self.assertEqual(premarket["total"], 1)
        self.assertEqual(premarket["items"][0]["market_phase"], "premarket")

        summary = service.get_summary(
            scope="stock",
            code="600519",
            eval_window_days=1,
            analysis_phase="intraday",
        )
        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertEqual(summary["total_evaluations"], 1)
        self.assertEqual(summary["diagnostics"]["phase_breakdown"]["intraday"], 1)
        self.assertEqual(summary["diagnostics"]["phase_breakdown"]["premarket"], 0)
        self.assertNotIn("premarket", summary["diagnostics"]["raw_phase_counts"])
        self.assertEqual(summary["diagnostics"]["raw_phase_counts"]["intraday"], 1)


class BacktestDailyRefillSeamTests(_BacktestDailyRefillSeamTestsFixture, unittest.TestCase):
    def test_try_fill_logs_warning_and_swallows_refill_failure(self):
        # 端口抛错时，用例层降级为 warning 且不向外传播——保持原内联实现的错误语义。
        boom = _RecordingDailyRefill(raise_exc=RuntimeError("boom"))
        service = self._service(boom)
        with self.assertLogs("src.application.backtest.service", level="WARNING") as cm:
            service._try_fill_daily_data(
                code="600514", analysis_date=date(2024, 1, 5), eval_window_days=1
            )
        self.assertTrue(any("补全日线数据失败" in m for m in cm.output))
