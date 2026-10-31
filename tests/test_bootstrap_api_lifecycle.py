# -*- coding: utf-8 -*-
"""Tests for :mod:`src.bootstrap.api_lifecycle`.

The lifespan owns the runtime scheduler, the shared system-config service and
two best-effort background warmups. These tests drive ``app_lifespan`` directly
(no ASGI stack) so the ordering, the CLI-vs-runtime scheduler ownership and the
shutdown contract stay pinned.
"""

from __future__ import annotations

import asyncio
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.bootstrap import api_lifecycle
from src.application.runtime.runtime_scheduler import (
    CLI_SCHEDULER_OWNER_ENV,
    RUNTIME_SCHEDULER_ARGS_ENV,
    RUNTIME_SCHEDULER_FORCE_ENABLED_ENV,
    RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV,
    RUNTIME_SCHEDULER_SUPPRESS_START_ENV,
)

_ENV_KEYS = (
    CLI_SCHEDULER_OWNER_ENV,
    RUNTIME_SCHEDULER_ARGS_ENV,
    RUNTIME_SCHEDULER_FORCE_ENABLED_ENV,
    RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV,
    RUNTIME_SCHEDULER_SUPPRESS_START_ENV,
)


class _FakeApp:
    """Minimal ``FastAPI`` stand-in: the lifespan only touches ``app.state``."""

    def __init__(self) -> None:
        self.state = SimpleNamespace()


class _FakeRuntimeSchedulerService:
    def __init__(
        self,
        events,
        *,
        owns_schedule=True,
        force_enabled=False,
        run_immediately_in_background=False,
        schedule_args_overrides=None,
    ) -> None:
        self.events = events
        self.owns_schedule = owns_schedule
        self.stopped = False
        events.append(
            (
                "init",
                owns_schedule,
                force_enabled,
                run_immediately_in_background,
                schedule_args_overrides,
            )
        )

    def reconcile_from_config(self, *, run_immediately=False, clear_enabled_override=False):
        self.events.append(("reconcile", run_immediately, clear_enabled_override))

    def stop(self) -> None:
        self.stopped = True
        self.events.append(("stop", self.owns_schedule))


class _FakeSystemConfigService:
    def __init__(self, runtime_scheduler=None) -> None:
        self.runtime_scheduler = runtime_scheduler


async def _never_ending(*args, **kwargs):
    """Stand-in for a warmup coroutine that must be cancelled on shutdown."""
    await asyncio.sleep(3600)


def _make_scheduler_factory(events):
    def factory(**kwargs):
        return _FakeRuntimeSchedulerService(events, **kwargs)

    return factory


def _run_lifespan(app, *, env=None, extra_patches=(), pending_warmups=True):
    """Enter/exit ``app_lifespan`` and return what was observed inside.

    ``pending_warmups`` replaces both warmup coroutines with never-ending ones so
    the shutdown cancel path is exercised without any network access.
    """
    observed = {}

    async def _exercise() -> None:
        async with api_lifecycle.app_lifespan(app):
            observed["stock_index_task"] = getattr(app.state, "stock_index_refresh_task", None)
            observed["market_cards_task"] = getattr(app.state, "market_cards_warmup_task", None)
            observed["state_during"] = sorted(vars(app.state))
            observed["env_during"] = {key: os.environ.get(key) for key in _ENV_KEYS}
            await asyncio.sleep(0.1)
        observed["state_after"] = sorted(vars(app.state))

    patches = list(extra_patches)
    if pending_warmups:
        patches = [
            patch.object(api_lifecycle, "_refresh_stock_index_cache_in_background", _never_ending),
            patch.object(api_lifecycle, "_warm_market_cards_cache_in_background", _never_ending),
        ] + patches

    for item in patches:
        item.start()
    try:
        with patch.dict(os.environ, env or {}):
            asyncio.run(_exercise())
    finally:
        for item in reversed(patches):
            item.stop()

    return observed


class AppLifespanTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {key: os.environ.pop(key, None) for key in _ENV_KEYS}
        self.addCleanup(self._restore_environment)

    def _restore_environment(self) -> None:
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_cli_scheduler_owner_disables_runtime_ownership(self) -> None:
        events = []
        app = _FakeApp()

        with patch.object(
            api_lifecycle,
            "RuntimeSchedulerService",
            _make_scheduler_factory(events),
        ), patch.object(api_lifecycle, "SystemConfigService", _FakeSystemConfigService):
            observed = _run_lifespan(app, env={CLI_SCHEDULER_OWNER_ENV: "true"})

        init_event = events[0]
        self.assertEqual(init_event[0], "init")
        self.assertIs(init_event[1], False)
        self.assertIs(init_event[2], False)
        self.assertIs(init_event[3], True)
        self.assertEqual(events[1], ("reconcile", False, False))
        self.assertEqual(events[-1], ("stop", False))
        self.assertNotIn("runtime_scheduler_service", observed["state_after"])
        self.assertNotIn("system_config_service", observed["state_after"])

    def test_suppress_start_skips_reconcile(self) -> None:
        events = []
        app = _FakeApp()

        with patch.object(
            api_lifecycle,
            "RuntimeSchedulerService",
            _make_scheduler_factory(events),
        ), patch.object(api_lifecycle, "SystemConfigService", _FakeSystemConfigService):
            observed = _run_lifespan(app, env={RUNTIME_SCHEDULER_SUPPRESS_START_ENV: "true"})

        kinds = [event[0] for event in events]
        self.assertEqual(kinds, ["init", "stop"])
        self.assertIs(events[0][1], True)
        self.assertIn("runtime_scheduler_service", observed["state_during"])

    def test_force_enabled_and_run_immediately_are_forwarded(self) -> None:
        events = []
        app = _FakeApp()

        with patch.object(
            api_lifecycle,
            "RuntimeSchedulerService",
            _make_scheduler_factory(events),
        ), patch.object(api_lifecycle, "SystemConfigService", _FakeSystemConfigService):
            _run_lifespan(
                app,
                env={
                    RUNTIME_SCHEDULER_FORCE_ENABLED_ENV: "true",
                    RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV: "true",
                },
            )

        self.assertIs(events[0][2], True)
        self.assertEqual(events[1], ("reconcile", True, False))

    def test_run_immediately_override_false_disables_immediate_run(self) -> None:
        events = []
        app = _FakeApp()

        with patch.object(
            api_lifecycle,
            "RuntimeSchedulerService",
            _make_scheduler_factory(events),
        ), patch.object(api_lifecycle, "SystemConfigService", _FakeSystemConfigService):
            _run_lifespan(app, env={RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV: "false"})

        self.assertEqual(events[1], ("reconcile", False, False))

    def test_run_immediately_falls_back_to_config(self) -> None:
        events = []
        app = _FakeApp()

        with patch.object(
            api_lifecycle,
            "RuntimeSchedulerService",
            _make_scheduler_factory(events),
        ), patch.object(api_lifecycle, "SystemConfigService", _FakeSystemConfigService), patch(
            "src.config.get_config",
            return_value=SimpleNamespace(schedule_run_immediately=True),
        ):
            _run_lifespan(app)

        self.assertEqual(events[1], ("reconcile", True, False))

    def test_schedule_args_overrides_are_forwarded_and_consumed(self) -> None:
        events = []
        app = _FakeApp()
        payload = {"no_notify": True, "workers": 2}

        with patch.object(
            api_lifecycle,
            "RuntimeSchedulerService",
            _make_scheduler_factory(events),
        ), patch.object(api_lifecycle, "SystemConfigService", _FakeSystemConfigService):
            observed = _run_lifespan(app, env={RUNTIME_SCHEDULER_ARGS_ENV: json.dumps(payload)})

        self.assertEqual(events[0][4], payload)
        self.assertIsNone(observed["env_during"][RUNTIME_SCHEDULER_ARGS_ENV])

    def test_invalid_schedule_args_payload_falls_back_to_empty(self) -> None:
        events = []
        app = _FakeApp()

        with patch.object(
            api_lifecycle,
            "RuntimeSchedulerService",
            _make_scheduler_factory(events),
        ), patch.object(api_lifecycle, "SystemConfigService", _FakeSystemConfigService):
            with self.assertLogs("src.bootstrap.api_lifecycle", level="WARNING"):
                _run_lifespan(app, env={RUNTIME_SCHEDULER_ARGS_ENV: "{not json"})

        self.assertEqual(events[0][4], {})

    def test_non_object_schedule_args_payload_falls_back_to_empty(self) -> None:
        events = []
        app = _FakeApp()

        with patch.object(
            api_lifecycle,
            "RuntimeSchedulerService",
            _make_scheduler_factory(events),
        ), patch.object(api_lifecycle, "SystemConfigService", _FakeSystemConfigService):
            _run_lifespan(app, env={RUNTIME_SCHEDULER_ARGS_ENV: "[1, 2, 3]"})

        self.assertEqual(events[0][4], {})

    def test_background_warmups_are_cancelled_on_shutdown(self) -> None:
        events = []
        app = _FakeApp()

        with patch.object(
            api_lifecycle,
            "RuntimeSchedulerService",
            _make_scheduler_factory(events),
        ), patch.object(api_lifecycle, "SystemConfigService", _FakeSystemConfigService):
            observed = _run_lifespan(app)

        stock_index_task = observed["stock_index_task"]
        market_cards_task = observed["market_cards_task"]
        self.assertIsNotNone(stock_index_task)
        self.assertIsNotNone(market_cards_task)
        self.assertTrue(stock_index_task.cancelled())
        self.assertTrue(market_cards_task.cancelled())

    def test_environment_flags_are_consumed_after_startup(self) -> None:
        events = []
        app = _FakeApp()

        with patch.object(
            api_lifecycle,
            "RuntimeSchedulerService",
            _make_scheduler_factory(events),
        ), patch.object(api_lifecycle, "SystemConfigService", _FakeSystemConfigService):
            observed = _run_lifespan(
                app,
                env={
                    RUNTIME_SCHEDULER_FORCE_ENABLED_ENV: "true",
                    RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV: "true",
                    RUNTIME_SCHEDULER_SUPPRESS_START_ENV: "true",
                },
            )

        for key in _ENV_KEYS:
            self.assertIsNone(observed["env_during"][key], key)

    def test_warmup_failure_does_not_block_startup(self) -> None:
        async def _instant_warmup() -> None:
            return None

        def _failing_refresh(settings):
            raise RuntimeError("network unavailable")

        app = _FakeApp()
        events = []

        with patch.object(
            api_lifecycle,
            "RuntimeSchedulerService",
            _make_scheduler_factory(events),
        ), patch.object(api_lifecycle, "SystemConfigService", _FakeSystemConfigService), patch.object(
            api_lifecycle,
            "settings_from_config",
            return_value=SimpleNamespace(),
        ), patch.object(
            api_lifecycle,
            "refresh_remote_stock_index_cache",
            side_effect=_failing_refresh,
        ), patch.object(
            api_lifecycle,
            "_warm_market_cards_cache_in_background",
            _instant_warmup,
        ), patch(
            "src.config.get_config",
            return_value=SimpleNamespace(schedule_run_immediately=False),
        ):
            with self.assertLogs("src.bootstrap.api_lifecycle", level="WARNING"):
                observed = _run_lifespan(app, pending_warmups=False)

        self.assertIn("runtime_scheduler_service", observed["state_during"])
        self.assertEqual(events[-1], ("stop", True))


if __name__ == "__main__":
    unittest.main()
