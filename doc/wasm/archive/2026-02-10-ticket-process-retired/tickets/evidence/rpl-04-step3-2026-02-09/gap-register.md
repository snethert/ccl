# RPL-04 Step 3 Gap Register (2026-02-09)

- `R4GAP-01`: Bridge-specific wrapper controls (`CCL_UI_BRIDGE_TEST_*`) are not currently wired; only `CCL_IPC_TEST_*` controls are effective.
- `R4GAP-02`: Bridge-specific telemetry schemas (`runtime_ui_bridge_route_event_v1`, `runtime_ui_bridge_backpressure_event_v1`, `runtime_ui_bridge_lane_summary_v1`, `runtime_ui_bridge_rollback_record_v1`) are not yet emitted in lane logs.
- `R4GAP-03`: Terminal schema `runtime_ui_bridge_step2_summary_v1` is not emitted natively by lanes; only draft summary can be synthesized post-run.
- `R4GAP-04`: Compatibility verdict fields for `R4I-01`..`R4I-06` are not yet emitted automatically and remain `pending`.
