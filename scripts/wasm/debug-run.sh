#!/usr/bin/env bash
# Launch a WASM test with Chrome DevTools debugging enabled.
#
# Usage:
#   scripts/wasm/debug-run.sh scripts/wasm/tests/smoke-test.mjs
#   scripts/wasm/debug-run.sh scripts/wasm/lib/make-real-image.mjs
#
# Then open chrome://inspect in Chrome and click "inspect" on the Node target.
# DWARF debug info is embedded in wasmcl.wasm — Chrome DevTools will show C source.
# See doc/wasm/debugging.md for detailed debugging workflows.

source "$(dirname "$0")/env.sh"
exec node --inspect-brk "${@}"
