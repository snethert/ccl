# Project Test Modes

This document separates sandbox-safe tests from host-only tests. The goal is to
keep everything runnable in the sandbox by default, and explicitly gate anything
that requires native services, browsers, or privileged OS access.

## Sandbox-Safe (Codex)

- Run all sandbox-safe tests: `scripts/tests/run-sandbox-tests.sh`
- WASM JS smoke tests: `node doc/wasm/js/all-smoke.mjs`
- Web UI node tests (no browser): `npm --prefix web-ui run test:sandbox`
- WASM/UI persistence smoke: `node doc/wasm/js/wasm-ui-persist-smoke.mjs`
- Non-interactive start-lisp smoke: `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs`
- Strict root non-interactive start-lisp check: `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive`
- Optional targeted WASM interrupt smoke: `node doc/wasm/js/interrupt-smoke.mjs`
- Target persistence default lane (RZ0.6):  
  `CCL_PERSIST_BACKEND=memory-snapshot CCL_PERSIST_SNAPSHOT_FILE=.tmp/persist-smoke.snapshot.json node doc/wasm/js/wasm-ui-persist-smoke.mjs`

## External / Host-Only

- Run all host-only tests: `scripts/tests/run-external-tests.sh`
- LMDB smoke: `node doc/wasm/js/lmdb-smoke.mjs`
- WASM persistence tests with LMDB enabled: `CCL_ENABLE_LMDB_TESTS=1 node --test doc/wasm/js/persist-service.test.mjs`
- Managed IndexedDB smoke server:
  - Start: `scripts/wasm/idb-smoke-server-control.sh start`
  - Status: `scripts/wasm/idb-smoke-server-control.sh status`
  - Stop: `scripts/wasm/idb-smoke-server-control.sh stop`
- `scripts/tests/run-external-tests.sh` starts the IDB smoke server only when
  `RUN_IDB_SMOKE_SERVER=1` is set.
- IndexedDB browser smoke page: `http://127.0.0.1:5173/doc/wasm/js/idb-smoke.html`
- Web UI headless browser tests: `WEB_UI_ENABLE_BROWSER_TESTS=1 npm --prefix web-ui run test:browser`

## Permission-Stable Workflow

For assistant-driven development, use the host make targets so sandbox-safe and
host-only operations stay clearly separated:

- Sandbox lane: `make -f scripts/wasm/persist-host.mk persist-sandbox`
- Host LMDB lane: `make -f scripts/wasm/persist-host.mk persist-host-lmdb`
- Host IDB server up/down:
  - `make -f scripts/wasm/persist-host.mk persist-idb-up`
  - `make -f scripts/wasm/persist-host.mk persist-idb-down`
- Host browser tests: `make -f scripts/wasm/persist-host.mk persist-host-browser`

Default architecture direction: memory-first snapshot persistence for unattended
execution, with LMDB/IndexedDB retained as integration lanes.

## Policy

- New tests must be labeled sandbox-safe or external in this file.
- External tests must be gated behind an environment variable or isolated in a
  dedicated script.
- Keep `doc/wasm/testing.md` as the WASM-specific pointer to this policy.
- Use `doc/wasm/persistence-dev-environment.md` for the host/sandbox persistence
  workflow and server lifecycle commands.
- Known status: `node doc/wasm/js/all-smoke.mjs` is green.
