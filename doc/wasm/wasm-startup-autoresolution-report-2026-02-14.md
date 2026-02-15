# WASM Startup Autoresolution Change Log and Root-Cause Report

Generated: 2026-02-14T20:09:13Z (UTC)
Repo: `/Users/buildsomething/Source/ccl`
Branch: `wasm-port`
HEAD: `c5636245`

## 1. Scope and Method

This document is built from two sources only:

1. Session history artifacts under `/private/tmp` (trace logs, step summaries, troubleshooting ledger).
2. A direct code sweep of the current tree (no assumptions from stale snapshots).

Primary question answered:

- What autoresolution behavior changed across this investigation?
- What is the root cause class for the current boot failure (`missing symbol`, `wrong package`, `wrong entry`, or other)?

## 2. Evidence Corpus

### 2.1 Session artifacts consumed

- `/private/tmp/rc-7-fasload-troubleshooting.md` (Steps 89-96 evidence ledger)
- `/private/tmp/step97.unresolved-symbols.txt`
- `/private/tmp/step97.autobind-symbols.txt`
- `/private/tmp/step97.method-fallback.autobind-seq.txt`
- `/private/tmp/step97.startup-resolution.classof1337.json`
- `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof7661.20260214T193611Z.log`
- `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof1337.20260214T193637Z.log`
- `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof1337-macptr1338.20260214T193747Z.log`
- `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof1337-getfptr5681-macptr4709-stackblock-vstackptr5692.20260214T194928Z.log`

### 2.2 Code sweep files consumed

- `doc/wasm/js/bootstrap-function-resolver.mjs`
- `doc/wasm/js/make-real-image.mjs`
- `doc/wasm/js/startup-binding-map.mjs`
- `lisp-kernel/wasm-kernel-stubs.c`
- `scripts/wasm/recompute-resume-closure-matrix.sh`
- `doc/wasm/startup-symbol-pipeline-spec/spec-closure-checklist.md`
- `doc/wasm/startup-symbol-pipeline-implementation-plan.md`

### 2.3 Commit sweep basis

Commit series analyzed (directly relevant to autoresolution and boundary behavior):

- `b46646c3` (2026-02-11)
- `37f24b96` (2026-02-12)
- `9fb515d7` (2026-02-12)
- `9b142779` (2026-02-12)
- `7a43ff93` (2026-02-12)
- `2c8fac2b` (2026-02-12)
- `bbf9af15` (2026-02-12)
- `1b9cbbbc` (2026-02-12)
- `96ee7269` (2026-02-13)
- `dc2af9af` (2026-02-13)
- `de9453d5` (2026-02-14)
- `d23a4c21` (2026-02-14)
- `ad5d1a8a` (2026-02-14)
- `60d1117d` (2026-02-14)
- `726c46f9` (2026-02-14)
- `aaacb903` (2026-02-14)
- `c5636245` (2026-02-14)

## 3. Current Autoresolution Architecture (Code Sweep)

### 3.1 Resolver core and package canonicalization

`bootstrap-function-resolver.mjs` currently provides:

- bootstrap-only host-side resolution phase gating (`bootstrap` vs `canonical-lisp`): `doc/wasm/js/bootstrap-function-resolver.mjs:9-11`, `doc/wasm/js/bootstrap-function-resolver.mjs:488-491`
- symbol package override canonicalization map including `KEYWORD::TOPLEVEL -> CCL::TOPLEVEL`: `doc/wasm/js/bootstrap-function-resolver.mjs:18-23`
- pre-fasload fallback package list (`INSPECTOR`, `SWINK`, `ANSI-LOOP`, `ARCH`, `X86`): `doc/wasm/js/bootstrap-function-resolver.mjs:25-31`
- ambiguity-aware lookup (`reason: ambiguous`): `doc/wasm/js/bootstrap-function-resolver.mjs:455-483`, `doc/wasm/js/bootstrap-function-resolver.mjs:524-533`
- const-pool symbol rewrite path with explicit diagnostics for package canonicalization (`bindingState: canonicalized-symbol-package`): `doc/wasm/js/bootstrap-function-resolver.mjs:833-894`

### 3.2 Pre-toplevel and const-pool gates

`make-real-image.mjs` enforces resolution in two places:

- pre-toplevel designator gate (`STARTUP_FUNCTION_DESIGNATOR_GATE`): `doc/wasm/js/make-real-image.mjs:898-934`
- const-pool rewrite/gate (`STARTUP_CONSTPOOL_FUNCTION_GATE`): `doc/wasm/js/make-real-image.mjs:1621-1676`

### 3.3 Required-callable closure seeding from contract

`startup-binding-map.mjs` seeds and enforces `requiredCallables` as first-class roots:

- load required callable list and count: `doc/wasm/js/startup-binding-map.mjs:1066-1070`
- enqueue callable seeds as synthetic refs: `doc/wasm/js/startup-binding-map.mjs:1268-1313`
- resolver application for required callable seeds, with ambiguity/unresolved accounting: `doc/wasm/js/startup-binding-map.mjs:1473-1489`
- required callable definition upgrades (`required_class: required-callable`): `doc/wasm/js/startup-binding-map.mjs:1499-1503`

### 3.4 Runtime-probe resolver fallback for map augmentation

`make-real-image.mjs` augments resolver misses with runtime fcell probing:

- runtime probe entry path and error classes (`runtime-symbol-unresolved`, `runtime-fcell-unresolved`, etc): `doc/wasm/js/make-real-image.mjs:3050-3125`
- metadata-first then runtime-probe fallback decision: `doc/wasm/js/make-real-image.mjs:3126-3205`

### 3.5 Required-fasload boundary classifier and reason tagging

Boundary reasons are explicitly classified:

- unresolved-function-symbol reason vs trap reason in catch path: `doc/wasm/js/make-real-image.mjs:5426-5429`
- unresolved-function-symbol reason vs rc-failed reason in rc!=0 path: `doc/wasm/js/make-real-image.mjs:5488-5491`
- unresolved function extraction (`arg_z_symbol` with `nfn_entry < 0`): `doc/wasm/js/make-real-image.mjs:4918-4930`

### 3.6 Boundary-autobind recovery machinery

Boundary-autobind currently supports:

