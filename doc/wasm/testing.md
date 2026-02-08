# WASM Testing

Project-wide test mode split is in `doc/testing.md`. This file keeps the
WASM-specific commands in one place.

## Sandbox-Safe

- `scripts/tests/run-sandbox-tests.sh`
- `node doc/wasm/js/all-smoke.mjs`
- `npm --prefix web-ui run test:sandbox`
- `node doc/wasm/js/wasm-ui-persist-smoke.mjs`
- `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs`
- `node doc/wasm/js/start-lisp-noninteractive-smoke.mjs --strict-start-lisp-noninteractive`
- Target persistence default lane:
  `CCL_PERSIST_BACKEND=memory-snapshot CCL_PERSIST_SNAPSHOT_FILE=.tmp/persist-smoke.snapshot.json node doc/wasm/js/wasm-ui-persist-smoke.mjs`

## Additional Targeted Smoke (Sandbox-Safe)

- `node doc/wasm/js/interrupt-smoke.mjs`

## External / Host-Only

- `node doc/wasm/js/lmdb-smoke.mjs`
- `CCL_ENABLE_LMDB_TESTS=1 node --test doc/wasm/js/persist-service.test.mjs`
- `scripts/wasm/idb-smoke-server-control.sh start`
- Open `http://127.0.0.1:5173/doc/wasm/js/idb-smoke.html`
- `scripts/wasm/idb-smoke-server-control.sh stop`
- `scripts/tests/run-external-tests.sh` starts IDB smoke server only with
  `RUN_IDB_SMOKE_SERVER=1`.

## Permission-Stable Workflow

- `make -f scripts/wasm/persist-host.mk persist-sandbox`
- `make -f scripts/wasm/persist-host.mk persist-host-lmdb`
- `make -f scripts/wasm/persist-host.mk persist-idb-up`
- `make -f scripts/wasm/persist-host.mk persist-idb-down`
- `make -f scripts/wasm/persist-host.mk persist-host-browser`

## Policy

- `doc/testing.md` is the source of truth for the sandbox/external split.
- `doc/wasm/persistence-dev-environment.md` defines the permission-stable
  persistence workflow used for unattended execution.
- Default unattended persistence architecture is memory-first snapshot backend;
  LMDB/IndexedDB remain integration lanes.
- Known status: `node doc/wasm/js/all-smoke.mjs` is green.
