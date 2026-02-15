# WASM Persistence Dev Environment

This runbook defines the persistence execution model used during MVP completion.

## Decision (authoritative)

Default unattended persistence must not depend on host-only privileges.

Operational model:

- Bootstrap persistence from a snapshot file.
- Load that snapshot into an in-memory IFB-like KV/chunk store.
- Execute all persistence operations in memory.
- Rewrite the snapshot file on exit only when state is dirty.
- Keep LMDB/IndexedDB as explicit integration lanes.

This is tracked as RZ0.6 in `web-ide/phase-8/implementation-plan.md`.

## Why this model

Host-only requirements (LMDB env open, localhost bind, browser launch) cause
permission-mode thrash for unattended development. Memory-first snapshot mode
keeps daily dev/test deterministic in sandbox-oriented environments.

## Lanes

### 1) Default unattended lane (target default)

- Backend: `memory-snapshot`
- Inputs:
  - `CCL_PERSIST_BACKEND=memory-snapshot`
  - `CCL_PERSIST_SNAPSHOT_FILE=<path>`

Expected behavior:

- Snapshot loaded once at process start.
- Writes mutate in-memory state only.
- Exit flush rewrites snapshot atomically only if dirty.

### 2) Integration lane (host-only)

- LMDB backend validation.
- IndexedDB/browser validation.

These remain required for backend compatibility, but are not the default
unattended execution path.

## Command surface

All lane commands are exposed through:

- `make -f scripts/wasm/persist-host.mk <target>`

Targets:

- `persist-sandbox`
  - Sandbox-safe persistence unit coverage (LMDB test skipped).
- `persist-host-lmdb`
  - LMDB smoke + LMDB-enabled persistence unit test.
- `persist-host-browser`
  - Browser tests requiring host browser permissions.
- `persist-idb-up`
  - Start IndexedDB smoke HTTP server.
- `persist-idb-status`
  - Check IndexedDB smoke server status.
- `persist-idb-url`
  - Print IndexedDB smoke URL.
- `persist-idb-logs`
  - Show IndexedDB smoke server logs.
- `persist-idb-down`
  - Stop IndexedDB smoke HTTP server.

## IndexedDB smoke server lifecycle

Lifecycle script:

- `scripts/wasm/idb-smoke-server-control.sh`

Defaults:

- URL: `http://127.0.0.1:5173/scripts/wasm/tests/idb-smoke.html`
- PID file: `/tmp/ccl-idb-smoke-server.pid`
- Log file: `/tmp/ccl-idb-smoke-server.log`

Overrides:

- `PORT`
- `NODE_BIN`
- `PID_FILE`
- `LOG_FILE`

## Recommended unattended sequence (current)

1. `make -f scripts/wasm/persist-host.mk persist-sandbox`
2. `make -f scripts/wasm/persist-host.mk persist-host-lmdb`
3. `make -f scripts/wasm/persist-host.mk persist-idb-up` (only for IDB integration checks)
4. Open `$(make -s -f scripts/wasm/persist-host.mk persist-idb-url)` if running the IDB smoke.
5. `make -f scripts/wasm/persist-host.mk persist-idb-down`

Default persistence smoke lane:

```bash
CCL_PERSIST_BACKEND=memory-snapshot CCL_PERSIST_SNAPSHOT_FILE=.tmp/persist-smoke.snapshot.json node scripts/wasm/tests/wasm-ui-persist-smoke.mjs
```

## Notes

- Keep default-lane failures separate from integration-lane failures.
- Do not block default unattended progress on host-only backend issues.
