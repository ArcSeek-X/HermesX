"""Tests for alphasift contracts."""

from tests.api.alphasift._alphasift_api_support import (
    _AlphaSiftOpportunitiesApiTestCaseFixture,
    _make_adapter_module,
    hrs_alphasift_bridge,
    patch,
    unittest,
)


class AlphaSiftOpportunitiesApiTestCase(_AlphaSiftOpportunitiesApiTestCaseFixture, unittest.TestCase):
    def test_strategies_returns_adapter_strategies(self) -> None:
        config = self._config(enabled=True)
        fake_module = _make_adapter_module(
            list_strategies=lambda: [
                {"id": "dual_low", "name": "双低选股", "description": "value", "category": "价值"},
                {"id": "trend_quality", "title": "趋势质量", "description": "trend", "tag": "框架"},
            ],
        )

        with patch("src.application.analysis.alphasift_service._import_alphasift", return_value=fake_module):
            payload = self._strategies(config=config)

        self.assertEqual(payload["enabled"], True)
        self.assertEqual(payload["strategy_count"], 2)
        self.assertEqual(payload["strategies"][0]["id"], "dual_low")
        self.assertEqual(payload["strategies"][0]["name"], "双低选股")
        self.assertEqual(payload["strategies"][1]["name"], "趋势质量")

    def test_fetch_ths_summary_event_ignores_missing_concept_name_column(self) -> None:
        import pandas as pd

        provider = hrs_alphasift_bridge.HrsEastMoneyHotspotProvider()
        summary = pd.DataFrame([
            {"日期": "2026-06-07", "驱动事件": "行业政策利好"},
        ])

        class _MockAkshare:
            @staticmethod
            def stock_board_concept_summary_ths():
                return summary

        with patch.dict("sys.modules", {"akshare": _MockAkshare()}):
            text = provider._fetch_ths_summary_event("MLCC")

        self.assertEqual(text, "")