- enable/disable: `CCL_WASM_BOUNDARY_AUTOBIND`: `doc/wasm/js/make-real-image.mjs:5020`
- method fallback toggle and allow/deny lists: `doc/wasm/js/make-real-image.mjs:5021`, `doc/wasm/js/make-real-image.mjs:5036-5043`, `doc/wasm/js/make-real-image.mjs:5065-5071`
- explicit entry overrides (`CCL_WASM_BOUNDARY_AUTOBIND_ENTRY_OVERRIDES`): `doc/wasm/js/make-real-image.mjs:5044-5063`
- unresolved symbol recovery + package candidate probing (`CCL`, `COMMON-LISP`, `CL`): `doc/wasm/js/make-real-image.mjs:5135-5173`
- override application (`source=boundary-autobind-entry-override`): `doc/wasm/js/make-real-image.mjs:5199-5213`
- method fallback to runtime module method names (`source=runtime-modules-method-fallback`): `doc/wasm/js/make-real-image.mjs:5232-5245`
- startup map mutation + immediate re-apply (`source=required-fasload-boundary-autobind`): `doc/wasm/js/make-real-image.mjs:5286-5334`

## 4. Chronological Autoresolution Change Ledger

## 4.1 Foundation phase

### `b46646c3` (2026-02-11): Initial integrated resolver stack

Change:

- Introduced `bootstrap-function-resolver.mjs` and wired designator rewriting + host bridge.

Evidence:

- `git show b46646c3` includes new resolver export `rewriteConstPoolFunctionDesignators`, host bridge symbol `wasm_host_resolve_function_designator_entry`, and pre-toplevel/const-pool gate emissions.
- Current retained surfaces:
  - `doc/wasm/js/make-real-image.mjs:1804-1823`
  - `doc/wasm/js/make-real-image.mjs:898-934`
  - `doc/wasm/js/make-real-image.mjs:1621-1676`

Impact:

- Moved function designator normalization from opportunistic runtime behavior into explicit bootstrap policy.

### `37f24b96` (2026-02-12): Purge startup bypasses

Change:

- Removed bypass-oriented host resolver hook path in kernel at that point.

Evidence:

- `git show 37f24b96` contains deletions for `wasm_host_resolve_function_designator_entry` imports/calls.

Impact:

- Tightened contract around startup path; reduced silent fallback behavior.

## 4.2 Unified startup binding-map and boundary observability

### `9fb515d7` + `9b142779` + `7a43ff93` + `2c8fac2b` (2026-02-12)

Change:

- Built and unified pre-fasload startup binding-map flow.
- Added required-fasload boundary payload with embedded startup map build/apply summaries.
- Added unresolved-function-symbol classification at boundary.

Evidence:

- `git log -S "REQUIRED_FASLOAD_BOUNDARY"` points to `9b142779`.
- `git log -S "required-fasload-unresolved-function-symbol-after-unified-startup-binding-map-apply"` points to `2c8fac2b`.
- Current retained reason classifier and boundary payload logic:
  - `doc/wasm/js/make-real-image.mjs:5426-5429`
  - `doc/wasm/js/make-real-image.mjs:5488-5491`

Impact:

- Boundary failures became classifiable as unresolved-symbol vs trap/rc-fail, enabling targeted autobind interventions.

## 4.3 Artifact-first resolver ownership

### `bbf9af15` + `1b9cbbbc` + `96ee7269` + `dc2af9af`

Change:

- Moved startup function resolution ownership to generated artifact logic (`startup-binding-map.mjs`), then removed broad fallback paths and restored strict apply progression.
- Fixed memory blowup and special initializer seeding around map/preinstall.

Evidence:

- `git show bbf9af15` shows large resolver build logic added in `startup-binding-map.mjs`.
- `git show 1b9cbbbc` shows fallback path removals.
- `git show 96ee7269` tied to strict pre-fasload apply.

Impact:

- Reduced nondeterministic startup behavior from runtime opportunism; made closure gaps explicit.

## 4.4 Required-callable and deferred-symbol closure hardening

### `de9453d5` + `d23a4c21` + `ad5d1a8a` (2026-02-14)

Change:

- Fixed scope artifact emission and blocker diagnostics.
- Restored required-callable startup rows.
- Widened callable metadata resolution for deferred fasload symbols, including runtime-probe fallback path.

Evidence:

- required-callable machinery in current tree: `doc/wasm/js/startup-binding-map.mjs:1066-1070`, `doc/wasm/js/startup-binding-map.mjs:1268-1313`, `doc/wasm/js/startup-binding-map.mjs:1473-1503`
- runtime probe fallback retained in `doc/wasm/js/make-real-image.mjs:3050-3205`

Impact:

- Reduced false misses from metadata-only matching; still not enough to close all required boundary symbols.

## 4.5 Diagnostic continuation and boundary autobind/autowire

### `60d1117d` + `726c46f9` + `aaacb903` + `c5636245` (2026-02-14)

Change:

- Added diagnostic continuation controls:
  - preinstall continue-on-throw env gate
  - apply continue-on-fail env gate
- Added/expanded boundary-autobind with:
  - method fallback allow/deny controls
  - per-symbol entry overrides
  - epoch-based retry dedupe
  - sample-symbol autobind attempts

Evidence:

- env gates in current source:
  - `doc/wasm/js/make-real-image.mjs:167-170`
- apply-continue emission logic:
  - `git show 726c46f9` indicates `STARTUP_BINDING_MAP_APPLY_CONTINUE` addition
- boundary-autobind controls and overrides:
  - `doc/wasm/js/make-real-image.mjs:5020-5073`
  - `doc/wasm/js/make-real-image.mjs:5199-5213`
  - `doc/wasm/js/make-real-image.mjs:5232-5245`
  - `doc/wasm/js/make-real-image.mjs:5286-5334`

Impact:

- Enabled iterative autoresolution at the first required-fasload boundary without aborting immediately.
- Also introduced risk of semantically invalid manual entry overrides (see root cause section 6.3).

## 5. Session-History Behavior and Outcomes

## 5.1 Deterministic parity was achieved (pipeline is reproducible)

From `rc-7` ledger:

- Step 89 recompute parity successful: `/private/tmp/rc-7-fasload-troubleshooting.md:1572`
- Step 90 checked-in unattended script successful: `/private/tmp/rc-7-fasload-troubleshooting.md:1609`
- Step 92 negative probe hard-fail confirmed (`exit=1`): `/private/tmp/rc-7-fasload-troubleshooting.md:1700`

Direct run evidence:

- zero-byte parity diffs in positive run: `/private/tmp/step90.recompute-script.run.log`
- negative mismatch exits non-zero: `/private/tmp/step90.recompute-script.summary.txt`

Interpretation:

- The closure matrix pipeline itself is deterministic and functioning as intended.
- The remaining blocker is semantic resolution correctness, not recompute nondeterminism.

## 5.2 Unresolved frontier progression under boundary-autobind

Unresolved symbol set extracted in this lane:

- `/private/tmp/step97.unresolved-symbols.txt`
- `/private/tmp/step97.autobind-symbols.txt`

Key sequence evidence:

- autobind sequence file: `/private/tmp/step97.method-fallback.autobind-seq.txt`
- shows repeated successful autobinds across symbols, but no complete boot convergence.

