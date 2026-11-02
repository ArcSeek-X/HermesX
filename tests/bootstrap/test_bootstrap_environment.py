# -*- coding: utf-8 -*-
"""Tests for :mod:`src.bootstrap.environment`.

``bootstrap_environment`` must be idempotent, must only touch env/proxy state
and must never create the database or start the scheduler.
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from src.bootstrap import environment

_ENV_KEYS = (
    "USE_PROXY",
    "PROXY_HOST",
    "PROXY_PORT",
    "GITHUB_ACTIONS",
    "http_proxy",
    "https_proxy",
)


class BootstrapEnvironmentTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {key: os.environ.pop(key, None) for key in _ENV_KEYS}
        environment._bootstrapped = False
        self.addCleanup(self._restore_environment)

    def _restore_environment(self) -> None:
        environment._bootstrapped = False
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_bootstrap_environment_is_idempotent(self) -> None:
        calls = []

        with patch("src.config.setup_env", side_effect=lambda: calls.append("setup_env")):
            environment.bootstrap_environment()
            environment.bootstrap_environment()

        self.assertEqual(calls, ["setup_env"])
        self.assertTrue(environment._bootstrapped)

    def test_bootstrap_environment_applies_proxy_when_enabled(self) -> None:
        os.environ["USE_PROXY"] = "true"
        os.environ["PROXY_HOST"] = "10.0.0.9"
        os.environ["PROXY_PORT"] = "7890"

        with patch("src.config.setup_env"):
            environment.bootstrap_environment()

        self.assertEqual(os.environ["http_proxy"], "http://10.0.0.9:7890")
        self.assertEqual(os.environ["https_proxy"], "http://10.0.0.9:7890")

    def test_bootstrap_environment_uses_proxy_defaults(self) -> None:
        os.environ["USE_PROXY"] = "true"

        with patch("src.config.setup_env"):
            environment.bootstrap_environment()

        self.assertEqual(os.environ["http_proxy"], "http://127.0.0.1:10809")

    def test_bootstrap_environment_skips_proxy_when_disabled(self) -> None:
        os.environ["USE_PROXY"] = "false"

        with patch("src.config.setup_env"):
            environment.bootstrap_environment()

        self.assertNotIn("http_proxy", os.environ)
        self.assertNotIn("https_proxy", os.environ)

    def test_bootstrap_environment_skips_proxy_on_github_actions(self) -> None:
        os.environ["USE_PROXY"] = "true"
        os.environ["GITHUB_ACTIONS"] = "true"

        with patch("src.config.setup_env"):
            environment.bootstrap_environment()

        self.assertNotIn("http_proxy", os.environ)
        self.assertNotIn("https_proxy", os.environ)

    def test_bootstrap_environment_does_not_touch_database_or_scheduler(self) -> None:
        from src.bootstrap import api_lifecycle, scheduling
        from src.storage import DatabaseManager

        before = DatabaseManager._instance
        with patch("src.config.setup_env"):
            environment.bootstrap_environment()

        self.assertIs(DatabaseManager._instance, before)
        self.assertFalse(hasattr(api_lifecycle, "_bootstrapped"))
        self.assertFalse(hasattr(scheduling, "_bootstrapped"))

    def test_is_public_bind_host(self) -> None:
        for host in ("0.0.0.0", "::", "[::]", "*", " 0.0.0.0 "):
            with self.subTest(host=host):
                self.assertTrue(environment.is_public_bind_host(host))

        for host in ("127.0.0.1", "localhost", "", "::1"):
            with self.subTest(host=host):
                self.assertFalse(environment.is_public_bind_host(host))

    def test_warn_skips_loopback_bind_without_importing_auth(self) -> None:
        with patch("src.auth.is_auth_enabled") as is_auth_enabled:
            environment.warn_if_public_webui_without_auth("127.0.0.1")

        is_auth_enabled.assert_not_called()

    def test_warn_skips_public_bind_when_auth_enabled(self) -> None:
        with patch("src.auth.is_auth_enabled", return_value=True), self.assertNoLogs(
            "src.bootstrap.environment", level="WARNING"
        ):
            environment.warn_if_public_webui_without_auth("0.0.0.0")

    def test_warn_logs_public_bind_without_auth(self) -> None:
        with patch("src.auth.is_auth_enabled", return_value=False), self.assertLogs(
            "src.bootstrap.environment", level="WARNING"
        ) as captured:
            environment.warn_if_public_webui_without_auth("0.0.0.0")

        self.assertIn("ADMIN_AUTH_ENABLED=false", "\n".join(captured.output))


if __name__ == "__main__":
    unittest.main()
