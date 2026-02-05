#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

NODE_BIN="${NODE_BIN:-node}"

echo "== wasm smoke =="
"$NODE_BIN" doc/wasm/js/all-smoke.mjs

echo "== web-ui node tests =="
npm --prefix web-ui run test:sandbox
