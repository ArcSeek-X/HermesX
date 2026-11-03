"""Tests for analysis market review contract."""

from tests.integration.analysis._analysis_api_contract_support import (
    AnalysisTaskQueue,
    Config,
    Future,
    MagicMock,
    Path,
    SimpleNamespace,
    TaskStatus,
    _AnalysisApiContractTestCaseFixture,
    analysis_endpoint_module,
    create_app,
    get_analysis_status,
    get_task_list,
    patch,
    tempfile,
    trigger_market_review,
    unittest,
)


class AnalysisApiContractTestCase(_AnalysisApiContractTestCaseFixture, unittest.TestCase):
    def test_market_review_region_is_authoritative_across_active_task_lifecycle(self) -> None:
        if (
            trigger_market_review is None
            or get_analysis_status is None
            or get_task_list is None
            or analysis_endpoint_module is None
        ):
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        class CapturingExecutor:
            def __init__(self) -> None:
                self.calls = []

            def submit(self, fn, *args, **kwargs):
                self.calls.append((fn, args, kwargs))
                return Future()

        cases = (
            ("us", None, "us"),
            ("us", "kr,jp", "jp,kr"),
        )
        original_queue_instance = AnalysisTaskQueue._instance
        try:
            for configured_region, request_region, expected_region in cases:
                with self.subTest(
                    configured_region=configured_region,
                    request_region=request_region,
                ):
                    AnalysisTaskQueue._instance = None
                    queue = AnalysisTaskQueue(max_workers=1)
                    executor = CapturingExecutor()
                    queue._executor = executor
                    events = []
                    queue._broadcast_event = (
                        lambda event_type, data: events.append((event_type, data))
                    )
                    request = analysis_endpoint_module.MarketReviewRequest(
                        send_notification=False,
                        region=request_region,
                    )
                    config = Config(market_review_region=configured_region)
                    report = SimpleNamespace(
                        report=f"{expected_region} report",
                        market_review_payload={
                            "kind": "market_review",
                            "region": expected_region,
                            "sections": [],
                        },
                    )

                    with patch.object(
                        analysis_endpoint_module,
                        "_try_acquire_market_review_lock",
                        return_value=object(),
                    ), patch.object(
                        analysis_endpoint_module,
                        "_build_market_review_runtime",
                        return_value=(MagicMock(), MagicMock(), MagicMock()),
                    ), patch(
                        "src.application.market.market_review.run_market_review",
                        return_value=report,
                    ) as run_market_review, patch(
                        "api.v1.endpoints.analysis.get_task_queue",
                        return_value=queue,
                    ), patch.object(
                        analysis_endpoint_module,
                        "_release_market_review_lock",
                    ):
                        accepted = trigger_market_review(request=request, config=config)
                        pending = get_analysis_status(accepted.task_id)
                        task_list = get_task_list(status=None, limit=20)
                        queue.update_task_progress(
                            accepted.task_id,
                            progress=5,
                            message="queued",
                        )

                        worker, args, kwargs = executor.calls[0]
                        worker(*args, **kwargs)
                        completed = get_analysis_status(accepted.task_id)

                    self.assertEqual(accepted.region, expected_region)
                    self.assertEqual(pending.status, "pending")
                    self.assertEqual(pending.region, expected_region)
                    self.assertEqual(task_list.tasks[0].region, expected_region)
                    self.assertEqual(completed.status, "completed")
                    self.assertEqual(completed.region, expected_region)
                    self.assertEqual(
                        completed.market_review_payload["region"],
                        expected_region,
                    )
                    self.assertEqual(
                        run_market_review.call_args.kwargs["override_region"],
                        expected_region,
                    )
                    for event_type in (
                        "task_created",
                        "task_progress",
                        "task_started",
                        "task_completed",
                    ):
                        payload = next(
                            payload
                            for current_type, payload in events
                            if current_type == event_type
                        )
                        self.assertEqual(payload["region"], expected_region)
        finally:
            AnalysisTaskQueue._instance = original_queue_instance

    def test_trigger_market_review_accepts_background_task(self) -> None:
        if trigger_market_review is None or analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")
        task_queue = MagicMock()
        task_queue.submit_background_task.return_value = SimpleNamespace(task_id="market-task-1")
        request = analysis_endpoint_module.MarketReviewRequest(send_notification=False)
        config = SimpleNamespace(
            trading_day_check_enabled=False,
            report_language="zh",
            market_review_region="cn",
        )
        lock_token = object()

        with patch.object(
            analysis_endpoint_module,
            "_try_acquire_market_review_lock",
            return_value=lock_token,
        ), patch("api.v1.endpoints.analysis.get_task_queue", return_value=task_queue):
            response = trigger_market_review(
                request=request,
                config=config,
            )

        self.assertEqual(response.status, "accepted")
        self.assertFalse(response.send_notification)
        self.assertEqual(response.region, "cn")
        self.assertEqual(response.task_id, "market-task-1")
        task_queue.submit_background_task.assert_called_once()
        args, kwargs = task_queue.submit_background_task.call_args
        self.assertTrue(callable(args[0]))
        self.assertEqual(kwargs["stock_code"], "market_review")
        self.assertEqual(kwargs["stock_name"], "大盘复盘")
        self.assertEqual(kwargs["message"], "大盘复盘任务已提交")
        self.assertEqual(kwargs["region"], "cn")

    def test_trigger_market_review_accepts_request_level_report_language(self) -> None:
        if trigger_market_review is None or analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        request = analysis_endpoint_module.MarketReviewRequest(
            send_notification=True,
            report_language="en",
        )
        config = SimpleNamespace(trading_day_check_enabled=False, report_language="zh", market_review_region="cn")
        lock_token = object()
        task_payload: dict[str, object] = {}

        runtime_notifier = MagicMock()
        runtime_search = MagicMock()
        runtime_analyzer = MagicMock()

        task_queue = MagicMock()

        def _capture_background_task(task_fn, **kwargs):
            task_payload["background_task"] = task_fn
            return SimpleNamespace(task_id="market-task-1")

        task_queue.submit_background_task.side_effect = _capture_background_task

        with patch.object(
            analysis_endpoint_module,
            "_try_acquire_market_review_lock",
            return_value=lock_token,
        ), patch.object(
            analysis_endpoint_module,
            "_build_market_review_runtime",
            return_value=(runtime_notifier, runtime_analyzer, runtime_search),
        ), patch("src.application.market.market_review.run_market_review") as run_market_review, patch(
            "api.v1.endpoints.analysis.get_task_queue",
            return_value=task_queue,
        ), patch.object(
            analysis_endpoint_module,
            "_release_market_review_lock",
            return_value=None,
        ):
            trigger_market_review(request=request, config=config)
            self.assertIn("background_task", task_payload)
            task_payload["background_task"]()

        call_kwargs = run_market_review.call_args.kwargs
        self.assertEqual(call_kwargs["send_notification"], True)
        self.assertEqual(call_kwargs["override_region"], "cn")
        self.assertEqual(call_kwargs["trigger_source"], "api")
        runtime_config = call_kwargs.get("config")
        self.assertIsNotNone(runtime_config)
        self.assertEqual(getattr(runtime_config, "report_language", None), "en")
        self.assertIsNot(runtime_config, config)

    def test_trigger_market_review_accepts_camel_case_report_language_alias(self) -> None:
        if trigger_market_review is None or analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        request = analysis_endpoint_module.MarketReviewRequest.model_validate({
            "send_notification": True,
            "reportLanguage": "en",
        })
        config = SimpleNamespace(trading_day_check_enabled=False, report_language="zh", market_review_region="cn")
        task_payload: dict[str, object] = {}

        runtime_notifier = MagicMock()
        runtime_search = MagicMock()
        runtime_analyzer = MagicMock()

        task_queue = MagicMock()

        def _capture_background_task(task_fn, **kwargs):
            task_payload["background_task"] = task_fn
            return SimpleNamespace(task_id="market-task-1")

        task_queue.submit_background_task.side_effect = _capture_background_task

        with patch.object(
            analysis_endpoint_module,
            "_try_acquire_market_review_lock",
            return_value=object(),
        ), patch.object(
            analysis_endpoint_module,
            "_build_market_review_runtime",
            return_value=(runtime_notifier, runtime_analyzer, runtime_search),
        ), patch("src.application.market.market_review.run_market_review") as run_market_review, patch(
            "api.v1.endpoints.analysis.get_task_queue",
            return_value=task_queue,
        ), patch.object(
            analysis_endpoint_module,
            "_release_market_review_lock",
            return_value=None,
        ):
            response = trigger_market_review(request=request, config=config)
            self.assertEqual(response.status, "accepted")
            self.assertIn("background_task", task_payload)
            task_payload["background_task"]()

        call_kwargs = run_market_review.call_args.kwargs
        runtime_config = call_kwargs.get("config")
        self.assertEqual(getattr(runtime_config, "report_language", None), "en")
        self.assertEqual(call_kwargs["trigger_source"], "api")

    def test_trigger_market_review_passes_canonical_request_region_without_mutating_config(self) -> None:
        if trigger_market_review is None or analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        request = analysis_endpoint_module.MarketReviewRequest.model_validate({
            "send_notification": False,
            "region": " KR, jp, KR ",
        })
        config = SimpleNamespace(report_language="zh", market_review_region="cn")
        task_payload: dict[str, object] = {}
        task_queue = MagicMock()

        def _capture_background_task(task_fn, **kwargs):
            task_payload["background_task"] = task_fn
            return SimpleNamespace(task_id="market-task-region")

        task_queue.submit_background_task.side_effect = _capture_background_task

        with patch.object(
            analysis_endpoint_module,
            "_try_acquire_market_review_lock",
            return_value=object(),
        ), patch.object(
            analysis_endpoint_module,
            "_build_market_review_runtime",
            return_value=(MagicMock(), MagicMock(), MagicMock()),
        ), patch(
            "src.application.market.market_review.run_market_review",
            return_value="report",
        ) as run_market_review, patch(
            "api.v1.endpoints.analysis.get_task_queue",
            return_value=task_queue,
        ), patch.object(
            analysis_endpoint_module,
            "_release_market_review_lock",
            return_value=None,
        ):
            response = trigger_market_review(request=request, config=config)
            task_payload["background_task"]()

        self.assertEqual(response.task_id, "market-task-region")
        self.assertEqual(response.region, "jp,kr")
        self.assertEqual(task_queue.submit_background_task.call_args.kwargs["region"], "jp,kr")
        self.assertEqual(run_market_review.call_args.kwargs["override_region"], "jp,kr")
        self.assertEqual(config.market_review_region, "cn")

    def test_market_review_background_uses_runtime_region_when_request_omits_override(self) -> None:
        if analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        runtime_config = SimpleNamespace(market_review_region="us")
        with patch.object(
            analysis_endpoint_module,
            "_build_market_review_runtime",
            return_value=(MagicMock(), MagicMock(), MagicMock()),
        ), patch(
            "src.application.market.market_review.run_market_review",
            return_value="report",
        ) as run_market_review, patch.object(
            analysis_endpoint_module,
            "_release_market_review_lock",
        ):
            analysis_endpoint_module._run_market_review_background(
                send_notification=False,
                effective_region="us",
                config=runtime_config,
            )

        call_kwargs = run_market_review.call_args.kwargs
        self.assertIs(call_kwargs["config"], runtime_config)
        self.assertEqual(call_kwargs["override_region"], "us")
        self.assertEqual(call_kwargs["config"].market_review_region, "us")

    def test_trigger_market_review_rejects_duplicate_submission(self) -> None:
        if trigger_market_review is None or analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        task_queue = MagicMock()
        request = analysis_endpoint_module.MarketReviewRequest(send_notification=True)
        config = SimpleNamespace(
            trading_day_check_enabled=False,
            report_language="zh",
            market_review_region="cn",
        )

        with patch.object(
            analysis_endpoint_module,
            "_try_acquire_market_review_lock",
            return_value=None,
        ), patch("api.v1.endpoints.analysis.get_task_queue", return_value=task_queue):
            with self.assertRaises(Exception) as ctx:
                trigger_market_review(
                    request=request,
                    config=config,
                )

        self.assertEqual(getattr(ctx.exception, "status_code", None), 409)
        task_queue.submit_background_task.assert_not_called()

    def test_trigger_market_review_rejects_when_shared_lock_is_held(self) -> None:
        if trigger_market_review is None or analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        from src.application.market.market_review_lock import (
            release_market_review_lock,
            try_acquire_market_review_lock,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            config = SimpleNamespace(
                trading_day_check_enabled=False,
                database_path=str(Path(temp_dir) / "stock_analysis.db"),
                report_language="zh",
                market_review_region="cn",
            )
            lock_token = try_acquire_market_review_lock(config)
            self.assertIsNotNone(lock_token)

            task_queue = MagicMock()
            try:
                with patch("api.v1.endpoints.analysis.get_task_queue", return_value=task_queue):
                    with self.assertRaises(Exception) as ctx:
                        trigger_market_review(
                            request=analysis_endpoint_module.MarketReviewRequest(
                                send_notification=True
                            ),
                            config=config,
                        )
            finally:
                release_market_review_lock(lock_token)

        self.assertEqual(getattr(ctx.exception, "status_code", None), 409)
        task_queue.submit_background_task.assert_not_called()

    def test_trigger_market_review_submits_even_when_configured_markets_closed(self) -> None:
        if trigger_market_review is None or analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        task_queue = MagicMock()
        task_queue.submit_background_task.return_value = SimpleNamespace(task_id="market-task-manual")
        request = analysis_endpoint_module.MarketReviewRequest(send_notification=True)
        config = SimpleNamespace(trading_day_check_enabled=True, market_review_region="cn")
        lock_token = object()

        with patch(
            "src.domain.market.trading_calendar.get_open_markets_today",
            return_value=set(),
        ) as get_open_markets_today, patch(
            "src.domain.market.trading_calendar.compute_effective_region",
            return_value="",
        ) as compute_effective_region, patch.object(
            analysis_endpoint_module,
            "_try_acquire_market_review_lock",
            return_value=lock_token,
        ) as acquire, patch("api.v1.endpoints.analysis.get_task_queue", return_value=task_queue):
            response = trigger_market_review(
                request=request,
                config=config,
            )

        self.assertEqual(response.status, "accepted")
        self.assertEqual(response.task_id, "market-task-manual")
        get_open_markets_today.assert_not_called()
        compute_effective_region.assert_not_called()
        acquire.assert_called_once_with(config)
        task_queue.submit_background_task.assert_called_once()

    def test_run_market_review_background_uses_configured_pipeline(self) -> None:
        if analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        config = SimpleNamespace(
            has_search_capability_enabled=lambda: True,
            bocha_api_keys=["bocha"],
            tavily_api_keys=["tavily"],
            anspire_api_keys=["anspire"],
            brave_api_keys=["brave"],
            serpapi_keys=["serpapi"],
            minimax_api_keys=["minimax"],
            searxng_base_urls=["http://searxng.local"],
            searxng_public_instances_enabled=False,
            news_max_age_days=5,
            news_strategy_profile="balanced",
            gemini_api_key="gemini-key",
            openai_api_key=None,
        )

        runtime_notifier = MagicMock()
        runtime_search = MagicMock()
        runtime_analyzer = MagicMock()
        with patch.object(
            analysis_endpoint_module,
            "_build_market_review_runtime",
            return_value=(runtime_notifier, runtime_analyzer, runtime_search),
        ), patch("src.application.market.market_review.run_market_review") as run_market_review:
            analysis_endpoint_module._run_market_review_background(
                send_notification=False,
                effective_region="cn,us",
                lock_token=None,
                config=config,
            )

        run_market_review.assert_called_once_with(
            notifier=runtime_notifier,
            analyzer=runtime_analyzer,
            search_service=runtime_search,
            config=config,
            send_notification=False,
            override_region="cn,us",
            return_structured=True,
            trigger_source="api",
        )

    def test_market_review_runtime_initializes_analyzer_for_litellm_provider(self) -> None:
        if analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        config = SimpleNamespace(
            has_search_capability_enabled=lambda: False,
            gemini_api_key=None,
            openai_api_key=None,
            litellm_model="anthropic/claude-sonnet-4-6",
            llm_model_list=[],
            anthropic_api_keys=["sk-ant-test-value"],
        )

        with patch("src.application.notification.notification.NotificationService"), \
             patch("src.application.analysis.analyzer.GeminiAnalyzer") as analyzer_cls:
            analyzer_cls.return_value.is_available.return_value = True

            _, analyzer, search_service = analysis_endpoint_module._build_market_review_runtime(config)

        analyzer_cls.assert_called_once_with(config=config)
        self.assertIs(analyzer, analyzer_cls.return_value)
        self.assertIsNone(search_service)

    def test_run_market_review_background_returns_non_empty_result_payload(self) -> None:
        if analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        runtime_notifier = MagicMock()
        runtime_search = MagicMock()
        runtime_analyzer = MagicMock()
        market_review_config = SimpleNamespace()
        with patch.object(
            analysis_endpoint_module,
            "_build_market_review_runtime",
            return_value=(runtime_notifier, runtime_analyzer, runtime_search),
        ), patch("src.application.market.market_review.run_market_review", return_value="report") as run_market_review:
            result = analysis_endpoint_module._run_market_review_background(
                send_notification=False,
                effective_region="cn",
                lock_token=None,
                config=market_review_config,
            )

        self.assertEqual(result, {"result": "report", "region": "cn"})
        run_market_review.assert_called_once_with(
            notifier=runtime_notifier,
            analyzer=runtime_analyzer,
            search_service=runtime_search,
            config=market_review_config,
            send_notification=False,
            override_region="cn",
            return_structured=True,
            trigger_source="api",
        )

    def test_run_market_review_uses_request_scoped_config_language(self) -> None:
        from src.application.market.market_review import run_market_review

        global_config = SimpleNamespace(report_language="zh", market_review_region="cn")
        scoped_config = SimpleNamespace(report_language="en", market_review_region="cn")
        notifier = MagicMock()
        notifier.save_report_to_file.return_value = "market_review.md"
        notifier.is_available.return_value = False
        review_result = SimpleNamespace(
            report="Market review body",
            market_light_snapshot={},
            structured_payload={
                "kind": "market_review",
                "language": "en",
                "sections": [{"key": "summary", "title": "Summary", "markdown": "Market review body"}],
            },
        )
        market_analyzer = MagicMock()
        market_analyzer.run_daily_review_with_snapshot.return_value = review_result

        with patch("src.application.market.market_review.get_config", return_value=global_config) as get_config_mock, \
             patch("src.application.market.market_review.MarketAnalyzer", return_value=market_analyzer) as market_analyzer_cls, \
             patch("src.application.market.market_review._persist_market_review_history") as persist:
            result = run_market_review(
                notifier=notifier,
                search_service=MagicMock(),
                send_notification=False,
                return_structured=True,
                config=scoped_config,
            )

        get_config_mock.assert_not_called()
        market_analyzer_cls.assert_called_once()
        self.assertIs(market_analyzer_cls.call_args.kwargs["config"], scoped_config)
        self.assertEqual(result.market_review_payload["language"], "en")
        self.assertEqual(persist.call_args.kwargs["config"].report_language, "en")

    def test_get_analysis_status_returns_market_review_report_from_queue(self) -> None:
        if get_analysis_status is None or analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        queue = MagicMock()
        queue.get_task.return_value = SimpleNamespace(
            task_id="market-task-1",
            region="cn,us",
            stock_code="market_review",
            stock_name="大盘复盘",
            status=analysis_endpoint_module.TaskStatusEnum.COMPLETED,
            progress=100,
            result={
                "result": "市场复盘报告示例文本",
                "market_review_payload": {
                    "kind": "market_review",
                    "region": "cn,us",
                    "sections": [],
                },
            },
            error=None,
            original_query=None,
            selection_source=None,
            analysis_phase="auto",
        )

        with patch("api.v1.endpoints.analysis.get_task_queue", return_value=queue):
            status = get_analysis_status("market-task-1")

        self.assertEqual(status.status, "completed")
        self.assertEqual(status.market_review_report, "市场复盘报告示例文本")
        self.assertEqual(status.market_review_payload["kind"], "market_review")
        self.assertEqual(status.market_review_payload["region"], "cn,us")
        self.assertEqual(status.region, "cn,us")
        self.assertIsNone(status.result)

    def test_run_market_review_background_raises_when_report_is_empty(self) -> None:
        if analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        runtime_notifier = MagicMock()
        runtime_search = MagicMock()
        runtime_analyzer = MagicMock()
        with patch.object(
            analysis_endpoint_module,
            "_build_market_review_runtime",
            return_value=(runtime_notifier, runtime_analyzer, runtime_search),
        ), patch("src.application.market.market_review.run_market_review", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "大盘复盘未返回可持久化报告"):
                analysis_endpoint_module._run_market_review_background(
                    send_notification=False,
                    effective_region="cn",
                    lock_token=None,
                    config=SimpleNamespace(),
                )

    def test_run_market_review_background_releases_lock_on_runtime_build_failure(self) -> None:
        if analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        lock_token = object()
        with patch.object(
            analysis_endpoint_module,
            "_build_market_review_runtime",
            side_effect=RuntimeError("runtime init failed"),
        ), patch.object(
            analysis_endpoint_module,
            "_release_market_review_lock",
        ) as release_market_review_lock:
            with self.assertRaises(RuntimeError):
                analysis_endpoint_module._run_market_review_background(
                    send_notification=False,
                    effective_region="cn",
                    lock_token=lock_token,
                    config=SimpleNamespace(),
                )

        release_market_review_lock.assert_called_once_with(lock_token)

    def test_run_market_review_background_runtime_build_failure_marks_task_failed(self) -> None:
        if analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        class _SyncExecutor:
            def submit(self, fn, *args, **kwargs):
                future = Future()
                try:
                    future.set_result(fn(*args, **kwargs))
                except Exception as exc:  # pragma: no cover - exercised via assert below
                    future.set_exception(exc)
                return future

        queue = AnalysisTaskQueue(max_workers=1)
        queue._executor = _SyncExecutor()
        with patch.object(
            analysis_endpoint_module,
            "_build_market_review_runtime",
            side_effect=RuntimeError("runtime init failed"),
        ), patch.object(analysis_endpoint_module, "_release_market_review_lock") as release_market_review_lock:
            task = queue.submit_background_task(
                lambda: analysis_endpoint_module._run_market_review_background(
                    send_notification=False,
                    effective_region="cn",
                    lock_token=object(),
                    config=SimpleNamespace(),
                ),
                stock_code="market_review",
                stock_name="大盘复盘",
                message="大盘复盘任务已提交",
            )

        task_info = queue.get_task(task.task_id)
        self.assertIsNotNone(task_info)
        self.assertEqual(task_info.status, TaskStatus.FAILED)
        self.assertEqual(task_info.error, "runtime init failed")
        self.assertEqual(task_info.message, "任务失败: runtime init failed")
        release_market_review_lock.assert_called_once()

    def test_get_analysis_status_returns_market_review_report_from_db(self) -> None:
        if get_analysis_status is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        mock_queue = MagicMock()
        mock_queue.get_task.return_value = None
        history_service, _ = self._history_service(
            record=SimpleNamespace(
                id=10,
                code="MARKET",
                name="大盘复盘",
                report_type="market_review",
                raw_result={"raw_response": "# 🎯 大盘复盘\n\n复盘正文"},
                context_snapshot={
                    "market_review_region": "jp,kr",
                    "market_review_payload": {
                        "kind": "market_review",
                        "region": "jp,kr",
                        "sections": [],
                    },
                },
                news_content="复盘正文",
                created_at=None,
            )
        )

        with patch("api.v1.endpoints.analysis.get_task_queue", return_value=mock_queue):
            result = get_analysis_status("market-task-1", history_service=history_service)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.market_review_report, "# 🎯 大盘复盘\n\n复盘正文")
        self.assertEqual(result.region, "jp,kr")
        self.assertEqual(result.market_review_payload["region"], "jp,kr")
        self.assertIsNone(result.result)

    def test_market_review_endpoint_accepts_omitted_body(self) -> None:
        if create_app is None or analysis_endpoint_module is None:
            self.skipTest("fastapi is not installed in this test environment")

        config = SimpleNamespace(trading_day_check_enabled=True, market_review_region="cn")

        with tempfile.TemporaryDirectory() as temp_dir:
            app = create_app(static_dir=Path(temp_dir))
            request_body = app.openapi()["paths"]["/api/v1/analysis/market-review"]["post"][
                "requestBody"
            ]

        self.assertNotIn("required", request_body)

        task_queue = MagicMock()
        task_queue.submit_background_task.return_value = SimpleNamespace(task_id="market-task-omitted")

        with patch.object(
            analysis_endpoint_module,
            "_try_acquire_market_review_lock",
            return_value=object(),
        ), patch("api.v1.endpoints.analysis.get_task_queue", return_value=task_queue):
            response = trigger_market_review(
                request=None,
                config=config,
            )

        self.assertTrue(response.send_notification)
        self.assertEqual(response.task_id, "market-task-omitted")
        task_queue.submit_background_task.assert_called_once()
