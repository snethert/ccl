# RPL-05 Step 3 Gap Register (run-v2)

- R5GAP-01: closed. Required storage telemetry schemas emitted across run-v2 lane logs.
- R5GAP-02: closed. Runtime lanes now report replacement profile backend `storage-v2-opfs` with profile-guard `status=pass`.
- R5GAP-03: closed. Fail-injection controls emit canonical `RPL05-E*` first-failure mappings for `R5V-07`..`R5V-14`.
- R5GAP-04: closed. Forced fallback path emits canonical `RPL05-E007` without silent fallback behavior.
- R5GAP-05: closed. Terminal summary now includes deterministic `results_digest`, full pass/fail mapping, and `x05_step2_ready=true`.
