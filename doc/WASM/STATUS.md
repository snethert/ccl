# Current status — 2026-09-11

Implementation baseline: upstream v1.13, `c994217adc56b3f8a564526cee4695893ac84d86`. Current document set: outline 0.17, acceptance 1.7, decisions 1.8. macOS is the sole reference host. Shared compiler and upstream kernel source remain unchanged.

| Work | State | Evidence scope / remaining work |
| --- | --- | --- |
| U1 native Gate 0 | ACCEPTED for same-host execution/repeatability | Two clean macOS x86-64 builds, 21,843 passing eligible tests per build, 75 upstream-disabled tests disclosed, 164 identical FASLs. Claude independently reproduced the results. Second-Mac reproduction remains open. [Native summary](evidence/native-baseline-summary.json). |
| Boundary S0-LL13-c / S0-LL19-b | ACCEPTED at retained bounds | Twelve cases and nine controls, real C stacks, TLS and exceptional restoration. |
| Integrated S0-LL20-a/b/c | ACCEPTED at retained bounds | Cons-only moving collector, admission, lifecycle and interruptible I/O; 22 cases, 14 controls, 1,000 seeded schedules. [Runtime scope](stage0/integrated-runtime.md). |
| Debugger frames S0-LL23-b | ACCEPTED at retained bounds | Eleven cases and eleven controls. Shared-cell relocation does not establish capture semantics; policy-1 unavailability is metadata only. [Frame scope](stage0/debug-frames.md). |
| Seven-record project acceptance | RECORDED | User-authorized [decision](stage0/project-acceptance.md) following Claude sign-off 52639e4e. Separate envelope preserves original bytes, timestamps, hashes and scopes. Original raw envelopes retain their earlier review flags. |
| C/C4/B dynamic-call corpus | Executed PASS; NOT ACCEPTED | 53 positive cases and 27 rejected controls per candidate; 159/81 total. Includes three 100,000-tail-transfer cases per candidate. Eighteen new inventory records await independent review. [Report and bounds](stage0/dynamic-call.md). |
| D3 selection / product risks | OPEN | No candidate selected or benchmarked. [Scale, startup and granularity](stage0/product-risk-plan.md) need coupled measurements and stated assumptions. Hand-built correctness does not measure production cost. |
| Qualified census / compiler | NOT RUN | Evaluated native instrumentation, closure evidence and executable pass 2 remain absent. Shared compiler work requires an authorized author under the standing rules. |
| Engine matrix / full object contracts | INCOMPLETE | Node/V8 hand-built execution does not qualify browsers, all profiles, full CCL object layouts or generated code. |
| Initial probes | Reviewed diagnostics only | Three PASS in r7; cannot discharge complete S0 IDs. Original inventory hash remains provenance. |
| Evidence repository | Retained separately | Immutable catalog, original failures and index snapshots; [pinned repository manifest](evidence/repository.json). |
| C/C4/B dynamic-call fixture review | Reviewed by Claude at 7187a89b; NOT ACCEPTED | [Fourth audit](stage0/claude-review.md): full source review, fresh 159/81 run, 864/864 byte-identical binaries, no defect; three nonblocking observations recorded. The eighteen records await project acceptance. |
| Stage 0 acceptance | BLOCKED | The combined gate has 42 reasons: 24 missing records and 18 new records awaiting review/acceptance. |

The new ABI fixture adds a separate C extension and new linked kernel. Existing boundary/runtime/frame sources remain unchanged. Fresh prerequisites execute before the ABI corpus; their re-execution does not extend the earlier acceptance to new ABI code. Original ABI development failures exposed duplicate result scanning and a stale frame result count. Both fixes are confined to the new fixture and have rejection controls.

Claude's sign-off includes the v2 evidence binding tooling and evidence repository. The new acceptance producer and ABI implementation are Codex-authored; their verification is not adversarial review. Version 2 bindings preserve unaffected accepted records when new tests or runners are added. See [verification](evidence/verification.json), [combined gate](evidence/current-stage0-gate-result.json), [history](history/changes.md) and [next work](stage0/plan.md).

H(G) is optional future work and blocks no scheduled stage. Historical H1 archives remain explicitly unavailable where not retained; their prior claims are not promoted to U1.
