"""Tests for analysis history lifecycle."""

from tests.application.history._analysis_history_support import (
    AnalysisHistory,
    AnalysisResult,
    BacktestResult,
    DecisionSignalFeedbackRecord,
    DecisionSignalOutcomeRecord,
    DecisionSignalRecord,
    HistoryService,
    MagicMock,
    Path,
    SimpleNamespace,
    TestClient,
    _AnalysisHistoryTestCaseFixture,
    _market_phase_summary,
    apply_daily_market_context_guardrail,
    create_app,
    datetime,
    delete_history_by_code,
    get_history_detail,
    get_history_list,
    get_stock_bar,
    json,
    patch,
    unittest,
)


class AnalysisHistoryTestCase(_AnalysisHistoryTestCaseFixture, unittest.TestCase):
    def test_history_timestamps_include_server_timezone_offset(self) -> None:
        serialized = HistoryService.serialize_created_at(datetime(2026, 7, 11, 0, 30))

        self.assertIsNotNone(serialized)
        self.assertRegex(serialized or "", r"[+-]\d{2}:\d{2}$")

    def test_history_query_failure_is_not_returned_as_an_empty_success(self) -> None:
        db = MagicMock()
        db.get_analysis_history_paginated.side_effect = RuntimeError("database unavailable")

        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            HistoryService(db).get_history_list(page=1, limit=20)

        if get_history_list is None:
            self.skipTest("fastapi is not installed in this test environment")

        with self.assertRaises(Exception) as raised:
            get_history_list(
                stock_code=None,
                report_type=None,
                start_date=None,
                end_date=None,
                page=1,
                limit=20,
                service=self._history_service(db),
            )

        self.assertEqual(getattr(raised.exception, "status_code", None), 500)

    def test_delete_history_by_code_deletes_more_than_one_lookup_batch(self) -> None:
        if delete_history_by_code is None:
            self.skipTest("fastapi is not installed in this test environment")

        remaining = {record_id: SimpleNamespace(id=record_id) for record_id in range(1, 10_002)}
        db = MagicMock()

        def get_records(*, code, limit=20, offset=0, **_kwargs):
            records = list(remaining.values())[offset:offset + limit]
            return records, len(remaining)

        def delete_records(record_ids):
            deleted = 0
            for record_id in record_ids:
                if remaining.pop(record_id, None) is not None:
                    deleted += 1
            return deleted

        db.get_analysis_history_paginated.side_effect = get_records
        db.delete_analysis_history_records.side_effect = delete_records

        response = delete_history_by_code("600519", service=self._history_service(db))

        self.assertEqual(response.deleted, 10_001)
        self.assertEqual(remaining, {})
        self.assertEqual(db.get_analysis_history_paginated.call_count, 2)

    def test_delete_history_by_code_rejects_blank_code_before_query(self) -> None:
        if delete_history_by_code is None:
            self.skipTest("fastapi is not installed in this test environment")

        record_id = self._save_history("query_delete_blank_code")
        with (
            patch.object(
                self.db,
                "get_analysis_history_paginated",
                wraps=self.db.get_analysis_history_paginated,
            ) as query,
            patch.object(
                self.db,
                "delete_analysis_history_records",
                wraps=self.db.delete_analysis_history_records,
            ) as delete,
        ):
            with self.assertRaises(Exception) as raised:
                delete_history_by_code(" ", service=self._history_service())

        self.assertEqual(getattr(raised.exception, "status_code", None), 400)
        query.assert_not_called()
        delete.assert_not_called()
        with self.db.get_session() as session:
            self.assertIsNotNone(session.query(AnalysisHistory).filter(AnalysisHistory.id == record_id).first())

    def test_history_display_resolves_bare_jp_kr_code_from_stock_pool(self) -> None:
        result = self._build_result()
        result.code = "005930"
        result.name = "Samsung Electronics"
        persisted_phase_summary = {
            **_market_phase_summary(),
            "phase": "postmarket",
            "market_local_time": "2025-01-02T16:10:00+09:00",
            "session_date": "2025-01-02",
            "effective_daily_bar_date": "2025-01-02",
            "is_market_open_now": False,
            "is_partial_bar": False,
            "minutes_to_open": 900,
            "minutes_to_close": None,
            "trigger_source": "scheduled_job",
            "analysis_intent": "postmarket",
            "warnings": ["legacy_snapshot"],
        }
        expected_phase_summary = {**persisted_phase_summary, "market": "kr"}
        expected_phase_summary["minutes_to_open"] = None

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_kr_bare",
            report_type="simple",
            news_content="news",
            context_snapshot={"market_phase_summary": persisted_phase_summary},
            save_snapshot=True,
        )
        self.assertGreater(saved, 0)

        service = HistoryService(self.db)
        with patch("src.application.history.read_model.resolve_index_stock_code", return_value="005930.KS"):
            listing = service.get_history_list(page=1, limit=5)
            detail = service.resolve_and_get_detail("query_kr_bare")

        self.assertEqual(listing["items"][0]["stock_code"], "005930.KS")
        self.assertEqual(listing["items"][0]["market_phase_summary"], expected_phase_summary)
        self.assertIsNotNone(detail)
        self.assertEqual(detail["stock_code"], "005930.KS")
        self.assertEqual(detail["market_phase_summary"], expected_phase_summary)

    def test_history_filter_and_stock_bar_merge_bare_and_resolved_jp_kr_codes(self) -> None:
        if get_stock_bar is None:
            self.skipTest("fastapi is not installed in this test environment")

        legacy = self._build_result()
        legacy.code = "005930"
        legacy.name = "Samsung Electronics"
        current = self._build_result()
        current.code = "005930.KS"
        current.name = "Samsung Electronics"

        self.assertGreater(
            self.db.save_analysis_history(
                result=legacy,
                query_id="query_kr_legacy",
                report_type="simple",
                news_content="news",
                context_snapshot={"market_phase_summary": _market_phase_summary()},
                save_snapshot=True,
            ),
            0,
        )
        self.assertGreater(
            self.db.save_analysis_history(
                result=current,
                query_id="query_kr_current",
                report_type="simple",
                news_content="news",
                context_snapshot={"market_phase_summary": _market_phase_summary()},
                save_snapshot=True,
            ),
            0,
        )

        with patch("src.application.history.read_model.resolve_index_stock_code", side_effect=lambda code: "005930.KS" if str(code).split(".", 1)[0] == "005930" else None):
            listing = HistoryService(self.db).get_history_list(stock_code="005930.KS", page=1, limit=10)
            stock_bar = get_stock_bar(
                start_date=None,
                end_date=None,
                limit=10,
                service=self._history_service(),
            )

        self.assertEqual(listing["total"], 2)
        self.assertEqual({item["query_id"] for item in listing["items"]}, {"query_kr_legacy", "query_kr_current"})
        self.assertEqual(len(stock_bar.items), 1)
        self.assertEqual(stock_bar.items[0].stock_code, "005930.KS")
        self.assertEqual(stock_bar.items[0].analysis_count, 2)

    def test_save_analysis_history_persists_sniper_columns_via_shared_parser(self) -> None:
        """迁出 sniper parser 后历史狙击点位列仍按原规则保存。"""
        result = self._build_result()
        result.dashboard = {
            "battle_plan": {
                "sniper_points": {
                    "ideal_buy": "理想买入点：125.5元",
                    "secondary_buy": "1.52-1.53 (回踩MA5/10附近)",
                    "stop_loss": "—",
                    "take_profit": "目标位：150.0元",
                }
            }
        }

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_shared_sniper_parser",
            report_type="simple",
            news_content="新闻摘要",
            context_snapshot=None,
            save_snapshot=False,
        )

        self.assertGreater(saved, 0)
        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(
                AnalysisHistory.query_id == "query_shared_sniper_parser"
            ).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            self.assertEqual(row.ideal_buy, 125.5)
            self.assertEqual(row.secondary_buy, 1.53)
            self.assertIsNone(row.stop_loss)
            self.assertEqual(row.take_profit, 150.0)

    def test_save_analysis_history_persists_model_used(self) -> None:
        """model_used should be persisted in raw_result for history detail."""
        result = self._build_result()
        result.model_used = "gemini/gemini-2.0-flash"

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_003",
            report_type="simple",
            news_content="新闻摘要",
            context_snapshot=None,
            save_snapshot=False
        )
        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == "query_003").first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            payload = json.loads(row.raw_result or "{}")
            self.assertEqual(payload.get("model_used"), "gemini/gemini-2.0-flash")

    def test_history_detail_hides_placeholder_model_used(self) -> None:
        """Placeholder model values should be normalized to None in detail response."""
        result = self._build_result()
        result.model_used = "unknown"

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_004",
            report_type="simple",
            news_content="新闻摘要",
            context_snapshot=None,
            save_snapshot=False
        )
        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == "query_004").first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            record_id = row.id

        service = HistoryService(self.db)
        detail = service.get_history_detail_by_id(record_id)
        self.assertIsNotNone(detail)
        self.assertIsNone(detail.get("model_used"))

    def test_history_list_includes_timeline_summary_fields(self) -> None:
        """History list items expose the fields needed by the same-stock timeline drawer."""
        result = self._build_result()
        result.model_used = "gemini/gemini-2.5-pro"
        context_snapshot = {
            "enhanced_context": {
                "realtime": {
                    "price": "51.5",
                    "change_pct": "-4.61%",
                    "volume_ratio": "1.17",
                    "turnover_rate": "11.46",
                },
            },
            "market_phase_summary": _market_phase_summary(),
        }

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_timeline_summary",
            report_type="detailed",
            news_content="新闻摘要",
            context_snapshot=context_snapshot,
            save_snapshot=True,
        )
        self.assertGreater(saved, 0)

        service = HistoryService(self.db)
        payload = service.get_history_list(stock_code="600519.SH", page=1, limit=5)

        self.assertEqual(payload["total"], 1)
        item = payload["items"][0]
        self.assertEqual(item["stock_code"], "600519")
        self.assertEqual(item["trend_prediction"], "看多")
        self.assertEqual(item["analysis_summary"], "基本面稳健，短期震荡")
        self.assertEqual(item["operation_advice"], "持有")
        self.assertEqual(item["action"], "buy")
        self.assertEqual(item["action_label"], "买入")
        self.assertEqual(item["model_used"], "gemini/gemini-2.5-pro")
        self.assertEqual(item["current_price"], 51.5)
        self.assertEqual(item["change_pct"], -4.61)
        self.assertEqual(item["volume_ratio"], 1.17)
        self.assertEqual(item["turnover_rate"], 11.46)
        self.assertEqual(item["market_phase_summary"]["phase"], "intraday")
        self.assertEqual(item["market_phase_summary"]["minutes_to_close"], 300)

    def test_history_persistence_keeps_softened_operation_advice_from_guardrail(self) -> None:
        """Conservative-market guardrail short operation_advice is persisted and exposed to history list."""
        result = self._build_result()
        result.decision_type = "buy"
        result.operation_advice = "立即买入并积极加仓"

        apply_daily_market_context_guardrail(
            result,
            daily_market_context={
                "region": "cn",
                "trade_date": "2026-06-06",
                "summary": "大盘退潮，高风险，建议观望，仓位上限30%。",
                "risk_tags": ["high_risk", "low_position_cap"],
            },
            report_language="zh",
        )

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_softened_operation_advice",
            report_type="simple",
            news_content="新闻摘要",
            context_snapshot=None,
            save_snapshot=False,
        )
        self.assertGreater(saved, 0)

        service = HistoryService(self.db)
        payload = service.get_history_list(stock_code="600519", page=1, limit=10)

        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["operation_advice"], "观望")
        self.assertLessEqual(len(payload["items"][0]["operation_advice"]), 20)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(
                AnalysisHistory.query_id == "query_softened_operation_advice"
            ).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            self.assertEqual(row.operation_advice, "观望")

    def test_market_review_history_can_be_filtered_without_stock_records(self) -> None:
        """Market review records should be queryable as a dedicated history collection."""
        stock_result = self._build_result()
        market_result = AnalysisResult(
            code="MARKET",
            name="大盘复盘",
            sentiment_score=50,
            trend_prediction="大盘复盘",
            operation_advice="查看复盘",
            analysis_summary="大盘复盘摘要",
        )

        self.assertGreater(
            self.db.save_analysis_history(
                result=stock_result,
                query_id="query_stock_history",
                report_type="detailed",
                news_content="个股正文",
                context_snapshot=None,
                save_snapshot=False,
            ),
            0,
        )
        self.assertGreater(
            self.db.save_analysis_history(
                result=market_result,
                query_id="query_market_review_history",
                report_type="market_review",
                news_content="大盘复盘正文",
                context_snapshot={
                    "report_kind": "market_review",
                    "market_review_region": "jp,kr",
                    "market_review_payload": {
                        "kind": "market_review",
                        "region": "jp,kr",
                        "sections": [{"title": "复盘", "markdown": "结构化正文"}],
                    },
                },
                save_snapshot=True,
            ),
            0,
        )

        service = HistoryService(self.db)
        payload = service.get_history_list(
            stock_code="MARKET",
            report_type="market_review",
            page=1,
            limit=10,
        )

        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["stock_code"], "MARKET")
        self.assertEqual(payload["items"][0]["report_type"], "market_review")
        self.assertEqual(payload["items"][0]["region"], "jp,kr")
        self.assertIsNone(payload["items"][0]["action"])
        self.assertIsNone(payload["items"][0]["action_label"])

        if get_history_list is not None:
            response = get_history_list(
                stock_code="MARKET",
                report_type="market_review",
                start_date=None,
                end_date=None,
                page=1,
                limit=10,
                service=self._history_service(),
            )
            self.assertEqual(response.items[0].region, "jp,kr")

    def test_history_detail_uses_service_resolved_action_fields(self) -> None:
        if get_history_detail is None:
            self.skipTest("fastapi is not installed in this test environment")

        service = MagicMock()
        service.get_latest_fundamental_snapshot.return_value = None
        service.get_detail.return_value = {
            "id": 1,
            "query_id": "query_action_conflict",
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "report_type": "detailed",
            "report_language": "zh",
            "created_at": "2026-05-21T17:40:00",
            "sentiment_score": 45,
            "operation_advice": "持有观察",
            "action": "watch",
            "action_label": "观望",
            "trend_prediction": "震荡",
            "analysis_summary": "等待确认",
            "raw_result": {
                "operation_advice": "持有观察",
                "action": "watch",
                "report_language": "zh",
            },
        }

        response = get_history_detail("query_action_conflict", service=service)

        self.assertEqual(response.summary.operation_advice, "持有观察")
        self.assertEqual(response.summary.action, "watch")
        self.assertEqual(response.summary.action_label, "观望")

    def test_history_list_matches_equivalent_suffixed_stock_codes(self) -> None:
        """Same-stock history should include rows saved with supported suffixed codes."""

        def save_record(code: str, query_id: str) -> None:
            result = self._build_result()
            result.code = code
            if "HK" in code:
                result.name = "腾讯控股"
            saved = self.db.save_analysis_history(
                result=result,
                query_id=query_id,
                report_type="simple",
                news_content="新闻摘要",
                context_snapshot=None,
                save_snapshot=False,
            )
            self.assertGreater(saved, 0)

        save_record("600519.SH", "query_cn_suffix")
        save_record("600519", "query_cn_plain")
        save_record("00700.HK", "query_hk_suffix")
        save_record("HK00700", "query_hk_prefix")

        service = HistoryService(self.db)

        cn_from_suffix = service.get_history_list(stock_code="600519.SH", page=1, limit=10)
        self.assertEqual(cn_from_suffix["total"], 2)
        self.assertEqual(
            {item["stock_code"] for item in cn_from_suffix["items"]},
            {"600519.SH", "600519"},
        )

        cn_from_plain = service.get_history_list(stock_code="600519", page=1, limit=10)
        self.assertEqual(cn_from_plain["total"], 2)
        self.assertEqual(
            {item["stock_code"] for item in cn_from_plain["items"]},
            {"600519.SH", "600519"},
        )

        hk_from_suffix = service.get_history_list(stock_code="00700.HK", page=1, limit=10)
        self.assertEqual(hk_from_suffix["total"], 2)
        self.assertEqual(
            {item["stock_code"] for item in hk_from_suffix["items"]},
            {"00700.HK", "HK00700"},
        )

        hk_from_prefix = service.get_history_list(stock_code="HK00700", page=1, limit=10)
        self.assertEqual(hk_from_prefix["total"], 2)
        self.assertEqual(
            {item["stock_code"] for item in hk_from_prefix["items"]},
            {"00700.HK", "HK00700"},
        )

    def test_history_list_matches_unpadded_hk_suffix_variants(self) -> None:
        """HK short suffix forms (e.g. 1810.HK) should match 5-digit canonical suffix/prefix forms."""

        def save_record(code: str, query_id: str) -> None:
            result = self._build_result()
            result.code = code
            if "HK" in code:
                result.name = "腾讯控股"
            saved = self.db.save_analysis_history(
                result=result,
                query_id=query_id,
                report_type="simple",
                news_content="新闻摘要",
                context_snapshot=None,
                save_snapshot=False,
            )
            self.assertGreater(saved, 0)

        save_record("1810.HK", "query_hk_unpadded")
        save_record("01810.HK", "query_hk_padded")
        save_record("HK01810", "query_hk_prefix")

        service = HistoryService(self.db)

        hk_from_suffix = service.get_history_list(stock_code="01810.HK", page=1, limit=10)
        self.assertEqual(hk_from_suffix["total"], 3)
        self.assertEqual(
            {item["stock_code"] for item in hk_from_suffix["items"]},
            {"1810.HK", "01810.HK", "HK01810"},
        )

        hk_from_prefix = service.get_history_list(stock_code="HK01810", page=1, limit=10)
        self.assertEqual(hk_from_prefix["total"], 3)
        self.assertEqual(
            {item["stock_code"] for item in hk_from_prefix["items"]},
            {"1810.HK", "01810.HK", "HK01810"},
        )

    def test_history_list_matches_sh_and_ss_suffixed_variants(self) -> None:
        """SH suffix and legacy `.SS` variants should be treated as the same A-share stock."""

        def save_record(code: str, query_id: str) -> None:
            result = self._build_result()
            result.code = code
            saved = self.db.save_analysis_history(
                result=result,
                query_id=query_id,
                report_type="simple",
                news_content="新闻摘要",
                context_snapshot=None,
                save_snapshot=False,
            )
            self.assertGreater(saved, 0)

        save_record("600519.SH", "query_cn_sh")
        save_record("600519.SS", "query_cn_ss")
        save_record("600519", "query_cn_plain")

        service = HistoryService(self.db)
        expected = {"600519.SH", "600519.SS", "600519"}

        from_sh = service.get_history_list(stock_code="600519.SH", page=1, limit=10)
        self.assertEqual(from_sh["total"], 3)
        self.assertEqual({item["stock_code"] for item in from_sh["items"]}, expected)

        from_ss = service.get_history_list(stock_code="600519.SS", page=1, limit=10)
        self.assertEqual(from_ss["total"], 3)
        self.assertEqual({item["stock_code"] for item in from_ss["items"]}, expected)

        from_plain = service.get_history_list(stock_code="600519", page=1, limit=10)
        self.assertEqual(from_plain["total"], 3)
        self.assertEqual({item["stock_code"] for item in from_plain["items"]}, expected)

    def test_history_detail_preserves_zero_change_pct(self) -> None:
        """change_pct=0.0（平盘）应原样返回，而不是被当成缺失值丢失。

        Regression for issue #1084: history endpoint used `or` chains that
        treated 0.0 as falsy and silently dropped the daily change.
        """
        if get_history_detail is None:
            self.skipTest("fastapi is not installed in this test environment")

        context_snapshot = {
            "enhanced_context": {
                "realtime": {"price": 100.0, "change_pct": 0.0},
            }
        }
        query_id = "query_change_pct_zero"
        saved = self.db.save_analysis_history(
            result=self._build_result(),
            query_id=query_id,
            report_type="simple",
            news_content="新闻摘要",
            context_snapshot=context_snapshot,
            save_snapshot=True,
        )
        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == query_id).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            record_id = row.id

        report = get_history_detail(str(record_id), service=self._history_service())
        self.assertEqual(report.meta.current_price, 100.0)
        self.assertEqual(report.meta.change_pct, 0.0)

    def test_history_detail_falls_back_to_realtime_quote_raw_change_pct(self) -> None:
        """缺少 enhanced_context.realtime.change_pct 时，应回退到 realtime_quote_raw。

        Regression for issue #1084: previously the realtime_quote_raw fallback
        was only consulted when current_price was missing, so reports with
        price-only enhanced_context lost their change_pct entirely.
        """
        if get_history_detail is None:
            self.skipTest("fastapi is not installed in this test environment")

        context_snapshot = {
            "enhanced_context": {
                "realtime": {"price": 200.0},
            },
            "realtime_quote_raw": {"change_pct": 1.23},
        }
        query_id = "query_change_pct_fallback"
        saved = self.db.save_analysis_history(
            result=self._build_result(),
            query_id=query_id,
            report_type="simple",
            news_content="新闻摘要",
            context_snapshot=context_snapshot,
            save_snapshot=True,
        )
        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == query_id).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            record_id = row.id

        report = get_history_detail(str(record_id), service=self._history_service())
        self.assertEqual(report.meta.current_price, 200.0)
        self.assertEqual(report.meta.change_pct, 1.23)

    @patch("src.auth.is_auth_enabled", return_value=False)
    def test_history_detail_ignores_non_dict_realtime_quote_raw(self, mock_auth) -> None:
        """GET /api/v1/history/{id} should tolerate truthy non-dict realtime_quote_raw."""
        if TestClient is None or create_app is None:
            self.skipTest("fastapi is not installed in this test environment")

        context_snapshot = {
            "enhanced_context": {
                "realtime": {"price": 300.0},
            },
            "realtime_quote_raw": "not-a-dict",
        }
        query_id = "query_change_pct_non_dict_raw"
        saved = self.db.save_analysis_history(
            result=self._build_result(),
            query_id=query_id,
            report_type="simple",
            news_content="新闻摘要",
            context_snapshot=context_snapshot,
            save_snapshot=True,
        )
        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == query_id).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            record_id = row.id

        static_dir = Path(self._temp_dir.name) / "empty-static"
        static_dir.mkdir(exist_ok=True)
        client = TestClient(create_app(static_dir=static_dir))

        response = client.get(f"/api/v1/history/{record_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["current_price"], 300.0)
        self.assertIsNone(payload["meta"]["change_pct"])

    def test_history_detail_accepts_dict_raw_result(self) -> None:
        """_record_to_detail_dict should handle dict raw_result without json.loads errors."""
        result = self._build_result()
        result.model_used = "gemini/gemini-2.0-flash"
        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_005",
            report_type="simple",
            news_content="新闻摘要",
            context_snapshot=None,
            save_snapshot=False
        )
        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == "query_005").first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            row.raw_result = {"model_used": "unknown", "extra": "v"}

            service = HistoryService(self.db)
            detail = service._record_to_detail_dict(row)

        self.assertIsNotNone(detail)
        self.assertIsInstance(detail.get("raw_result"), dict)
        self.assertIsNone(detail.get("model_used"))

    def test_history_detail_prefers_raw_sniper_strings(self) -> None:
        """History detail should display the original sniper point strings from raw_result."""
        result = self._build_result()
        result.dashboard = {
            "battle_plan": {
                "sniper_points": {
                    "ideal_buy": "理想买入点：125.5元",
                    "secondary_buy": "120-121 元分批",
                    "stop_loss": "跌破 110 元止损",
                    "take_profit": "目标位：150.0元",
                }
            }
        }

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_006",
            report_type="simple",
            news_content="新闻摘要",
            context_snapshot=None,
            save_snapshot=False
        )
        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == "query_006").first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            record_id = row.id

        service = HistoryService(self.db)
        detail = service.get_history_detail_by_id(record_id)
        self.assertIsNotNone(detail)
        self.assertEqual(detail.get("ideal_buy"), "理想买入点：125.5元")
        self.assertEqual(detail.get("secondary_buy"), "120-121 元分批")
        self.assertEqual(detail.get("stop_loss"), "跌破 110 元止损")
        self.assertEqual(detail.get("take_profit"), "目标位：150.0元")

    def test_history_detail_falls_back_to_numeric_sniper_columns(self) -> None:
        """History detail should still fall back to stored numeric sniper columns when raw strings are unavailable."""
        result = self._build_result()
        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_007",
            report_type="simple",
            news_content="新闻摘要",
            context_snapshot=None,
            save_snapshot=False
        )
        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(AnalysisHistory.query_id == "query_007").first()
            if row is None:
                self.fail("未找到保存的历史记录")
            row.ideal_buy = 125.5
            row.secondary_buy = 120.0
            row.stop_loss = 110.0
            row.take_profit = 150.0
            row.raw_result = json.dumps({"model_used": "gemini/gemini-2.0-flash"})
            session.commit()
            self.assertEqual(row.id, saved)
            record_id = row.id

        service = HistoryService(self.db)
        detail = service.get_history_detail_by_id(record_id)
        self.assertIsNotNone(detail)
        self.assertEqual(detail.get("ideal_buy"), "125.5")
        self.assertEqual(detail.get("secondary_buy"), "120.0")
        self.assertEqual(detail.get("stop_loss"), "110.0")
        self.assertEqual(detail.get("take_profit"), "150.0")

    def test_history_detail_localizes_english_summary_fields(self) -> None:
        """History detail should localize summary enums for English reports."""
        if get_history_detail is None:
            self.skipTest("fastapi is not installed in this test environment")

        result = AnalysisResult(
            code="AAPL",
            name="股票AAPL",
            sentiment_score=78,
            trend_prediction="看多",
            operation_advice="买入",
            analysis_summary="Momentum remains constructive.",
            report_language="en",
        )

        saved = self.db.save_analysis_history(
            result=result,
            query_id="query_english_detail_001",
            report_type="full",
            news_content="news",
            context_snapshot=None,
            save_snapshot=False,
        )
        self.assertGreater(saved, 0)

        with self.db.get_session() as session:
            row = session.query(AnalysisHistory).filter(
                AnalysisHistory.query_id == "query_english_detail_001"
            ).first()
            if row is None:
                self.fail("未找到保存的历史记录")
            self.assertEqual(row.id, saved)
            record_id = row.id

        report = get_history_detail(str(record_id), service=self._history_service())

        self.assertEqual(report.meta.report_language, "en")
        self.assertEqual(report.meta.stock_name, "Unnamed Stock")
        self.assertEqual(report.summary.operation_advice, "Buy")
        self.assertEqual(report.summary.action, "buy")
        self.assertEqual(report.summary.action_label, "Buy")
        self.assertEqual(report.summary.trend_prediction, "Bullish")
        self.assertEqual(report.summary.sentiment_label, "Bullish")

    def test_delete_analysis_history_records_also_cleans_backtests_and_decision_signals(self) -> None:
        """删除历史记录时应一并清理关联回测结果和决策信号。"""
        record_id = self._save_history("query_delete_001")
        linked_signal_id = None

        with self.db.session_scope() as session:
            session.add(BacktestResult(
                analysis_history_id=record_id,
                code="600519",
                analysis_date=None,
                eval_window_days=10,
                engine_version="v1",
                eval_status="pending",
            ))
            linked_signal = DecisionSignalRecord(
                stock_code="600519",
                stock_name="贵州茅台",
                market="cn",
                source_type="analysis",
                source_report_id=record_id,
                trace_id="trace-delete-linked",
                market_phase="intraday",
                trigger_source="api",
                action="buy",
                action_label="买入",
                reason="linked",
                plan_quality="minimal",
                status="active",
            )
            session.add(linked_signal)
            session.flush()
            linked_signal_id = linked_signal.id
            session.add(DecisionSignalOutcomeRecord(
                signal_id=linked_signal_id,
                horizon="3d",
                engine_version="decision-signal-v1",
                eval_status="completed",
                outcome="hit",
                action="buy",
                market="cn",
                source_type="analysis",
                plan_quality="minimal",
                holding_state="holding",
            ))
            session.add(DecisionSignalFeedbackRecord(
                signal_id=linked_signal_id,
                feedback_value="useful",
                source="api",
            ))
            session.add(DecisionSignalRecord(
                stock_code="000001",
                stock_name="平安银行",
                market="cn",
                source_type="analysis",
                source_report_id=record_id + 999,
                trace_id="trace-delete-unrelated",
                market_phase="intraday",
                trigger_source="api",
                action="watch",
                action_label="观望",
                reason="unrelated",
                plan_quality="minimal",
                status="active",
            ))

        deleted = self.db.delete_analysis_history_records([record_id])
        self.assertEqual(deleted, 1)

        with self.db.get_session() as session:
            self.assertIsNone(session.query(AnalysisHistory).filter(AnalysisHistory.id == record_id).first())
            self.assertEqual(
                session.query(BacktestResult).filter(BacktestResult.analysis_history_id == record_id).count(),
                0,
            )
            self.assertEqual(
                session.query(DecisionSignalRecord).filter(DecisionSignalRecord.source_report_id == record_id).count(),
                0,
            )
            self.assertEqual(
                session.query(DecisionSignalOutcomeRecord).filter(
                    DecisionSignalOutcomeRecord.signal_id == linked_signal_id
                ).count(),
                0,
            )
            self.assertEqual(
                session.query(DecisionSignalFeedbackRecord).filter(
                    DecisionSignalFeedbackRecord.signal_id == linked_signal_id
                ).count(),
                0,
            )
            self.assertEqual(
                session.query(DecisionSignalRecord).filter(DecisionSignalRecord.trace_id == "trace-delete-unrelated").count(),
                1,
            )

    def test_delete_analysis_history_records_keeps_signals_for_nonexistent_history_id(self) -> None:
        """不存在的历史 ID 不应触发弱关联 DecisionSignal 清理。"""
        missing_id = 987654321

        with self.db.session_scope() as session:
            session.add(DecisionSignalRecord(
                stock_code="600519",
                stock_name="贵州茅台",
                market="cn",
                source_type="manual",
                source_report_id=missing_id,
                trace_id="trace-delete-missing-history",
                market_phase="intraday",
                trigger_source="api",
                action="watch",
                action_label="观望",
                reason="manual signal with unverified report id",
                plan_quality="minimal",
                status="active",
            ))

        deleted = self.db.delete_analysis_history_records([missing_id])
        self.assertEqual(deleted, 0)

        with self.db.get_session() as session:
            self.assertEqual(
                session.query(DecisionSignalRecord).filter(
                    DecisionSignalRecord.trace_id == "trace-delete-missing-history"
                ).count(),
                1,
            )

    def test_delete_analysis_history_records_cleans_only_existing_ids_in_mixed_batch(self) -> None:
        """混合存在/不存在 ID 时，只清理实际存在历史记录的关联数据。"""
        record_id = self._save_history("query_delete_mixed")
        missing_id = record_id + 987654

        with self.db.session_scope() as session:
            session.add(BacktestResult(
                analysis_history_id=record_id,
                code="600519",
                analysis_date=None,
                eval_window_days=10,
                engine_version="v1",
                eval_status="pending",
            ))
            session.add(DecisionSignalRecord(
                stock_code="600519",
                stock_name="贵州茅台",
                market="cn",
                source_type="analysis",
                source_report_id=record_id,
                trace_id="trace-delete-mixed-linked",
                market_phase="intraday",
                trigger_source="api",
                action="buy",
                action_label="买入",
                reason="linked",
                plan_quality="minimal",
                status="active",
            ))
            session.add(DecisionSignalRecord(
                stock_code="000001",
                stock_name="平安银行",
                market="cn",
                source_type="manual",
                source_report_id=missing_id,
                trace_id="trace-delete-mixed-missing",
                market_phase="intraday",
                trigger_source="api",
                action="watch",
                action_label="观望",
                reason="weak report id collision",
                plan_quality="minimal",
                status="active",
            ))

        deleted = self.db.delete_analysis_history_records([record_id, missing_id])
        self.assertEqual(deleted, 1)

        with self.db.get_session() as session:
            self.assertIsNone(session.query(AnalysisHistory).filter(AnalysisHistory.id == record_id).first())
            self.assertEqual(
                session.query(BacktestResult).filter(BacktestResult.analysis_history_id == record_id).count(),
                0,
            )
            self.assertEqual(
                session.query(DecisionSignalRecord).filter(
                    DecisionSignalRecord.trace_id == "trace-delete-mixed-linked"
                ).count(),
                0,
            )
            self.assertEqual(
                session.query(DecisionSignalRecord).filter(
                    DecisionSignalRecord.trace_id == "trace-delete-mixed-missing"
                ).count(),
                1,
            )

    @patch("src.auth.is_auth_enabled", return_value=False)
    def test_delete_history_api_deletes_selected_records(self, mock_auth) -> None:
        """DELETE /api/v1/history should remove only the requested records."""
        if TestClient is None or create_app is None:
            self.skipTest("fastapi is not installed in this test environment")

        record_id_1 = self._save_history("query_delete_api_001")
        record_id_2 = self._save_history("query_delete_api_002")

        static_dir = Path(self._temp_dir.name) / "empty-static"
        static_dir.mkdir(exist_ok=True)
        client = TestClient(create_app(static_dir=static_dir))

        response = client.request(
            "DELETE",
            "/api/v1/history",
            json={"record_ids": [record_id_1]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("deleted"), 1)

        with self.db.get_session() as session:
            self.assertIsNone(session.query(AnalysisHistory).filter(AnalysisHistory.id == record_id_1).first())
            self.assertIsNotNone(session.query(AnalysisHistory).filter(AnalysisHistory.id == record_id_2).first())
