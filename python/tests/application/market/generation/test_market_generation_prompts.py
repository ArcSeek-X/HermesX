"""Tests for market generation prompts."""

from tests.application.analysis._market_analyzer_generate_text_support import (
    SimpleNamespace,
    _TestMarketAnalyzerBypassFixFixture,
    _llm_usage_hmac_env,
)


class TestMarketAnalyzerBypassFix(_TestMarketAnalyzerBypassFixFixture):
    def test_generate_template_review_uses_english_shell_for_cn_when_report_language_is_en(self):
        from src.application.market.market_analyzer import MarketOverview, MarketIndex

        ma = self._make_market_analyzer_with_mock_generate_text(return_value=None)
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
                )
            ],
            up_count=3200,
            down_count=1800,
            limit_up_count=88,
            limit_down_count=5,
            total_amount=14567.0,
            top_sectors=[{"name": "AI算力", "change_pct": 3.25}],
            bottom_sectors=[{"name": "煤炭", "change_pct": -1.12}],
        )

        result = ma.generate_market_review(overview, [])

        assert "A-share Market Recap" in result
        assert "### 1. Market Summary" in result
        assert "### 3. Breadth & Liquidity" in result
        assert "Turnover (CNY 100m)" in result
        assert "### 4. Sector / Theme Highlights" in result
        assert "### 6. Strategy Framework" in result
        assert "### 一、市场总结" not in result

    def test_generate_template_review_keeps_chinese_shell_for_us_when_report_language_is_default(self):
        from src.domain.market.profile import US_PROFILE
        from src.domain.market.strategy import get_market_strategy_blueprint
        from src.application.market.market_analyzer import MarketOverview, MarketIndex

        ma = self._make_market_analyzer_with_mock_generate_text(return_value=None)
        ma.region = "us"
        ma.profile = US_PROFILE
        ma.strategy = get_market_strategy_blueprint("us")
        overview = MarketOverview(
            date="2026-03-05",
            indices=[
                MarketIndex(
                    code="SPX",
                    name="标普500",
                    current=5200.0,
                    change=-18.0,
                    change_pct=-0.35,
                )
            ],
        )

        result = ma.generate_market_review(overview, [])

        assert "## 2026-03-05 大盘复盘" in result
        assert "### 一、盘面总览" in result
        assert "今日美股市场整体呈现**小幅下跌**态势" in result
        assert "### 6. Strategy Framework" not in result
        assert "### 六、策略框架" in result
        assert "### 1. Market Summary" not in result
        assert "US Market Recap" not in result

    def test_market_review_payload_sections_skip_top_report_title(self):
        from src.application.market.market_analyzer import MarketAnalyzer

        ma = MarketAnalyzer.__new__(MarketAnalyzer)
        sections = ma._split_report_sections("""## 2026-06-03 大盘复盘

> 今日指数分化。

### 一、盘面总览
正文
""")

        assert sections[0]["key"] == "overview"
        assert "今日指数分化" in sections[0]["markdown"]
        assert all(section["title"] != "2026-06-03 大盘复盘" for section in sections)

    def test_news_block_renders_title_source_and_link_only(self):
        from src.application.market.market_analyzer import MarketAnalyzer

        ma = MarketAnalyzer.__new__(MarketAnalyzer)
        ma.config = SimpleNamespace(report_language="zh")
        ma.region = "cn"
        long_snippet = (
            "复盘必读 2026-05-06 复盘的意义在于更清晰地把握市场脉搏，"
            "综合描述 A 股三大指数今日集体反弹，成交额放大，科技成长方向领涨。"
        )

        result = ma._build_news_block([
            {
                "title": "A股收评：科创50指数放量反弹涨5.47% 两市成交额重回3万亿元",
                "snippet": long_snippet,
                "source": "东方财富",
                "published_date": "2026-05-06",
                "url": "https://example.com/news/1",
            }
        ])

        assert "#### 近三日市场线索" in result
        assert "| 序号 |" not in result
        assert "摘要/线索片段" not in result
        assert "关注点" not in result
        assert "成交额放大" not in result
        assert (
            "- 1. [A股收评：科创50指数放量反弹涨5.47% 两市成交额重回3万亿元]"
            "(https://example.com/news/1)（东方财富 / 2026-05-06）"
        ) in result

    def test_news_block_uses_english_metadata_punctuation(self):
        from src.application.market.market_analyzer import MarketAnalyzer

        ma = MarketAnalyzer.__new__(MarketAnalyzer)
        ma.config = SimpleNamespace(report_language="en")
        ma.region = "us"

        result = ma._build_news_block([
            {
                "title": "Chip stocks rally as AI demand improves",
                "source": "Reuters",
                "published_date": "2026-05-06",
                "url": "https://example.com/news/2",
            }
        ])

        assert "#### News Catalysts" in result
        assert (
            "- 1. [Chip stocks rally as AI demand improves](https://example.com/news/2)"
            " (Reuters / 2026-05-06)"
        ) in result
        assert "（Reuters" not in result

    def test_review_prompt_caps_news_url_context(self):
        from src.application.market.market_analyzer import MarketOverview

        ma = self._make_market_analyzer_with_mock_generate_text(return_value="review")
        long_url = "https://example.com/redirect?" + "utm_campaign=" + ("x" * 420)

        prompt = ma._build_review_prompt(
            MarketOverview(date="2026-05-06"),
            [
                {
                    "title": "A股收评：指数放量反弹",
                    "snippet": "科技成长方向领涨",
                    "source": "测试来源",
                    "published_date": "2026-05-06",
                    "url": long_url,
                }
            ],
        )

        assert long_url not in prompt
        assert "URL: https://example.com/redirect?" in prompt
        assert ("x" * 220) not in prompt

    def test_market_review_includes_concept_rankings_in_prompt_payload_and_tables(self):
        from src.application.market.market_analyzer import MarketIndex, MarketOverview

        ma = self._make_market_analyzer_with_mock_generate_text(return_value="复盘结果")
        overview = MarketOverview(
            date="2026-03-18",
            indices=[
                MarketIndex(code="000001", name="上证指数", current=3200.0, change_pct=0.6),
            ],
            top_sectors=[{"name": "半导体", "change_pct": 2.35}],
            bottom_sectors=[{"name": "煤炭", "change_pct": -1.1}],
            top_concepts=[{"name": "机器人概念", "change_pct": 4.2}],
            bottom_concepts=[{"name": "转基因", "change_pct": -2.05}],
        )

        prompt = ma._build_review_prompt(overview, [])
        table_block = ma._build_sector_block(overview)
        payload = ma.build_market_review_payload(
            overview,
            [],
            "A股复盘报告",
            market_light_snapshot={"dimensions": {"breadth": {"score": 55, "available": False}}},
        )

        assert "行业领涨: 半导体(+2.35%)" in prompt
        assert "概念领涨: 机器人概念(+4.20%)" in prompt
        assert "#### 概念板块领涨 Top 5" in table_block
        assert "| 1 | 机器人概念 | +4.20% |" in table_block
        assert payload["sectors"]["top"][0]["name"] == "半导体"
        assert payload["concepts"]["top"][0]["name"] == "机器人概念"
