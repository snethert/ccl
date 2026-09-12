# Claude adversarial review and disposition — 2026-09-11

Provenance: two reviews supplied by the user in this conversation. The reviewed author was Codex; the reviewer was Claude. This satisfies the requested different-model adversarial review of **r8**. It is not acceptance of r8 or automatic review of later changes. The first supplied notes are retained [verbatim](../history/claude-first-review.txt); the follow-up findings and dispositions are recorded below.

Claude reported fresh fixture execution and byte-identical rebuilt binaries, matching counts, valid r3/r6 original failures, the correct r8 archive hash, passing document/checker controls, and no tracked upstream source edits. Those are reviewer-reported observations; this record does not invent missing raw Claude execution logs. The follow-up withdrew the earlier recommendation for Codex to audit its own implementation and approved committing the isolated additions after verification.

| Finding | Disposition |
| --- | --- |
| Exceptional return left worker 0 idle in JavaScript with RUNNING/admitted state; retirement depended on it | Reproduced unchanged in [original r9 failure](../evidence/runs/2026-09-11-integrated-r9.zip). Fixed in `program.mjs` by parking after checkpoint restoration; `retire` now admits. r10 collects between exceptional exit and retirement; an omitted-park mutant reproduces the failed collector and idle RUNNING TCR. |
| D5 omitted generation-guarded final wakes and explicit active-request routing | [D5 protocol v1.1](../decisions.md) records both mechanisms, terminal-outcome ordering, and the idle-host-boundary requirement with dated rationale. |
| Missing-notification controls used self-witnessing rejection | README and case comments now identify the waiter-count witness. A host-outcome-after-final-wake mutant adds a third explicit waiter witness. |
| Unpinned LLD | Both runners explicitly select Homebrew clang/LLD 21.1.8 and verify versions; executable paths and hashes are retained. r10 passed with all three selection variables unset. |
| Stale probe/boundary inventory hashes labeled current | Old records are marked superseded. Fresh probes r5 bind the current inventory; r10 contains the freshly executed boundary prerequisites. |
| Platform mismatch | User selected macOS. Native target, bootstrap, second-Mac reproduction and external census tracing now use macOS. Fresh native r3 passes both release-era test runs with 164/164 raw-identical FASLs; the current-head diagnostic retains three failures separately. Earlier platform-specific facts are historical only. |
| Heading, sentence, typo and stale DOCX verification | Fixed in the coordinated outline 0.14 / acceptance 1.4 / decisions 1.5 package; reading copies and verification regenerated. |
| Evidence weight and missing standing rules | Superseded packs moved byte-for-byte to the external local store with locators/hashes. Current packs and original integrated failures r3/r6/r9 stay in the repository. Root AGENTS.md and CLAUDE.md record the user-supplied scope and verification rules. |

At this first-audit checkpoint, the r10 runtime result records remained **NOT_REVIEWED** because the changes following Claude's r8 audit had not received a new external review. The second audit below supersedes that review status without rewriting the original result envelopes. Stage 0 remains incomplete. No shared compiler or upstream `lisp-kernel` source was edited. Same-author verification of these fixes supports a reviewable commit, not acceptance.

## Second Claude audit — r10, probes r5 and native Gate 0 — 11 September 2026

Reviewer: Claude Fable 5.1, executing directly in its own session on the reference host (macOS 24.6.0, Intel Xeon W-2140B, Node v25.6.1 / V8 14.1, Homebrew clang and LLD 21.1.8, WABT 1.0.39). Author of the reviewed changes: Codex. This section covers the changes made after the r8 audit above. It is a reviewer disposition, not a project acceptance decision; every slice below stays NOT ACCEPTED until the acceptance policy's review record exists.

Note on provenance: `history/claude-first-review.txt` retains the second of Claude's conversation reviews (the integrated-harness update); the initial document-level review and the Codex-authorship pass were not retained verbatim. Their findings are all represented in the disposition table above.

### Verification performed

