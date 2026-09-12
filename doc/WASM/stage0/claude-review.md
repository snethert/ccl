

## Sixth Claude audit — reversible native observation, NATIVE-CENSUS-r5 at 3ce72d35 — 12 September 2026

Reviewer: Claude Fable 5.1, in its own session on the reference host. Author: Codex, under the 12 September standing-rule exception for reversible startup instrumentation. Scope: `tests/wasm/native-census/` in full (`observation.patch`, `patch.json`, `observer.lisp`, `probe.lisp`, `inspect-native.lisp`, `run.py`, `reversible.py`, `record.py`, `analyze.py`, `trace-startup.py` and the four self-tests), `doc/WASM/stage0/native-census.md`, the S0-LL08-b/native envelope and the retained r5 evidence. Reviewer disposition only; project acceptance is separate.

### Execution evidence

Fresh run at HEAD in the reviewer's session from the pinned macos-u1-inputs into a separate disposable tree: execution PASS; both native suites 21,843 / 21,843 with 0 failed, missing or unexpected; 161 of 164 FASLs identical during observation with exactly the three patched files differing; all 164 FASLs identical after removal and clean rebuild; every archived source file restored; 167 clean outputs restored; the work tree's observation state reads inactive with all original digests matching. Against retained r5: all 164 FASL hashes identical in the baseline, observed and restored-clean builds; the evaluated snapshot and the 35-callback cold-start sequence identical; `analyze.py` yields the same counts (279 slots, 12 reserved, 599 templates, 51,342 function observations, 164 sources, 103,313 call forms, 3,647 unknown targets). Kernel and image bytes differ from r5, as they already did between the two accepted Gate 0 builds; the probe FASL differs from r5 only through its embedded source path and is identical between the reviewer's own baseline and observed compilations. `test-observer.py` against the reviewer's build: one positive, six rejected, identical probe FASL. `test-reversible.py` (8 controls), `test-clean-outputs.py` (3) and `test-record.py` against r5 (6 rejections) pass. The three original file digests in `patch.json` equal the U1 git blobs at c994217a. The r5 artifact list verifies (563 files), the producer copy of `record.py` matches the committed file, the 26 prior accepted records are unchanged apart from the disclosed path rebasing, and the gate is BLOCKED with 22 missing and one unreviewed. The main checkout has no change outside `doc/WASM`, `tests/wasm` and `CLAUDE.md`.

### Mechanism review

- **The patch is observation only.** Seven hook sites in three files, each guarded by `boundp` and a non-nil test on `ccl::*startup-census-hook*`, so an image without the observer never calls anything. The two sites that wrap an evaluated form (`%compile-time-eval`, the startup callback loop) use `multiple-value-prog1`, so values and the surrounding restart are preserved. No site touches acode, operator tables, backend state or results. The disassembly delta of the six patched functions is hook loads, `BOUNDP` calls and label renumbering.
- **Reversal is real and defended.** `ObservationUnit` refuses a Git checkout or symlinked source, checks all three original digests before touching anything, persists recovery metadata before the first mutation, applies with `git apply --check` first, verifies the observed digests, and on any exit restores from the backed-up originals and re-verifies. Recovery accepts only known original or patched bytes and refuses unexplained edits or damaged backups. The runner then restores the 167 clean outputs, rebuilds from the original bootstrap and requires 164 identical FASLs, and asserts the hook symbol is absent from the restored image.
- **The R6 comparison is fair.** Baseline and observed builds both start from the original bootstrap image, both load the same three compiled files first, and both rebuild with the same declared gensym seed; the observer isolates its own gensym use and blocks re-entry. No normalization is applied. The r2 development failure, where observer DEFVARs shifted later gensym names, is retained and was fixed by removing the initializers rather than by normalizing output.
- **The observations are checked against independent controls.** The probe requires named functions, a direct dependency, an unknown indirect target, macro expansion, a compile-time effect and multiple values, and six injected observer mutations are each rejected while the probe FASL stays byte-identical. The analyzer validates sequence numbers, a single completion, operator ID and flag consistency with the evaluated lookup, reserved-slot emptiness, and callback order equal to the evaluated registrations.

### Findings

No defect found. Six observations, none blocking:

