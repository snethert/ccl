# RPL-05 Step 3 Gap Register (run-v1)

- R5GAP-01: Storage telemetry schemas (`storage_v2_local_tx_event_v1`, `storage_v2_local_tx_summary_v1`, `storage_v2_ref_state_event_v1`, `storage_v2_lease_state_event_v1`, `storage_v2_local_recovery_report_v1`, `storage_v2_profile_guard_report_v1`) were not emitted in lane logs.
- R5GAP-02: Runtime lane still reported `persistence backend: memory-snapshot` under all validations instead of `storage-v2-opfs` profile guard pass posture.
- R5GAP-03: `CCL_STORAGE_V2_TEST_INJECT_FAILURE` controls did not produce canonical `RPL05-E*` first-failure outcomes in emitted summaries.
- R5GAP-04: `CCL_STORAGE_V2_TEST_FORCE_FALLBACK=1` did not surface `RPL05-E007` fail-path artifacts for no-fallback policy validation.
- R5GAP-05: Terminal `storage_v2_local_step2_summary_v1` required fields (`results_digest`, pass/fail lane mapping from emitted storage schemas) remain incomplete without native storage schema outputs.
