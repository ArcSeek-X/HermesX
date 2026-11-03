"""Tests for multi agent stock scope."""

from tests.application.agent._multi_agent_support import (
    _COMMON_WORDS,
    _TestExtractStockCodeFixture,
    _TestStockScopeResolutionFixture,
    _extract_stock_code,
    resolve_stock_scope,
    unittest,
)


class TestExtractStockCode(_TestExtractStockCodeFixture, unittest.TestCase):
    def test_a_share_plain(self):
        self.assertEqual(_extract_stock_code("600519"), "600519")

    def test_a_share_chinese_prefix(self):
        """Critical: Chinese char + digits must still match (no \\b)."""
        self.assertEqual(_extract_stock_code("分析600519"), "600519")

    def test_a_share_chinese_suffix(self):
        self.assertEqual(_extract_stock_code("600519怎么样"), "600519")

    def test_a_share_in_sentence(self):
        self.assertEqual(_extract_stock_code("请帮我看看600519的走势"), "600519")

    def test_a_share_with_prefix_0(self):
        self.assertEqual(_extract_stock_code("分析000858"), "000858")

    def test_a_share_with_prefix_3(self):
        self.assertEqual(_extract_stock_code("分析300750"), "300750")

    def test_a_share_not_match_7_digits(self):
        """Should not match 7-digit number."""
        self.assertEqual(_extract_stock_code("1234567"), "")

    def test_a_share_embedded_in_longer_number(self):
        """Should not extract from within a longer number."""
        self.assertEqual(_extract_stock_code("86006005190001"), "")

    def test_hk_lowercase(self):
        self.assertEqual(_extract_stock_code("look at hk00700"), "HK00700")

    def test_hk_uppercase(self):
        self.assertEqual(_extract_stock_code("HK00700 analysis"), "HK00700")

    def test_hk_chinese(self):
        self.assertEqual(_extract_stock_code("分析hk00700"), "HK00700")

    def test_hk_not_match_alpha_prefix(self):
        """Letters before 'hk' should not prevent match."""
        # "xhk00700" has alpha before hk, lookbehind should block
        self.assertNotEqual(_extract_stock_code("xhk00700"), "HK00700")

    def test_us_ticker(self):
        self.assertEqual(_extract_stock_code("analyze AAPL"), "AAPL")

    def test_us_ticker_in_chinese(self):
        self.assertEqual(_extract_stock_code("看看TSLA"), "TSLA")

    def test_us_ticker_5_chars(self):
        self.assertEqual(_extract_stock_code("check GOOGL"), "GOOGL")

    def test_lowercase_us_ticker_with_analysis_hint(self):
        self.assertEqual(_extract_stock_code("分析tsla"), "TSLA")

    def test_lowercase_us_ticker_bare(self):
        self.assertEqual(_extract_stock_code("tsla"), "TSLA")

    def test_bse_code_with_8_prefix(self):
        self.assertEqual(_extract_stock_code("分析830799"), "830799")

    def test_bse_code_with_92_prefix(self):
        self.assertEqual(_extract_stock_code("看看920748"), "920748")

    def test_common_word_buy(self):
        self.assertEqual(_extract_stock_code("should I BUY"), "")

    def test_common_word_sell(self):
        self.assertEqual(_extract_stock_code("should I SELL"), "")

    def test_common_word_hold(self):
        self.assertEqual(_extract_stock_code("should I HOLD"), "")

    def test_common_word_etf(self):
        self.assertEqual(_extract_stock_code("what about ETF"), "")

    def test_common_word_rsi(self):
        self.assertEqual(_extract_stock_code("RSI is high"), "")

    def test_common_word_macd(self):
        self.assertEqual(_extract_stock_code("check MACD"), "")

    def test_common_word_stock(self):
        self.assertEqual(_extract_stock_code("good STOCK pick"), "")

    def test_common_word_trend(self):
        self.assertEqual(_extract_stock_code("the TREND is up"), "")

    def test_finance_abbrev_excluded(self):
        for text in [
            "TTM",
            "市盈率 TTM 怎么看",
            "PE 怎么看",
            "PE TTM",
            "WHAT IS PE",
            "PE IS HIGH",
            "WHAT IS TTM",
            "YOY",
            "QOQ",
            "EBITDA",
            "DCF",
            "CAGR",
        ]:
            with self.subTest(text=text):
                self.assertEqual(_extract_stock_code(text), "")

    def test_finance_abbrev_before_real_ticker(self):
        self.assertEqual(_extract_stock_code("PE AAPL 怎么看"), "AAPL")
        self.assertEqual(_extract_stock_code("TTM AAPL 怎么看"), "AAPL")
        self.assertEqual(_extract_stock_code("WHAT IS PE AAPL"), "AAPL")

    def test_a_share_takes_priority_over_us(self):
        """When both A-share code and US ticker appear, A-share wins."""
        self.assertEqual(_extract_stock_code("600519 vs AAPL"), "600519")

    def test_empty_string(self):
        self.assertEqual(_extract_stock_code(""), "")

    def test_no_code(self):
        self.assertEqual(_extract_stock_code("hello world"), "")

    def test_single_char_uppercase(self):
        """Single uppercase letter should not match."""
        self.assertEqual(_extract_stock_code("I think"), "")

    def test_lowercase_not_us_ticker(self):
        """Lowercase letters should not match US regex."""
        self.assertEqual(_extract_stock_code("analyze aapl"), "")

    def test_common_words_set_completeness(self):
        """Ensure critical finance terms are in _COMMON_WORDS."""
        expected_in_set = {
            "BUY", "SELL", "HOLD", "ETF", "IPO", "RSI", "MACD", "STOCK", "TREND",
            "TTM", "PE", "YOY", "QOQ", "EBITDA", "DCF", "CAGR", "KDJ",
            "IS", "WHAT", "HIGH",
        }
        self.assertTrue(expected_in_set.issubset(_COMMON_WORDS))