- `manage.py check`, `test-controls.py` (29 controls) and `check-evidence.py --include-external` (23 identities) pass on the committed tree.
- Fresh execution of all three Wasm runners into empty directories outside the checkout. Probes: 3 PASS. Boundary: 2 PASS, 12 cases, 9 rejected controls. Integrated: 22 positive PASS, 14 REJECTED, 1,000 seeded schedules PASS. Each fresh envelope binds the current inventory hash and gates BLOCKED with 54 remaining reasons and no provenance failure.
- Every rebuilt module and object is byte-identical to the retained current packs: r10 kernel, program, lazy, emitted, boundary object, the omitted-park mutant and the prerequisite boundary modules; r5 cons, late-worker and materialized memory modules.
- Retained archive hashes for r10, r9, r6, r3 and r5 match `evidence/index.json`. r9 retains the original FAIL for the idle-RUNNING defect found in the r8 audit.
- Code review of the fixes: `program.mjs` now parks on the exceptional path after checkpoint restoration; `retire` admits before mutating; the new `collection-between-nonlocal-exit-and-retirement` case exercises the previously uncovered window; the `omitted-exception-park` control is rejected with the specific failed-collector snapshot. D5 protocol v1.1 text matches the fixture's generation-guarded wake pair, active-request routing and idle-boundary parking. Toolchain selection is pinned by explicit path and version check; the r10 record was produced with all selection variables unset.
- Native Gate 0 reproduced independently from the pinned inputs with the unmodified runner: two clean builds from the pinned v1.13 bootstrap, 21,843/21,843 eligible tests passing in each, 75 upstream-disabled tests recorded, 164/164 FASLs raw-identical between the two builds, and all 164 FASL hashes identical to the retained r3 pack (same host, independent execution). Archived source unchanged.
- The 2026-head diagnostic reproduced exactly: 21,850 pass, the same three post-release failures (bitvector reader, constant-index complex-single-float vector, `#.` multiple values), 75 upstream-disabled tests.
- No tracked upstream source is modified by commit 85adc038; its changes are confined to `doc/WASM`, `tests/wasm`, `CLAUDE.md` and `AGENTS.md`.

### Dispositions

| Slice / record | Disposition |
| --- | --- |
| S0-LL13-c, S0-LL19-b (r10 prerequisites) | REVIEWED_NO_DEFECT_FOUND_NOT_ACCEPTED, hand-built scope only. |
| S0-LL20-a, S0-LL20-b, S0-LL20-c (r10) | REVIEWED_NO_DEFECT_FOUND_NOT_ACCEPTED, hand-built scope only. The r8 defect is fixed and its regression is retained. |
| PROBE-* (r5) | REVIEWED_NO_DEFECT_FOUND; probes never discharge S0 IDs. |
| G0-U1-a (native r3) | REVIEWED_REPRODUCED_NOT_ACCEPTED: execution and same-host repeatability confirmed independently; second-Mac reproduction (S0-LL08-c) and the acceptance decision remain outstanding. |

### Findings not blocking commit

- The external evidence store is a set of absolute local paths under `/Users/buildsomething/Source/ccl-evidence` with no version control or backup. The index says so. The packs are hash-bound, so relocation is safe, but durability depends on that directory surviving.
- Commit 85adc038 was authored by Codex under the operator's git identity and its message does not say so. This record and the commit that adds it state the provenance; rewriting the earlier message is the operator's choice.
- Stage 0 remains BLOCKED on the census, layout, ABI, engine and control slices; nothing in this audit changes that.

## Subsequent Codex frame fixture — review boundary

The S0-LL23-b frame proof was authored after this audit. Its fresh integrated prerequisites use the same reviewed runtime source, but this audit does not review the new frame reader, emitted frames, maps or controls. r10, probes r5 and native r3 retain their original bytes and review records in the evidence index. Adding the frame runner changes the global inventory hash: fresh Wasm runs bind the new inventory, while the unchanged native r3 execution is explicitly re-bound by verifying its original artifacts. At that point no new native execution or external frame review was claimed; the later frame audit is recorded below.

## Subsequent architecture feedback supplied by the user

