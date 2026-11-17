"""Tests for system config runtime."""

from tests.application.runtime._system_config_service_support import (
    _SystemConfigRuntimePortWiringTestCaseFixture,
    system_config_service,
    unittest,
)


class SystemConfigRuntimePortWiringTestCase(_SystemConfigRuntimePortWiringTestCaseFixture, unittest.TestCase):
    def test_unconfigured_ports_fail_fast(self) -> None:
        originals = (
            system_config_service._config_probe_port,
            system_config_service._notification_dispatch_port,
            system_config_service._runtime_reset_port,
        )
        try:
            system_config_service._config_probe_port = None
            system_config_service._notification_dispatch_port = None
            system_config_service._runtime_reset_port = None
            with self.assertRaises(RuntimeError):
                system_config_service._get_config_probe_port()
            with self.assertRaises(RuntimeError):
                system_config_service._get_notification_dispatch_port()
            with self.assertRaises(RuntimeError):
                system_config_service._get_runtime_reset_port()
        finally:
            (
                system_config_service._config_probe_port,
                system_config_service._notification_dispatch_port,
                system_config_service._runtime_reset_port,
            ) = originals
