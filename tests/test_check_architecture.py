# -*- coding: utf-8 -*-
"""Tests for ``scripts/check_architecture.py``."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_architecture.py"


def _load_guard():
    spec = importlib.util.spec_from_file_location("check_architecture", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Register before exec so dataclasses can resolve string annotations.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class ArchitectureScanTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.guard = _load_guard()
        self._temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._temp_dir.name)

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def test_allowed_import_produces_no_violation(self) -> None:
        _write(self.root, "api/routes.py", "from src.services.stock_service import StockService\n")

        violations, errors = self.guard.scan(self.root)

        self.assertEqual(errors, [])
        self.assertEqual(violations, {})

    def test_direct_violation_is_detected(self) -> None:
        _write(self.root, "api/repo.py", "from src.storage import DatabaseManager\n")

        violations, errors = self.guard.scan(self.root)

        self.assertEqual(errors, [])
        self.assertEqual(violations[("api/repo.py", "src.storage")], 1)

    def test_from_package_import_is_detected(self) -> None:
        _write(self.root, "api/from_src.py", "from src import storage\n")

        violations, _ = self.guard.scan(self.root)

        self.assertEqual(violations[("api/from_src.py", "src.storage")], 1)

    def test_import_statement_is_detected(self) -> None:
        _write(self.root, "api/plain.py", "import data_provider.base\n")

        violations, _ = self.guard.scan(self.root)

        self.assertEqual(violations[("api/plain.py", "data_provider.base")], 1)

    def test_multiple_statements_are_counted(self) -> None:
        _write(
            self.root,
            "api/multi.py",
            "from src.storage import DatabaseManager\n"
            "\n"
            "def load():\n"
            "    from src.storage import get_db\n"
            "    return get_db()\n",
        )

        violations, _ = self.guard.scan(self.root)

        self.assertEqual(violations[("api/multi.py", "src.storage")], 2)

    def test_relative_import_resolution(self) -> None:
        relative = Path("src/services/quote/mod.py")

        self.assertEqual(
            self.guard._resolve_relative(relative, 1, "helpers"),
            "src.services.quote.helpers",
        )
        self.assertEqual(
            self.guard._resolve_relative(relative, 2, "core"),
            "src.services.core",
        )
        self.assertEqual(
            self.guard._resolve_relative(relative, 1, None),
            "src.services.quote",
        )

    def test_parse_errors_are_reported(self) -> None:
        _write(self.root, "api/broken.py", "def broken(:\n")

        _, errors = self.guard.scan(self.root)

        self.assertEqual(len(errors), 1)
        self.assertIn("api/broken.py", errors[0])

    def test_missing_layer_directories_do_not_fail(self) -> None:
        violations, errors = self.guard.scan(self.root)

        self.assertEqual(violations, {})
        self.assertEqual(errors, [])

    def test_src_fallback_rule_blocks_entry_driver_imports(self) -> None:
        _write(
            self.root,
            "src/notification.py",
            "def send():\n"
            "    from bot.platforms.feishu_stream import FeishuReplyClient\n",
        )
        _write(
            self.root,
            "src/agent/tools/handler.py",
            "from api.v1.schemas.run_flow import RunFlowSnapshot\n",
        )

        violations, errors = self.guard.scan(self.root)

        self.assertEqual(errors, [])
        self.assertEqual(
            violations[("src/notification.py", "bot.platforms.feishu_stream")], 1
        )
        self.assertEqual(
            violations[("src/agent/tools/handler.py", "api.v1.schemas.run_flow")], 1
        )

    def test_src_fallback_rule_allows_backend_to_backend_imports(self) -> None:
        _write(
            self.root,
            "src/notification.py",
            "from src.schemas.bot_message import BotMessage\n",
        )

        violations, errors = self.guard.scan(self.root)

        self.assertEqual(errors, [])
        self.assertEqual(violations, {})

    def test_application_rule_blocks_concrete_repository_import(self) -> None:
        # PP-7 收紧：仓储已全部下沉 infra，application 不得再直接 import
        # ``src.repositories``（端口化回归防线）。
        _write(
            self.root,
            "src/application/quote/stock_service.py",
            "from src.repositories import StockRepository\n",
        )

        violations, errors = self.guard.scan(self.root)

        self.assertEqual(errors, [])
        self.assertEqual(
            violations[("src/application/quote/stock_service.py", "src.repositories")], 1
        )

    def test_application_rule_blocks_private_member_access(self) -> None:
        _write(
            self.root,
            "src/application/history/service.py",
            "from src.services.history_service import HistoryService\n"
            "\n"
            "\n"
            "class HistoryQueryService:\n"
            "    def _history(self):\n"
            "        return HistoryService(self._repository)\n"
            "\n"
            "    def delete_by_code(self, stock_code):\n"
            "        history = self._history()\n"
            "        return HistoryService._history_code_filter_candidates(stock_code) + "
            "history._display_stock_code(stock_code)\n",
        )

        violations, errors = self.guard.scan(self.root)

        self.assertEqual(errors, [])
        self.assertEqual(
            violations[("src/application/history/service.py", "private:_history_code_filter_candidates")],
            1,
        )
        self.assertEqual(
            violations[("src/application/history/service.py", "private:_display_stock_code")],
            1,
        )

    def test_application_rule_allows_own_and_dunder_members(self) -> None:
        _write(
            self.root,
            "src/application/history/service.py",
            "class HistoryQueryService:\n"
            "    def __init__(self, repository):\n"
            "        self._repository = repository\n"
            "\n"
            "    def list_records(self, record):\n"
            "        state = record.__dict__\n"
            "        return self._repository.get(state), self._helper()\n"
            "\n"
            "    @classmethod\n"
            "    def _build(cls):\n"
            "        return cls._instance\n",
        )

        violations, errors = self.guard.scan(self.root)

        self.assertEqual(errors, [])
        self.assertEqual(violations, {})

    def test_private_member_rule_is_scoped_to_the_application_layer(self) -> None:
        # ``src/services`` and ``api`` keep their private helpers to themselves;
        # only the application layer is held to the public surface of other layers.
        _write(
            self.root,
            "src/services/history_service.py",
            "class HistoryService:\n"
            "    def list(self):\n"
            "        return _module_helper()\n",
        )
        _write(
            self.root,
            "api/v1/endpoints/history.py",
            "from src.services.history_service import HistoryService\n"
            "\n"
            "def endpoint():\n"
            "    return HistoryService._hidden()\n",
        )

        violations, errors = self.guard.scan(self.root)

        self.assertEqual(errors, [])
        self.assertEqual(violations, {})

    def test_repository_has_no_cross_layer_private_member_access(self) -> None:
        """The shipped worktree must not rely on baseline entries for private members."""
        violations, errors = self.guard.scan(REPO_ROOT)

        self.assertEqual(errors, [])
        self.assertEqual(
            [
                (path, module)
                for (path, module) in violations
                if module.startswith(self.guard.PRIVATE_MEMBER_PREFIX)
            ],
            [],
        )


class ArchitectureBaselineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.guard = _load_guard()
        self._temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._temp_dir.name)
        self.baseline_path = self.root / "baseline.json"

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def test_baseline_allows_existing_violation(self) -> None:
        _write(self.root, "api/legacy.py", "from src.storage import DatabaseManager\n")
        violations, _ = self.guard.scan(self.root)
        self.guard.write_baseline(self.baseline_path, violations)

        baseline = self.guard.load_baseline(self.baseline_path)

        self.assertEqual(
            self.guard.find_new_violations(violations, baseline),
            {},
        )

    def test_baseline_blocks_increased_count(self) -> None:
        _write(self.root, "api/legacy.py", "from src.storage import DatabaseManager\n")
        violations, _ = self.guard.scan(self.root)
        self.guard.write_baseline(self.baseline_path, violations)

        _write(
            self.root,
            "api/legacy.py",
            "from src.storage import DatabaseManager\n"
            "from src.storage import get_db\n",
        )
        current, _ = self.guard.scan(self.root)
        new = self.guard.find_new_violations(
            current,
            self.guard.load_baseline(self.baseline_path),
        )

        self.assertEqual(new[("api/legacy.py", "src.storage")], (2, 1))

    def test_baseline_reports_resolved_violations(self) -> None:
        _write(self.root, "api/legacy.py", "from src.storage import DatabaseManager\n")
        violations, _ = self.guard.scan(self.root)
        self.guard.write_baseline(self.baseline_path, violations)

        _write(self.root, "api/legacy.py", "from src.services.stock_service import StockService\n")
        current, _ = self.guard.scan(self.root)
        resolved = self.guard.find_resolved_violations(
            current,
            self.guard.load_baseline(self.baseline_path),
        )

        self.assertEqual(resolved[("api/legacy.py", "src.storage")], 1)

    def test_write_baseline_output_is_sorted_and_versioned(self) -> None:
        _write(self.root, "api/z.py", "from src.storage import DatabaseManager\n")
        _write(self.root, "api/a.py", "from data_provider.base import normalize_stock_code\n")
        violations, _ = self.guard.scan(self.root)

        self.guard.write_baseline(self.baseline_path, violations)

        payload = json.loads(self.baseline_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["version"], 1)
        self.assertEqual(
            [entry["path"] for entry in payload["entries"]],
            ["api/a.py", "api/z.py"],
        )

    def test_check_command_fails_on_new_violation(self) -> None:
        _write(self.root, "api/legacy.py", "from src.storage import DatabaseManager\n")
        violations, _ = self.guard.scan(self.root)
        self.guard.write_baseline(self.baseline_path, violations)

        self.assertEqual(
            self.guard.main(["--check", "--root", str(self.root), "--baseline", str(self.baseline_path)]),
            0,
        )

        _write(
            self.root,
            "api/new_violation.py",
            "from data_provider.base import canonical_stock_code\n",
        )

        self.assertEqual(
            self.guard.main(["--check", "--root", str(self.root), "--baseline", str(self.baseline_path)]),
            1,
        )


if __name__ == "__main__":
    unittest.main()
