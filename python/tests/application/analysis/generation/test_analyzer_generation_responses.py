"""Tests for analyzer generation responses."""

from tests.application.analysis._market_analyzer_generate_text_support import (
    MagicMock,
    SimpleNamespace,
    _TestAnalyzerGenerateTextFixture,
    _assert_usage_contains,
    _llm_usage_hmac_env,
    analyzer_module,
    contextmanager,
    json,
    patch,
    pytest,
)


class TestAnalyzerGenerateText(_TestAnalyzerGenerateTextFixture):
    def test_generate_text_returns_llm_response(self):
        analyzer = self._make_analyzer()
        with patch.object(analyzer, "_call_litellm", return_value="市场分析报告") as mock_call:
            result = analyzer.generate_text("写一份复盘", max_tokens=1024, temperature=0.5)
            assert result == "市场分析报告"
            mock_call.assert_called_once_with(
                "写一份复盘",
                generation_config={"max_tokens": 1024, "temperature": 0.5},
            )

    @pytest.mark.parametrize(
        ("generation_backend", "executable_name"),
        [
            ("codex_cli", "codex"),
            ("claude_code_cli", "claude"),
            ("opencode_cli", "opencode"),
        ],
    )
    def test_local_cli_is_available_without_litellm_api_keys(self, generation_backend, executable_name):
        analyzer = self._make_analyzer()
        analyzer._litellm_available = False
        analyzer._router = None
        analyzer._config_override = SimpleNamespace(
            generation_backend=generation_backend,
            generation_fallback_backend="",
            generation_backend_timeout_seconds=300,
            generation_backend_max_output_bytes=1048576,
            generation_backend_max_concurrency=1,
            local_cli_backend_max_concurrency=1,
        )

        with patch("src.infrastructure.generation.local_cli_backend.shutil.which", return_value=f"/usr/bin/{executable_name}"), \
             patch("src.infrastructure.generation.local_cli_backend.os.access", return_value=True):
            assert analyzer.get_generation_backend_config_error() is None
            assert analyzer.is_available() is True

    def test_generate_text_default_params(self):
        analyzer = self._make_analyzer()
        with patch.object(analyzer, "_call_litellm", return_value="ok") as mock_call:
            analyzer.generate_text("hello")
            _, kwargs = mock_call.call_args
            gen_cfg = kwargs["generation_config"]
            assert gen_cfg["max_tokens"] == 2048
            assert gen_cfg["temperature"] == 0.7

    def test_call_litellm_stream_records_legacy_message_audit_for_actual_messages(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="gemini/gemini-2.0-flash",
            litellm_fallback_models=[],
            llm_model_list=[],
        )

        def stream_response():
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="ok"))],
                usage=SimpleNamespace(prompt_tokens=8, completion_tokens=1, total_tokens=9),
            )

        audit_context = {
            "language": "zh",
            "market_group": "cn",
            "analysis_mode": "stock_analysis",
            "dynamic_markers": [
                {"marker_name": "stock_code", "message_role": "user", "text": "600519"},
                {"marker_name": "quote", "message_role": "user", "text": "## 📈 技术面数据"},
            ],
        }

        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=stream_response()):
            text, model, usage = analyzer._call_litellm(
                "## 📊 股票基础信息\n| 股票代码 | **600519** |\n\n## 📈 技术面数据\n",
                {"max_tokens": 128, "temperature": 0.2},
                system_prompt="system prompt",
                stream=True,
                audit_context=audit_context,
            )

        assert text == "ok"
        assert model == "gemini/gemini-2.0-flash"
        _assert_usage_contains(usage, {"prompt_tokens": 8, "completion_tokens": 1, "total_tokens": 9})
        assert usage["language"] == "zh"
        assert usage["market_group"] == "cn"
        assert usage["analysis_mode"] == "stock_analysis"
        assert usage["provider"] == "gemini"
        assert usage["transport"] == "litellm"
        assert usage["message_count"] == 2
        markers = json.loads(usage["known_dynamic_marker_positions"])
        assert [marker["marker_name"] for marker in markers] == ["stock_code", "quote"]
        assert "600519" not in usage["known_dynamic_marker_positions"]

    @patch("src.infrastructure.providers.analyzer_runtime.litellm.Router")
    def test_analyzer_legacy_router_recovery_cache_is_scoped_by_api_base(self, mock_router):
        """Analyzer legacy recovery should not leak across same model different api_base."""
        from src.application.analysis.analyzer import call_litellm_with_param_recovery as real_call
        from src.infrastructure.generation.generation_params import clear_litellm_generation_param_recovery_cache

        clear_litellm_generation_param_recovery_cache()
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="analyzer ok"))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
        )
        strict_router = MagicMock()
        flex_router = MagicMock()
        strict_router.completion.side_effect = [
            RuntimeError("Unsupported parameter: temperature is not supported"),
            response,
        ]
        flex_router.completion.return_value = response
        mock_router.side_effect = [strict_router, flex_router]

        strict_cfg = SimpleNamespace(
            litellm_model="openai/shared-model",
            litellm_fallback_models=[],
            llm_model_list=[],
            llm_temperature=0.2,
            gemini_api_keys=[],
            anthropic_api_keys=[],
            openai_api_keys=["sk-strict-key-1", "sk-strict-key-2"],
            deepseek_api_keys=[],
            openai_base_url="https://strict.example/v1",
        )
        flex_cfg = SimpleNamespace(
            litellm_model="openai/shared-model",
            litellm_fallback_models=[],
            llm_model_list=[],
            llm_temperature=0.2,
            gemini_api_keys=[],
            anthropic_api_keys=[],
            openai_api_keys=["sk-flex-key-1", "sk-flex-key-2"],
            deepseek_api_keys=[],
            openai_base_url="https://flex.example/v1",
        )

        captured_model_lists = []

        def _fake_recovery(call, **kwargs):
            captured_model_lists.append(kwargs.get("model_list"))
            return real_call(call, **kwargs)

        import src.application.analysis.analyzer as analyzer_module
        from src.application.analysis.analyzer import GeminiAnalyzer

        with patch.object(analyzer_module, "call_litellm_with_param_recovery", side_effect=_fake_recovery):
            GeminiAnalyzer(config=strict_cfg)._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
            )
            GeminiAnalyzer(config=flex_cfg)._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
            )

        assert len(captured_model_lists) == 2
        strict_model_list = captured_model_lists[0]
        flex_model_list = captured_model_lists[1]
        assert strict_model_list is not None
        assert flex_model_list is not None
        assert all(
            item.get("litellm_params", {}).get("api_base") == "https://strict.example/v1"
            for item in strict_model_list
        )
        assert all(
            item.get("litellm_params", {}).get("api_base") == "https://flex.example/v1"
            for item in flex_model_list
        )
        assert strict_router.completion.call_args_list[0].kwargs["temperature"] == 0.2
        assert "temperature" not in strict_router.completion.call_args_list[1].kwargs
        assert flex_router.completion.call_args.kwargs["temperature"] == 0.2

    def test_call_litellm_stream_falls_back_to_non_stream_before_first_chunk(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="gemini/gemini-2.0-flash",
            litellm_fallback_models=[],
            llm_model_list=[],
        )

        def broken_stream():
            raise RuntimeError("stream unsupported")
            yield  # pragma: no cover

        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="full response"))],
            usage=SimpleNamespace(prompt_tokens=4, completion_tokens=5, total_tokens=9),
        )

        dispatch_calls = []

        def fake_dispatch(model, call_kwargs, **kwargs):
            dispatch_calls.append(call_kwargs.copy())
            if call_kwargs.get("stream"):
                return broken_stream()
            return response

        with patch.object(analyzer, "_dispatch_litellm_completion", side_effect=fake_dispatch):
            text, model, usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
                stream=True,
            )

        assert text == "full response"
        assert model == "gemini/gemini-2.0-flash"
        _assert_usage_contains(usage, {"prompt_tokens": 4, "completion_tokens": 5, "total_tokens": 9})
        assert len(dispatch_calls) == 2
        assert dispatch_calls[0]["stream"] is True
        assert "stream" not in dispatch_calls[1]

    def test_call_litellm_hermes_route_forces_non_stream_direct_client(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="openai/hermes-agent",
            litellm_fallback_models=[],
            llm_model_list=[
                {
                    "model_name": "openai/hermes-agent",
                    "litellm_params": {
                        "model": "openai/hermes-agent",
                        "api_key": "sk-hermes-test-value",
                        "api_base": "http://127.0.0.1:8642/v1",
                    },
                    "model_info": {"hrs_channel": "hermes"},
                }
            ],
            llm_temperature=0.0,
            generation_backend="litellm",
            generation_fallback_backend="litellm",
            llm_channel_config_issues=[],
            llm_blocks_legacy_fallback=False,
        )
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="OK"))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )
        seen_kwargs = {}

        @contextmanager
        def fake_no_proxy_client(**_kwargs):
            yield object()

        def fake_completion(**kwargs):
            seen_kwargs.update(kwargs)
            return response

        with patch("src.infrastructure.generation.hermes.open_hermes_no_proxy_client", side_effect=fake_no_proxy_client), \
             patch("src.infrastructure.providers.analyzer_runtime.litellm.completion", side_effect=fake_completion):
            text, model, _usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.0},
                stream=True,
            )

        assert text == "OK"
        assert model == "openai/hermes-agent"
        assert seen_kwargs["model"] == "openai/hermes-agent"
        assert seen_kwargs["stream"] is False
        assert "api_key" not in seen_kwargs
        assert "api_base" not in seen_kwargs
        assert "client" in seen_kwargs

    def test_invalid_hermes_with_valid_sibling_keeps_analyzer_available(self):
        from src.config import Config
        from src.application.analysis.analyzer import GeminiAnalyzer

        env = {
            "LLM_CHANNELS": "hermes,primary",
            "LLM_PRIMARY_PROTOCOL": "openai",
            "LLM_PRIMARY_BASE_URL": "https://example.invalid/v1",
            "LLM_PRIMARY_API_KEY": "sk-primary-test-value",
            "LLM_PRIMARY_MODELS": "gpt-sibling",
            "OPENAI_API_KEY": "sk-openai-test-value",
        }

        with patch("src.config.settings.setup_env"), \
             patch.object(Config, "parse_litellm_yaml", return_value=[]), \
             patch.dict("os.environ", env, clear=True):
            config = Config._load_from_env()
            analyzer = GeminiAnalyzer(config=config)

        assert config.litellm_model == "openai/gpt-sibling"
        assert "hermes-agent" in config.llm_blocked_hermes_routes
        assert "openai/hermes-agent" in config.llm_blocked_hermes_routes
        assert analyzer.is_available() is True
        assert analyzer.get_generation_backend_config_error() is None

    def test_explicit_invalid_hermes_primary_with_valid_sibling_is_blocked_before_completion(self):
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
            "LITELLM_MODEL": "bad model",
        }

        with patch("src.config.settings.setup_env"), \
             patch.object(Config, "parse_litellm_yaml", return_value=[]), \
             patch.dict("os.environ", env, clear=True):
            config = Config._load_from_env()
            analyzer = GeminiAnalyzer(config=config)

        assert "bad model" in config.llm_blocked_hermes_routes
        assert "openai/bad model" in config.llm_blocked_hermes_routes
        error = analyzer.get_generation_backend_config_error()
        assert error is not None
        assert error.error_code is GenerationErrorCode.UNSAFE_CONFIG
        assert error.details["code"] == "explicit_hermes_route_invalid"
        assert error.details["reason"] == "explicit_hermes_route_invalid"
        assert error.details["field"] == "LITELLM_MODEL"
        assert analyzer.is_available() is False

        with patch("src.infrastructure.providers.analyzer_runtime.litellm.completion") as completion:
            with pytest.raises(GenerationError):
                analyzer._call_litellm("prompt", {"max_tokens": 4})
        completion.assert_not_called()

    def test_call_litellm_minimax_reasoning_only_blocks_fall_back_to_message_content(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="openai/MiniMax-M3",
            litellm_fallback_models=[],
            llm_model_list=[],
        )
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    content_blocks=[
                        SimpleNamespace(type="thinking", text="Internal reasoning"),
                    ],
                    message=SimpleNamespace(content='{"sentiment_score": 72}'),
                )
            ],
            usage=None,
        )

        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=response):
            text, model_used, _usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
            )

        assert text == '{"sentiment_score": 72}'
        assert model_used == "openai/MiniMax-M3"

    def test_call_litellm_minimax_strips_leading_think_wrapper(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="openai/MiniMax-M3",
            litellm_fallback_models=[],
            llm_model_list=[],
        )
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    content_blocks=None,
                    message=SimpleNamespace(
                        content='<think>Internal reasoning</think>\n{"sentiment_score": 72}'
                    ),
                )
            ],
            usage=None,
        )

        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=response):
            text, model_used, _usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
                response_validator=analyzer._validate_json_response,
            )

        assert text == '{"sentiment_score": 72}'
        assert model_used == "openai/MiniMax-M3"

    def test_call_litellm_preserves_think_markup_inside_json_string(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="openai/MiniMax-M3",
            litellm_fallback_models=[],
            llm_model_list=[],
        )
        expected = '{"analysis_summary":"literal <think>text</think>"}'
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    content_blocks=None,
                    message=SimpleNamespace(content=expected),
                )
            ],
            usage=None,
        )

        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=response):
            text, model_used, _usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
                response_validator=analyzer._validate_json_response,
            )

        assert text == expected
        assert model_used == "openai/MiniMax-M3"

    def test_call_litellm_minimax_stream_ignores_reasoning_blocks(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="openai/MiniMax-M3",
            litellm_fallback_models=[],
            llm_model_list=[],
        )

        def stream_response():
            yield SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(
                            content=[
                                {"type": "reasoning", "text": "Internal reasoning"},
                                {"type": "text", "text": '{"sentiment_score": '},
                            ]
                        )
                    )
                ],
                usage=None,
            )
            yield SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(
                            content=[{"type": "text", "text": "72}"}]
                        )
                    )
                ],
                usage=None,
            )

        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=stream_response()):
            text, model_used, _usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
                stream=True,
                response_validator=analyzer._validate_json_response,
            )

        assert text == '{"sentiment_score": 72}'
        assert model_used == "openai/MiniMax-M3"

    def test_call_litellm_minimax_stream_strips_split_think_wrapper(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="openai/MiniMax-M3",
            litellm_fallback_models=[],
            llm_model_list=[],
        )

        def stream_response():
            for content in (
                "<thi",
                "nk>Internal reasoning</think>",
                '{"sentiment_score": ',
                "72}",
            ):
                yield SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content=content))],
                    usage=None,
                )

        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=stream_response()):
            text, model_used, _usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
                stream=True,
                response_validator=analyzer._validate_json_response,
            )

        assert text == '{"sentiment_score": 72}'
        assert model_used == "openai/MiniMax-M3"

    def test_call_litellm_normalizes_kimi_k26_temperature(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="openai/kimi-k2.6",
            litellm_fallback_models=[],
            llm_model_list=[],
        )
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=response) as mock_dispatch:
            text, model_used, usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
            )

        assert text == "ok"
        assert model_used == "openai/kimi-k2.6"
        _assert_usage_contains(usage, {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})
        call_kwargs = mock_dispatch.call_args.args[1]
        assert call_kwargs["temperature"] == 1.0

    def test_call_litellm_non_stream_records_legacy_message_audit_for_actual_messages(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="openai/gpt-4o-mini",
            litellm_fallback_models=[],
            llm_model_list=[],
        )
        prompt = (
            "# 决策仪表盘分析请求\n"
            "| 股票代码 | **600519** |\n"
            "| 股票名称 | **贵州茅台** |\n"
            "| 分析日期 | 2026-06-19 |\n\n"
            "## ✅ 分析任务\n"
            "请输出 JSON。"
        )
        fixed_rules_offset = prompt.index("## ✅ 分析任务")
        audit_context = {
            "language": "zh",
            "market_group": "cn",
            "analysis_mode": "stock_analysis",
            "dynamic_markers": [
                {"marker_name": "stock_code", "message_role": "user", "text": "600519"},
                {"marker_name": "stock_name", "message_role": "user", "text": "贵州茅台"},
                {"marker_name": "analysis_date", "message_role": "user", "text": "2026-06-19"},
            ],
        }
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=1, total_tokens=11),
        )

        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=response):
            text, model_used, usage = analyzer._call_litellm(
                prompt,
                {"max_tokens": 128, "temperature": 0.2},
                system_prompt="system prompt",
                audit_context=audit_context,
            )

        assert text == "ok"
        assert model_used == "openai/gpt-4o-mini"
        _assert_usage_contains(usage, {"prompt_tokens": 10, "completion_tokens": 1, "total_tokens": 11})
        assert usage["provider"] == "openai"
        assert usage["message_count"] == 2
        markers = {
            marker["marker_name"]: marker
            for marker in json.loads(usage["known_dynamic_marker_positions"])
        }
        for marker_name in ("stock_code", "stock_name", "analysis_date"):
            assert markers[marker_name]["message_role"] == "user"
            assert markers[marker_name]["char_offset"] < fixed_rules_offset
        assert "600519" not in usage["known_dynamic_marker_positions"]
        assert "贵州茅台" not in usage["known_dynamic_marker_positions"]
        assert "2026-06-19" not in usage["known_dynamic_marker_positions"]

    def test_call_litellm_normalizes_kimi_k26_temperature_for_yaml_alias(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="kimi_router",
            litellm_fallback_models=[],
            llm_model_list=[
                {
                    "model_name": "kimi_router",
                    "litellm_params": {"model": "openai/kimi-k2.6"},
                }
            ],
        )
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=response) as mock_dispatch:
            text, model_used, usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
            )

        assert text == "ok"
        assert model_used == "kimi_router"
        _assert_usage_contains(usage, {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})
        call_kwargs = mock_dispatch.call_args.args[1]
        assert call_kwargs["temperature"] == 1.0

    def test_call_litellm_normalizes_kimi_k26_temperature_for_non_thinking_yaml_alias(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="kimi_router",
            litellm_fallback_models=[],
            llm_model_list=[
                {
                    "model_name": "kimi_router",
                    "litellm_params": {
                        "model": "openai/kimi-k2.6",
                        "extra_body": {"thinking": {"type": "disabled"}},
                    },
                }
            ],
        )
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=response) as mock_dispatch:
            text, model_used, usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
            )

        assert text == "ok"
        assert model_used == "kimi_router"
        _assert_usage_contains(usage, {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})
        call_kwargs = mock_dispatch.call_args.args[1]
        assert call_kwargs["temperature"] == 0.6

    def test_call_litellm_omits_temperature_for_gpt5_family(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="openai/gpt5.5-ferr",
            litellm_fallback_models=[],
            llm_model_list=[],
        )
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=response) as mock_dispatch:
            text, model_used, usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
            )

        assert text == "ok"
        assert model_used == "openai/gpt5.5-ferr"
        _assert_usage_contains(usage, {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})
        call_kwargs = mock_dispatch.call_args.args[1]
        assert "temperature" not in call_kwargs

    def test_parse_response_valid_json_returns_success(self):
        """_parse_response must return success=True when LLM output contains valid JSON."""
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(report_language="zh")

        from src.application.analysis.analyzer import GeminiAnalyzer
        import json

        valid_response = json.dumps({
            "sentiment_score": 75,
            "trend_prediction": "看多",
            "operation_advice": "持有",
            "analysis_summary": "测试分析",
        })
        result = GeminiAnalyzer._parse_response(analyzer, valid_response, "600519", "贵州茅台")
        assert result.success is True
        assert result.error_message is None
