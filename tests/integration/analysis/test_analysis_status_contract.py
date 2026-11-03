"""Tests for analysis status contract."""

from tests.integration.analysis._analysis_api_contract_support import (
    AnalysisService,
    MagicMock,
    QueueTaskInfo,
    SimpleNamespace,
    TaskStatus,
    _AnalysisApiContractTestCaseFixture,
    _analysis_context_pack_overview,
    _market_phase_summary,
    _market_structure_context,
    analysis_endpoint_module,
    datetime,
    get_analysis_status,
    get_task_list,
    json,
    patch,
    unittest,
)


class AnalysisApiContractTestCase(_AnalysisApiContractTestCaseFixture, unittest.TestCase):
    def test_get_analysis_status_accepts_cancel_states_from_queue(self) -> None:
        if get_analysis_status is None or analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        for task_status in (
            analysis_endpoint_module.TaskStatusEnum.CANCEL_REQUESTED,
            analysis_endpoint_module.TaskStatusEnum.CANCELLED,
        ):
            with self.subTest(task_status=task_status.value):
                queue = MagicMock()
                queue.get_task.return_value = SimpleNamespace(
                    task_id=f"task-{task_status.value}",
                    region=None,
                    trace_id=f"trace-{task_status.value}",
                    stock_code="600519",
                    stock_name="贵州茅台",
                    status=task_status,
                    progress=42,
                    result=None,
                    error=None,
                    original_query=None,
                    selection_source=None,
                    analysis_phase="auto",
                    skills=[],
                )

                with patch("api.v1.endpoints.analysis.get_task_queue", return_value=queue):
                    status = get_analysis_status(f"task-{task_status.value}")

                self.assertEqual(status.status, task_status.value)
                self.assertEqual(status.progress, 42)
                self.assertIsNone(status.result)

    def test_get_analysis_status_normalizes_completed_queue_result_contract(self) -> None:
        if get_analysis_status is None or analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        created_at = datetime(2026, 5, 21, 17, 40, 0)
        queue = MagicMock()
        queue.get_task.return_value = SimpleNamespace(
            task_id="task-queue-1",
            region=None,
            stock_code="600519",
            stock_name="贵州茅台",
            status=analysis_endpoint_module.TaskStatusEnum.COMPLETED,
            progress=100,
            result={
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "report": {
                    "meta": {"query_id": "task-queue-1", "stock_code": "600519"},
                    "summary": {"analysis_summary": "summary", "operation_advice": "不建议买入"},
                },
            },
            error=None,
            original_query=None,
            selection_source=None,
            analysis_phase="auto",
            created_at=created_at,
            completed_at=datetime(2026, 5, 21, 17, 45, 0),
        )

        with patch("api.v1.endpoints.analysis.get_task_queue", return_value=queue):
            status = get_analysis_status("task-queue-1")

        self.assertEqual(status.status, "completed")
        self.assertIsNotNone(status.result)
        self.assertEqual(status.result.query_id, "task-queue-1")
        self.assertEqual(status.result.stock_code, "600519")
        self.assertEqual(status.result.stock_name, "贵州茅台")
        self.assertEqual(status.result.created_at, created_at.isoformat())
        self.assertEqual(
            status.result.report["summary"]["analysis_summary"],
            "summary",
        )
        self.assertEqual(status.result.report["summary"]["operation_advice"], "不建议买入")
        self.assertEqual(status.result.report["summary"]["action"], "avoid")
        self.assertEqual(status.result.report["summary"]["action_label"], "回避")

    def test_get_analysis_status_prefers_raw_result_action_over_summary_action(self) -> None:
        if get_analysis_status is None or analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        created_at = datetime(2026, 5, 21, 17, 40, 0)
        queue = MagicMock()
        queue.get_task.return_value = SimpleNamespace(
            task_id="task-queue-action-conflict",
            region=None,
            stock_code="600519",
            stock_name="贵州茅台",
            status=analysis_endpoint_module.TaskStatusEnum.COMPLETED,
            progress=100,
            result={
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "report": {
                    "meta": {
                        "query_id": "task-queue-action-conflict",
                        "stock_code": "600519",
                        "report_type": "detailed",
                        "report_language": "zh",
                    },
                    "summary": {
                        "analysis_summary": "summary",
                        "operation_advice": "持有观察",
                        "action": "buy",
                    },
                    "details": {
                        "raw_result": {
                            "operation_advice": "持有观察",
                            "action": "watch",
                            "report_language": "zh",
                        },
                    },
                },
            },
            error=None,
            original_query=None,
            selection_source=None,
            analysis_phase="auto",
            created_at=created_at,
            completed_at=datetime(2026, 5, 21, 17, 45, 0),
        )

        with patch("api.v1.endpoints.analysis.get_task_queue", return_value=queue):
            status = get_analysis_status("task-queue-action-conflict")

        self.assertEqual(status.status, "completed")
        self.assertIsNotNone(status.result)
        self.assertEqual(status.result.report["summary"]["action"], "watch")
        self.assertEqual(status.result.report["summary"]["action_label"], "观望")

    def test_get_analysis_status_preserves_zero_sentiment_score_when_aligning_action(self) -> None:
        if get_analysis_status is None or analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        created_at = datetime(2026, 5, 21, 17, 40, 0)
        queue = MagicMock()
        queue.get_task.return_value = SimpleNamespace(
            task_id="task-queue-zero-score",
            region=None,
            stock_code="600519",
            stock_name="贵州茅台",
            status=analysis_endpoint_module.TaskStatusEnum.COMPLETED,
            progress=100,
            result={
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "report": {
                    "meta": {
                        "query_id": "task-queue-zero-score",
                        "stock_code": "600519",
                        "report_type": "detailed",
                        "report_language": "zh",
                    },
                    "summary": {
                        "analysis_summary": "趋势显著恶化",
                        "operation_advice": "持有",
                        "sentiment_score": 0,
                    },
                    "details": {
                        "raw_result": {
                            "operation_advice": "持有",
                            "report_language": "zh",
                        },
                    },
                },
            },
            error=None,
            original_query=None,
            selection_source=None,
            analysis_phase="auto",
            created_at=created_at,
            completed_at=datetime(2026, 5, 21, 17, 45, 0),
        )

        with patch("api.v1.endpoints.analysis.get_task_queue", return_value=queue):
            status = get_analysis_status("task-queue-zero-score")

        self.assertEqual(status.status, "completed")
        self.assertIsNotNone(status.result)
        self.assertEqual(status.result.report["summary"]["sentiment_score"], 0)
        self.assertEqual(status.result.report["summary"]["action"], "sell")
        self.assertEqual(status.result.report["summary"]["action_label"], "卖出")

    def test_get_analysis_status_preserves_zero_sentiment_score_when_enriching_report(self) -> None:
        if get_analysis_status is None or analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        created_at = datetime(2026, 5, 21, 17, 40, 0)
        queue = MagicMock()
        queue.get_task.return_value = SimpleNamespace(
            task_id="task-queue-zero-score-enriched",
            region=None,
            stock_code="600519",
            stock_name="贵州茅台",
            status=analysis_endpoint_module.TaskStatusEnum.COMPLETED,
            progress=100,
            result={
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "report": {
                    "meta": {
                        "query_id": "task-queue-zero-score-enriched",
                        "stock_code": "600519",
                        "report_type": "detailed",
                        "report_language": "zh",
                    },
                    "summary": {
                        "analysis_summary": "趋势显著恶化",
                        "operation_advice": "持有",
                        "sentiment_score": 0,
                    },
                    "details": {
                        "raw_result": {
                            "operation_advice": "持有",
                            "report_language": "zh",
                        },
                    },
                },
            },
            error=None,
            original_query=None,
            selection_source=None,
            analysis_phase="auto",
            created_at=created_at,
            completed_at=datetime(2026, 5, 21, 17, 45, 0),
        )

        with patch("api.v1.endpoints.analysis.get_task_queue", return_value=queue), \
             patch(
                 "api.v1.endpoints.analysis._load_sync_fundamental_sources",
                 return_value=({}, None, None),
             ):
            status = get_analysis_status("task-queue-zero-score-enriched")

        self.assertEqual(status.status, "completed")
        self.assertIsNotNone(status.result)
        self.assertEqual(status.result.report["summary"]["sentiment_score"], 0)
        self.assertEqual(status.result.report["summary"]["action"], "sell")
        self.assertEqual(status.result.report["summary"]["action_label"], "卖出")

    def test_get_analysis_status_enriches_in_memory_market_structure_from_raw_result(self) -> None:
        if get_analysis_status is None or analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        market_structure = _market_structure_context()
        created_at = datetime(2026, 5, 21, 17, 40, 0)
        queue = MagicMock()
        queue.get_task.return_value = SimpleNamespace(
            task_id="task-queue-market-structure-raw",
            region=None,
            stock_code="300024",
            stock_name="机器人",
            status=analysis_endpoint_module.TaskStatusEnum.COMPLETED,
            progress=100,
            result={
                "stock_code": "300024",
                "stock_name": "机器人",
                "report": {
                    "meta": {
                        "query_id": "task-queue-market-structure-raw",
                        "stock_code": "300024",
                        "report_type": "detailed",
                        "report_language": "zh",
                    },
                    "summary": {"analysis_summary": "summary"},
                    "details": {"news_summary": "news"},
                },
            },
            error=None,
            original_query=None,
            selection_source=None,
            analysis_phase="auto",
            created_at=created_at,
            completed_at=datetime(2026, 5, 21, 17, 45, 0),
        )

        history_service, _ = self._history_service()

        with patch("api.v1.endpoints.analysis.get_task_queue", return_value=queue), \
             patch(
                 "api.v1.endpoints.analysis._load_sync_fundamental_sources",
                 return_value=(
                     None,
                     None,
                     {
                         "model_used": "test-model",
                         "report_language": "zh",
                         "market_structure_context": market_structure,
                     },
                 ),
             ) as load_sources:
            status = get_analysis_status(
                "task-queue-market-structure-raw",
                history_service=history_service,
            )

        self.assertEqual(status.status, "completed")
        self.assertIsNotNone(status.result)
        self.assertEqual(
            status.result.report["details"]["market_structure"]["market_theme_context"]["active_themes"][0]["name"],
            "机器人概念",
        )
        self.assertEqual(
            status.result.report["details"]["raw_result"]["market_structure_context"]["market_theme_context"]["active_themes"][0]["name"],
            "机器人概念",
        )
        self.assertNotIn(
            "raw_result",
            status.result.report["details"]["raw_result"],
        )
        load_sources.assert_called_once_with(
            query_id="task-queue-market-structure-raw",
            stock_code="300024",
            history_service=history_service,
        )

    def test_get_analysis_status_enriches_in_memory_market_structure_without_history_snapshot(self) -> None:
        if get_analysis_status is None or analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        market_structure = _market_structure_context()
        service = AnalysisService()
        task_result = service._build_analysis_response(
            SimpleNamespace(
                code="300024",
                name="机器人",
                current_price=999.9,
                change_pct=1.1,
                model_used="test-model",
                analysis_summary="summary",
                operation_advice="持有",
                trend_prediction="震荡",
                sentiment_score=80,
                news_summary="news",
                technical_analysis="tech",
                fundamental_analysis="fundamental",
                risk_warning="risk",
                market_structure_context=market_structure,
                to_dict=lambda: {
                    "analysis_summary": "summary",
                    "operation_advice": "持有",
                    "trend_prediction": "震荡",
                    "sentiment_score": 80,
                    "report_language": "zh",
                    "news_summary": "news",
                    "technical_analysis": "tech",
                    "fundamental_analysis": "fundamental",
                    "risk_warning": "risk",
                    "market_structure_context": market_structure,
                },
            ),
            "task-in-memory-no-history",
            report_type="detailed",
        )
        created_at = datetime(2026, 5, 21, 17, 40, 0)
        queue = MagicMock()
        queue.get_task.return_value = SimpleNamespace(
            task_id="task-in-memory-no-history",
            region=None,
            stock_code="300024",
            stock_name="机器人",
            status=analysis_endpoint_module.TaskStatusEnum.COMPLETED,
            progress=100,
            result=task_result,
            error=None,
            original_query=None,
            selection_source=None,
            analysis_phase="auto",
            created_at=created_at,
            completed_at=datetime(2026, 5, 21, 17, 45, 0),
        )

        with patch("api.v1.endpoints.analysis.get_task_queue", return_value=queue), \
             patch(
                 "api.v1.endpoints.analysis._load_sync_fundamental_sources",
                 return_value=(None, None, None),
             ):
            status = get_analysis_status("task-in-memory-no-history")

        self.assertEqual(status.status, "completed")
        self.assertIsNotNone(status.result)
        self.assertEqual(
            status.result.report["details"]["market_structure"]["market_theme_context"]["active_themes"][0]["name"],
            "机器人概念",
        )

    def test_get_analysis_status_preserves_queue_report_created_at_when_enriching(self) -> None:
        if get_analysis_status is None or analysis_endpoint_module is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        created_at = datetime(2026, 5, 21, 17, 40, 0)
        queue = MagicMock()
        queue.get_task.return_value = SimpleNamespace(
            task_id="task-queue-2",
            region=None,
            stock_code="600519",
            stock_name="贵州茅台",
            status=analysis_endpoint_module.TaskStatusEnum.COMPLETED,
            progress=100,
            result={
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "report": {
                    "meta": {"query_id": "task-queue-2", "stock_code": "600519"},
                    "summary": {"analysis_summary": "summary"},
                },
            },
            error=None,
            original_query=None,
            selection_source=None,
            analysis_phase="auto",
            created_at=created_at,
            completed_at=datetime(2026, 5, 21, 17, 45, 0),
        )

        with patch("api.v1.endpoints.analysis.get_task_queue", return_value=queue), \
             patch(
                 "api.v1.endpoints.analysis._load_sync_fundamental_sources",
                 return_value=({}, None, None),
             ):
            status = get_analysis_status("task-queue-2")

        self.assertEqual(status.status, "completed")
        self.assertIsNotNone(status.result)
        self.assertEqual(status.result.created_at, created_at.isoformat())
        self.assertEqual(
            status.result.report["meta"]["created_at"],
            created_at.isoformat(),
        )

    def test_get_analysis_status_completed_db_snapshot_preserves_zero_change_pct(self) -> None:
        if get_analysis_status is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        mock_queue = MagicMock()
        mock_queue.get_task.return_value = None
        history_service, _ = self._history_service(
            record=SimpleNamespace(
                id=1,
                code="600519",
                name="贵州茅台",
                report_type="detailed",
                raw_result={"report_language": "zh", "model_used": "test-model"},
                context_snapshot={
                    "enhanced_context": {
                        "realtime": {
                            "price": 1234.5,
                            "change_pct": 0.0,
                            "change_60d": 12.3,
                        }
                    },
                    "realtime_quote_raw": {"price": 1234.5, "change_pct": 9.9},
                },
                sentiment_score=80,
                operation_advice="持有",
                trend_prediction="看多",
                analysis_summary="summary",
                ideal_buy=None,
                secondary_buy=None,
                stop_loss=None,
                take_profit=None,
                created_at=None,
            )
        )

        with patch("api.v1.endpoints.analysis.get_task_queue", return_value=mock_queue):
            result = get_analysis_status("task-1", history_service=history_service)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.result.report["meta"]["current_price"], 1234.5)
        self.assertEqual(result.result.report["meta"]["change_pct"], 0.0)

    def test_get_analysis_status_completed_db_snapshot_reads_change_pct_from_raw_when_price_present(self) -> None:
        if get_analysis_status is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        mock_queue = MagicMock()
        mock_queue.get_task.return_value = None
        history_service, _ = self._history_service(
            record=SimpleNamespace(
                id=2,
                code="AAPL",
                name="Apple",
                report_type="detailed",
                raw_result={"report_language": "en", "model_used": "test-model"},
                context_snapshot={
                    "enhanced_context": {
                        "realtime": {
                            "price": 180.35,
                            "change_pct": None,
                            "change_60d": None,
                        }
                    },
                    "realtime_quote_raw": {"price": 180.35, "pct_chg": -1.25},
                },
                sentiment_score=72,
                operation_advice="Hold",
                trend_prediction="Neutral",
                analysis_summary="summary",
                ideal_buy=None,
                secondary_buy=None,
                stop_loss=None,
                take_profit=None,
                created_at=None,
            )
        )

        with patch("api.v1.endpoints.analysis.get_task_queue", return_value=mock_queue):
            result = get_analysis_status("task-2", history_service=history_service)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.result.report["meta"]["current_price"], 180.35)
        self.assertEqual(result.result.report["meta"]["change_pct"], -1.25)

    def test_get_analysis_status_completed_db_snapshot_does_not_use_change_60d_as_intraday_change(self) -> None:
        if get_analysis_status is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        mock_queue = MagicMock()
        mock_queue.get_task.return_value = None
        history_service, _ = self._history_service(
            record=SimpleNamespace(
                id=3,
                code="MSFT",
                name="Microsoft",
                report_type="detailed",
                raw_result={"report_language": "en", "model_used": "test-model"},
                context_snapshot={
                    "enhanced_context": {
                        "realtime": {
                            "price": 412.6,
                            "change_pct": None,
                            "change_60d": 14.8,
                        }
                    },
                    "realtime_quote_raw": {"price": 412.6},
                },
                sentiment_score=70,
                operation_advice="Hold",
                trend_prediction="Neutral",
                analysis_summary="summary",
                ideal_buy=None,
                secondary_buy=None,
                stop_loss=None,
                take_profit=None,
                created_at=None,
            )
        )

        with patch("api.v1.endpoints.analysis.get_task_queue", return_value=mock_queue):
            result = get_analysis_status("task-3", history_service=history_service)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.result.report["meta"]["current_price"], 412.6)
        self.assertIsNone(result.result.report["meta"]["change_pct"])

    def test_get_analysis_status_reads_price_fields_from_context_snapshot_preserving_zero_change_pct(self) -> None:
        if get_analysis_status is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        record = SimpleNamespace(
            id=1,
            code="600519",
            name="贵州茅台",
            report_type="detailed",
            created_at=datetime(2026, 4, 10, 12, 0, 0),
            raw_result=json.dumps({"model_used": "test-model", "report_language": "zh"}),
            context_snapshot=json.dumps(
                {
                    "enhanced_context": {
                        "realtime": {
                            "price": 1234.5,
                            "change_pct": 0.0,
                            "change_60d": 9.99,
                        }
                    },
                    "realtime_quote_raw": {
                        "price": 999.9,
                        "change_pct": 8.88,
                        "pct_chg": 7.77,
                    },
                }
            ),
            sentiment_score=80,
            operation_advice="持有",
            trend_prediction="震荡上行",
            analysis_summary="summary",
            ideal_buy=None,
            secondary_buy=None,
            stop_loss=None,
            take_profit=None,
        )
        history_service, _ = self._history_service(record=record)

        with patch("api.v1.endpoints.analysis.get_task_queue") as queue_mock:
            queue_mock.return_value.get_task.return_value = None
            status = get_analysis_status("task_123", history_service=history_service)

        self.assertEqual(status.status, "completed")
        self.assertEqual(status.result.report["meta"]["current_price"], 1234.5)
        self.assertEqual(status.result.report["meta"]["change_pct"], 0.0)
        self.assertEqual(status.result.report["meta"]["model_used"], "test-model")

    def test_get_analysis_status_restores_market_structure_from_raw_result_without_snapshot(self) -> None:
        if get_analysis_status is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        market_structure = {
            "schema_version": "market-structure-v1",
            "status": "partial",
            "market": "cn",
            "market_theme_context": {
                "schema_version": "market-theme-v1",
                "status": "partial",
                "market": "cn",
                "active_themes": [{"name": "机器人概念"}],
            },
            "stock_market_position": {
                "schema_version": "stock-market-position-v1",
                "status": "partial",
                "stock_code": "300024",
                "market": "cn",
                "primary_theme": {"name": "机器人概念"},
            },
        }
        record = SimpleNamespace(
            id=1,
            code="300024",
            name="机器人",
            report_type="detailed",
            created_at=datetime(2026, 4, 10, 12, 0, 0),
            raw_result=json.dumps(
                {
                    "model_used": "test-model",
                    "report_language": "zh",
                    "market_structure_context": market_structure,
                }
            ),
            context_snapshot=None,
            sentiment_score=80,
            operation_advice="持有",
            trend_prediction="震荡上行",
            analysis_summary="summary",
            ideal_buy=None,
            secondary_buy=None,
            stop_loss=None,
            take_profit=None,
        )
        history_service, _ = self._history_service(record=record)

        with patch("api.v1.endpoints.analysis.get_task_queue") as queue_mock:
            queue_mock.return_value.get_task.return_value = None
            status = get_analysis_status("task_market_structure_raw_1", history_service=history_service)

        self.assertEqual(status.status, "completed")
        self.assertEqual(
            status.result.report["details"]["market_structure"]["market_theme_context"]["active_themes"][0]["name"],
            "机器人概念",
        )

    def test_get_analysis_status_completed_db_snapshot_includes_agent_snapshot_board_details(self) -> None:
        if get_analysis_status is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        overview = _analysis_context_pack_overview()
        phase_summary = _market_phase_summary()
        record = SimpleNamespace(
            id=1,
            code="600519",
            name="贵州茅台",
            report_type="detailed",
            created_at=datetime(2026, 4, 10, 12, 0, 0),
            raw_result=json.dumps({"model_used": "test-model", "report_language": "zh"}),
            context_snapshot=json.dumps(
                {
                    "fundamental_context": {
                        "belong_boards": [{"name": "白酒", "type": "行业"}],
                        "boards": {
                            "data": {
                                "top": [{"name": "白酒", "change_pct": 2.8}],
                                "bottom": [],
                            }
                        },
                    },
                    "realtime_quote": {
                        "price": 1888.0,
                        "change_pct": 1.56,
                    },
                    "analysis_context_pack_overview": overview,
                    "market_phase_summary": {
                        **phase_summary,
                        "quote_timestamp": "not-public",
                    },
                }
            ),
            news_content="news",
            sentiment_score=80,
            operation_advice="持有",
            trend_prediction="震荡上行",
            analysis_summary="summary",
            ideal_buy=None,
            secondary_buy=None,
            stop_loss=None,
            take_profit=None,
        )
        history_service, _ = self._history_service(record=record)

        with patch("api.v1.endpoints.analysis.get_task_queue") as queue_mock:
            queue_mock.return_value.get_task.return_value = None
            status = get_analysis_status("task_agent_snapshot_1", history_service=history_service)

        self.assertEqual(status.status, "completed")
        self.assertEqual(status.result.report["meta"]["current_price"], 1888.0)
        self.assertEqual(status.result.report["meta"]["change_pct"], 1.56)
        self.assertIsNone(status.analysis_phase)
        self.assertEqual(
            status.result.report["meta"]["market_phase_summary"]["phase"],
            "intraday",
        )
        self.assertEqual(
            status.result.report["details"]["belong_boards"],
            [{"name": "白酒", "type": "行业"}],
        )
        self.assertEqual(
            status.result.report["details"]["sector_rankings"]["top"][0]["name"],
            "白酒",
        )
        self.assertEqual(
            status.result.report["details"]["analysis_context_pack_overview"]["metadata"]["trigger_source"],
            "api",
        )
        self.assertEqual(
            status.result.report["details"]["analysis_context_pack_overview"]["data_quality"]["overall_score"],
            88,
        )
        self.assertNotIn(
            "analysis_context_pack_overview",
            status.result.report["details"]["context_snapshot"],
        )
        self.assertNotIn(
            "market_phase_summary",
            status.result.report["details"]["context_snapshot"],
        )

    def test_get_analysis_status_in_memory_task_enriches_agent_snapshot_board_details(self) -> None:
        if get_analysis_status is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        overview = _analysis_context_pack_overview()
        phase_summary = _market_phase_summary()
        context_snapshot = {
            "fundamental_context": {
                "belong_boards": [{"name": "白酒", "type": "行业"}],
                "boards": {
                    "data": {
                        "top": [{"name": "白酒", "change_pct": 2.8}],
                        "bottom": [],
                    }
                },
            },
            "realtime_quote": {
                "price": 1888.0,
                "change_pct": 1.56,
            },
            "analysis_context_pack_overview": overview,
            "market_phase_summary": phase_summary,
        }
        task = QueueTaskInfo(
            task_id="task_agent_snapshot_in_memory_1",
            stock_code="600519",
            stock_name="贵州茅台",
            status=TaskStatus.COMPLETED,
            progress=100,
            result={
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "report": {
                    "meta": {
                        "query_id": "task_agent_snapshot_in_memory_1",
                        "stock_code": "600519",
                        "stock_name": "贵州茅台",
                        "report_type": "detailed",
                        "report_language": "zh",
                        "created_at": "2026-04-10T12:00:00",
                        "model_used": "test-model",
                    },
                    "summary": {"analysis_summary": "summary"},
                    "details": {"news_summary": "news"},
                },
            },
            error=None,
            original_query=None,
            selection_source=None,
            analysis_phase="auto",
            skills=None,
            created_at=datetime(2026, 4, 10, 12, 0, 0),
            completed_at=datetime(2026, 4, 10, 12, 1, 0),
        )
        record = SimpleNamespace(context_snapshot=json.dumps(context_snapshot))
        history_service, repository = self._history_service(record=record)

        with patch("api.v1.endpoints.analysis.get_task_queue") as queue_mock:
            queue_mock.return_value.get_task.return_value = task
            status = get_analysis_status(
                "task_agent_snapshot_in_memory_1",
                history_service=history_service,
            )

        self.assertEqual(status.status, "completed")
        self.assertEqual(status.result.report["meta"]["current_price"], 1888.0)
        self.assertEqual(status.result.report["meta"]["change_pct"], 1.56)
        self.assertEqual(
            status.result.report["meta"]["market_phase_summary"]["phase"],
            "intraday",
        )
        self.assertEqual(
            status.result.report["details"]["belong_boards"],
            [{"name": "白酒", "type": "行业"}],
        )
        self.assertEqual(
            status.result.report["details"]["sector_rankings"]["top"][0]["name"],
            "白酒",
        )
        self.assertEqual(
            status.result.report["details"]["analysis_context_pack_overview"]["metadata"]["trigger_source"],
            "api",
        )
        self.assertEqual(
            status.result.report["details"]["analysis_context_pack_overview"]["data_quality"]["overall_score"],
            88,
        )
        self.assertNotIn(
            "analysis_context_pack_overview",
            status.result.report["details"]["context_snapshot"],
        )
        self.assertNotIn(
            "market_phase_summary",
            status.result.report["details"]["context_snapshot"],
        )
        repository.get_latest_analysis_by_query_id.assert_called_once_with(
            "task_agent_snapshot_in_memory_1",
            code="600519",
            report_type=None,
        )

    def test_get_analysis_status_in_memory_task_without_db_snapshot_preserves_service_phase_summary(self) -> None:
        if get_analysis_status is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        phase_summary = _market_phase_summary()
        task = QueueTaskInfo(
            task_id="task_no_snapshot_in_memory_1",
            stock_code="600519",
            stock_name="贵州茅台",
            status=TaskStatus.COMPLETED,
            progress=100,
            analysis_phase="intraday",
            result={
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "report": {
                    "meta": {
                        "query_id": "task_no_snapshot_in_memory_1",
                        "stock_code": "600519",
                        "stock_name": "贵州茅台",
                        "market_phase_summary": phase_summary,
                    },
                    "summary": {"analysis_summary": "summary"},
                },
            },
            error=None,
            original_query=None,
            selection_source=None,
            skills=None,
            created_at=datetime(2026, 4, 10, 12, 0, 0),
            completed_at=datetime(2026, 4, 10, 12, 1, 0),
        )

        history_service, _ = self._history_service()

        with patch("api.v1.endpoints.analysis.get_task_queue") as queue_mock, \
             patch(
                 "api.v1.endpoints.analysis._load_sync_fundamental_sources",
                 return_value=(None, None, None),
             ) as load_sources:
            queue_mock.return_value.get_task.return_value = task
            status = get_analysis_status(
                "task_no_snapshot_in_memory_1",
                history_service=history_service,
            )

        self.assertEqual(status.status, "completed")
        self.assertEqual(status.analysis_phase, "intraday")
        self.assertIsNotNone(status.result)
        self.assertEqual(
            status.result.report["meta"]["market_phase_summary"]["phase"],
            "intraday",
        )
        load_sources.assert_called_once_with(
            query_id="task_no_snapshot_in_memory_1",
            stock_code="600519",
            history_service=history_service,
        )

    def test_get_task_list_includes_analysis_phase_and_skills(self) -> None:
        if get_task_list is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        task = SimpleNamespace(
            task_id="task-list-phase",
            trace_id="trace-list-phase",
            stock_code="600519",
            stock_name="贵州茅台",
            status=TaskStatus.PROCESSING,
            progress=42,
            message="running",
            report_type="detailed",
            created_at=datetime(2026, 4, 10, 12, 0, 0),
            started_at=datetime(2026, 4, 10, 12, 0, 1),
            completed_at=None,
            error=None,
            original_query="茅台",
            selection_source="manual",
            analysis_phase="postmarket",
            skills=["growth_quality"],
            region=None,
        )
        queue = MagicMock()
        queue.list_all_tasks.return_value = [task]
        queue.get_task_stats.return_value = {
            "total": 1,
            "pending": 0,
            "processing": 1,
            "completed": 0,
            "failed": 0,
        }

        with patch("api.v1.endpoints.analysis.get_task_queue", return_value=queue):
            response = get_task_list(status=None, limit=20)

        self.assertEqual(response.tasks[0].analysis_phase, "postmarket")
        self.assertEqual(response.tasks[0].skills, ["growth_quality"])
