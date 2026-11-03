"""Tests for market generation responses."""

from tests.application.analysis._market_analyzer_generate_text_support import (
    _TestMarketAnalyzerBypassFixFixture,
    _llm_usage_hmac_env,
    pytest,
)


class TestMarketAnalyzerBypassFix(_TestMarketAnalyzerBypassFixFixture):
    def test_market_review_uses_8192_max_tokens(self):
        """generate_market_review() should request a larger output budget to avoid truncation."""
        from src.application.market.market_analyzer import MarketOverview, MarketIndex

        ma = self._make_market_analyzer_with_mock_generate_text(return_value="复盘结果")
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
        _, kwargs = ma.analyzer.generate_text.call_args
        assert kwargs["max_tokens"] == 8192
        assert kwargs["temperature"] == 0.7

    def test_inject_data_into_review_matches_english_headings(self):
        from src.application.market.market_analyzer import MarketOverview, MarketIndex

        ma = self._make_market_analyzer_with_mock_generate_text(return_value="review")
        ma.config.report_language = "en"
        overview = MarketOverview(
            date="2026-03-05",
            indices=[
                MarketIndex(
                    code="000001",
                    name="上证指数",
                    current=3300.0,
                    change=12.0,
                    change_pct=0.36,
                    amount=145000000000.0,
                )
            ],
            up_count=3200,
            down_count=1800,
            flat_count=100,
            limit_up_count=88,
            limit_down_count=5,
            total_amount=14567.0,
            top_sectors=[{"name": "AI算力", "change_pct": 3.25}],
            bottom_sectors=[{"name": "煤炭", "change_pct": -1.12}],
        )
        review = """## 2026-03-05 A-share Market Recap

### 1. Market Summary
Summary text.

### 2. Index Commentary
Index text.

### 4. Sector Highlights
Sector text.
"""

        result = ma._inject_data_into_review(review, overview)

        assert "- **Market Signal**: 66/100 (constructive, risk-on)" in result
        assert "- **Breadth**: Advancers 3200 / Decliners 1800 / Flat 100;" in result
        assert "Turnover 14567 (CNY 100m)" in result
        assert "| Index | Last | Change % | Open | High | Low | Amplitude | Turnover (CNY 100m) |" in result
        assert "#### Leading Industry Sectors" in result
        assert "| 1 | AI算力 | +3.25% |" in result
        assert "#### Lagging Industry Sectors" in result
        assert "| 1 | 煤炭 | -1.12% |" in result

    def test_inject_data_into_review_matches_reference_style_chinese_headings(self):
        from src.application.market.market_analyzer import MarketOverview, MarketIndex

        ma = self._make_market_analyzer_with_mock_generate_text(return_value="review")
        overview = MarketOverview(
            date="2026-03-05",
            indices=[
                MarketIndex(
                    code="000001",
                    name="上证指数",
                    current=3300.0,
                    change=12.0,
                    change_pct=0.36,
                    open=3288.0,
                    high=3312.0,
                    low=3276.0,
                    amount=145000000000.0,
                    amplitude=1.1,
                )
            ],
            up_count=3200,
            down_count=1800,
            flat_count=100,
            limit_up_count=88,
            limit_down_count=5,
            total_amount=14567.0,
            top_sectors=[{"name": "AI算力", "change_pct": 3.25}],
            bottom_sectors=[{"name": "煤炭", "change_pct": -1.12}],
        )
        news = [{"title": "AI算力板块走强", "snippet": "算力产业链延续活跃，成交额放大"}]
        review = """## 2026-03-05 大盘复盘

### 一、盘面总览
总结。

### 二、指数结构
指数。

### 三、板块主线
板块。

### 五、消息催化
新闻。
"""

        result = ma._inject_data_into_review(review, overview, news)

        assert "盘面信号" in result
        assert "66/100（偏暖，可进攻）" in result
        assert "绿灯（可进攻）" not in result
        assert "大盘红绿灯" not in result
        assert "green（可进攻）" not in result
        assert "信号依据" in result
        signal_line = next(line for line in result.splitlines() if "**盘面信号**" in line)
        drivers_line = next(line for line in result.splitlines() if "**信号依据**" in line)
        assert signal_line.startswith("- ")
        assert "66/100" in signal_line
        assert "█" not in result
        assert "░" not in result
        assert "盘面温度" not in drivers_line
        assert "操作建议" in result
        assert "盘面温度" not in result
        assert "| 上涨/下跌/平盘 | 3200 / 1800 / 100 |" in result
        assert "| 指数 | 最新 | 涨跌幅 | 开盘 | 最高 | 最低 | 振幅 | 成交额(亿) |" in result
        assert "| 上证指数 | 3300.00 | 🟢 +0.36% | 3288.00 | 3312.00 | 3276.00 | 1.10% | 1450 |" in result
        assert "#### 行业板块领涨 Top 5" in result
        assert "| 1 | AI算力 | +3.25% |" in result
        assert "#### 近三日市场线索" not in result
        assert "AI算力板块走强" not in result
        assert "新闻。" in result
        assert "算力产业链延续活跃" not in result

    def test_inject_data_into_review_appends_sector_block_when_heading_drifts(self):
        from src.application.market.market_analyzer import MarketOverview

        ma = self._make_market_analyzer_with_mock_generate_text(return_value="review")
        overview = MarketOverview(
            date="2026-03-05",
            top_sectors=[{"name": "AI算力", "change_pct": 3.25}],
            bottom_sectors=[{"name": "煤炭", "change_pct": -1.12}],
        )
        review = """## 2026-03-05 大盘复盘

### 今日主线观察
正文。
"""

        result = ma._inject_data_into_review(review, overview)

        assert "### 三、板块主线" in result
        assert "#### 行业板块领涨 Top 5" in result
        assert "| 1 | AI算力 | +3.25% |" in result
        assert "#### 行业板块领跌 Top 5" in result
        assert "| 1 | 煤炭 | -1.12% |" in result

    def test_market_light_snapshot_marks_defensive_market_red(self):
        from src.application.market.market_analyzer import MarketIndex, MarketOverview

        ma = self._make_market_analyzer_with_mock_generate_text(return_value="review")
        overview = MarketOverview(
            date="2026-03-06",
            indices=[
                MarketIndex(code="000001", name="上证指数", current=3200, change_pct=-1.8),
                MarketIndex(code="399001", name="深证成指", current=9800, change_pct=-2.4),
            ],
            up_count=900,
            down_count=4100,
            limit_up_count=10,
            limit_down_count=80,
            total_amount=9800.0,
        )

        snapshot = ma.build_market_light_snapshot(overview)

        assert snapshot["status"] == "red"
        assert snapshot["label"] == "偏防守"
        assert snapshot["score"] < 40
        assert snapshot["region"] == "cn"
        assert snapshot["trade_date"] == "2026-03-06"
        assert snapshot["data_quality"] == "ok"
        assert snapshot["dimensions"]["breadth"]["available"] is True
        assert snapshot["dimensions"]["index"]["available"] is True
        assert snapshot["dimensions"]["limit"]["available"] is True
        assert any("亏钱效应" in reason for reason in snapshot["reasons"])

    def test_market_light_snapshot_uses_english_labels_and_reasons(self):
        from src.application.market.market_analyzer import MarketIndex, MarketOverview

        ma = self._make_market_analyzer_with_mock_generate_text(return_value="review")
        ma.config.report_language = "en"
        overview = MarketOverview(
            date="2026-03-06",
            indices=[
                MarketIndex(code="000001", name="SSE Composite", current=3200, change_pct=-1.8),
                MarketIndex(code="399001", name="SZSE Component", current=9800, change_pct=-2.4),
            ],
            up_count=900,
            down_count=4100,
            limit_up_count=10,
            limit_down_count=80,
            total_amount=9800.0,
        )

        snapshot = ma.build_market_light_snapshot(overview)

        assert snapshot["status"] == "red"
        assert snapshot["label"] == "risk-off"
        assert snapshot["guidance"] == (
            "Risk is elevated; prioritize drawdown control and avoid chasing weak rebounds."
        )
        assert not any(reason.startswith("market temperature ") for reason in snapshot["reasons"])
        assert any(
            reason.startswith("advancers ratio ") and "downside pressure dominates" in reason
            for reason in snapshot["reasons"]
        )

    def test_market_light_snapshot_marks_us_without_breadth_as_partial(self):
        from src.domain.market.profile import US_PROFILE
        from src.application.market.market_analyzer import MarketIndex, MarketOverview

        ma = self._make_market_analyzer_with_mock_generate_text(return_value="review")
        ma.region = "us"
        ma.profile = US_PROFILE
        ma.config.report_language = "en"
        overview = MarketOverview(
            date="2026-03-06",
            indices=[MarketIndex(code="SPX", name="S&P 500", current=5000, change_pct=0.5)],
        )

        snapshot = ma.build_market_light_snapshot(overview)

        assert snapshot["region"] == "us"
        assert snapshot["data_quality"] == "partial"
        assert snapshot["dimensions"]["breadth"] == {"score": 50, "available": False}
        assert snapshot["dimensions"]["index"]["available"] is True
        assert snapshot["dimensions"]["limit"] == {"score": 50, "available": False}

    @pytest.mark.parametrize(
        ("region", "profile_name", "index_code", "index_name"),
        [
            ("jp", "JP_PROFILE", "N225", "Nikkei 225"),
            ("kr", "KR_PROFILE", "KS11", "KOSPI"),
        ],
    )
    def test_market_light_snapshot_accepts_jp_kr_regions(
        self, region, profile_name, index_code, index_name
    ):
        import src.domain.market.profile as market_profile
        from src.application.market.market_analyzer import MarketIndex, MarketOverview

        ma = self._make_market_analyzer_with_mock_generate_text(return_value="review")
        ma.region = region
        ma.profile = getattr(market_profile, profile_name)
        overview = MarketOverview(
            date="2026-03-06",
            indices=[MarketIndex(code=index_code, name=index_name, current=30000, change_pct=0.5)],
        )

        snapshot = ma.build_market_light_snapshot(overview)

        assert snapshot["region"] == region
        assert snapshot["trade_date"] == "2026-03-06"
        assert snapshot["data_quality"] == "partial"
        assert snapshot["dimensions"]["breadth"] == {"score": 50, "available": False}
        assert snapshot["dimensions"]["index"]["available"] is True
        assert snapshot["dimensions"]["limit"] == {"score": 50, "available": False}

    def test_market_review_payload_omits_breadth_for_markets_without_stats(self):
        from src.domain.market.profile import US_PROFILE
        from src.application.market.market_analyzer import MarketIndex, MarketOverview

        ma = self._make_market_analyzer_with_mock_generate_text(return_value="复盘结果")
        ma.region = "us"
        ma.profile = US_PROFILE

        payload = ma.build_market_review_payload(
            MarketOverview(
                date="2026-03-18",
                indices=[
                    MarketIndex(code="SPX", name="S&P 500", current=5200.0, change_pct=0.6),
                ],
                up_count=1000,
                down_count=400,
                limit_up_count=10,
                limit_down_count=0,
                total_amount=9800.0,
            ),
            [],
            "美股复盘报告",
            market_light_snapshot={"dimensions": {"breadth": {"score": 60, "available": True}}},
        )

        assert "breadth" not in payload
        assert payload["indices"][0]["code"] == "SPX"

    def test_market_review_payload_omits_breadth_for_cn_market_without_available_stats(self):
        from src.application.market.market_analyzer import MarketIndex, MarketOverview

        ma = self._make_market_analyzer_with_mock_generate_text(return_value="复盘结果")
        payload = ma.build_market_review_payload(
            MarketOverview(
                date="2026-03-18",
                indices=[
                    MarketIndex(code="000001", name="上证指数", current=3200.0, change_pct=0.6),
                ],
                up_count=0,
                down_count=0,
                flat_count=0,
                limit_up_count=0,
                limit_down_count=0,
                total_amount=0.0,
            ),
            [],
            "A股复盘报告",
            market_light_snapshot={"dimensions": {"breadth": {"score": 55, "available": False}}},
        )

        assert "breadth" not in payload
        assert payload["indices"][0]["name"] == "上证指数"

    def test_market_review_payload_includes_breadth_only_when_stats_available(self):
        from src.application.market.market_analyzer import MarketIndex, MarketOverview

        ma = self._make_market_analyzer_with_mock_generate_text(return_value="复盘结果")
        payload = ma.build_market_review_payload(
            MarketOverview(
                date="2026-03-18",
                indices=[
                    MarketIndex(code="000001", name="上证指数", current=3200.0, change_pct=0.6),
                ],
                up_count=1200,
                down_count=900,
                flat_count=60,
                limit_up_count=12,
                limit_down_count=4,
                total_amount=12345.0,
            ),
            [],
            "A股复盘报告",
            market_light_snapshot={"dimensions": {"breadth": {"score": 62, "available": True}}},
        )

        assert payload["breadth"] is not None
        assert payload["breadth"]["up_count"] == 1200
        assert payload["breadth"]["down_count"] == 900
        assert payload["breadth"]["limit_up_count"] == 12
        assert payload["breadth"]["total_amount"] == 12345.0

    def test_us_english_indices_do_not_label_turnover_as_cny(self):
        from src.domain.market.profile import US_PROFILE
        from src.domain.market.strategy import get_market_strategy_blueprint
        from src.application.market.market_analyzer import MarketOverview, MarketIndex

        ma = self._make_market_analyzer_with_mock_generate_text(return_value=None)
        ma.config.report_language = "en"
        ma.region = "us"
        ma.profile = US_PROFILE
        ma.strategy = get_market_strategy_blueprint("us")
        overview = MarketOverview(
            date="2026-03-05",
            indices=[
                MarketIndex(
                    code="SPX",
                    name="S&P 500",
                    current=5200.0,
                    change=35.0,
                    change_pct=0.68,
                    amount=9876543210.0,
                )
            ],
        )

        result = ma._build_indices_block(overview)

        assert "CNY 100m" not in result
        assert "Turnover (USD bn)" in result
        assert "| S&P 500 | 5200.00 |" in result

    def test_indices_block_uses_configured_red_up_color_scheme(self):
        from src.application.market.market_analyzer import MarketOverview, MarketIndex

        ma = self._make_market_analyzer_with_mock_generate_text(return_value=None)
        ma.config.market_review_color_scheme = "red_up"
        overview = MarketOverview(
            date="2026-03-05",
            indices=[
                MarketIndex(code="000001", name="上证指数", current=3200.0, change_pct=0.68),
                MarketIndex(code="399001", name="深证成指", current=9800.0, change_pct=-0.42),
                MarketIndex(code="399006", name="创业板指", current=2100.0, change_pct=0.0),
            ],
        )

        result = ma._build_indices_block(overview)

        assert "| 上证指数 | 3200.00 | 🔴 +0.68% |" in result
        assert "| 深证成指 | 9800.00 | 🟢 -0.42% |" in result
        assert "| 创业板指 | 2100.00 | ⚪ +0.00% |" in result

    def test_indices_block_keeps_green_up_default_color_scheme(self):
        from src.application.market.market_analyzer import MarketOverview, MarketIndex

        ma = self._make_market_analyzer_with_mock_generate_text(return_value=None)
        overview = MarketOverview(
            date="2026-03-05",
            indices=[
                MarketIndex(code="000001", name="上证指数", current=3200.0, change_pct=0.68),
                MarketIndex(code="399001", name="深证成指", current=9800.0, change_pct=-0.42),
            ],
        )

        result = ma._build_indices_block(overview)

        assert "| 上证指数 | 3200.00 | 🟢 +0.68% |" in result
        assert "| 深证成指 | 9800.00 | 🔴 -0.42% |" in result

    def test_no_private_attribute_access_in_market_analyzer_source(self):
        """Static guard: market_analyzer.py must not access private analyzer attrs."""
        import ast
        import pathlib

        import src.application.market.market_analyzer as market_analyzer_module

        src = pathlib.Path(market_analyzer_module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(src)
        forbidden = {
            "_model", "_router", "_use_openai", "_use_anthropic",  # historical
            "_call_litellm",      # use generate_text() instead
            "_litellm_available", # use is_available() instead
        }

        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                if node.attr in forbidden:
                    violations.append(node.attr)

        assert violations == [], (
            f"market_analyzer.py still accesses private Analyzer attributes: {violations}"
        )
