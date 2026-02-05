#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

NODE_BIN="${NODE_BIN:-node}"

echo "== lmdb smoke =="
"$NODE_BIN" doc/wasm/js/lmdb-smoke.mjs

echo "== wasm persistence (lmdb enabled) =="
CCL_ENABLE_LMDB_TESTS=1 "$NODE_BIN" --test doc/wasm/js/persist-service.test.mjs

echo "== web-ui browser tests =="
WEB_UI_ENABLE_BROWSER_TESTS=1 npm --prefix web-ui run test:browser

echo "== indexeddb browser smoke =="
echo "Run: node scripts/wasm/idb-smoke-server.mjs"
echo "Open: http://127.0.0.1:5173/doc/wasm/js/idb-smoke.html"
