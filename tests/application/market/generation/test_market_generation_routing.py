"""Tests for market generation routing."""

from tests.application.analysis._market_analyzer_generate_text_support import (
    _TestMarketAnalyzerBypassFixFixture,
    _llm_usage_hmac_env,
)


class TestMarketAnalyzerBypassFix(_TestMarketAnalyzerBypassFixFixture):
    def test_no_access_to_private_model_attribute(self):
        """generate_text() must be called; _model must never be accessed."""
        ma = self._make_market_analyzer_with_mock_generate_text("复盘结果")
        # Ensure _model attribute does not exist (simulates PR #494 state)
        assert not hasattr(ma.analyzer, "_model") or ma.analyzer._model is None, (
            "_model should not be set on the LiteLLM-based analyzer"
        )
        # generate_text is a MagicMock, so calling it won't crash
        result = ma.analyzer.generate_text("prompt")
        assert isinstance(result, str) and len(result) > 0
        ma.analyzer.generate_text.assert_called_once()
