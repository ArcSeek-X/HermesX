"""Tests for search news dates."""

from tests.application.intelligence._search_news_freshness_support import (
    SearchService,
    _SearchNewsFreshnessTestCaseFixture,
    _response,
    _result,
    datetime,
    patch,
    timedelta,
    timezone,
    unittest,
)


class SearchNewsFreshnessTestCase(_SearchNewsFreshnessTestCaseFixture, unittest.TestCase):
    def test_effective_window_uses_profile_and_news_max_age(self) -> None:
        """window = min(profile_days, NEWS_MAX_AGE_DAYS)."""
        service, mock_search = self._create_service_with_mock_provider(
            news_max_age_days=3,
            news_strategy_profile="medium",  # 7
        )
        service.search_stock_news("600519", "贵州茅台", max_results=5)
        kwargs = mock_search.call_args[1]
        self.assertEqual(kwargs["days"], 3)

    def test_package_security_news_does_not_trigger_download_filter(self) -> None:
        """Bare package wording in product/security news should not look like a download page."""
        fresh = datetime.now().date().isoformat()
        service, _ = self._create_service_with_mock_provider(
            news_max_age_days=3,
            news_strategy_profile="short",
            response=_response(
                [
                    _result(
                        "金山办公 688111 WPS 安装包被曝漏洞",
                        fresh,
                        snippet="公司回应 WPS 安装包安全漏洞并发布修复计划。",
                        url="https://finance.example.invalid/news/688111-security",
                        source="finance.example.invalid",
                    )
                ]
            ),
        )

        resp = service.search_stock_news("688111", "金山办公", max_results=1)

        self.assertEqual(
            [item.title for item in resp.results],
            ["金山办公 688111 WPS 安装包被曝漏洞"],
        )
        self.assertEqual(resp.results[0].relevance_category, "direct_company_news")

    def test_search_comprehensive_intel_widens_analytical_provider_windows(self) -> None:
        """Market analysis and earnings should request a longer provider lookback."""
        fresh_dt = datetime.now(timezone.utc).replace(microsecond=0)
        fresh_text = fresh_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        service, mock_search = self._create_service_with_mock_provider(
            news_max_age_days=3,
            news_strategy_profile="short",
        )
        mock_search.side_effect = [
            _response([_result("latest_news", fresh_text)]),
            _response([_result("market_analysis", None)]),
            _response([_result("risk_check", fresh_text)]),
            _response([_result("announcement_item", fresh_text)]),
            _response([_result("earnings", None)]),
        ]

        with patch("src.application.intelligence.search_service.time.sleep"):
            intel = service.search_comprehensive_intel(
                stock_code="600519",
                stock_name="贵州茅台",
                max_searches=5,
            )

        self.assertIn("earnings", intel)
        self.assertEqual(
            [call[1]["days"] for call in mock_search.call_args_list],
            [
                3,
                service.ANALYTICAL_INTEL_LOOKBACK_DAYS,
                3,
                3,
                service.ANALYTICAL_INTEL_LOOKBACK_DAYS,
            ],
        )

    def test_search_comprehensive_intel_analytical_keeps_unknown_dates_and_crops_by_window(self) -> None:
        """Analytical dimensions keep unknown-date results while clipping known results to 180 days."""
        today = datetime.now().date()
        very_old = (today - timedelta(days=220)).isoformat()
        in_window = (today - timedelta(days=170)).isoformat()
        fresh_dt = datetime.now(timezone.utc).replace(microsecond=0)
        fresh_text = fresh_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        service, mock_search = self._create_service_with_mock_provider(
            news_max_age_days=3,
            news_strategy_profile="short",
        )
        mock_search.side_effect = [
            _response([_result("latest_news", fresh_text)]),
            _response([
                _result("market_analysis_too_old", very_old),
                _result("market_analysis_unknown", None),
                _result("market_analysis_in_window", in_window),
            ]),
            _response([_result("risk_check", fresh_text)]),
            _response([_result("announcement_item", fresh_text)]),
            _response([
                _result("earnings_too_old", very_old),
                _result("earnings_unknown", None),
                _result("earnings_in_window", in_window),
            ]),
        ]

        with patch("src.application.intelligence.search_service.time.sleep"):
            intel = service.search_comprehensive_intel(
                stock_code="600519",
                stock_name="贵州茅台",
                max_searches=5,
            )

        self.assertEqual(
            [item.title for item in intel["market_analysis"].results],
            ["market_analysis_unknown", "market_analysis_in_window"],
        )
        self.assertIsNone(intel["market_analysis"].results[0].published_date)
        self.assertEqual(intel["market_analysis"].results[1].published_date, in_window)
        self.assertEqual(
            [item.title for item in intel["earnings"].results],
            ["earnings_unknown", "earnings_in_window"],
        )
        self.assertIsNone(intel["earnings"].results[0].published_date)
        self.assertEqual(intel["earnings"].results[1].published_date, in_window)

    def test_search_comprehensive_intel_etf_risk_check_keeps_unknown_dates(self) -> None:
        """ETF risk_check should avoid strict freshness filtering."""
        fresh_dt = datetime.now(timezone.utc).replace(microsecond=0)
        fresh_text = fresh_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        expected_fresh_date = fresh_dt.astimezone().date().isoformat()

        service, mock_search = self._create_service_with_mock_provider(
            news_max_age_days=3,
            news_strategy_profile="short",
        )
        mock_search.side_effect = [
            _response([_result("latest_news", fresh_text)]),
            _response([_result("market_analysis_unknown", None)]),
            _response([_result("risk_unknown", None)]),
        ]

        with patch("src.application.intelligence.search_service.time.sleep"):
            intel = service.search_comprehensive_intel(
                stock_code="510300",
                stock_name="沪深300ETF",
                max_searches=3,
            )

        self.assertEqual(intel["latest_news"].results[0].published_date, expected_fresh_date)
        self.assertEqual([item.title for item in intel["market_analysis"].results], ["market_analysis_unknown"])
        self.assertIsNone(intel["market_analysis"].results[0].published_date)
        self.assertEqual([item.title for item in intel["risk_check"].results], ["risk_unknown"])
        self.assertIsNone(intel["risk_check"].results[0].published_date)

    def test_effective_window_helper_has_no_side_effect(self) -> None:
        """_effective_news_window_days should not mutate stored news_window_days."""
        service, _ = self._create_service_with_mock_provider(
            news_max_age_days=3,
            news_strategy_profile="short",
        )
        service.news_window_days = 99
        resolved = service._effective_news_window_days()
        self.assertEqual(resolved, 3)
        self.assertEqual(service.news_window_days, 99)

    def test_unix_timestamp_normalizes_to_local_date(self) -> None:
        """Unix timestamp should be converted to local date before window filtering."""
        dt_utc = datetime(2026, 3, 15, 23, 30, tzinfo=timezone.utc)
        timestamp = str(int(dt_utc.timestamp()))
        expected_local_date = dt_utc.astimezone().date()
        parsed = SearchService._normalize_news_publish_date(timestamp)
        self.assertEqual(parsed, expected_local_date)

    def test_iso_utc_string_normalizes_to_local_date(self) -> None:
        """ISO datetime with timezone should be converted to local date."""
        dt_utc = datetime(2026, 3, 15, 23, 30, tzinfo=timezone.utc)
        iso_text = "2026-03-15T23:30:00Z"
        expected_local_date = dt_utc.astimezone().date()
        parsed = SearchService._normalize_news_publish_date(iso_text)
        self.assertEqual(parsed, expected_local_date)

    def test_rfc_utc_string_normalizes_to_local_date(self) -> None:
        """RFC datetime with timezone should be converted to local date."""
        dt_utc = datetime(2026, 3, 15, 23, 30, tzinfo=timezone.utc)
        rfc_text = "Sun, 15 Mar 2026 23:30:00 +0000"
        expected_local_date = dt_utc.astimezone().date()
        parsed = SearchService._normalize_news_publish_date(rfc_text)
        self.assertEqual(parsed, expected_local_date)
