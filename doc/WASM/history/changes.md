# Change history

## 2026-09-11 — fourth Claude audit: C/C4/B dynamic-call fixture reviewed

Authorized by the user's request to review the new fixture.

- Claude read the complete dynamic-call fixture and protocol, re-executed it at HEAD (159 positive, 81 rejected, prerequisites 12/9, 22/14/1,000, 11/11) and confirmed 864/864 modules and objects byte-identical to the retained r1 pack.
- Mechanism review covered frame publication, single-scanner result ownership across ordinary, nested, debugger, tail and nonlocal paths, tail transfer under fifty collections, lazy installation validation, and the Lisp-level condition paths. No defect found.
- Three nonblocking observations recorded: dispatch-time role validation is a test-path stand-in, circular APPLY reports the capacity condition, and the single-scanner invariant is not asserted at inspection points.
- Disposition recorded in `stage0/claude-review.md` and as `external_review` on DYNAMIC-CALL-r1. `inventory.json` unchanged; no record promoted to ACCEPTED.

## 2026-09-11 — scoped project acceptance and C/C4/B correctness

Following Claude's sign-off committed as 52639e4e, the user authorized proceeding. A separate acceptance envelope records exactly seven original native/runtime/frame records as ACCEPTED within their reviewed scopes. The original report, timestamps, test revisions, contract digests and artifacts are unchanged. Fourteen acceptance-producer controls verify identity, scope, failure rejection and preservation. Acceptance alone reduces the gate from 49 reasons to 42 missing records.

The isolated dynamic-call fixture implements C/C4/B through one corpus: 53 positive cases and 27 rejected controls per candidate, 159/81 total. It freshly executes boundary 12/9, integrated 22/14/1,000 seeds and frames 11/11. New ABI source and its new linked kernel remain NOT_REVIEWED/NOT_ACCEPTED. A separate rebuild reproduces all 35 new objects/modules byte-identically; all 49 prerequisite objects/modules match the previously reviewed r5 pack. No shared compiler, upstream kernel or earlier fixture source changed.

Original ABI development r1 exposed duplicate scanning of a result slot through both the TCR descriptor and a root record. Development r2 exposed a stale frame result count during nested output reuse. Both fixes change only the new fixture, retain original failed evidence and have rejection controls. Later control-development runs detected an old-code substitution via the new source-metadata oracle before the expected value check; the control now recognizes that precise rejection. Larger development evidence is retained in the separate evidence repository, with hashes in the source index.

Outline 0.17, acceptance 1.7 and decisions 1.8 remove the remaining mandatory specialized-entry language in D7, consistent with the user's prior H(G) retirement. Generic C/C4/B and runtime-adapter signature/role/stub checks remain mandatory. The protocol declares finite argument, result, stack, root, frame, reply, Worker and heap bounds. It does not select D3 or claim generated code, production scale or browser/startup qualification.

The current aggregate selects the seven accepted originals plus eighteen new unreviewed records. Its 42 reasons comprise 24 missing and eighteen unreviewed records. Original evidence and pre-change documents are retained. The new implementation needs independent review before project acceptance; measurements and the compiler/census track remain next.


## 2026-09-11 — third Claude audit: full verification and reviewer sign-off at 9c2ef44d

Authorized by the user's request to verify all tested functionality with evidence and sign off.

- Claude re-executed probes, boundary, integrated and frame fixtures at HEAD: 6/6 and 49/49 modules and objects byte-identical to retained r7 and r5; gate on the fresh envelope reproduces BLOCKED with 49 reasons. The retained combined gate result reproduces exactly.
- Native r3's v2 envelope verified: 375/375 execution artifacts identical to the original pack; no new native execution. Claude's own two-build reproduction matches all 164 FASL hashes.
- v2 evidence binding reviewed in full with its 42 controls; the fresh run's contract digest equals r5's across different inventory snapshots. Evidence repository catalog check passes on 6,767 files. No defect found in any reviewed component.
- Reviewer sign-off recorded per record in `stage0/claude-review.md` and as `external_review` on the current index entries. `inventory.json` unchanged. No record is promoted to ACCEPTED; that requires a project acceptance envelope.

## 2026-09-11 — H(G) retired from mandatory work; product risks and evidence repository

