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
