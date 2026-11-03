"""Tests for alphasift configuration."""

from tests.api.alphasift._alphasift_api_support import (
    DEFAULT_ALPHASIFT_TEST_SPEC,
    HTTPException,
    MagicMock,
    SimpleNamespace,
    _AlphaSiftOpportunitiesApiTestCaseFixture,
    _AlphaSiftRuntimePortWiringTestCaseFixture,
    _make_adapter_module,
    _missing_alphasift_module_diagnostics,
    _raise_alphasift_unavailable,
    alphasift_endpoint,
    alphasift_service,
    configure_alphasift_runtime,
    hrs_alphasift_bridge,
    os,
    patch,
    unittest,
)


class AlphaSiftOpportunitiesApiTestCase(_AlphaSiftOpportunitiesApiTestCaseFixture, unittest.TestCase):
    def test_default_install_spec_is_commit_pinned(self) -> None:
        self.assertRegex(
            DEFAULT_ALPHASIFT_TEST_SPEC,
            r"^git\+https://github\.com/ZhuLinsen/alphasift\.git@[0-9a-f]{40}$",
        )

    def test_status_defaults_to_disabled(self) -> None:
        config = self._config(enabled=False)

        with patch("src.application.analysis.alphasift_service._call_alphasift_status", side_effect=_raise_alphasift_unavailable):
            payload = alphasift_endpoint.alphasift_status(config=config)

        self.assertEqual(payload["enabled"], False)
        self.assertEqual(payload["available"], False)
        self.assertEqual(payload["install_spec_is_default"], True)
        self.assertNotIn("diagnostics", payload)
        self.assertNotIn("install_spec", payload)

    def test_status_marks_custom_install_source(self) -> None:
        config = self._config(enabled=False, install_spec="git+https://example.com/private/alphasift.git")

        with patch("src.application.analysis.alphasift_service._call_alphasift_status", side_effect=_raise_alphasift_unavailable):
            payload = alphasift_endpoint.alphasift_status(config=config)

        self.assertEqual(payload["install_spec_is_default"], False)
        self.assertNotIn("install_spec", payload)

    def test_status_includes_adapter_contract_metadata(self) -> None:
        config = self._config(enabled=True)

        with patch(
            "src.application.analysis.alphasift_service._call_alphasift_status",
            return_value={"available": True, "contract_version": "1", "version": "0.2.0", "strategy_count": 8},
        ):
            payload = alphasift_endpoint.alphasift_status(config=config)

        self.assertTrue(payload["available"])
        self.assertEqual(payload["contract_version"], "1")
        self.assertEqual(payload["version"], "0.2.0")
        self.assertEqual(payload["strategy_count"], 8)

    def test_status_includes_alphasift_source_health_snapshot(self) -> None:
        config = self._config(enabled=True)

        with (
            patch(
                "src.application.analysis.alphasift_service._call_alphasift_status",
                return_value={"available": True, "contract_version": "1", "version": "0.2.0", "strategy_count": 8},
            ),
            patch(
                "src.application.analysis.alphasift_service._get_alphasift_source_health_snapshot",
                return_value={"snapshot": {"sina": {"failures": 2, "disabled": False}}},
            ),
        ):
            payload = alphasift_endpoint.alphasift_status(config=config)

        self.assertEqual(payload["source_health"]["snapshot"]["sina"]["failures"], 2)

    def test_status_preserves_adapter_available_false_without_diagnostics(self) -> None:
        config = self._config(enabled=False)

        with patch(
            "src.application.analysis.alphasift_service._call_alphasift_status",
            return_value={"available": False, "contract_version": "1", "version": "0.2.0", "strategy_count": 0},
        ):
            payload = alphasift_endpoint.alphasift_status(config=config)

        self.assertFalse(payload["available"])
        self.assertEqual(payload["contract_version"], "1")
        self.assertNotIn("diagnostics", payload)

    def test_status_logs_and_reports_adapter_runtime_exception_diagnostics(self) -> None:
        config = self._config(enabled=False)
        fake_module = _make_adapter_module(get_status=MagicMock(side_effect=RuntimeError("get_status failed")))

        with (
            patch("src.application.analysis.alphasift_service._import_alphasift", return_value=fake_module),
            self.assertLogs("src.application.analysis.alphasift_service", level="WARNING") as captured,
        ):
            payload = alphasift_endpoint.alphasift_status(config=config)

        self.assertFalse(payload["available"])
        self.assertEqual(payload["diagnostics"]["reason"], "unexpected_exception")
        self.assertEqual(payload["diagnostics"]["stage"], "get_status")
        self.assertEqual(payload["diagnostics"]["error_type"], "RuntimeError")
        self.assertIn("Unexpected AlphaSift get_status failure", "\n".join(captured.output))

    def test_status_logs_and_reports_unexpected_import_exception_diagnostics(self) -> None:
        config = self._config(enabled=False)
        missing_sub_dependency = ModuleNotFoundError("No module named 'optional_dep'", name="optional_dep")

        with (
            patch("src.application.analysis.alphasift_service._prepare_alphasift_runtime_env"),
            patch("src.application.analysis.alphasift_service.importlib.import_module", side_effect=missing_sub_dependency),
            self.assertLogs("src.application.analysis.alphasift_service", level="WARNING") as captured,
        ):
            payload = alphasift_endpoint.alphasift_status(config=config)

        self.assertFalse(payload["available"])
        self.assertEqual(payload["diagnostics"]["reason"], "unexpected_exception")
        self.assertEqual(payload["diagnostics"]["stage"], "import_adapter")
        self.assertEqual(payload["diagnostics"]["error_type"], "ModuleNotFoundError")
        self.assertIn("Unexpected AlphaSift import_adapter failure", "\n".join(captured.output))

    def test_status_marks_missing_module_for_dependency_diagnostic(self) -> None:
        config = self._config(enabled=True)
        missing_module_exc = ModuleNotFoundError("No module named 'alphasift.dsa_adapter'", name="alphasift.dsa_adapter")

        with (
            patch("src.application.analysis.alphasift_service._import_alphasift", side_effect=missing_module_exc),
            self.assertLogs("src.application.analysis.alphasift_service", level="WARNING"),
        ):
            payload = alphasift_endpoint.alphasift_status(config=config)

        self.assertFalse(payload["available"])
        self.assertEqual(payload["diagnostics"]["reason"], "missing_module")
        self.assertEqual(payload["diagnostics"]["stage"], "import_adapter")
        self.assertEqual(payload["diagnostics"]["error_type"], "ModuleNotFoundError")

    def test_status_logs_and_reports_invalid_get_status_result_diagnostics(self) -> None:
        config = self._config(enabled=False)
        fake_module = _make_adapter_module(get_status=lambda: ["not", "a", "dict"])

        with (
            patch("src.application.analysis.alphasift_service._import_alphasift", return_value=fake_module),
            self.assertLogs("src.application.analysis.alphasift_service", level="WARNING") as captured,
        ):
            payload = alphasift_endpoint.alphasift_status(config=config)

        self.assertFalse(payload["available"])
        self.assertEqual(payload["diagnostics"]["reason"], "unexpected_exception")
        self.assertEqual(payload["diagnostics"]["stage"], "get_status_result")
        self.assertEqual(payload["diagnostics"]["error_type"], "TypeError")
        self.assertIn("Unexpected AlphaSift get_status_result failure", "\n".join(captured.output))

    def test_status_logs_and_reports_missing_get_status_callable_diagnostics(self) -> None:
        config = self._config(enabled=False)
        fake_module = SimpleNamespace(list_strategies=lambda: [], screen=MagicMock(return_value=[]))

        with (
            patch("src.application.analysis.alphasift_service._import_alphasift", return_value=fake_module),
            self.assertLogs("src.application.analysis.alphasift_service", level="WARNING") as captured,
        ):
            payload = alphasift_endpoint.alphasift_status(config=config)

        self.assertFalse(payload["available"])
        self.assertEqual(payload["diagnostics"]["reason"], "unexpected_exception")
        self.assertEqual(payload["diagnostics"]["stage"], "get_status_callable")
        self.assertEqual(payload["diagnostics"]["error_type"], "AlphaSiftServiceError")
        self.assertIn("Unexpected AlphaSift get_status_callable failure", "\n".join(captured.output))

    def test_strategies_rejects_when_enabled_but_adapter_missing(self) -> None:
        config = self._config(enabled=True)

        with (
            patch(
                "src.application.analysis.alphasift_service._get_alphasift_status_snapshot",
                return_value=({}, False, _missing_alphasift_module_diagnostics()),
            ),
            patch("src.application.analysis.alphasift_service._install_alphasift") as install_mock,
        ):
            with self.assertRaises(HTTPException) as caught:
                self._strategies(config=config)

        self.assertEqual(caught.exception.status_code, 424)
        self.assertEqual(caught.exception.detail["error"], "alphasift_unavailable")
        self.assertEqual(caught.exception.detail.get("diagnostics", {}).get("reason"), "missing_module")
        install_mock.assert_not_called()

    def test_install_rejects_spoofed_localhost_without_admin_session(self) -> None:
        config = self._config(enabled=True)
        request = SimpleNamespace(
            cookies={alphasift_endpoint.COOKIE_NAME: "invalid-session"},
            url=SimpleNamespace(hostname="localhost"),
            client=SimpleNamespace(host="127.0.0.1"),
        )

        with (
            patch.dict(os.environ, {"HRS_DESKTOP_MODE": "false"}, clear=False),
            patch("api.v1.endpoints.alphasift.refresh_auth_state") as refresh_mock,
            patch("api.v1.endpoints.alphasift.is_auth_enabled", return_value=True),
            patch("api.v1.endpoints.alphasift.verify_session", return_value=False) as verify_session_mock,
            patch("src.application.analysis.alphasift_service.subprocess.run") as run_mock,
        ):
            with self.assertRaises(HTTPException) as caught:
                alphasift_endpoint.alphasift_install(request=request, config=config)

        self.assertEqual(caught.exception.status_code, 401)
        self.assertEqual(caught.exception.detail["error"], "alphasift_install_access_denied")
        refresh_mock.assert_called_once()
        verify_session_mock.assert_called_once_with("invalid-session")
        run_mock.assert_not_called()

    def test_install_allows_valid_admin_session_outside_desktop_mode(self) -> None:
        config = self._config(enabled=True)
        request = self._request({alphasift_endpoint.COOKIE_NAME: "valid-session"})

        with (
            patch.dict(os.environ, {"HRS_DESKTOP_MODE": "false"}, clear=False),
            patch("api.v1.endpoints.alphasift.refresh_auth_state") as refresh_mock,
            patch("api.v1.endpoints.alphasift.is_auth_enabled", return_value=True),
            patch("api.v1.endpoints.alphasift.verify_session", return_value=True) as verify_session_mock,
            patch("src.application.analysis.alphasift_service._install_alphasift", return_value={"installed": True}) as install_mock,
        ):
            payload = alphasift_endpoint.alphasift_install(request=request, config=config)

        self.assertEqual(payload["installed"], True)
        refresh_mock.assert_called_once()
        verify_session_mock.assert_called_once_with("valid-session")
        install_mock.assert_called_once_with(config)

    def test_install_rejects_when_disabled_without_side_effects(self) -> None:
        config = self._config(enabled=False)

        with (
            patch.dict(os.environ, {"HRS_DESKTOP_MODE": "true"}, clear=False),
            patch("src.application.analysis.alphasift_service.subprocess.run") as run_mock,
            patch("src.application.analysis.alphasift_service._import_alphasift") as import_mock,
        ):
            with self.assertRaises(HTTPException) as caught:
                alphasift_endpoint.alphasift_install(request=self._request(), config=config)

        self.assertEqual(caught.exception.status_code, 403)
        self.assertEqual(caught.exception.detail["error"], "alphasift_disabled")
        import_mock.assert_not_called()
        run_mock.assert_not_called()

    def test_install_invokes_pip_when_enabled_and_missing(self) -> None:
        config = self._config(enabled=True)
        completed = SimpleNamespace(returncode=0, stdout="installed", stderr="")

        with (
            patch.dict(os.environ, {"HRS_DESKTOP_MODE": "true"}, clear=False),
            patch("src.application.analysis.alphasift_service._is_alphasift_available", side_effect=[False, True]),
            patch(
                "src.application.analysis.alphasift_service._call_alphasift_status",
                return_value={"available": True, "supported_markets": ["cn"], "contract_version": "1", "version": "0.2.0", "strategy_count": 1},
            ),
            patch("src.application.analysis.alphasift_service.subprocess.run", return_value=completed) as run_mock,
            patch("src.application.analysis.alphasift_service._get_hrs_adapter", return_value=_make_adapter_module()),
        ):
            payload = alphasift_endpoint.alphasift_install(request=self._request(), config=config)

        self.assertEqual(payload["installed"], True)
        self.assertEqual(payload["already_installed"], False)
        self.assertEqual(payload["install_spec_is_default"], True)
        self.assertNotIn("install_spec", payload)
        run_mock.assert_called_once()
        install_command = run_mock.call_args.args[0]
        self.assertIn("--upgrade", install_command)
        self.assertIn("--force-reinstall", install_command)
        self.assertIn(DEFAULT_ALPHASIFT_TEST_SPEC, install_command)

    def test_install_rejects_when_alphasift_adapter_reports_unavailable(self) -> None:
        config = self._config(enabled=True)
        completed = SimpleNamespace(returncode=0, stdout="installed", stderr="")

        with (
            patch.dict(os.environ, {"HRS_DESKTOP_MODE": "true"}, clear=False),
            patch(
                "src.application.analysis.alphasift_service._call_alphasift_status",
                side_effect=[
                    {"available": False},
                    {"available": False},
                ],
            ),
            patch("src.application.analysis.alphasift_service.subprocess.run", return_value=completed) as run_mock,
            patch("src.application.analysis.alphasift_service._get_hrs_adapter") as get_adapter_mock,
        ):
            with self.assertRaises(HTTPException) as caught:
                alphasift_endpoint.alphasift_install(request=self._request(), config=config)

        self.assertEqual(caught.exception.status_code, 424)
        self.assertEqual(caught.exception.detail["error"], "alphasift_unavailable")
        run_mock.assert_called_once()
        get_adapter_mock.assert_not_called()

    def test_install_rejects_untrusted_spec(self) -> None:
        config = self._config(enabled=True, install_spec="git+https://example.com/private/alphasift.git")

        with (
            patch.dict(os.environ, {"HRS_DESKTOP_MODE": "true"}, clear=False),
            patch("src.application.analysis.alphasift_service._is_alphasift_available", return_value=False),
            patch("src.application.analysis.alphasift_service.subprocess.run") as run_mock,
        ):
            with self.assertRaises(HTTPException) as caught:
                alphasift_endpoint.alphasift_install(request=self._request(), config=config)

        self.assertEqual(caught.exception.status_code, 403)
        self.assertEqual(caught.exception.detail["error"], "alphasift_install_spec_not_allowed")
        run_mock.assert_not_called()

    def test_alphasift_runtime_priority_puts_tushare_before_sina_when_token_exists(self) -> None:
        config = self._config(enabled=True)
        config.tushare_token = "token-1"

        with patch.dict(alphasift_service.os.environ, {"SNAPSHOT_SOURCE_PRIORITY": ""}, clear=False):
            env = hrs_alphasift_bridge._build_alphasift_runtime_env(config)

        self.assertEqual(env["SNAPSHOT_SOURCE_PRIORITY"], "tushare,sina,efinance,akshare_em,em_datacenter")