1. **Codex amended the standing rules.** The commit adds a "clean implementation start" rule to `CLAUDE.md` attributed to a user clarification. The rule is consistent with the user's direction, but the reviewer cannot verify the attribution; the user should confirm it.
2. **Four harness files changed after r5 ran** (`test-reversible.py`, `test-observer.py`, `trace-startup.py`, `README.md`) and three were added (`record.py` and two tests). The changes strengthen controls and retention and are disclosed in the history; the six files the producer pins are byte-identical to the r5 runner copy, and the retained producer copy matches the commit.
3. **Kernel and image bytes are not reproducible across runs.** FASLs are. Any future claim about images must rest on FASL identity or a deterministic kernel build, not on image hashes.
4. **67 operator slots never appear in the build observation** (12 reserved plus 55 defined). This is census input, not a defect, but the closure work must not treat "observed during rebuild" as the reachable set; the analyzer already reports both lists.
5. **The external cold-start file trace remains unexecuted.** The runner is correct in structure, holds the client before exec and refuses to count an untraced run, but it needs administrator access that the agent session lacks. This is the one piece of the startup record only the user can produce.
6. **Startup coverage begins at the callback loop.** Runtime and stream initialization before `restore-lisp-pointers` reaches its callback list is outside the hooks, as the report states.

### Disposition

| Record | Reviewer disposition |
| --- | --- |
| S0-LL08-b, variant native (NATIVE-CENSUS-r5) | REVIEWED_NO_DEFECT_FOUND_NOT_ACCEPTED, at the declared scope: evaluated operator IDs, flags and reserved slots unchanged under a reversible observation patch, with two passing native suites and 164 identical FASLs after removal. Reproduced independently. |
| Build, probe, cold-start and test event logs | Reviewed as census inputs; they do not discharge S0-LL15-b or S0-LL15-c, which still need the seed set, conservative closure, joins, initializer semantics and the external trace. |

Not covered by this audit: the external file trace, the complete census graph, the census checker against a real graph, and any Wasm backend work. The implementation baseline remains pristine U1.

### Follow-up to the sixth audit

The user confirmed the `CLAUDE.md` clean-start line, resolving observation 1, and accepted S0-LL08-b at its stated scope. Claude produced the acceptance envelope at the user's direction; that operation is recorded in `stage0/project-acceptance.md` and is not part of the audit.

Correction: the sixth-audit report and the reviewer's notes described S0-LL21-a as accepted, carrying forward an acceptance whose authorization quote the fifth audit had already flagged as reviewer text. The user has since clarified that no such acceptance was given and Codex withdrew it (db395218). S0-LL21-a stands at REVIEWED_NO_DEFECT_FOUND_NOT_ACCEPTED; the 27-record aggregate the reviewer composed for LL08-b is historical, and the corrected 26-record aggregate is current.

## Seventh Claude audit — dependency extension, external trace and the LL21-a correction, at db395218 — 12 September 2026

Reviewer: Claude Fable 5.1, in its own session on the reference host. Author: Codex, under the reversible-observation exception. Scope: `tests/wasm/native-census/dependencies.lisp`, `dependency-probe.lisp`, `redefinition-probe/`, `dependency-graph.py`, `reconcile-trace.py`, `test-dependencies.py`, `test-trace.py`, the `run.py` and `trace-startup.py` changes, `doc/WASM/stage0/native-dependencies.md`, the r6/r7 native runs, the Terminal trace r2 and its reconciliation, and the LL21-a acceptance correction. Reviewer disposition only.

### Execution evidence

Fresh r7-equivalent run at HEAD in the reviewer's session with `--observer-extension`: execution PASS; both native suites 21,843 / 21,843; 161 of 164 FASLs identical under observation with exactly the three patched files differing; 164 of 164 after removal; all sources and 167 clean outputs restored; the graph built from the reviewer's own build log matches Codex's analysis r3 in every summary count, including 55 cross-layer definition groups. Against retained r7 and r5: all 164 FASL hashes identical in the baseline, observed and restored-clean builds; the extension hash in the report equals the committed `dependencies.lisp` and the retained runner copy; all 573 r7 artifact identities verify. `dependency-graph.py` run by the reviewer over the retained r7 build log produces a `graph.json` byte-identical to Codex's analysis r3 with the same summary counts. `test-dependencies.py` against the reviewer's own r5-equivalent build: two native variants, four identical FASLs, eight controls rejected, repeated empty observation preserves dependencies. `reconcile-trace.py` over the retained Terminal trace reproduces Codex's reconciliation exactly; `test-trace.py` passes with the actual trace positive and five mutants rejected. Document, evidence, acceptance and checker tools pass; the gate on the corrected aggregate is BLOCKED with 22 missing and one "unreviewed", which is LL21-a awaiting a project decision. No file outside `doc/WASM`, `tests/wasm` and `CLAUDE.md` differs from v1.13.

