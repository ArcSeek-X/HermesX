"""Tests for alert worker contracts."""

from tests.integration.alert._alert_worker_support import (
    AlertWorker,
    AsyncMock,
    MagicMock,
    SimpleNamespace,
    _AlertWorkerTestCaseFixture,
    compute_requested_days,
    compute_required_bars,
    date,
    json,
    normalize_indicator_parameters,
    patch,
    pd,
    unittest,
)


class AlertIndicatorHelperTestCase(unittest.TestCase):
    def test_required_bars_and_requested_days_are_stable(self) -> None:
        cases = {
            "ma_price_cross": ({"window": 20, "direction": "above"}, 21),
            "rsi_threshold": ({"period": 12, "threshold": 70, "direction": "above"}, 13),
            "macd_cross": (
                {"fast_period": 12, "slow_period": 26, "signal_period": 9, "direction": "bullish_cross"},
                36,
            ),
            "kdj_cross": ({"period": 9, "k_period": 3, "d_period": 3, "direction": "bullish_cross"}, 16),
            "cci_threshold": ({"period": 14, "threshold": 100, "direction": "above"}, 15),
        }

        for alert_type, (params, required_bars) in cases.items():
            normalized = normalize_indicator_parameters(alert_type, params)
            self.assertEqual(compute_required_bars(alert_type, normalized), required_bars)
            self.assertEqual(
                compute_requested_days(alert_type, normalized),
                min(max(required_bars * 3, required_bars + 30), 365),
            )


