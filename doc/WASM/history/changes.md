# Change history

## 2026-09-11 — logical debugger-frame prerequisite

Authorized by the user's “What is next? Proceed.” Codex added the isolated S0-LL23-b fixture before D3 ABI selection. It links the reviewed runtime objects unchanged and publishes explicit frames, independent C readers, lexical/root maps and build-bound source locations. Cases exercise moving roots, complete results, lower-policy unavailable values, nested debugging, EH restoration, escaped captured cells and generation/version lifetimes. Dedicated controls reject stale slots, invalid metadata, fabricated values, collapsed lexical identities, broken restoration and bounds violations.

The initial formal r1 run passed ten cases and eleven controls. A subsequent capacity review found that its 2,048-byte inspection packet could not represent all eight advertised frames with six values (2,056 bytes). The next revision enlarges the packet to 4,096 bytes and exercises the full eight-frame capacity across moving GC. The narrower original r1 remains retained, without relabeling it as evidence of maximum-capacity coverage.

The new runner changes the inventory identity. Fresh probes and runtime prerequisites use that identity; native r3 is re-bound only after verifying its original artifacts and unchanged native contract. Original execution timestamps and Claude's prior review scope are retained. The new proof is NOT_REVIEWED and NOT_ACCEPTED; no shared compiler or upstream kernel source is modified. C/C4/B correctness and measurements, qualified census work and remaining Stage 0 obligations are still open.

## 2026-09-11 — second Claude audit of r10, probes r5 and native Gate 0

Authorized by the user's request to verify the latest tests and mark the documents.

- Claude Fable 5.1 re-executed all three Wasm runners and the native baseline runner from the pinned inputs in its own session. Wasm modules are byte-identical to r10 and r5; native results match r3 exactly, including all 164 FASL hashes. The 2026-head diagnostic reproduced its three failures.
- Recorded reviewer dispositions in `stage0/claude-review.md`, `evidence/index.json` (external_review on r10, r5 and native r3) and `STATUS.md`. `stage0/inventory.json` is unchanged so every CURRENT envelope keeps its inventory binding. No slice is accepted; the combined gate remains BLOCKED.
- Provenance: commit 85adc038 was authored by Codex under the operator's git identity. This entry and the commit adding it record that fact.

## 2026-09-11 — macOS reference, Claude audit fixes and evidence retention

Authorized by the user's macOS platform decision and supplied Claude reviews.

- Selected macOS as the sole active Wasm project reference platform. Gate 0 uses U1's x86-64 Darwin target; S0-LL08-c repeats it on a second Mac. Removed alternate-host provisioning and tracing requirements. Historical facts remain in the history ledger; upstream native code remains unchanged.
- Recorded Claude's external audit of Codex's r8 work. The audit found a real idle RUNNING Worker on exceptional return. Original r9 reproduces the collector failure; r10 parks on exception, admits retirement, and collects in the formerly uncovered window. Its omitted-park mutant must fail with the specific state/owner snapshot.
- Added the host-outcome-after-final-wake control and accurate waiter-witness descriptions. r10 passes 22 positive cases, 14 rejected controls and 1,000 seeds, plus both boundary prerequisites. Ordinary scalar result reads occur before parking. No post-audit change is labeled externally accepted.
- Amended D5 to protocol v1.1 and coordinated outline 0.14 / acceptance 1.4 / decisions 1.5. Fixed the heading, malformed floating-point sentence and census typo. Generated reading copies and verification use the current hashes.
- Pinned both clang and LLD to 21.1.8 with explicit Homebrew paths and executable hashes. Cleared selection environment variables for the retained r10 execution. Runners distinguish the U1 baseline from the checkout commit so a documentation/fixture commit does not invalidate reproduction.
- Moved superseded packs to the external local evidence store without changing their bytes. Keep the current fixture packs and original failures r3/r6/r9 in-tree. Probes r4 and boundary r2 retain their old inventory hashes with explicit superseded status; fresh r5 probes and r10 prerequisites use the current inventory.
- Added three archive-currency checker controls: a valid current pack, a stale index mislabeled current, and an old result envelope relabeled with the current inventory hash. The checker suite now passes 29 controls.
- Added project standing rules that reflect the user's supplied instructions. Codex is limited to isolated fixtures, tooling and documentation; shared compiler and upstream kernel source remain protected.

The native baseline uses the last upstream ccl-tests commit preceding the v1.13 release, `561ab1be82fefd53a61089eaad4357023e1fa961`. The initially selected 2026 test head includes post-release regressions and remains a separate diagnostic with its failures retained. Driver errors also ran tests inside LOAD dynamic bindings and selected verbose mode, which changes two warning-output assertions. The corrected driver invokes tests after LOAD returns with upstream’s default nonverbose mode. Neither failed record is rewritten or described as passing. Final native r3 performs two clean macOS builds and passes 21,843/21,843 eligible tests in each (75 upstream-disabled tests recorded). All 164 FASLs are raw-identical. The corrected, fresh 2026-head diagnostic passes 21,850 and retains three post-release failures: bitvector reader, constant-index complex-single-float access, and multiple values in read-time evaluation. These do not become waived or passing tests. The combined native/Wasm Stage 0 gate remains BLOCKED for missing work and reviews.

