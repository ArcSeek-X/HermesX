"""Tests for search news providers."""

from tests.application.intelligence._search_news_freshness_support import (
    MagicMock,
    SearchService,
    SimpleNamespace,
    _SearchNewsFreshnessTestCaseFixture,
    _response,
    _result,
    activate_run_diagnostic_context,
    current_diagnostic_snapshot,
    datetime,
    patch,
    reset_run_diagnostic_context,
    timedelta,
    timezone,
    unittest,
)


class SearchNewsFreshnessTestCase(_SearchNewsFreshnessTestCaseFixture, unittest.TestCase):
    def test_search_stock_news_try_next_provider_when_filtered_empty(self) -> None:
        """If provider-A passes API call but all results are filtered, continue to provider-B."""
        today = datetime.now().date()
        old = (today - timedelta(days=90)).isoformat()
        fresh = today.isoformat()

        service = SearchService(
            bocha_keys=["dummy_key"],
            searxng_public_instances_enabled=False,
            news_max_age_days=3,
            news_strategy_profile="short",
        )

        p1 = SimpleNamespace(
            is_available=True,
            name="P1",
            search=MagicMock(return_value=_response([_result("too_old", old)])),
        )
        p2 = SimpleNamespace(
            is_available=True,
            name="P2",
            search=MagicMock(return_value=_response([_result("fresh", fresh)])),
        )
        service._providers = [p1, p2]

        resp = service.search_stock_news("600519", "贵州茅台", max_results=3)
        self.assertEqual([r.title for r in resp.results], ["fresh"])
        p1.search.assert_called_once()
        p2.search.assert_called_once()

    def test_search_stock_news_records_provider_diagnostics_for_fallback(self) -> None:
        """News search provider attempts should appear in run-flow diagnostics."""
        today = datetime.now().date()
        old = (today - timedelta(days=90)).isoformat()
        fresh = today.isoformat()
        service = SearchService(
            bocha_keys=["dummy_key"],
            searxng_public_instances_enabled=False,
            news_max_age_days=3,
            news_strategy_profile="short",
        )
        tavily = SimpleNamespace(
            is_available=True,
            name="Tavily",
            search=MagicMock(return_value=_response([_result("too_old", old)])),
        )
        searxng = SimpleNamespace(
            is_available=True,
            name="SearXNG",
            search=MagicMock(return_value=_response([_result("贵州茅台 600519 最新公告", fresh)])),
        )
        service._providers = [tavily, searxng]

        token = activate_run_diagnostic_context(
            trace_id="trace-news",
            task_id="task-news",
            query_id="query-news",
            stock_code="600519",
            trigger_source="api",
        )
        try:
            response = service.search_stock_news("600519", "贵州茅台", max_results=3)
            diagnostics = current_diagnostic_snapshot()
        finally:
            reset_run_diagnostic_context(token)

        self.assertEqual([item.title for item in response.results], ["贵州茅台 600519 最新公告"])
        provider_runs = diagnostics["provider_runs"]
        self.assertEqual([run["data_type"] for run in provider_runs], ["news_search", "news_search"])
        self.assertEqual([run["provider"] for run in provider_runs], ["Tavily", "SearXNG"])
        self.assertFalse(provider_runs[0]["success"])
        self.assertTrue(provider_runs[1]["success"])
        self.assertEqual(provider_runs[1]["record_count"], 1)

    def test_search_stock_news_tries_next_provider_when_chinese_context_is_english_only(self) -> None:
        """Chinese-preferred queries should not stop on English-only provider results."""
        fresh = datetime.now().date().isoformat()
        service = SearchService(
            bocha_keys=["dummy_key"],
            searxng_public_instances_enabled=False,
            news_max_age_days=3,
            news_strategy_profile="short",
        )

        p1 = SimpleNamespace(
            is_available=True,
            name="P1",
            search=MagicMock(
                return_value=_response(
                    [
                        _result("English headline", fresh),
                        _result("Another English story", fresh),
                    ]
                )
            ),
        )
        p2 = SimpleNamespace(
            is_available=True,
            name="P2",
            search=MagicMock(return_value=_response([_result("中文资讯", fresh)])),
        )
        service._providers = [p1, p2]

        resp = service.search_stock_news("600519", "贵州茅台", max_results=3)
        self.assertEqual([r.title for r in resp.results], ["中文资讯"])
        p1.search.assert_called_once()
        p2.search.assert_called_once()

    def test_a_share_chinese_sector_provider_beats_higher_scored_english_sector(self) -> None:
        """When no direct hit exists, Chinese-preferred flows should compare language before score."""
        fresh = datetime.now().date().isoformat()
        service = SearchService(
            bocha_keys=["dummy_key"],
            searxng_public_instances_enabled=False,
            news_max_age_days=3,
            news_strategy_profile="short",
        )

        p1 = SimpleNamespace(
            is_available=True,
            name="EnglishSector",
            search=MagicMock(
                return_value=_response(
                    [
                        _result(
                            "Baijiu industry quarterly results improve",
                            fresh,
                            snippet="Sector peers report better market share.",
                            source="sec.gov",
                        )
                    ]
                )
            ),
        )
        p2 = SimpleNamespace(
            is_available=True,
            name="ChineseSector",
            search=MagicMock(
                return_value=_response(
                    [
                        _result(
                            "白酒板块资金回暖",
                            fresh,
                            snippet="消费行业反弹。",
                        )
                    ]
                )
            ),
        )
        service._providers = [p1, p2]

        resp = service.search_stock_news("600519", "贵州茅台", max_results=1)

        self.assertEqual([r.title for r in resp.results], ["白酒板块资金回暖"])
        self.assertEqual(resp.results[0].relevance_category, "sector_related_news")
        p1.search.assert_called_once()
        p2.search.assert_called_once()

    def test_search_stock_news_keeps_english_provider_order_for_us_stock(self) -> None:
        """English stock searches should keep the first successful provider result."""
        fresh = datetime.now().date().isoformat()
        service = SearchService(
            bocha_keys=["dummy_key"],
            searxng_public_instances_enabled=False,
            news_max_age_days=3,
            news_strategy_profile="short",
        )

        p1 = SimpleNamespace(
            is_available=True,
            name="P1",
            search=MagicMock(return_value=_response([_result("Apple earnings beat", fresh)])),
        )
        p2 = SimpleNamespace(
            is_available=True,
            name="P2",
            search=MagicMock(return_value=_response([_result("苹果资讯", fresh)])),
        )
        service._providers = [p1, p2]

        resp = service.search_stock_news("AAPL", "Apple", max_results=3)
        self.assertEqual([r.title for r in resp.results], ["Apple earnings beat"])
        p1.search.assert_called_once()
        p2.search.assert_not_called()

    def test_a_share_direct_company_news_beats_sector_provider_fallback(self) -> None:
        """A-share direct company hits should beat generic sector news from earlier providers."""
        fresh = datetime.now().date().isoformat()
        service = SearchService(
            bocha_keys=["dummy_key"],
            searxng_public_instances_enabled=False,
            news_max_age_days=3,
            news_strategy_profile="short",
        )

        p1 = SimpleNamespace(
            is_available=True,
            name="P1",
            search=MagicMock(
                return_value=_response(
                    [
                        _result(
                            "白酒行业景气度回暖 多只龙头上涨",
                            fresh,
                            snippet="消费板块获得资金关注。",
                        )
                    ]
                )
            ),
        )
        p2 = SimpleNamespace(
            is_available=True,
            name="P2",
            search=MagicMock(
                return_value=_response(
                    [
                        _result("沪指震荡收涨，市场情绪回暖", fresh),
                        _result(
                            "贵州茅台 600519 发布回购公告",
                            fresh,
                            snippet="贵州茅台披露公司公告，董事会审议通过回购方案。",
                            source="cninfo",
                        ),
                    ]
                )
            ),
        )
        service._providers = [p1, p2]

        resp = service.search_stock_news("600519", "贵州茅台", max_results=2)

        self.assertEqual(resp.results[0].title, "贵州茅台 600519 发布回购公告")
        self.assertEqual(resp.results[0].relevance_category, "direct_company_news")
        self.assertIn("股票代码", "；".join(resp.results[0].relevance_reasons or []))
        p1.search.assert_called_once()
        p2.search.assert_called_once()

    def test_a_share_chinese_direct_news_beats_english_direct_provider_fallback(self) -> None:
        """Chinese-preferred queries should keep looking past English-only direct hits."""
        fresh = datetime.now().date().isoformat()
        service = SearchService(
            bocha_keys=["dummy_key"],
            searxng_public_instances_enabled=False,
            news_max_age_days=3,
            news_strategy_profile="short",
        )

        p1 = SimpleNamespace(
            is_available=True,
            name="EnglishDirect",
            search=MagicMock(
                return_value=_response(
                    [
                        _result(
                            "Kweichow Moutai 600519 announces buyback",
                            fresh,
                            snippet="The company reported an updated share repurchase plan.",
                        )
                    ]
                )
            ),
        )
        p2 = SimpleNamespace(
            is_available=True,
            name="ChineseDirect",
            search=MagicMock(
                return_value=_response(
                    [
                        _result(
                            "贵州茅台 600519 发布回购公告",
                            fresh,
                            snippet="贵州茅台披露公司回购公告。",
                        )
                    ]
                )
            ),
        )
        service._providers = [p1, p2]

        resp = service.search_stock_news("600519", "贵州茅台", max_results=1)

        self.assertEqual(resp.results[0].title, "贵州茅台 600519 发布回购公告")
        self.assertEqual(resp.results[0].relevance_category, "direct_company_news")
        p1.search.assert_called_once()
        p2.search.assert_called_once()

    def test_ambiguous_english_name_generic_event_does_not_stop_provider_fallback(self) -> None:
        """Ambiguous title-only names plus broad event words should not count as direct hits."""
        fresh = datetime.now().date().isoformat()
        service = SearchService(
            bocha_keys=["dummy_key"],
            searxng_public_instances_enabled=False,
            news_max_age_days=3,
            news_strategy_profile="short",
        )
        p1 = SimpleNamespace(
            is_available=True,
            name="AmbiguousProvider",
            search=MagicMock(
                return_value=_response(
                    [
                        _result(
                            "Apple stock results improve after harvest update",
                            fresh,
                            snippet="Fruit market coverage tracks inventory and crop supply.",
                        )
                    ]
                )
            ),
        )
        p2 = SimpleNamespace(
            is_available=True,
            name="TickerProvider",
            search=MagicMock(
                return_value=_response(
                    [
                        _result(
                            "AAPL Apple earnings beat analyst expectations",
                            fresh,
                            snippet="Apple revenue guidance improved after quarterly earnings.",
                        )
                    ]
                )
            ),
        )
        service._providers = [p1, p2]

        resp = service.search_stock_news("AAPL", "Apple", max_results=1)

        self.assertEqual(resp.results[0].title, "AAPL Apple earnings beat analyst expectations")
        self.assertEqual(resp.results[0].relevance_category, "direct_company_news")
        p1.search.assert_called_once()
        p2.search.assert_called_once()

    def test_search_stock_news_brave_locale_matches_market_context(self) -> None:
        """Brave locale should follow Chinese-preferred vs US-stock contexts."""
        fresh_dt = datetime.now(timezone.utc).replace(microsecond=0)
        fresh_iso = fresh_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        for stock_code, stock_name, expected_lang, expected_country, title, description in (
            ("600519", "贵州茅台", "zh-hans", "CN", "中文资讯", "中文摘要"),
            ("AAPL", "Apple", "en", "US", "Apple earnings beat", "English summary"),
        ):
            with self.subTest(stock_code=stock_code):
                fake_response = MagicMock()
                fake_response.status_code = 200
                fake_response.json.return_value = {
                    "web": {
                        "results": [
                            {
                                "title": title,
                                "description": description,
                                "url": "https://example.com/news",
                                "age": fresh_iso,
                            }
                        ]
                    }
                }

                with patch("src.infrastructure.search.provider_base.requests.get", return_value=fake_response) as mock_get:
                    service = SearchService(
                        brave_keys=["dummy_key"],
                        searxng_public_instances_enabled=False,
                        news_max_age_days=3,
                        news_strategy_profile="short",
                    )
                    resp = service.search_stock_news(stock_code, stock_name, max_results=1)

                self.assertEqual(len(resp.results), 1)
                params = mock_get.call_args.kwargs["params"]
                self.assertEqual(params["search_lang"], expected_lang)
                self.assertEqual(params["country"], expected_country)
