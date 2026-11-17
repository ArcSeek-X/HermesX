"""Tests for analyzer generation routing."""

from tests.application.analysis._market_analyzer_generate_text_support import (
    MagicMock,
    SimpleNamespace,
    _AnalyzerRuntimePortWiringTestCaseFixture,
    _OPENAI_COMPATIBILITY_PAYLOAD_FIXTURES,
    _TestAnalyzerGenerateTextFixture,
    _assert_usage_contains,
    _llm_usage_hmac_env,
    _usage_port,
    analyzer_module,
    configure_analyzer_runtime,
    patch,
    pytest,
)


class TestAnalyzerGenerateText(_TestAnalyzerGenerateTextFixture):
    def test_legacy_market_group_normalizes_supported_markets(self):
        from src.application.analysis.analyzer import _legacy_market_group

        assert _legacy_market_group("") == "unknown"
        assert _legacy_market_group("unknown") == "unknown"
        assert _legacy_market_group("600519") == "cn"
        assert _legacy_market_group("hk00700") == "hk"
        assert _legacy_market_group("AAPL") == "us"

    def test_call_litellm_wrapper_uses_generation_backend_tuple_contract(self):
        from src.application.generation.ports import GenerationBackend

        analyzer = self._make_analyzer()
        backend = MagicMock(spec=GenerationBackend)
        backend.generate.return_value = SimpleNamespace(
            text="backend response",
            model="gemini/gemini-3.1-pro-preview",
            usage={"provider": "gemini", "total_tokens": 9},
        )

        with patch.object(analyzer, "get_generation_backend", return_value=backend):
            result = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
                system_prompt="system",
                stream=True,
                stream_progress_callback=lambda _chars: None,
                response_validator=lambda _text: None,
                audit_context={"call_type": "analysis"},
            )

        assert result == (
            "backend response",
            "gemini/gemini-3.1-pro-preview",
            {"provider": "gemini", "total_tokens": 9},
        )
        backend.generate.assert_called_once()
        _, generation_config = backend.generate.call_args.args
        assert generation_config == {"max_tokens": 128, "temperature": 0.2}
        assert backend.generate.call_args.kwargs["system_prompt"] == "system"
        assert backend.generate.call_args.kwargs["stream"] is True
        assert callable(backend.generate.call_args.kwargs["stream_progress_callback"])
        assert callable(backend.generate.call_args.kwargs["response_validator"])
        assert backend.generate.call_args.kwargs["audit_context"] == {"call_type": "analysis"}

    def test_call_litellm_legacy_path_uses_legacy_model_list_for_param_recovery(self):
        with patch("src.application.analysis.analyzer.get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.litellm_model = "openai/gpt-4o-mini"
            cfg.litellm_fallback_models = []
            cfg.gemini_api_keys = []
            cfg.anthropic_api_keys = []
            cfg.deepseek_api_keys = []
            cfg.openai_api_keys = ["sk-openai-legacy-a", "sk-openai-legacy-b"]
            cfg.openai_base_url = None
            cfg.llm_model_list = [
                {
                    "model_name": "__legacy_openai__",
                    "litellm_params": {
                        "model": "__legacy_openai__",
                        "api_key": "sk-openai-legacy-a",
                        "api_base": "https://legacy-a.example/v1",
                        "extra_headers": {"x-tenant": "legacy-a"},
                    },
                },
                {
                    "model_name": "__legacy_openai__",
                    "litellm_params": {
                        "model": "__legacy_openai__",
                        "api_key": "sk-openai-legacy-b",
                        "api_base": "https://legacy-b.example/v1",
                        "extra_headers": {"x-tenant": "legacy-b"},
                    },
                },
            ]
            cfg.llm_temperature = 0.7
            mock_cfg.return_value = cfg

            from src.application.analysis.analyzer import GeminiAnalyzer

            analyzer = GeminiAnalyzer()
            analyzer._config_override = cfg

        captured = {}

        def _fake_call_litellm_with_param_recovery(call, **kwargs):
            captured["model_list"] = kwargs.get("model_list")
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
                usage=None,
            )

        with patch("src.application.analysis.analyzer.call_litellm_with_param_recovery", side_effect=_fake_call_litellm_with_param_recovery):
            text, _, _ = analyzer._call_litellm("回归用例", {"max_tokens": 128, "temperature": 0.7})

        assert text == "ok"
        passed_model_list = captured.get("model_list")
        assert passed_model_list is not None
        assert len(passed_model_list) == 2
        assert all(item["litellm_params"].get("model") == "openai/gpt-4o-mini" for item in passed_model_list)
        assert [item["litellm_params"]["api_base"] for item in passed_model_list] == [
            "https://legacy-a.example/v1",
            "https://legacy-b.example/v1",
        ]
        assert [item["litellm_params"]["extra_headers"] for item in passed_model_list] == [
            {"x-tenant": "legacy-a"},
            {"x-tenant": "legacy-b"},
        ]

    @pytest.mark.parametrize("selected_model", ["anthropic/foo bad", "openai/anthropic/foo bad"])
    def test_provider_looking_malformed_hermes_model_is_not_reinterpreted_as_direct_provider(self, selected_model):
        from src.config import Config
        from src.application.analysis.analyzer import GeminiAnalyzer
        from src.application.generation.ports import GenerationError

        env = {
            "LLM_CHANNELS": "hermes,primary",
            "LLM_HERMES_API_KEY": "hermes-key",
            "LLM_HERMES_MODELS": "anthropic/foo bad",
            "LLM_PRIMARY_PROTOCOL": "openai",
            "LLM_PRIMARY_BASE_URL": "https://example.invalid/v1",
            "LLM_PRIMARY_API_KEY": "sibling-key",
            "LLM_PRIMARY_MODELS": "gpt-sibling",
            "ANTHROPIC_API_KEY": "anthropic-legacy-key",
            "LITELLM_MODEL": selected_model,
        }

        with patch("src.config.settings.setup_env"), \
             patch.object(Config, "parse_litellm_yaml", return_value=[]), \
             patch.dict("os.environ", env, clear=True):
            config = Config._load_from_env()
            analyzer = GeminiAnalyzer(config=config)

        error = analyzer.get_generation_backend_config_error()
        assert error is not None
        assert error.details["code"] == "explicit_hermes_route_invalid"
        assert error.details["field"] == "LITELLM_MODEL"

        with patch("src.infrastructure.providers.analyzer_runtime.litellm.completion") as completion:
            with pytest.raises(GenerationError):
                analyzer._call_litellm("prompt", {"max_tokens": 4})
        completion.assert_not_called()

    @pytest.mark.parametrize(
        "provider_model,response_payload,expected_text",
        _OPENAI_COMPATIBILITY_PAYLOAD_FIXTURES,
        ids=[
            "issue1279-message-content-null",
            "issue1279-message-content-list",
            "issue2013-minimax-reasoning-block",
        ],
    )
    def test_call_litellm_extracts_external_provider_text_shapes(self, provider_model, response_payload, expected_text):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model=provider_model,
            litellm_fallback_models=[],
            llm_model_list=[],
        )
        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=response_payload):
            text, model_used, usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
            )

        assert text == expected_text
        assert model_used == provider_model
        _assert_usage_contains(usage, response_payload["usage"])

    def test_call_litellm_stream_falls_back_to_non_stream_after_partial_and_falls_back_model(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="provider/bad-model",
            litellm_fallback_models=["provider/good-model"],
            llm_model_list=[],
        )

        def partial_then_broken_stream():
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="abc"))],
                usage=None,
            )
            raise RuntimeError("stream disconnected")

        def good_stream():
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="fallback"))],
                usage=SimpleNamespace(prompt_tokens=4, completion_tokens=5, total_tokens=9),
            )

        fallback_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="fallback full"))],
            usage=SimpleNamespace(prompt_tokens=7, completion_tokens=8, total_tokens=15),
        )

        dispatch_calls = []

        def fake_dispatch(model, call_kwargs, **kwargs):
            dispatch_calls.append((model, bool(call_kwargs.get("stream"))))
            if model == "provider/bad-model":
                if call_kwargs.get("stream"):
                    return partial_then_broken_stream()
                raise RuntimeError("non-stream model broken")
            if call_kwargs.get("stream"):
                return good_stream()
            return fallback_response

        with patch.object(analyzer, "_dispatch_litellm_completion", side_effect=fake_dispatch):
            text, model_used, usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
                stream=True,
            )

        assert text == "fallback"
        assert model_used == "provider/good-model"
        _assert_usage_contains(usage, {"prompt_tokens": 4, "completion_tokens": 5, "total_tokens": 9})
        assert dispatch_calls == [
            ("provider/bad-model", True),
            ("provider/bad-model", False),
            ("provider/good-model", True),
        ]

    def test_analyze_all_models_invalid_json_goes_through_post_processing(self):
        """When all models return non-JSON, analyze() must still run integrity
        checks, placeholder fill, and persist_llm_usage — no early return.

        With report_integrity_retry=1, the retry loop runs once (re-prompting
        with complement instructions); when that also yields invalid JSON the
        exhausted-retries path fires placeholder fill.
        """
        from src.application.analysis.analyzer import AnalysisResult, _AllModelsFailedError

        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            gemini_request_delay=0,
            report_language="zh",
            litellm_model="provider/primary-model",
            litellm_fallback_models=["provider/fallback-model"],
            llm_temperature=0.7,
            llm_model_list=[],
            report_integrity_enabled=True,
            report_integrity_retry=1,
        )

        # _parse_response on non-JSON text produces a text fallback result
        text_fallback_result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=50,
            trend_prediction="震荡",
            operation_advice="持有",
            analysis_summary="部分文本摘要",
            success=False,
            error_message="LLM response is not valid JSON; analysis result will not be persisted",
        )

        all_models_error = _AllModelsFailedError(
            "all failed",
            last_response_text="这不是 JSON，而是纯文本分析结果",
            last_model="provider/fallback-model",
            last_usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        )

        with patch.object(analyzer, "is_available", return_value=True), \
             patch.object(analyzer, "_get_analysis_system_prompt", return_value="system"), \
             patch.object(analyzer, "_format_prompt", return_value="prompt"), \
             patch.object(
                 analyzer,
                 "_call_litellm",
                 side_effect=all_models_error,
             ) as mock_call, \
             patch.object(analyzer, "_parse_response", return_value=text_fallback_result) as mock_parse, \
             patch.object(analyzer, "_build_market_snapshot", return_value={}), \
             patch.object(analyzer, "_check_content_integrity", return_value=(False, ["dashboard.core_conclusion.one_sentence"])), \
             patch.object(analyzer, "_build_integrity_retry_prompt", return_value="retry prompt"), \
             patch.object(analyzer, "_apply_placeholder_fill") as mock_fill, \
             patch.object(_usage_port(), "persist") as mock_usage:

            result = analyzer.analyze(
                {"code": "600519", "stock_name": "贵州茅台"},
                news_context="some news",
            )

        # _call_litellm called twice: initial + 1 retry
        assert mock_call.call_count == 2

        # _parse_response called twice (initial + retry)
        assert mock_parse.call_count == 2
        mock_parse.assert_called_with("这不是 JSON，而是纯文本分析结果", "600519", "贵州茅台")

        # Placeholder fill was applied after retry exhaustion
        mock_fill.assert_called_once()
        assert "dashboard.core_conclusion.one_sentence" in mock_fill.call_args[0][1]

        # 用量经过已装配的遥测端口 persist 写入（最后一次模型与 usage）
        mock_usage.assert_called_once()
        usage_args = mock_usage.call_args
        assert usage_args[0][0] == {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        assert usage_args[0][1] == "provider/fallback-model"
        assert usage_args[1]["call_type"] == "analysis"
        assert usage_args[1]["stock_code"] == "600519"

        # Result is success=False (text fallback), but all fields exist
        assert result.success is False
        assert result.code == "600519"
        assert result.search_performed is True


class AnalyzerRuntimePortWiringTestCase(_AnalyzerRuntimePortWiringTestCaseFixture):
    def test_configure_analyzer_runtime_binds_adapter_idempotently(self) -> None:
        import src.application.analysis.analyzer as analyzer_module
        from src.application.analysis.analyzer_runtime_ports import AnalyzerLLMPort  # noqa: F401  契约锚点
        from src.infrastructure.providers.analyzer_runtime import AnalyzerLLMAdapter

        original = analyzer_module._analyzer_llm_port
        try:
            # None 不覆盖：幂等语义保持不变。
            analyzer_module.set_analyzer_llm_port(None)
            assert isinstance(analyzer_module._get_analyzer_llm_port(), AnalyzerLLMAdapter)
            configure_analyzer_runtime()
            configure_analyzer_runtime()
            assert isinstance(analyzer_module._get_analyzer_llm_port(), AnalyzerLLMAdapter)
        finally:
            analyzer_module._analyzer_llm_port = original
