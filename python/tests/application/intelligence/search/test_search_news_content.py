"""Tests for search news content."""

from tests.application.intelligence._search_news_freshness_support import (
    MagicMock,
    SearchResult,
    SearchService,
    SimpleNamespace,
    _SearchNewsFreshnessTestCaseFixture,
    _response,
    _result,
    datetime,
    unittest,
)


class SearchNewsFreshnessTestCase(_SearchNewsFreshnessTestCaseFixture, unittest.TestCase):
    def test_download_like_news_without_size_or_url_hints_is_filtered(self) -> None:
        """Content-only Android/download signals should still trigger low-quality filtering."""
        fresh = datetime.now().date().isoformat()
        service, _ = self._create_service_with_mock_provider(
            news_max_age_days=3,
            news_strategy_profile="short",
            response=_response(
                [
                    _result(
                        "腾讯控股 00700 官方版客户端安卓版下载",
                        fresh,
                        snippet="点此获取最新版安卓版客户端，支持一键下载安装包。",
                        url="https://finance.example.invalid/tencent/stock/00700",
                        source="finance.example.invalid",
                    ),
                    _result(
                        "腾讯控股 00700 发布回购公告",
                        fresh,
                        snippet="腾讯控股披露股份回购公告。",
                        source="hkexnews",
                    ),
                ]
            ),
        )

        resp = service.search_stock_news("00700.HK", "腾讯控股", max_results=2)

        self.assertEqual([item.title for item in resp.results], ["腾讯控股 00700 发布回购公告"])

    def test_url_only_app_route_does_not_drop_direct_stock_news(self) -> None:
        """App-style news hosts or paths need content evidence before admission drops."""
        fresh = datetime.now().date().isoformat()
        service, _ = self._create_service_with_mock_provider(
            news_max_age_days=3,
            news_strategy_profile="short",
            response=_response(
                [
                    _result(
                        "腾讯控股 00700 发布回购公告",
                        fresh,
                        snippet="腾讯控股披露股份回购公告，成交维持活跃。",
                        url="https://app.finance.example.invalid/apps/markets/00700",
                        source="app.finance.example.invalid",
                    )
                ]
            ),
        )

        resp = service.search_stock_news("00700.HK", "腾讯控股", max_results=1)

        self.assertEqual([item.title for item in resp.results], ["腾讯控股 00700 发布回购公告"])
        self.assertEqual(resp.results[0].relevance_category, "direct_company_news")

    def test_url_backed_app_rating_listing_is_filtered(self) -> None:
        """App-store URL plus version/rating metrics should be treated as listing noise."""
        fresh = datetime.now().date().isoformat()
        service, _ = self._create_service_with_mock_provider(
            news_max_age_days=3,
            news_strategy_profile="short",
            response=_response(
                [
                    _result(
                        "腾讯控股 00700 app store rating",
                        fresh,
                        snippet="4.8 stars, 10M downloads, version 12.8 for mobile app users.",
                        url="https://apps.example.invalid/tencent/00700",
                        source="apps.example.invalid",
                    ),
                    _result(
                        "腾讯控股 00700 发布回购公告",
                        fresh,
                        snippet="腾讯控股披露股份回购公告。",
                        url="https://finance.example.invalid/news/00700-buyback",
                        source="finance.example.invalid",
                    ),
                ]
            ),
        )

        resp = service.search_stock_news("00700.HK", "腾讯控股", max_results=1)

        self.assertEqual([item.title for item in resp.results], ["腾讯控股 00700 发布回购公告"])

    def test_content_moderation_pornography_phrase_does_not_trigger_adult_spam_filter(self) -> None:
        """Content-safety/regulatory news can mention 色情 without being adult-service spam."""
        fresh = datetime.now().date().isoformat()
        service, _ = self._create_service_with_mock_provider(
            news_max_age_days=3,
            news_strategy_profile="short",
            response=_response(
                [
                    _result(
                        "腾讯控股 00700 加强色情低俗内容治理",
                        fresh,
                        snippet="腾讯控股升级内容安全体系，持续治理色情低俗内容风险。",
                        url="https://finance.example.invalid/news/00700-content-safety",
                        source="finance.example.invalid",
                    )
                ]
            ),
        )

        resp = service.search_stock_news("00700.HK", "腾讯控股", max_results=1)

        self.assertEqual(
            [item.title for item in resp.results],
            ["腾讯控股 00700 加强色情低俗内容治理"],
        )
        self.assertEqual(resp.results[0].relevance_category, "direct_company_news")

    def test_label_only_official_source_is_honored_without_url(self) -> None:
        """Exact official labels without URL should still receive official-source treatment."""
        fresh = datetime.now().date().isoformat()
        service, _ = self._create_service_with_mock_provider(
            news_max_age_days=3,
            news_strategy_profile="short",
            response=_response(
                [
                    SearchResult(
                        title="董事会公告",
                        snippet="股份回购事项。",
                        url="",
                        source="hkexnews",
                        published_date=fresh,
                    ),
                    _result(
                        "腾讯控股 00700 发布回购公告",
                        fresh,
                        snippet="腾讯控股披露股份回购公告。",
                        url="https://finance.example.invalid/news/00700-buyback",
                        source="finance.example.invalid",
                    ),
                ]
            ),
        )

        resp = service.search_stock_news("00700.HK", "腾讯控股", max_results=2)

        self.assertEqual(
            [item.title for item in resp.results],
            ["腾讯控股 00700 发布回购公告", "董事会公告"],
        )
        official_result = resp.results[1]
        self.assertGreater(official_result.relevance_score or 0, 0)
        self.assertIn("来源接近公告或交易所渠道", official_result.relevance_reasons)

    def test_full_chinese_official_source_label_is_honored_without_url(self) -> None:
        """Full Chinese exchange labels without URL should retain official-source treatment."""
        fresh = datetime.now().date().isoformat()
        service, _ = self._create_service_with_mock_provider(
            news_max_age_days=3,
            news_strategy_profile="short",
            response=_response(
                [
                    SearchResult(
                        title="上市公司公告",
                        snippet="股份回购事项。",
                        url="",
                        source="上海证券交易所",
                        published_date=fresh,
                    ),
                    _result(
                        "贵州茅台 600519 发布回购公告",
                        fresh,
                        snippet="贵州茅台披露股份回购公告。",
                        url="https://finance.example.invalid/news/600519-buyback",
                        source="finance.example.invalid",
                    ),
                ]
            ),
        )

        resp = service.search_stock_news("600519", "贵州茅台", max_results=2)

        self.assertEqual(
            [item.title for item in resp.results],
            ["贵州茅台 600519 发布回购公告", "上市公司公告"],
        )
        official_result = resp.results[1]
        self.assertGreater(official_result.relevance_score or 0, 0)
        self.assertIn("来源接近公告或交易所渠道", official_result.relevance_reasons)

    def test_common_word_us_ticker_does_not_match_title_case_words(self) -> None:
        """Bare alphabetic tickers should not turn ordinary words into direct hits."""
        fresh = datetime.now().date().isoformat()
        service = SearchService(
            bocha_keys=["dummy_key"],
            searxng_public_instances_enabled=False,
            news_max_age_days=3,
            news_strategy_profile="short",
        )
        p1 = SimpleNamespace(
            is_available=True,
            name="GenericProvider",
            search=MagicMock(
                return_value=_response(
                    [
                        _result(
                            "All investors brace for inflation data",
                            fresh,
                            snippet="Market participants watch a broad macro update.",
                        )
                    ]
                )
            ),
        )
        p2 = SimpleNamespace(
            is_available=True,
            name="CompanyProvider",
            search=MagicMock(
                return_value=_response(
                    [
                        _result(
                            "ALL Allstate quarterly earnings beat expectations",
                            fresh,
                            snippet="Allstate revenue guidance improved after quarterly results.",
                        )
                    ]
                )
            ),
        )
        service._providers = [p1, p2]

        resp = service.search_stock_news("ALL", "Allstate", max_results=1)

        self.assertEqual(resp.results[0].title, "ALL Allstate quarterly earnings beat expectations")
        self.assertEqual(resp.results[0].relevance_category, "direct_company_news")
        p1.search.assert_called_once()
        p2.search.assert_called_once()
