#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dependency-direction guard for the HermesX backend.

This script is the executable form of the layering rules described in
``ARCHITECTURE_TARGET.md``. It scans the current worktree with ``ast`` and
compares the result against a checked-in baseline so that existing debt does
not block development while every *new* cross-layer dependency does. Two kinds
of dependency are detected:

1. import statements (``import`` / ``from ... import``, including nested ones
   inside function bodies);
2. private member access (``obj._member``) inside layers that must only talk to
   the public surface of other layers. ``self._x`` / ``cls._x`` are always fine.

Usage::

    python scripts/check_architecture.py --check
    python scripts/check_architecture.py --report
    python scripts/check_architecture.py --write-baseline

Baseline entries are aggregated as ``(path, module) -> count`` so that line
shifts never invalidate the baseline. A new violation is any key whose current
count is higher than the baseline count (or that is missing from the baseline
entirely). Private member accesses use the ``private:<name>`` key namespace so
they never collide with import keys.

Known limitation: dynamically resolved imports (``importlib.import_module`` and
``__import__``) are not detected. Keep them out of the layers listed here, or
extend the scanner when a real use case appears.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASELINE = Path(__file__).resolve().parent / "architecture_baseline.json"
BASELINE_VERSION = 1

SCAN_ROOTS: tuple[str, ...] = ("api", "bot", "src")
SKIP_DIR_NAMES = frozenset({
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "build",
    "dist",
})

# Baseline key namespace for private member accesses (imports use dotted module
# paths, so ``private:...`` can never collide with them).
PRIVATE_MEMBER_PREFIX = "private:"


@dataclass(frozen=True)
class Rule:
    """A single source-layer / forbidden-dependency pair."""

    source_prefix: str
    forbidden: tuple[str, ...]
    note: str
    forbid_private_members: bool = False


# Keep this table in sync with ARCHITECTURE_TARGET.md section 2.
RULES: tuple[Rule, ...] = (
    Rule(
        "api/",
        ("src.storage", "src.repositories", "src.infrastructure", "data_provider"),
        "HTTP drivers call application use cases, not persistence or providers",
    ),
    Rule(
        "bot/",
        ("src.storage", "src.repositories", "src.infrastructure", "data_provider"),
        "Bot drivers call application use cases, not persistence or providers",
    ),
    Rule(
        "src/services/",
        ("fastapi", "sqlalchemy", "api.", "bot."),
        "Application services must stay transport- and ORM-agnostic",
    ),
    Rule(
        "src/core/",
        ("fastapi", "sqlalchemy", "api.", "bot."),
        "Core orchestration must not depend on drivers",
    ),
    Rule(
        "src/domain/",
        (
            "fastapi",
            "sqlalchemy",
            "data_provider",
            "src.services",
            "src.core",
            "src.storage",
            "src.config",
            "src.repositories",
            "src.infrastructure",
            "src.application",
            "api.",
            "bot.",
        ),
        "Domain holds business rules only; no IO, ORM, framework or outer layers "
        "(W4.1: ``src.application`` added so pure rules sunk into the domain cannot "
        "be re-coupled to the use-case layer)",
    ),
    Rule(
        "src/application/",
        (
            "fastapi",
            "sqlalchemy",
            "data_provider",
            "src.repositories",
            "src.infrastructure",
            "src.storage",
            "api.",
            "bot.",
        ),
        "Application depends on domain and ports, not concrete adapters or drivers "
        "(W4.2: ``src.storage`` added once the last direct import was moved behind "
        "``AnalysisPipelinePersistencePort``)",
        # The application layer reuses read models from ``src.services`` during the
        # migration; that reuse must go through the public surface, otherwise the
        # outer layer silently owns implementation details of the inner one.
        forbid_private_members=True,
    ),
    Rule(
        "src/infrastructure/",
        ("api.", "bot."),
        "Infrastructure adapters must not depend on entry drivers",
    ),
    Rule(
        "src/bootstrap/",
        ("api.", "bot."),
        "Bootstrap wires adapters and lifecycle; drivers inject themselves",
    ),
    Rule(
        "src/config/",
        (
            "fastapi",
            "sqlalchemy",
            "data_provider",
            "src.services",
            "src.core",
            "src.repositories",
            "src.infrastructure",
            "src.storage",
            "src.application",
            "api.",
            "bot.",
        ),
        "Configuration depends on the domain only (ARCHITECTURE_TARGET §2); vendor "
        "parameter rules stay behind application ports. W4.5 removed the last three "
        "``src.infrastructure`` delegates by sinking alias→wire-model resolution into "
        "``src.domain.generation.wire_models`` and routing thinking/fallback helpers "
        "through ``GenerationRuntimePort`` (``src.utils`` remains allowed as a legacy "
        "shared helper)",
    ),
    # Fallback for every ``src/`` subtree without a more specific rule above
    # (``src/agent``, ``src/schemas``, ``src/utils``, root modules
    # such as ``src/notification.py``, ...). Specific rules win because
    # ``_rule_for`` returns the first match.
    Rule(
        "src/",
        ("api.", "bot."),
        "Backend layers must not depend on entry drivers",
    ),
)


