"""Tests for search news routing."""

from tests.application.intelligence._search_news_freshness_support import (
    SearchResult,
    SearchService,
    _SearchNewsFreshnessTestCaseFixture,
    unittest,
)


class SearchNewsFreshnessTestCase(_SearchNewsFreshnessTestCaseFixture, unittest.TestCase):
    def test_score_news_relevance_english_alias_dedup_prevents_double_count(self) -> None:
        """massif-01 blocker follow-up: alias expansion dedup prevents
        double-counting when legal alias and short alias resolve to same term.
        For AAPL: STOCK_ENGLISH_NAME_MAP['AAPL'] = ('Apple Inc.', 'Apple')
        _company_identity_terms('Apple Inc.') -> ['Apple Inc.', 'Apple']
        _company_identity_terms('Apple') -> ['Apple']
        Without dedup: snippet 'Apple reports earnings beat' would match
        'Apple' twice (once from each alias path) → 16+16=32 direct_signal
        With event term +12 = 44 → direct_company_news (incorrect).
        With dedup: only one 'Apple' term scored → 16 direct_signal
        With event term +12 = 28 → sector_related_news (correct).
        """
        # Setup: generic market title, snippet with only English alias hit
        item = SearchResult(
            title="US stocks mixed after Fed comments",
            snippet="Apple reports earnings beat and revenue grows.",
            url="",
            source=""
        )
        scored = SearchService._score_news_relevance(
            item, stock_code="AAPL", stock_name="苹果"
        )
        # Should NOT be direct (insufficient signal without title hit)
        self.assertEqual(scored.relevance_category, "sector_related_news")
        self.assertLess(scored.relevance_score, 38)
        # Should have exactly one hit on the alias term
        reasons = "；".join(scored.relevance_reasons or [])
        self.assertIn("摘要命中公司英文别名 Apple", reasons)
        self.assertNotIn("标题命中公司英文别名", reasons)