## 2026-09-11 — integrated moving-GC, concurrency and I/O proof

Authorized by the user's request to complete the next hand-built runtime work.

- Added `tests/wasm/stage0/integrated-runtime/` and bound S0-LL20-a/b/c to its runner. It links the existing freestanding C fixture with a bounded cons-only copying collector and D5 protocol, and runs actual emitted Wasm frames and Node Workers on macOS.
- Implemented live C/emitted root relocation, cyclic/shared graphs, from-space poisoning, nested binding restoration, complete VSP values, admitted code installation, competing collectors, wrapping generation admission, final membership rescan, child handoff roots, allocation rechecking, interrupted I/O, nested descriptors and retirement/reclamation.
- Recorded 21 deterministic positive cases, 12 rejection controls and 1,000 seeded schedules in current run r8. Safepoint, whole-rendezvous and schedule bounds are enforced. The runner also freshly executes both earlier C-boundary slices. No native compiler source changed.
- Preserved the original failing r3 regression: the final wake write of an old host completion could modify a descriptor after reuse. Schema v2 coupled generation and wake in an aligned atomic 64-bit pair; conditional final publication now rejects the old generation. Its bypass mutant must fail.
- Preserved the original failing r6 regression: an interrupt directed at the parent request did not wake a nested debugger request. Schema v3 added the current active-request pointer, distinct from outstanding request ownership, and restored it on normal and exceptional returns. The wrong-descriptor mutant must fail.
- Aligned the final emitted ordinary result with the existing `(value0, nvalues)` fixture contract, including fixture NIL for zero values. This does not select D3 argument placement.
- Retained all formal runs and development compilation diagnostics as compressed evidence packs. Earlier passing packs remain labeled with their narrower coverage; they are not substituted for the final run. Recorded implementer review is separate from pending Stage 0 acceptance review.

## 2026-09-11 — executable C/Wasm boundary slices

- Added `tests/wasm/stage0/runtime-boundary/` for S0-LL13-c and S0-LL19-b, with freestanding C compilation, strict linking, final-binary import/ownership checks, actual overlapping C activations, per-Worker TLS/stacks and emitted `try_table` boundary restoration.
- Retained two execution runs. Run r1 covered seven negative controls; r2 added actual link-signature mismatch and omitted-transfer controls, and bound the two runners in the current inventory. Run r2 passes both slices, twelve normal/EH cases and nine negative controls. Neither run is Stage 0 acceptance.
- Specified the fixture's caller-owned VSP result region and limited restart choices explicitly. Moving GC, the D3 candidates, full CCL conditions/restarts and the combined LL20 harness remain outstanding.
- Replaced per-obligation execution-status prose with references to the current ledger so the acceptance contract does not become a second stale status report. No obligation or acceptance threshold changed.
- Clarified that Linux is the recorded native regression host, not a Wasm dependency. Docker environment preparation was set aside after the user questioned its relevance; it supplies no native qualification. Existing native implementation source remains unchanged.

## 2026-09-11 — outline 0.13, acceptance 1.3, decisions 1.4

Authorized by the user's request to apply the document assessment recommendations.

- Selected the existing clean v1.13 checkout as implementation baseline. Classified `4ca4df4` inventories, Gate 0 and ARM64 reports as historical; no historical result was rescinded or promoted to this revision.
- Clarified R6: protect existing target-specific source; compare unchanged-input target output; review intended changes to shared compiler artifacts explicitly. Executable changes cannot be normalized away.
- Added an evidence index with explicit missing retention information, a current status ledger, Stage 0 subgates and quantitative benchmark/liveness policies.
- Added initial data-layout and logical debugger-frame contracts, a census schema/completeness rule, expanded test IDs and a generated obligation index.
- Replaced the stale workflow with a maintained diagram showing independent architecture work and external native load tracing.
- Added document generation/consistency tools, a fail-closed result checker and limited executable Wasm probes. These do not constitute Stage 0 acceptance.
- Preserved the original document files and image with full SHA-256 identities. D1/D2/D4/D5 selections, D3's candidate sequence, R1–R7, R6a and all 24 regression obligations remain in force.

Baseline scope decision: `S0-LL08-c@decisions-1.3` requested a second-host reproduction of the H1/E5 ARM64 result. The selected U1 baseline lacks that complete backend. `S0-LL08-c@decisions-1.4` instead requires second-host reproducibility of the pinned U1 x86-64 Linux baseline. The old unexecuted test specification is preserved in the original document; it does not become a passing or not-applicable result. Historical H1/E5 claims remain unchanged, and their archive/reproduction work stays on the evidence ledger. The withdrawn applicability claim is that H1's ARM64 recipe qualifies the v1.13 implementation. R6's other supported-target checks remain required. This is part of the user-authorized baseline alignment, not a performance-driven waiver.
