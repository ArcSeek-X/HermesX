"""Tests for analyzer generation prompts."""

from tests.application.analysis._market_analyzer_generate_text_support import (
    SimpleNamespace,
    _TestAnalyzerGenerateTextFixture,
    _assert_usage_contains,
    _llm_usage_hmac_env,
    _usage_port,
    json,
    patch,
)


class TestAnalyzerGenerateText(_TestAnalyzerGenerateTextFixture):
    def test_legacy_audit_marker_specs_use_language_and_optional_context(self):
        from src.application.analysis.analyzer import _legacy_audit_marker_specs

        zh_markers = _legacy_audit_marker_specs(
            {"date": "2026-06-19"},
            code="600519",
            stock_name="贵州茅台",
            report_language="zh",
            news_context="news",
            analysis_context_pack_summary="pack summary",
        )
        zh_by_name = {marker["marker_name"]: marker for marker in zh_markers}

        assert zh_by_name["stock_code"]["text"] == "600519"
        assert zh_by_name["stock_name"]["text"] == "贵州茅台"
        assert zh_by_name["analysis_date"]["text"] == "2026-06-19"
        assert zh_by_name["market_phase"]["text"] == "## 市场阶段上下文"
        assert zh_by_name["daily_market_context"]["text"] == "## 大盘环境摘要"
        assert zh_by_name["analysis_context_pack"]["text"] == "pack summary"
        assert zh_by_name["quote"]["text"] == "## 📈 技术面数据"
        assert zh_by_name["news_context"]["text"] == "## 📰 舆情情报"
        assert {marker["message_role"] for marker in zh_markers} == {"user"}

        en_markers = _legacy_audit_marker_specs(
            {"date": ""},
            code="AAPL",
            stock_name="Apple",
            report_language="en",
            news_context=None,
            analysis_context_pack_summary=None,
        )
        en_by_name = {marker["marker_name"]: marker for marker in en_markers}

        assert en_by_name["market_phase"]["text"] == "## Market Phase Context"
        assert en_by_name["daily_market_context"]["text"] == "## Daily Market Context"
        assert "analysis_date" not in en_by_name
        assert "analysis_context_pack" not in en_by_name
        assert "news_context" not in en_by_name

    def test_call_litellm_stream_aggregates_chunks_and_reports_progress(self):
        analyzer = self._make_analyzer()
        analyzer._config_override = SimpleNamespace(
            litellm_model="gemini/gemini-2.0-flash",
            litellm_fallback_models=[],
            llm_model_list=[],
        )

        def stream_response():
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="abc"))],
                usage=None,
            )
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="def"))],
                usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
            )

        progress_updates = []

        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=stream_response()):
            text, model, usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
                stream=True,
                stream_progress_callback=progress_updates.append,
            )

        assert text == "abcdef"
        assert model == "gemini/gemini-2.0-flash"
        _assert_usage_contains(usage, {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3})
        assert progress_updates == [3, 6]

    def test_prompt_cache_hints_disabled_does_not_change_analyzer_request_shape(self):
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
            llm_prompt_cache_telemetry_enabled=True,
            llm_prompt_cache_hints_enabled=False,
            llm_prompt_cache_diagnostics_level="off",
        )
        analyzer = GeminiAnalyzer(config=cfg)
        captured = {}

        def _fake_recovery(call, **kwargs):
            captured["call_kwargs"] = kwargs["call_kwargs"]
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
                usage={"prompt_tokens": 10, "completion_tokens": 1, "total_tokens": 11},
            )

        with patch("src.application.analysis.analyzer.call_litellm_with_param_recovery", side_effect=_fake_recovery):
            text, _, _ = analyzer._call_litellm("dynamic prompt", {"max_tokens": 128, "temperature": 0.7})

        assert text == "ok"
        call_kwargs = captured["call_kwargs"]
        assert "prompt_cache_key" not in call_kwargs
        assert call_kwargs["messages"] == [
            {"role": "system", "content": analyzer.TEXT_SYSTEM_PROMPT},
            {"role": "user", "content": "dynamic prompt"},
        ]

    def test_call_litellm_preserves_anthropic_litellm_prompt_tokens_without_input_tokens(self):
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
                prompt_tokens=100,
                completion_tokens=20,
                total_tokens=120,
                cache_read_input_tokens=0,
                cache_creation_input_tokens=0,
            ),
        )

        with patch.object(analyzer, "_dispatch_litellm_completion", return_value=response):
            text, model_used, usage = analyzer._call_litellm(
                "prompt",
                {"max_tokens": 128, "temperature": 0.2},
            )

        assert text == "ok"
        assert model_used == "claude-router"
        assert usage["prompt_tokens"] == 100
        assert usage["completion_tokens"] == 20
        assert usage["total_tokens"] == 120
        assert usage["normalized_prompt_tokens"] == 100
        assert usage["normalized_uncached_input_tokens"] == 100
        assert usage["cache_observation"] == "zero_hit"
        assert usage["messages_hmac"] and len(usage["messages_hmac"]) == 64

    def test_analyze_records_marker_positions_from_real_prompt_format(self):
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
            news_max_age_days=3,
            news_strategy_profile="short",
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
                usage=SimpleNamespace(prompt_tokens=42, completion_tokens=3, total_tokens=45),
            )

        context = {
            "code": "600519",
            "stock_name": "贵州茅台",
            "date": "2026-06-19",
            "today": {
                "close": 1500,
                "open": 1490,
                "high": 1510,
                "low": 1480,
                "pct_chg": 1.2,
                "volume": 100000,
                "amount": 150000000,
            },
            "market_phase_context": {
                "phase": "intraday",
                "is_partial_bar": False,
            },
            "daily_market_context": {
                "summary": "市场偏谨慎，等待量能确认。",
                "region": "cn",
                "trade_date": "2026-06-19",
            },
        }

        with patch.object(analyzer, "is_available", return_value=True), \
             patch.object(analyzer, "_get_analysis_system_prompt", return_value="system"), \
             patch.object(analyzer, "_get_skill_prompt_sections", return_value=("RSI skill raw", "Default skill policy", False)), \
             patch.object(analyzer, "_validate_json_response"), \
             patch.object(analyzer, "_dispatch_litellm_completion", return_value=stream_response()), \
             patch.object(analyzer, "_parse_response", return_value=parsed_result), \
             patch.object(analyzer, "_build_market_snapshot", return_value={}), \
             patch.object(_usage_port(), "persist") as mock_usage:
            result = analyzer.analyze(
                context,
                news_context="2026-06-18 贵州茅台发布经营公告。",
                analysis_context_pack_summary="## 分析上下文包\n- 估值处于中性区间。",
            )

        assert result.analysis_summary == "分析结果"
        mock_usage.assert_called_once()
        usage_arg, _ = mock_usage.call_args[0]
        markers = {
            marker["marker_name"]: marker
            for marker in json.loads(usage_arg["known_dynamic_marker_positions"])
        }
        for marker_name in (
            "stock_code",
            "stock_name",
            "analysis_date",
            "market_phase",
            "daily_market_context",
            "analysis_context_pack",
            "quote",
            "news_context",
        ):
            assert marker_name in markers
            assert markers[marker_name]["message_role"] == "user"
            assert isinstance(markers[marker_name]["char_offset"], int)
            assert markers[marker_name]["char_offset"] >= 0
        assert usage_arg["legacy_prompt_mode"] == "skill_aware"
        assert usage_arg["skill_config_hmac"] and len(usage_arg["skill_config_hmac"]) == 64
        assert "600519" not in usage_arg["known_dynamic_marker_positions"]
        assert "贵州茅台" not in usage_arg["known_dynamic_marker_positions"]
        assert "2026-06-19" not in usage_arg["known_dynamic_marker_positions"]
