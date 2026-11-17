"""Tests for main bootstrap."""

from tests.bootstrap.entrypoints._main_schedule_mode_support import (
    MagicMock,
    Path,
    SimpleNamespace,
    _MainScheduleModeTestCaseFixture,
    date,
    datetime,
    logging,
    main,
    patch,
    timezone,
    unittest,
)


class MainScheduleModeTestCase(_MainScheduleModeTestCaseFixture, unittest.TestCase):
    def test_daily_market_context_target_date_routes_jp_kr_calendars(self) -> None:
        current_time = datetime(2026, 5, 7, 0, 30, tzinfo=timezone.utc)
        calls = []

        def resolve_effective_date(market, *, current_time=None):
            calls.append((market, current_time))
            return date(2026, 5, 7)

        with patch(
            "src.domain.market.trading_calendar.get_effective_trading_date",
            side_effect=resolve_effective_date,
        ):
            self.assertEqual(
                main._resolve_daily_market_context_target_date("jp", current_time),
                date(2026, 5, 7),
            )
            self.assertEqual(
                main._resolve_daily_market_context_target_date("kr", current_time),
                date(2026, 5, 7),
            )
            self.assertEqual(
                main._resolve_daily_market_context_target_date("jp,kr", current_time),
                date(2026, 5, 7),
            )

        self.assertEqual(
            calls,
            [
                ("jp", current_time),
                ("kr", current_time),
                ("jp", current_time),
            ],
        )

    def test_standalone_futu_downstream_failure_keeps_existing_exit_semantics(self) -> None:
        args = self._make_args(portfolio="futu")
        config = self._make_config(run_immediately=True)

        with (
            patch("main.parse_arguments", return_value=args),
            patch("main.get_config", return_value=config),
            patch("src.infrastructure.observability.logging_config.setup_logging"),
            patch("main._refresh_stock_index_cache_for_analysis"),
            patch(
                "src.brokers.futu.portfolio.load_futu_stock_codes",
                return_value=["AAPL"],
            ) as loader,
            patch(
                "main._compute_trading_day_filter",
                side_effect=RuntimeError("calendar unavailable"),
            ),
        ):
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        loader.assert_called_once_with()

    def test_reload_runtime_config_refreshes_env_before_resetting_singleton(self) -> None:
        runtime_config = self._make_config(schedule_enabled=True, schedule_time="09:30")
        call_order = []

        def fake_reload_env() -> None:
            call_order.append("reload_env")

        def fake_reset_instance() -> None:
            call_order.append("reset_instance")

        def fake_get_config():
            call_order.append("get_config")
            return runtime_config

        with patch(
            "main._reload_env_file_values_preserving_overrides",
            side_effect=fake_reload_env,
        ), patch(
            "main.Config.reset_instance",
            side_effect=fake_reset_instance,
        ), patch(
            "main.get_config",
            side_effect=fake_get_config,
        ):
            reloaded_config = main._reload_runtime_config()

        self.assertIs(reloaded_config, runtime_config)
        self.assertEqual(call_order, ["reload_env", "reset_instance", "get_config"])

    def test_prime_daily_market_context_query_fallback_reuses_runtime_context(self) -> None:
        target_date = date(2026, 3, 26)
        config = self._make_config(
            trading_day_check_enabled=False,
            market_review_enabled=True,
            market_review_region="cn",
            single_stock_notify=False,
            merge_email_notification=True,
            analysis_delay=0,
            database_path=str(Path(self.temp_dir.name) / "stock_analysis.db"),
        )
        pipeline = MagicMock()
        pipeline._daily_market_context_service = None
        pipeline.db = MagicMock()
        pipeline.query_id = "prime-query"
        context = SimpleNamespace(
            source="market_review_runtime",
            summary="本轮运行时复盘摘要",
            full_report="本轮运行时完整复盘",
            query_id="prime-query",
        )
        service = MagicMock()
        service.get_context.return_value = context

        with patch(
            "src.application.market.daily_market_context.DailyMarketContextService",
            return_value=service,
        ):
            summary, full_report = main._prime_daily_market_context(
                config,
                pipeline=pipeline,
                region="cn",
                no_market_review=False,
                allow_generate=False,
                target_date=target_date,
                return_full_report=True,
                require_current_query_match=True,
            )

        self.assertEqual(summary, "本轮运行时复盘摘要")
        self.assertEqual(full_report, "本轮运行时完整复盘")
        self.assertTrue(service.get_context.call_args.kwargs["require_query_id_match"])

    def test_run_market_review_with_shared_lock_forwards_request_config(self) -> None:
        config = self._make_config(
            trading_day_check_enabled=False,
            market_review_enabled=True,
            daily_market_context_enabled=True,
            single_stock_notify=False,
            merge_email_notification=False,
            analysis_delay=0,
            database_path=str(Path(self.temp_dir.name) / "stock_analysis.db"),
        )
        run_review = MagicMock(return_value="复盘结果")

        with patch("src.application.market.market_review_lock.try_acquire_market_review_lock", return_value=object()) as acquire_lock, \
             patch("src.application.market.market_review_lock.release_market_review_lock") as release_lock:
            result = main._run_market_review_with_shared_lock(
                config,
                run_review,
                send_notification=False,
            )

        self.assertEqual(result, "复盘结果")
        acquire_lock.assert_called_once_with(config)
        run_review.assert_called_once_with(config=config, send_notification=False)
        release_lock.assert_called_once_with(unittest.mock.ANY)

    def test_prime_daily_market_context_uses_ephemeral_service_for_multi_market_region(self) -> None:
        config = self._make_config(
            trading_day_check_enabled=False,
            market_review_enabled=True,
            single_stock_notify=False,
            merge_email_notification=False,
            analysis_delay=0,
            database_path=str(Path(self.temp_dir.name) / "stock_analysis.db"),
        )
        pipeline = MagicMock()
        pipeline._daily_market_context_service = MagicMock()
        pipeline._daily_market_context_service.get_context.return_value = SimpleNamespace(
            source="analysis_history",
            summary="旧A股复盘摘要",
        )
        pipeline.db = MagicMock()
        context = SimpleNamespace(source="analysis_history", summary="多市场复盘摘要", full_report="完整复盘正文")
        regional_service = MagicMock()
        regional_service.get_context.return_value = context

        with patch("src.application.market.daily_market_context.DailyMarketContextService", return_value=regional_service) as service_cls:
            summary, full_report = main._prime_daily_market_context(
                config,
                pipeline=pipeline,
                region="cn,us",
                no_market_review=False,
                allow_generate=False,
                target_date=date(2026, 3, 26),
                return_full_report=True,
            )

        self.assertEqual(summary, "多市场复盘摘要")
        self.assertEqual(full_report, "完整复盘正文")
        service_cls.assert_called_once_with(history_repo=pipeline.db)
        regional_service.get_context.assert_called_once()
        self.assertIsNot(
            regional_service,
            pipeline._daily_market_context_service,
            "多市场预热必须使用独立服务避免共享缓存污染",
        )
        pipeline._daily_market_context_service.get_context.assert_not_called()

        get_context_kwargs = regional_service.get_context.call_args.kwargs
        self.assertEqual(get_context_kwargs["region"], "cn,us")
        self.assertFalse(get_context_kwargs["force_refresh"])
        self.assertFalse(get_context_kwargs["allow_generate"])
        self.assertFalse(get_context_kwargs["persist_market_review_history"])

    def test_bootstrap_logging_persists_when_config_load_fails(self) -> None:
        """Config load failure must be logged to stderr and return exit code 1.

        Bootstrap logging is stderr-only so healthy runs never write to a
        hard-coded directory.  The error is still captured by process runners
        (e.g. GitHub Actions) that collect stderr output.
        """
        import io

        args = self._make_args()

        capture_stream = io.StringIO()
        capture_handler = logging.StreamHandler(capture_stream)
        capture_handler.setLevel(logging.DEBUG)
        capture_handler.setFormatter(logging.Formatter("%(message)s"))

        root_logger = logging.getLogger()

        with patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", side_effect=RuntimeError("config boom")):
            root_logger.addHandler(capture_handler)
            try:
                exit_code = main.main()
            finally:
                root_logger.removeHandler(capture_handler)
                capture_handler.close()

        self.assertEqual(exit_code, 1)
        output = capture_stream.getvalue()
        self.assertIn("加载配置失败", output)
        self.assertIn("config boom", output)

    def test_bootstrap_logging_failure_does_not_block_startup(self) -> None:
        """Bootstrap log dir unwritable must not prevent startup (P1 regression)."""
        args = self._make_args()
        config = self._make_config()

        with patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch("main._setup_bootstrap_logging", side_effect=OSError("read-only fs")), \
             patch("src.infrastructure.observability.logging_config.setup_logging"), \
             patch("main.run_full_analysis") as run_mock:
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        run_mock.assert_called_once()

    def test_runtime_file_logging_permission_error_falls_back_to_console(self) -> None:
        """Configured file logging failures should not prevent Docker startup."""
        import io

        args = self._make_args()
        config = self._make_config(log_dir="/app/logs")
        capture_stream = io.StringIO()
        capture_handler = logging.StreamHandler(capture_stream)
        capture_handler.setLevel(logging.DEBUG)
        capture_handler.setFormatter(logging.Formatter("%(message)s"))

        root_logger = logging.getLogger()

        with patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch(
                 "src.infrastructure.observability.logging_config.setup_logging",
                 side_effect=PermissionError("/app/logs/stock_analysis_20260511.log"),
             ), \
             patch("main.run_full_analysis") as run_mock:
            root_logger.addHandler(capture_handler)
            try:
                exit_code = main.main()
            finally:
                root_logger.removeHandler(capture_handler)
                capture_handler.close()

        self.assertEqual(exit_code, 0)
        run_mock.assert_called_once()
        output = capture_stream.getvalue()
        self.assertIn("文件日志初始化失败，已降级为控制台日志输出", output)
        self.assertIn("/app/logs", output)
        self.assertIn("官方 Docker 镜像启动入口会自动修复默认挂载目录权限", output)

    def test_lazy_pipeline_triggers_env_bootstrap(self) -> None:
        """P2: lazy StockAnalysisPipeline access must call _bootstrap_environment."""
        # Reset the lazy descriptor cache so __get__ fires again
        main._LazyPipelineDescriptor._resolved = None
        main._env_bootstrapped = False

        with patch("main._bootstrap_environment", wraps=main._bootstrap_environment) as mock_boot, \
             patch("src.application.analysis.pipeline.StockAnalysisPipeline", create=True, new_callable=lambda: type("FakePipeline", (), {})):
            try:
                _ = main.StockAnalysisPipeline
            except Exception:
                pass
            mock_boot.assert_called()

        # Cleanup: reset state
        main._LazyPipelineDescriptor._resolved = None
        main._env_bootstrapped = False
