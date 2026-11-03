"""Tests for notification reports."""

from tests.application.notification._notification_support import (
    AnalysisResult,
    NotificationService,
    _TestNotificationServiceReportGenerationFixture,
    _attach_decision_signal_summary,
    _make_config,
    _make_response,
    mock,
    unittest,
)


class TestNotificationServiceReportGeneration(_TestNotificationServiceReportGenerationFixture, unittest.TestCase):
    @mock.patch("src.application.notification.notification.get_config")
    def test_report_rows_and_summary_use_same_score_aligned_action(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="AAPL",
            name="Apple",
            sentiment_score=72,
            trend_prediction="Bullish",
            operation_advice="Hold",
            decision_type="hold",
            report_language="en",
        )

        out = service.generate_brief_report([result], report_date="2026-07-11")

        self.assertIn("🟢1 🟡0 🔴0", out)
        self.assertIn("Buy | Score 72", out)
        self.assertNotIn("Hold | Score 72", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_generate_aggregate_report_routes_by_report_type(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config()
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
        )

        with mock.patch.object(service, "generate_dashboard_report", return_value="dashboard") as mock_dashboard, mock.patch.object(
            service, "generate_brief_report", return_value="brief"
        ) as mock_brief:
            self.assertEqual(service.generate_aggregate_report([result], "simple"), "dashboard")
            self.assertEqual(service.generate_aggregate_report([result], "full"), "dashboard")
            self.assertEqual(service.generate_aggregate_report([result], "detailed"), "dashboard")
            self.assertEqual(service.generate_aggregate_report([result], "brief"), "brief")

        self.assertEqual(mock_dashboard.call_count, 3)
        mock_brief.assert_called_once()

    @mock.patch("src.application.notification.notification.get_config")
    def test_generate_single_stock_report_keeps_legacy_simple_format(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(report_renderer_enabled=True)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
        )

        with mock.patch("src.application.reporting.report_renderer.render") as mock_render:
            out = service.generate_single_stock_report(result)

        mock_render.assert_not_called()
        self.assertIn("贵州茅台", out)
        self.assertIn("600519", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_generate_brief_report_shows_model_by_default(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
            model_used="gemini/gemini-2.5-flash",
        )

        out = service.generate_brief_report([result], report_date="2026-02-01")

        self.assertIn("*分析模型: gemini/gemini-2.5-flash*", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_generate_dashboard_report_shows_model_by_default(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
            model_used="gemini/gemini-2.5-flash",
        )

        out = service.generate_dashboard_report([result], report_date="2026-02-01")

        self.assertIn("*分析模型：gemini/gemini-2.5-flash*", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_generate_dashboard_report_shows_phase_decision_in_default_renderer(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="等待确认",
            dashboard={
                "core_conclusion": {"one_sentence": "等待确认"},
                "phase_decision": {
                    "action_window": "盘中跟踪",
                    "immediate_action": "等待确认",
                    "watch_conditions": ["放量突破"],
                    "next_check_time": "14:30",
                    "confidence_reason": "数据质量可用",
                    "data_limitations": ["quote: stale"],
                },
            },
        )

        out = service.generate_dashboard_report([result], report_date="2026-02-01")

        self.assertIn("盘中决策护栏", out)
        self.assertIn("盘中跟踪", out)
        self.assertIn("等待确认", out)
        self.assertIn("放量突破", out)
        self.assertIn("quote: stale", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_generate_dashboard_report_skips_context_only_phase_decision_default_renderer(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="等待确认",
            dashboard={
                "core_conclusion": {"one_sentence": "等待确认"},
                "phase_decision": {
                    "phase_context": {"phase": "intraday", "market": "cn"},
                    "watch_conditions": [],
                    "data_limitations": [],
                },
            },
        )

        out = service.generate_dashboard_report([result], report_date="2026-02-01")

        self.assertNotIn("盘中决策护栏", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_generate_dashboard_report_omits_decision_signal_excerpt_fallback(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = _attach_decision_signal_summary(AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
        ))

        out = service.generate_dashboard_report([result], report_date="2026-02-01")

        self.assertNotIn("AI 决策信号", out)
        self.assertNotIn("理由: 技术面走弱", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_generate_daily_report_omits_decision_signal_excerpt_fallback(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        result = _attach_decision_signal_summary(AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
        ))

        for summary_only in (True, False):
            service = NotificationService()
            service._report_summary_only = summary_only
            out = service.generate_daily_report([result], report_date="2026-02-01")
            self.assertNotIn("AI 决策信号", out)
            self.assertNotIn("理由: 技术面走弱", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_strategy_synthesis_legacy_shapes_are_safe_in_fallback_reports(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()

        for malformed in ("bad-shape", ["bad-shape"], 42, True):
            result = AnalysisResult(
                code="600519",
                name="贵州茅台",
                sentiment_score=50,
                trend_prediction="震荡",
                operation_advice="观望",
                report_language="zh",
                dashboard={
                    "core_conclusion": {"one_sentence": "测试"},
                    "intelligence": {},
                    "battle_plan": {},
                    "strategy_synthesis": malformed,
                },
            )

            markdown = service.generate_dashboard_report([result], report_date="2026-07-19")
            wechat = service.generate_wechat_dashboard([result])

            self.assertNotIn("多策略综合", markdown)
            self.assertNotIn("多策略综合", wechat)

        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=50,
            trend_prediction="震荡",
            operation_advice="观望",
            report_language="zh",
            dashboard={
                "core_conclusion": {"one_sentence": "测试"},
                "intelligence": {},
                "battle_plan": {},
                "strategy_synthesis": {
                    "final_signal": "hold",
                    "consensus_level": "insufficient",
                    "conflict_severity": "none",
                    "conflict_count": 0,
                    "supporting_skills": "bad-shape",
                    "opposing_skills": ["bad-shape"],
                    "conflicts": "bad-shape",
                    "summary_params": {"invalid_opinion_count": "3"},
                },
            },
        )

        markdown = service.generate_dashboard_report([result], report_date="2026-07-19")
        wechat = service.generate_wechat_dashboard([result])

        self.assertIn("另有 3 个策略解析失败", markdown)
        self.assertIn("另有 3 个策略解析失败", wechat)

    @mock.patch("src.application.notification.notification.get_config")
    def test_generate_dashboard_report_omits_decision_signal_excerpt_with_renderer(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=True)
        service = NotificationService()
        result = _attach_decision_signal_summary(AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
        ))

        out = service.generate_dashboard_report([result], report_date="2026-02-01")

        self.assertNotIn("AI 决策信号", out)
        self.assertNotIn("理由: 技术面走弱", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_aggregate_reports_show_compact_market_status_only(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
        )
        result.market_phase_summary = {
            "phase": "intraday",
            "market": "cn",
            "trigger_source": "portfolio",
            "is_partial_bar": True,
        }
        result.analysis_context_pack_overview = {
            "data_quality": {
                "level": "limited",
                "limitations": ["quote: stale", "news: missing", "portfolio_context: hidden"],
            }
        }
        result.raw_response = "raw context pack and prompt should not appear"

        out = service.generate_brief_report([result], report_date="2026-02-01")

        self.assertIn("市场状态：A股 · 盘中", out)
        self.assertNotIn("阶段：intraday", out)
        self.assertNotIn("触发来源：portfolio", out)
        self.assertNotIn("盘中数据提示", out)
        self.assertNotIn("数据质量: limited", out)
        self.assertNotIn("限制: quote: stale", out)
        self.assertNotIn("限制: news: missing", out)
        self.assertNotIn("portfolio_context: hidden", out)
        self.assertNotIn("raw context pack", out)
        self.assertNotIn("prompt", out.lower())

    @mock.patch("src.application.notification.notification.get_config")
    def test_template_dashboard_report_uses_single_market_status_line(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(report_renderer_enabled=True)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
        )
        result.market_phase_summary = {
            "phase": "postmarket",
            "market": "cn",
            "trigger_source": "cli",
        }
        result.analysis_context_pack_overview = {
            "data_quality": {
                "level": "good",
                "limitations": ["technical: partial"],
            }
        }

        out = service.generate_dashboard_report([result], report_date="2026-02-01")

        self.assertIn("市场状态：A股 · 盘后", out)
        self.assertEqual(out.count("市场状态："), 1)
        self.assertNotIn("阶段：postmarket", out)
        self.assertNotIn("触发来源：cli", out)
        self.assertNotIn("数据质量: good", out)
        self.assertNotIn("technical: partial", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_generated_reports_skip_phase_pack_excerpt_when_summary_missing(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
        )

        out = service.generate_brief_report([result], report_date="2026-02-01")

        self.assertNotIn("摘要来源", out)
        self.assertNotIn("评估器快照", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_generate_dashboard_report_collapses_unavailable_chip_structure(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
            dashboard={
                "data_perspective": {
                    "chip_structure": {
                        "profit_ratio": "数据缺失，无法判断",
                        "avg_cost": "数据缺失，无法判断",
                        "concentration": "数据缺失，无法判断",
                        "chip_health": "数据缺失，无法判断",
                    }
                }
            },
        )

        out = service.generate_dashboard_report([result], report_date="2026-02-01")

        self.assertIn("**筹码**: 筹码分布未启用或数据源暂不可用，未纳入筹码判断。", out)
        self.assertEqual(out.count("数据缺失，无法判断"), 0)

    @mock.patch("src.application.notification.notification.get_config")
    def test_generate_reports_hide_model_when_disabled(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(
            report_renderer_enabled=False,
            report_show_llm_model=False,
        )
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
            model_used="gemini/gemini-2.5-flash",
        )

        dashboard = service.generate_dashboard_report([result], report_date="2026-02-01")
        single = service.generate_single_stock_report(result)

        self.assertNotIn("分析模型", dashboard)
        self.assertNotIn("gemini/gemini-2.5-flash", dashboard)
        self.assertNotIn("分析模型", single)
        self.assertNotIn("gemini/gemini-2.5-flash", single)

    @mock.patch("src.application.notification.notification.get_config")
    def test_generate_single_stock_report_appends_fundamental_blocks(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
        )
        result.fundamental_context = self._make_fundamental_context()

        out = service.generate_single_stock_report(result)

        # 财务摘要
        self.assertIn("财务摘要", out)
        self.assertIn("2024-09-30", out)
        self.assertIn("12360.00 亿元", out)
        self.assertIn("22.45%", out)
        self.assertIn("15.23%", out)
        self.assertIn("91.55%", out)
        # 股东回报
        self.assertIn("股东回报", out)
        self.assertIn("30.8760 元", out)
        self.assertIn("1.85%", out)
        self.assertIn("2024-06-26", out)
        # 关联板块（白酒带行业信号；MSCI中国 带概念信号）
        self.assertIn("关联板块", out)
        self.assertIn("白酒", out)
        self.assertIn("领涨", out)
        self.assertIn("+3.42%", out)
        self.assertIn("MSCI中国", out)
        self.assertIn("- 白酒 (行业板块 领涨 +3.42%)", out)
        self.assertIn("- MSCI中国 (概念板块 领涨 +1.23%)", out)
        self.assertIn("+1.23%", out)
        self.assertNotIn("| 板块 | 类型 | 板块表现 | 板块涨跌幅 |", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_generate_single_stock_report_skips_fundamental_blocks_when_missing(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
        )

        out = service.generate_single_stock_report(result)

        self.assertNotIn("财务摘要", out)
        self.assertNotIn("股东回报", out)
        self.assertNotIn("关联板块", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_generate_single_stock_report_handles_partial_fundamental_context(
        self, mock_get_config: mock.MagicMock
    ):
        """Only dividend data present — render shareholder return, skip the other two."""
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
        )
        result.fundamental_context = {
            "earnings": {
                "status": "partial",
                "data": {
                    "dividend": {
                        "events": [],
                        "ttm_event_count": 0,
                        "ttm_cash_dividend_per_share": 0.5,
                    }
                },
            },
        }

        out = service.generate_single_stock_report(result)

        self.assertNotIn("财务摘要", out)
        self.assertIn("股东回报", out)
        self.assertIn("0.5000 元", out)
        self.assertNotIn("关联板块", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_generate_single_stock_report_uses_currency_for_us(
        self, mock_get_config: mock.MagicMock
    ):
        """USD currency on financial_report yields 亿美元 suffix instead of 亿元."""
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="AAPL",
            name="Apple Inc.",
            sentiment_score=64,
            trend_prediction="震荡",
            operation_advice="观望",
            analysis_summary="观望等待 AI 兑现节奏。",
        )
        result.fundamental_context = {
            "earnings": {
                "status": "ok",
                "data": {
                    "financial_report": {
                        "report_date": "2026-03-31",
                        "revenue": 1.11e11,
                        "net_profit_parent": 2.95e10,
                        "operating_cash_flow": 2.87e10,
                        "roe": 141.47,
                        "currency": "USD",
                    },
                    "dividend": {
                        "events": [{
                            "event_date": "2026-05-11",
                            "ex_dividend_date": "2026-05-11",
                            "cash_dividend_per_share": 0.27,
                            "is_pre_tax": True,
                        }],
                        "ttm_event_count": 4,
                        "ttm_cash_dividend_per_share": 1.05,
                        "ttm_dividend_yield_pct": 0.36,
                    },
                },
            },
            "growth": {"status": "ok", "data": {"revenue_yoy": 16.60, "roe": 141.47, "gross_margin": 47.86}},
            "belong_boards": [
                {"name": "Technology", "type": "行业"},
                {"name": "Consumer Electronics", "type": "概念"},
            ],
        }

        out = service.generate_single_stock_report(result)

        self.assertIn("财务摘要", out)
        self.assertIn("亿美元", out)
        self.assertNotIn("12360.00 亿元", out)
        # Sample expected formatted values
        self.assertIn("1110.00 亿美元", out)
        self.assertIn("141.47%", out)
        # Dividend per share also picks up currency suffix
        self.assertIn("1.0500 美元", out)
        # Sector + industry render as belong_boards
        self.assertIn("Technology", out)
        self.assertIn("Consumer Electronics", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_related_boards_renders_each_board_signal_without_placeholder(
        self, mock_get_config: mock.MagicMock
    ):
        """Rows without a matching change_pct stay as plain board entries."""
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
        )
        result.fundamental_context = {
            "earnings": {"status": "ok", "data": {}},
            "growth": {"status": "ok", "data": {}},
            "boards": {"status": "ok", "data": {
                "top": [{"name": "白酒", "change_pct": 3.42}],
                "bottom": [],
            }},
            "belong_boards": [
                {"name": "白酒", "code": "BK0596", "type": "行业"},
                {"name": "MSCI中国", "code": "BK0805", "type": "概念"},
            ],
        }

        out = service.generate_single_stock_report(result)

        self.assertNotIn("板块表现", out)
        self.assertNotIn("板块涨跌幅", out)
        self.assertIn("领涨", out)
        self.assertIn("+3.42%", out)
        self.assertIn("- 白酒 (行业板块 领涨 +3.42%)", out)
        self.assertIn("MSCI中国", out)
        self.assertIn("- MSCI中国", out)
        self.assertNotIn("- MSCI中国 (", out)
        self.assertNotIn("| MSCI中国 | 概念 | -- | -- |", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_generate_single_stock_report_uses_currency_for_hk(
        self, mock_get_config: mock.MagicMock
    ):
        """HK ADRs have financialCurrency=CNY but trade/pay dividends in HKD.

        The financial summary must render in 元 (CNY income statement) while
        dividends must render in 港元 — they are NOT the same currency on
        yfinance HK payloads, so the renderer must read each block's own
        ``currency`` field rather than assuming a single global currency.
        """
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="HK09988",
            name="阿里巴巴-W",
            sentiment_score=68,
            trend_prediction="看多",
            operation_advice="逢低买入",
            analysis_summary="云业务回正，回购持续。",
        )
        result.fundamental_context = {
            "earnings": {
                "status": "ok",
                "data": {
                    "financial_report": {
                        "report_date": "2026-03-31",
                        "revenue": 1.02e12,
                        "net_profit_parent": 1.04e11,
                        "operating_cash_flow": 3.6e10,
                        "roe": 9.22,
                        "currency": "CNY",
                    },
                    "dividend": {
                        "events": [{
                            "event_date": "2025-06-11",
                            "ex_dividend_date": "2025-06-11",
                            "cash_dividend_per_share": 1.95812,
                            "is_pre_tax": True,
                        }],
                        "ttm_event_count": 1,
                        "ttm_cash_dividend_per_share": 1.95812,
                        "ttm_dividend_yield_pct": 1.75,
                        "currency": "HKD",
                    },
                },
            },
            "growth": {"status": "ok", "data": {"revenue_yoy": 2.9, "roe": 9.22, "gross_margin": 39.81}},
            "belong_boards": [
                {"name": "Consumer Cyclical", "type": "行业"},
                {"name": "Internet Retail", "type": "概念"},
            ],
        }

        out = service.generate_single_stock_report(result)

        # Income statement still rendered in CNY (financialCurrency).
        self.assertIn("10200.00 亿元", out)
        # Dividend per share follows the dividend currency, NOT the financial currency.
        self.assertIn("1.9581 港元", out)
        self.assertNotIn("1.9581 元 ", out)
        self.assertIn("Consumer Cyclical", out)

    @mock.patch("src.application.notification.notification.get_config")
    def test_generate_dashboard_report_appends_fundamental_blocks(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=72,
            trend_prediction="看多",
            operation_advice="持有",
            analysis_summary="稳健",
            dashboard={
                "core_conclusion": {"one_sentence": "稳健持有"},
                "battle_plan": {
                    "sniper_points": {
                        "ideal_buy": "1600",
                        "stop_loss": "1500",
                        "take_profit": "1800",
                    }
                },
            },
        )
        result.fundamental_context = self._make_fundamental_context()

        out = service.generate_dashboard_report([result], report_date="2026-05-20")

        self.assertIn("财务摘要", out)
        self.assertIn("股东回报", out)
        self.assertIn("关联板块", out)
        self.assertIn("白酒", out)
        self.assertIn("领涨", out)

    @mock.patch("src.application.notification.notification.get_config")
    @mock.patch("requests.post")
    def test_send_uses_injected_image_render_port(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        """R3-S11：转图经 ``ImageRenderPort`` 注入，不再直接 import 具体实现。"""
        cfg = _make_config(
            custom_webhook_urls=["https://example.com/webhook"],
            markdown_to_image_channels=["custom"],
            markdown_to_image_max_chars=4321,
        )
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200)

        render_port = mock.MagicMock()
        render_port.markdown_to_image.return_value = b"png"

        service = NotificationService(image_render_port=render_port)
        ok = service.send("markdown content")

        self.assertTrue(ok)
        render_port.markdown_to_image.assert_called_once_with(
            "markdown content", max_chars=4321
        )
