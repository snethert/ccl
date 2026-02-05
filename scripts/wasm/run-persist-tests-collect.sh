#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

NODE_BIN="${NODE_BIN:-node}"
LOG_PATH="${LOG_PATH:-doc/wasm/js/persist-test-report.txt}"

# Run and capture all output.
{
  echo "persist-test-report"
  echo "timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "root: $ROOT_DIR"
  echo "node: $($NODE_BIN -v)"
  echo ""
  echo "== lmdb-smoke =="
  "$NODE_BIN" doc/wasm/js/lmdb-smoke.mjs
  echo "lmdb-smoke-exit: $?"
  echo ""
  echo "== persist-unit-tests =="
  CCL_ENABLE_LMDB_TESTS=1 "$NODE_BIN" --test doc/wasm/js/persist-service.test.mjs
  echo "persist-tests-exit: $?"
} 2>&1 | tee "$LOG_PATH"
