"""Tests for analyzer generation usage."""

from tests.application.analysis._market_analyzer_generate_text_support import (
    SimpleNamespace,
    _TestAnalyzerGenerateTextFixture,
    _TestGenerationUsagePersistPortFixture,
    _assert_usage_contains,
    _llm_usage_hmac_env,
    _usage_port,
    analyzer_module,
    json,
    patch,
)


class TestAnalyzerGenerateText(_TestAnalyzerGenerateTextFixture):
    def test_generate_text_does_not_persist_unavailable_usage(self):
        analyzer = self._make_analyzer()
        usage = {
            "usage_available": False,
            "usage_source": "unavailable",
            "backend": "codex_cli",
        }
        with patch.object(analyzer, "_call_litellm", return_value=("复盘", "codex_cli", usage)), \
             patch.object(_usage_port(), "persist") as mock_persist:
            result = analyzer.generate_text("写一份复盘")

        assert result == "复盘"
        mock_persist.assert_not_called()

    def test_analyze_does_not_persist_unavailable_usage(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            generation_backend="codex_cli",
            generation_fallback_backend="",
            generation_backend_timeout_seconds=300,
            generation_backend_max_output_bytes=1048576,
            generation_backend_max_concurrency=1,
            local_cli_backend_max_concurrency=1,
            litellm_model="",
            gemini_request_delay=0,
            report_language="zh",
            llm_temperature=0.7,
            report_integrity_enabled=False,
            report_integrity_retry=0,
        )
        response_text = json.dumps({
            "sentiment_score": 70,
            "trend_prediction": "看多",
            "operation_advice": "持有",
            "analysis_summary": "测试",
        })
        usage = {
            "usage_available": False,
            "usage_source": "unavailable",
            "backend": "codex_cli",
        }

        with patch.object(analyzer, "get_generation_backend_config_error", return_value=None), \
             patch.object(analyzer, "is_available", return_value=True), \
             patch.object(analyzer, "_get_analysis_system_prompt", return_value="system"), \
             patch.object(analyzer, "_get_skill_prompt_sections", return_value=(None, None, True)), \
             patch.object(analyzer, "_format_prompt", return_value="prompt"), \
             patch.object(analyzer, "_call_litellm", return_value=(response_text, "codex_cli", usage)), \
             patch.object(analyzer, "_build_market_snapshot", return_value={}), \
             patch.object(_usage_port(), "persist") as mock_persist:
            result = analyzer.analyze({"code": "600519", "stock_name": "贵州茅台"})

        assert result.success is True
        mock_persist.assert_not_called()

    def test_call_litellm_stream_reads_private_hidden_usage_best_effort(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="openai/gpt-4o-mini",
            litellm_fallback_models=[],
            llm_model_list=[],
        )

        def stream_response():
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="abc"))],
                usage=None,
            )
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content=""))],
                usage=None,
                _hidden_params={
                    "usage": SimpleNamespace(prompt_tokens=11, completion_tokens=2, total_tokens=13)
                },
            )

        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=stream_response()):
            text, model, usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
                stream=True,
            )

        assert text == "abc"
        assert model == "openai/gpt-4o-mini"
        _assert_usage_contains(usage, {"prompt_tokens": 11, "completion_tokens": 2, "total_tokens": 13})

    def test_prompt_cache_telemetry_disabled_filters_cache_fields_from_analyzer_usage(self):
        from src.application.analysis.analyzer import GeminiAnalyzer

        cfg = SimpleNamespace(
            litellm_model="openai/gpt-4o",
            litellm_fallback_models=[],
            llm_model_list=[],
            llm_temperature=0.7,
            gemini_api_keys=[],
            anthropic_api_keys=[],
            openai_api_keys=["sk-openai-test"],
            deepseek_api_keys=[],
            openai_base_url=None,
            llm_prompt_cache_telemetry_enabled=False,
            llm_prompt_cache_hints_enabled=False,
            llm_prompt_cache_diagnostics_level="off",
        )
        analyzer = GeminiAnalyzer(config=cfg)

        def _fake_recovery(call, **kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
                usage={
                    "prompt_tokens": 1200,
                    "completion_tokens": 1,
                    "total_tokens": 1201,
                    "prompt_tokens_details": {"cached_tokens": 1000},
                },
            )

        with patch("src.application.analysis.analyzer.call_litellm_with_param_recovery", side_effect=_fake_recovery):
            _, _, usage = analyzer._call_litellm("dynamic prompt", {"max_tokens": 128, "temperature": 0.7})

        assert usage["prompt_tokens"] == 1200
        assert usage["completion_tokens"] == 1
        assert usage["total_tokens"] == 1201
        assert "provider_usage_json" not in usage
        assert "normalized_cache_read_tokens" not in usage
        assert "cache_capability" not in usage
        assert usage["messages_hmac"]

    def test_prompt_cache_telemetry_disabled_marks_no_usage_response_for_storage(self):
        from src.application.analysis.analyzer import GeminiAnalyzer

        cfg = SimpleNamespace(
            litellm_model="openai/gpt-4o",
            litellm_fallback_models=[],
            llm_model_list=[],
            llm_temperature=0.7,
            gemini_api_keys=[],
            anthropic_api_keys=[],
            openai_api_keys=["sk-openai-test"],
            deepseek_api_keys=[],
            openai_base_url=None,
            llm_prompt_cache_telemetry_enabled=False,
            llm_prompt_cache_hints_enabled=False,
            llm_prompt_cache_diagnostics_level="off",
        )
        analyzer = GeminiAnalyzer(config=cfg)

        def _fake_recovery(call, **kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
                usage=None,
            )

        with patch("src.application.analysis.analyzer.call_litellm_with_param_recovery", side_effect=_fake_recovery):
            text, _, usage = analyzer._call_litellm("dynamic prompt", {"max_tokens": 128, "temperature": 0.7})

        assert text == "ok"
        assert getattr(usage, "prompt_cache_telemetry_disabled", False)
        assert "cache_capability" not in usage
        assert "cache_eligibility" not in usage
        assert "cache_observation" not in usage
        assert usage["messages_hmac"]

    def test_call_litellm_system_hmac_distinguishes_language_and_market_prompt(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="openai/gpt-4o-mini",
            litellm_fallback_models=[],
            llm_model_list=[],
        )
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=1, total_tokens=11),
        )

        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=response):
            _, _, zh_usage = analyzer._call_litellm(
                "same user prompt 600519",
                {"max_tokens": 128, "temperature": 0.2},
                system_prompt="system prompt zh cn",
                audit_context={
                    "language": "zh",
                    "market_group": "cn",
                    "analysis_mode": "stock_analysis",
                    "dynamic_markers": [
                        {"marker_name": "stock_code", "message_role": "user", "text": "600519"},
                    ],
                },
            )
            _, _, en_usage = analyzer._call_litellm(
                "same user prompt 600519",
                {"max_tokens": 128, "temperature": 0.2},
                system_prompt="system prompt en us",
                audit_context={
                    "language": "en",
                    "market_group": "us",
                    "analysis_mode": "stock_analysis",
                    "dynamic_markers": [
                        {"marker_name": "stock_code", "message_role": "user", "text": "600519"},
                    ],
                },
            )

        assert zh_usage["system_message_hmac"] != en_usage["system_message_hmac"]
        assert zh_usage["messages_hmac"] != en_usage["messages_hmac"]
        assert zh_usage["user_message_hmac"] == en_usage["user_message_hmac"]
        assert zh_usage["market_group"] == "cn"
        assert en_usage["market_group"] == "us"

    def test_call_litellm_resolves_anthropic_alias_for_usage_normalization(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="claude-router",
            litellm_fallback_models=[],
            llm_model_list=[
                {
                    "model_name": "claude-router",
                    "litellm_params": {"model": "anthropic/claude-sonnet-test"},
                }
            ],
        )
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=SimpleNamespace(
                input_tokens=100,
                output_tokens=30,
                cache_read_input_tokens=10,
                cache_creation_input_tokens=20,
            ),
        )

        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=response):
            text, model_used, usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
            )

        assert text == "ok"
        assert model_used == "claude-router"
        assert usage["prompt_tokens"] == 130
        assert usage["completion_tokens"] == 30
        assert usage["total_tokens"] == 160
        assert usage["normalized_cache_read_tokens"] == 10
        assert usage["normalized_cache_write_tokens"] == 20
        assert usage["cache_observation"] == "read_and_write"

    def test_call_litellm_uses_openai_wire_model_for_alias_usage_threshold(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="fast",
            litellm_fallback_models=[],
            llm_model_list=[
                {
                    "model_name": "fast",
                    "litellm_params": {"model": "openai/gpt-4o"},
                }
            ],
        )
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=SimpleNamespace(
                prompt_tokens=500,
                completion_tokens=20,
                total_tokens=520,
                prompt_tokens_details={"cached_tokens": 0},
            ),
        )

        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=response):
            text, model_used, usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
            )

        assert text == "ok"
        assert model_used == "fast"
        assert usage["provider_min_cache_tokens"] == 1024
        assert usage["cache_capability"] == "supported"
        assert usage["cache_eligibility"] == "below_threshold"
        assert usage["cache_observation"] == "unknown"
        assert usage["normalized_cache_read_tokens"] == 0
        assert usage["normalized_cache_eligible_input_tokens"] is None
        assert usage["normalized_cache_hit_ratio"] is None

    def test_call_litellm_stream_resolves_glm_alias_for_usage_normalization(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="glm-router",
            litellm_fallback_models=[],
            llm_model_list=[
                {
                    "model_name": "glm-router",
                    "litellm_params": {"model": "zhipu/glm-4.5"},
                }
            ],
        )

        def stream_response():
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="ok"))],
                usage=SimpleNamespace(
                    prompt_tokens=1200,
                    completion_tokens=80,
                    total_tokens=1280,
                    prompt_tokens_details={"cached_tokens": 1200},
                ),
            )

        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=stream_response()):
            text, model_used, usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
                stream=True,
            )

        assert text == "ok"
        assert model_used == "glm-router"
        assert usage["normalized_cache_read_tokens"] == 1200
        assert usage["cache_capability"] == "supported"
        assert usage["cache_observation"] == "full_hit"

    def test_call_litellm_stream_uses_openai_wire_model_for_alias_usage_threshold(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="fast",
            litellm_fallback_models=[],
            llm_model_list=[
                {
                    "model_name": "fast",
                    "litellm_params": {"model": "openai/gpt-4o"},
                }
            ],
        )

        def stream_response():
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="ok"))],
                usage=SimpleNamespace(
                    prompt_tokens=500,
                    completion_tokens=20,
                    total_tokens=520,
                    prompt_tokens_details={"cached_tokens": 0},
                ),
            )

        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=stream_response()):
            text, model_used, usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
                stream=True,
            )

        assert text == "ok"
        assert model_used == "fast"
        assert usage["provider_min_cache_tokens"] == 1024
        assert usage["cache_capability"] == "supported"
        assert usage["cache_eligibility"] == "below_threshold"
        assert usage["cache_observation"] == "unknown"
        assert usage["normalized_cache_read_tokens"] == 0
        assert usage["normalized_cache_eligible_input_tokens"] is None
        assert usage["normalized_cache_hit_ratio"] is None

    def test_analyze_persists_provider_usage_from_private_stream_hidden_usage_best_effort(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            gemini_request_delay=0,
            report_language="zh",
            litellm_model="openai/gpt-4o-mini",
            litellm_fallback_models=[],
            llm_model_list=[],
            llm_temperature=0.2,
            report_integrity_enabled=False,
            report_integrity_retry=0,
        )

        from src.application.analysis.analyzer import AnalysisResult

        parsed_result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=80,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="分析结果",
        )

        def stream_response():
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content='{"sentiment_score":80}'))],
                usage=None,
            )
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content=""))],
                usage=None,
                _hidden_params={
                    "usage": SimpleNamespace(prompt_tokens=11, completion_tokens=2, total_tokens=13)
                },
            )

        with patch.object(analyzer, "is_available", return_value=True), \
             patch.object(analyzer, "_get_analysis_system_prompt", return_value="system"), \
             patch.object(analyzer, "_get_skill_prompt_sections", return_value=("RSI skill raw", "Default skill policy", False)), \
             patch.object(analyzer, "_format_prompt", return_value="prompt"), \
             patch.object(analyzer, "_validate_json_response"), \
             patch.object(analyzer, "_dispatch_litellm_completion", return_value=stream_response()), \
             patch.object(analyzer, "_parse_response", return_value=parsed_result), \
             patch.object(analyzer, "_build_market_snapshot", return_value={}), \
             patch.object(_usage_port(), "persist") as mock_usage:
            result = analyzer.analyze({"code": "600519", "stock_name": "贵州茅台"})

        assert result.analysis_summary == "分析结果"
        mock_usage.assert_called_once()
        usage_arg, model_arg = mock_usage.call_args[0]
        assert model_arg == "openai/gpt-4o-mini"
        _assert_usage_contains(usage_arg, {"prompt_tokens": 11, "completion_tokens": 2, "total_tokens": 13})
        assert usage_arg["language"] == "zh"
        assert usage_arg["market_group"] == "cn"
        assert usage_arg["analysis_mode"] == "stock_analysis"
        assert usage_arg["legacy_prompt_mode"] == "skill_aware"
        assert usage_arg["skill_config_hmac"] and len(usage_arg["skill_config_hmac"]) == 64
        assert usage_arg["provider"] == "openai"
        assert usage_arg["transport"] == "litellm"
        assert usage_arg["message_count"] == 2
        assert json.loads(usage_arg["known_dynamic_marker_positions"]) == []
        assert mock_usage.call_args.kwargs == {"call_type": "analysis", "stock_code": "600519"}


class TestGenerationUsagePersistPort(_TestGenerationUsagePersistPortFixture):
    def test_adapter_persist_delegates_to_storage(self) -> None:
        from src.infrastructure.generation.adapters.port_usage import GenerationUsageAdapter

        usage = {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8}
        with patch("src.storage.persist_llm_usage") as mock_persist:
            GenerationUsageAdapter().persist(
                usage,
                "openai/gpt-4o-mini",
                call_type="analysis",
                stock_code="600519",
            )

        mock_persist.assert_called_once_with(
            usage,
            "openai/gpt-4o-mini",
            call_type="analysis",
            stock_code="600519",
        )

    def test_analyzer_usage_write_has_no_storage_import(self) -> None:
        """分析器写用量必须走生成链路端口，不得回退为 application→storage 直连。"""
        from pathlib import Path

        source = Path(analyzer_module.__file__).read_text(encoding="utf-8")
        assert "from src.storage" not in source
        assert not hasattr(analyzer_module, "persist_llm_usage")
