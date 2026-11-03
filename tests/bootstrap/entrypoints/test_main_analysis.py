"""Tests for main analysis."""

from tests.bootstrap.entrypoints._main_schedule_mode_support import (
    MagicMock,
    Path,
    SimpleNamespace,
    _MainScheduleModeTestCaseFixture,
    date,
    main,
    patch,
    timezone,
    unittest,
)


class MainScheduleModeTestCase(_MainScheduleModeTestCaseFixture, unittest.TestCase):
    def test_standalone_run_resolves_stocks_before_run_full_analysis(self) -> None:
        args = self._make_args(stocks="005930")
        config = self._make_config(run_immediately=True)

        with patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch("src.infrastructure.observability.logging_config.setup_logging"), \
             patch("main.run_full_analysis") as run_full_analysis:
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        run_full_analysis.assert_called_once()
        _, _, stock_codes = run_full_analysis.call_args.args
        self.assertEqual(stock_codes, ["005930.KS"])

    def test_run_full_analysis_skips_market_review_when_shared_lock_is_held(self) -> None:
        from src.application.market.market_review_lock import (
            release_market_review_lock,
            try_acquire_market_review_lock,
        )

        args = self._make_args()
        config = self._make_config(
            trading_day_check_enabled=False,
            market_review_enabled=True,
            daily_market_context_enabled=True,
            no_market_review=False,
            single_stock_notify=False,
            merge_email_notification=False,
            analysis_delay=0,
            database_path=str(Path(self.temp_dir.name) / "stock_analysis.db"),
        )
        pipeline = MagicMock()
        pipeline.run.return_value = []
        events = []
        pipeline_kwargs = {}

        def refresh_index(config_arg):
            events.append("refresh")

        def build_pipeline(*args, **kwargs):
            events.append("pipeline")
            pipeline_kwargs.update(kwargs)
            return pipeline

        lock_token = try_acquire_market_review_lock(config)
        self.assertIsNotNone(lock_token)
        try:
            with patch.object(main, "_refresh_stock_index_cache_for_analysis", side_effect=refresh_index) as refresh, \
                 patch("src.application.analysis.pipeline.StockAnalysisPipeline", side_effect=build_pipeline), \
                 patch("src.application.market.market_review.run_market_review") as run_market_review:
                main.run_full_analysis(config, args, [])
        finally:
            release_market_review_lock(lock_token)

            refresh.assert_called_once_with(config)
        self.assertEqual(events[:2], ["refresh", "pipeline"])
        self.assertTrue(pipeline_kwargs["daily_market_context_allow_generate"])
        pipeline.run.assert_called_once()
        run_market_review.assert_not_called()

    def test_run_full_analysis_defaults_daily_context_on_without_disabling_market_review(self) -> None:
        args = self._make_args()
        config = self._make_config(
            trading_day_check_enabled=False,
            market_review_enabled=True,
            single_stock_notify=False,
            merge_email_notification=False,
            analysis_delay=0,
            database_path=str(Path(self.temp_dir.name) / "stock_analysis.db"),
        )
        pipeline = MagicMock()
        pipeline.run.return_value = []
        pipeline_kwargs = {}

        def build_pipeline(*args, **kwargs):
            pipeline_kwargs.update(kwargs)
            return pipeline

        with patch.object(main, "_refresh_stock_index_cache_for_analysis") as refresh, \
             patch("main._compute_trading_day_filter", return_value=([], "cn", False)), \
             patch("src.application.analysis.pipeline.StockAnalysisPipeline", side_effect=build_pipeline), \
             patch("main._prime_daily_market_context", side_effect=[("", ""), ("缓存摘要", "完整复盘")]) as prime_context, \
             patch("main._run_market_review_with_shared_lock", return_value=SimpleNamespace(report="大盘复盘")) as run_with_lock:
            main.run_full_analysis(config, args, [])

        self.assertTrue(pipeline_kwargs["daily_market_context_enabled"])
        self.assertTrue(pipeline_kwargs["daily_market_context_allow_generate"])
        self.assertEqual(prime_context.call_count, 2)
        run_with_lock.assert_called_once()
        refresh.assert_called_once_with(config)

    def test_run_full_analysis_primes_daily_market_context_before_stock_analysis(self) -> None:
        args = self._make_args()
        target_date = date(2026, 3, 26)
        reference_times = []
        config = self._make_config(
            trading_day_check_enabled=False,
            market_review_enabled=True,
            daily_market_context_enabled=True,
            single_stock_notify=False,
            merge_email_notification=False,
            analysis_delay=0,
            database_path=str(Path(self.temp_dir.name) / "stock_analysis.db"),
        )
        pipeline = MagicMock()
        pipeline.run.return_value = []
        pipeline_kwargs = {}

        def build_pipeline(*args, **kwargs):
            pipeline_kwargs.update(kwargs)
            return pipeline

        def resolve_target_date(region, current_time):
            self.assertEqual(region, "cn")
            reference_times.append(current_time)
            return target_date

        with patch.object(main, "_refresh_stock_index_cache_for_analysis") as refresh, \
             patch("main._compute_trading_day_filter", return_value=([], "cn", False)), \
             patch("main._resolve_daily_market_context_target_date", side_effect=resolve_target_date), \
             patch("src.application.analysis.pipeline.StockAnalysisPipeline", side_effect=build_pipeline), \
             patch("main._prime_daily_market_context", return_value=("大盘退潮，高风险，建议观望，仓位上限30%。", "完整复盘正文")) as prime_context, \
             patch("main._run_market_review_with_shared_lock") as run_with_lock, \
             patch("src.application.market.market_review.run_market_review") as run_market_review:
            main.run_full_analysis(config, args, [])

        self.assertTrue(pipeline_kwargs["daily_market_context_allow_generate"])
        prime_context.assert_has_calls(
            [
                unittest.mock.call(
                    config,
                    pipeline=pipeline,
                    region="cn",
                    no_market_review=False,
                    allow_generate=False,
                    target_date=target_date,
                    return_full_report=False,
                ),
                unittest.mock.call(
                    config,
                    pipeline=pipeline,
                    region="cn",
                    no_market_review=False,
                    allow_generate=False,
                    target_date=target_date,
                    return_full_report=True,
                    require_current_query_match=True,
                ),
            ]
        )
        self.assertEqual(len(reference_times), 1)
        self.assertIs(pipeline.run.call_args.kwargs["current_time"], reference_times[0])
        self.assertEqual(pipeline.run.call_args.kwargs["current_time"].tzinfo, timezone.utc)
        run_with_lock.assert_called_once()
        self.assertFalse(run_with_lock.call_args.kwargs["merge_notification"])
        self.assertTrue(run_with_lock.call_args.kwargs["send_notification"])
        run_market_review.assert_not_called()
        refresh.assert_called_once_with(config)
        pipeline.run.assert_called_once()

    def test_run_full_analysis_does_not_reuse_single_context_for_multi_market_review(self) -> None:
        args = self._make_args()
        target_date = date(2026, 3, 26)
        config = self._make_config(
            trading_day_check_enabled=True,
            market_review_region="both",
            market_review_enabled=True,
            daily_market_context_enabled=True,
            single_stock_notify=False,
            merge_email_notification=False,
            analysis_delay=0,
            database_path=str(Path(self.temp_dir.name) / "stock_analysis.db"),
        )
        pipeline = MagicMock()
        pipeline.run.return_value = []
        pipeline_kwargs = {}

        def build_pipeline(*args, **kwargs):
            pipeline_kwargs.update(kwargs)
            return pipeline

        with patch.object(main, "_refresh_stock_index_cache_for_analysis") as refresh, \
             patch("main._compute_trading_day_filter", return_value=([], "cn,us", False)), \
             patch("main._resolve_daily_market_context_target_date", return_value=target_date), \
             patch("src.application.analysis.pipeline.StockAnalysisPipeline", side_effect=build_pipeline), \
             patch("main._prime_daily_market_context", return_value=("A股缓存摘要", "")) as prime_context, \
             patch("main._run_market_review_with_shared_lock", return_value="多市场复盘") as run_with_lock, \
             patch("src.application.market.market_review.run_market_review") as run_market_review:
            main.run_full_analysis(config, args, [])

        self.assertTrue(pipeline_kwargs["daily_market_context_allow_generate"])
        prime_context.assert_has_calls(
            [
                unittest.mock.call(
                    config,
                    pipeline=pipeline,
                    region="cn,us",
                    no_market_review=False,
                    allow_generate=False,
                    target_date=target_date,
                    return_full_report=False,
                ),
                unittest.mock.call(
                    config,
                    pipeline=pipeline,
                    region="cn,us",
                    no_market_review=False,
                    allow_generate=False,
                    target_date=target_date,
                    return_full_report=True,
                    require_current_query_match=True,
                ),
            ]
        )
        run_with_lock.assert_called_once()
        self.assertEqual(run_with_lock.call_args.kwargs["override_region"], "cn,us")
        run_market_review.assert_not_called()
        refresh.assert_called_once_with(config)
        pipeline.run.assert_called_once()

    def test_run_full_analysis_generates_full_market_review_once_after_stock_analysis(self) -> None:
        args = self._make_args()
        target_date = date(2026, 3, 26)
        config = self._make_config(
            trading_day_check_enabled=False,
            market_review_enabled=True,
            daily_market_context_enabled=True,
            single_stock_notify=False,
            merge_email_notification=False,
            analysis_delay=0,
            database_path=str(Path(self.temp_dir.name) / "stock_analysis.db"),
        )
        pipeline = MagicMock()
        events = []
        pipeline.run.side_effect = lambda **kwargs: events.append("stock-run") or []
        pipeline_kwargs = {}

        def build_pipeline(*args, **kwargs):
            events.append("pipeline")
            pipeline_kwargs.update(kwargs)
            return pipeline

        def run_with_lock(*args, **kwargs):
            events.append("market-review")
            return SimpleNamespace(report="完整复盘")

        with patch.object(main, "_refresh_stock_index_cache_for_analysis") as refresh, \
             patch("main._compute_trading_day_filter", return_value=([], "cn", False)), \
             patch("main._resolve_daily_market_context_target_date", return_value=target_date), \
             patch("src.application.analysis.pipeline.StockAnalysisPipeline", side_effect=build_pipeline), \
             patch("main._prime_daily_market_context", return_value=("", "")) as prime_context, \
             patch("main._run_market_review_with_shared_lock", side_effect=run_with_lock) as run_with_lock_mock, \
             patch("src.application.market.market_review.run_market_review") as run_market_review:
            main.run_full_analysis(config, args, [])

        self.assertTrue(pipeline_kwargs["daily_market_context_allow_generate"])
        self.assertEqual(events, ["pipeline", "stock-run", "market-review"])
        query_scoped_read = unittest.mock.call(
            config,
            pipeline=pipeline,
            region="cn",
            no_market_review=False,
            allow_generate=False,
            target_date=target_date,
            return_full_report=True,
            require_current_query_match=True,
        )
        self.assertEqual(
            prime_context.call_args_list,
            [
                unittest.mock.call(
                    config,
                    pipeline=pipeline,
                    region="cn",
                    no_market_review=False,
                    allow_generate=False,
                    target_date=target_date,
                    return_full_report=False,
                ),
                query_scoped_read,
                query_scoped_read,
            ],
        )
        run_with_lock_mock.assert_called_once()
        run_market_review.assert_not_called()
        refresh.assert_called_once_with(config)
        pipeline.run.assert_called_once()

    def test_run_full_analysis_reuses_runtime_market_context_after_stock_analysis(self) -> None:
        args = self._make_args()
        target_date = date(2026, 3, 26)
        config = self._make_config(
            trading_day_check_enabled=False,
            market_review_enabled=True,
            daily_market_context_enabled=True,
            single_stock_notify=False,
            merge_email_notification=False,
            analysis_delay=0,
            database_path=str(Path(self.temp_dir.name) / "stock_analysis.db"),
        )
        pipeline = MagicMock()
        pipeline.run.return_value = []
        pipeline.notifier = MagicMock(
            is_available=MagicMock(return_value=True),
            send=MagicMock(return_value=True),
        )
        pipeline_kwargs = {}

        def build_pipeline(*args, **kwargs):
            pipeline_kwargs.update(kwargs)
            return pipeline

        runtime_context = ("本轮运行时复盘摘要", "## 本轮运行时完整复盘")
        with patch.object(main, "_refresh_stock_index_cache_for_analysis") as refresh, \
             patch("main._compute_trading_day_filter", return_value=([], "cn", False)), \
             patch("main._resolve_daily_market_context_target_date", return_value=target_date), \
             patch("src.application.analysis.pipeline.StockAnalysisPipeline", side_effect=build_pipeline), \
             patch(
                 "main._prime_daily_market_context",
                 side_effect=[("", ""), ("", ""), runtime_context],
             ) as prime_context, \
             patch("main._run_market_review_with_shared_lock") as run_with_lock, \
             patch("src.application.market.market_review.run_market_review") as run_market_review:
            main.run_full_analysis(config, args, [])

        self.assertTrue(pipeline_kwargs["daily_market_context_allow_generate"])
        run_with_lock.assert_not_called()
        run_market_review.assert_not_called()
        pipeline.notifier.send.assert_called_once()
        self.assertIn("## 本轮运行时完整复盘", pipeline.notifier.send.call_args.args[0])
        self.assertEqual(pipeline.notifier.send.call_args.kwargs["route_type"], "report")
        query_scoped_read = unittest.mock.call(
            config,
            pipeline=pipeline,
            region="cn",
            no_market_review=False,
            allow_generate=False,
            target_date=target_date,
            return_full_report=True,
            require_current_query_match=True,
        )
        self.assertEqual(
            prime_context.call_args_list,
            [
                unittest.mock.call(
                    config,
                    pipeline=pipeline,
                    region="cn",
                    no_market_review=False,
                    allow_generate=False,
                    target_date=target_date,
                    return_full_report=False,
                ),
                query_scoped_read,
                query_scoped_read,
            ],
        )
        refresh.assert_called_once_with(config)
        pipeline.run.assert_called_once()

    def test_run_full_analysis_saves_reused_runtime_market_context_without_notify(self) -> None:
        args = self._make_args(no_notify=True)
        target_date = date(2026, 3, 26)
        config = self._make_config(
            trading_day_check_enabled=False,
            market_review_enabled=True,
            daily_market_context_enabled=True,
            single_stock_notify=False,
            merge_email_notification=False,
            analysis_delay=0,
            database_path=str(Path(self.temp_dir.name) / "stock_analysis.db"),
        )
        pipeline = MagicMock()
        pipeline.run.return_value = []
        pipeline.notifier = MagicMock()
        pipeline.notifier.save_report_to_file.return_value = "/tmp/market_review.md"

        def build_pipeline(*args, **kwargs):
            return pipeline

        runtime_context = ("本轮运行时复盘摘要", "## 本轮运行时完整复盘")
        with (
            patch.object(main, "_refresh_stock_index_cache_for_analysis") as refresh,
            patch("main._compute_trading_day_filter", return_value=([], "cn", False)),
            patch("main._resolve_daily_market_context_target_date", return_value=target_date),
            patch("src.application.analysis.pipeline.StockAnalysisPipeline", side_effect=build_pipeline),
            patch(
                "main._prime_daily_market_context",
                side_effect=[("", ""), ("", ""), runtime_context],
            ) as prime_context,
            patch("main._run_market_review_with_shared_lock") as run_with_lock,
            patch("src.application.market.market_review.run_market_review") as run_market_review,
        ):
            main.run_full_analysis(config, args, [])

        run_with_lock.assert_not_called()
        run_market_review.assert_not_called()
        pipeline.notifier.send.assert_not_called()
        pipeline.notifier.save_report_to_file.assert_called_once()
        saved_content, saved_filename = pipeline.notifier.save_report_to_file.call_args.args
        self.assertTrue(saved_content.startswith("# 🎯 大盘复盘\n\n"))
        self.assertIn("## 本轮运行时完整复盘", saved_content)
        self.assertTrue(saved_filename.startswith("market_review_"))
        self.assertTrue(saved_filename.endswith(".md"))
        self.assertEqual(prime_context.call_count, 3)
        refresh.assert_called_once_with(config)
        pipeline.run.assert_called_once()

    def test_run_full_analysis_still_runs_market_review_for_merge_disabled_with_reused_context(self) -> None:
        args = self._make_args()
        target_date = date(2026, 3, 26)
        config = self._make_config(
            trading_day_check_enabled=False,
            market_review_enabled=True,
            daily_market_context_enabled=True,
            single_stock_notify=False,
            merge_email_notification=False,
            analysis_delay=0,
            database_path=str(Path(self.temp_dir.name) / "stock_analysis.db"),
        )
        pipeline = MagicMock()
        pipeline.run.return_value = []
        pipeline_kwargs = {}

        def build_pipeline(*args, **kwargs):
            pipeline_kwargs.update(kwargs)
            return pipeline

        with patch.object(main, "_refresh_stock_index_cache_for_analysis") as refresh, \
             patch("main._compute_trading_day_filter", return_value=([], "cn", False)), \
             patch("main._resolve_daily_market_context_target_date", return_value=target_date), \
             patch("src.application.analysis.pipeline.StockAnalysisPipeline", side_effect=build_pipeline), \
             patch(
                "main._prime_daily_market_context",
                return_value=("大盘退潮，高风险，建议观望。", "## 完整大盘复盘\n市场结构偏弱，建议保守。"),
             ) as prime_context, \
             patch("main._run_market_review_with_shared_lock") as run_with_lock, \
             patch("src.application.market.market_review.run_market_review") as run_market_review:
            main.run_full_analysis(config, args, [])

        self.assertTrue(pipeline_kwargs["daily_market_context_allow_generate"])
        prime_context.assert_has_calls(
            [
                unittest.mock.call(
                    config,
                    pipeline=pipeline,
                    region="cn",
                    no_market_review=False,
                    allow_generate=False,
                    target_date=target_date,
                    return_full_report=False,
                ),
                unittest.mock.call(
                    config,
                    pipeline=pipeline,
                    region="cn",
                    no_market_review=False,
                    allow_generate=False,
                    target_date=target_date,
                    return_full_report=True,
                    require_current_query_match=True,
                ),
            ]
        )
        run_with_lock.assert_called_once()
        self.assertFalse(run_with_lock.call_args.kwargs["merge_notification"])
        run_market_review.assert_not_called()
        refresh.assert_called_once_with(config)
        pipeline.run.assert_called_once()

    def test_run_full_analysis_waits_for_analysis_delay_before_market_review(self) -> None:
        args = self._make_args()
        target_date = date(2026, 3, 26)
        config = self._make_config(
            trading_day_check_enabled=False,
            market_review_enabled=True,
            daily_market_context_enabled=True,
            single_stock_notify=False,
            merge_email_notification=False,
            analysis_delay=2,
            database_path=str(Path(self.temp_dir.name) / "stock_analysis.db"),
        )
        pipeline = MagicMock()
        events = []
        pipeline.run.side_effect = lambda **kwargs: events.append("stock-run") or []
        pipeline_kwargs = {}

        def build_pipeline(*args, **kwargs):
            events.append("pipeline")
            pipeline_kwargs.update(kwargs)
            return pipeline

        def run_with_lock(*args, **kwargs):
            events.append("market-review")
            return SimpleNamespace(report="完整复盘")

        with patch.object(main, "_refresh_stock_index_cache_for_analysis") as refresh, \
             patch("main._compute_trading_day_filter", return_value=([], "cn", False)), \
             patch("main._resolve_daily_market_context_target_date", return_value=target_date), \
             patch("src.application.analysis.pipeline.StockAnalysisPipeline", side_effect=build_pipeline), \
             patch("main._prime_daily_market_context", return_value=("", "")) as prime_context, \
             patch("main._run_market_review_with_shared_lock", side_effect=run_with_lock) as run_with_lock_mock, \
             patch("time.sleep") as sleep, \
             patch("src.application.market.market_review.run_market_review") as run_market_review:
            main.run_full_analysis(config, args, [])

        self.assertTrue(pipeline_kwargs["daily_market_context_allow_generate"])
        self.assertEqual(events, ["pipeline", "stock-run", "market-review"])
        self.assertEqual(sleep.call_count, 1)
        sleep.assert_called_once_with(2)
        self.assertEqual(
            run_with_lock_mock.call_args.kwargs["send_notification"],
            True,
        )
        run_market_review.assert_not_called()
        run_with_lock_mock.assert_called_once()
        refresh.assert_called_once_with(config)
        prime_context.assert_has_calls(
            [
                unittest.mock.call(
                    config,
                    pipeline=pipeline,
                    region="cn",
                    no_market_review=False,
                    allow_generate=False,
                    target_date=target_date,
                    return_full_report=False,
                ),
                unittest.mock.call(
                    config,
                    pipeline=pipeline,
                    region="cn",
                    no_market_review=False,
                    allow_generate=False,
                    target_date=target_date,
                    return_full_report=True,
                    require_current_query_match=True,
                ),
                unittest.mock.call(
                    config,
                    pipeline=pipeline,
                    region="cn",
                    no_market_review=False,
                    allow_generate=False,
                    target_date=target_date,
                    return_full_report=True,
                    require_current_query_match=True,
                ),
            ]
        )