The user explicitly directed: “Ignore H(G) entirely except as a possible future enhancement. It should not stop progress.” Outline 0.15, acceptance 1.5 and decisions 1.6 now require only C/C4/B. Five H correctness variants and eight H benchmark rows are removed; all 38 acceptance IDs remain, with 24 required candidate/workload measurements. H has no Stage 0 dependency, generated-code deadline or Stage 1 gate. No required generic candidate has been omitted or marked passing.

Benchmark policy v2 preserves the generic comparison statistics and fixture progress limits, removes mandatory hybrid thresholds, and requires a stated granularity/installation basis. Old policy SHA-256: `fcbb9e7ab758a71914d8200f6fa4788b20dd1c48515e8f8be3e8d7fe8ea179c1`. New policy SHA-256: `a9e69df97867b7cc608ce6bd6ae5ea2118a5b53dc03eb4391c72f9e870a838a4`. The original document set, policy and inventory remain in the evidence repository. No ABI selection measurements had run, so no prior ABI measurement is being relabeled. Frame r4 and probes r7 freshly bind the new inventory; native r3 is explicitly re-bound after verifying unchanged artifacts and the same Gate 0 contract, without another native execution.

Claude's broader feedback is recorded in the product-risk plan. Scale and browser startup remain unmeasured; module granularity must accompany ABI comparisons. The plan distinguishes HTTP-byte caching, engine code caching, compilation, per-Worker instantiation and lazy first use, with primary documentation for the corrections. The native census and an authorized small compiler spike can progress alongside the architecture work.

The external evidence store is made a separate local Git repository with a portable SHA-256 catalog, original-pack mirrors and corruption controls. Original failed runs remain byte-identical. No remote or off-machine backup is claimed. The gate checker has 32 synthetic controls, including passing the complete generic set without H and blocking a missing generic candidate even when an H record is supplied. A mistaken initial synthetic-control expectation was preserved and corrected; it was not a runtime regression.

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


## 2026-09-11 — record the frame audit and scope evidence compatibility

Claude’s user-supplied audit of `ff900004` found no defect in debugger-frame r3. Its reproduction counts remain scoped to that pack: eleven cases and eleven rejected controls, boundary 12/9, integrated 22/14/1,000 seeds, 49 byte-identical modules/objects, 29 checker controls and 28 evidence identities. The index records that independent review without rewriting the original pre-review envelope. Low-policy availability remains a reporting-only proof. The permanent-root shared-cell case now explicitly disclaims capture/escape semantics; only its diagnostic label and documentation changed.

Outline 0.16, acceptance 1.6 and decisions 1.7 add version 2 evidence envelopes. Each result retains its exact original inventory and binds the test plus transitive prerequisite contracts and inventory version. Only review/status bookkeeping and the inventory’s presentation note are excluded. Unrelated inventory additions preserve prior bindings while missing new results still block acceptance. Changed semantics, dependencies, declared policy fields, roles or inventory versions invalidate affected results. Legacy envelopes keep strict whole-file identity until an explicit artifact-verified format upgrade writes a separate report; original hashes, timestamps, failures and review dispositions are never relabeled.

Fresh r5 verifies all three Wasm producer paths: eleven frame cases/eleven controls, boundary 12/9 and integrated 22/14/1,000 schedules. All 31 prerequisite modules/objects remain identical to reviewed r10. The frame reader includes a changed build identity because the wrapper/documentation inputs changed; no claim is made that every new frame binary matches r3. Separate format-only upgrades of reviewed frame/native r3 preserve their original execution bytes (including all 49 r3 frame/prerequisite binaries). The native producer is checked against copied completed-run artifacts; no native execution is claimed. The actual combined seven-record gate tolerates an unrelated test addition and adds only that missing-result reason. The 32 existing checker controls and 42 new binding/migration controls pass. Current probes are explicitly diagnostic; their whole-inventory hash remains provenance.

Current packs and original failures remain in-tree; superseded r4 bytes and the prior document/tool records are preserved in the separate evidence repository. The new binding tooling requires its own independent review. Stage 0 remains BLOCKED, C/C4/B correctness and measurement remain next, and H(G) is optional future work with no scheduled obligation. No shared compiler or upstream kernel source changed.
