# RPL-03 Step 3 Assertion Report (2026-02-09)

Execution basis:

- Command set: `IPCV-01`..`IPCV-12` from `doc/wasm/tickets/RPL-03-shared-memory-ipc-core.md`
- Output matrix: `ipcv-results.tsv`
- Terminal summary: `ipc_conformance_summary_v1.json`

Observed results:

- All lanes exited `0`.
- No lane emitted any required IPC schema markers:
  - `ipc_protocol_ready_v1`
  - `ipc_channel_event_v1`
  - `ipc_channel_summary_v1`
  - `ipc_conformance_summary_v1` (runtime-emitted)
- Deterministic fail-injection lanes (`IPCV-05`..`IPCV-12`) did not emit runtime `RPL03-E*` failure codes.

Assertion outcome:

- Baseline pass set (`IPCV-01`..`IPCV-04`): failed (required artifact emission absent).
- Deterministic fail set (`IPCV-05`..`IPCV-12`): failed (expected failure-code/transition assertions absent).
- `X-03` closure readiness: `false`.