Claude expressed confidence in the tested D5 admission protocol, C-boundary restoration, D1/D2 representation choices, D4 split and acceptance machinery. The feedback also identifies scale, cold start and cross-module calling costs as unproved, recommends coupling granularity with D3, and proposes a generated-code H(G) experiment plus parallel census/compiler work. These are recorded in the [product-risk plan](product-risk-plan.md), including corrections to the blanket browser-cache and per-Worker compilation assumptions. This feedback supplies no new run archive or specific audit of the logical-frame addition, and did not change its then-NOT_REVIEWED/NOT_ACCEPTED status. The later frame audit below supplies that separate review.

The user then explicitly directed that H(G) be ignored except as a possible future enhancement. The revised C/C4/B-only gate implements that scope decision; it does not impose a generated-code H deadline. No other obligation is waived, and no unexecuted candidate is labeled passing.

## Claude audit of debugger-frame r3 — supplied by the user

Disposition: **REVIEWED_NO_DEFECT_FOUND_NOT_ACCEPTED** for the bounded r3 frame mechanism at commit `ff900004`. Claude reports a fresh run with eleven positive cases, eleven rejected controls, boundary prerequisites 12/9 and integrated prerequisites 22/14 with 1,000 seeds. All 49 rebuilt objects/modules matched r3 byte-for-byte, its archive hash matched the index, and the gate blocked only on expected remaining work. The reported 29 checker controls and 28 evidence identities describe that earlier checkout; they are not the later H-retirement or binding-tool counts.

Claude checked the 64-byte header against the writer, C assertions and host oracle; publication before calls; absence of polls during construction/restoration; moving tagged roots with an unchanged raw slot; joint restoration of frames, checkpoints, result ownership and active request before parking; and the live-address/generation test whose stale thread lifetime alone causes rejection. The stale-slot mutant fails in the runtime’s semispace check. The reviewed integrated-runtime implementation remains unchanged.

Nonblocking observations: policy-1 unavailable values are still materialized and rooted, so no optimized storage-cost claim is proved; the shared cell has a permanent root and proves relocation rather than capture/escape; and the duplicated C/schema lexical table remains a limitation of this hand-built proof. The labels now state those bounds directly. Generated closure semantics and measured D3 costs remain required.

The inventory-churn recommendation is implemented separately as [v2 per-test binding](../contracts/evidence-binding.md). It preserves original snapshots and validates the test plus transitive prerequisites. This new tooling and its producer changes are not covered by Claude’s r3 audit. No result is promoted to ACCEPTED.

## Third Claude audit and reviewer sign-off — HEAD 9c2ef44d, 11 September 2026

Reviewer: Claude Fable 5.1, executing in its own session on the reference host. Scope: every tested functionality at the current checkout, including the two Codex commits after the second audit (H(G) retirement 04288377 and v2 evidence binding 9c2ef44d). This is a reviewer sign-off with evidence. Project acceptance, which flips the gate's per-record disposition, remains the operator's decision and is not asserted here.

### Evidence gathered at HEAD

| Check | Result |
| --- | --- |
| Upstream source since v1.13 | `git diff c994217a HEAD` outside `doc/WASM`, `tests/wasm`, `CLAUDE.md`, `AGENTS.md` is empty. |
| Document tooling | `manage.py check` PASS; 32 checker controls PASS; 42 contract-binding controls PASS; 33 retained evidence identities PASS; `git diff --check` clean. |
| Probes, fresh | 3 PASS; 6 of 6 modules byte-identical to retained r7. |
| Boundary, integrated and frames, fresh (one runner) | Boundary 12 cases / 9 controls; integrated 22 / 14 / 1,000 seeds; frames 11 / 11; all six S0 records PASS. 49 of 49 rebuilt modules and objects byte-identical to retained r5. Gate on the fresh envelope: BLOCKED, 49 reasons, none a provenance or execution failure. |
| v2 binding invariance | The fresh run's `S0-LL23-b` contract digest equals r5's although the two runs retained different inventory snapshots; the binding varies with contract content, not with unrelated inventory edits, as designed. |
| Combined current gate | Re-running `gate.py` on the retained combined envelope reproduces the recorded result exactly: BLOCKED, 49 reasons, 7 of them "unreviewed" for the seven executed records. |
| Native Gate 0, v2 envelope | 375 of 375 execution artifacts byte-identical to the original r3 pack; the 4 additional files are the binding source and snapshot. No new native execution was claimed, and none occurred. |
| Native Gate 0, independent reproduction | Two clean builds from the pinned inputs in the reviewer's session: 21,843 / 21,843 eligible tests each, 164 / 164 FASLs raw-identical, and all 164 hashes identical to the r3 pack. The 2026-head diagnostic reproduced its three failures. |
| Evidence repository | `catalog.py check` PASS: 6,767 immutable files, 157 indexed identities; 8 catalog controls PASS; `git fsck --full` clean apart from one dangling blob. Working tree clean at e57e1d9. |