class AlphaSiftRuntimePortWiringTestCase(_AlphaSiftRuntimePortWiringTestCaseFixture, unittest.TestCase):
    def test_configure_alphasift_runtime_binds_adapter_idempotently(self) -> None:
        from src.application.analysis.alphasift_ports import AlphaSiftRuntimePort  # noqa: F401  契约锚点
        from src.infrastructure.providers.hrs_alphasift_bridge import AlphaSiftRuntimeAdapter

        original = alphasift_service._alphasift_runtime_port
        try:
            alphasift_service.set_alphasift_runtime_port(None)  # None 不覆盖：幂等语义
            self.assertIsInstance(alphasift_service._get_alphasift_runtime_port(), AlphaSiftRuntimeAdapter)
            configure_alphasift_runtime()
            configure_alphasift_runtime()
            self.assertIsInstance(alphasift_service._get_alphasift_runtime_port(), AlphaSiftRuntimeAdapter)
        finally:
            alphasift_service._alphasift_runtime_port = original

    def test_unconfigured_port_fails_fast(self) -> None:
        original = alphasift_service._alphasift_runtime_port
        try:
            alphasift_service._alphasift_runtime_port = None
            with self.assertRaises(alphasift_service.AlphaSiftServiceError) as caught:
                alphasift_service._get_alphasift_runtime_port()
            self.assertEqual(caught.exception.status_code, 503)
            self.assertEqual(caught.exception.detail["error"], "alphasift_runtime_port_not_configured")
        finally:
            alphasift_service._alphasift_runtime_port = original