### Mechanism review

- **The extension is observation only.** It redefines four observer functions in the observer's own package and reads compiler objects: afunc identity, parent, variables, acode call operands, the evaluated builtin table, `fboundp` and `macro-function` states. It appends to the observer's JSON records, never to acode. The three-file source patch is unchanged (same hash). Identical FASLs across all three builds and the four probe FASLs confirm no output effect.
- **Identity, not names.** A weak EQ table assigns identities to afuncs, root variables and call-site nodes, so two same-named lexical functions are distinguished and a self call targets its own afunc. Self calls are read correctly: the first operand is the argument list. Builtin calls are resolved through the evaluated builtin vector and cross-checked by the graph builder against the snapshot. Anything not exactly resolvable is kept as an unresolved category with no fabricated targets, and the graph builder rejects targets on unresolved calls, unknown categories, operator/category disagreement, missing callee bodies and name/identity disagreement.
- **Declarations versus installations.** Definition forms are recognized from top-level and expanded forms only, never from quoted data or function bodies, and the probe checks that a quoted DEFUN is not reported. Native binding state is sampled at source transitions, initializer entry and return, and explicit load checkpoints, with previous state and sample interval retained; the builder rejects discontinuous histories. The report is explicit that compilation order is not load order and that samples miss transient replacements.
- **The trace.** The v2 tracer holds the launcher before exec, filters on both the PID and a byte-identical uniquely named kernel copy, and requires a pre-exec read, a post-exec read inside CCL, the image open, a matching native PID, clean exits and no loss report. The reconciler parses every line, excludes other processes, classifies host loader and device activity, and reports the four remaining anonymous or relative dyld path contexts rather than dropping them. The trace shows one image open and no source or FASL reads, as expected for a saved image.
- **The correction.** The corrected aggregate differs from the previous one only in LL21-a's disposition and review pointer; all 26 other result objects are byte-equal, including LL08-b. Original envelopes and the withdrawn decision are retained.

### Findings

No defect found. Four observations, none blocking:

1. **The LL21-a acceptance was never the user's.** The fifth-audit observation flagged the quote; Codex has now recorded the user's clarification and withdrawn it. The reviewer's own sixth-audit follow-up and memory repeated the misattribution and have been corrected. An acceptance quote must be verified as the user's own words before an envelope is produced.
2. **`dependency-graph.py` and `README.md` changed after r7 ran.** The retained runner copy is the earlier builder; analysis r3 and the reviewer's byte-identical rebuild use the committed one. Disclosed through the r1 to r3 analysis history.
3. **Unresolved work is large and honestly stated.** 1,729 dynamic call sites, 951 referenced bindings with no compiled candidate in this capture, and four loader path contexts remain. None of this discharges S0-LL15-b or S0-LL15-c.
4. **No inventory slot covers this evidence.** The dependency and trace records are census inputs indexed as diagnostics. They earn gate credit only through the LL15-b/c records once closure exists.

### Disposition

| Record | Reviewer disposition |
| --- | --- |
| NATIVE-DEPENDENCIES-r7, DEPENDENCIES-GRAPH-r3, TRACE r2 and reconciliation r2 | REVIEWED_NO_DEFECT_FOUND, diagnostic census inputs; no gate acceptance applies. |
| LL21-a acceptance correction | VERIFIED: only the LL21-a disposition changed; S0-LL21-a remains REVIEWED_NO_DEFECT_FOUND_NOT_ACCEPTED pending the user's decision. |

Not covered: the LL15-b/c closure algorithm, the census exchange format, generated code. The implementation baseline remains pristine U1.

