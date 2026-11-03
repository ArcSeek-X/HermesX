"""Tests for alert worker analysis."""

from tests.integration.alert._alert_worker_support import (
    AlertWorker,
    AsyncMock,
    DecisionSignalService,
    MagicMock,
    SimpleNamespace,
    _AlertWorkerTestCaseFixture,
    date,
    patch,
    pd,
    unittest,
)


class AlertWorkerTestCase(_AlertWorkerTestCaseFixture, unittest.TestCase):
    def test_p6_triggered_stock_alert_links_latest_active_decision_signal(self) -> None:
        self._create_rule(target="600519")
        signal_service = DecisionSignalService()
        signal_service.create_signal({
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "market": "cn",
            "source_type": "analysis",
            "source_report_id": 1390,
            "trace_id": "analysis-1390",
            "trigger_source": "api",
            "action": "sell",
            "reason": "跌破关键支撑",
            "watch_conditions": "观察能否收回均线",
            "risk_summary": "下行风险扩大",
        })
        notifier = self._notifier()
        worker = AlertWorker(
            config_provider=lambda: self._config(),
            service=self.service,
            decision_signal_service=signal_service,
            notifier=notifier,
        )

        with patch(
            "src.application.alert.events.EventMonitor.get_realtime_quote",
            new=AsyncMock(return_value=SimpleNamespace(price=1810.0)),
        ):
            stats = worker.run_once()

        self.assertEqual(stats["triggered"], 1)
        all_signals = signal_service.list_signals(stock_code="600519", market="cn", page_size=10)["items"]
        self.assertEqual(len(all_signals), 1)
        self.assertEqual(all_signals[0]["source_type"], "analysis")
        trigger = self._triggers(status="triggered")[0]
        summary = trigger["decision_signal_summary"]
        self.assertEqual(summary["id"], all_signals[0]["id"])
        self.assertEqual(summary["action"], "sell")
        alert_text = notifier.send_with_results.call_args.args[0]
        self.assertIn("AI 决策信号", alert_text)
        self.assertIn("跌破关键支撑", alert_text)
        self.assertIn("观察能否收回均线", alert_text)

    def test_p6_triggered_stock_alert_creates_alert_signal_when_no_active_signal(self) -> None:
        self._create_rule(target="600519")
        signal_service = DecisionSignalService()
        notifier = self._notifier()
        worker = AlertWorker(
            config_provider=lambda: self._config(),
            service=self.service,
            decision_signal_service=signal_service,
            notifier=notifier,
        )

        with patch(
            "src.application.alert.events.EventMonitor.get_realtime_quote",
            new=AsyncMock(return_value=SimpleNamespace(price=1810.0)),
        ):
            stats = worker.run_once()

        self.assertEqual(stats["triggered"], 1)
        signals = signal_service.list_signals(source_type="alert", stock_code="600519", market="cn", page_size=10)[
            "items"
        ]
        self.assertEqual(len(signals), 1)
        item = signals[0]
        self.assertEqual(item["action"], "alert")
        self.assertEqual(item["trigger_source"], "alert")
        self.assertEqual(item["source_agent"], "alert_worker")
        self.assertIsNone(item["market_phase"])
        self.assertTrue(str(item["trace_id"]).startswith("alert-rule-"))
        self.assertEqual(item["metadata"]["rule_id"], 1)
        self.assertEqual(item["metadata"]["alert_type"], "price_cross")
        self.assertEqual(self._triggers(status="triggered")[0]["decision_signal_summary"]["id"], item["id"])

    def test_p6_alert_signal_trace_id_is_idempotent_for_same_rule(self) -> None:
        self._create_rule(target="600519")
        signal_service = DecisionSignalService()
        notifier = self._notifier(
            self._dispatch_result(False, dispatched=True),
            self._dispatch_result(False, dispatched=True),
        )
        worker = AlertWorker(
            config_provider=lambda: self._config(),
            service=self.service,
            decision_signal_service=signal_service,
            notifier=notifier,
        )

        with patch(
            "src.application.alert.events.EventMonitor.get_realtime_quote",
            new=AsyncMock(return_value=SimpleNamespace(price=1810.0)),
        ):
            worker.run_once()
            worker.run_once()

        signals = signal_service.list_signals(source_type="alert", stock_code="600519", market="cn", page_size=10)[
            "items"
        ]
        self.assertEqual(len(signals), 1)
        self.assertIsNone(signals[0]["market_phase"])
        self.assertEqual(len(self._triggers(status="triggered")), 2)

    def test_p6_non_stock_alert_targets_skip_decision_signal_write(self) -> None:
        signal_service = MagicMock()
        worker = AlertWorker(
            config_provider=lambda: self._config(),
            service=self.service,
            decision_signal_service=signal_service,
        )
        for runtime_rule in (
            SimpleNamespace(
                key="market:cn",
                rule=SimpleNamespace(target_scope="market", target="cn", metadata={}),
                source="db",
                severity="warning",
                effective_target="cn",
                display_target="cn",
            ),
            SimpleNamespace(
                key="portfolio_account:all",
                rule=SimpleNamespace(target_scope="portfolio_account", target="all", metadata={}),
                source="db",
                severity="warning",
                effective_target="portfolio_account:all",
                display_target="all accounts",
            ),
            SimpleNamespace(
                key="single_symbol:SPX",
                rule=SimpleNamespace(
                    target_scope="single_symbol",
                    stock_code="SPX",
                    metadata={},
                ),
                source="db",
                severity="warning",
                effective_target="SPX",
                display_target="SPX",
            ),
        ):
            worker._attach_decision_signal_summary_safely(runtime_rule, {"record_status": "triggered"})

        signal_service.get_latest_active.assert_not_called()
        signal_service.create_signal.assert_not_called()

    def test_db_triggered_history_deduplicates_same_daily_signal(self) -> None:
        rule = self._create_rule(
            name="MA",
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
        notifier = self._notifier()

        async def _run_inline(func, *args, **kwargs):
            return func(*args, **kwargs)

        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service, notifier=notifier)
        with patch("data_provider.DataFetcherManager", return_value=manager), \
             patch("src.application.alert.service.asyncio.to_thread", new=_run_inline):
            first = worker.run_once()
            second = worker.run_once()

        self.assertEqual(first["triggered"], 1)
        self.assertEqual(first["recorded"], 1)
        self.assertEqual(second["triggered"], 1)
        self.assertEqual(second["recorded"], 0)
        triggers = self._triggers(rule_id=rule["id"], status="triggered")
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]["data_timestamp"], "2026-05-15T00:00:00")
        cooldown_attempts = self._notifications(channel="__cooldown__")
        self.assertEqual(len(cooldown_attempts), 1)
        self.assertEqual(cooldown_attempts[0]["trigger_id"], triggers[0]["id"])
        notifier.send_with_results.assert_called_once()
