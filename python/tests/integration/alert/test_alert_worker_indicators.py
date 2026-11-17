"""Tests for alert worker indicators."""

from tests.integration.alert._alert_worker_support import (
    AlertWorker,
    AsyncMock,
    MagicMock,
    SimpleNamespace,
    _AlertWorkerTestCaseFixture,
    calculate_rsi,
    date,
    evaluate_indicator_alert,
    normalize_indicator_parameters,
    patch,
    pd,
    unittest,
)


class AlertIndicatorHelperTestCase(unittest.TestCase):
    def test_rejects_indicator_periods_that_exceed_fetchable_history(self) -> None:
        cases = [
            ("macd_cross", {"fast_period": 2, "slow_period": 250, "signal_period": 250}),
            ("kdj_cross", {"period": 250, "k_period": 250, "d_period": 250}),
        ]

        for alert_type, params in cases:
            with self.subTest(alert_type=alert_type):
                with self.assertRaisesRegex(ValueError, "at most 365 days"):
                    normalize_indicator_parameters(alert_type, params)

    def test_indicator_edge_cross_and_level_only_semantics(self) -> None:
        ma_params = normalize_indicator_parameters("ma_price_cross", {"window": 2, "direction": "above"})
        triggered = evaluate_indicator_alert(
            "ma_price_cross",
            "TEST",
            ma_params,
            pd.DataFrame({
                "date": pd.date_range("2026-01-01", periods=3),
                "close": [10, 9, 12],
            }),
        )
        level_only = evaluate_indicator_alert(
            "ma_price_cross",
            "TEST",
            ma_params,
            pd.DataFrame({
                "date": pd.date_range("2026-01-01", periods=3),
                "close": [10, 12, 13],
            }),
        )

        self.assertEqual(triggered.status, "triggered")
        self.assertEqual(level_only.status, "not_triggered")

    def test_rsi_uses_wilder_not_sma(self) -> None:
        close = pd.Series([10.0, 9.0, 11.0])
        old_sma_rsi = 66.66666666666666
        wilder_rsi = calculate_rsi(close, 2)

        self.assertNotAlmostEqual(float(wilder_rsi.iloc[-1]), old_sma_rsi)
        self.assertAlmostEqual(float(wilder_rsi.iloc[-1]), 80.0)

    def test_indicator_formulas_cover_rsi_macd_kdj_cci_and_chinese_columns(self) -> None:
        rsi_params = normalize_indicator_parameters("rsi_threshold", {
            "period": 2,
            "threshold": 50,
            "direction": "above",
        })
        rsi = evaluate_indicator_alert(
            "rsi_threshold",
            "TEST",
            rsi_params,
            pd.DataFrame({"日期": pd.date_range("2026-01-01", periods=3), "收盘": [10, 9, 11]}),
        )

        macd_params = normalize_indicator_parameters("macd_cross", {
            "fast_period": 2,
            "slow_period": 3,
            "signal_period": 2,
            "direction": "bullish_cross",
        })
        macd = evaluate_indicator_alert(
            "macd_cross",
            "TEST",
            macd_params,
            pd.DataFrame({
                "date": pd.date_range("2026-01-01", periods=7),
                "close": [10, 9, 8, 7, 6, 5, 10],
            }),
        )

        kdj_params = normalize_indicator_parameters("kdj_cross", {
            "period": 3,
            "k_period": 2,
            "d_period": 2,
            "direction": "bullish_cross",
        })
        kdj_close = [5, 5, 5, 5, 5, 5, 5, 6]
        kdj = evaluate_indicator_alert(
            "kdj_cross",
            "TEST",
            kdj_params,
            pd.DataFrame({
                "date": pd.date_range("2026-01-01", periods=len(kdj_close)),
                "high": [value + 1 for value in kdj_close],
                "low": [value - 1 for value in kdj_close],
                "close": kdj_close,
            }),
        )

        cci_params = normalize_indicator_parameters("cci_threshold", {
            "period": 3,
            "threshold": 50,
            "direction": "above",
        })
        cci_close = [5, 5, 6, 5, 7]
        cci = evaluate_indicator_alert(
            "cci_threshold",
            "TEST",
            cci_params,
            pd.DataFrame({
                "date": pd.date_range("2026-01-01", periods=len(cci_close)),
                "high": [value + 1 for value in cci_close],
                "low": [value - 1 for value in cci_close],
                "close": cci_close,
            }),
        )

        self.assertEqual(rsi.status, "triggered")
        self.assertAlmostEqual(rsi.observed_value, 80.0)
        self.assertEqual(macd.status, "triggered")
        self.assertAlmostEqual(macd.observed_value, 0.321823559670782)
        self.assertEqual(kdj.status, "triggered")
        self.assertAlmostEqual(kdj.observed_value, 4.166666666666664)
        self.assertEqual(cci.status, "triggered")
        self.assertAlmostEqual(cci.observed_value, 100.00000000000001)

    def test_indicator_degraded_paths_cover_missing_data_and_partial_bar(self) -> None:
        missing_columns = evaluate_indicator_alert(
            "cci_threshold",
            "TEST",
            normalize_indicator_parameters("cci_threshold", {"period": 3, "threshold": 100}),
            pd.DataFrame({"date": pd.date_range("2026-01-01", periods=4), "close": [1, 2, 3, 4]}),
        )
        partial = evaluate_indicator_alert(
            "ma_price_cross",
            "TEST",
            normalize_indicator_parameters("ma_price_cross", {"window": 2, "direction": "above"}),
            pd.DataFrame({
                "date": [date(2026, 5, 16), date(2026, 5, 17), date(2026, 5, 18), date(2026, 5, 19)],
                "close": [10, 9, 12, 8],
            }),
            now=pd.Timestamp("2026-05-19 15:00:00").to_pydatetime(),
        )

        self.assertEqual(missing_columns.status, "degraded")
        self.assertIn("missing high", missing_columns.message)
        self.assertEqual(partial.status, "triggered")
        self.assertEqual(partial.data_timestamp, pd.Timestamp("2026-05-18").to_pydatetime())

    def test_indicator_drops_unparseable_last_bar_before_cutoff(self) -> None:
        result = evaluate_indicator_alert(
            "ma_price_cross",
            "TEST",
            normalize_indicator_parameters("ma_price_cross", {"window": 2, "direction": "above"}),
            pd.DataFrame({
                "date": [date(2026, 5, 16), date(2026, 5, 17), date(2026, 5, 18), "not-a-date"],
                "close": [10, 11, 12, 8],
            }),
            now=pd.Timestamp("2026-05-19 15:00:00").to_pydatetime(),
        )

        self.assertEqual(result.status, "not_triggered")
        self.assertEqual(result.data_timestamp, pd.Timestamp("2026-05-18").to_pydatetime())

    def test_indicator_requires_two_closed_bars_for_edge_evaluation(self) -> None:
        result = evaluate_indicator_alert(
            "ma_price_cross",
            "TEST",
            normalize_indicator_parameters("ma_price_cross", {"window": 2, "direction": "above"}),
            pd.DataFrame({
                "date": [date(2026, 5, 18), "not-a-date"],
                "close": [10, 12],
            }),
            now=pd.Timestamp("2026-05-19 15:00:00").to_pydatetime(),
        )

        self.assertEqual(result.status, "degraded")
        self.assertEqual(result.message, "insufficient closed bars for edge evaluation")
        self.assertEqual(result.data_timestamp, pd.Timestamp("2026-05-18").to_pydatetime())


