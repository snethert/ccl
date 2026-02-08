# WASM Testing

Project-wide test mode split is in `doc/testing.md`. This file keeps the
WASM-specific commands in one place.

## Sandbox-Safe

- `scripts/tests/run-sandbox-tests.sh`
- `node doc/wasm/js/all-smoke.mjs`
- `npm --prefix web-ui run test:sandbox`
- `node doc/wasm/js/wasm-ui-persist-smoke.mjs` (runtime path; currently failing on root image const-pool install, entry 320)
- `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs`
- `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive` (blocker repro: timeout)

## Additional Targeted Smoke (Sandbox-Safe)

- `node doc/wasm/js/interrupt-smoke.mjs`

## External / Host-Only

- `node doc/wasm/js/lmdb-smoke.mjs`
- `CCL_ENABLE_LMDB_TESTS=1 node --test doc/wasm/js/persist-service.test.mjs`
- `node scripts/wasm/idb-smoke-server.mjs`
- Open `http://127.0.0.1:5173/doc/wasm/js/idb-smoke.html`

## Policy

- `doc/testing.md` is the source of truth for the sandbox/external split.
- Known status: `node doc/wasm/js/all-smoke.mjs` is green.
