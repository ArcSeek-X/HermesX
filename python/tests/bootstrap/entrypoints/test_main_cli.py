"""Tests for main cli."""

from tests.bootstrap.entrypoints._main_schedule_mode_support import (
    MagicMock,
    Path,
    SimpleNamespace,
    _MainScheduleModeTestCaseFixture,
    date,
    main,
    patch,
    unittest,
)


class MainScheduleModeTestCase(_MainScheduleModeTestCaseFixture, unittest.TestCase):
    def test_check_notify_returns_before_other_modes(self) -> None:
        args = self._make_args(check_notify=True, serve=True, schedule=True, market_review=True)
        config = self._make_config(webui_enabled=False)
        diagnostic_result = SimpleNamespace(ok=True)

        with patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch("src.infrastructure.observability.logging_config.setup_logging"), \
             patch("main.start_api_server") as start_api_server, \
             patch("main.run_full_analysis") as run_full_analysis, \
             patch(
                 "src.application.alert.notification_diagnostics.run_notification_diagnostics",
                 return_value=diagnostic_result,
             ) as run_diagnostics, \
             patch(
                 "src.application.alert.notification_diagnostics.format_notification_diagnostics",
                 return_value="通知配置诊断",
             ), \
             patch("builtins.print") as print_output:
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        run_diagnostics.assert_called_once_with(config)
        print_output.assert_called_once_with("通知配置诊断")
        start_api_server.assert_not_called()
        run_full_analysis.assert_not_called()

    def test_single_run_keeps_cli_stock_override(self) -> None:
        args = self._make_args(stocks="600519,000001")
        config = self._make_config(run_immediately=True)

        with patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch("src.infrastructure.observability.logging_config.setup_logging"), \
             patch("main.run_full_analysis") as run_full_analysis:
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        run_full_analysis.assert_called_once_with(config, args, ["600519", "000001"])

    def test_run_full_analysis_disables_generation_when_no_market_review_flag_set(self) -> None:
        args = self._make_args(no_market_review=True)
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
             patch("src.application.analysis.pipeline.StockAnalysisPipeline", side_effect=build_pipeline), \
             patch("main._prime_daily_market_context") as prime_context, \
             patch("src.application.market.market_review.run_market_review") as run_market_review:
            main.run_full_analysis(config, args, [])

        self.assertFalse(pipeline_kwargs["daily_market_context_allow_generate"])
        self.assertEqual(pipeline_kwargs["daily_market_context_enabled"], False)
        prime_context.assert_not_called()
        run_market_review.assert_not_called()
        refresh.assert_called_once_with(config)

    def test_prime_daily_market_context_readonly_mode_still_reuses_cached_context(self) -> None:
        target_date = date(2026, 3, 26)
        config = self._make_config(
            trading_day_check_enabled=False,
            market_review_enabled=True,
            market_review_region="cn",
            single_stock_notify=False,
            merge_email_notification=False,
            analysis_delay=0,
            database_path=str(Path(self.temp_dir.name) / "stock_analysis.db"),
        )
        pipeline = MagicMock()
        pipeline._daily_market_context_service = None
        pipeline.db = MagicMock()
        pipeline.query_id = "prime-query"
        context = SimpleNamespace(source="analysis_history", summary="历史复盘摘要")
        service = MagicMock()
        service.get_context.return_value = context

        with patch(
            "src.application.market.daily_market_context.DailyMarketContextService",
            return_value=service,
        ) as service_cls:
            summary, full_report = main._prime_daily_market_context(
                config,
                pipeline=pipeline,
                region="cn",
                no_market_review=False,
                allow_generate=False,
                target_date=target_date,
                return_full_report=True,
            )

        self.assertEqual(summary, "历史复盘摘要")
        self.assertEqual(full_report, "")
        service_cls.assert_called_once_with(history_repo=pipeline.db)
        call_kwargs = service.get_context.call_args.kwargs
        self.assertEqual(call_kwargs["region"], "cn")
        self.assertFalse(call_kwargs["force_refresh"])
        self.assertFalse(call_kwargs["allow_generate"])
        self.assertFalse(call_kwargs["persist_market_review_history"])
        self.assertEqual(call_kwargs["target_date"], target_date)
        self.assertEqual(call_kwargs["current_query_id"], "prime-query")

    def test_market_review_mode_uses_shared_runtime_assembly(self) -> None:
        args = self._make_args(market_review=True)
        config = self._make_config(
            trading_day_check_enabled=True,
            market_review_region="both",
            market_review_enabled=False,
            database_path=str(Path(self.temp_dir.name) / "stock_analysis.db"),
        )
        runtime_notifier = MagicMock()
        runtime_analyzer = MagicMock()
        runtime_search_service = MagicMock()

        with patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch("src.infrastructure.observability.logging_config.setup_logging"), \
             patch("main._run_market_review_with_shared_lock") as run_with_lock, \
             patch(
                 "src.application.market.market_review_runtime.build_market_review_runtime",
                 return_value=(
                    runtime_notifier,
                    runtime_analyzer,
                    runtime_search_service,
                 ),
             ) as runtime_builder, \
             patch("src.application.market.market_review.run_market_review") as run_market_review, \
             patch("src.domain.market.trading_calendar.get_open_markets_today", return_value={"cn", "us"}), \
             patch("src.domain.market.trading_calendar.compute_effective_region", return_value="cn,us"):
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        runtime_builder.assert_called_once_with(config)
        run_with_lock.assert_called_once()
        call_args = run_with_lock.call_args
        self.assertEqual(call_args.args[0], config)
        self.assertIs(call_args.args[1], run_market_review)
        self.assertIs(call_args.kwargs["notifier"], runtime_notifier)
        self.assertIs(call_args.kwargs["analyzer"], runtime_analyzer)
        self.assertIs(call_args.kwargs["search_service"], runtime_search_service)
        self.assertTrue(call_args.kwargs["send_notification"])
        self.assertNotIn("merge_notification", call_args.kwargs)
        self.assertEqual(call_args.kwargs["override_region"], "cn,us")
        self.assertEqual(call_args.kwargs["trigger_source"], "cli")

    def test_market_review_mode_respects_comma_list_market_review_region(self) -> None:
        args = self._make_args(market_review=True)
        config = self._make_config(
            trading_day_check_enabled=True,
            market_review_region="jp,kr",
            market_review_enabled=False,
            database_path=str(Path(self.temp_dir.name) / "stock_analysis.db"),
        )
        runtime_notifier = MagicMock()
        runtime_analyzer = MagicMock()
        runtime_search_service = MagicMock()

        with patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch("src.infrastructure.observability.logging_config.setup_logging"), \
             patch("main._run_market_review_with_shared_lock") as run_with_lock, \
             patch(
                 "src.application.market.market_review_runtime.build_market_review_runtime",
                 return_value=(runtime_notifier, runtime_analyzer, runtime_search_service),
             ) as runtime_builder, \
             patch("src.application.market.market_review.run_market_review"), \
             patch("src.domain.market.trading_calendar.get_open_markets_today", return_value={"jp", "kr"}):
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        runtime_builder.assert_called_once_with(config)
        call_args = run_with_lock.call_args
        self.assertIs(call_args.args[0], config)
        self.assertEqual(call_args.kwargs["override_region"], "jp,kr")
        self.assertEqual(call_args.kwargs["trigger_source"], "cli")
