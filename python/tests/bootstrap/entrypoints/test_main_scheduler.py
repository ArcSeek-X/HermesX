"""Tests for main scheduler."""

from tests.bootstrap.entrypoints._main_schedule_mode_support import (
    MagicMock,
    Path,
    _MainScheduleModeTestCaseFixture,
    date,
    datetime,
    json,
    main,
    os,
    patch,
    timezone,
    unittest,
)


class MainScheduleModeTestCase(_MainScheduleModeTestCaseFixture, unittest.TestCase):
    def test_compute_trading_day_filter_supports_comma_list_regions(self) -> None:
        args = self._make_args()
        config = self._make_config(
            trading_day_check_enabled=True,
            market_review_enabled=True,
            market_review_region="jp,kr",
            database_path=str(Path(self.temp_dir.name) / "stock_analysis.db"),
        )

        stock_codes = ["cn-stock", "jp-stock", "kr-stock", "us-stock", "none-stock"]

        with patch(
            "src.domain.market.trading_calendar.get_market_for_stock",
            side_effect=lambda code: {"cn-stock": "cn", "jp-stock": "jp", "kr-stock": "kr", "us-stock": "us"}.get(code),
        ), patch("src.domain.market.trading_calendar.get_open_markets_today", return_value={"jp", "kr"}):
            filtered_codes, effective_region, should_skip_all = main._compute_trading_day_filter(
                config,
                args,
                stock_codes,
            )

        self.assertEqual(filtered_codes, ["jp-stock", "kr-stock", "none-stock"])
        self.assertEqual(effective_region, "jp,kr")
        self.assertFalse(should_skip_all)

    def test_schedule_mode_ignores_cli_stock_snapshot(self) -> None:
        args = self._make_args(schedule=True, stocks="600519,000001")
        config = self._make_config(schedule_enabled=False)
        scheduled_call = {}

        def fake_run_with_schedule(
            task,
            schedule_time,
            run_immediately,
            background_tasks=None,
            schedule_time_provider=None,
        ):
            scheduled_call["schedule_time"] = schedule_time
            scheduled_call["run_immediately"] = run_immediately
            scheduled_call["background_tasks"] = background_tasks or []
            scheduled_call["resolved_schedule_time"] = (
                schedule_time_provider() if schedule_time_provider is not None else None
            )
            task()

        with patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch("main._reload_runtime_config", return_value=config), \
             patch("main._build_schedule_time_provider", return_value=lambda: "18:00"), \
             patch("src.infrastructure.observability.logging_config.setup_logging"), \
             patch("main.run_full_analysis") as run_full_analysis, \
             patch("main.logger.warning") as warning_log, \
             patch("src.application.runtime.scheduler.run_with_schedule", side_effect=fake_run_with_schedule):
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            scheduled_call,
            {
                "schedule_time": "18:00",
                "run_immediately": True,
                "background_tasks": [],
                "resolved_schedule_time": "18:00",
            },
        )
        run_full_analysis.assert_called_once_with(config, args, None)
        warning_log.assert_any_call(
            "定时模式下检测到 --stocks 参数；计划执行将忽略启动时股票快照，并在每次运行前重新读取最新的 STOCK_LIST。"
        )

    def test_schedule_mode_reload_uses_latest_runtime_config(self) -> None:
        args = self._make_args(schedule=True)
        startup_config = self._make_config(schedule_enabled=True, schedule_time="18:00")
        runtime_config = self._make_config(schedule_enabled=True, schedule_time="09:30")
        scheduled_call = {}

        def fake_run_with_schedule(
            task,
            schedule_time,
            run_immediately,
            background_tasks=None,
            schedule_time_provider=None,
        ):
            scheduled_call["schedule_time"] = schedule_time
            scheduled_call["resolved_schedule_time"] = (
                schedule_time_provider() if schedule_time_provider is not None else None
            )
            task()

        with patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=startup_config), \
             patch("main._reload_runtime_config", return_value=runtime_config), \
             patch("main._build_schedule_time_provider", return_value=lambda: "09:30"), \
             patch("src.infrastructure.observability.logging_config.setup_logging"), \
             patch("main.run_full_analysis") as run_full_analysis, \
             patch("src.application.runtime.scheduler.run_with_schedule", side_effect=fake_run_with_schedule):
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            scheduled_call,
            {"schedule_time": "18:00", "resolved_schedule_time": "09:30"},
        )
        run_full_analysis.assert_called_once_with(runtime_config, args, None)

    def test_schedule_mode_registers_event_monitor_background_task(self) -> None:
        args = self._make_args(schedule=True)
        config = self._make_config(
            schedule_enabled=False,
            agent_event_monitor_enabled=True,
            agent_event_monitor_interval_minutes=7,
        )
        worker = MagicMock()
        worker.run_once.return_value = {"triggered": 2}
        scheduled_call = {}

        def fake_run_with_schedule(
            task,
            schedule_time,
            run_immediately,
            background_tasks=None,
            schedule_time_provider=None,
        ):
            scheduled_call["schedule_time"] = schedule_time
            scheduled_call["run_immediately"] = run_immediately
            scheduled_call["background_tasks"] = background_tasks or []
            scheduled_call["resolved_schedule_time"] = (
                schedule_time_provider() if schedule_time_provider is not None else None
            )

        with patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch("main._reload_runtime_config", return_value=config) as reload_config, \
             patch("main._build_schedule_time_provider", return_value=lambda: "18:00"), \
             patch("src.infrastructure.observability.logging_config.setup_logging"), \
             patch("main.run_full_analysis") as run_full_analysis, \
             patch("src.bootstrap.alert.build_alert_worker", return_value=worker) as worker_cls, \
             patch("src.application.runtime.scheduler.run_with_schedule", side_effect=fake_run_with_schedule):
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        worker_cls.assert_called_once()
        self.assertIs(worker_cls.call_args.kwargs["config_provider"], reload_config)
        run_full_analysis.assert_not_called()
        self.assertEqual(scheduled_call["schedule_time"], "18:00")
        self.assertEqual(scheduled_call["run_immediately"], True)
        self.assertEqual(scheduled_call["resolved_schedule_time"], "18:00")
        self.assertEqual(len(scheduled_call["background_tasks"]), 1)
        background_task = scheduled_call["background_tasks"][0]
        self.assertEqual(background_task["name"], "agent_event_monitor")
        self.assertEqual(background_task["interval_seconds"], 7 * 60)
        self.assertEqual(background_task["run_immediately"], True)

        with patch("main.logger.info") as info_log:
            background_task["task"]()

        worker.run_once.assert_called_once_with()
        info_log.assert_any_call("[EventMonitor] 本轮触发 %d 条提醒", 2)

    def test_schedule_mode_registers_event_monitor_worker_without_legacy_rules(self) -> None:
        args = self._make_args(schedule=True)
        config = self._make_config(
            schedule_enabled=False,
            agent_event_monitor_enabled=True,
            agent_event_alert_rules_json="",
        )
        worker = MagicMock()
        worker.run_once.return_value = {"triggered": 0}
        scheduled_call = {}

        def fake_run_with_schedule(
            task,
            schedule_time,
            run_immediately,
            background_tasks=None,
            schedule_time_provider=None,
        ):
            scheduled_call["background_tasks"] = background_tasks or []

        with patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch("main._reload_runtime_config", return_value=config), \
             patch("main._build_schedule_time_provider", return_value=lambda: "18:00"), \
             patch("src.infrastructure.observability.logging_config.setup_logging"), \
             patch("main.run_full_analysis") as run_full_analysis, \
             patch("src.bootstrap.alert.build_alert_worker", return_value=worker) as worker_cls, \
             patch("src.application.runtime.scheduler.run_with_schedule", side_effect=fake_run_with_schedule):
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        worker_cls.assert_called_once()
        run_full_analysis.assert_not_called()
        self.assertEqual(len(scheduled_call["background_tasks"]), 1)
        self.assertEqual(scheduled_call["background_tasks"][0]["name"], "agent_event_monitor")

    def test_serve_schedule_mode_continues_scheduler_when_api_server_start_fails(self) -> None:
        args = self._make_args(serve=True, schedule=True, host="127.0.0.1", port=8000)
        config = self._make_config(webui_enabled=False, schedule_enabled=False)
        scheduled_call = {}

        def fake_run_with_schedule(
            task,
            schedule_time,
            run_immediately,
            background_tasks=None,
            schedule_time_provider=None,
        ):
            scheduled_call["schedule_time"] = schedule_time
            scheduled_call["run_immediately"] = run_immediately
            scheduled_call["background_tasks"] = background_tasks or []
            task()

        with patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}, clear=False), \
             patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch("main._reload_runtime_config", return_value=config), \
             patch("main._build_schedule_time_provider", return_value=lambda: "18:00"), \
             patch("main.prepare_webui_frontend_assets", return_value=True), \
             patch("main.start_api_server", side_effect=RuntimeError("port busy")), \
             patch("main.start_bot_stream_clients") as start_bots, \
             patch("main.run_full_analysis") as run_full_analysis, \
             patch("src.application.runtime.scheduler.run_with_schedule", side_effect=fake_run_with_schedule), \
             patch("main.logger.error") as error_log:
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        start_bots.assert_not_called()
        run_full_analysis.assert_called_once_with(config, args, None)
        self.assertEqual(scheduled_call["schedule_time"], "18:00")
        self.assertEqual(scheduled_call["run_immediately"], True)
        self.assertEqual(scheduled_call["background_tasks"], [])
        error_log.assert_called_once()

    def test_serve_with_enabled_schedule_uses_api_runtime_scheduler(self) -> None:
        from src.application.runtime.runtime_scheduler import (
            CLI_SCHEDULER_OWNER_ENV,
            RUNTIME_SCHEDULER_ARGS_ENV,
            RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV,
        )

        args = self._make_args(
            serve=True,
            schedule=False,
            host="127.0.0.1",
            port=8000,
            no_notify=True,
            no_market_review=True,
            dry_run=True,
            force_run=True,
            single_notify=True,
            no_context_snapshot=True,
            workers=4,
        )
        config = self._make_config(webui_enabled=False, schedule_enabled=True)
        marker_seen_by_server = []
        run_immediately_seen_by_server = []
        runtime_args_seen_by_server = []

        def fake_start_api_server(host, port, config):
            marker_seen_by_server.append(os.getenv(CLI_SCHEDULER_OWNER_ENV))
            run_immediately_seen_by_server.append(os.getenv(RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV))
            runtime_args_seen_by_server.append(json.loads(os.getenv(RUNTIME_SCHEDULER_ARGS_ENV, "{}")))

        with patch.dict(
            os.environ,
            {"GITHUB_ACTIONS": "false", CLI_SCHEDULER_OWNER_ENV: "true"},
            clear=False,
        ), \
             patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch("main.prepare_webui_frontend_assets", return_value=True), \
             patch("main.start_api_server", side_effect=fake_start_api_server), \
             patch("main.start_bot_stream_clients") as start_bots, \
             patch("main.time.sleep", side_effect=KeyboardInterrupt), \
             patch("src.application.runtime.scheduler.run_with_schedule") as run_with_schedule:
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(marker_seen_by_server, [None])
        self.assertEqual(run_immediately_seen_by_server, ["true"])
        self.assertEqual(runtime_args_seen_by_server, [{
            "no_notify": True,
            "no_market_review": True,
            "dry_run": True,
            "force_run": True,
            "single_notify": True,
            "no_context_snapshot": True,
            "workers": 4,
        }])
        start_bots.assert_called_once_with(config)
        run_with_schedule.assert_not_called()

    def test_serve_schedule_flag_enables_api_runtime_scheduler(self) -> None:
        from src.application.runtime.runtime_scheduler import (
            CLI_SCHEDULER_OWNER_ENV,
            RUNTIME_SCHEDULER_ARGS_ENV,
            RUNTIME_SCHEDULER_FORCE_ENABLED_ENV,
            RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV,
        )

        args = self._make_args(
            serve=True,
            schedule=True,
            host="127.0.0.1",
            port=8000,
            no_notify=True,
            no_market_review=True,
            dry_run=True,
            force_run=True,
            single_notify=True,
            no_context_snapshot=True,
            workers=4,
        )
        config = self._make_config(webui_enabled=False, schedule_enabled=False)
        marker_seen_by_server = []
        force_enabled_seen_by_server = []
        run_immediately_seen_by_server = []
        runtime_args_seen_by_server = []

        def fake_start_api_server(host, port, config):
            marker_seen_by_server.append(os.getenv(CLI_SCHEDULER_OWNER_ENV))
            force_enabled_seen_by_server.append(os.getenv(RUNTIME_SCHEDULER_FORCE_ENABLED_ENV))
            run_immediately_seen_by_server.append(os.getenv(RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV))
            runtime_args_seen_by_server.append(json.loads(os.getenv(RUNTIME_SCHEDULER_ARGS_ENV, "{}")))

        with patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}, clear=False), \
             patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch("main.prepare_webui_frontend_assets", return_value=True), \
             patch("main.start_api_server", side_effect=fake_start_api_server), \
             patch("main.start_bot_stream_clients"), \
             patch("main.time.sleep", side_effect=KeyboardInterrupt), \
             patch("src.application.runtime.scheduler.run_with_schedule") as run_with_schedule:
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(marker_seen_by_server, [None])
        self.assertEqual(force_enabled_seen_by_server, ["true"])
        self.assertEqual(run_immediately_seen_by_server, ["true"])
        self.assertEqual(runtime_args_seen_by_server, [{
            "no_notify": True,
            "no_market_review": True,
            "dry_run": True,
            "force_run": True,
            "single_notify": True,
            "no_context_snapshot": True,
            "workers": 4,
        }])
        self.assertFalse(config.schedule_enabled)
        run_with_schedule.assert_not_called()

    def test_serve_schedule_flag_passes_no_run_immediately_to_runtime_scheduler(self) -> None:
        from src.application.runtime.runtime_scheduler import RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV

        args = self._make_args(
            serve=True,
            schedule=True,
            no_run_immediately=True,
            host="127.0.0.1",
            port=8000,
        )
        config = self._make_config(webui_enabled=False, schedule_enabled=False)
        run_immediately_seen_by_server = []

        def fake_start_api_server(host, port, config):
            run_immediately_seen_by_server.append(os.getenv(RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV))

        with patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}, clear=False), \
             patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch("main.prepare_webui_frontend_assets", return_value=True), \
             patch("main.start_api_server", side_effect=fake_start_api_server), \
             patch("main.start_bot_stream_clients"), \
             patch("main.time.sleep", side_effect=KeyboardInterrupt), \
             patch("src.application.runtime.scheduler.run_with_schedule") as run_with_schedule:
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_immediately_seen_by_server, ["false"])
        run_with_schedule.assert_not_called()

    def test_serve_only_suppresses_startup_scheduler_without_disabling_runtime_owner(self) -> None:
        from src.application.runtime.runtime_scheduler import (
            CLI_SCHEDULER_OWNER_ENV,
            RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV,
            RUNTIME_SCHEDULER_SUPPRESS_START_ENV,
        )

        args = self._make_args(serve_only=True, host="127.0.0.1", port=8000)
        config = self._make_config(webui_enabled=False, schedule_enabled=True)
        marker_seen_by_server = []
        suppress_seen_by_server = []
        run_immediately_seen_by_server = []

        def fake_start_api_server(host, port, config):
            marker_seen_by_server.append(os.getenv(CLI_SCHEDULER_OWNER_ENV))
            suppress_seen_by_server.append(os.getenv(RUNTIME_SCHEDULER_SUPPRESS_START_ENV))
            run_immediately_seen_by_server.append(os.getenv(RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV))

        with patch.dict(
            os.environ,
            {"GITHUB_ACTIONS": "false", CLI_SCHEDULER_OWNER_ENV: "true"},
            clear=False,
        ), \
             patch("main.parse_arguments", return_value=args), \
             patch("main.get_config", return_value=config), \
             patch("main.prepare_webui_frontend_assets", return_value=True), \
             patch("main.start_api_server", side_effect=fake_start_api_server), \
             patch("main.start_bot_stream_clients") as start_bots, \
             patch("main.time.sleep", side_effect=KeyboardInterrupt), \
             patch("src.application.runtime.scheduler.run_with_schedule") as run_with_schedule:
            exit_code = main.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(marker_seen_by_server, [None])
        self.assertEqual(suppress_seen_by_server, ["true"])
        self.assertEqual(run_immediately_seen_by_server, [None])
        start_bots.assert_called_once_with(config)
        run_with_schedule.assert_not_called()

    def test_schedule_time_provider_propagates_config_read_failures(self) -> None:
        with patch.object(
            main,
            "_INITIAL_PROCESS_ENV",
            {},
        ), patch(
            "src.config.env_file.ConfigManager.read_config_map",
            side_effect=RuntimeError("boom"),
        ):
            provider = main._build_schedule_time_provider("18:00")

            with self.assertRaisesRegex(RuntimeError, "boom"):
                provider()

    def test_schedule_time_provider_respects_process_env_precedence(self) -> None:
        with patch.dict(
            os.environ,
            {"SCHEDULE_TIME": "18:00"},
            clear=False,
        ), patch.object(
            main,
            "_INITIAL_PROCESS_ENV",
            {"SCHEDULE_TIME": "18:00"},
        ), patch(
            "src.config.env_file.ConfigManager.read_config_map",
            side_effect=AssertionError("should not read .env when process env override exists"),
        ):
            provider = main._build_schedule_time_provider("09:30")

            self.assertEqual(provider(), "18:00")

    def test_schedule_time_provider_falls_back_to_system_default_on_clear(self) -> None:
        """When SCHEDULE_TIME is cleared/removed from config, provider returns '18:00'."""
        with patch.dict(
            os.environ,
            {"SCHEDULE_TIME": "09:30"},
            clear=False,
        ), patch.object(
            main,
            "_INITIAL_PROCESS_ENV",
            {},
        ), patch(
            "src.config.env_file.ConfigManager.read_config_map",
            return_value={},
        ):
            provider = main._build_schedule_time_provider("09:30")
            self.assertEqual(provider(), "18:00")

    def test_schedule_time_provider_falls_back_to_system_default_on_empty(self) -> None:
        """When SCHEDULE_TIME is empty string in config, provider returns '18:00'."""
        with patch.dict(
            os.environ,
            {"SCHEDULE_TIME": "09:30"},
            clear=False,
        ), patch.object(
            main,
            "_INITIAL_PROCESS_ENV",
            {},
        ), patch(
            "src.config.env_file.ConfigManager.read_config_map",
            return_value={"SCHEDULE_TIME": "  "},
        ):
            provider = main._build_schedule_time_provider("09:30")
            self.assertEqual(provider(), "18:00")

    def test_resolve_daily_market_context_target_date_passes_jp_kr_to_trading_calendar(self) -> None:
        current_time = datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc)
        target_date = date(2026, 3, 25)

        with patch("src.domain.market.trading_calendar.get_effective_trading_date", return_value=target_date) as get_date:
            self.assertEqual(
                main._resolve_daily_market_context_target_date("jp", current_time),
                target_date,
            )
            self.assertEqual(
                main._resolve_daily_market_context_target_date("kr", current_time),
                target_date,
            )

        self.assertEqual(
            get_date.call_args_list,
            [
                unittest.mock.call("jp", current_time=current_time),
                unittest.mock.call("kr", current_time=current_time),
            ],
        )

    def test_config_enabled_schedule_marks_market_review_source_as_schedule(self) -> None:
        args = self._make_args(schedule=False)
        target_date = date(2026, 3, 26)
        config = self._make_config(
            schedule_enabled=True,
            trading_day_check_enabled=False,
            market_review_enabled=True,
            no_market_review=False,
            single_stock_notify=False,
            merge_email_notification=False,
            analysis_delay=0,
            database_path=str(Path(self.temp_dir.name) / "stock_analysis.db"),
        )
        pipeline = MagicMock()
        pipeline.run.return_value = []

        with patch.object(main, "_refresh_stock_index_cache_for_analysis"), \
             patch.object(main, "_compute_trading_day_filter", return_value=(["600519"], "cn", False)), \
             patch("main._resolve_daily_market_context_target_date", return_value=target_date), \
             patch("src.application.analysis.pipeline.StockAnalysisPipeline", return_value=pipeline), \
             patch("main._prime_daily_market_context", return_value=("", "")), \
             patch("main._run_market_review_with_shared_lock", return_value="market report") as run_with_lock, \
             patch("src.application.market.market_review.run_market_review") as run_market_review:
            main.run_full_analysis(config, args, ["600519"])

        pipeline.run.assert_called_once()
        run_with_lock.assert_called_once()
        call_args = run_with_lock.call_args
        self.assertIs(call_args.args[1], run_market_review)
        self.assertEqual(call_args.kwargs["trigger_source"], "schedule")
