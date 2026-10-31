#!/usr/bin/env bash

set -euo pipefail

syntax_check() {
  echo "==> backend-gate: Python syntax check"
  python -m py_compile main.py server.py webui.py src/auth.py src/application/analysis/analyzer.py src/application/notification/notification.py
  python -m py_compile src/config/__init__.py src/config/settings.py src/config/env_file.py src/config/registry.py
  python -m py_compile src/storage.py src/application/runtime/scheduler.py src/application/intelligence/search_service.py
  python -m py_compile src/application/market/market_analyzer.py src/domain/analysis/stock_analyzer.py
  python -m py_compile src/bootstrap/*.py scripts/check_architecture.py
  python -m py_compile data_provider/*.py
}

architecture_check() {
  echo "==> backend-gate: architecture import guard"
  python scripts/check_architecture.py --check
}

flake8_checks() {
  echo "==> backend-gate: flake8 critical checks"
  flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
}

deterministic_checks() {
  echo "==> backend-gate: local deterministic checks"
  ./scripts/test.sh code
  ./scripts/test.sh yfinance
}

offline_test_suite() {
  echo "==> backend-gate: offline test suite"
  python -m pytest -m "not network"
}

run_all() {
  syntax_check
  architecture_check
  flake8_checks
  deterministic_checks
  offline_test_suite
  echo "==> backend-gate: all checks passed"
}

phase="${1:-all}"

case "$phase" in
  all)
    run_all
    ;;
  syntax)
    syntax_check
    ;;
  architecture)
    architecture_check
    ;;
  flake8)
    flake8_checks
    ;;
  deterministic)
    deterministic_checks
    ;;
  offline-tests)
    offline_test_suite
    ;;
  *)
    echo "Usage: $0 [all|syntax|architecture|flake8|deterministic|offline-tests]" >&2
    exit 2
    ;;
esac
