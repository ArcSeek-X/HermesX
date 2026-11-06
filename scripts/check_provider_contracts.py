#!/usr/bin/env python3
"""Audit baseline provider files, public call signatures and current import consumers.

Read-only contract audit; no SDK instances, requests, baseline updates or Git mutations.
"""

from __future__ import annotations

import argparse
import ast
import dataclasses
import importlib
import inspect
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent

# Deliberately retired internal module paths retain baseline contract coverage.
# Values map each old public symbol to its unique current implementation.
RETIRED_MODULES = {
    "data_provider.us_index_mapping": {
        "US_INDEX_MAPPING": "src.domain.market.us_index_symbols",
        "is_us_index_code": "src.domain.market.us_index_symbols",
        "is_us_stock_code": "src.domain.market.us_index_symbols",
        "get_us_index_yf_symbol": "data_provider.common.symbols",
    },
}

MODULE_DESTINATIONS = {
    "data_provider.tickflow_fetcher": "data_provider.runtime.fetchers.tickflow",
    "data_provider.akshare_fetcher": "data_provider.runtime.fetchers.akshare",
    "data_provider.longbridge_fetcher": "data_provider.runtime.fetchers.longbridge",
    "data_provider.efinance_fetcher": "data_provider.runtime.fetchers.efinance",
    "data_provider.tushare_fetcher": "data_provider.runtime.fetchers.tushare",
    "data_provider.pytdx_fetcher": "data_provider.runtime.fetchers.pytdx",
    "data_provider.yfinance_fetcher": "data_provider.runtime.fetchers.yfinance",
    "data_provider.baostock_fetcher": "data_provider.runtime.fetchers.baostock",
    "data_provider.finnhub_fetcher": "data_provider.runtime.fetchers.finnhub",
    "data_provider.alphavantage_fetcher": "data_provider.runtime.fetchers.alphavantage",
    "data_provider.eastmoney_quote_snapshot": "data_provider.market.eastmoney_source",
    "data_provider.tencent_quote_snapshot": "data_provider.market.tencent_source",
    "data_provider.fundamental_adapter": "data_provider.fundamentals.akshare_source",
    "data_provider.yfinance_fundamental_adapter": "data_provider.fundamentals.yfinance_source",
    "data_provider.realtime_types": "data_provider.realtime.types",
    "data_provider.stockdb_fetcher": "data_provider.clients.stockdb",
    "data_provider.stocksdk_bridge": "data_provider.clients.stocksdk.bridge",
    "data_provider.tencent_fetcher": "data_provider.kline.daily_tencent_source",
    "data_provider.tw_institutional_fetcher": "data_provider.institutional.tw_client",
    "data_provider.wallstreetcn_calendar_fetcher": "data_provider.calendar.wallstreetcn_source",
    "data_provider.wallstreetcn_live_news_fetcher": "data_provider.news.wallstreetcn_live",
}
RETIRED_MODULES["data_provider.realtime_types"] = {
    name: "data_provider.common.health"
    for name in ("CircuitBreaker", "get_chip_circuit_breaker", "get_realtime_circuit_breaker")
}


def baseline_symbol(module_name, name):
    target = RETIRED_MODULES.get(module_name, {}).get(name, MODULE_DESTINATIONS.get(module_name, module_name))
    return getattr(importlib.import_module(target), name, None)


def shape(node):
    args = node.args
    positional = args.posonlyargs + args.args
    defaults = len(positional) - len(args.defaults)
    result = [
        (a.arg, "POSITIONAL_ONLY" if i < len(args.posonlyargs) else "POSITIONAL_OR_KEYWORD", i >= defaults)
        for i, a in enumerate(positional)
    ]
    result += [(a.arg, "KEYWORD_ONLY", default is not None) for a, default in zip(args.kwonlyargs, args.kw_defaults)]
    if args.vararg:
        result.append((args.vararg.arg, "VAR_POSITIONAL", False))
    if args.kwarg:
        result.append((args.kwarg.arg, "VAR_KEYWORD", False))
    return [x for x in result if x[0] not in ("self", "cls")]