Startup resolution coverage snapshot:

- `/private/tmp/step97.startup-resolution.classof1337.json`
- `resolved=589`, `unresolved=5433`, `required_unresolved=3`

Interpretation:

- Autoresolution is successfully patching many unresolved call sites, but critical required-fasload edge symbols remain unstable or semantically wrong.

## 5.3 High-value override experiments and outcomes

### Case A: `CLASS-OF=7661` (wrong semantic entry, immediate trap path)

Evidence:

- override applied: `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof7661.20260214T193611Z.log:703`
- mapped to entry: `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof7661.20260214T193611Z.log:704`
- trap stack includes `_SPmisc_ref`: `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof7661.20260214T193611Z.log:719`
- boundary reason becomes trap-after-unified-startup-binding-map-apply: `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof7661.20260214T193611Z.log:727`
- terminal failure trapped: `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof7661.20260214T193611Z.log:729`

Conclusion:

- Entry override resolved the symbol name but violated runtime semantics/ABI expectations.

### Case B: `CLASS-OF=1337` (better than 7661, but unresolved chain continues)

Evidence:

- override applied: `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof1337.20260214T193637Z.log:703`
- unresolved edge moves to `%MACPTR-DOMAIN`: `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof1337.20260214T193637Z.log:732`
- autobind cannot resolve `%MACPTR-DOMAIN`: `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof1337.20260214T193637Z.log:733`
- repeats unresolved `%MACPTR-DOMAIN`: `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof1337.20260214T193637Z.log:759`
- terminal rc path remains `-7`: `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof1337.20260214T193637Z.log:771`

Conclusion:

- Better semantic fit than 7661, but not sufficient to close the required-fasload unresolved frontier.

### Case C: `%MACPTR-DOMAIN=1338` (bad low-level override, memory trap)

Evidence:

- override applied: `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof1337-macptr1338.20260214T193747Z.log:733`
- first trap is `memory access out of bounds`: `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof1337-macptr1338.20260214T193747Z.log:749`
- boundary reason trap-after-unified-startup-binding-map-apply: `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof1337-macptr1338.20260214T193747Z.log:757`
- secondary hard trap via `_SPmisc_alloc`: `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof1337-macptr1338.20260214T193747Z.log:770`
- terminal trapped fail: `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof1337-macptr1338.20260214T193747Z.log:781`

Conclusion:

- This is a concrete wrong-entry override: name is resolved, runtime semantics are invalid.

### Case D: deeper stack-path overrides (`ON-ANY-TSP-STACK`, `%PTR-TO-VSTACK-P`) still end rc=-7

Evidence:

- unresolved shifted to `ON-ANY-TSP-STACK`: `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof1337-getfptr5681-macptr4709-stackblock-vstackptr5692.20260214T194928Z.log:883`
- override for `ON-ANY-TSP-STACK`: `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof1337-getfptr5681-macptr4709-stackblock-vstackptr5692.20260214T194928Z.log:884`
- unresolved shifted to `%PTR-TO-VSTACK-P`: `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof1337-getfptr5681-macptr4709-stackblock-vstackptr5692.20260214T194928Z.log:913`
- override for `%PTR-TO-VSTACK-P`: `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof1337-getfptr5681-macptr4709-stackblock-vstackptr5692.20260214T194928Z.log:914`
- final reason changes to generic failed-after-unified-startup-binding-map-apply (no unresolved symbol captured): `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof1337-getfptr5681-macptr4709-stackblock-vstackptr5692.20260214T194928Z.log:943`
- terminal still `rc=-7`: `/private/tmp/boot-only.trace.make-root-image.override-canon1072-classof1337-getfptr5681-macptr4709-stackblock-vstackptr5692.20260214T194928Z.log:980`

Conclusion:

- Boundary-autobind can advance the frontier but not yet fully close it; unresolved class transitions into non-symbol rc-fail.

## 6. Root-Cause Classification

## 6.1 Primary root cause

Primary class: **missing/incorrectly-resolved function symbol at required-fasload boundary**, specifically unresolved function designators (`nfn_entry=-1`) that survive pre-fasload map apply and surface at first required fasload.

Why this is primary:

- Boundary reason repeatedly reports `required-fasload-unresolved-function-symbol-after-unified-startup-binding-map-apply` with explicit symbols (for example `%MACPTR-DOMAIN`, `ON-ANY-TSP-STACK`, `%PTR-TO-VSTACK-P`).
- Startup map apply status in these runs is still `pass`; failure occurs after entering required fasload.

## 6.2 Secondary root cause

Secondary class: **wrong package namespace at designator time** (canonicalization issue).

Why:

- Resolver explicitly carries package canonicalization/override mechanisms, including `TOPLEVEL` KEYWORD-to-CCL mapping and pre-fasload package fallback (`doc/wasm/js/bootstrap-function-resolver.mjs:18-23`, `doc/wasm/js/bootstrap-function-resolver.mjs:25-33`, `doc/wasm/js/bootstrap-function-resolver.mjs:833-894`).
- Presence of this machinery indicates package drift was an active observed failure mode.

Status:

- Partially mitigated by rewrite/canonicalization; not sufficient alone to fully boot.

## 6.3 Tertiary root cause (introduced by manual intervention path)

Tertiary class: **wrong entry override (semantic/ABI mismatch)**.

Why:

- Explicit overrides can force symbol->entry binding even when metadata/package matching would avoid it.
- Demonstrated bad outcomes:
  - `CLASS-OF=7661` triggers `_SPmisc_ref` trap.
  - `%MACPTR-DOMAIN=1338` triggers out-of-bounds and `_SPmisc_alloc` traps.

Status:

- This is not the original root cause, but it is a major risk introduced by aggressive override-based autoresolution.

## 6.4 Not root cause

- Deterministic recompute/parity pipeline itself is not root cause (Step 89/90/93 parity and hard-fail checks all behave correctly).

## 7. Direct Answer: “Missing symbol / wrong package / wrong entry?”

Most accurate classification for current state:

1. **Missing symbol / unresolved function designator at boundary**: yes, this is the primary blocker.
2. **Wrong package**: yes, present as a contributing class; canonicalization reduced but did not eliminate failures.
3. **Wrong entry override**: yes, appears when manual entry overrides force semantically invalid functions; this creates trap regressions.

So the root cause is not a single label. It is a staged failure:

- unresolved designator frontier (primary),
- partly driven by namespace/package mismatches (secondary),
- and made worse by incorrect manual entry overrides during autowire experiments (tertiary).

## 8. Autoresolution Changes Inventory (Consolidated)

Concrete changes made in this investigation branch/session that affect autoresolution behavior:

