"""Tests for main server."""

from tests.bootstrap.entrypoints._main_schedule_mode_support import (
    FutuPortfolioError,
    MagicMock,
    Path,
    SimpleNamespace,
    _MainScheduleModeTestCaseFixture,
    _api_app_stub_modules,
    date,
    main,
    os,
    patch,
    socket,
    unittest,
)


class MainScheduleModeTestCase(_MainScheduleModeTestCaseFixture, unittest.TestCase):
    def test_public_webui_bind_warns_when_auth_is_disabled(self) -> None:
        with patch("src.auth.is_auth_enabled", return_value=False), \
             patch("src.bootstrap.environment.logger.warning") as warning_log:
            main._warn_if_public_webui_without_auth("0.0.0.0")

        warning_log.assert_called_once()
        self.assertIn("WEBUI_HOST=%s", warning_log.call_args.args[0])
        self.assertEqual(warning_log.call_args.args[1], "0.0.0.0")

    def test_loopback_webui_bind_does_not_warn_when_auth_is_disabled(self) -> None:
        with patch("src.auth.is_auth_enabled", return_value=False), \
             patch("src.bootstrap.environment.logger.warning") as warning_log:
            main._warn_if_public_webui_without_auth("127.0.0.1")

        warning_log.assert_not_called()

    def test_web_service_bind_uses_config_when_cli_omits_host_and_port(self) -> None:
        args = self._make_args(host=None, port=None)
        config = self._make_config(webui_host="127.0.0.1", webui_port=18000)

        host, port = main._resolve_web_service_bind(args, config)

        self.assertEqual(host, "127.0.0.1")
        self.assertEqual(port, 18000)

    def test_web_service_bind_keeps_explicit_cli_host_and_port(self) -> None:
        args = self._make_args(host="0.0.0.0", port=8000)
        config = self._make_config(webui_host="127.0.0.1", webui_port=18000)

        host, port = main._resolve_web_service_bind(args, config)

        self.assertEqual(host, "0.0.0.0")
        self.assertEqual(port, 8000)

    def test_serve_only_uses_config_bind_when_cli_omits_host_and_port(self) -> None:
        args = self._make_args(serve_only=True)
        config = self._make_config(webui_enabled=False, webui_host="127.0.0.1", webui_port=18000)
        observed_bind = []

        def fake_start_api_server(host, port, config):
            observed_bind.append((host, port))

        with patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}, clear=False), \
             patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch("main.prepare_webui_frontend_assets", return_value=True), \
             patch("main.start_api_server", side_effect=fake_start_api_server), \
             patch("main.start_bot_stream_clients"), \
             patch("main.time.sleep", side_effect=KeyboardInterrupt):
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(observed_bind, [("127.0.0.1", 18000)])

    def test_serve_only_keeps_explicit_cli_bind_over_config(self) -> None:
        args = self._make_args(serve_only=True, host="0.0.0.0", port=8000)
        config = self._make_config(webui_enabled=False, webui_host="127.0.0.1", webui_port=18000)
        observed_bind = []

        def fake_start_api_server(host, port, config):
            observed_bind.append((host, port))

        with patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}, clear=False), \
             patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch("main.prepare_webui_frontend_assets", return_value=True), \
             patch("main.start_api_server", side_effect=fake_start_api_server), \
             patch("main.start_bot_stream_clients"), \
             patch("main.time.sleep", side_effect=KeyboardInterrupt):
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(observed_bind, [("0.0.0.0", 8000)])

    def test_start_api_server_fails_before_thread_when_port_is_busy(self) -> None:
        config = self._make_config(log_level="INFO")

        class BusySocket:
            def bind(self, address):
                raise OSError("address already in use")

            def close(self):
                pass

        with patch("socket.socket", return_value=BusySocket()) as socket_factory, \
             patch("threading.Thread") as thread_cls:
            with self.assertRaises(RuntimeError) as caught:
                main.start_api_server("127.0.0.1", 8000, config)

        socket_factory.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        self.assertIn("127.0.0.1:8000", str(caught.exception))
        thread_cls.assert_not_called()

    def test_start_api_server_fails_when_uvicorn_background_startup_fails(self) -> None:
        config = self._make_config(log_level="INFO")

        class _FakeUvicornServer:
            def __init__(self, config):
                self.config = config
                self.started = False

            def run(self) -> None:
                raise RuntimeError("lifespan bootstrap failed")

        class _FakeUvicornConfig:
            def __init__(self, *args, **kwargs):
                pass

        class _FakeUvicornModule:
            Config = _FakeUvicornConfig

            Server = _FakeUvicornServer

        class _UnusedSocket:
            def bind(self, address):
                pass

            def close(self):
                pass

        with patch("socket.socket", return_value=_UnusedSocket()), \
             patch.dict(
                 "sys.modules",
                 {"uvicorn": _FakeUvicornModule(), **_api_app_stub_modules()},
             ):

            with self.assertRaises(RuntimeError) as caught:
                main.start_api_server("127.0.0.1", 8000, config)

        self.assertIn("lifespan bootstrap failed", str(caught.exception))

    def test_start_api_server_compatible_with_uvicorn_install_signal_handlers_method(self) -> None:
        config = self._make_config(log_level="INFO")

        class _CompatServer:
            instance = None

            def __init__(self, config):
                type(self).instance = self
                self.config = config
                self.started = False
                self.install_signal_handlers = self._install_signal_handlers

            def _install_signal_handlers(self) -> None:
                return None

            def run(self) -> None:
                self.started = True

        class _CompatConfig:
            def __init__(self, *args, **kwargs):
                if "install_signal_handlers" in kwargs:
                    raise TypeError("install_signal_handlers is unsupported")

        class _UnusedSocket:
            def bind(self, address):
                pass

            def close(self):
                pass

        with patch("socket.socket", return_value=_UnusedSocket()), \
             patch.dict(
                 "sys.modules",
                 {
                     "uvicorn": SimpleNamespace(Config=_CompatConfig, Server=_CompatServer),
                     **_api_app_stub_modules(),
                 },
             ):
            main.start_api_server("127.0.0.1", 8000, config)

        self.assertIsNotNone(_CompatServer.instance)
        self.assertTrue(callable(_CompatServer.instance.install_signal_handlers))
        self.assertTrue(_CompatServer.instance.started)

    def test_standalone_futu_portfolio_failure_returns_nonzero(self) -> None:
        args = self._make_args(portfolio="futu")
        config = self._make_config(run_immediately=True)
        error = FutuPortfolioError("OpenD unavailable")

        with (
            patch("main.parse_arguments", return_value=args),
            patch("main.get_config", return_value=config),
            patch("src.infrastructure.observability.logging_config.setup_logging"),
            patch("main._refresh_stock_index_cache_for_analysis"),
            patch(
                "src.brokers.futu.portfolio.load_futu_stock_codes",
                side_effect=error,
            ) as loader,
        ):
            exit_code = main.main()

        self.assertEqual(exit_code, 1)
        loader.assert_called_once_with()

    def test_standalone_futu_portfolio_success_returns_zero(self) -> None:
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
                return_value=([], "", True),
            ),
        ):
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        loader.assert_called_once_with()

    def test_serve_mode_exits_when_api_server_start_fails(self) -> None:
        args = self._make_args(serve_only=True, host="127.0.0.1", port=8000)
        config = self._make_config(webui_enabled=False)

        with patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}, clear=False), \
             patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch("main.prepare_webui_frontend_assets", return_value=True), \
             patch("main.start_api_server", side_effect=RuntimeError("port busy")), \
             patch("main.start_bot_stream_clients") as start_bots, \
             patch("main.logger.error") as error_log:
            exit_code = main.main()

        self.assertEqual(exit_code, 1)
        start_bots.assert_not_called()
        error_log.assert_called_once()

    def test_webui_only_maps_to_serve_only_and_exits_when_api_server_start_fails(self) -> None:
        args = self._make_args(webui_only=True, host="127.0.0.1", port=8000)
        config = self._make_config(webui_enabled=False)

        with patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}, clear=False), \
             patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch("main.prepare_webui_frontend_assets", return_value=True), \
             patch("main.start_api_server", side_effect=RuntimeError("port busy")), \
             patch("main.start_bot_stream_clients") as start_bots, \
             patch("main.run_full_analysis") as run_full_analysis, \
             patch("main.logger.error") as error_log:
            exit_code = main.main()

        self.assertEqual(exit_code, 1)
        start_bots.assert_not_called()
        run_full_analysis.assert_not_called()
        error_log.assert_called_once()

    def test_serve_mode_continues_single_analysis_when_api_server_start_fails(self) -> None:
        args = self._make_args(serve=True, host="127.0.0.1", port=8000)
        config = self._make_config(webui_enabled=False, run_immediately=True)

        with patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}, clear=False), \
             patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch("main.prepare_webui_frontend_assets", return_value=True), \
             patch("main.start_api_server", side_effect=RuntimeError("port busy")), \
             patch("main.start_bot_stream_clients") as start_bots, \
             patch("main.run_full_analysis") as run_full_analysis, \
             patch("main._run_analysis_with_runtime_scheduler_lock") as run_with_lock, \
             patch("main.logger.error") as error_log:
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        start_bots.assert_not_called()
        run_with_lock.assert_called_once_with(config, args, None)
        run_full_analysis.assert_not_called()
        error_log.assert_called_once()

    def test_serve_mode_uses_shared_analysis_lock_for_immediate_run_full_analysis(self) -> None:
        args = self._make_args(
            serve=True,
            schedule=False,
            portfolio="futu",
            host="127.0.0.1",
            port=8000,
        )
        config = self._make_config(webui_enabled=False, run_immediately=True)

        with (
            patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}, clear=False),
            patch("main.parse_arguments", return_value=args),
            patch("main.get_config", return_value=config),
            patch("main.prepare_webui_frontend_assets", return_value=True),
            patch("main.start_api_server"),
            patch("main.start_bot_stream_clients") as start_bots,
            patch("main.time.sleep", side_effect=KeyboardInterrupt),
            patch("main.run_full_analysis") as run_full_analysis,
            patch("main._run_analysis_with_runtime_scheduler_lock") as run_with_lock,
        ):
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_with_lock.call_count, 1)
        run_with_lock.assert_called_once_with(config, args, None)
        run_full_analysis.assert_not_called()
        start_bots.assert_called_once_with(config)

    def test_serve_mode_keeps_running_after_futu_portfolio_load_failure(self) -> None:
        args = self._make_args(
            serve=True,
            schedule=False,
            portfolio="futu",
            host="127.0.0.1",
            port=8000,
        )
        config = self._make_config(webui_enabled=False, run_immediately=True)
        error = FutuPortfolioError("OpenD unavailable")

        with (
            patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}, clear=False),
            patch("main.parse_arguments", return_value=args),
            patch("main.get_config", return_value=config),
            patch("main.prepare_webui_frontend_assets", return_value=True),
            patch("main.start_api_server"),
            patch("main.start_bot_stream_clients") as start_bots,
            patch("main.time.sleep", side_effect=KeyboardInterrupt),
            patch(
                "main._run_analysis_with_runtime_scheduler_lock",
                side_effect=error,
            ) as run_with_lock,
            patch("main.logger.exception") as exception_log,
        ):
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        run_with_lock.assert_called_once_with(config, args, None)
        start_bots.assert_called_once_with(config)
        exception_log.assert_any_call(
            "Futu 持仓导入失败，Web/API 服务继续运行: %s",
            error,
        )

    def test_reload_runtime_config_preserves_process_env_overrides(self) -> None:
        self.env_path.write_text(
            "OPENAI_API_KEY=stale-file\nSCHEDULE_TIME=09:30\n",
            encoding="utf-8",
        )
        runtime_config = self._make_config(schedule_enabled=True, schedule_time="09:30")

        with patch.dict(
            os.environ,
            {
                "ENV_FILE": str(self.env_path),
                "OPENAI_API_KEY": "runtime-secret",
                "SCHEDULE_TIME": "18:00",
            },
            clear=False,
        ), patch.object(
            main,
            "_INITIAL_PROCESS_ENV",
            {"OPENAI_API_KEY": "runtime-secret"},
        ), patch.object(
            main,
            "_RUNTIME_ENV_FILE_KEYS",
            {"SCHEDULE_TIME"},
        ), patch(
            "main.get_config",
            return_value=runtime_config,
        ) as get_config_mock:
            reloaded_config = main._reload_runtime_config()
            self.assertEqual(os.environ["OPENAI_API_KEY"], "runtime-secret")
            self.assertEqual(os.environ["SCHEDULE_TIME"], "09:30")

        self.assertIs(reloaded_config, runtime_config)
        get_config_mock.assert_called_once_with()

    def test_reload_env_file_values_preserves_managed_env_vars_when_read_fails(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ENV_FILE": str(self.env_path),
                "OPENAI_API_KEY": "runtime-secret",
                "SCHEDULE_TIME": "09:30",
            },
            clear=False,
        ), patch.object(
            main,
            "_INITIAL_PROCESS_ENV",
            {},
        ), patch.object(
            main,
            "_RUNTIME_ENV_FILE_KEYS",
            {"OPENAI_API_KEY", "SCHEDULE_TIME"},
        ), patch(
            "main.dotenv_values",
            side_effect=OSError("boom"),
        ):
            main._reload_env_file_values_preserving_overrides()

            self.assertEqual(os.environ["OPENAI_API_KEY"], "runtime-secret")
            self.assertEqual(os.environ["SCHEDULE_TIME"], "09:30")
            self.assertEqual(
                main._RUNTIME_ENV_FILE_KEYS,
                {"OPENAI_API_KEY", "SCHEDULE_TIME"},
            )

    def test_run_full_analysis_reuses_cached_market_context_as_full_report(self) -> None:
        args = self._make_args()
        target_date = date(2026, 3, 26)
        config = self._make_config(
            trading_day_check_enabled=False,
            market_review_enabled=True,
            daily_market_context_enabled=True,
            single_stock_notify=False,
            merge_email_notification=True,
            analysis_delay=0,
            database_path=str(Path(self.temp_dir.name) / "stock_analysis.db"),
            report_type="simple",
        )
        pipeline = MagicMock()
        pipeline.run.return_value = []
        pipeline.notifier = MagicMock(
            is_available=MagicMock(return_value=True),
            generate_aggregate_report=MagicMock(return_value=""),
            send=MagicMock(return_value=True),
        )
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
                return_value=(
                    "大盘退潮，高风险，建议观望。",
                    "## 完整大盘复盘\n市场结构偏弱，建议保守。",
                ),
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
        run_with_lock.assert_not_called()
        run_market_review.assert_not_called()
        refresh.assert_called_once_with(config)
        pipeline.run.assert_called_once_with(
            stock_codes=[],
            dry_run=False,
            send_notification=True,
            merge_notification=True,
            current_time=unittest.mock.ANY,
        )
        notifier_message = pipeline.notifier.send.call_args.args[0]
        self.assertIn("## 完整大盘复盘", notifier_message)
        self.assertNotIn("大盘退潮，高风险，建议观望。", notifier_message)

    def test_run_full_analysis_import_failure_propagates(self) -> None:
        """P1: import failures in run_full_analysis must propagate, not be swallowed."""
        args = self._make_args()
        config = self._make_config()

        with patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch("src.infrastructure.observability.logging_config.setup_logging"), \
             patch.dict("sys.modules", {"src.application.analysis.pipeline": None}):
            exit_code = main.main()

        self.assertEqual(exit_code, 1)
