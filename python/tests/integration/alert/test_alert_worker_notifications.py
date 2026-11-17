"""Tests for alert worker notifications."""

from tests.integration.alert._alert_worker_support import (
    AlertWorker,
    AsyncMock,
    DecisionSignalService,
    SimpleNamespace,
    _AlertWorkerTestCaseFixture,
    patch,
    unittest,
)


class AlertWorkerTestCase(_AlertWorkerTestCaseFixture, unittest.TestCase):
    def test_p6_notification_failure_does_not_block_alert_signal_write(self) -> None:
        self._create_rule(target="600519")
        signal_service = DecisionSignalService()

        class FailingNotifier:
            def send_with_results(self, *_args, **_kwargs):
                raise RuntimeError("webhook token=secret failed")

        worker = AlertWorker(
            config_provider=lambda: self._config(),
            service=self.service,
            decision_signal_service=signal_service,
            notifier=FailingNotifier(),
        )

        with patch(
            "src.application.alert.events.EventMonitor.get_realtime_quote",
            new=AsyncMock(return_value=SimpleNamespace(price=1810.0)),
        ):
            stats = worker.run_once()

        self.assertEqual(stats["triggered"], 1)
        self.assertEqual(stats["recorded"], 1)
        self.assertEqual(stats["notified"], 0)
        self.assertEqual(len(self._triggers(status="triggered")), 1)
        signals = signal_service.list_signals(source_type="alert", stock_code="600519", market="cn", page_size=10)[
            "items"
        ]
        self.assertEqual(len(signals), 1)

    def test_missing_quote_writes_skipped_trigger_without_notification(self) -> None:
        self._create_rule(target="600519")
        notifier = self._notifier()
        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service, notifier=notifier)

        with patch("src.application.alert.events.EventMonitor.get_realtime_quote", new=AsyncMock(return_value=None)):
            stats = worker.run_once()

        self.assertEqual(stats["skipped"], 1)
        triggers = self._triggers(status="skipped")
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]["target"], "600519")
        self.assertIn("No realtime quote", triggers[0]["diagnostics"])
        notifier.send_with_results.assert_not_called()

    def test_notification_failure_does_not_block_other_rules(self) -> None:
        self._create_rule(target="600519")
        self._create_rule(
            name="CATL drop",
            target="300750",
            alert_type="price_change_percent",
            parameters={"direction": "down", "change_pct": 3.0},
        )
        notifier = self._notifier(RuntimeError("webhook secret failed"), self._dispatch_result(True))

        async def _quote(_monitor, stock_code):
            if stock_code == "600519":
                return SimpleNamespace(price=1810.0)
            return {"pct_chg": "-3.25%"}

        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service, notifier=notifier)
        with patch("src.application.alert.events.EventMonitor.get_realtime_quote", new=_quote):
            stats = worker.run_once()

        self.assertEqual(stats["triggered"], 2)
        self.assertEqual(stats["recorded"], 2)
        self.assertEqual(stats["notified"], 1)
        self.assertEqual(len(self._triggers(status="triggered")), 2)
        self.assertEqual(notifier.send_with_results.call_count, 2)