1. bootstrap function resolver with ambiguity-aware metadata lookup.
2. pre-toplevel strict gate and const-pool rewrite gate diagnostics.
3. startup-binding-map artifact ownership for required-callable seeding.
4. runtime probe fallback for resolver misses when metadata is insufficient.
5. required-fasload boundary classifier (`unresolved-symbol` vs `trap` vs `rc-fail`) with startup map payload carry-through.
6. env-gated diagnostic continuation:
   - preinstall continue-on-throw,
   - apply continue-on-fail.
7. boundary-autobind engine:
   - dynamic unresolved symbol capture,
   - package candidate probing,
   - method fallback,
   - sample-symbol sweeps,
   - map mutation + re-apply in-loop.
8. explicit entry override parsing (`CCL_WASM_BOUNDARY_AUTOBIND_ENTRY_OVERRIDES`) for forced symbol->entry mapping.
9. reproducibility productization (`scripts/wasm/recompute-resume-closure-matrix.sh`) to distinguish semantic failure from nondeterminism.

## 9. Practical Implication for Boot Recovery

Given the evidence, the shortest path to stable boot is:

- treat entry overrides as last resort and require semantic validation before accepting them,
- prioritize resolver/package corrections and required-callable closure expansion,
- keep boundary-autobind enabled for discovery but gate override acceptance on repeated trap-free runs,
- continue using deterministic recompute parity checks to ensure investigative changes are semantically, not procedurally, driven.

## 10. Explicit Answer to Your Meta-Question

No. The previous version captured root-cause classes and change history, but it did not include a full counterfactual section listing the exact data that, if available up front, would have prevented most of the dead ends and trap-inducing overrides.

This amendment adds that section and a results-first deterministic data wish list.

## 11. Lessons Learned: What Exact Missing Information Cost Time

The failures during this and recent sessions were mostly not due to missing tooling, but due to missing authoritative data.

### 11.1 Missing symbol identity truth

What was missing:

- A stable symbol identity record (not just text names), including package lineage and interning lifecycle.

What this caused:

- We repeatedly treated text-level symbol equality as identity.
- We pursued unresolved symbols reactively at boundary time instead of proving symbol readiness earlier.

What would have been avoided:

- Large parts of the iterative unresolved frontier chase (`CLASS-OF` -> `%MACPTR-DOMAIN` -> `ON-ANY-TSP-STACK` -> `%PTR-TO-VSTACK-P`).

### 11.2 Missing entry semantic truth

What was missing:

- A machine-readable contract that says which entry is semantically valid for each function symbol (ABI, calling convention, stack discipline, ownership constraints).

What this caused:

- We had to trial unsafe manual entry overrides.
- Wrong overrides succeeded at binding time but failed at runtime (`_SPmisc_ref`, `_SPmisc_alloc`, OOB).

What would have been avoided:

- `CLASS-OF=7661` trap lane and `%MACPTR-DOMAIN=1338` trap lane.

### 11.3 Missing package graph and canonicalization ground truth

What was missing:

- A complete package topology dataset with import/export/use/shadow/nickname state by phase.

What this caused:

- Package rewrites and fallback logic had to be inferred and evolved in-flight.
- Ambiguity between “wrong package” and “missing symbol” remained longer than necessary.

What would have been avoided:

- Overuse of package heuristics and fallback toggles.

### 11.4 Missing required-callable closure completeness proof

What was missing:

- A canonical, phase-accurate list of all callables that must be interned and callable by first required fasload.

What this caused:

- Required callable closure was treated as an incremental discovery problem.
- Boundary-autobind was forced to act as discovery + repair simultaneously.

What would have been avoided:

- Many boundary retries that only shifted the unresolved frontier.

### 11.5 Missing const-pool semantic graph

What was missing:

- A full semantic index of const-pool refs: symbol designators, package expectations, callable expectations, and transitive closure.

What this caused:

- We relied on runtime specref diagnostics for dependency discovery.
- We discovered critical edges late (after entering required fasload).

What would have been avoided:

- Late-cycle unresolved function discovery and trial-and-error reseeding.

### 11.6 Missing “genuine interned” gate signal

What was missing:

- A definitive boolean/attestation per required symbol: “interned and stable in real package for this phase.”

What this caused:

- No clean decision boundary for bypass/autobind retirement.

What would have been avoided:

- Extended coexistence of true resolution and bypass-style recovery mechanisms.

### 11.7 Missing image corruption early-warning dataset

What was missing:

- Pre-save and post-save integrity assertions for critical object classes, package tables, and callable cells.

What this caused:

- Safety depended too much on absence of obvious traps instead of direct integrity evidence.

What would have been avoided:

- Ambiguity around whether a run is merely “non-crashing” versus “semantically clean and save-safe.”

## 12. Deterministic Data Wish List (Results-First, Feasibility Ignored)

This is the complete “if we had this, we would stop guessing” dataset set.

### 12.1 Symbol and package identity datasets

1. `symbol_identity_registry.v1.jsonl`
- Required fields:
  - `symbol_uid` (stable, content-addressed or compiler-assigned)
  - `print_name_utf8`
  - `home_package_uid`
  - `creation_phase`
  - `declared_role` (`function`, `special`, `type`, `macro`, etc)
  - `source_origin` (file/form digest)
  - `current_package_uid_by_phase`
  - `extern_status_by_phase`
- Result unlocked:
  - Eliminate text-name ambiguity across phases.

2. `package_graph_ledger.v1.json`
- Required fields:
  - `package_uid`, `canonical_name`, `nicknames`
  - `uses`, `used_by`, `imports`, `exports`, `shadows`
  - `phase_visibility`
  - `readtable_case_policy`
- Result unlocked:
  - Deterministic package canonicalization; no heuristic package fallback.

3. `interning_event_stream.v1.jsonl`
- Required fields:
  - `event_id`, `phase`, `op` (`intern`, `import`, `export`, `shadow`, `unintern`)
  - `package_uid`, `symbol_uid`
  - `source_form_digest`
  - `monotonic_seq`
- Result unlocked:
  - Exact “genuinely interned” proof for each required symbol.

### 12.2 Function entry semantic datasets

4. `function_entry_semantics.v1.jsonl`
- Required fields:
  - `entry_uid`, `entry_index`, `symbol_uid`, `package_uid`
  - `call_abi_kind`, `gc_root_policy_mode`
  - `nargs_min`, `nargs_max`, `rest_allowed`
  - `stack_effect_contract` (vsp/tsp/csp constraints)
  - `alloc_behavior`, `subprims_touched`
  - `valid_boot_phases`
- Result unlocked:
  - Wrong-entry overrides become impossible to accept silently.

5. `entry_alias_evolution_map.v1.jsonl`
- Required fields:
  - `entry_uid`
  - `entry_index_by_build_hash`
  - `semantics_hash`
