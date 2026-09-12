# D3 measurement implementation handoff

Status: preparation only; no timing or ABI recommendation. The eighteen C/C4/B correctness records are accepted under the [fourth-audit decision](project-acceptance.md). The reviewed r1 implementation and its 864 binaries remain unchanged. The [readiness report](../evidence/abi-measurement-readiness.json) binds this handoff to the accepted evidence and existing inventories/policy.

The first deliverable is an isolated measurement harness, not timings of the existing correctness runner. That runner includes JavaScript commands, immutable inspection replies, assertions and trace collection around individual calls. Its elapsed time would mix supervision with ABI cost. Use batched Wasm loops with observable complete results, keep required frame/root/stack publication and restoration in the timed path, and put host reporting outside each batch. Requalify the resulting emitted code against the accepted corpus before using it for comparisons. Lower-policy availability currently changes reporting only; charge its actual materialized storage until an independently checked implementation changes it.

The existing benchmark policy names S0-LL21-a as a correctness prerequisite. That separate record is still missing even though the accepted S0-LL21-b corpus exercises related late-Worker installation. Implement an explicitly identified S0-LL21-a case and its evidence producer; do not relabel old evidence or grant new acceptance from an adjacent test. The complete S0-ENGINE-a and S0-CONTRACTS-a records are also missing prerequisites for final S0-ABI-selection. These gaps do not prevent building and checking an exploratory harness, but they remain explicit before claiming selection evidence.

Use the existing 24 candidate/workload IDs and unchanged [benchmark policy](benchmarks.json). Each of the eight workloads below runs for C, C4 and B with identical bodies, inputs, observable outputs and root/cleanup obligations.

| Workload | Measurement implementation |
| --- | --- |
| Direct calls | Put caller and callee in the same module for a real direct instruction. Retain a separate cross-instance form; the r1 `direct` wrapper alone does not measure caller-to-callee same-module granularity. |
| Unknown indirect callees | Vary actual table targets with a retained seeded schedule; distinguish monomorphic and changing targets and inspect engine evidence for elimination/inlining. |
| Closures | Use distinct self/environment objects and consume their results; include arguments on each side of the candidate's parameter/overflow boundary. |
| Optional/rest/keyword binding | Retain defaults, supplied flags, rest allocation, keyword ordering and ordinary condition behavior; freeze the subcase mixture before selection trials. |
| APPLY | Spread proper lists through rooted storage. Keep improper/circular/capacity inputs in correctness checks rather than counting failure time as useful throughput. |
| Multiple values | Consume every value for zero, one and six results, including preservation across nested calls. |
| Cross-arity tail chains | Alternate growing/shrinking overflow with live binding/cleanup extent; retain bounded-stack/root checks outside the timing summary. |
| Allocation with forced collection | Hold live roots while varying allocation pressure; report allocation and collection work separately, with request-to-park and release-to-progress observations. |

For every configuration retain binary/metadata bytes, adapter/stub bytes and counts, table slots, root stores/reloads, explicit/C-stack reservations and high-water marks, shared versus per-Worker allocations, module compilation/installation and first-call latency. Reserved linear memory is not resident engine memory. A missing metric stays unavailable; do not infer it from the 1 MiB correctness fixture allocation.

Run exploratory packaging/startup sweeps under the [product-risk plan](product-risk-plan.md), then freeze the representative matrix and its digest before selection trials. Compare same-instance and cross-instance calls and state the eager/lazy boundary, weighted call distribution, Worker counts, engine version/tier and flags. Preserve all exploration records, including exhaustion or rejected configurations. Node observations characterize Node only; browser startup/cache evidence remains separate. Census-derived workload representativeness and product budgets remain open.

The policy already requires at least 30 independent paired trials, at least 1,000 ms warmup and 250 ms sample time per workload, seeded randomized order, 95% confidence intervals and 10,000 paired bootstrap resamples. Inner iterations do not count as independent trials. The geometric-mean ratio and simplicity order B/C/C4 apply only after the declared correctness, uncertainty, resource and product-evidence conditions are met. Report no selection if those conditions are unresolved. No thresholds or workload weights have been changed by this handoff.

Claude's nonblocking observations are carried into implementation work: a production loader needs a real slot-role registry with a corruption control; the r1 circular APPLY case currently reaches the 32-element capacity condition rather than detecting a cycle; and the measurement fixture should explicitly assert the single-scanner rule at legal inspection points before timing. Those follow-ups do not alter the accepted r1 bytes. Any changed implementation needs its own verification and independent review. H(G) remains optional future work.
