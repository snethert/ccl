# RPL-04 Step 3 Assertion Report (rerun 2026-02-10)

Execution basis:

- Command set: `R4V-01`..`R4V-14` from `doc/wasm/tickets/RPL-04-runtime-ui-bridge-shared-path.md`
- Output matrix: `r4v-results.tsv`
- Terminal summary: `runtime_ui_bridge_step2_summary_v1.json`

Observed lane results:

- R4V-01: lane=R4L-01, exit=0, summary_status=pass, first_failure_code=none, artifacts=1/1/1/0/1, assertion_pass=true
- R4V-02: lane=R4L-01, exit=0, summary_status=pass, first_failure_code=none, artifacts=1/1/1/0/1, assertion_pass=true
- R4V-03: lane=R4L-01, exit=0, summary_status=pass, first_failure_code=none, artifacts=1/1/1/0/1, assertion_pass=true
- R4V-04: lane=R4L-02, exit=0, summary_status=pass, first_failure_code=none, artifacts=3/3/3/0/3, assertion_pass=true
- R4V-05: lane=R4L-03, exit=0, summary_status=pass, first_failure_code=none, artifacts=1/1/1/0/1, assertion_pass=true
- R4V-06: lane=R4L-04, exit=0, summary_status=pass, first_failure_code=none, artifacts=3/3/3/0/3, assertion_pass=true
- R4V-07: lane=R4L-05, exit=1, summary_status=fail, first_failure_code=RPL03-E008, artifacts=1/1/1/0/1, assertion_pass=true
- R4V-08: lane=R4L-05, exit=1, summary_status=fail, first_failure_code=RPL03-E010, artifacts=1/1/1/0/1, assertion_pass=true
- R4V-09: lane=R4L-05, exit=1, summary_status=fail, first_failure_code=RPL03-E002, artifacts=1/1/1/0/1, assertion_pass=true
- R4V-10: lane=R4L-05, exit=1, summary_status=fail, first_failure_code=RPL03-E003, artifacts=1/1/1/0/1, assertion_pass=true
- R4V-11: lane=R4L-05, exit=1, summary_status=fail, first_failure_code=RPL03-E007, artifacts=1/1/1/0/1, assertion_pass=true
- R4V-12: lane=R4L-06, exit=1, summary_status=fail, first_failure_code=RPL03-E008, artifacts=1/1/1/1/1, assertion_pass=true
- R4V-13: lane=R4L-04, exit=0, summary_status=pass, first_failure_code=none, artifacts=3/3/3/0/3, assertion_pass=true
- R4V-14: lane=R4L-04, exit=0, summary_status=pass, first_failure_code=none, artifacts=3/3/3/0/3, assertion_pass=true

Assertion outcome:

- Baseline pass set (`R4V-01`..`R4V-06`): pass.
- Deterministic fail set (`R4V-07`..`R4V-12`): pass (expected failure codes and rollback behavior observed).
- Compatibility assertion set (`R4V-13`, `R4V-14`): pass.
- `allow_hotpath_fallback=false`: preserved across emitted artifacts.
- `X-04` closure readiness: `true`.

Gap closure status:

- R4GAP-01: closed (wrapper controls `CCL_UI_BRIDGE_TEST_*` now drive deterministic lane behavior).
- R4GAP-02: closed (bridge-specific telemetry schemas `runtime_ui_bridge_route_event_v1`, `runtime_ui_bridge_backpressure_event_v1`, `runtime_ui_bridge_lane_summary_v1`, `runtime_ui_bridge_rollback_record_v1` emitted in rerun logs).
- R4GAP-03: closed (native terminal `runtime_ui_bridge_step2_summary_v1` emitted in lane logs and committed as aggregate summary).
- R4GAP-04: closed (`R4I-01`..`R4I-06` compatibility verdicts are explicit and non-pending).