- Result unlocked:
  - Cross-build stability without brittle raw index assumptions.

6. `designator_resolution_truth_table.v1.jsonl`
- Required fields:
  - `phase`, `input_name`, `input_package`
  - `canonical_symbol_uid`
  - `resolved_entry_uid`
  - `status` (`resolved`, `ambiguous`, `missing`)
  - `allowed_reason_codes`
- Result unlocked:
  - Resolver behavior is pre-declared, not inferred from failures.

### 12.3 Closure and const-pool datasets

7. `required_callable_closure_contract.v1.json`
- Required fields:
  - `required_symbol_uid`
  - `required_package_uid`
  - `required_by_phase`
  - `required_entry_uid`
  - `must_be_interned_by_phase`
  - `must_be_callable_by_phase`
- Result unlocked:
  - Up-front closure completeness proof before required fasload begins.

8. `const_pool_semantic_graph.v1.jsonl`
- Required fields:
  - `owner_entry_uid`, `const_index`
  - `payload_kind`
  - `referenced_symbol_uid` (if any)
  - `referenced_entry_uid` (if any)
  - `required_class`
  - `origin_form_digest`
  - `dependency_edges`
- Result unlocked:
  - Deterministic transitive callable discovery, zero boundary-time surprises.

9. `fasl_designator_manifest.v1.jsonl`
- Required fields:
  - `fasl_path`, `offset`, `designator_kind`
  - `symbol_uid`, `package_uid`
  - `expected_resolution_policy` (`required`, `deferred`)
  - `expected_entry_uid` (if required)
- Result unlocked:
  - No speculative designator rewrites.

### 12.4 Runtime determinism and forensic datasets

10. `boot_phase_state_machine.v1.json`
- Required fields:
  - states, transitions, guard invariants, required events
  - fail reason codes and required diagnostics payload fields
- Result unlocked:
  - Deterministic phase progression and strict fail classification.

11. `boundary_forensic_packet.v1.jsonl`
- Required fields per failure:
  - `phase`, `reason`, `rc`, `trap_message`
  - `arg_z_symbol_uid`, `arg_z_package_uid`
  - `nfn_entry_uid` (nullable)
  - `pending_throw_symbol_uid`
  - `startup_map_digest`
  - `resolver_decision_id`
- Result unlocked:
  - Immediate, unambiguous root-cause classification.

12. `resolver_decision_log.v1.jsonl`
- Required fields:
  - input designator
  - candidate set (ordered)
  - rejection reasons per candidate
  - final decision and confidence class
- Result unlocked:
  - Removes “why did this entry/package get picked?” uncertainty.

13. `autobind_action_ledger.v1.jsonl`
- Required fields:
  - unresolved symbol uid/package uid
  - selected source (`metadata`, `method-fallback`, `override`)
  - selected entry uid/index
  - semantic compatibility verdict
  - rollback token
- Result unlocked:
  - Autobind becomes audit-safe and reversible.

14. `memory_layout_abi_manifest.v1.json`
- Required fields:
  - subtag table, object header contracts, vector layouts
  - `macptr`/foreign object invariants
  - subprim preconditions by opcode
- Result unlocked:
  - Prevents trap-only debugging loops around low-level layout violations.

### 12.5 Image integrity and no-corruption datasets

15. `image_integrity_manifest.v1.json`
- Required fields:
  - object-space checksums by segment
  - package table checksum
  - symbol table checksum
  - fcell/vcell coherence counts
  - class/metaobject graph invariants
- Result unlocked:
  - Positive proof that saved image is not merely “booted” but structurally sound.

16. `package_correctness_attestation.v1.json`
- Required fields:
  - for each required symbol uid: expected package uid vs actual package uid
  - interned/external status at save time
- Result unlocked:
  - Guarantees “everything in its real package.”

17. `callable_attestation.v1.json`
- Required fields:
  - for each required callable symbol uid:
    - expected entry uid
    - actual fcell entry uid
    - ABI compatibility verdict
    - phase timestamp
- Result unlocked:
  - Guarantees callable identity correctness at save boundary.

18. `save_preflight_hard_gates.v1.json`
- Required fields:
  - list of mandatory assertions
  - pass/fail result per assertion
  - blocking severity
- Result unlocked:
  - Prevents saving known-corrupt or semantically unresolved images.

### 12.6 Build/environment determinism datasets

19. `build_provenance_lock.v1.json`
- Required fields:
  - commit SHAs, wasm binary digests, toolchain versions, compile flags
  - generated artifact digests (runtime modules, contracts, scope maps)
- Result unlocked:
  - Cross-run determinism tied to exact binaries and inputs.

20. `execution_envelope.v1.json`
- Required fields:
  - env vars, locale, timezone, memory sizing policy, seed values
  - explicit list of enabled diagnostics and bypasses
- Result unlocked:
  - Removes hidden run-to-run behavior drift.

## 13. Precise Minimal Data Required to Remove Bypass Entirely

If the goal is specifically to eliminate bypass/autobind after genuine interning, these datasets are minimally required:

1. `symbol_identity_registry.v1.jsonl`
2. `package_graph_ledger.v1.json`
3. `interning_event_stream.v1.jsonl`
4. `function_entry_semantics.v1.jsonl`
5. `required_callable_closure_contract.v1.json`
6. `const_pool_semantic_graph.v1.jsonl`
7. `callable_attestation.v1.json`
8. `package_correctness_attestation.v1.json`
9. `image_integrity_manifest.v1.json`
10. `save_preflight_hard_gates.v1.json`

Without this set, removing bypass is faith-based. With this set, bypass retirement becomes a deterministic gate decision.

## 14. Deterministic “No Corruption + Real Package + No Bypass” Acceptance Contract

Bypass and autobind may be removed only when all conditions are true for `N` consecutive full runs (recommend `N >= 10`):

1. `required_unresolved == 0` in startup resolution output.
2. `REQUIRED_FASLOAD_BOUNDARY` never reports:
   - `required-fasload-unresolved-function-symbol-after-unified-startup-binding-map-apply`
   - `required-fasload-trap-after-unified-startup-binding-map-apply`
3. Startup map source never includes `+required-fasload-boundary-autobind`.
4. No `boundary-autobind override` events appear.
5. Every required callable attests expected entry uid == actual entry uid.
6. Every required symbol attests expected package uid == actual package uid.
7. Image integrity manifest checksums and invariants are stable and pass.
8. Save preflight hard gates pass with zero waived failures.

If any condition fails, bypass retirement is rejected.

## 15. Counterfactual Mapping: What Would Have Prevented the Main Pain Points

1. Problem: `CLASS-OF=7661` looked syntactically valid, trapped at runtime.
- Missing data that would have prevented it:
  - `function_entry_semantics.v1.jsonl` with semantic compatibility checks.
  - `callable_attestation.v1.json` pre-apply dry-run verifier.