### Review of the v2 binding tooling

Read in full: `evidence_binding.py`, `bind-evidence.py`, the `gate.py` and `check-evidence.py` integrations, `test-bindings.py`, the three runner changes and `record.py`. The semantic digest covers the test entry and its transitive prerequisites minus bookkeeping fields, plus inventory context minus the test list and note; cycles, unknown prerequisites, duplicate IDs and escaping paths are rejected; migrations never overwrite and never rewrite an artifact. The 42 controls exercise the cases that matter, including a changed prerequisite description and a changed runner. One limitation, not a defect: `binding_errors` stops at the first error, so a report with several problems reveals them one at a time. No defect found.

### Sign-off

| Record | Reviewer disposition |
| --- | --- |
| G0-U1-a, native r3 (v2 envelope) | SIGNED OFF for same-host execution and repeatability. Second-Mac reproduction S0-LL08-c remains open. |
| S0-LL13-c, S0-LL19-b | SIGNED OFF, hand-built scope. |
| S0-LL20-a, S0-LL20-b, S0-LL20-c | SIGNED OFF, hand-built cons-only scope at recorded bounds. |
| S0-LL23-b, frames r3 through r5 | SIGNED OFF, hand-built scope; observations from the r3 audit stand and are now labeled in the fixture. |
| Probes r7 | Verified; diagnostics only, no S0 credit. |
| v2 evidence binding and evidence repository | REVIEWED, no defect found. |

Bounds of this sign-off: it covers the mechanisms as executed in kilobyte-scale cons-only fixtures on Node and V8, and the native baseline on one Mac. It does not cover scale, startup, browser engines, generated code, the census track or D3. To make the gate count these records, the project needs an acceptance envelope that sets `review_disposition` to ACCEPTED with this record as `review_record`; producing that envelope is a project decision and a small producer step, not a reviewer action.

## Fourth Claude audit — C/C4/B dynamic-call fixture, DYNAMIC-CALL-r1 at 7187a89b — 11 September 2026

Reviewer: Claude Fable 5.1, in its own session on the reference host. Author: Codex. Scope: `tests/wasm/stage0/dynamic-call/` in full (`abi.c`, `support.mjs`, `functions.mjs`, `cases.mjs`, `harness.mjs`, `loader.mjs`, `actor.mjs`, `build.mjs`, `run.mjs`, `schema.json`) and `doc/WASM/abi/dynamic-call.v0.md`, against LL05, LL21-b, LL04 and LL13-a as bound in the inventory. Reviewer disposition only; project acceptance is separate.

### Execution evidence

Fresh run at HEAD: 159 positive PASS, 81 controls REJECTED, 0 failures; prerequisites boundary 12/9, integrated 22/14/1,000 seeds, frames 11/11; 24 records PASS. 864 of 864 modules and objects byte-identical to the retained r1 pack, including all 35 new ABI binaries, all 49 previously reviewed prerequisite binaries and every quarantined mutant build. Gate on the fresh envelope: BLOCKED with 25 missing and 24 unreviewed, no provenance or execution failure.

### Mechanism review