def _matches(module: str, forbidden: str) -> bool:
    if forbidden.endswith("."):
        return module.startswith(forbidden)
    return module == forbidden or module.startswith(forbidden + ".")


def _package_parts(relative_path: Path) -> list[str]:
    """Return the package parts a relative import is resolved against."""
    parts = list(relative_path.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    else:
        parts.pop()  # drop the module name, keep the package
    return parts


def _resolve_relative(relative_path: Path, level: int, module: str | None) -> str:
    package = _package_parts(relative_path)
    # level == 1 refers to the current package, level == 2 to its parent, ...
    keep = len(package) - (level - 1)
    base = package[:keep] if keep > 0 else []
    if module:
        base.extend(module.split("."))
    return ".".join(part for part in base if part)


def _statement_targets(node: ast.AST, relative_path: Path) -> list[str]:
    """Return import targets for a single import statement, shortest first."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]

    if not isinstance(node, ast.ImportFrom):
        return []

    if node.level:
        base = _resolve_relative(relative_path, node.level, node.module)
    else:
        base = node.module or ""

    targets: list[str] = []
    if base:
        targets.append(base)
    for alias in node.names:
        if alias.name == "*":
            continue
        targets.append(f"{base}.{alias.name}" if base else alias.name)
    # Shortest first: ``from data_provider.base import X`` should be recorded as
    # ``data_provider.base`` rather than ``data_provider.base.X``.
    return sorted(dict.fromkeys(targets), key=lambda item: (item.count("."), len(item)))


def _private_member_target(node: ast.AST) -> str | None:
    """Return the baseline key when ``node`` reads another object's private member.

    Only a bare ``self`` / ``cls`` receiver counts as "the layer's own member";
    anything else (``history._x``, ``Other._x``, ``type(self)._x``) is treated as
    reaching into another object's implementation details.
    """
    if not isinstance(node, ast.Attribute):
        return None
    name = node.attr
    if not name.startswith("_") or name.startswith("__"):
        return None
    receiver = node.value
    if isinstance(receiver, ast.Name) and receiver.id in ("self", "cls"):
        return None
    return f"{PRIVATE_MEMBER_PREFIX}{name}"


def _rule_for(relative_path: str) -> Rule | None:
    for rule in RULES:
        if relative_path.startswith(rule.source_prefix):
            return rule
    return None


def _iter_python_files(root: Path) -> Iterable[tuple[Path, Path]]:
    for scan_root in SCAN_ROOTS:
        base = root / scan_root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            relative_path = path.relative_to(root)
            if any(part in SKIP_DIR_NAMES for part in relative_path.parts):
                continue
            yield path, relative_path


def scan(root: Path) -> tuple[Counter[tuple[str, str]], list[str]]:
    """Scan ``root`` and return ``(violations, parse_errors)``."""
    violations: Counter[tuple[str, str]] = Counter()
    parse_errors: list[str] = []

    for path, relative_path in _iter_python_files(root):
        relative = relative_path.as_posix()
        rule = _rule_for(relative)
        if rule is None:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            parse_errors.append(f"{relative}: {exc}")
            continue

        for node in ast.walk(tree):
            if rule.forbid_private_members:
                private_target = _private_member_target(node)
                if private_target:
                    violations[(relative, private_target)] += 1
            targets = _statement_targets(node, relative_path)
            if not targets:
                continue
            matched: list[str] = []
            for target in targets:
                if any(_matches(target, forbidden) for forbidden in rule.forbidden):
                    matched.append(target)
                    break
            for target in matched:
                violations[(relative, target)] += 1

    return violations, parse_errors


def load_baseline(path: Path) -> dict[tuple[str, str], int]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("entries", [])
    baseline: dict[tuple[str, str], int] = {}
    for entry in entries:
        key = (str(entry["path"]), str(entry["module"]))
        baseline[key] = int(entry.get("count", 1))
    return baseline


def write_baseline(path: Path, violations: Counter[tuple[str, str]]) -> None:
    entries = [
        {"path": path_key, "module": module, "count": count}
        for (path_key, module), count in sorted(violations.items())
    ]
    payload = {
        "version": BASELINE_VERSION,
        "generated_at": date.today().isoformat(),
        "entries": entries,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def find_new_violations(
    current: Counter[tuple[str, str]],
    baseline: dict[tuple[str, str], int],
) -> dict[tuple[str, str], tuple[int, int]]:
    """Return ``{key: (current_count, baseline_count)}`` for new violations."""
    return {
        key: (count, baseline.get(key, 0))
        for key, count in current.items()
        if count > baseline.get(key, 0)
    }


def find_resolved_violations(
    current: Counter[tuple[str, str]],
    baseline: dict[tuple[str, str], int],
) -> dict[tuple[str, str], int]:
    """Return baseline entries whose violation count decreased or vanished."""
    return {
        key: base_count - current.get(key, 0)
        for key, base_count in baseline.items()
        if current.get(key, 0) < base_count
    }


def _print_report(violations: Counter[tuple[str, str]]) -> None:
    if not violations:
        print("No architecture violations found.")
        return
    grouped: dict[str, list[tuple[str, str, int]]] = {}
    for (path, module), count in sorted(violations.items()):
        rule = _rule_for(path)
        label = f"{rule.source_prefix} (baseline rules)" if rule else "unmatched"
        grouped.setdefault(label, []).append((path, module, count))
    total = sum(violations.values())
    print(f"Current architecture violations: {total} cross-layer reference(s)")
    for label in sorted(grouped):
        print(f"\n{label}")
        for path, module, count in grouped[label]:
            suffix = f" x{count}" if count > 1 else ""
            print(f"  {path} -> {module}{suffix}")


def _default_baseline_path(root: Path) -> Path:
    if root.resolve() == REPO_ROOT:
        return DEFAULT_BASELINE
    return root / "scripts" / "architecture_baseline.json"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check cross-layer imports against the architecture baseline.",
    )
    parser.add_argument("--check", action="store_true", help="fail on new violations")
    parser.add_argument("--report", action="store_true", help="print current violations")
    parser.add_argument("--write-baseline", action="store_true", help="rewrite the baseline file")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root to scan")
    parser.add_argument("--baseline", type=Path, default=None, help="baseline JSON path")
    args = parser.parse_args(argv)

    if not (args.check or args.report or args.write_baseline):
        parser.print_help()
        return 2

    root: Path = args.root
    baseline_path: Path = args.baseline or _default_baseline_path(root)

    violations, parse_errors = scan(root)

    if parse_errors:
        print("Failed to parse the following files:", file=sys.stderr)
        for error in parse_errors:
            print(f"  {error}", file=sys.stderr)
        if args.check:
            return 1

    if args.report or args.check:
        _print_report(violations)

    if args.write_baseline:
        write_baseline(baseline_path, violations)
        print(f"\nBaseline written to {baseline_path} ({len(violations)} entries).")

    if args.check:
        baseline = load_baseline(baseline_path)
        new_violations = find_new_violations(violations, baseline)
        resolved = find_resolved_violations(violations, baseline)

        if new_violations:
            print("\nNew architecture violations detected:", file=sys.stderr)
            for (path, module), (current_count, baseline_count) in sorted(
                new_violations.items()
            ):
                print(
                    f"  {path} -> {module}: {current_count} (baseline {baseline_count})",
                    file=sys.stderr,
                )
            print(
                "\nMove the dependency behind an application port (or use the public "
                "member instead of a private one), or update the baseline with "
                "`--write-baseline` only when the change is intentional.",
                file=sys.stderr,
            )
            return 1

        if resolved:
            total = sum(resolved.values())
            print(
                f"\nBaseline has {total} no-longer-reproduced violation(s). "
                "Run `--write-baseline` to shrink it.",
            )

        print("\nArchitecture guard passed.")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