class AlertWorkerTestCase(_AlertWorkerTestCaseFixture, unittest.TestCase):
    def test_legacy_json_parse_failure_does_not_crash_or_block_persisted_rules(self) -> None:
        before = self.env_path.read_text(encoding="utf-8")
        self._create_rule(target="600519")
        notifier = self._notifier()
        worker = AlertWorker(config_provider=lambda: self._config("[invalid"), service=self.service, notifier=notifier)

        with patch(
            "src.application.alert.events.EventMonitor.get_realtime_quote",
            new=AsyncMock(return_value=SimpleNamespace(price=1810.0)),
        ):
            stats = worker.run_once()

        self.assertEqual(stats["loaded"], 1)
        self.assertEqual(stats["triggered"], 1)
        self.assertEqual(len(self._triggers()), 1)
        self.assertEqual(self.env_path.read_text(encoding="utf-8"), before)

    def test_price_cross_numeric_yyyymmdd_quote_date_writes_correct_timestamp(self) -> None:
        rule = self._create_rule(target="600519")
        notifier = self._notifier()
        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service, notifier=notifier)

        with patch(
            "src.application.alert.events.EventMonitor.get_realtime_quote",
            new=AsyncMock(return_value=SimpleNamespace(price=1810.0, date=20260517)),
        ):
            stats = worker.run_once()

        self.assertEqual(stats["triggered"], 1)
        triggers = self._triggers(rule_id=rule["id"], status="triggered")
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]["data_timestamp"], "2026-05-17T00:00:00")

    def test_price_cross_space_separated_quote_time_writes_timestamp(self) -> None:
        rule = self._create_rule(target="600519")
        notifier = self._notifier()
        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service, notifier=notifier)

        with patch(
            "src.application.alert.events.EventMonitor.get_realtime_quote",
            new=AsyncMock(return_value=SimpleNamespace(price=1810.0, quote_time="2026-05-17 15:00:00")),
        ):
            stats = worker.run_once()

        self.assertEqual(stats["triggered"], 1)
        triggers = self._triggers(rule_id=rule["id"], status="triggered")
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]["data_timestamp"], "2026-05-17T15:00:00")

    def test_volume_spike_trigger_writes_expected_trigger_fields(self) -> None:
        rule = self._create_rule(
            name="Volume",
            target="000858",
            alert_type="volume_spike",
            parameters={"multiplier": 2.0},
        )
        manager = MagicMock()
        daily = pd.DataFrame(
            {
                "date": [date(2026, 5, 13), date(2026, 5, 14), date(2026, 5, 15)],
                "volume": [1000, 1000, 5000],
            }
        )
        manager.get_daily_data.return_value = (daily, "test_source")
        notifier = self._notifier()

        async def _run_inline(func, *args, **kwargs):
            return func(*args, **kwargs)

        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service, notifier=notifier)
        with patch("data_provider.DataFetcherManager", return_value=manager), \
             patch("src.application.alert.service.asyncio.to_thread", new=_run_inline):
            stats = worker.run_once()

        self.assertEqual(stats["triggered"], 1)
        self.assertEqual(stats["recorded"], 1)
        self.assertEqual(stats["notified"], 1)
        triggers = self._triggers(rule_id=rule["id"], status="triggered")
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]["target"], "000858")
        self.assertEqual(triggers[0]["observed_value"], 5000.0)
        self.assertAlmostEqual(triggers[0]["threshold"], 4666.666666666667)
        self.assertEqual(triggers[0]["data_source"], "daily_data")
        self.assertEqual(triggers[0]["data_timestamp"], "2026-05-15T00:00:00")
        notifier.send_with_results.assert_called_once()

    def test_volume_spike_history_deduplicates_same_daily_signal(self) -> None:
        rule = self._create_rule(
            name="Volume",
            target="000858",
            alert_type="volume_spike",
            parameters={"multiplier": 2.0},
            cooldown_policy={"cooldown_seconds": 60},
        )
        manager = MagicMock()
        manager.get_daily_data.return_value = (
            pd.DataFrame({
                "date": [date(2026, 5, 13), date(2026, 5, 14), date(2026, 5, 15)],
                "volume": [1000, 1000, 5000],
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
        self.assertEqual(triggers[0]["target"], "000858")
        self.assertEqual(triggers[0]["data_source"], "daily_data")
        self.assertEqual(triggers[0]["data_timestamp"], "2026-05-15T00:00:00")
        cooldown_attempts = self._notifications(channel="__cooldown__")
        self.assertEqual(len(cooldown_attempts), 1)
        self.assertEqual(cooldown_attempts[0]["trigger_id"], triggers[0]["id"])
        notifier.send_with_results.assert_called_once()

    def test_technical_indicator_rules_share_run_once_daily_cache(self) -> None:
        self._create_rule(
            name="MA one",
            target="600519",
            alert_type="ma_price_cross",
            parameters={"window": 2, "direction": "above"},
        )
        self._create_rule(
            name="MA two",
            target="600519",
            alert_type="ma_price_cross",
            parameters={"window": 2, "direction": "above"},
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

        self.assertEqual(first["triggered"], 2)
        self.assertEqual(second["triggered"], 2)
        self.assertEqual(len(self._triggers(status="triggered")), 2)
        self.assertEqual(manager.get_daily_data.call_count, 2)
        manager.get_daily_data.assert_called_with("600519", days=33)

    def test_technical_indicator_insufficient_data_writes_degraded_trigger(self) -> None:
        rule = self._create_rule(
            name="MA insufficient",
            target="600519",
            alert_type="ma_price_cross",
            parameters={"window": 20, "direction": "above"},
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
            stats = worker.run_once()

        self.assertEqual(stats["degraded"], 1)
        triggers = self._triggers(rule_id=rule["id"], status="degraded")
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]["target"], "600519")
        self.assertIn("insufficient data: need 21 bars, got 3", triggers[0]["diagnostics"])
        manager.get_daily_data.assert_called_once_with("600519", days=63)
        notifier.send_with_results.assert_not_called()

    def test_technical_indicator_fetch_exception_writes_failed_trigger(self) -> None:
        self._create_rule(
            name="MA",
            target="600519",
            alert_type="ma_price_cross",
            parameters={"window": 2, "direction": "above"},
        )
        manager = MagicMock()
        manager.get_daily_data.side_effect = RuntimeError("token=secret-token data fetch failed")
        notifier = self._notifier()

        async def _run_inline(func, *args, **kwargs):
            return func(*args, **kwargs)

        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service, notifier=notifier)
        with patch("data_provider.DataFetcherManager", return_value=manager), \
             patch("src.application.alert.service.asyncio.to_thread", new=_run_inline):
            stats = worker.run_once()

        self.assertEqual(stats["failed"], 1)
        failed = self._triggers(status="failed")
        self.assertEqual(len(failed), 1)
        self.assertNotIn("secret-token", failed[0]["diagnostics"])
        notifier.send_with_results.assert_not_called()

    def test_unsupported_persisted_rule_is_skipped_without_crashing_worker(self) -> None:
        self.service.repo.create_rule({
            "name": "Future rule",
            "target_scope": "single_symbol",
            "target": "600519",
            "alert_type": "future_indicator",
            "parameters": "{}",
            "severity": "warning",
            "enabled": True,
            "source": "api",
        })

        worker = AlertWorker(config_provider=lambda: self._config(), service=self.service)
        stats = worker.run_once()

        self.assertEqual(stats["loaded"], 0)
        self.assertEqual(stats["evaluated"], 0)
        self.assertEqual(self._triggers(), [])