- **Frame and roots.** `$enter` builds a 512-byte frame above the caller-owned overflow area, chains one root record per eight argument slots plus a result record and a temporary record, copies parameters and overflow words into rooted slots, then publishes the chain and frame head before any operation that can poll. Unused candidate parameters must be NIL and the root budget is enforced before publication. The C reader's static assertions and `abi_check` verify header, bounds, alignment, block counts and membership of every record in the live chain independently of the writer.
- **Result ownership.** Each physical result word has exactly one scanner: while the TCR descriptor owns a region its root record count is zero, and `nested_call`, `debugger`, `finish` and `tail_exit` switch ownership with plain stores between polls. I traced the ordinary, nested, nested-twice, debugger, tail and nonlocal paths; the transient windows where a region is briefly double-registered contain no poll, allocation or host entry, which the protocol requires. The two development failures Codex hit here are real and their mutants trap in the collector as claimed.
- **Tail transfer.** Transfer values are cached in locals, the frame is retired without polling, the overflow area is rewritten for the new count, and `return_call_indirect` dispatches through the loader. Function objects are reachable through the anchors root record, so self reloads survive the fifty collections a 100,000-step chain performs. Bounded stack and root use are asserted against the recorded baseline, and the enclosing binding and handler records are checked on every iteration.
- **Lazy installation.** The stub publishes self and arguments, suspends on the reviewed request protocol, and after the host supplies bytes the loader checks digest, validity, absence of start/data/element sections, memory profile, table contract, import allow-list, export set and per-export signatures before publishing any slot. The stub then reloads self from its frame, retires its frame and redispatches. The stale-stub mutant traps in the semispace check.
- **Lisp-level semantics.** Arity, designator, capacity, generation and stack conditions are explicit fixture conditions raised before entry, never engine traps. Optional/rest builds the rest list under forced collection. Keyword processing follows leftmost-wins and leftmost `:allow-other-keys`. APPLY spreads a proper list into rooted staging slots.
- **Candidates.** C, C4 and B share one corpus; B routes every argument through the overflow area and its swapped-argument mutant targets that path specifically.

### Findings

No defect found. Three observations, none blocking:

1. **Dispatch-time role validation is a stand-in.** Install-time validation is real: export names and signatures are checked before a slot is filled. But the `ROLE_MISMATCH` rejection in `same-signature-wrong-role` is a throw placed on the test-injected path, not a check of a slot's registered role against the requested role. The companion `bypassed-role-validation` control correctly shows that the semantic oracle catches the substitution when that throw is absent. This satisfies S0-LL05-b as written, which admits semantic assertions, but a production loader will need a dispatch-time or install-time role registry, and the mutant should then corrupt that registry.
2. **A circular APPLY list is reported as the capacity condition (911), not an improper-list condition.** Detection is by exceeding 32 elements. Correct at these bounds; the case name should not suggest cycle detection.
3. **The single-scanner invariant is not checked at inspection points.** `abi_check` verifies chain membership but not that the TCR-owned region's root record count is zero. Adding that check would turn a class of ownership bugs from collector traps into precise fixture failures.

### Disposition

| Records | Reviewer disposition |
| --- | --- |
| S0-LL05-a/b/c/d and S0-LL21-b, variants C, C4 and B | REVIEWED_NO_DEFECT_FOUND_NOT_ACCEPTED, hand-built scope at the declared bounds: 32 arguments, 6 values, 8 frames, 16 KiB stack, cons-only heap, Node/V8 only. |
| S0-LL04-a, S0-LL04-b, S0-LL13-a | REVIEWED_NO_DEFECT_FOUND_NOT_ACCEPTED. Independent C and emitted cons oracles with unequal payloads, dotted, shared, nested and cyclic graphs, NIL reads and mutation; the one-sided swap is rejected; overlapping and undersized ownership maps are rejected before publication. |

Not covered by this audit: ABI timing or selection, module granularity, browser engines, generated code, and any production object model. D3 remains open.

## Fifth Claude audit — D3 measurement derivative and S0-LL21-a, ABI-MEASUREMENTS-r2 at 023181c0 — 12 September 2026