class AlertWorkerTestCase(_AlertWorkerTestCaseFixture, unittest.TestCase):
    def test_triggered_diagnostics_merge_visibility_and_market_scope_uses_region(self) -> None:
        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service)
        runtime_rule = SimpleNamespace(
            target_scope="market",
            target="cn",
            effective_target="cn",
        )
        result = {
            "status": "triggered",
            "diagnostics": '{"existing":"keep"}',
        }

        with patch(
            "src.application.alert.worker.build_market_phase_context",
            return_value={
                "phase": "intraday",
                "market": "cn",
                "trigger_source": "alert",
                "is_trading_day": True,
                "is_partial_bar": True,
            },
        ) as build_context, patch(
            "src.application.alert.worker.get_market_for_stock",
            side_effect=AssertionError("market scope must not infer stock market"),
        ):
            diagnostics = worker._diagnostics_for_status("triggered", result, runtime_rule)

        payload = json.loads(diagnostics)
        self.assertEqual(payload["existing"], "keep")
        visibility = payload["analysis_visibility"]
        self.assertEqual(visibility["source"], "alert_trigger_market_context")
        self.assertEqual(visibility["market_phase_summary"]["phase"], "intraday")
        self.assertEqual(visibility["market_phase_summary"]["market"], "cn")
        self.assertTrue(visibility["market_phase_summary"]["is_partial_bar"])
        build_context.assert_called_once()
        self.assertEqual(build_context.call_args.kwargs["market"], "cn")

    def test_enabled_db_rule_triggers_and_disabled_rule_is_ignored(self) -> None:
        enabled_rule = self._create_rule(target="600519")
        self._create_rule(
            name="Disabled",
            target="000001",
            parameters={"direction": "above", "price": 10},
            enabled=False,
        )
        notifier = self._notifier()
        seen_codes = []

        async def _quote(_monitor, stock_code):
            seen_codes.append(stock_code)
            return SimpleNamespace(price=1810.0)

        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service, notifier=notifier)
        with patch("src.application.alert.events.EventMonitor.get_realtime_quote", new=_quote):
            stats = worker.run_once()

        self.assertEqual(stats["loaded"], 1)
        self.assertEqual(stats["triggered"], 1)
        self.assertEqual(seen_codes, ["600519"])
        triggers = self._triggers(rule_id=enabled_rule["id"])
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]["status"], "triggered")
        self.assertEqual(triggers[0]["target"], "600519")
        self.assertEqual(triggers[0]["observed_value"], 1810.0)
        self.assertEqual(triggers[0]["threshold"], 1800.0)
        notifier.send_with_results.assert_called_once()
        self.assertEqual(notifier.send_with_results.call_args.kwargs["route_type"], "alert")
        notifications = self._notifications(trigger_id=triggers[0]["id"])
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["channel"], "custom")
        self.assertTrue(notifications[0]["success"])

    def test_create_trigger_if_absent_rejects_non_dedupable_history(self) -> None:
        cases = [
            {
                "name": "non_triggered_status",
                "fields": {
                    "rule_id": 1,
                    "target": "600519",
                    "status": "skipped",
                    "data_timestamp": date(2026, 5, 15),
                },
            },
            {
                "name": "missing_rule_id",
                "fields": {
                    "target": "600519",
                    "status": "triggered",
                    "data_timestamp": date(2026, 5, 15),
                },
            },
            {
                "name": "missing_data_timestamp",
                "fields": {
                    "rule_id": 1,
                    "target": "600519",
                    "status": "triggered",
                    "data_timestamp": None,
                },
            },
        ]
        for case in cases:
            with self.subTest(case["name"]):
                with self.assertRaisesRegex(ValueError, "requires triggered status"):
                    self.service.repo.create_trigger_if_absent(case["fields"])

    def test_legacy_rules_coexist_with_db_rules_and_db_rule_wins_duplicate_key(self) -> None:
        self._create_rule(target="600519")
        legacy_rules = (
            '[{"stock_code":"600519","alert_type":"price_cross","direction":"above","price":1800},'
            '{"stock_code":"300750","alert_type":"price_change_percent","direction":"down","change_pct":3.5}]'
        )

        async def _quote(_monitor, stock_code):
            if stock_code == "300750":
                return {"pct_chg": "-3.75%"}
            return SimpleNamespace(price=1810.0)

        worker = AlertWorker(
            config_provider=lambda: self._config(legacy_rules),
            service=self.service,
            notifier=self._notifier(),
        )
        with patch("src.application.alert.events.EventMonitor.get_realtime_quote", new=_quote):
            stats = worker.run_once()

        self.assertEqual(stats["loaded"], 2)
        self.assertEqual(stats["triggered"], 2)
        targets = {item["target"] for item in self._triggers()}
        self.assertEqual(targets, {"600519", "300750"})

    def test_legacy_rules_keep_existing_duplicate_trigger_history(self) -> None:
        legacy_rules = (
            '[{"stock_code":"600519","alert_type":"price_cross","direction":"above","price":1800}]'
        )
        notifier = self._notifier()

        async def _quote(_monitor, _stock_code):
            return SimpleNamespace(price=1810.0)

        worker = AlertWorker(
            config_provider=lambda: self._config(legacy_rules),
            service=self.service,
            notifier=notifier,
        )
        with patch("src.application.alert.events.EventMonitor.get_realtime_quote", new=_quote):
            first = worker.run_once()
            second = worker.run_once()

        self.assertEqual(first["triggered"], 1)
        self.assertEqual(first["recorded"], 1)
        self.assertEqual(second["triggered"], 1)
        self.assertEqual(second["recorded"], 1)
        triggers = self._triggers(status="triggered")
        self.assertEqual(len(triggers), 2)
        self.assertTrue(all(item["rule_id"] is None for item in triggers))
        self.assertTrue(all(item["data_timestamp"] is None for item in triggers))
        notifier.send_with_results.assert_called_once()

    def test_all_invalid_legacy_rules_do_not_crash(self) -> None:
        invalid_rules = (
            '[{"stock_code":"600519","alert_type":"price_cross","direction":"sideways","price":1800},'
            '{"stock_code":"300750","alert_type":"price_change_percent","direction":"down","change_pct":0}]'
        )
        worker = AlertWorker(config_provider=lambda: self._config(invalid_rules), service=self.service)

        stats = worker.run_once()

        self.assertEqual(stats["loaded"], 0)
        self.assertEqual(stats["evaluated"], 0)
        self.assertEqual(self._triggers(), [])

    def test_empty_sources_are_a_noop(self) -> None:
        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service)

        stats = worker.run_once()

        self.assertEqual(stats["loaded"], 0)
        self.assertEqual(stats["evaluated"], 0)
        self.assertEqual(self._triggers(), [])

    def test_ambiguous_numeric_quote_timestamp_is_not_written_as_epoch(self) -> None:
        rule = self._create_rule(target="600519")
        notifier = self._notifier()
        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service, notifier=notifier)

        with patch(
            "src.application.alert.events.EventMonitor.get_realtime_quote",
            new=AsyncMock(return_value=SimpleNamespace(price=1810.0, timestamp=1700000000)),
        ):
            stats = worker.run_once()

        self.assertEqual(stats["triggered"], 1)
        triggers = self._triggers(rule_id=rule["id"], status="triggered")
        self.assertEqual(len(triggers), 1)
        self.assertIsNone(triggers[0]["data_timestamp"])

    def test_service_test_rule_exception_uses_same_sanitized_reason_and_message(self) -> None:
        rule = self._create_rule(target="600519")

        async def _raise(_rule, _monitor, **_kwargs):
            raise RuntimeError("token=secret-token failed at https://example.com/webhook")

        with patch.object(self.service, "evaluate_rule", new=_raise):
            result = self.service.test_rule(rule["id"])

        self.assertEqual(result["status"], "evaluation_error")
        self.assertEqual(result["record_status"], "failed")
        self.assertEqual(result["reason"], result["message"])
        self.assertNotIn("secret-token", result["reason"])
        self.assertNotIn("example.com/webhook", result["message"])

    def test_daily_data_unavailable_writes_degraded_trigger(self) -> None:
        self._create_rule(
            name="Volume",
            target="000858",
            alert_type="volume_spike",
            parameters={"multiplier": 2.5},
        )
        manager = MagicMock()
        manager.get_daily_data.return_value = None

        async def _run_inline(func, *args, **kwargs):
            return func(*args, **kwargs)

        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service)
        with patch("data_provider.DataFetcherManager", return_value=manager), \
             patch("src.application.alert.service.asyncio.to_thread", new=_run_inline):
            stats = worker.run_once()

        self.assertEqual(stats["degraded"], 1)
        triggers = self._triggers(status="degraded")
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]["target"], "000858")
        self.assertIn("No daily volume data", triggers[0]["diagnostics"])

    def test_malformed_daily_data_response_writes_degraded_trigger(self) -> None:
        self._create_rule(
            name="Volume",
            target="000858",
            alert_type="volume_spike",
            parameters={"multiplier": 2.5},
        )
        manager = MagicMock()
        manager.get_daily_data.return_value = {"unexpected": "shape"}

        async def _run_inline(func, *args, **kwargs):
            return func(*args, **kwargs)

        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service)
        with patch("data_provider.DataFetcherManager", return_value=manager), \
             patch("src.application.alert.service.asyncio.to_thread", new=_run_inline):
            stats = worker.run_once()

        self.assertEqual(stats["degraded"], 1)
        triggers = self._triggers(status="degraded")
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]["target"], "000858")
        self.assertIn("Malformed daily volume data", triggers[0]["diagnostics"])

    def test_db_triggered_history_keeps_distinct_data_timestamps(self) -> None:
        rule = self._create_rule(
            name="MA",
            target="600519",
            alert_type="ma_price_cross",
            parameters={"window": 2, "direction": "above"},
            cooldown_policy={"cooldown_seconds": 60},
        )
        manager = MagicMock()
        manager.get_daily_data.side_effect = [
            (
                pd.DataFrame({
                    "date": [date(2026, 5, 13), date(2026, 5, 14), date(2026, 5, 15)],
                    "close": [10, 9, 12],
                }),
                "unit-test",
            ),
            (
                pd.DataFrame({
                    "date": [date(2026, 5, 14), date(2026, 5, 15), date(2026, 5, 16)],
                    "close": [10, 9, 12],
                }),
                "unit-test",
            ),
        ]

        async def _run_inline(func, *args, **kwargs):
            return func(*args, **kwargs)

        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service, notifier=self._notifier())
        with patch("data_provider.DataFetcherManager", return_value=manager), \
             patch("src.application.alert.service.asyncio.to_thread", new=_run_inline):
            first = worker.run_once()
            second = worker.run_once()

        self.assertEqual(first["recorded"], 1)
        self.assertEqual(second["recorded"], 1)
        triggers = self._triggers(rule_id=rule["id"], status="triggered")
        self.assertEqual(len(triggers), 2)
        self.assertEqual(
            {item["data_timestamp"] for item in triggers},
            {"2026-05-15T00:00:00", "2026-05-16T00:00:00"},
        )

    def test_db_triggered_history_deduplicates_per_rule_id(self) -> None:
        first_rule = self._create_rule(
            name="MA one",
            target="600519",
            alert_type="ma_price_cross",
            parameters={"window": 2, "direction": "above"},
            cooldown_policy={"cooldown_seconds": 60},
        )
        second_rule = self._create_rule(
            name="MA two",
            target="600519",
            alert_type="ma_price_cross",
            parameters={"window": 2, "direction": "above"},
            cooldown_policy={"cooldown_seconds": 60},
        )
        manager = MagicMock()
        manager.get_daily_data.return_value = (
            pd.DataFrame({
                "date": [date(2026, 5, 13), date(2026, 5, 14), date(2026, 5, 15)],
                "close": [10, 9, 12],
            }),
            "unit-test",
        )

        async def _run_inline(func, *args, **kwargs):
            return func(*args, **kwargs)

        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service, notifier=self._notifier())
        with patch("data_provider.DataFetcherManager", return_value=manager), \
             patch("src.application.alert.service.asyncio.to_thread", new=_run_inline):
            first = worker.run_once()
            second = worker.run_once()

        self.assertEqual(first["recorded"], 2)
        self.assertEqual(second["recorded"], 0)
        triggers = self._triggers(status="triggered")
        self.assertEqual(len(triggers), 2)
        self.assertEqual({item["rule_id"] for item in triggers}, {first_rule["id"], second_rule["id"]})

    def test_non_triggered_status_history_is_not_deduplicated(self) -> None:
        self._create_rule(name="Skipped", target="600519")
        self._create_rule(
            name="Degraded",
            target="000858",
            alert_type="volume_spike",
            parameters={"multiplier": 2.5},
        )
        self._create_rule(
            name="Failed",
            target="300750",
            alert_type="price_change_percent",
            parameters={"direction": "down", "change_pct": 3.0},
        )
        status_by_target = {
            "600519": "skipped",
            "000858": "degraded",
            "300750": "failed",
        }

        async def _evaluate(rule, _monitor, **_kwargs):
            status = status_by_target[rule.stock_code]
            return {
                "rule_id": self.service.runtime_rule_id(rule),
                "record_status": status,
                "triggered": False,
                "observed_value": None,
                "threshold": self.service.threshold_for_rule(rule),
                "data_source": self.service.data_source_for_rule(rule),
                "data_timestamp": None,
                "reason": f"{status} test",
                "message": f"{status} test",
            }

        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service, notifier=self._notifier())
        with patch.object(self.service, "evaluate_rule", new=_evaluate):
            first = worker.run_once()
            second = worker.run_once()

        self.assertEqual(first["recorded"], 3)
        self.assertEqual(second["recorded"], 3)
        for status in ("skipped", "degraded", "failed"):
            self.assertEqual(len(self._triggers(status=status)), 2)

    def test_market_light_rule_triggers_with_market_payload_and_deduplicates_trade_date(self) -> None:
        rule = self._create_rule(
            name="Market risk-off",
            target_scope="market",
            target="cn",
            alert_type="market_light_status",
            parameters={"statuses": ["red", "yellow"]},
        )
        snapshot = {
            "region": "cn",
            "trade_date": "2026-03-07",
            "status": "red",
            "score": 35,
            "label": "偏防守",
            "temperature_label": "偏弱",
            "reasons": ["test"],
            "guidance": "test",
            "dimensions": {
                "breadth": {"score": 20, "available": True},
                "index": {"score": 30, "available": True},
                "limit": {"score": 10, "available": True},
            },
            "data_quality": "ok",
        }
        notifier = self._notifier()
        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service, notifier=notifier)

        with patch("src.application.market.market_light_alerts.build_current_snapshot", return_value=snapshot):
            first = worker.run_once()
            second = worker.run_once()

        self.assertEqual(first["triggered"], 1)
        self.assertEqual(first["recorded"], 1)
        self.assertEqual(second["triggered"], 1)
        self.assertEqual(second["recorded"], 0)
        notifier.send_with_results.assert_called_once()
        self.assertEqual(notifier.send_with_results.call_args.kwargs["route_type"], "alert")
        triggers = self._triggers(rule_id=rule["id"], status="triggered")
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]["target"], "cn")
        self.assertEqual(triggers[0]["observed_value"], 35.0)
        self.assertEqual(triggers[0]["data_source"], "market_light")
        self.assertEqual(triggers[0]["data_timestamp"], "2026-03-07T00:00:00")

    def test_market_light_rule_skips_non_trading_day_when_check_enabled(self) -> None:
        self._create_rule(
            name="Market risk-off",
            target_scope="market",
            target="cn",
            alert_type="market_light_status",
            parameters={"statuses": ["red"]},
        )
        config = SimpleNamespace(
            agent_event_monitor_enabled=True,
            agent_event_alert_rules_json="",
            trading_day_check_enabled=True,
        )
        worker = AlertWorker(config_provider=lambda: config, service=self.service)

        with patch("src.application.market.market_light_alerts.get_open_markets_today", return_value=set()), patch(
            "src.application.market.market_light_alerts.build_current_snapshot"
        ) as build_snapshot:
            stats = worker.run_once()

        self.assertEqual(stats["skipped"], 1)
        build_snapshot.assert_not_called()
        triggers = self._triggers(status="skipped")
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]["target"], "cn")
        self.assertEqual(triggers[0]["data_source"], "market_light")

    def test_single_rule_failure_does_not_block_other_rules(self) -> None:
        self._create_rule(target="600519")
        self._create_rule(
            name="CATL drop",
            target="300750",
            alert_type="price_change_percent",
            parameters={"direction": "down", "change_pct": 3.0},
        )
        notifier = self._notifier()

        async def _quote(_monitor, stock_code):
            if stock_code == "600519":
                raise RuntimeError("token=secret-token failed at https://example.com/webhook")
            return {"pct_chg": "-3.25%"}

        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service, notifier=notifier)
        with patch("src.application.alert.events.EventMonitor.get_realtime_quote", new=_quote):
            stats = worker.run_once()

        self.assertEqual(stats["failed"], 1)
        self.assertEqual(stats["triggered"], 1)
        failed = self._triggers(status="failed")
        self.assertEqual(len(failed), 1)
        self.assertNotIn("secret-token", failed[0]["diagnostics"])
        self.assertNotIn("example.com/webhook", failed[0]["diagnostics"])
        self.assertEqual(len(self._triggers(status="triggered")), 1)

    def test_trigger_record_failure_does_not_block_other_rules(self) -> None:
        self._create_rule(target="600519")
        self._create_rule(
            name="CATL drop",
            target="300750",
            alert_type="price_change_percent",
            parameters={"direction": "down", "change_pct": 3.0},
        )
        notifier = self._notifier()
        original_create_trigger = self.service.repo.create_trigger

        def _create_trigger(fields):
            if fields["target"] == "600519":
                raise RuntimeError("database locked")
            return original_create_trigger(fields)

        async def _quote(_monitor, stock_code):
            if stock_code == "600519":
                return SimpleNamespace(price=1810.0)
            return {"pct_chg": "-3.25%"}

        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service, notifier=notifier)
        with patch.object(self.service.repo, "create_trigger", side_effect=_create_trigger), \
             patch("src.application.alert.events.EventMonitor.get_realtime_quote", new=_quote):
            stats = worker.run_once()

        self.assertEqual(stats["triggered"], 2)
        self.assertEqual(stats["recorded"], 1)
        self.assertEqual(stats["notified"], 2)
        triggers = self._triggers(status="triggered")
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]["target"], "300750")

    def test_legacy_rule_still_uses_fingerprint_suppression(self) -> None:
        raw_rules = '[{"stock_code":"600519","alert_type":"price_cross","direction":"above","price":1800}]'
        notifier = self._notifier()
        now = {"value": 1000.0}

        worker = AlertWorker(
            config_provider=lambda: self._config(raw_rules),
            service=self.service,
            notifier=notifier,
            now_provider=lambda: now["value"],
            fingerprint_ttl_seconds=60,
        )
        with patch(
            "src.application.alert.events.EventMonitor.get_realtime_quote",
            new=AsyncMock(return_value=SimpleNamespace(price=1810.0)),
        ):
            worker.run_once()
            now["value"] += 10
            worker.run_once()
            now["value"] += 61
            worker.run_once()

        self.assertEqual(notifier.send_with_results.call_count, 2)
        self.assertEqual(len(self._triggers(status="triggered")), 3)

    def test_p6_empty_watchlist_writes_skipped_trigger(self) -> None:
        self._create_rule(
            name="Watchlist",
            target_scope="watchlist",
            target="default",
            alert_type="price_cross",
            parameters={"direction": "above", "price": 10},
        )
        config = self._config()
        config.stock_list = []
        worker = AlertWorker(config_provider=lambda: config, service=self.service, notifier=self._notifier())

        stats = worker.run_once()

        self.assertEqual(stats["skipped"], 1)
        triggers = self._triggers(status="skipped")
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]["target"], "watchlist:default")
        self.assertIn("No watchlist targets", triggers[0]["diagnostics"])

    def test_p6_overflow_payload_is_dry_run_only_and_worker_does_not_write_degraded_history(self) -> None:
        rule = self._create_rule(
            name="Large watchlist",
            target_scope="watchlist",
            target="default",
            alert_type="price_cross",
            parameters={"direction": "above", "price": 10},
        )
        row = self.service.repo.get_rule(rule["id"])
        config = self._config()
        config.stock_list = [f"{index:06d}" for index in range(1, 102)]

        dry_run_payloads = self.service.build_runtime_payloads(row, config=config)
        worker_payloads = self.service.build_runtime_payloads(row, config=config, include_overflow_payload=False)

        self.assertEqual(len(dry_run_payloads), 101)
        self.assertTrue(dry_run_payloads[-1].effective_target.endswith(":overflow"))
        self.assertEqual(len(worker_payloads), 100)
        self.assertFalse(any(payload.effective_target.endswith(":overflow") for payload in worker_payloads))

        async def _not_triggered(rule_obj, *_args, **_kwargs):
            return {
                "rule_id": self.service.runtime_rule_id(rule_obj),
                "status": "not_triggered",
                "record_status": None,
                "triggered": False,
                "observed_value": 9.0,
                "threshold": 10.0,
                "data_source": "realtime_quote",
                "data_timestamp": None,
                "reason": "below threshold",
                "message": "below threshold",
            }

        worker = AlertWorker(config_provider=lambda: config, service=self.service, notifier=self._notifier())
        with patch.object(self.service, "evaluate_rule", new=_not_triggered):
            stats = worker.run_once()

        self.assertEqual(stats["loaded"], 100)
        self.assertEqual(stats["degraded"], 0)
        self.assertEqual(self._triggers(status="degraded"), [])

    def test_p6_portfolio_account_risk_uses_account_effective_target_and_diagnostics(self) -> None:
        rule = self._create_rule(
            name="Portfolio risk",
            target_scope="portfolio_account",
            target="all",
            alert_type="portfolio_concentration",
            parameters={},
        )
        notifier = self._notifier()

        async def _evaluate_portfolio(rule_obj, *_args, **_kwargs):
            return {
                "rule_id": self.service.runtime_rule_id(rule_obj),
                "status": "triggered",
                "record_status": "triggered",
                "triggered": True,
                "observed_value": 42.0,
                "threshold": 35.0,
                "data_source": "portfolio_risk",
                "data_timestamp": None,
                "reason": "account all concentration top weight 42.00%",
                "message": "account all concentration top weight 42.00%",
                "diagnostics": '{"account_id":"all","currency":"CNY","as_of":"2026-05-20"}',
            }

        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service, notifier=notifier)
        with patch.object(self.service, "evaluate_rule", new=_evaluate_portfolio):
            stats = worker.run_once()

        self.assertEqual(stats["triggered"], 1)
        triggers = self._triggers(rule_id=rule["id"], status="triggered")
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]["target"], "account:all")
        self.assertIn("account_id", triggers[0]["diagnostics"])