2. Problem: `%MACPTR-DOMAIN` remained unresolved after improving `CLASS-OF`.
- Missing data that would have prevented it:
  - `required_callable_closure_contract.v1.json`
  - `const_pool_semantic_graph.v1.jsonl` with full transitive edge closure.

3. Problem: `%MACPTR-DOMAIN=1338` produced OOB and `_SPmisc_alloc` traps.
- Missing data that would have prevented it:
  - low-level `memory_layout_abi_manifest.v1.json`
  - entry ABI + subprim precondition contracts in `function_entry_semantics.v1.jsonl`.

4. Problem: repeated unresolved frontier shifts (`ON-ANY-TSP-STACK`, `%PTR-TO-VSTACK-P`) without clean convergence criteria.
- Missing data that would have prevented it:
  - precomputed `designator_resolution_truth_table.v1.jsonl`
  - hard closure completeness gate from `required_callable_closure_contract.v1.json`.

5. Problem: uncertainty about “safe to save image” versus “did not trap yet.”
- Missing data that would have prevented it:
  - `image_integrity_manifest.v1.json`
  - `save_preflight_hard_gates.v1.json`.

## 16. Implementation Plan: Dynamic-Resolution Replacement Path (Bounded, Non-Miniscule Increments)

This section appends an execution plan that replaces runtime/autobind heuristics with instrumented Lisp truth artifacts consumed by JS. It is intentionally staged in bounded increments, with explicit scope limits per increment and without constant testing after every small edit.

### 16.1 Goals and Non-Goals

Goals:

1. Replace boundary-time dynamic autoresolution with deterministic, precomputed truth from instrumented Lisp execution.
2. Produce richer manifests/contracts that JS can consume without probing/fallback.
3. Preserve determinism and auditability while reducing manual override risk.
4. Remove dead fallback code as strict sources become authoritative.

Non-goals:

1. Do not redesign the full runtime architecture.
2. Do not attempt to collect all 20 wish-list datasets in a single wave.
3. Do not run full end-to-end tests after each micro-change.

### 16.2 Delivery Principle: “Three-Lane Ownership”

1. `collect` lane (Lisp-instrumented, non-publishing)
- Executes bootstrap/load flow.
- Emits truth events/artifacts.
- May keep diagnostic fallbacks for discovery only.

2. `compile-contract` lane (artifact synthesis)
- Converts raw truth into canonical contract files.
- Performs schema and closure checks.
- Produces publish inputs.

3. `publish` lane (strict)
- Consumes only canonical artifacts.
- No runtime probe, no boundary-autobind, no manual entry overrides.
- Hard-fails on any unresolved/ambiguous required item.

### 16.3 Minimal Artifact Set for First Replacement Wave

Deliver these first (already identified as minimal in Section 13):

1. `symbol_identity_registry.v1.jsonl`
2. `package_graph_ledger.v1.json`
3. `interning_event_stream.v1.jsonl`
4. `function_entry_semantics.v1.jsonl`
5. `required_callable_closure_contract.v1.json`
6. `const_pool_semantic_graph.v1.jsonl`
7. `callable_attestation.v1.json`
8. `package_correctness_attestation.v1.json`
9. `image_integrity_manifest.v1.json`
10. `save_preflight_hard_gates.v1.json`

Rationale:
- This set is sufficient to retire bypass paths deterministically.
- Additional datasets can be layered later without blocking replacement.

### 16.4 Bounded Increments (Milestones)

Each milestone is intentionally larger than a tiny patch, but still bounded and reviewable. Testing cadence is milestone-based, not per commit.

#### Milestone M1: Event Substrate in Lisp (No Behavior Change)

Scope:

1. Add a Lisp-side event emitter with stable schema envelope:
- `schema_version`
- `event_type`
- `phase`
- `monotonic_seq`
- payload object

2. Add sinks:
- file sink (JSONL)
- optional stdout mirror for diagnostics

3. Add feature flags:
- `CCL_WASM_STARTUP_TRUTH_COLLECT=1`
- `CCL_WASM_STARTUP_TRUTH_OUT=<path>`

4. Instrument only passive events first:
- package create/use/import/export/shadow events
- intern/unintern events
- symbol identity observations

Out of scope:
- No resolver decisions yet.
- No JS consumption changes yet.

Acceptance outputs:
- Non-empty `symbol_identity_registry` + `package_graph_ledger` + `interning_event_stream` derivable from events.

Test cadence for M1:
- 1 focused run after implementation complete.
- 1 rerun for determinism check.
- No intermediate full-suite runs.

#### Milestone M2: Callable and Entry Semantics Capture

Scope:

1. Instrument callable-binding events:
- symbol -> fcell updates
- entry index assignment
- phase/time of assignment

2. Emit semantic compatibility fields where available:
- nargs limits/rest
- ABI/calling class
- stack/alloc invariants (as currently observable)

3. Build `function_entry_semantics.v1.jsonl` and `callable_attestation.v1.json` from M1+M2 stream.

Out of scope:
- No publish-lane gating changes yet.

Acceptance outputs:
- Required callables in contract have attested entry targets or explicit unresolved reasons.

Test cadence for M2:
- 1 bounded bootstrap run.
- 1 targeted negative fixture (known bad entry) to confirm semantic rejection signal.

#### Milestone M3: Const-Pool and Required-Closure Compiler

Scope:

1. Record const-pool designator resolution events with ownership:
- owner entry
- const index
- symbol/package designator
- resolution status/reason

2. Compile transitive closure into:
- `const_pool_semantic_graph.v1.jsonl`
- `required_callable_closure_contract.v1.json`

3. Add compile-time closure checks:
- required unresolved must be zero for publish candidates
- ambiguities explicit and blocking

Out of scope:
- Runtime path not yet stripped.

Acceptance outputs:
- Closure compiler emits deterministic graph/contract and explicit blockers.

Test cadence for M3:
- 1 full collect->compile run.
- 1 rerun with digest compare for contract determinism.

#### Milestone M4: JS Strict Consumption Path (Dual-Path Period)

Scope:

1. Add JS strict input mode:
- consume canonical artifacts only
- disable runtime probing and boundary-autobind in strict mode

2. Add strict hard gates:
- required unresolved = 0
- expected package == actual package
- expected entry == actual callable attestation

3. Keep legacy/dynamic path behind explicit diagnostic mode flag for temporary fallback.

Out of scope:
- Legacy code deletion deferred until M5.

Acceptance outputs:
- publish-mode run either succeeds cleanly or fails with explicit contract reasons.

Test cadence for M4:
- 1 strict happy-path run.
- 1 strict negative-path run (intentional contract mismatch).

