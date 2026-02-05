#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

NODE_BIN="${NODE_BIN:-node}"

echo "== lmdb smoke =="
"$NODE_BIN" doc/wasm/js/lmdb-smoke.mjs

echo "== wasm persistence =="
CCL_ENABLE_LMDB_TESTS=1 "$NODE_BIN" --test doc/wasm/js/persist-service.test.mjs

echo "== web-ui browser tests =="
WEB_UI_ENABLE_BROWSER_TESTS=1 npm --prefix web-ui run test:browser

echo "== indexeddb browser smoke =="
PORT="${PORT:-5173}"
node scripts/wasm/idb-smoke-server.mjs &
SERVER_PID=$!
trap 'kill "$SERVER_PID" >/dev/null 2>&1 || true' EXIT

URL="http://127.0.0.1:${PORT}/doc/wasm/js/idb-smoke.html"
sleep 0.2
if command -v open >/dev/null 2>&1; then
  open "$URL"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL"
else
  echo "Open: $URL"
fi

echo "idb-smoke: press Ctrl-C to stop the server"
wait "$SERVER_PID"
