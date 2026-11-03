"""Tests for analysis services contract."""

from tests.integration.analysis._analysis_api_contract_support import (
    AnalysisService,
    MagicMock,
    Path,
    SimpleNamespace,
    _AnalysisApiContractTestCaseFixture,
    _call_litellm_vision,
    _handle_sync_analysis,
    _load_sync_fundamental_sources,
    _market_structure_context,
    create_app,
    json,
    patch,
    tempfile,
    unittest,
)


class AnalysisApiContractTestCase(_AnalysisApiContractTestCaseFixture, unittest.TestCase):
    def test_analysis_service_passes_request_skills_to_pipeline(self) -> None:
        service = object.__new__(AnalysisService)
        pipeline_instance = MagicMock()
        pipeline_instance.process_single_stock.return_value = object()
        request_skills = ["growth_quality"]

        with patch("src.config.get_config", return_value=SimpleNamespace()), \
             patch("src.application.analysis.pipeline.StockAnalysisPipeline", return_value=pipeline_instance) as pipeline_cls, \
             patch.object(AnalysisService, "_build_analysis_response", return_value={"stock_code": "600519"}):
            result = AnalysisService.analyze_stock(
                service,
                "600519",
                report_type="full",
                query_id="q1",
                skills=request_skills,
            )

        self.assertEqual(result, {"stock_code": "600519"})
        self.assertEqual(pipeline_cls.call_args.kwargs["analysis_skills"], request_skills)

    def test_analysis_service_returns_none_and_records_last_error_for_unsuccessful_pipeline_result(self) -> None:
        service = AnalysisService()
        pipeline_instance = MagicMock()
        pipeline_instance.process_single_stock.return_value = SimpleNamespace(
            success=False,
            error_message="LLM stream interrupted",
        )

        with patch("src.config.get_config", return_value=SimpleNamespace()), \
             patch("src.application.analysis.pipeline.StockAnalysisPipeline", return_value=pipeline_instance):
            result = service.analyze_stock("600519", report_type="detailed", query_id="q1", send_notification=False)

        self.assertIsNone(result)
        self.assertEqual(service.last_error, "LLM stream interrupted")

    def test_handle_sync_analysis_uses_service_last_error_for_failed_pipeline_result(self) -> None:
        if _handle_sync_analysis is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        service_instance = MagicMock()
        service_instance.analyze_stock.return_value = None
        service_instance.last_error = "LLM stream interrupted"

        with patch("src.application.analysis.analysis_service.AnalysisService", return_value=service_instance):
            with self.assertRaises(Exception) as ctx:
                _handle_sync_analysis(
                    "600519",
                    SimpleNamespace(
                        report_type="detailed",
                        force_refresh=False,
                        notify=True,
                        analysis_phase="auto",
                    ),
                    self._history_service()[0],
                )

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertEqual(
            ctx.exception.detail,
            {
                "error": "analysis_failed",
                "message": "LLM stream interrupted",
            },
        )

    def test_handle_sync_analysis_restores_market_structure_from_raw_result_snapshot(self) -> None:
        if _handle_sync_analysis is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        market_structure = _market_structure_context()
        service_instance = MagicMock()
        service_instance.analyze_stock.return_value = {
            "stock_code": "300024",
            "stock_name": "机器人",
            "report": {
                "meta": {"stock_code": "300024", "report_language": "zh"},
                "summary": {"analysis_summary": "summary"},
                "strategy": {},
                "details": {"news_summary": "news"},
            },
        }

        with patch("uuid.uuid4", return_value=SimpleNamespace(hex="q-sync-market-structure")), \
             patch("src.application.analysis.analysis_service.AnalysisService", return_value=service_instance), \
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
             ):
            result = _handle_sync_analysis(
                "300024",
                SimpleNamespace(
                    report_type="detailed",
                    force_refresh=False,
                    notify=True,
                    skills=None,
                    analysis_phase="intraday",
                ),
                self._history_service()[0],
            )

        self.assertEqual(
            result.report["details"]["market_structure"]["market_theme_context"]["active_themes"][0]["name"],
            "机器人概念",
        )

    def test_handle_sync_analysis_carries_market_structure_from_service_without_fallback(self) -> None:
        if _handle_sync_analysis is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        market_structure = _market_structure_context()
        service = AnalysisService()
        service_result = service._build_analysis_response(
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
            "q-sync-no-history",
            report_type="detailed",
        )
        service_instance = MagicMock()
        service_instance.analyze_stock.return_value = service_result

        with patch("uuid.uuid4", return_value=SimpleNamespace(hex="q-sync-no-history")), \
             patch("src.application.analysis.analysis_service.AnalysisService", return_value=service_instance), \
             patch(
                 "api.v1.endpoints.analysis._load_sync_fundamental_sources",
                 return_value=(None, None, None),
             ):
            result = _handle_sync_analysis(
                "300024",
                SimpleNamespace(
                    report_type="detailed",
                    force_refresh=False,
                    notify=True,
                    skills=None,
                    analysis_phase="intraday",
                ),
                self._history_service()[0],
            )

        self.assertIsNotNone(result)
        self.assertEqual(
            result.report["details"]["market_structure"]["market_theme_context"]["active_themes"][0]["name"],
            "机器人概念",
        )
        self.assertEqual(
            result.report["details"]["raw_result"]["market_structure_context"]["market_theme_context"]["active_themes"][0]["name"],
            "机器人概念",
        )
        self.assertNotIn(
            "raw_result",
            result.report["details"]["raw_result"],
        )

    def test_analysis_service_passes_analysis_phase_to_pipeline(self) -> None:
        service = AnalysisService()
        pipeline_instance = MagicMock()
        pipeline_instance.process_single_stock.return_value = SimpleNamespace(
            success=True,
            code="600519",
            name="贵州茅台",
            current_price=1234.56,
            change_pct=1.23,
            model_used="test-model",
            analysis_summary="summary",
            operation_advice="hold",
            trend_prediction="up",
            sentiment_score=80,
            news_summary="news",
            technical_analysis="tech",
            fundamental_analysis="fundamental",
            risk_warning="risk",
            get_sniper_points=lambda: {},
        )

        with patch("src.config.get_config", return_value=SimpleNamespace()), patch(
            "src.application.analysis.pipeline.StockAnalysisPipeline",
            return_value=pipeline_instance,
        ) as pipeline_cls:
            result = service.analyze_stock(
                "600519",
                report_type="detailed",
                send_notification=False,
                analysis_phase="postmarket",
            )

        self.assertIsNotNone(result)
        self.assertEqual(pipeline_cls.call_args.kwargs["analysis_phase"], "postmarket")

    def test_load_sync_fundamental_sources_uses_query_and_code_for_fallback(self) -> None:
        if _load_sync_fundamental_sources is None:
            self.skipTest("analysis endpoint helpers unavailable in this environment")

        raw_result_payload = {
            "model_used": "test-model",
            "report_language": "zh",
            "market_structure_context": _market_structure_context(),
        }
        fallback_payload = {
            "earnings": {
                "data": {
                    "financial_report": {"report_date": "2025-12-31"},
                    "dividend": {"ttm_dividend_yield_pct": 2.1},
                }
            }
        }
        history_service, repository = self._history_service(
            record=SimpleNamespace(
                context_snapshot=None,
                raw_result=json.dumps(raw_result_payload, ensure_ascii=False),
            ),
            fundamental=fallback_payload,
        )

        context_snapshot, fundamental_snapshot, raw_result_snapshot = _load_sync_fundamental_sources(
            query_id="q_sync_001",
            stock_code="600519",
            history_service=history_service,
        )

        self.assertIsNone(context_snapshot)
        self.assertEqual(fundamental_snapshot, fallback_payload)
        self.assertEqual(raw_result_snapshot, raw_result_payload)
        repository.get_latest_analysis_by_query_id.assert_called_once_with(
            "q_sync_001",
            code="600519",
            report_type=None,
        )
        repository.get_latest_fundamental_snapshot.assert_called_once_with(
            query_id="q_sync_001",
            code="600519",
        )

    def test_openapi_declares_single_and_batch_async_202_payloads(self) -> None:
        if create_app is None:
            self.skipTest("fastapi is not installed in this test environment")

        with tempfile.TemporaryDirectory() as temp_dir:
            app = create_app(static_dir=Path(temp_dir))
            schema = app.openapi()["paths"]["/api/v1/analysis/analyze"]["post"]["responses"]["202"][
                "content"
            ]["application/json"]["schema"]

        refs = {item["$ref"] for item in schema["anyOf"]}
        self.assertEqual(
            refs,
            {
                "#/components/schemas/TaskAccepted",
                "#/components/schemas/BatchTaskAcceptedResponse",
            },
        )

    def test_openapi_declares_backtest_phase_filter_enum_and_400(self) -> None:
        if create_app is None:
            self.skipTest("fastapi is not installed in this test environment")

        with tempfile.TemporaryDirectory() as temp_dir:
            app = create_app(static_dir=Path(temp_dir))
            paths = app.openapi()["paths"]

        for path in (
            "/api/v1/backtest/results",
            "/api/v1/backtest/performance",
            "/api/v1/backtest/performance/{code}",
        ):
            operation = paths[path]["get"]
            self.assertIn("400", operation["responses"])
            params = {param["name"]: param for param in operation["parameters"]}
            schema = params["analysis_phase"]["schema"]
            enum_values = set()
            stack = [schema]
            while stack:
                current = stack.pop()
                if not isinstance(current, dict):
                    continue
                enum_values.update(current.get("enum") or [])
                stack.extend(current.get("anyOf") or [])
                stack.extend(current.get("oneOf") or [])

            self.assertEqual(enum_values, {"premarket", "intraday", "postmarket", "unknown"})


class ImageStockExtractorContractTestCase(unittest.TestCase):
    def test_litellm_completion_patch_target_remains_available(self) -> None:
        cfg = SimpleNamespace(
            vision_model="",
            openai_vision_model=None,
            litellm_model="",
            gemini_api_keys=["sk-gemini-testkey-1234"],
            gemini_model="gemini-2.0-flash",
            anthropic_api_keys=[],
            anthropic_model="claude-3-5-sonnet-20241022",
            openai_api_keys=[],
            openai_model="gpt-4o-mini",
            openai_base_url=None,
        )
        msg = MagicMock()
        msg.content = '["600519"]'
        choice = MagicMock()
        choice.message = msg
        response = MagicMock()
        response.choices = [choice]

        with patch("src.application.analysis.image_stock_extractor.get_config", return_value=cfg), \
             patch("src.infrastructure.generation.vision_litellm.litellm.completion", return_value=response) as mock_completion:
            result = _call_litellm_vision("base64data", "image/jpeg")

        self.assertEqual(result, '["600519"]')
        mock_completion.assert_called_once()