### Follow-up to the seventh audit

The user accepted S0-LL21-a directly in the reviewer's session. Claude produced the acceptance envelope at the user's direction; recorded in `stage0/project-acceptance.md`, not part of the audit.

## Eighth Claude audit — dyld context classification and clean-image candidates, at eaa0a273 — 12 September 2026

Scope: `reconcile-trace.py` and `test-trace.py` changes, `startup-closure/` (inspector, candidates, seeds, run, controls), `native-loader-contexts.json`, `startup-candidates-summary.json`, retained packet r1. No shared source changed; checkers and gate unchanged (27 accepted, 22 missing, 0 unreviewed).

Reproduced in the reviewer's session: the candidate packet from the retained r7 kernel and clean image is byte-identical to r1 in all four output files; the retained artifact hashes and every input identity match the committed files; the 14 candidate controls and 16 trace controls pass; the reconciler classifies the four dyld operations and leaves none unresolved. The five explicit pre-callback seeds are the literal first statements of `restore-lisp-pointers`, and the other seeds name real definitions.

No defect. Three observations, none blocking: the dyld rule is a fingerprint of this host's loader sequence, which is acceptable because everything before the image open is by construction pre-Lisp; the candidate universe is deliberately the full superset with no address-taken pruning, so it is sound but not yet informative for the dynamic calls; and 183 referenced names have no candidate in either capture and are the next worklist. Disposition: REVIEWED_NO_DEFECT_FOUND, diagnostic census inputs, no gate credit.

## Ninth Claude audit — census stub registration, S0-LL08-a at 21c6aed7 — 12 September 2026

Scope: `tests/wasm/native-census/stub-backend/` in full (registration unit, patch, two payload sources, session, corpus, snapshot, runner, producer, oracle and tests), `doc/WASM/stage0/stub-registration.md`, the CENSUS-STUB-REGISTRATION-r1 packet and its envelope. No shared source changed in the checkout; checkers pass; the standalone record is not yet composed into an aggregate, so the gate still lists S0-LL08-a as missing.

Reproduced in the reviewer's session from the pinned inputs and the retained r7 kernel: PASS; both native suites 21,843 / 21,843 with 75 disabled; 163 of 164 FASLs identical while registered with only `bin/systems.dx64fsl` differing; 164 of 164 after removal and clean rebuild; all 164 FASL hashes, the changed systems FASL, both census module FASLs, the evaluated snapshot and the fourteen target-session rows byte-identical to r1; the same ten target outcomes. The six unit controls and eleven producer controls pass in the reviewer's session; the patch's before-hash equals the U1 blob of `lib/systems.lisp`; all 74 retained artifacts and the executed fixture and dependency identities verify.

Mechanism: the unit adds two module records to `lib/systems.lisp` and two files under `compiler/WASM-CENSUS/` in a disposable copy only, with ownership, identity and unexplained-edit refusals mirroring the observation unit. The backend registers a real `backend` struct with a D1 subset `target-arch`, zero argument registers for B, and a pass-2 entry that throws the front-end function object to a capture tag and errors if pass 2 ever returns, so no target code can be emitted. Sessions establish backend, features, FASL target, foreign data and TARGET/OS nicknames through the same `with-cross-compilation-target` the real cross-build uses, then read the corpus; the oracle checks read-time literals, reader features, the 32-bit natural-access acode, the five-on-stack argument partition, and direct, lexical and unresolved dependencies. Native state is checked identical on return and on nonlocal escape.

No defect. Three observations, none blocking: the record's `test_revision` is the hash of a gzip archive and so changes on every producer run, which is harmless but not reproducible; the standalone envelope must be composed into the aggregate at acceptance, at which point the gate will show LL08-a as unreviewed rather than missing; and the architecture record deliberately leaves uvector subtags and most layout rows empty, so it cannot yet compile the general corpus, which the report states. Disposition: S0-LL08-a / native REVIEWED_NO_DEFECT_FOUND_NOT_ACCEPTED at the fourteen-form registration and target-state scope.

### Follow-up to the ninth audit

The user accepted S0-LL08-a in the reviewer's session. Claude produced the acceptance envelope at the user's direction; recorded in `stage0/project-acceptance.md`, not part of the audit.