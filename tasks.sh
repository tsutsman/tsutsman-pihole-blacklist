#!/usr/bin/env bash
set -euo pipefail

cmd=${1:-help}

run_tests() {
  pytest -q
}

run_lint() {
  ruff check .
  bandit -r scripts -ll || true
}

run_format() {
  ruff format .
  black .
}

run_audit() {
  pip-audit --strict || true
}

run_generate() {
  python scripts/generate_lists.py --formats adguard ublock hosts
}

case "$cmd" in
  test) run_tests ;;
  lint) run_lint ;;
  fmt|format) run_format ;;
  audit) run_audit ;;
  gen|generate) run_generate ;;
  help|*)
    echo "Usage: $0 [test|lint|format|audit|generate]";
    ;;
esac


