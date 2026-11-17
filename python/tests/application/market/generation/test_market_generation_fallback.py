"""Tests for market generation fallback."""

from tests.application.analysis._market_analyzer_generate_text_support import (
    SimpleNamespace,
    _TestMarketAnalyzerBypassFixFixture,
    _llm_usage_hmac_env,
    patch,
    pytest,
)


class TestMarketAnalyzerBypassFix(_TestMarketAnalyzerBypassFixFixture):
    def test_generate_text_none_falls_back_to_template(self):
        """generate_market_review() falls back to template when generate_text returns None."""
        from src.application.market.market_analyzer import MarketOverview, MarketIndex

        ma = self._make_market_analyzer_with_mock_generate_text(return_value=None)
        overview = MarketOverview(
            date="2026-03-05",
            indices=[
                MarketIndex(
                    code="000001",
                    name="上证指数",
                    current=3300.0,
                    change=5.0,
                    change_pct=0.15,
                )
            ],
        )
        result = ma.generate_market_review(overview, [])
        assert isinstance(result, str) and len(result) > 0
        ma.analyzer.generate_text.assert_called_once()

    def test_generation_backend_config_error_does_not_template_fallback(self):
        from src.application.generation.ports import GenerationError
        from src.application.market.market_analyzer import MarketOverview, MarketIndex

        ma = self._make_market_analyzer_with_mock_generate_text(return_value=None)
        ma.analyzer._config_override.generation_backend = "codex"
        overview = MarketOverview(
            date="2026-03-05",
            indices=[
                MarketIndex(
                    code="000001",
                    name="上证指数",
                    current=3300.0,
                    change=5.0,
                    change_pct=0.15,
                )
            ],
        )

        with patch.object(ma, "_generate_template_review", wraps=ma._generate_template_review) as template_review, \
             patch("src.application.market.market_analyzer.record_llm_run") as mock_record_llm_run:
            with pytest.raises(GenerationError) as exc_info:
                ma.generate_market_review(overview, [])

        assert exc_info.value.details["field"] == "GENERATION_BACKEND"
        assert exc_info.value.details["requested_backend"] == "codex"
        template_review.assert_not_called()
        ma.analyzer.generate_text.assert_not_called()
        mock_record_llm_run.assert_called_once()
        diagnostic = mock_record_llm_run.call_args.kwargs
        assert diagnostic["success"] is False
        assert diagnostic["call_type"] == "market_review"
        assert diagnostic["error_type"] == "GenerationError"
        assert "backend_not_configured" in str(diagnostic["error_message"])

    def test_local_backend_execution_error_does_not_template_fallback(self):
        from src.application.generation.ports import GenerationError, GenerationErrorCode
        from src.application.market.market_analyzer import MarketOverview, MarketIndex

        ma = self._make_market_analyzer_with_mock_generate_text(return_value=None)
        ma.analyzer.generate_text.side_effect = GenerationError(
            error_code=GenerationErrorCode.COMMAND_NOT_FOUND,
            stage="configuration",
            retryable=False,
            fallbackable=True,
            backend="codex_cli",
            provider="codex_cli",
            details={"reason": "executable_not_found"},
        )
        overview = MarketOverview(
            date="2026-03-05",
            indices=[
                MarketIndex(
                    code="000001",
                    name="上证指数",
                    current=3300.0,
                    change=5.0,
                    change_pct=0.15,
                )
            ],
        )

        with patch.object(ma, "_generate_template_review", wraps=ma._generate_template_review) as template_review:
            with pytest.raises(GenerationError) as exc_info:
                ma.generate_market_review(overview, [])

        assert exc_info.value.error_code is GenerationErrorCode.COMMAND_NOT_FOUND
        template_review.assert_not_called()

    def test_generation_backend_config_error_without_analyzer_does_not_template_fallback(self):
        from src.application.generation.ports import GenerationError
        from src.application.market.market_analyzer import MarketOverview, MarketIndex

        overview = MarketOverview(
            date="2026-03-05",
            indices=[
                MarketIndex(
                    code="000001",
                    name="上证指数",
                    current=3300.0,
                    change=5.0,
                    change_pct=0.15,
                )
            ],
        )
        cases = [
            ("generation_backend", "GENERATION_BACKEND"),
            ("generation_fallback_backend", "GENERATION_FALLBACK_BACKEND"),
        ]

        for attr_name, expected_field in cases:
            ma = self._make_market_analyzer_with_mock_generate_text(return_value=None)
            ma.analyzer = None
            ma.config.generation_backend = "litellm"
            ma.config.generation_fallback_backend = "litellm"
            setattr(ma.config, attr_name, "codex")

            with patch.object(ma, "_generate_template_review", wraps=ma._generate_template_review) as template_review, \
                 patch("src.application.market.market_analyzer.record_llm_run") as mock_record_llm_run:
                with pytest.raises(GenerationError) as exc_info:
                    ma.generate_market_review(overview, [])

            assert exc_info.value.details["field"] == expected_field
            assert exc_info.value.details["requested_backend"] == "codex"
            template_review.assert_not_called()
            mock_record_llm_run.assert_called_once()

    def test_generate_template_review_uses_jp_title_for_english_fallback(self):
        from src.domain.market.profile import JP_PROFILE
        from src.domain.market.strategy import get_market_strategy_blueprint
        from src.application.market.market_analyzer import MarketOverview, MarketIndex

        ma = self._make_market_analyzer_with_mock_generate_text(return_value=None)
        ma.region = "jp"
        ma.profile = JP_PROFILE
        ma.strategy = get_market_strategy_blueprint("jp")
        ma.config.report_language = "en"
        overview = MarketOverview(
            date="2026-03-05",
            indices=[
                MarketIndex(
                    code="N225",
                    name="Nikkei 225",
                    current=39000.0,
                    change=120.0,
                    change_pct=0.31,
                )
            ],
        )

        result = ma.generate_market_review(overview, [])

        assert "Japan Market Recap" in result
        assert "Today's Japan market showed" in result
        assert "A-share Market Recap" not in result

    @pytest.mark.parametrize(
        ("region", "profile_name", "index_code", "index_name", "english_title", "zh_label"),
        [
            ("jp", "JP_PROFILE", "N225", "Nikkei 225", "Japan Market Recap", "今日日股市场整体呈现"),
            ("kr", "KR_PROFILE", "KS11", "KOSPI", "Korea Market Recap", "今日韩股市场整体呈现"),
        ],
    )
    def test_generate_template_review_uses_jp_kr_labels_for_no_llm_fallback(
        self, region, profile_name, index_code, index_name, english_title, zh_label
    ):
        import src.domain.market.profile as market_profile
        from src.domain.market.strategy import get_market_strategy_blueprint
        from src.application.market.market_analyzer import MarketOverview, MarketIndex

        ma = self._make_market_analyzer_with_mock_generate_text(return_value=None)
        ma.region = region
        ma.profile = getattr(market_profile, profile_name)
        ma.strategy = get_market_strategy_blueprint(region)
        overview = MarketOverview(
            date="2026-03-05",
            indices=[
                MarketIndex(
                    code=index_code,
                    name=index_name,
                    current=30000.0,
                    change=120.0,
                    change_pct=0.4,
                )
            ],
        )

        ma.config.report_language = "en"
        english_result = ma.generate_market_review(overview, [])
        assert f"## 2026-03-05 {english_title}" in english_result
        assert "A-share Market Recap" not in english_result

        ma.config.report_language = "zh"
        zh_result = ma.generate_market_review(overview, [])
        assert zh_label in zh_result
        assert "今日A股市场整体呈现" not in zh_result

    def test_news_block_uses_dash_when_source_metadata_missing(self):
        from src.application.market.market_analyzer import MarketAnalyzer

        ma = MarketAnalyzer.__new__(MarketAnalyzer)
        ma.config = SimpleNamespace(report_language="zh")
        ma.region = "cn"

        result = ma._build_news_block([
            {
                "title": "政策利好带动板块活跃",
                "snippet": "相关主题成交放大",
            }
        ])

        assert "- 1. 政策利好带动板块活跃" in result
        assert "相关主题成交放大" not in result
        assert "| 1 | 政策利好带动板块活跃 |" not in result
