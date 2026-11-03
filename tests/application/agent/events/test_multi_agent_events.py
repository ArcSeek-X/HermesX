"""Tests for multi agent events."""

from tests.application.agent._multi_agent_support import (
    AsyncMock,
    MagicMock,
    SimpleNamespace,
    _TestEventMonitorAsyncFixture,
    _TestEventMonitorConfigIntegrationFixture,
    _TestEventMonitorFixture,
    patch,
    unittest,
)


class TestEventMonitor(_TestEventMonitorFixture, unittest.TestCase):
    def test_round_trip(self):
        from src.application.alert.events import EventMonitor, PriceAlert, PriceChangeAlert, VolumeAlert
        monitor = EventMonitor()
        monitor.add_alert(PriceAlert(stock_code="600519", direction="above", price=1800.0))
        monitor.add_alert(PriceChangeAlert(stock_code="300750", direction="down", change_pct=3.5))
        monitor.add_alert(VolumeAlert(stock_code="000858", multiplier=3.0))

        data = monitor.to_dict_list()
        self.assertEqual(len(data), 3)
        self.assertEqual(data[1]["alert_type"], "price_change_percent")
        self.assertEqual(data[1]["change_pct"], 3.5)

        restored = EventMonitor.from_dict_list(data)
        self.assertEqual(len(restored.rules), 3)
        self.assertEqual(restored.rules[0].stock_code, "600519")
        self.assertEqual(restored.rules[1].stock_code, "300750")
        self.assertEqual(restored.rules[2].stock_code, "000858")

    def test_serialization_contract_keeps_supported_rule_keys_stable(self):
        from src.application.alert.events import (
            AlertStatus,
            EventMonitor,
            PriceAlert,
            PriceChangeAlert,
            VolumeAlert,
        )

        monitor = EventMonitor()
        monitor.add_alert(PriceAlert(stock_code="600519", direction="above", price=1800.0))
        monitor.add_alert(PriceChangeAlert(stock_code="300750", direction="down", change_pct=3.5))
        monitor.add_alert(VolumeAlert(stock_code="000858", multiplier=3.0))
        monitor.rules[1].status = AlertStatus.TRIGGERED
        monitor.rules[2].status = AlertStatus.EXPIRED

        data = monitor.to_dict_list()

        common_keys = {
            "stock_code",
            "alert_type",
            "description",
            "status",
            "created_at",
            "ttl_hours",
        }
        self.assertEqual(set(data[0]), common_keys | {"direction", "price"})
        self.assertEqual(set(data[1]), common_keys | {"direction", "change_pct"})
        self.assertEqual(set(data[2]), common_keys | {"multiplier"})
        known_status_values = {status.value for status in AlertStatus}
        for entry in data:
            self.assertIn(entry["status"], known_status_values)

        restored = EventMonitor.from_dict_list(data)

        self.assertEqual([rule.status for rule in restored.rules], [
            AlertStatus.ACTIVE,
            AlertStatus.TRIGGERED,
            AlertStatus.EXPIRED,
        ])

    def test_remove_expired(self):
        import time
        from src.application.alert.events import EventMonitor, PriceAlert
        monitor = EventMonitor()
        alert = PriceAlert(stock_code="600519", direction="above", price=1800.0, ttl_hours=0.0)
        alert.created_at = time.time() - 3600  # 1 hour ago
        monitor.rules.append(alert)
        removed = monitor.remove_expired()
        self.assertEqual(removed, 1)
        self.assertEqual(len(monitor.rules), 0)

    def test_add_alert_rejects_unsupported_rule_type(self):
        from src.application.alert.events import EventMonitor, SentimentAlert

        monitor = EventMonitor()

        with self.assertRaises(ValueError):
            monitor.add_alert(SentimentAlert(stock_code="600519"))

    def test_from_dict_list_skips_unsupported_placeholder_rule_type(self):
        from src.application.alert.events import EventMonitor

        data = [
            {"stock_code": "600519", "alert_type": "sentiment_shift"},
            {
                "stock_code": "000858",
                "alert_type": "volume_spike",
                "multiplier": 2.5,
            },
        ]

        monitor = EventMonitor.from_dict_list(data)

        self.assertEqual(len(monitor.rules), 1)
        self.assertEqual(monitor.rules[0].stock_code, "000858")

    def test_from_dict_list_skips_price_change_without_change_pct(self):
        from src.application.alert.events import EventMonitor

        data = [
            {
                "stock_code": "300750",
                "alert_type": "price_change_percent",
                "direction": "up",
            }
        ]

        monitor = EventMonitor.from_dict_list(data)

        self.assertEqual(monitor.rules, [])