class TestStockScopeResolution(_TestStockScopeResolutionFixture, unittest.TestCase):
    def test_maintain_keeps_current_stock_for_finance_abbrev_followup(self):
        result = resolve_stock_scope(
            "如果不考虑 TTM 呢",
            {"stock_code": "600519", "stock_name": "匿名标的"},
        )

        self.assertEqual(result.stock_scope.mode, "maintain")
        self.assertEqual(result.effective_context["stock_code"], "600519")
        self.assertEqual(result.effective_context["stock_name"], "匿名标的")
        self.assertEqual(result.stock_scope.allowed_stock_codes, {"600519"})

    def test_switch_clears_old_stock_context_fields(self):
        result = resolve_stock_scope(
            "换成 AAPL 看看",
            {
                "stock_code": "600519",
                "stock_name": "匿名标的",
                "previous_analysis_summary": {"summary": "old"},
                "previous_strategy": {"action": "hold"},
                "previous_price": 1800,
                "previous_change_pct": 1.2,
                "realtime_quote": {"price": 1800},
                "analysis_context_pack_summary": "old pack",
                "report_language": "zh",
            },
        )

        self.assertEqual(result.stock_scope.mode, "switch")
        self.assertEqual(result.stock_scope.expected_stock_code, "AAPL")
        self.assertEqual(result.stock_scope.allowed_stock_codes, {"AAPL"})
        self.assertEqual(result.effective_context["stock_code"], "AAPL")
        self.assertEqual(result.effective_context["stock_name"], "")
        self.assertEqual(result.effective_context["report_language"], "zh")
        for stale_key in (
            "previous_analysis_summary",
            "previous_strategy",
            "previous_price",
            "previous_change_pct",
            "realtime_quote",
            "analysis_context_pack_summary",
        ):
            self.assertNotIn(stale_key, result.effective_context)

    def test_switch_allows_single_new_code_when_current_code_is_mentioned(self):
        result = resolve_stock_scope(
            "换成 AAPL 看看，不考虑 600519",
            {"stock_code": "600519", "stock_name": "匿名标的"},
        )

        self.assertEqual(result.stock_scope.mode, "switch")
        self.assertEqual(result.stock_scope.expected_stock_code, "AAPL")
        self.assertEqual(result.stock_scope.allowed_stock_codes, {"AAPL"})
        self.assertEqual(result.effective_context["stock_code"], "AAPL")
        self.assertEqual(result.effective_context["stock_name"], "")

    def test_compare_allows_multiple_codes_without_polluting_current_context(self):
        result = resolve_stock_scope(
            "比较 600519 和 AAPL",
            {"stock_code": "600519", "stock_name": "匿名标的"},
        )

        self.assertEqual(result.stock_scope.mode, "compare")
        self.assertEqual(result.effective_context["stock_code"], "600519")
        self.assertEqual(result.effective_context["stock_name"], "匿名标的")
        self.assertEqual(result.stock_scope.allowed_stock_codes, {"600519", "AAPL"})

    def test_compare_allows_plain_five_digit_hk_code(self):
        result = resolve_stock_scope(
            "比较 01810 和 AAPL",
            {"stock_code": "600519", "stock_name": "匿名标的"},
        )

        self.assertEqual(result.stock_scope.mode, "compare")
        self.assertEqual(result.effective_context["stock_code"], "600519")
        self.assertEqual(result.effective_context["stock_name"], "匿名标的")
        self.assertEqual(result.stock_scope.allowed_stock_codes, {"600519", "HK01810", "AAPL"})

    def test_compare_hints_allow_multiple_codes_without_switching_context(self):
        cases = [
            "分析 600519 和 AAPL 的差异",
            "AAPL 相比 600519 怎么样",
            "和 AAPL 的差异怎么看",
        ]

        for message in cases:
            with self.subTest(message=message):
                result = resolve_stock_scope(
                    message,
                    {"stock_code": "600519", "stock_name": "匿名标的"},
                )

                self.assertEqual(result.stock_scope.mode, "compare")
                self.assertEqual(result.effective_context["stock_code"], "600519")
                self.assertEqual(result.effective_context["stock_name"], "匿名标的")
                self.assertEqual(result.stock_scope.allowed_stock_codes, {"600519", "AAPL"})

    def test_multiple_explicit_codes_are_compare_scope(self):
        cases = [
            ("AAPL 和 TSLA 哪个更值得买", {"600519", "AAPL", "TSLA"}),
            ("AAPL 和 TSLA 谁更适合", {"600519", "AAPL", "TSLA"}),
            ("分析 AAPL 和 TSLA", {"600519", "AAPL", "TSLA"}),
        ]

        for message, expected_allowed in cases:
            with self.subTest(message=message):
                result = resolve_stock_scope(
                    message,
                    {"stock_code": "600519", "stock_name": "匿名标的"},
                )

                self.assertEqual(result.stock_scope.mode, "compare")
                self.assertEqual(result.effective_context["stock_code"], "600519")
                self.assertEqual(result.effective_context["stock_name"], "匿名标的")
                self.assertEqual(result.stock_scope.allowed_stock_codes, expected_allowed)

    def test_multiple_lowercase_explicit_codes_are_compare_scope_with_choice_hint(self):
        result = resolve_stock_scope(
            "aapl 和 tsla 哪个更值得买",
            {"stock_code": "600519", "stock_name": "匿名标的"},
        )

        self.assertEqual(result.stock_scope.mode, "compare")
        self.assertEqual(result.effective_context["stock_code"], "600519")
        self.assertEqual(result.stock_scope.allowed_stock_codes, {"600519", "AAPL", "TSLA"})

    def test_single_stock_difference_phrase_still_switches_context(self):
        result = resolve_stock_scope(
            "分析 AAPL 的差异化优势",
            {"stock_code": "600519", "stock_name": "匿名标的"},
        )

        self.assertEqual(result.stock_scope.mode, "switch")
        self.assertEqual(result.stock_scope.expected_stock_code, "AAPL")
        self.assertEqual(result.effective_context["stock_code"], "AAPL")
        self.assertEqual(result.effective_context["stock_name"], "")

    def test_moving_average_indicator_token_does_not_switch_context(self):
        cases = [
            "分析 MA 均线",
            "看看 MA 怎么排列",
            "分析 KDJ 指标",
            "KDJ 怎么看",
        ]

        for message in cases:
            with self.subTest(message=message):
                result = resolve_stock_scope(
                    message,
                    {"stock_code": "600519", "stock_name": "匿名标的"},
                )

                self.assertEqual(result.stock_scope.mode, "maintain")
                self.assertEqual(result.stock_scope.expected_stock_code, "600519")
                self.assertEqual(result.stock_scope.allowed_stock_codes, {"600519"})
                self.assertEqual(result.effective_context["stock_code"], "600519")

    def test_dotted_us_ticker_stays_intact_in_scope_resolution(self):
        result = resolve_stock_scope(
            "比较 BRK.B 和 AAPL",
            {"stock_code": "600519", "stock_name": "匿名标的"},
        )

        self.assertEqual(result.stock_scope.mode, "compare")
        self.assertEqual(result.stock_scope.allowed_stock_codes, {"600519", "BRK.B", "AAPL"})
        self.assertEqual(result.effective_context["stock_code"], "600519")

    def test_invalid_context_exchange_token_is_not_trusted_as_current_stock(self):
        result = resolve_stock_scope(
            "继续看",
            {"stock_code": "HK", "stock_name": "港股"},
        )

        self.assertEqual(result.stock_scope.mode, "maintain")
        self.assertEqual(result.stock_scope.expected_stock_code, "")
        self.assertEqual(result.stock_scope.allowed_stock_codes, set())
        self.assertNotIn("stock_code", result.effective_context)
        self.assertNotIn("stock_name", result.effective_context)

    def test_compare_does_not_treat_exchange_affixes_as_standalone_tickers(self):
        cases = [
            ("比较 01810 和 AAPL", {"600519", "HK01810", "AAPL"}, set()),
            ("比较 1810.HK 和 AAPL", {"600519", "HK01810", "AAPL"}, {"HK"}),
            ("比较 0700.HK 和 600519", {"600519", "HK00700"}, {"HK"}),
            ("比较 600519.SH 和 AAPL", {"600519", "AAPL"}, {"SH"}),
            ("比较 000001.SZ 和 AAPL", {"600519", "000001", "AAPL"}, {"SZ"}),
            ("比较 600519.SS 和 AAPL", {"600519", "AAPL"}, {"SS"}),
            ("比较 1810.hk 和 tsla", {"600519", "HK01810", "TSLA"}, {"HK"}),
            ("比较 SH600519 和 AAPL", {"600519", "AAPL"}, {"SH"}),
            ("比较 SZ000001 和 AAPL", {"600519", "000001", "AAPL"}, {"SZ"}),
            ("比较 BJ920748 和 AAPL", {"600519", "920748", "AAPL"}, {"BJ"}),
            ("比较 HK01810 和 AAPL", {"600519", "HK01810", "AAPL"}, {"HK"}),
            ("比较 hk01810 和 tsla", {"600519", "HK01810", "TSLA"}, {"HK"}),
            ("比较 600519 SH 和 AAPL", {"600519", "AAPL"}, {"SH"}),
            ("比较 000001 SZ 和 AAPL", {"600519", "000001", "AAPL"}, {"SZ"}),
            ("比较 920748 BJ 和 AAPL", {"600519", "920748", "AAPL"}, {"BJ"}),
            ("比较 01810 HK 和 AAPL", {"600519", "HK01810", "AAPL"}, {"HK"}),
            ("比较 600519 SS 和 AAPL", {"600519", "AAPL"}, {"SS"}),
        ]

        for message, expected_allowed, forbidden_tokens in cases:
            with self.subTest(message=message):
                result = resolve_stock_scope(
                    message,
                    {"stock_code": "600519", "stock_name": "匿名标的"},
                )

                self.assertEqual(result.stock_scope.mode, "compare")
                self.assertEqual(result.stock_scope.allowed_stock_codes, expected_allowed)
                for token in forbidden_tokens:
                    self.assertNotIn(token, result.stock_scope.allowed_stock_codes)

    def test_switch_recognizes_lowercase_us_ticker_with_explicit_hint(self):
        result = resolve_stock_scope(
            "分析tsla",
            {"stock_code": "600519", "stock_name": "匿名标的"},
        )

        self.assertEqual(result.stock_scope.mode, "switch")
        self.assertEqual(result.stock_scope.expected_stock_code, "TSLA")
        self.assertEqual(result.effective_context["stock_code"], "TSLA")
        self.assertEqual(result.effective_context["stock_name"], "")

    def test_compare_recognizes_lowercase_us_tickers(self):
        result = resolve_stock_scope(
            "比较 600519 和 tsla",
            {"stock_code": "600519", "stock_name": "匿名标的"},
        )

        self.assertEqual(result.stock_scope.mode, "compare")
        self.assertEqual(result.effective_context["stock_code"], "600519")
        self.assertEqual(result.stock_scope.allowed_stock_codes, {"600519", "TSLA"})