#### Milestone M5: Retirement of Dynamic Autoresolution + Dead Code Removal

Scope:

1. Remove/disable in publish mode:
- boundary-autobind mutation path
- runtime-probe resolver fallback
- manual entry override acceptance

2. Delete dead/unused fallback code once strict path is proven.

3. Preserve diagnostic collection lane for forensic use, isolated from publish path.

Acceptance outputs:
- Publish lane has no dynamic resolution dependencies.
- Dead code removed and references cleaned.

Test cadence for M5:
- 1 end-to-end strict publish run.
- 1 repeat stability run.
- No broad unrelated suite expansion.

### 16.5 Testing Policy (Explicitly Non-Constant)

To satisfy “NO CONSTANT TESTING,” use this cadence:

1. No full-run tests during intra-milestone coding.
2. Run tests only at milestone boundary when code is feature-complete for that milestone.
3. For each milestone:
- one primary verification run
- one repeat/determinism run
- one targeted negative only where specified
4. Defer broader regression suites to M5 completion.

### 16.6 Work Package Breakdown (Actionable)

WP-1 (Lisp instrumentation runtime)
1. Add event envelope writer utility.
2. Add event sink lifecycle (open/flush/close).
3. Add macros/helpers to emit events with minimal call-site noise.

WP-2 (Lisp hook points)
1. Package operations hooks.
2. Interning hooks.
3. Callable/fcell binding hooks.
4. Optional const-pool resolver decision hooks.

WP-3 (Artifact compiler scripts)
1. JSONL -> normalized registries.
2. Closure derivation and required-callable contract emitter.
3. Attestation generators.
4. Deterministic sort/canonical JSON writer.

WP-4 (JS strict ingestion)
1. Parse/load canonical artifacts.
2. Enforce strict gates.
3. Emit explicit failure taxonomies (machine-readable).

WP-5 (Retirement cleanup)
1. Remove dead fallback code paths.
2. Remove now-unused env flags in publish path.
3. Update docs/spec/checklists and runbooks.

### 16.7 Exit Criteria by Milestone

M1 exit:
- Event pipeline emits stable identity/package/intern streams.

M2 exit:
- Callable and entry attestation artifacts emitted with explicit unresolved reasons.

M3 exit:
- Required closure contract generated with deterministic digest and blocker list.

M4 exit:
- JS strict mode runs exclusively from artifacts and hard-fails correctly.

M5 exit:
- Publish lane free of dynamic autoresolution and dead fallback code removed.

### 16.8 Risk Register and Mitigations

Risk 1: Instrumentation overhead destabilizes bootstrap.
- Mitigation: buffered sink + event sampling toggle for non-required classes.

Risk 2: Incomplete hook coverage misses critical symbol transitions.
- Mitigation: closure compiler marks provenance gaps as blocking; do not silently default.

Risk 3: Semantic ABI fields unavailable at first.
- Mitigation: emit `unknown` with explicit blockers for required callables; never auto-pass unknown required semantics.

Risk 4: Dual-path drift during M4.
- Mitigation: publish mode disallows fallback by policy; diagnostic mode isolated.

### 16.9 Governance: What Is Forbidden During Replacement

1. No new manual entry override shortcuts added to publish path.
2. No package-default fallback to `COMMON-LISP` for required callables.
3. No silent ambiguity resolution for required symbols.
4. No publish artifact update when strict gates fail.

### 16.10 Immediate Next Step (First Increment Start)

Start with M1 WP-1/WP-2 only:

1. Implement Lisp event envelope + file sink.
2. Instrument package/intern/symbol identity events.
3. Emit `startup_truth_v1.jsonl` from first-pass boot collect lane.
4. Defer all strict JS behavior changes until M1 artifact quality is confirmed.

This provides a bounded first delivery with high information yield and minimal destabilization.

### 16.11 Status Update (2026-02-14, post-M1 collect-lane patchset)

Latest implementation commit:
- `d06e0b96be542e4f6058a8013f4e7c1b0aae9e39` (`wasm: stabilize startup truth collect emission path`)

What changed in this update:
1. Kernel-side startup-truth intern-event emission now has a reentrancy guard and preserves caller pending-throw state:
- `lisp-kernel/wasm-kernel-stubs.c` (`wasm_emit_startup_truth_intern_event`)
2. JS collect lane primes `doc/wasm/startup_truth_v1.jsonl` in persistence and seeds one schema-valid record before boundary execution:
- `doc/wasm/js/make-real-image.mjs`

Milestone-boundary verification (primary + repeat) on 2026-02-14:
- Run logs:
  - `/private/tmp/m1d.run1.final.log`
  - `/private/tmp/m1d.run2.final.log`
- Collected outputs:
  - `/private/tmp/m1d.startup_truth.run1.jsonl`
  - `/private/tmp/m1d.startup_truth.run2.jsonl`

Observed outcomes:
1. Previous collect-lane extractor blocker is removed:
- No more `failed to open doc/wasm/startup_truth_v1.jsonl in persistence store`.
- Both runs emit `STARTUP_TRUTH_COLLECT {"status":"ok", ...}`.
2. `startup_truth_v1.jsonl` is now produced and deterministic across run1/run2:
- file size: `196` bytes in both runs
- `cmp` equality: pass
3. First required fasload boundary remains a hard blocker:
- still fails at `l1-fasls/l1-cl-package.lafsl`
- trap now observed as `table index is out of bounds`
- boundary reason remains `required-fasload-trap-after-unified-startup-binding-map-apply`
4. Current emitted truth payload is minimal (seed event), so full M1 passive event stream quality is still pending.

Revised M1 status:
- Partially complete:
  - collect-lane file emission path is now functional and deterministic.
- Still pending for full M1 acceptance:
  - collect a non-trivial passive event stream (package/intern/symbol-identity) before first required-fasload trap, or make that trap path emit enough events to satisfy M1 artifact quality.

Immediate next step (unchanged milestone scope, refined blocker focus):
1. Keep M1 scope (no strict publish behavior changes).
2. Resolve first required-fasload trap path enough to allow passive event hooks to execute.
3. Re-run two-run boundary cadence and confirm `startup_truth_v1.jsonl` is non-empty from runtime instrumentation, not only seeded.

### 16.12 Status Update (2026-02-14, post-M1e intern-callability guard attempt)

What changed in this update:
1. Added a callability guard before invoking `%WASM-STARTUP-TRUTH-INTERN-EVENT`:
- `lisp-kernel/wasm-kernel-stubs.c` (`wasm_emit_startup_truth_intern_event`)
- Guard now requires the symbol fcell to be non-UDF and a callable misc object (`function`/`pseudofunction`) before `wasm_funcall5`.
2. Rebuilt wasm kernel artifact:
- `doc/wasm/js/wasmcl.wasm`

