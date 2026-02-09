# RPL-03 Step 3 Assertion Report (rerun 2026-02-09)

Execution basis:

- Command set: `IPCV-01`..`IPCV-12` from `doc/wasm/tickets/RPL-03-shared-memory-ipc-core.md`
- Output matrix: `ipcv-results.tsv`
- Terminal summary: `ipc_conformance_summary_v1.json`

Observed lane results:

- IPCV-01: exit=0, summary_status=pass, summary_code=null, artifacts=1/8/4/1, assertion_pass=true
- IPCV-02: exit=0, summary_status=pass, summary_code=null, artifacts=1/8/4/1, assertion_pass=true
- IPCV-03: exit=0, summary_status=pass, summary_code=null, artifacts=1/8/4/1, assertion_pass=true
- IPCV-04: exit=0, summary_status=pass, summary_code=null, artifacts=1/12/6/1, assertion_pass=true
- IPCV-05: exit=1, summary_status=fail, summary_code=RPL03-E001, artifacts=1/8/4/1, assertion_pass=true
- IPCV-06: exit=1, summary_status=fail, summary_code=RPL03-E002, artifacts=1/8/4/1, assertion_pass=true
- IPCV-07: exit=1, summary_status=fail, summary_code=RPL03-E003, artifacts=1/8/4/1, assertion_pass=true
- IPCV-08: exit=1, summary_status=fail, summary_code=RPL03-E004, artifacts=1/8/4/1, assertion_pass=true
- IPCV-09: exit=1, summary_status=fail, summary_code=RPL03-E005, artifacts=1/12/6/1, assertion_pass=true
- IPCV-10: exit=1, summary_status=fail, summary_code=RPL03-E006, artifacts=1/8/4/1, assertion_pass=true
- IPCV-11: exit=1, summary_status=fail, summary_code=RPL03-E008, artifacts=1/12/6/1, assertion_pass=true
- IPCV-12: exit=1, summary_status=fail, summary_code=RPL03-E010, artifacts=1/8/4/1, assertion_pass=true

Assertion outcome:

- Baseline pass set (`IPCV-01`..`IPCV-04`): pass.
- Deterministic fail set (`IPCV-05`..`IPCV-12`): pass (expected failure codes and transitions observed).
- `allow_hotpath_fallback=false`: preserved across emitted artifacts.
- `X-03` closure readiness: `true`.

Gap closure status:

- IPCGAP-01: closed (baseline artifact emission present).
- IPCGAP-02: closed (deterministic fail-lane behavior matches expected `RPL03-E*`).
- IPCGAP-03: closed (runtime-emitted `ipc_conformance_summary_v1` present in every lane log).
- IPCGAP-04: closed (fail-lane channel events include expected `WLCT-*` transition IDs).
