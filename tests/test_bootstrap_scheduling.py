# -*- coding: utf-8 -*-
"""Tests for :mod:`src.bootstrap.scheduling`.

``configure_runtime_scheduler_env`` is the single place that translates CLI
serve/schedule flags into ``HRS_RUNTIME_SCHEDULER_*`` environment variables, so
the exact semantics must stay pinned by tests.
"""

from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace

from src.bootstrap.scheduling import configure_runtime_scheduler_env
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


def _make_args(**overrides) -> SimpleNamespace:
    values = {
        "serve_only": False,
        "schedule": False,
        "no_run_immediately": False,
        "no_notify": False,
        "no_market_review": False,
        "dry_run": False,
        "force_run": False,
        "single_notify": False,
        "no_context_snapshot": False,
        "workers": None,
        "portfolio": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _make_config(**overrides) -> SimpleNamespace:
    values = {"schedule_enabled": False, "schedule_run_immediately": True}
    values.update(overrides)
    return SimpleNamespace(**values)


class ConfigureRuntimeSchedulerEnvTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {key: os.environ.pop(key, None) for key in _ENV_KEYS}
        self.addCleanup(self._restore_environment)

    def _restore_environment(self) -> None:
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_serve_only_suppresses_scheduler_start(self) -> None:
        args = _make_args(serve_only=True, schedule=True)
        config = _make_config(schedule_enabled=True, schedule_run_immediately=True)

        runtime_args = configure_runtime_scheduler_env(args, config)

        self.assertEqual(os.environ[RUNTIME_SCHEDULER_SUPPRESS_START_ENV], "true")
        self.assertNotIn(RUNTIME_SCHEDULER_FORCE_ENABLED_ENV, os.environ)
        self.assertNotIn(RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV, os.environ)
        self.assertNotIn(CLI_SCHEDULER_OWNER_ENV, os.environ)
        self.assertEqual(json.loads(os.environ[RUNTIME_SCHEDULER_ARGS_ENV]), runtime_args)

    def test_schedule_flag_forces_enabled_and_run_immediately(self) -> None:
        args = _make_args(schedule=True)
        config = _make_config(schedule_run_immediately=True)

        configure_runtime_scheduler_env(args, config)

        self.assertNotIn(RUNTIME_SCHEDULER_SUPPRESS_START_ENV, os.environ)
        self.assertEqual(os.environ[RUNTIME_SCHEDULER_FORCE_ENABLED_ENV], "true")
        self.assertEqual(os.environ[RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV], "true")

    def test_config_schedule_enabled_does_not_force_enabled(self) -> None:
        args = _make_args()
        config = _make_config(schedule_enabled=True, schedule_run_immediately=True)

        configure_runtime_scheduler_env(args, config)

        self.assertNotIn(RUNTIME_SCHEDULER_FORCE_ENABLED_ENV, os.environ)
        self.assertEqual(os.environ[RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV], "true")

    def test_no_run_immediately_overrides_config(self) -> None:
        args = _make_args(schedule=True, no_run_immediately=True)
        config = _make_config(schedule_run_immediately=True)

        configure_runtime_scheduler_env(args, config)

        self.assertEqual(os.environ[RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV], "false")

    def test_schedule_disabled_drops_run_immediately(self) -> None:
        args = _make_args()
        config = _make_config(schedule_enabled=False, schedule_run_immediately=True)

        configure_runtime_scheduler_env(args, config)

        self.assertNotIn(RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV, os.environ)

    def test_schedule_args_payload(self) -> None:
        args = _make_args(
            dry_run=True,
            no_notify=True,
            no_market_review=True,
            force_run=True,
            single_notify=True,
            no_context_snapshot=True,
            workers=4,
            portfolio="futu",
        )

        runtime_args = configure_runtime_scheduler_env(args, _make_config())

        self.assertEqual(
            runtime_args,
            {
                "no_notify": True,
                "no_market_review": True,
                "dry_run": True,
                "force_run": True,
                "single_notify": True,
                "no_context_snapshot": True,
                "workers": 4,
                "portfolio": "futu",
            },
        )
        self.assertEqual(json.loads(os.environ[RUNTIME_SCHEDULER_ARGS_ENV]), runtime_args)

    def test_schedule_args_omit_portfolio_when_unset(self) -> None:
        args = _make_args()

        runtime_args = configure_runtime_scheduler_env(args, _make_config())

        self.assertNotIn("portfolio", runtime_args)
        self.assertEqual(
            sorted(runtime_args),
            [
                "dry_run",
                "force_run",
                "no_context_snapshot",
                "no_market_review",
                "no_notify",
                "single_notify",
                "workers",
            ],
        )

    def test_clears_stale_environment_keys(self) -> None:
        os.environ[CLI_SCHEDULER_OWNER_ENV] = "true"
        os.environ[RUNTIME_SCHEDULER_SUPPRESS_START_ENV] = "true"
        os.environ[RUNTIME_SCHEDULER_FORCE_ENABLED_ENV] = "true"
        os.environ[RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV] = "true"
        os.environ[RUNTIME_SCHEDULER_ARGS_ENV] = '{"stale": true}'

        configure_runtime_scheduler_env(_make_args(), _make_config())

        self.assertNotIn(CLI_SCHEDULER_OWNER_ENV, os.environ)
        self.assertNotIn(RUNTIME_SCHEDULER_SUPPRESS_START_ENV, os.environ)
        self.assertNotIn(RUNTIME_SCHEDULER_FORCE_ENABLED_ENV, os.environ)
        self.assertNotIn(RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV, os.environ)
        self.assertNotIn("stale", json.loads(os.environ[RUNTIME_SCHEDULER_ARGS_ENV]))


if __name__ == "__main__":
    unittest.main()