Milestone-boundary verification (primary + repeat) on 2026-02-14:
- Run logs:
  - `/private/tmp/m1e.run1.final.log`
  - `/private/tmp/m1e.run2.final.log`
- Collected outputs:
  - `/private/tmp/m1e.startup_truth.run1.jsonl`
  - `/private/tmp/m1e.startup_truth.run2.jsonl`

Observed outcomes:
1. First required fasload boundary behavior is unchanged:
- still fails at `l1-fasls/l1-cl-package.lafsl`
- trap remains `table index is out of bounds`
- boundary reason remains `required-fasload-trap-after-unified-startup-binding-map-apply`
2. Collect output remains deterministic and unchanged:
- file size: `196` bytes in both runs
- line count: `1` in both runs
- `cmp` equality: pass
3. Runtime passive event stream is still not present before the boundary trap:
- output remains the seeded `collect-prime` record only.

Revised M1 status:
- Still partially complete:
  - collect-lane file emission path remains functional/deterministic.
- Still blocked for full M1 acceptance:
  - non-trivial passive package/intern/symbol-identity event emission has not yet been observed.

Immediate next step (same milestone scope):
1. Keep M1 scope and collect lane behavior unchanged.
2. Investigate the first required-fasload trap path directly (`wasm_fasload_path`/subprim call chain) instead of startup-truth callback callability.
3. Re-run boundary cadence once a trap-path change is in place and require runtime-generated (not seeded-only) truth events.

### 16.13 Status Update (2026-02-14, post-M1k2 baseline-truth emission + rebuild-orchestrator)

What changed in this update:
1. Added a canonical sync rebuild orchestrator:
- `scripts/wasm/rebuild-everything.sh`
- documented in `doc/wasm/project-overview.md` under “Canonical rebuild command”
- includes versioned artifact refresh (`doc/wasm/bootstrap-l0-contract.v1.json`, `doc/wasm/startup-symbol-scope.source_scope_v1.json`)
2. Stabilized collect-lane truth emission by adding kernel-side baseline JSONL writes during collect configuration:
- `lisp-kernel/wasm-kernel-stubs.c` (`wasm_emit_startup_truth_collect_baseline`, called from `wasm_configure_startup_truth_collect`)
3. Removed failing collect-lane runtime preload attempt from JS startup path:
- `doc/wasm/js/make-real-image.mjs`

Milestone-boundary verification (primary + repeat) on 2026-02-14:
- Run logs:
  - `/private/tmp/m1k2.run1.final.log`
  - `/private/tmp/m1k2.run2.final.log`
- Collected outputs:
  - `/private/tmp/m1k2.startup_truth.run1.jsonl`
  - `/private/tmp/m1k2.startup_truth.run2.jsonl`

Observed outcomes:
1. Collect extraction remains healthy:
- both runs report `STARTUP_TRUTH_COLLECT {"status":"ok", ...}`
- both outputs exist and are deterministic (`12` lines, `3004` bytes, `cmp` pass)
2. Truth payload is now non-trivial before termination:
- includes seed + kernel-baseline `intern` and `symbol-identity-observe` events
- sample symbols: `%FASLOAD`, `%FASL-OPEN`, `%SIMPLE-FASL-OPEN`, `INTERN`, `DEFAULT`
3. First required fasload remains the hard blocker:
- still fails at `l1-fasls/l1-cl-package.lafsl`
- trap observed as `Maximum call stack size exceeded`
- boundary reason remains `required-fasload-trap-after-unified-startup-binding-map-apply`

Revised M1 status:
- Improved but still not fully accepted:
  - deterministic, non-empty startup truth collection now works in collect lane.
  - full passive package lifecycle coverage (`create/use/import/export/shadow/unintern`) is still incomplete in emitted stream.
- Hard blocker remains:
  - pre-runtime required-fasload trap prevents broader runtime-phase event capture.

Immediate next step:
1. Keep publish-path behavior unchanged.
2. Trace and fix the required-fasload trap call chain (`wasm_prepare_entry_call` -> `_SPfuncall` path) so collect runs can execute deeper instrumentation.
3. Expand passive event hooks to cover package lifecycle events once trap is unblocked.

### 16.14 Status Update (2026-02-14, post-M1k7 collect-lane pre-fasload hard-stop)

What changed in this update:
1. Restored normal startup binding-map behavior in collect lane (removed collect-only startup-map skip), so collect no longer mutates L0 setup policy.
2. Added an explicit collect-lane guard in `doc/wasm/js/make-real-image.mjs`:
- if pre-fasload L0 contract fails, collect now closes/extracts `startup_truth_v1.jsonl` and exits before required-fasload execution.
- this replaces trap-driven termination with deterministic contract-fail termination.
3. Performed full sync rebuild order to eliminate artifact skew:
- `scripts/wasm/rebuild-everything.sh --no-root-image`
- this rebuilt `wasm-boot.image`, regenerated `doc/wasm/wasm-runtime-modules.json` + `.idx`, refreshed `doc/wasm/bootstrap-l0-contract.v1.json`, and regenerated `doc/wasm/startup-symbol-scope.source_scope_v1.json`.

Milestone-boundary verification (primary + repeat) on 2026-02-14:
- Run logs:
  - `/private/tmp/m1k7.run1.final.log`
  - `/private/tmp/m1k7.run2.final.log`
- Collected outputs:
  - `/private/tmp/m1k7.startup_truth.run1.jsonl`
  - `/private/tmp/m1k7.startup_truth.run2.jsonl`

Observed outcomes:
1. First-required-fasload trap path is no longer reached in collect mode:
- no `REQUIRED_FASLOAD_BOUNDARY` emission
- no `Maximum call stack size exceeded` in run logs
2. Collect output remains deterministic and non-empty:
- both runs emit `STARTUP_TRUTH_COLLECT {"status":"ok","reason":"l0-bootstrap-contract-fail",...}`
- both outputs exist and match (`12` lines, `3055` bytes, `cmp` pass)
3. Current blocker is now explicit and earlier:
- pre-fasload L0 contract fails with `6` requirement failures (`symbol/callable/special unresolved`), then collect lane exits cleanly.

Revised M1 status:
- Improved/stabilized:
  - collect lane now fails deterministically without entering the unstable first-fasload trap path.
  - startup truth artifact extraction is preserved on fail path.
- Still pending for full M1 acceptance:
  - passive runtime package lifecycle stream remains incomplete (artifact content is still baseline-seeded rather than deep runtime event capture).

Immediate next step:
1. Resolve pre-fasload L0 contract failures (especially missing CCL symbols/specials around vector-output-stream and structure refs) so collect can progress past pre-fasload gates.
2. Once L0 gate passes, re-enable required-fasload boundary traversal under collect and validate non-baseline runtime event emission.
