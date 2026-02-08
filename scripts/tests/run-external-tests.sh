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
RUN_IDB_SMOKE_SERVER="${RUN_IDB_SMOKE_SERVER:-0}"
OPEN_IDB_SMOKE_BROWSER="${OPEN_IDB_SMOKE_BROWSER:-0}"

if [[ "${RUN_IDB_SMOKE_SERVER}" != "1" ]]; then
  echo "skipped (set RUN_IDB_SMOKE_SERVER=1 to start idb smoke server)"
  exit 0
fi

PORT="${PORT}" NODE_BIN="${NODE_BIN}" scripts/wasm/idb-smoke-server-control.sh restart
URL="$(PORT="${PORT}" scripts/wasm/idb-smoke-server-control.sh url)"
echo "idb-smoke url: ${URL}"
echo "stop server with: scripts/wasm/idb-smoke-server-control.sh stop"

if [[ "${OPEN_IDB_SMOKE_BROWSER}" == "1" ]]; then
  if command -v open >/dev/null 2>&1; then
    open "${URL}"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "${URL}"
  else
    echo "could not auto-open browser; open manually: ${URL}"
  fi
fi