Reviewer: Claude Fable 5.1, in its own session on the reference host. Author: Codex. Scope: `tests/wasm/stage0/abi-measurements/` in full (`measure.c`, `support.mjs`, `functions.mjs`, `emit.mjs`, `cases.mjs`, `workloads.mjs`, `harness.mjs`, `loader.mjs`, `actor.mjs`, `build.mjs`, `run.mjs`, `resources.mjs`, `statistics.mjs`, `test-statistics.mjs`, `schema.json`, `README.md`), the source delta of the six copied files against the reviewed dynamic-call fixture, `doc/WASM/stage0/abi-measurements.md`, the fdebe7b3 acceptance operation, and the retained r2 evidence. Reviewer disposition only; project acceptance is separate.

### Execution evidence

Fresh run at HEAD in the reviewer's session, same engine flags: 486 positive PASS, 279 controls REJECTED, 72 batch checks PASS, 27 batch controls REJECTED, 27 trial-candidate rows, 0 failures, exit 0. The reviewed dynamic-call prerequisites executed first and passed (159/81, 24 records). 4,518 of 4,518 Wasm modules and objects byte-identical to the retained r2 pack, including the 864 reviewed prerequisite binaries; the bound test revision and contract digest are identical to r2. The reviewer's own three-trial ratios rank the candidates differently from r2 within the same 1 to 3 percent band, which is what observation 2 below predicts. Codex's r1 prototype and r2 build binaries are identical in all 135 build objects, as the r2 report claims. An independent Python recomputation from the raw r2 trial files reproduces every candidate ratio, bootstrap interval and point-best choice to within 1e-9, and confirms that every retained warm and sample batch traverses whole 32-record schedules and that each reported nanoseconds-per-iteration equals the sum of its sample batches. Evidence catalog: 102,450 files, 448 indexed identities, check PASS. Document, checker, binding, acceptance and evidence tools all pass; the gate on the current aggregate is BLOCKED with 23 missing and one unreviewed (S0-LL21-a), as recorded.

The fdebe7b3 acceptance operation was checked separately: the eighteen dynamic-call records gained ACCEPTED dispositions, the seven earlier acceptances and every original artifact identity are unchanged, and the policy file hash cited by every measurement equals the committed `benchmarks.json`.

### Mechanism review

- **Source delta.** The derivative differs from the reviewed fixture only in: a `$measuring` global in the support module that skips per-call admission, parking and inspection inside a batch and routes `$invoke` through the driver's `dispatch` slot; a forced-collection hook at generic entry read from state offset 76; the driver, bundle, registry and schedule emitters; the `Roles` registry, `validateDriver` and the publication commands in the actor; and `measure.c`. No reviewed dynamic-call, frame, runtime or boundary source changed, and no shared compiler or upstream kernel file changed since c994217a.
- **Timed path.** `batch` admits once, checks ownership, enables measuring mode, then for each record clears results, stages 32 inputs, builds any APPLY list or heap argument with the rooted `abi_cons`, calls `start`, folds the first value and every result through the C graph digest, polls, and repeats. Diagnostic and measured modes execute identical bytes; only host forwarding is suppressed, and any host request, callback or install inside a batch throws. The same driver and `batch` export are exercised by the 72 batch checks and 27 batch controls before any timing, so the dispatch path is qualified, not just timed.
- **Ownership assertion.** `measure_ownership` walks the live root chain and the TCR result descriptor, collects physical scanner addresses, and requires each result word of every frame on the chain to have exactly one scanner (933), the active region's advertised count to match (932) and no duplicate addresses (931). It walks `reserved[0]`, which is `frame_head` at TCR offset 224, and reads the result base and count at frame offsets 116 and 112, which is where `$enter` and `$count` write them. It runs only at legal inspection points, outside the no-poll handoffs. This discharges the third observation of the fourth audit; the duplicate-scanner batch control now fails with 931 instead of a collector trap.
- **Role registry.** Publication validates every slot's code, role and function type before filling any, and `resolve`/`checkAll` compare the live table entry with the registered function. The `actual-same-signature-table-corruption` control replaces a real same-signature entry and is caught by `checkAll` before a batch. Normal lookups are a Wasm registry function; only the injected controls use the JavaScript path. This discharges the first observation.
- **Graph digest.** The C reader and the JavaScript oracle apply the same FNV-style mix over an address-independent breadth-first numbering, so sharing and cycles are compared structurally and moved conses do not change the observation. Both cap at 64 nodes. The oracle for the tail-chain workload correctly reduces a 2,000-transfer chain to the final fold with arguments 0 and 2 on the even-length chain.
- **Statistics.** Paired ratios are per trial across the eight workloads, bootstrap resamples whole trials with the seeded xorshift generator, percentile intervals are reported and the policy minima are checked and reported as gaps. The ten controls cover known ratios under common drift, reproduction, missing or duplicate candidates, invalid timings and insufficient trials or durations. `NO_SELECTION` is unconditional.
- **S0-LL21-a.** Worker 0 validates the prebuilt module bytes, writes the logical code and digest into a shared publication record and releases a generation word with a sequentially consistent store. Worker 1 and a late Worker 2 load the generation, compare the digest with their own record, hit the uninstalled stub, request installation through the reviewed lazy path, install matching roles and execute version 2; Worker 0 then calls the old version 1 object. The late Worker collects during installation. Missing publication and a flipped digest bit are rejected.

