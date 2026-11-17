"""Tests for agent pipeline results."""

from tests.application.agent._agent_pipeline_support import (
    _TestSafeIntFixture,
    unittest,
)


class TestSafeInt(_TestSafeIntFixture, unittest.TestCase):
    def test_int_passthrough(self):
        safe_int = self._get_safe_int()
        self.assertEqual(safe_int(80), 80)

    def test_float_truncate(self):
        safe_int = self._get_safe_int()
        self.assertEqual(safe_int(75.6), 75)

    def test_string_numeric(self):
        safe_int = self._get_safe_int()
        self.assertEqual(safe_int("80"), 80)

    def test_string_with_unit(self):
        """LLM may return '80分' instead of 80."""
        safe_int = self._get_safe_int()
        self.assertEqual(safe_int("80分"), 80)

    def test_string_with_percent(self):
        safe_int = self._get_safe_int()
        self.assertEqual(safe_int("75%"), 75)

    def test_none_default(self):
        safe_int = self._get_safe_int()
        self.assertEqual(safe_int(None), 50)
        self.assertEqual(safe_int(None, 60), 60)

    def test_empty_string(self):
        safe_int = self._get_safe_int()
        self.assertEqual(safe_int(""), 50)

    def test_non_numeric_string(self):
        safe_int = self._get_safe_int()
        self.assertEqual(safe_int("high"), 50)

    def test_negative(self):
        safe_int = self._get_safe_int()
        self.assertEqual(safe_int("-10"), -10)
