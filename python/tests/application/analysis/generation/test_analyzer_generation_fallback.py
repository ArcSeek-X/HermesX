"""Tests for analyzer generation fallback."""

from tests.application.analysis._market_analyzer_generate_text_support import (
    MagicMock,
    SimpleNamespace,
    _AnalyzerRuntimePortWiringTestCaseFixture,
    _TestAnalyzerGenerateTextFixture,
    _assert_no_provider_usage_hmac_only,
    _assert_usage_contains,
    _llm_usage_hmac_env,
    _usage_port,
    analyzer_module,
    contextmanager,
    json,
    patch,
    pytest,
)


class TestAnalyzerGenerateText(_TestAnalyzerGenerateTextFixture):
    def test_analyze_uses_litellm_fallback_when_codex_cli_config_error_is_fallbackable(self):
        from src.application.generation.ports import GenerationBackend, GenerationError, GenerationErrorCode
        from src.infrastructure.generation.local_cli_backend import LocalCliGenerationBackend

        analyzer = self._make_analyzer()
        analyzer._litellm_available = True
        analyzer._config_override = SimpleNamespace(
            generation_backend="codex_cli",
            generation_fallback_backend="litellm",
            litellm_model="gemini/gemini-2.0-flash",
            litellm_fallback_models=[],
            llm_model_list=[],
            report_language="zh",
            gemini_request_delay=0,
            llm_temperature=0.7,
            report_integrity_enabled=False,
            report_integrity_retry=0,
        )
        codex_error = GenerationError(
            error_code=GenerationErrorCode.COMMAND_NOT_FOUND,
            stage="configuration",
            retryable=False,
            fallbackable=True,
            backend="codex_cli",
            provider="codex_cli",
            details={"reason": "executable_not_found"},
        )
        primary_backend = MagicMock(spec=LocalCliGenerationBackend)
        primary_backend.get_config_error.return_value = codex_error
        primary_backend.generate.side_effect = codex_error
        fallback_backend = MagicMock(spec=GenerationBackend)
        fallback_backend.generate.return_value = SimpleNamespace(
            text=json.dumps({
                "sentiment_score": 70,
                "trend_prediction": "看多",
                "operation_advice": "持有",
                "analysis_summary": "fallback ok",
            }),
            model="gemini/gemini-2.0-flash",
            usage={
                "usage_available": False,
                "usage_source": "unavailable",
                "backend": "litellm",
            },
        )

        def _backend_for(backend_id=None):
            return primary_backend if backend_id == "codex_cli" else fallback_backend

        with patch.object(analyzer, "get_generation_backend", side_effect=_backend_for), \
             patch.object(analyzer, "_get_analysis_system_prompt", return_value="system"), \
             patch.object(analyzer, "_get_skill_prompt_sections", return_value=(None, None, True)), \
             patch.object(analyzer, "_format_prompt", return_value="prompt"), \
             patch.object(analyzer, "_build_market_snapshot", return_value={}):
            assert analyzer.is_available() is True
            result = analyzer.analyze({"code": "600519", "stock_name": "贵州茅台"})

        assert result.success is True
        assert result.analysis_summary == "fallback ok"
        primary_backend.generate.assert_called()
        fallback_backend.generate.assert_called()

    def test_analyze_preserves_litellm_text_fallback_after_codex_cli_primary_failure(self):
        from src.application.analysis.analyzer import AnalysisResult, _AllModelsFailedError
        from src.application.generation.ports import GenerationBackend, GenerationError, GenerationErrorCode

        analyzer = self._make_analyzer()
        analyzer._litellm_available = True
        analyzer._config_override = SimpleNamespace(
            generation_backend="codex_cli",
            generation_fallback_backend="litellm",
            litellm_model="provider/primary-model",
            litellm_fallback_models=["provider/fallback-model"],
            llm_model_list=[],
            report_language="zh",
            gemini_request_delay=0,
            llm_temperature=0.7,
            report_integrity_enabled=False,
            report_integrity_retry=0,
        )
        primary_error = GenerationError(
            error_code=GenerationErrorCode.COMMAND_NOT_FOUND,
            stage="configuration",
            retryable=False,
            fallbackable=True,
            backend="codex_cli",
            provider="codex_cli",
            details={"reason": "executable_not_found"},
        )
        all_models_error = _AllModelsFailedError(
            "all fallback models returned invalid JSON",
            last_response_text="这不是 JSON，而是 fallback 模型返回的纯文本分析",
            last_model="provider/fallback-model",
            last_usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        )
        text_fallback_result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=50,
            trend_prediction="震荡",
            operation_advice="持有",
            analysis_summary="纯文本兜底摘要",
            success=False,
            error_message="LLM response is not valid JSON; analysis result will not be persisted",
        )
        primary_backend = MagicMock(spec=GenerationBackend)
        primary_backend.generate.side_effect = primary_error
        fallback_backend = MagicMock(spec=GenerationBackend)
        fallback_backend.generate.side_effect = all_models_error

        def _backend_for(backend_id):
            return primary_backend if backend_id == "codex_cli" else fallback_backend

        with patch.object(analyzer, "get_generation_backend_config_error", return_value=None), \
             patch.object(analyzer, "is_available", return_value=True), \
             patch.object(analyzer, "get_generation_backend", side_effect=_backend_for), \
             patch.object(analyzer, "_get_analysis_system_prompt", return_value="system"), \
             patch.object(analyzer, "_get_skill_prompt_sections", return_value=(None, None, True)), \
             patch.object(analyzer, "_format_prompt", return_value="prompt"), \
             patch.object(analyzer, "_parse_response", return_value=text_fallback_result) as mock_parse, \
             patch.object(analyzer, "_build_market_snapshot", return_value={}), \
             patch.object(_usage_port(), "persist") as mock_persist:
            result = analyzer.analyze({"code": "600519", "stock_name": "贵州茅台"})

        assert result.analysis_summary == "纯文本兜底摘要"
        assert result.raw_response == "这不是 JSON，而是 fallback 模型返回的纯文本分析"
        assert result.model_used == "provider/fallback-model"
        mock_parse.assert_called_once_with(
            "这不是 JSON，而是 fallback 模型返回的纯文本分析",
            "600519",
            "贵州茅台",
        )
        mock_persist.assert_called_once_with(
            {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            "provider/fallback-model",
            call_type="analysis",
            stock_code="600519",
        )
        primary_backend.generate.assert_called_once()
        fallback_backend.generate.assert_called_once()

    def test_generate_text_returns_none_on_failure(self):
        analyzer = self._make_analyzer()
        with patch.object(analyzer, "_call_litellm", side_effect=Exception("LLM error")):
            result = analyzer.generate_text("prompt")
            assert result is None  # must not raise

    def test_generate_text_raises_generation_error_for_unsupported_backend(self):
        from src.application.generation.ports import GenerationError

        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            generation_backend="codex",
            generation_fallback_backend="litellm",
        )

        with pytest.raises(GenerationError) as exc_info:
            analyzer.generate_text("prompt")

        assert exc_info.value.details["field"] == "GENERATION_BACKEND"
        assert exc_info.value.details["requested_backend"] == "codex"

    def test_call_litellm_wraps_fallback_generation_error_with_primary_context(self):
        from src.application.generation.ports import GenerationBackend, GenerationError, GenerationErrorCode

        analyzer = self._make_analyzer()
        analyzer._config_override.generation_backend = "codex_cli"
        analyzer._config_override.generation_fallback_backend = "litellm"
        primary_error = GenerationError(
            error_code=GenerationErrorCode.COMMAND_NOT_FOUND,
            stage="configuration",
            retryable=False,
            fallbackable=True,
            backend="codex_cli",
            provider="codex_cli",
            details={"reason": "executable_not_found"},
        )
        fallback_error = GenerationError(
            error_code=GenerationErrorCode.INVALID_JSON,
            stage="validation",
            retryable=True,
            fallbackable=True,
            backend="litellm",
            provider="gemini",
            details={"reason": "invalid_json"},
        )
        primary_backend = MagicMock(spec=GenerationBackend)
        primary_backend.generate.side_effect = primary_error
        fallback_backend = MagicMock(spec=GenerationBackend)
        fallback_backend.generate.side_effect = fallback_error

        def _backend_for(backend_id):
            return primary_backend if backend_id == "codex_cli" else fallback_backend

        with patch.object(analyzer, "get_generation_backend", side_effect=_backend_for):
            with pytest.raises(GenerationError) as exc_info:
                analyzer._call_litellm("prompt", {"max_tokens": 128})

        error = exc_info.value
        assert error.stage == "fallback"
        assert error.error_code is GenerationErrorCode.INVALID_JSON
        assert error.details["reason"] == "fallback_backend_failed"
        assert error.details["primary_error"]["error_code"] == "command_not_found"
        assert error.details["primary_error"]["details"]["reason"] == "executable_not_found"
        assert error.details["fallback_error"]["error_code"] == "invalid_json"
        assert error.details["fallback_error"]["details"]["reason"] == "invalid_json"

    def test_call_litellm_rejects_unknown_generation_backend_without_litellm_fallback(self):
        from src.application.generation.ports import GenerationError

        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            generation_backend="codex",
            generation_fallback_backend="litellm",
        )

        with pytest.raises(GenerationError) as exc_info:
            analyzer._call_litellm("prompt", {"max_tokens": 128})

        assert exc_info.value.details["requested_backend"] == "codex"

    def test_call_litellm_rejects_unknown_generation_fallback_backend(self):
        from src.application.generation.ports import GenerationError

        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            generation_backend="litellm",
            generation_fallback_backend="codex",
        )

        with pytest.raises(GenerationError) as exc_info:
            analyzer._call_litellm("prompt", {"max_tokens": 128})

        assert exc_info.value.details["field"] == "GENERATION_FALLBACK_BACKEND"
        assert exc_info.value.details["requested_backend"] == "codex"

    def test_analyze_reports_generation_backend_config_error_instead_of_api_key_missing(self):
        analyzer = self._make_analyzer()
        analyzer._litellm_available = True
        analyzer._config_override = SimpleNamespace(
            generation_backend="codex",
            generation_fallback_backend="litellm",
            report_language="zh",
            gemini_request_delay=0,
        )

        with patch.object(analyzer, "_get_analysis_system_prompt", return_value="system"), \
             patch.object(analyzer, "_get_skill_prompt_sections", return_value=(None, None, True)):
            result = analyzer.analyze({"code": "AAPL", "stock_name": "Apple"})

        assert result.success is False
        assert "backend_not_configured" in result.error_message
        assert "GENERATION_BACKEND" in result.error_message
        assert "codex" in result.error_message
        assert "API Key" not in result.error_message
        assert "API Key" not in result.analysis_summary

    def test_call_litellm_hermes_failure_redacts_secret_from_logs_and_error(self, caplog):
        from src.application.analysis.analyzer import _AllModelsFailedError

        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="openai/hermes-agent",
            litellm_fallback_models=[],
            llm_model_list=[
                {
                    "model_name": "openai/hermes-agent",
                    "litellm_params": {
                        "model": "openai/hermes-agent",
                        "api_key": "saved-secret-token",
                        "api_base": "http://127.0.0.1:8642/v1",
                    },
                    "model_info": {"hrs_channel": "hermes"},
                }
            ],
            llm_temperature=0.0,
            generation_backend="litellm",
            generation_fallback_backend="",
            llm_channel_config_issues=[],
            llm_blocks_legacy_fallback=False,
        )

        @contextmanager
        def fake_no_proxy_client(**_kwargs):
            yield object()

        caplog.set_level("WARNING", logger="src.application.analysis.analyzer")
        with patch("src.infrastructure.generation.hermes.open_hermes_no_proxy_client", side_effect=fake_no_proxy_client), \
             patch("src.infrastructure.providers.analyzer_runtime.litellm.completion", side_effect=RuntimeError("upstream saw saved-secret-token")):
            with pytest.raises(_AllModelsFailedError) as exc_info:
                analyzer._call_litellm("prompt", {"max_tokens": 4})

        assert "saved-secret-token" not in str(exc_info.value)
        assert "saved-secret-token" not in caplog.text
        assert "[REDACTED]" in str(exc_info.value)

    def test_analyze_redacts_hermes_secret_from_final_error_result(self, caplog):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="openai/hermes-agent",
            litellm_fallback_models=[],
            llm_model_list=[
                {
                    "model_name": "openai/hermes-agent",
                    "litellm_params": {
                        "model": "openai/hermes-agent",
                        "api_key": "saved-secret-token",
                        "api_base": "http://127.0.0.1:8642/v1",
                    },
                    "model_info": {"hrs_channel": "hermes"},
                }
            ],
            generation_backend="litellm",
            generation_fallback_backend="",
            llm_channel_config_issues=[],
            llm_blocks_legacy_fallback=False,
            llm_temperature=0.0,
            report_integrity_enabled=False,
            report_integrity_retry=0,
            report_language="zh",
            gemini_request_delay=0,
        )
        context = {"code": "600519", "stock_name": "贵州茅台"}

        caplog.set_level("ERROR", logger="src.application.analysis.analyzer")
        with patch.object(analyzer, "get_generation_backend_config_error", return_value=None), \
             patch.object(analyzer, "is_available", return_value=True), \
             patch.object(analyzer, "_get_analysis_system_prompt", return_value="system"), \
             patch.object(analyzer, "_get_skill_prompt_sections", return_value=("", "", False)), \
             patch.object(analyzer, "_format_prompt", return_value="prompt"), \
             patch.object(analyzer, "_call_litellm", side_effect=RuntimeError("upstream saw saved-secret-token")):
            result = analyzer.analyze(context)

        assert result.success is False
        assert "saved-secret-token" not in result.error_message
        assert "saved-secret-token" not in result.analysis_summary
        assert "saved-secret-token" not in result.risk_warning
        assert "saved-secret-token" not in caplog.text
        assert "[REDACTED]" in result.error_message

    def test_generation_config_error_rejects_mixed_hermes_route(self):
        from src.application.generation.ports import GenerationErrorCode

        analyzer = self._make_analyzer()
        analyzer._router = None
        analyzer._litellm_available = False
        analyzer._config_override = SimpleNamespace(
            litellm_model="shared-route",
            litellm_fallback_models=[],
            llm_model_list=[
                {
                    "model_name": "shared-route",
                    "litellm_params": {
                        "model": "hermes-agent",
                        "api_key": "sk-hermes-test-value",
                        "api_base": "http://127.0.0.1:8642/v1",
                    },
                    "model_info": {"hrs_channel": "hermes"},
                },
                {
                    "model_name": "shared-route",
                    "litellm_params": {
                        "model": "openai/gpt-4o-mini",
                        "api_key": "sk-openai-test-value",
                    },
                },
            ],
            generation_backend="litellm",
            generation_fallback_backend="",
            llm_channel_config_issues=[],
            llm_blocks_legacy_fallback=False,
        )

        error = analyzer.get_generation_backend_config_error()

        assert error is not None
        assert error.error_code is GenerationErrorCode.UNSAFE_CONFIG
        assert error.details["code"] == "mixed_hermes_route_unsupported"

    def test_generation_config_error_rejects_bare_mixed_hermes_route(self):
        from src.application.generation.ports import GenerationErrorCode

        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="shared-route",
            litellm_fallback_models=[],
            llm_model_list=[
                {
                    "model_name": "openai/shared-route",
                    "litellm_params": {
                        "model": "openai/hermes-agent",
                        "api_key": "sk-hermes-test-value",
                        "api_base": "http://127.0.0.1:8642/v1",
                    },
                    "model_info": {"hrs_channel": "hermes"},
                },
                {
                    "model_name": "openai/shared-route",
                    "litellm_params": {
                        "model": "openai/gpt-4o-mini",
                        "api_key": "sk-openai-test-value",
                    },
                },
            ],
            generation_backend="litellm",
            generation_fallback_backend="",
            llm_channel_config_issues=[],
            llm_blocks_legacy_fallback=False,
        )

        error = analyzer.get_generation_backend_config_error()

        assert error is not None
        assert error.error_code is GenerationErrorCode.UNSAFE_CONFIG
        assert error.details["code"] == "mixed_hermes_route_unsupported"

    def test_generation_config_error_rejects_mixed_hermes_fallback_route(self):
        from src.application.generation.ports import GenerationErrorCode

        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="openai/gpt-4o-mini",
            litellm_fallback_models=["shared-route"],
            llm_model_list=[
                {
                    "model_name": "shared-route",
                    "litellm_params": {
                        "model": "openai/hermes-agent",
                        "api_key": "sk-hermes-test-value",
                        "api_base": "http://127.0.0.1:8642/v1",
                    },
                    "model_info": {"hrs_channel": "hermes"},
                },
                {
                    "model_name": "shared-route",
                    "litellm_params": {
                        "model": "openai/gpt-4o-mini",
                        "api_key": "sk-openai-test-value",
                    },
                },
            ],
            generation_backend="litellm",
            generation_fallback_backend="",
            llm_channel_config_issues=[],
            llm_blocks_legacy_fallback=False,
        )

        error = analyzer.get_generation_backend_config_error()

        assert error is not None
        assert error.error_code is GenerationErrorCode.UNSAFE_CONFIG
        assert error.details["code"] == "mixed_hermes_route_unsupported"
        assert error.details["route_name"] == "shared-route"

    def test_generation_config_error_rejects_bare_mixed_hermes_fallback_route(self):
        from src.application.generation.ports import GenerationErrorCode

        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="openai/gpt-4o-mini",
            litellm_fallback_models=["shared-route"],
            llm_model_list=[
                {
                    "model_name": "openai/shared-route",
                    "litellm_params": {
                        "model": "openai/hermes-agent",
                        "api_key": "sk-hermes-test-value",
                        "api_base": "http://127.0.0.1:8642/v1",
                    },
                    "model_info": {"hrs_channel": "hermes"},
                },
                {
                    "model_name": "openai/shared-route",
                    "litellm_params": {
                        "model": "openai/gpt-4o-mini",
                        "api_key": "sk-openai-test-value",
                    },
                },
            ],
            generation_backend="litellm",
            generation_fallback_backend="",
            llm_channel_config_issues=[],
            llm_blocks_legacy_fallback=False,
        )

        error = analyzer.get_generation_backend_config_error()

        assert error is not None
        assert error.error_code is GenerationErrorCode.UNSAFE_CONFIG
        assert error.details["code"] == "mixed_hermes_route_unsupported"

    def test_explicit_invalid_hermes_fallback_with_valid_sibling_is_blocked_before_loop(self):
        from src.config import Config
        from src.application.analysis.analyzer import GeminiAnalyzer
        from src.application.generation.ports import GenerationError, GenerationErrorCode

        env = {
            "LLM_CHANNELS": "hermes,primary",
            "LLM_HERMES_API_KEY": "hermes-key",
            "LLM_HERMES_MODELS": "bad model",
            "LLM_PRIMARY_PROTOCOL": "openai",
            "LLM_PRIMARY_BASE_URL": "https://example.invalid/v1",
            "LLM_PRIMARY_API_KEY": "sibling-key",
            "LLM_PRIMARY_MODELS": "gpt-sibling",
            "OPENAI_API_KEY": "legacy-key",
            "LITELLM_MODEL": "openai/gpt-sibling",
            "LITELLM_FALLBACK_MODELS": "bad model",
        }

        with patch("src.config.settings.setup_env"), \
             patch.object(Config, "parse_litellm_yaml", return_value=[]), \
             patch.dict("os.environ", env, clear=True):
            config = Config._load_from_env()
            analyzer = GeminiAnalyzer(config=config)

        error = analyzer.get_generation_backend_config_error()
        assert error is not None
        assert error.error_code is GenerationErrorCode.UNSAFE_CONFIG
        assert error.details["code"] == "explicit_hermes_route_invalid"
        assert error.details["field"] == "LITELLM_FALLBACK_MODELS"
        assert analyzer.is_available() is False

        with patch("src.infrastructure.providers.analyzer_runtime.litellm.completion") as completion:
            with pytest.raises(GenerationError):
                analyzer._call_litellm("prompt", {"max_tokens": 4})
        completion.assert_not_called()

    def test_invalid_hermes_config_error_handles_canonicalize_value_error(self):
        from src.application.generation.ports import GenerationErrorCode

        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="bad hermes route",
            litellm_fallback_models=[],
            llm_model_list=[],
            generation_backend="litellm",
            generation_fallback_backend="",
            llm_channel_config_issues=[
                {
                    "field": "LLM_HERMES_MODELS",
                    "code": "invalid_model",
                    "message": "Hermes model IDs must be valid",
                }
            ],
            llm_blocks_legacy_fallback=True,
            llm_blocked_hermes_routes=["openai/hermes-agent"],
        )

        with patch("src.application.analysis.analyzer.canonicalize_hermes_model_ref", side_effect=ValueError("bad model")), \
             patch("src.infrastructure.providers.analyzer_runtime.litellm.completion") as completion:
            error = analyzer.get_generation_backend_config_error()

        assert error is not None
        assert error.error_code is GenerationErrorCode.UNSAFE_CONFIG
        assert error.details["code"] == "invalid_model"
        completion.assert_not_called()

    def test_call_litellm_falls_back_to_message_content_when_blocks_empty(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="openai/deepseek-chat",
            litellm_fallback_models=[],
            llm_model_list=[],
        )
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    content_blocks=[],
                    message=SimpleNamespace(content="message response"),
                )
            ],
            usage=None,
        )

        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=response):
            text, model_used, usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
            )

        assert text == "message response"
        assert model_used == "openai/deepseek-chat"
        _assert_no_provider_usage_hmac_only(usage)
        assert "message_count" not in usage
        assert "known_dynamic_marker_positions" not in usage

    def test_call_litellm_recovers_from_temperature_default_error(self):
        from src.infrastructure.generation.generation_params import clear_litellm_generation_param_recovery_cache

        clear_litellm_generation_param_recovery_cache()
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="openai/custom-default-temp",
            litellm_fallback_models=[],
            llm_model_list=[],
        )
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )
        calls = []

        def _dispatch(model, call_kwargs, **_kwargs):
            calls.append(dict(call_kwargs))
            if len(calls) == 1:
                raise RuntimeError(
                    "temperature=0.2 is unsupported. Only the default (1.0) value is supported."
                )
            return response

        with patch.object(analyzer, "_dispatch_litellm_completion", side_effect=_dispatch):
            text, model_used, usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
            )

        assert text == "ok"
        assert model_used == "openai/custom-default-temp"
        _assert_usage_contains(usage, {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})
        assert calls[0]["temperature"] == 0.2
        assert calls[1]["temperature"] == 1.0

    def test_call_litellm_keeps_user_temperature_for_non_kimi_fallback(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="openai/kimi-k2.6",
            litellm_fallback_models=["openai/gpt-4o-mini"],
            llm_model_list=[],
        )
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="fallback ok"))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )
        temperatures = []

        def fake_dispatch(model, call_kwargs, **kwargs):
            temperatures.append((model, call_kwargs["temperature"]))
            if model == "openai/kimi-k2.6":
                raise RuntimeError("primary failed")
            return response

        with patch.object(analyzer, "_dispatch_litellm_completion", side_effect=fake_dispatch):
            text, model_used, usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
            )

        assert text == "fallback ok"
        assert model_used == "openai/gpt-4o-mini"
        _assert_usage_contains(usage, {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})
        assert temperatures == [
            ("openai/kimi-k2.6", 1.0),
            ("openai/gpt-4o-mini", 0.2),
        ]

    def test_analyze_integrity_retry_keeps_progress_monotonic(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            gemini_request_delay=0,
            report_language="zh",
            litellm_model="gemini/gemini-2.0-flash",
            llm_temperature=0.2,
            report_integrity_enabled=True,
            report_integrity_retry=1,
        )

        from src.application.analysis.analyzer import AnalysisResult

        progress_updates = []
        first_result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=80,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="首轮结果",
        )
        second_result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=82,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="补全后结果",
        )

        with patch.object(analyzer, "is_available", return_value=True), \
             patch.object(analyzer, "_get_analysis_system_prompt", return_value="system"), \
             patch.object(analyzer, "_format_prompt", return_value="prompt"), \
             patch.object(
                 analyzer,
                 "_call_litellm",
                 side_effect=[
                     ("first response", "model-a", {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}),
                     ("second response", "model-a", {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}),
                 ],
             ), \
             patch.object(analyzer, "_parse_response", side_effect=[first_result, second_result]), \
             patch.object(analyzer, "_build_market_snapshot", return_value={}), \
             patch.object(
                 analyzer,
                 "_check_content_integrity",
                 side_effect=[(False, ["analysis_summary"]), (True, [])],
             ), \
             patch.object(analyzer, "_build_integrity_retry_prompt", return_value="retry prompt"), \
             patch.object(_usage_port(), "persist"):
            result = analyzer.analyze(
                {"code": "600519", "stock_name": "贵州茅台"},
                progress_callback=lambda progress, message: progress_updates.append((progress, message)),
            )

        assert result.analysis_summary == "补全后结果"
        assert [progress for progress, _ in progress_updates] == [68, 93, 94, 95]
        assert "补全重试" in progress_updates[2][1]
        assert "解析 JSON" in progress_updates[3][1]

    def test_parse_response_non_json_returns_failure(self):
        """_parse_response must return success=False when LLM output is not valid JSON."""
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(report_language="zh")

        from src.application.analysis.analyzer import GeminiAnalyzer

        result = GeminiAnalyzer._parse_response(analyzer, "这是一段纯文本分析，没有 JSON。", "600519", "贵州茅台")
        assert result.success is False
        assert result.error_message is not None
        assert result.code == "600519"

    def test_parse_response_malformed_json_returns_failure(self):
        """_parse_response must return success=False when JSON extraction fails."""
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(report_language="zh")

        from src.application.analysis.analyzer import GeminiAnalyzer

        malformed = "Here is the analysis: {broken json content without closing"
        result = GeminiAnalyzer._parse_response(analyzer, malformed, "AAPL", "Apple")
        assert result.success is False
        assert result.error_message is not None

    def test_json_parse_failure_triggers_fallback_model(self):
        """When the primary model returns non-JSON, _call_litellm must try the fallback model."""
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="provider/primary-model",
            litellm_fallback_models=["provider/fallback-model"],
            llm_model_list=[],
        )

        import json as _json
        valid_json = _json.dumps({"sentiment_score": 70, "trend_prediction": "看多"})
        dispatch_calls = []

        def fake_dispatch(model, call_kwargs, **kwargs):
            dispatch_calls.append(model)
            if "primary" in model:
                return SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content="这不是 JSON 格式的响应"))],
                    usage=None,
                )
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=valid_json))],
                usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            )

        with patch.object(analyzer, "_dispatch_litellm_completion", side_effect=fake_dispatch):
            text, model_used, usage = analyzer._call_litellm(
                "test prompt",
                {"max_tokens": 128, "temperature": 0.7},
                response_validator=analyzer._validate_json_response,
            )

        assert "primary" in dispatch_calls[0], "primary model should be tried first"
        assert len(dispatch_calls) == 2, "fallback model should be tried after primary JSON failure"
        assert "fallback" in model_used
        assert valid_json == text

    def test_all_models_invalid_json_raises_all_models_failed_error(self):
        """When all models return non-JSON, _AllModelsFailedError is raised with last_response_text."""
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="provider/primary-model",
            litellm_fallback_models=["provider/fallback-model"],
            llm_model_list=[],
        )

        from src.application.analysis.analyzer import _AllModelsFailedError

        def fake_dispatch(model, call_kwargs, **kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="这不是 JSON 格式的响应"))],
                usage=None,
            )

        with patch.object(analyzer, "_dispatch_litellm_completion", side_effect=fake_dispatch):
            with pytest.raises(_AllModelsFailedError) as exc_info:
                analyzer._call_litellm(
                    "test prompt",
                    {"max_tokens": 128, "temperature": 0.7},
                    response_validator=analyzer._validate_json_response,
                )

        assert exc_info.value.last_response_text == "这不是 JSON 格式的响应"


class AnalyzerRuntimePortWiringTestCase(_AnalyzerRuntimePortWiringTestCaseFixture):
    def test_get_analyzer_llm_port_fail_fast_when_unbound(self) -> None:
        import src.application.analysis.analyzer as analyzer_module

        original = analyzer_module._analyzer_llm_port
        try:
            analyzer_module._analyzer_llm_port = None
            with pytest.raises(RuntimeError):
                analyzer_module._get_analyzer_llm_port()
        finally:
            analyzer_module._analyzer_llm_port = original
