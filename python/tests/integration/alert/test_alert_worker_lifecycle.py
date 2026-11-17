"""Tests for alert worker lifecycle."""

from tests.integration.alert._alert_worker_support import (
    AlertWorker,
    AsyncMock,
    ChannelAttemptResult,
    MagicMock,
    NotificationDispatchResult,
    SimpleNamespace,
    _AlertWorkerTestCaseFixture,
    date,
    patch,
    pd,
    unittest,
)


class AlertWorkerTestCase(_AlertWorkerTestCaseFixture, unittest.TestCase):
    def test_cooldown_zero_reuses_same_trigger_history_but_keeps_notifications(self) -> None:
        rule = self._create_rule(
            name="MA",
            target="600519",
            alert_type="ma_price_cross",
            parameters={"window": 2, "direction": "above"},
            cooldown_policy={"cooldown_seconds": 0},
        )
        manager = MagicMock()
        manager.get_daily_data.return_value = (
            pd.DataFrame({
                "date": [date(2026, 5, 13), date(2026, 5, 14), date(2026, 5, 15)],
                "close": [10, 9, 12],
            }),
            "unit-test",
        )
        notifier = self._notifier(self._dispatch_result(True), self._dispatch_result(True))

        async def _run_inline(func, *args, **kwargs):
            return func(*args, **kwargs)

        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service, notifier=notifier)
        with patch("data_provider.DataFetcherManager", return_value=manager), \
             patch("src.application.alert.service.asyncio.to_thread", new=_run_inline):
            first = worker.run_once()
            second = worker.run_once()

        self.assertEqual(first["notified"], 1)
        self.assertEqual(second["notified"], 1)
        self.assertEqual(second["recorded"], 0)
        triggers = self._triggers(rule_id=rule["id"], status="triggered")
        self.assertEqual(len(triggers), 1)
        notifications = self._notifications(trigger_id=triggers[0]["id"])
        self.assertEqual(len(notifications), 2)
        self.assertEqual(notifier.send_with_results.call_count, 2)

    def test_notification_dispatch_results_are_recorded_and_success_updates_cooldown(self) -> None:
        rule = self._create_rule(target="600519", cooldown_policy={"cooldown_seconds": 60})

        class FakeNotifier:
            def send_with_results(self, *_args, **_kwargs):
                return NotificationDispatchResult(
                    dispatched=True,
                    success=True,
                    status="partial_failed",
                    channel_results=[
                        ChannelAttemptResult(channel="wechat", success=False, error_code="send_failed", retryable=True),
                        ChannelAttemptResult(channel="custom", success=True, latency_ms=12),
                    ],
                )

        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service, notifier=FakeNotifier())
        with patch(
            "src.application.alert.events.EventMonitor.get_realtime_quote",
            new=AsyncMock(return_value=SimpleNamespace(price=1810.0)),
        ):
            stats = worker.run_once()

        self.assertEqual(stats["notified"], 1)
        triggers = self._triggers(rule_id=rule["id"], status="triggered")
        self.assertEqual(len(triggers), 1)
        notifications = self._notifications(trigger_id=triggers[0]["id"])
        by_channel = {item["channel"]: item for item in notifications}
        self.assertEqual(set(by_channel), {"wechat", "custom"})
        self.assertFalse(by_channel["wechat"]["success"])
        self.assertTrue(by_channel["custom"]["success"])
        cooldown = self.service.repo.get_rule_cooldown_summary(
            rule_id=rule["id"],
            target="600519",
            severity="warning",
        )
        self.assertIsNotNone(cooldown)

    def test_noise_suppression_records_synthetic_attempt_without_upserting_cooldown(self) -> None:
        rule = self._create_rule(target="600519", cooldown_policy={"cooldown_seconds": 60})

        class FakeNotifier:
            def send_with_results(self, *_args, **_kwargs):
                return NotificationDispatchResult(
                    dispatched=False,
                    success=False,
                    status="noise_suppressed",
                    message="cooldown: duplicated static notification",
                )

        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service, notifier=FakeNotifier())
        with patch(
            "src.application.alert.events.EventMonitor.get_realtime_quote",
            new=AsyncMock(return_value=SimpleNamespace(price=1810.0)),
        ):
            stats = worker.run_once()

        self.assertEqual(stats["notified"], 0)
        triggers = self._triggers(rule_id=rule["id"], status="triggered")
        self.assertEqual(len(triggers), 1)
        notifications = self._notifications(trigger_id=triggers[0]["id"])
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["channel"], "__noise_suppressed__")
        self.assertEqual(notifications[0]["error_code"], "noise_suppressed")
        cooldown = self.service.repo.get_rule_cooldown_summary(
            rule_id=rule["id"],
            target="600519",
            severity="warning",
        )
        self.assertIsNone(cooldown)

    def test_no_channel_and_all_failed_do_not_upsert_cooldown(self) -> None:
        rule = self._create_rule(target="600519", cooldown_policy={"cooldown_seconds": 60})
        dispatches = [
            NotificationDispatchResult(dispatched=False, success=False, status="no_channel", message="no channel"),
            NotificationDispatchResult(
                dispatched=True,
                success=False,
                status="all_failed",
                channel_results=[ChannelAttemptResult(channel="wechat", success=False, error_code="send_failed")],
            ),
        ]

        class FakeNotifier:
            def send_with_results(self, *_args, **_kwargs):
                return dispatches.pop(0)

        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service, notifier=FakeNotifier())
        with patch(
            "src.application.alert.events.EventMonitor.get_realtime_quote",
            new=AsyncMock(return_value=SimpleNamespace(price=1810.0)),
        ):
            first = worker.run_once()
            second = worker.run_once()

        self.assertEqual(first["notified"], 0)
        self.assertEqual(second["notified"], 0)
        channels = {item["channel"] for item in self._notifications()}
        self.assertEqual(channels, {"__no_channel__", "wechat"})
        cooldown = self.service.repo.get_rule_cooldown_summary(
            rule_id=rule["id"],
            target="600519",
            severity="warning",
        )
        self.assertIsNone(cooldown)

    def test_db_cooldown_suppresses_duplicate_notifications_but_expires(self) -> None:
        self._create_rule(target="600519", cooldown_policy={"cooldown_seconds": 60})
        notifier = self._notifier()
        now = {"value": 1000.0}

        worker = AlertWorker(
            config_provider=lambda: self._config(),
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
            now["value"] += 30
            worker.run_once()
            now["value"] += 61
            worker.run_once()

        self.assertEqual(notifier.send_with_results.call_count, 2)
        self.assertEqual(len(self._triggers(status="triggered")), 3)
        cooldown_attempts = self._notifications(channel="__cooldown__")
        self.assertEqual(len(cooldown_attempts), 1)
        self.assertEqual(cooldown_attempts[0]["error_code"], "cooldown_active")

    def test_db_cooldown_read_failure_uses_fingerprint_fallback(self) -> None:
        self._create_rule(target="600519", cooldown_policy={"cooldown_seconds": 60})
        notifier = self._notifier()
        now = {"value": 1000.0}

        worker = AlertWorker(
            config_provider=lambda: self._config(),
            service=self.service,
            notifier=notifier,
            now_provider=lambda: now["value"],
            fingerprint_ttl_seconds=86400,
        )
        with patch.object(
            self.service.repo,
            "get_active_cooldown",
            side_effect=RuntimeError("database locked token=secret-token"),
        ), patch(
            "src.application.alert.events.EventMonitor.get_realtime_quote",
            new=AsyncMock(return_value=SimpleNamespace(price=1810.0)),
        ):
            first = worker.run_once()
            now["value"] += 10
            second = worker.run_once()
            now["value"] += 61
            third = worker.run_once()

        self.assertEqual(first["notified"], 1)
        self.assertEqual(second["cooldown_suppressed"], 1)
        self.assertEqual(third["notified"], 1)
        self.assertEqual(notifier.send_with_results.call_count, 2)
        self.assertEqual(len(self._triggers(status="triggered")), 3)
        suppressed_attempts = self._notifications(channel="__cooldown_read_failed__")
        self.assertEqual(len(suppressed_attempts), 1)
        self.assertEqual(suppressed_attempts[0]["error_code"], "cooldown_read_failed")
        self.assertNotIn("secret-token", suppressed_attempts[0]["diagnostics"] or "")

    def test_failed_db_notification_does_not_start_read_failure_fallback_window(self) -> None:
        self._create_rule(target="600519", cooldown_policy={"cooldown_seconds": 60})
        notifier = self._notifier(self._dispatch_result(False), self._dispatch_result(True))
        now = {"value": 1000.0}

        worker = AlertWorker(
            config_provider=lambda: self._config(),
            service=self.service,
            notifier=notifier,
            now_provider=lambda: now["value"],
            fingerprint_ttl_seconds=60,
        )
        with patch.object(
            self.service.repo,
            "get_active_cooldown",
            side_effect=RuntimeError("database locked"),
        ), patch(
            "src.application.alert.events.EventMonitor.get_realtime_quote",
            new=AsyncMock(return_value=SimpleNamespace(price=1810.0)),
        ):
            first = worker.run_once()
            now["value"] += 10
            second = worker.run_once()
            now["value"] += 10
            third = worker.run_once()

        self.assertEqual(first["notified"], 0)
        self.assertEqual(second["notified"], 1)
        self.assertEqual(third["cooldown_suppressed"], 1)
        self.assertEqual(notifier.send_with_results.call_count, 2)
        self.assertEqual(len(self._notifications(channel="__cooldown_read_failed__")), 1)

    def test_db_rule_with_cooldown_zero_is_not_suppressed_by_fingerprint(self) -> None:
        self._create_rule(target="600519", cooldown_policy={"cooldown_seconds": 0})
        notifier = self._notifier()
        now = {"value": 1000.0}

        worker = AlertWorker(
            config_provider=lambda: self._config(),
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

        self.assertEqual(notifier.send_with_results.call_count, 2)
        self.assertEqual(len(self._triggers(status="triggered")), 2)
        self.assertEqual(self._notifications(channel="__cooldown__"), [])

    def test_failed_db_notification_attempts_do_not_start_cooldown_window(self) -> None:
        self._create_rule(target="600519")
        notifier = self._notifier(
            self._dispatch_result(False),
            RuntimeError("temporary webhook failure"),
            self._dispatch_result(True),
        )
        now = {"value": 1000.0}

        worker = AlertWorker(
            config_provider=lambda: self._config(),
            service=self.service,
            notifier=notifier,
            now_provider=lambda: now["value"],
            fingerprint_ttl_seconds=60,
        )
        with patch(
            "src.application.alert.events.EventMonitor.get_realtime_quote",
            new=AsyncMock(return_value=SimpleNamespace(price=1810.0)),
        ):
            first = worker.run_once()
            now["value"] += 10
            second = worker.run_once()
            now["value"] += 10
            third = worker.run_once()
            now["value"] += 10
            fourth = worker.run_once()

        self.assertEqual(first["notified"], 0)
        self.assertEqual(second["notified"], 0)
        self.assertEqual(third["notified"], 1)
        self.assertEqual(fourth["notified"], 0)
        self.assertEqual(notifier.send_with_results.call_count, 3)
        self.assertEqual(len(self._triggers(status="triggered")), 4)

    def test_p6_watchlist_expands_to_child_keys_for_db_cooldown_fallback(self) -> None:
        self._create_rule(
            name="Watchlist",
            target_scope="watchlist",
            target="default",
            alert_type="price_cross",
            parameters={"direction": "above", "price": 10},
            cooldown_policy={"cooldown_seconds": 60},
        )
        notifier = self._notifier()
        config = self._config()
        config.stock_list = ["600519", "000001"]
        now = {"value": 1000.0}

        async def _quote(_monitor, _stock_code):
            return SimpleNamespace(price=11.0)

        worker = AlertWorker(
            config_provider=lambda: config,
            service=self.service,
            notifier=notifier,
            now_provider=lambda: now["value"],
            fingerprint_ttl_seconds=86400,
        )
        with patch.object(
            self.service.repo,
            "get_active_cooldown",
            side_effect=RuntimeError("database locked"),
        ), patch("src.application.alert.events.EventMonitor.get_realtime_quote", new=_quote):
            first = worker.run_once()
            now["value"] += 10
            second = worker.run_once()

        self.assertEqual(first["loaded"], 2)
        self.assertEqual(first["notified"], 2)
        self.assertEqual(second["cooldown_suppressed"], 2)
        self.assertEqual(notifier.send_with_results.call_count, 2)
        targets = {item["target"] for item in self._triggers(status="triggered")}
        self.assertEqual(targets, {"600519", "000001"})
