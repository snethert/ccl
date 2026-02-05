# Project Test Modes

This document separates sandbox-safe tests from host-only tests. The goal is to
keep everything runnable in the sandbox by default, and explicitly gate anything
that requires native services, browsers, or privileged OS access.

## Sandbox-Safe (Codex)

- Run all sandbox-safe tests: `scripts/tests/run-sandbox-tests.sh`
- WASM JS smoke tests: `node doc/wasm/js/all-smoke.mjs`
- Web UI node tests (no browser): `npm --prefix web-ui run test:sandbox`

## External / Host-Only

- Run all host-only tests: `scripts/tests/run-external-tests.sh`
- LMDB smoke: `node doc/wasm/js/lmdb-smoke.mjs`
- WASM persistence tests: `CCL_ENABLE_LMDB_TESTS=1 node --test doc/wasm/js/persist-service.test.mjs`
- IndexedDB browser smoke server: `node scripts/wasm/idb-smoke-server.mjs`
- IndexedDB browser smoke page: open `http://127.0.0.1:5173/doc/wasm/js/idb-smoke.html`
- Web UI headless browser tests: `WEB_UI_ENABLE_BROWSER_TESTS=1 npm --prefix web-ui run test:browser`

## Policy

- New tests must be labeled sandbox-safe or external in this file.
- External tests must be gated behind an environment variable or isolated in a
  dedicated script.
- Keep `doc/wasm/testing.md` as the WASM-specific pointer to this policy.