### Findings

No defect found. Five observations, none blocking acceptance of S0-LL21-a at its stated bounds:

1. **The publication carries identity, not code.** Each Worker already holds every module's bytes from its creation data; the shared record transfers only the code number and SHA-256, and installation still fetches bytes through the existing request protocol. The case therefore proves first-call installation in an existing and a late Worker against a published identity, not delivery of prebuilt bytes between Workers. The report's wording is accurate; the acceptance scope should say it explicitly.
2. **The exploratory timer cannot yet rank the candidates.** A direct-call iteration costs about 2,300 ns, almost all of it protocol that is identical for C, C4 and B: the 512-byte frame fill, root records, checkpoints, result copy, graph digest, poll and cleanup. The argument staging that the ABI actually changes is a sliver of that, and the observed spread is 1 to 4 percent in every packaging. The frozen rule chooses the simplest candidate within 5 percent, so applied to a harness with this overhead profile it returns B regardless of the true difference. Before selection trials, the harness needs a positive sensitivity control, for example a deliberately penalized candidate variant that the rule must detect above the band, or the fixed cost must be reduced or separated. This is a design requirement for `S0-ABI-selection`, not a defect in r2, which claims no selection.
3. **"Same-module direct" includes an eight-way dispatch chain.** The bundle's `dispatch` selects the callee with a sequence of comparisons before the direct tail call. Generated code has no such chain. Fine for exploration; the selection design should disclose it or emit true per-callsite direct calls.
4. **Bundled packagings validate bytes they do not execute.** In the direct and same-instance configurations the individual callable modules are validated for identity, but the bundle driver is what is instantiated; its digest is validated separately by `validateDriver`. Both come from the same build, so this is disclosed and consistent, but the per-code compile and instantiate timings in those configurations are empty by construction.
5. **The two publication controls are host-side assertions.** Missing and corrupted publication are rejected in the actor before any Wasm executes. They show the checks exist; they do not exercise a Wasm-side acquire path.

### Disposition

| Record | Reviewer disposition |
| --- | --- |
| S0-LL21-a, variant full (ABI-MEASUREMENTS-r2) | REVIEWED_NO_DEFECT_FOUND_NOT_ACCEPTED, at the declared bounds: eight hand-built definitions, two live Workers plus one late Worker, identity-only publication with bytes pre-provisioned per Worker, cons-only 4 KiB semispaces, Node/V8 only. |
| Exploratory timings (24 measurement IDs) | REVIEWED_EXPLORATORY_ONLY. Correct as computed and reproduced; no selection value. Observation 2 must be resolved in the selection harness design before `S0-ABI-selection` is attempted. |

Not covered by this audit: the frozen benchmark policy itself, browser engines, the optimized tier, generated code, representative workload weights, and any production object model. D3 remains open.
