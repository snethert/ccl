#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
FIXTURES_DIR="$ROOT_DIR/scripts/wasm/tests/startup-symbol-scope-fixtures"

"${CCL_BIN:-ccl}" --no-init --batch \
  -l "$ROOT_DIR/scripts/wasm/collect-startup-symbol-scope.lisp" \
  -- \
  --run-fixture-tests \
  --fixtures-dir "$FIXTURES_DIR"