class TestEventMonitorAsync(_TestEventMonitorAsyncFixture, unittest.IsolatedAsyncioTestCase):
    async def test_check_price_uses_to_thread_and_triggers(self):
        from src.application.alert.events import EventMonitor, PriceAlert

        monitor = EventMonitor()
        rule = PriceAlert(stock_code="600519", direction="above", price=1800.0)
        quote = SimpleNamespace(price=1810.0)

        with patch("src.application.alert.events.asyncio.to_thread", new=AsyncMock(return_value=quote)) as to_thread:
            triggered = await monitor._check_price(rule)

        self.assertIsNotNone(triggered)
        self.assertEqual(triggered.rule.stock_code, "600519")
        to_thread.assert_awaited_once()

    async def test_check_price_change_uses_to_thread_and_triggers(self):
        from src.application.alert.events import EventMonitor, PriceChangeAlert

        monitor = EventMonitor()
        rule = PriceChangeAlert(stock_code="300750", direction="down", change_pct=3.0)
        quote = SimpleNamespace(change_pct=-3.25)

        with patch("src.application.alert.events.asyncio.to_thread", new=AsyncMock(return_value=quote)) as to_thread:
            triggered = await monitor._check_price_change(rule)

        self.assertIsNotNone(triggered)
        self.assertEqual(triggered.rule.stock_code, "300750")
        self.assertEqual(triggered.current_value, -3.25)
        self.assertIn("current = -3.25%", triggered.message)
        to_thread.assert_awaited_once()

    async def test_check_price_change_accepts_dict_payload_alias(self):
        from src.application.alert.events import EventMonitor, PriceChangeAlert

        monitor = EventMonitor()
        rule = PriceChangeAlert(stock_code="AAPL", direction="up", change_pct=2.0)

        with patch("src.application.alert.events.asyncio.to_thread", new=AsyncMock(return_value={"pct_chg": "2.35%"})):
            triggered = await monitor._check_price_change(rule)

        self.assertIsNotNone(triggered)
        self.assertEqual(triggered.current_value, 2.35)

    async def test_realtime_rules_read_quote_port_per_quote_check(self):
        # A6-4 后 EventMonitor 通过 RealtimeQuotePort 取行情（不再直接 new DataFetcherManager），
        # 此处锁定「每条规则各取一次行情」的契约。
        from src.application.alert.events import (
            EventMonitor,
            PriceAlert,
            PriceChangeAlert,
            set_realtime_quote_port,
        )

        monitor = EventMonitor()
        monitor.add_alert(PriceAlert(stock_code="600519", direction="above", price=1800.0))
        monitor.add_alert(PriceChangeAlert(stock_code="600519", direction="up", change_pct=3.0))

        port = MagicMock()
        port.get_realtime_quote.return_value = SimpleNamespace(price=1810.0, change_pct=3.25)

        async def _run_inline(func, *args, **kwargs):
            return func(*args, **kwargs)

        set_realtime_quote_port(port)
        try:
            with patch("src.application.alert.events.asyncio.to_thread", new=_run_inline):
                triggered = await monitor.check_all()
        finally:
            set_realtime_quote_port(None)

        self.assertEqual(port.get_realtime_quote.call_count, 2)
        port.get_realtime_quote.assert_any_call("600519")
        self.assertEqual(len(triggered), 2)

    async def test_check_volume_safe_when_fetch_returns_none(self):
        """_check_volume must not crash when get_daily_data returns None."""
        from src.application.alert.events import EventMonitor, VolumeAlert

        monitor = EventMonitor()
        rule = VolumeAlert(stock_code="600519", multiplier=2.0)

        with patch("src.application.alert.events.asyncio.to_thread", new=AsyncMock(return_value=None)):
            result = await monitor._check_volume(rule)

        self.assertIsNone(result)

    async def test_check_all_async_callback(self):
        """on_trigger callbacks should be properly awaited if coroutine."""
        from src.application.alert.events import EventMonitor, PriceAlert

        monitor = EventMonitor()
        rule = PriceAlert(stock_code="600519", direction="above", price=1800.0)
        monitor.add_alert(rule)

        callback_values = []
        async_cb = AsyncMock(side_effect=lambda alert: callback_values.append(alert.rule.stock_code))
        monitor.on_trigger(async_cb)

        quote = SimpleNamespace(price=1810.0)
        with patch("src.application.alert.events.asyncio.to_thread", new=AsyncMock(return_value=quote)):
            triggered = await monitor.check_all()

        self.assertEqual(len(triggered), 1)
        async_cb.assert_awaited_once()