def audit(root: Path, baseline: str):
    files = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", baseline, "data_provider"], cwd=root, text=True
    ).splitlines()
    files = [p for p in files if p.endswith(".py")]
    records, errors = [], []
    for path in files:
        original = subprocess.check_output(["git", "show", f"{baseline}:{path}"], cwd=root, text=True)
        tree = ast.parse(original)
        module_name = path[:-3].replace("/", ".").removesuffix(".__init__")
        retired = module_name in RETIRED_MODULES or module_name in MODULE_DESTINATIONS
        module = None if retired else importlib.import_module(module_name)
        checked = 0
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                obj = baseline_symbol(module_name, node.name)
                if not inspect.isclass(obj):
                    errors.append(f"{path}: missing class {node.name}")
                    continue
                candidates = [
                    (fn, getattr(obj, fn.name, None))
                    for fn in node.body
                    if isinstance(fn, ast.FunctionDef) and (not fn.name.startswith("_") or fn.name == "__init__")
                ]
                if dataclasses.is_dataclass(obj):
                    old_fields = [
                        n.target.id
                        for n in node.body
                        if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
                    ]
                    current_fields = [f.name for f in dataclasses.fields(obj)]
                    if old_fields != current_fields:
                        errors.append(f"{path}: dataclass fields changed: {node.name}")
            elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                candidates = [(node, baseline_symbol(module_name, node.name))]
            else:
                continue
            for fn, current in candidates:
                checked += 1
                is_property = any(isinstance(d, ast.Name) and d.id == "property" for d in fn.decorator_list)
                if is_property and isinstance(current, property):
                    current = current.fget
                elif is_property:
                    errors.append(f"{path}: property changed: {fn.name}")
                if not callable(current):
                    errors.append(f"{path}: missing callable {fn.name}")
                    continue
                signature = inspect.signature(current)
                actual = {
                    p.name: (p.kind.name, p.default is not inspect.Parameter.empty)
                    for p in signature.parameters.values()
                    if p.name not in ("self", "cls")
                }
                expected_positional = [name for name, kind, _ in shape(fn) if kind.startswith("POSITIONAL")]
                actual_positional = [name for name, (kind, _) in actual.items() if kind.startswith("POSITIONAL")]
                if actual_positional[: len(expected_positional)] != expected_positional:
                    errors.append(f"{path}:{fn.name}: positional parameter order changed")
                expected_names = {name for name, _, _ in shape(fn)}
                for name, (kind, default) in actual.items():
                    if name not in expected_names and not default and kind not in ("VAR_POSITIONAL", "VAR_KEYWORD"):
                        errors.append(f"{path}:{fn.name}: new required parameter {name}")
                for name, kind, default in shape(fn):
                    # New optional parameters are allowed, existing parameters retain kind/default presence.
                    if actual.get(name) != (kind, default):
                        errors.append(f"{path}:{fn.name}: incompatible parameter {name}: {actual.get(name)}")
        records.append(
            {
                "path": path,
                "canonical_module": MODULE_DESTINATIONS.get(module_name) if retired else module.__name__,
                "symbol_destinations": RETIRED_MODULES.get(module_name, {}),
                "retired_internal_path": retired,
                "checked_callables": checked,
                "retained": (root / path).exists(),
            }
        )
    consumers = []
    python_paths = set(root.glob("*.py"))
    for base in ("src", "api", "bot", "scripts", "tests", "data_provider", ".github/scripts"):
        python_paths.update((root / base).rglob("*.py"))
    for path in sorted(python_paths):
        if any(x in {"node_modules", "__pycache__"} for x in path.parts):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                targets = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom):
                targets = [n.module or ""]
            elif (
                isinstance(n, ast.Constant)
                and isinstance(n.value, str)
                and re.fullmatch(r"data_provider(?:\.[A-Za-z_]\w*)*", n.value)
            ):
                targets = [n.value]
            else:
                continue
            for target in targets:
                if target == "data_provider" or target.startswith("data_provider."):
                    consumers.append(
                        {
                            "path": path.relative_to(root).as_posix(),
                            "line": n.lineno,
                            "target": target,
                            "symbolic": isinstance(n, ast.Constant),
                        }
                    )
    integration_references = []
    for base in ("scripts", ".github", "docker"):
        for path in sorted((root / base).rglob("*")):
            if (
                not path.is_file()
                or path.suffix not in {".sh", ".ps1", ".yml", ".yaml"}
                or "node_modules" in path.parts
            ):
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if "data_provider" in line:
                    integration_references.append(
                        {"path": path.relative_to(root).as_posix(), "line": number, "kind": "build/workflow"}
                    )
    package = importlib.import_module("data_provider")
    exports = {
        name: {
            "module": module,
            "symbol": symbol,
            "resolved": getattr(package, name) is getattr(importlib.import_module(module), symbol),
        }
        for name, (module, symbol) in package._EXPORTS.items()
    }
    return {
        "integration_references": integration_references,
        "export_registry": exports,
        "baseline": baseline,
        "baseline_files": records,
        "consumers": consumers,
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT))
    report = audit(ROOT, args.baseline)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        f"{len(report['baseline_files'])} baseline files; {sum(x['checked_callables'] for x in report['baseline_files'])} callables; {len(report['consumers'])} consumer references; {len(report['errors'])} errors"
    )
    for error in report["errors"]:
        print(error)
    return bool(report["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