class TestEventMonitorConfigIntegration(_TestEventMonitorConfigIntegrationFixture, unittest.TestCase):
    def test_build_event_monitor_from_config(self):
        from src.application.alert.events import build_event_monitor_from_config

        config = SimpleNamespace(
            agent_event_monitor_enabled=True,
            agent_event_alert_rules_json='[{"stock_code":"600519","alert_type":"price_cross","direction":"above","price":1800}]',
        )

        with patch("src.application.notification.notification.NotificationService", return_value=MagicMock()):
            monitor = build_event_monitor_from_config(config=config)

        self.assertIsNotNone(monitor)
        self.assertEqual(len(monitor.rules), 1)
        self.assertEqual(monitor.rules[0].stock_code, "600519")

    def test_configured_event_monitor_notification_uses_alert_route(self):
        from src.application.alert.events import TriggeredAlert, build_event_monitor_from_config

        config = SimpleNamespace(
            agent_event_monitor_enabled=True,
            agent_event_alert_rules_json='[{"stock_code":"600519","alert_type":"price_cross","direction":"above","price":1800}]',
        )
        notifier = MagicMock()
        notifier.send.return_value = True

        monitor = build_event_monitor_from_config(config=config, notifier=notifier)

        self.assertIsNotNone(monitor)
        monitor._callbacks[0](TriggeredAlert(rule=monitor.rules[0], message="hit"))
        notifier.send.assert_called_once()
        self.assertIn("hit", notifier.send.call_args.args[0])
        self.assertEqual(notifier.send.call_args.kwargs["route_type"], "alert")

    def test_build_event_monitor_from_config_accepts_price_change_percent(self):
        from src.application.alert.events import PriceChangeAlert, build_event_monitor_from_config

        config = SimpleNamespace(
            agent_event_monitor_enabled=True,
            agent_event_alert_rules_json=(
                '[{"stock_code":"300750","alert_type":"price_change_percent",'
                '"direction":"down","change_pct":3.5}]'
            ),
        )

        with patch("src.application.notification.notification.NotificationService", return_value=MagicMock()):
            monitor = build_event_monitor_from_config(config=config)

        self.assertIsNotNone(monitor)
        self.assertEqual(len(monitor.rules), 1)
        self.assertIsInstance(monitor.rules[0], PriceChangeAlert)
        self.assertEqual(monitor.rules[0].change_pct, 3.5)

    def test_build_event_monitor_returns_none_on_invalid_json(self):
        from src.application.alert.events import build_event_monitor_from_config

        config = SimpleNamespace(
            agent_event_monitor_enabled=True,
            agent_event_alert_rules_json='[invalid',
        )

        monitor = build_event_monitor_from_config(config=config)
        self.assertIsNone(monitor)

    def test_build_event_monitor_skips_invalid_rule_entries(self):
        from src.application.alert.events import build_event_monitor_from_config

        config = SimpleNamespace(
            agent_event_monitor_enabled=True,
            agent_event_alert_rules_json=(
                '[{"stock_code":"600519","alert_type":"price_cross","direction":"above","price":1800},'
                '{"stock_code":"000858","alert_type":"price_cross","status":"bad","direction":"above","price":120}]'
            ),
        )

        with patch("src.application.notification.notification.NotificationService", return_value=MagicMock()):
            monitor = build_event_monitor_from_config(config=config)

        self.assertIsNotNone(monitor)
        self.assertEqual(len(monitor.rules), 1)
        self.assertEqual(monitor.rules[0].stock_code, "600519")

    def test_build_event_monitor_skips_unsupported_rule_types(self):
        from src.application.alert.events import build_event_monitor_from_config

        config = SimpleNamespace(
            agent_event_monitor_enabled=True,
            agent_event_alert_rules_json=(
                '[{"stock_code":"600519","alert_type":"sentiment_shift"},'
                '{"stock_code":"000858","alert_type":"price_cross","direction":"above","price":120}]'
            ),
        )

        with patch("src.application.notification.notification.NotificationService", return_value=MagicMock()):
            monitor = build_event_monitor_from_config(config=config)

        self.assertIsNotNone(monitor)
        self.assertEqual(len(monitor.rules), 1)
        self.assertEqual(monitor.rules[0].stock_code, "000858")
