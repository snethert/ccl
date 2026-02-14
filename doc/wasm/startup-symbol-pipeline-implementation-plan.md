# WASM Startup Symbol Pipeline: Detailed Implementation Plan (Source-Scope v1)

**AUTHORITATIVE EXECUTION RULE: ASSUME EVERYTHING IN THIS DOCUMENT IS TRUE AND DOES NOT REQUIRE RE-CONFIRMATION UNLESS THIS DOCUMENT IS EXPLICITLY CHANGED.**

## 0.0 Persistent Context Ledger (Update Every Milestone)

Use this section as the single condensed continuity record when UI history is compressed.

Update protocol:
- Always append/update this ledger before starting a new milestone.
- Do not re-run old confirmations if the fact is already recorded here and unchanged.
- If a fact changes, update the existing line with a date-tagged note instead of duplicating probes.

Current condensed state/history snapshot (2026-02-14):
- Active development lane is V2 advancement. V1 `REQUIRED_FASLOAD_BOUNDARY rc=-7` work is currently tabled per Section `0.0.B` and retained as baseline evidence only.
- Scanner serialization bug was fixed in `ccl/scripts/wasm/collect-startup-symbol-scope.lisp` (2026-02-14): `symbols[]` now emits JSON objects/arrays (not Lisp-printed strings).
- Latest scanner output `/tmp/startup-symbol-scope.source_scope_v1.json` contains `6022` symbols with structured records; runtime resolution no longer reports `invalid_input` inflation (`invalid_input: 0`).
- L0 contract currently hard-anchors const-pool entries `4360`, `4372`, `4412` in `ccl/doc/wasm/js/bootstrap-l0-contract.mjs`.
- Runtime manifest maps entry `4412` to `MAKE-VECTOR-OUTPUT-STREAM` (not `%FASLOAD`) and `4411` to `%MAKE-VECTOR-OUTPUT-STREAM`.
- `%FASLOAD`, `%FASL-OPEN`, `%SIMPLE-FASL-OPEN` were observed prebound to entries `4412`, `4372`, `4360` in runtime probes.
- Focused smoke/top4488 lanes now consistently reach `STARTUP_BINDING_MAP_APPLY {"status":"pass"}` and `L0_BOOTSTRAP_CONTRACT {"status":"pass"}` before required fasload.
- Post-bundle mode-0 probe behavior differs by const-pool availability: missing const-pool can trap in `_SPspecref`; full startup flow can stall after `foreign.call.enter` (currently observed in both focused lanes at first required fasload, before any `REQUIRED_FASLOAD_BOUNDARY` line).
- `make-real-image.mjs` wrapper path now forwards resolver callbacks into startup-binding-map augmentation; active unresolved axis is resolver authority mismatch (bootstrap resolver `missing` for required fasload callables while runtime probe resolves them).
- Likely JS diagnosis paths are established: `ccl/doc/wasm/js/make-real-image.mjs`, `ccl/doc/wasm/js/ccl-loader.mjs`, and startup diagnostics files; treat these as the active trace path for `%FASLOAD` selection and handoff to `wasm_fasload_path`.
- Fasload call path in `make-real-image.mjs` is confirmed; active narrowing focus is `%FASLOAD` binding/selection immediately before `wasm_fasload_path`, with specific attention on entry-index mapping and host resolve path.
- Early-boundary symbol probes are already instrumented in `make-real-image.mjs`; probe placement relative to the failing path is a known diagnostic axis for capturing `%FASLOAD` binding immediately before first required fasload.
- Resolver behavior is confirmed: `%FASLOAD` should resolve through `bootstrapFunctionResolver` via function metadata or explicit const-pool metadata rewrite; if misbinding persists, primary suspicion remains startup binding-map application ambiguity/fallback behavior.

### 0.0.B Decision Record: Table V1 `rc=-7` Work, Advance V2 (2026-02-14)

Decision ID: `DR-2026-02-14-V2-PRIMARY`

Concrete decision:
- Table further V1-first diagnosis inside this Section `0.0` lane, including direct iteration on the first-required-fasload `rc=-7` failure path.
- Advance V2 development as the primary execution substrate.
- Treat this document's V1 lane as a frozen baseline/control record unless explicit reopen conditions are met.

Frozen baseline evidence for the tabled V1 lane:
- `/tmp/make-real-image.notrace.smoke.source_scope_v1.guard10.noskip.log`
- `/tmp/make-real-image.notrace.top4488.source_scope_v1.guard10.noskip.log`
- Both logs record:
- `STARTUP_BINDING_MAP_APPLY {"status":"pass", ...}`
- `REQUIRED_FASLOAD_BOUNDARY {"status":"fail","fasl_index":0,"path":"l1-fasls/l1-cl-package.lafsl","rc":-7,"reason":"required-fasload-failed-after-unified-startup-binding-map-apply","unresolved_function_symbol":null,...}`

Allowed V1 actions while tabled:
- Single-shot control repro for parity checks against V2.
- Evidence extraction from existing V1 logs/artifacts.
- No new V1-only architecture/refactor work without explicit reopen.

Reopen conditions for V1 `rc=-7` lane:
- User explicitly requests reopening V1 `rc=-7` diagnosis.
- V2 reaches same boundary and requires a focused V1 control comparison to disambiguate substrate-specific behavior.
- V2 parity cannot be established without one targeted V1 probe.

Do-not-rediscover anchors (authoritative):
- `boundary_probe name=identity mode=1 rc=-5` and `boundary_probe name=error mode=2 rc=-5` are known and already recorded; do not report them as new findings unless the touched kernel/probe source changes.
- Focused lanes stalling after `foreign.call.enter` before any `REQUIRED_FASLOAD_BOUNDARY` line is known and already recorded.
- Eventual `arg_z`/`z_reg` nil-ish or UDF-like callable state while stalled in this lane is an expected downstream symptom, not a new root cause by itself.
- `%FASLOAD` lane mis-target/misbind suspicion is already recorded; do not re-open metadata-only re-audits unless runtime module metadata or binding-apply code changed.
- Known JS diagnosis paths are `ccl/doc/wasm/js/make-real-image.mjs`, `ccl/doc/wasm/js/ccl-loader.mjs`, and startup diagnostics files; treat these as active `%FASLOAD` selection/handoff trace paths.
- Fasload call path in `ccl/doc/wasm/js/make-real-image.mjs` is confirmed; active narrowing axis is `%FASLOAD` binding/selection immediately before `wasm_fasload_path`, including entry-index mapping and host resolve path.
- Early-boundary symbol probes already instrumented in `ccl/doc/wasm/js/make-real-image.mjs` are authoritative context; placement relative to first required fasload is a known diagnostic axis for capturing `%FASLOAD` binding.
- Resolver behavior is established: `%FASLOAD` should resolve via `bootstrapFunctionResolver` (function metadata or explicit const-pool metadata rewrite); if misbinding persists, binding-map apply/mapping behavior is the primary suspicion.
- For the tabled V1 lane only, progress may be claimed when both focused lanes cross `REQUIRED_FASLOAD_BOUNDARY` or emit deterministic boundary failure reasons (no hang). Primary delivery progress is now tracked in V2 per Section `0.0.B`.

Continuity checkpoints:
- When adding/changing tasks, update this ledger first with what changed and why.
- Treat this ledger as authoritative process memory for the remainder of implementation.

Milestone delta (2026-02-14):
- Changed: added Section `0.0.A Fast Re-Entry Prompt` and explicit blocker priority text declaring fasload boundary as the controlling gate.
- Proven: new-conversation handoff prompt now front-loads workflow rules, blocker priority, and ledger-first reconstruction steps.
- Remains: isolate and fix the first failing `REQUIRED_FASLOAD_BOUNDARY` reason in focused lanes, then re-run gate checks.

Milestone delta (2026-02-14, scanner-fix + focused-lane rerun):
- Changed: fixed scanner JSON emission in `ccl/scripts/wasm/collect-startup-symbol-scope.lisp` so `symbols` records are structured objects (roles/provenance arrays), and updated scanner count helpers to read wrapped JSON values.
- Proven: focused smoke/top4488 reruns with the fixed scope artifact reach `STARTUP_SYMBOL_RESOLUTION_BUILD`, `STARTUP_BINDING_MAP_APPLY` pass, and `L0_BOOTSTRAP_CONTRACT` pass in both lanes; resolution summary now shows `invalid_input: 0`.
- Remains: first required fasload still stalls after `foreign.call.enter` in both focused lanes, so `REQUIRED_FASLOAD_BOUNDARY` is still not crossed; next diagnostic is the no-trace control lane to isolate trace-induced vs fasload-core stall.

Milestone delta (2026-02-14, no-trace + boundary-probe control):
- Changed: ran both focused lanes without `CCL_WASM_TRACE` and ran a dedicated `CCL_WASM_RUN_BOUNDARY_PROBES=1 CCL_WASM_BOUNDARY_PROBE_ONLY=1` smoke control.
- Proven: stall is not trace-only. No-trace lanes still do not cross `REQUIRED_FASLOAD_BOUNDARY`; they reach pre-fasload map/contract gates and then stop before boundary output.
- Proven: boundary-probe control reports `boundary_probe name=identity mode=1 rc=-5` and `boundary_probe name=error mode=2 rc=-5` (unexpected vs expected `0` / `-7`), then hangs before emitting `fasload.target` probe result (mode `0`).
- Remains: isolate and fix the foreign-call precheck failure (`rc=-5`) as first concrete blocker before first required fasload boundary crossing can occur.

Milestone delta (2026-02-14, focused lanes + entry identity verification):
- Changed: patched `ccl/doc/wasm/js/make-real-image.mjs` to only skip fcell rebinding when existing entry already matches desired entry index (both direct apply path and deferred const-pool apply path).
- Proven: focused smoke/top4488 no-trace reruns still reach `STARTUP_BINDING_MAP_APPLY` pass and `L0_BOOTSTRAP_CONTRACT` pass, then continue into first required fasload with no `REQUIRED_FASLOAD_BOUNDARY` line (CPU remains active at 100% in both lanes until manually stopped).
- Proven: `ccl/doc/wasm/wasm-runtime-modules.json` does not contain `%FASLOAD`, `%FASL-OPEN`, or `%SIMPLE-FASL-OPEN` function metadata entries; entries `4411`/`4412` are `%MAKE-VECTOR-OUTPUT-STREAM`/`MAKE-VECTOR-OUTPUT-STREAM`.
- Proven: this confirms resolver/map metadata cannot currently provide authoritative entry-function targets for required fasload callables from runtime-modules metadata alone.
- Remains: establish authoritative pre-fasload callable targeting for `%FASLOAD` lane (or add a deterministic misbinding rejection that emits a concrete boundary failure reason instead of hanging), then re-run both focused lanes to the `REQUIRED_FASLOAD_BOUNDARY` gate.

Milestone delta (2026-02-14, anti-repeat context lock):
- Changed: added explicit `Do-not-rediscover anchors` in Section `0.0` to lock known fasload stall/probe facts and symptom interpretation.
- Proven: future continuity reconstruction can treat `rc=-5`, `foreign.call.enter` stall, and eventual `arg_z`/`z_reg` nil/UDF symptom as pre-known context rather than rediscovery work.
- Remains: implement the first concrete fix that converts current first-required fasload behavior from hang to deterministic `REQUIRED_FASLOAD_BOUNDARY` outcome in both focused lanes.

Milestone delta (2026-02-14, required-callable resolver verification guard):
- Changed: patched `ccl/doc/wasm/js/make-real-image.mjs` in `applyStartupBindingMapOrFail` to require bootstrap-resolver verification for `required-callable` fcell bindings before skip/reuse/apply; added deterministic failures for unresolved or mismatched required callable entry targets.
- Proven: current focused no-trace build logs still show `required_callable_count: 3` with `resolver_unresolved: 3` under `STARTUP_BINDING_MAP_BUILD.coverage.contract_required_const_pool_function_bindings`, matching `%FASLOAD`, `%FASL-OPEN`, `%SIMPLE-FASL-OPEN` unresolved-in-metadata state.
- Remains: rerun focused smoke/top4488 lanes to confirm this converts the previous post-`foreign.call.enter` hang into deterministic pre-fasload map-apply failure reasons (until callable entry authority is restored).

Milestone delta (2026-02-14, focused lane deterministic pre-fasload failure established):
- Changed: added pre-apply contract classification checks in `ccl/doc/wasm/js/make-real-image.mjs` so required callable symbols must be present in the startup map with required callable binding class, otherwise map apply fails deterministically.
- Proven: bounded focused lanes now fail deterministically before required fasload in both smoke and top4488:
  - `/tmp/make-real-image.notrace.smoke.source_scope_v1.guard2.skipfasl.log`
  - `/tmp/make-real-image.notrace.top4488.source_scope_v1.guard2.skipfasl.log`
  both emit `STARTUP_BINDING_MAP_APPLY {"status":"fail", ... "failed_count":3, "first_failure":{"symbol_key":"CCL::%FASLOAD","reason":"required-callable-binding-missing-from-map"}}` followed by `FAIL: pre-fasload startup binding map apply failed: 3 requirement(s)`.
- Proven: this replaces the previous ambiguous hang signature in focused diagnosis runs with a concrete pre-fasload boundary-class failure reason.
- Remains: determine why `%FASLOAD`, `%FASL-OPEN`, `%SIMPLE-FASL-OPEN` are absent/demoted in synthesized startup binding map entries despite contract-required callable coverage, then restore authoritative callable entry targeting.

Milestone delta (2026-02-14, resolver handoff restoration for required callables):
- Changed: patched `ccl/doc/wasm/js/make-real-image.mjs` wrapper `augmentStartupBindingMapArtifactWithContractConstPoolFunctions` to forward resolver callbacks into builder augmentation (`resolveFunctionDesignator`) instead of discarding resolver (`void resolver`).
- Proven: by code path inspection, contract-required callable emission is no longer forced into metadata-only fallback when runtime module metadata lacks `%FASLOAD` family entries.
- Remains: rerun focused bounded lane diagnostics to confirm `STARTUP_REQUIRED_CALLABLE_BINDINGS` now includes `%FASLOAD`, `%FASL-OPEN`, `%SIMPLE-FASL-OPEN` rows and that pre-fasload apply failure reason shifts accordingly.

Milestone delta (2026-02-14, resolver-vs-runtime callable authority matrix):
- Changed: added env-gated diagnostic `CCL_WASM_DIAG_REQUIRED_CALLABLE_RESOLVER=1` in `ccl/doc/wasm/js/make-real-image.mjs` to emit `STARTUP_REQUIRED_CALLABLE_RESOLVER` rows comparing bootstrap resolver (`with_package`/`name_only`) vs runtime symbol-fcell probe for each required callable.
- Proven: bounded smoke lane log `/tmp/make-real-image.notrace.smoke.source_scope_v1.guard5.diag.log` shows bootstrap resolver `missing` for all three required callables while runtime probe resolves entries `{%FASLOAD:4412,%FASL-OPEN:4372,%SIMPLE-FASL-OPEN:4360}`.
- Remains: convert this resolver/runtime mismatch into deterministic map synthesis that preserves required-callable metadata class and reaches pre-fasload apply pass in focused lanes.

Milestone delta (2026-02-14, required-callable rows restored + apply pass in focused bounded lanes):
- Changed: patched `ccl/doc/wasm/js/make-real-image.mjs` resolver callback adapter to accept builder payload shape (`{name,packageName}`), added runtime-fcell fallback for resolver `missing`, and patched `ccl/doc/wasm/js/startup-binding-map.mjs` to stamp `definition.required_class:"required-callable"` for `contract-required-callable` entries.
- Proven: bounded focused smoke and top4488 lanes now emit required callable rows and pass pre-fasload map apply:
  - `/tmp/make-real-image.notrace.smoke.source_scope_v1.guard9.diag.log`
  - `/tmp/make-real-image.notrace.top4488.source_scope_v1.guard9.diag.log`
  both show:
  - `STARTUP_REQUIRED_CALLABLE_BINDINGS ... "total_rows":3 ... "missing_required_callable_keys":[]`
  - `STARTUP_BINDING_MAP_APPLY {"status":"pass", ... "failed_count":0}`
- Proven: augmentation coverage now reports `resolver_resolved:3`, `emitted_entries:3`, `fcell_entries:3`, replacing prior zero-row required-callable map state.
- Remains: rerun without `CCL_WASM_SKIP_REQUIRED_FASLOADS=1` and confirm actual `REQUIRED_FASLOAD_BOUNDARY` behavior; bounded skip-fasload runs currently stop later at bootstrap sanity (`FAIL: bootstrap sanity check failed; ... exit=4`) and do not exercise first required fasload boundary.

Milestone delta (2026-02-14, option-1 no-skip focused lanes):
- Changed: ran both focused lanes without `CCL_WASM_SKIP_REQUIRED_FASLOADS`, preserving required-callable diagnostics:
  - `/tmp/make-real-image.notrace.smoke.source_scope_v1.guard10.noskip.log`
  - `/tmp/make-real-image.notrace.top4488.source_scope_v1.guard10.noskip.log`
- Proven: both lanes now cross into first required fasload and emit deterministic boundary failure (no hang):
  - `REQUIRED_FASLOAD_BOUNDARY {"status":"fail","fasl_index":0,"first_required_fasload":true,"path":"l1-fasls/l1-cl-package.lafsl","rc":-7,"reason":"required-fasload-failed-after-unified-startup-binding-map-apply","unresolved_function_symbol":null,...}`
  - terminal failure: `FAIL: wasm_fasload_path(l1-fasls/l1-cl-package.lafsl) returned -7`
- Proven: pre-fasload gates remain healthy in both no-skip runs (`STARTUP_BINDING_MAP_APPLY {"status":"pass"}` with required callable rows restored).
- Remains: isolate `rc=-7` failure cause inside first required fasload path (`l1-cl-package.lafsl`) now that startup binding-map omission/misbinding is no longer the active boundary reason.

Milestone delta (2026-02-14, decision lock: table V1 `rc=-7`, move primary to V2):
- Changed: added Section `0.0.B` with decision `DR-2026-02-14-V2-PRIMARY` to table V1-first `rc=-7` diagnosis and designate V2 as primary substrate.
- Proven: V1 baseline required for future parity checks is concretely frozen in guard10 no-skip logs (smoke/top4488) with matching first-required-fasload `rc=-7` signature.
- Remains: advance V2 implementation until it reaches equivalent first-required-fasload boundary semantics; continue debugging on V2 lane first.

Milestone delta (2026-02-14, troubleshooting note on recursion depth):
- Changed: documented that transitive const-pool recursion depth limiting is retained as a future troubleshooting option only.
- Proven: current default diagnostic posture keeps full recursive closure enabled; no depth cap is active in the normal pipeline path.
- Remains: only revisit depth limiting as an explicit, temporary diagnostic toggle if future evidence shows it is required to isolate memory/closure interactions.

### 0.0.A Fast Re-Entry Prompt (Use At Start Of New Conversations)

Canonical reusable template:
- `doc/wasm/startup-symbol-next-session-prompt-template.md`

Copy/paste prompt for compressed-history handoffs:

```text
Continue the WASM startup-symbol workflow using `ccl/doc/wasm/startup-symbol-pipeline-implementation-plan.md` as authoritative truth.

Non-negotiable priority: fasload is the blocker.
- Treat `REQUIRED_FASLOAD_BOUNDARY` as the primary gate.
- Do not claim progress unless both focused lanes pass this boundary.
- Do not re-audit already-recorded facts unless a touched source file changed.

Before any new work:
1) Read Section `0.0 Persistent Context Ledger`.
2) Reconstruct continuity from the ledger only.
3) State assumptions explicitly.

Execution focus:
- Diagnose and resolve first failing fasload reason.
- Keep architecture locked to source-scope artifact flow.
- Avoid introducing fallback parser paths or unrelated refactors.

Execution continuity contract (strict):
- Continue executing sequential steps until blocked by a concrete dependency or an explicit user decision.
- If at least one executable next step exists, execute it immediately.
- `objective_complete` is not a valid stop reason by itself; only stop when blocked or explicitly paused by user.
- Do not end with "minimum required work complete" while executable steps remain.
- In every terminal response, include a copy-paste `NEXT_SESSION_PROMPT` block inline (not only as a file path).
- In every terminal response, include:
  - `TERMINATION_CHECKLIST` with keys:
    - `termination_reason` (`blocked_dependency` or `user_decision`)
    - `next_executable_step_exists` (`yes`/`no`)
    - `if_yes_why_not_executed` (concrete blocker only)
    - `attempted_mitigations` (at least two attempts if blocked)
    - `next_step_id` (updated)
    - `next_session_prompt_emitted` (`yes` required)
    - `if_no_why` (only for blocked cases)
  - If blocked, include `BLOCKED_REPORT_FORMAT` exactly:
    - `blocker_type`
    - `failing_command`
    - `exact_error_output`
    - `dependency_needed`
    - `mitigation_attempt_1`
    - `mitigation_attempt_2`
    - `why_no_further_local_step_is_executable`

After each milestone:
- Append a short ledger delta: what changed, what was proven, what remains.
```

## 0. Purpose And Required Outcome

This document is the implementation plan to replace the current startup binding construction path with a deterministic, source-scoped, exact-resolution pipeline.

Primary required outcome:
- Build reaches pre-fasload apply + L0 contract gate deterministically.
- Required fasload boundary no longer fails because startup map omitted required callable symbols present in `level-1`.
- No reintroduction of preinstall/closure memory explosion.

Current failure signatures this plan explicitly addresses:
- `REQUIRED_FASLOAD_BOUNDARY ... "reason":"required-fasload-unresolved-function-symbol-after-unified-startup-binding-map-apply"`
- unresolved symbol example: `CLASS-HAS-A-FORWARD-REFERENCED-SUPERCLASS-P`
- memory failure signatures in old bulk path:
  - `WASM misc_alloc: reserve failed`
  - `Error: wasm_memory_grow_and_relocate failed for ... pages`

## 0.1 Scope

In scope:
- `ccl/doc/wasm/js/startup-binding-map.mjs`
- `ccl/doc/wasm/js/make-real-image.mjs`
- `ccl/doc/wasm/js/bootstrap-l0-contract.mjs` (read-only unless contract update needed)
- `ccl/scripts/wasm/collect-startup-symbol-scope.lisp` (new host-CCL scanner)
- Pipeline integration scripts under `ccl/scripts/wasm/` that produce the scope artifact before `make-real-image.mjs`
- `ccl/doc/wasm/build.md` documentation update
- Validation logs under `/tmp/` and/or `ccl/doc/wasm/repro/...`

Out of scope:
- changing Lisp kernel gate semantics
- changing required fasload ordering
- broad runtime dependency discovery loops

## 0.2 Working Definition Of Success

All must be true:
1. `STARTUP_SYMBOL_PIPELINE` log line exists and reports `mode:"source_scope_v1"` and `legacy_enabled:false`.
2. `STARTUP_SYMBOL_SCOPE_BUILD` exists and reports full L0/L1 coverage counts.
3. `STARTUP_SYMBOL_RESOLUTION_BUILD` exists and reports deterministic resolved/unresolved counts.
4. `STARTUP_BINDING_MAP_APPLY` is `"status":"pass"` in smoke lane and top4488 lane.
5. `L0_BOOTSTRAP_CONTRACT` is `"status":"pass"` in smoke lane and top4488 lane.
6. `REQUIRED_FASLOAD_BOUNDARY` does not fail for unresolved startup callable symbol omission.
7. No memory-growth failure signature appears:
   - no `WASM misc_alloc: reserve failed`
   - no `wasm_memory_grow_and_relocate failed`
8. Legacy bulk seed path is either deleted or provably inert and uncallable in production mode.
9. No required startup binding fails due to missing or stubbed startup ABI:
   - no required entry with reason `missing-kernel-export`
   - no required entry with reason `initializer-kind-unsupported-at-apply`

## 0.3 Why This Must Be A Series Of Tasks

This should be executed as a strict series of tasks (phased), because each phase has hard dependencies:
- Scanner language decision before implementation, then schema lock before scanner implementation.
- Scanner before resolver.
- Resolver before map generation.
- Map generation before apply/runtime validation.
- Validation before dead-code removal.

This plan is organized as phases with explicit sub-steps (`X.Y.A`) for implementation and audit.

## 0.4 Compromise Decision (Authoritative)

This plan adopts the following compromise as the controlling architecture:
1. Implement scanner `collect-startup-symbol-scope.lisp` in host CCL.
2. Run scanner in the existing compile pipeline where host CCL is already required.
3. Emit deterministic `startup_symbol_scope_v1` JSON artifact.
4. Keep `make-real-image.mjs` as consumer/resolver/apply only.
5. Do not keep a second JS parser path (no dual semantics).

Why:
- Uses real Lisp reader/package semantics (`in-package`, escapes, reader conditionals).
- Eliminates high-risk JS reader reimplementation bugs.
- Keeps orchestration and diagnostics in Node where current startup flow already runs.

Caveat (required):
- Do not invoke the Lisp scanner from inside `make-real-image.mjs`.
- Generate scope artifact earlier in compile/repro pipeline and pass it in.

## 0.5 Drop-Nothing Integration Rule (Including Already-Complete Work)

This plan is additive and preserves all prior tasks.
- No task from this document is deleted as part of compromise integration.
- If work is already complete, keep the task and mark it as verified with evidence (log line, code search, or artifact).
- If work is partial, keep existing task text and add remaining implementation deltas; do not collapse phases.
- Migration compatibility is allowed only for rollout control and must not introduce a second parser semantics path.

---

## 1. Phase 1: Baseline, Freeze, And Guardrails

### 1.1 Baseline Capture

#### 1.1.A Task
I will capture current behavior signatures from the latest smoke/top4488 logs before changing logic.

- Tool/script: shell + `rg`
- Language: shell
- Inputs:
  - `/tmp/make-real-image*.smoke*.log`
  - `/tmp/make-real-image*.top4488*.log`
- Outputs:
  - Baseline summary markdown block added to work notes (or commit message draft)
  - Captured lines for:
    - `STARTUP_BINDING_MAP_BUILD`
    - `STARTUP_BINDING_MAP_PREINSTALL`
    - `STARTUP_BINDING_MAP_APPLY`
    - `L0_BOOTSTRAP_CONTRACT`
    - `REQUIRED_FASLOAD_BOUNDARY`

Acceptance criteria:
- Baseline includes counts and first failure reason for both lanes.

#### 1.1.B Verification Command
```bash
for f in /tmp/make-real-image*.top4488*.log /tmp/make-real-image*.smoke*.log; do
  [ -f "$f" ] || continue
  echo "=== $f"
  rg -n "STARTUP_BINDING_MAP_BUILD|STARTUP_BINDING_MAP_PREINSTALL|STARTUP_BINDING_MAP_APPLY|L0_BOOTSTRAP_CONTRACT|REQUIRED_FASLOAD_BOUNDARY|WASM misc_alloc|wasm_memory_grow_and_relocate failed" "$f"
done
```

### 1.2 Pipeline Freeze Log

#### 1.2.A Task
I will add one startup mode line so every run reports which symbol pipeline is active.

- File: `ccl/doc/wasm/js/make-real-image.mjs`
- Output line format:
  - `STARTUP_SYMBOL_PIPELINE {"schema_version":"startup_symbol_pipeline_v1","mode":"source_scope_v1","legacy_enabled":false}`

Acceptance criteria:
- Line appears exactly once per run.

### 1.3 Legacy Override Policy (Temporary)

#### 1.3.A Task
I will define temporary emergency rollback behavior and expiry before implementation begins.

- Policy:
  - Optional env override: `CCL_WASM_STARTUP_SYMBOL_PIPELINE=legacy` (temporary)
  - Expires after parity validation pass in both lanes
  - Must be removed in cleanup phase

Acceptance criteria:
- Documented in `ccl/doc/wasm/build.md`
- CI/repro path defaults to `source_scope_v1`

### 1.4 Scanner Implementation Language Freeze

#### 1.4.A Task
I will lock the scanner implementation language to Common Lisp for this project and prevent a second parser implementation in JS.

This is the first implementation change in the sequence: switch parser implementation language to Common Lisp while preserving JSON schema + diagnostics contracts consumed by Node.

- Policy:
  - parser/reader implementation lives only in `collect-startup-symbol-scope.lisp`
  - Node runtime consumes artifacts and does not parse Lisp source directly for scope construction
  - no dual parser path is permitted in final design

Acceptance criteria:
- code search confirms no active JS Lisp parser in startup scope pipeline
- `make-real-image.mjs` only consumes prebuilt scope artifact (or fails if missing)
- existing diagnostics contract remains stable or intentionally versioned (`STARTUP_SYMBOL_*` lines preserved)

---

## 2. Phase 2: Contracts, Schemas, And Determinism Rules

### 2.1 Scope Artifact Schema (`startup_symbol_scope_v1`)

#### 2.1.A Task
I will write schema constants and serializer rules for `startup_symbol_scope_v1` in the host CCL scanner and mirror consumer-side validation constants in JS.

- Files:
  - `ccl/scripts/wasm/collect-startup-symbol-scope.lisp` (new)
  - `ccl/doc/wasm/js/make-real-image.mjs` (consumer-side schema checks)
  - optionally shared JSON schema doc/constants file if needed
- Language:
  - Common Lisp (artifact producer)
  - JavaScript (artifact consumer validation)
- Inputs:
  - parsed Lisp source forms from L0/L1
  - contract-required symbol definitions from `bootstrap-l0-contract.mjs`
- Output artifact (in-memory and optionally disk JSON):
  - top-level:
    - `schema_version`
    - `generator_version`
    - `inputs`
    - `symbols`
    - `counts`

Compatibility contract during parser-language switch:
- preserve existing diagnostic line names in Node (`STARTUP_SYMBOL_PIPELINE`, `STARTUP_SYMBOL_SCOPE_BUILD`, `STARTUP_SYMBOL_RESOLUTION_BUILD`)
- preserve artifact schema field names unless a deliberate schema-version bump is introduced

#### 2.1.B Required `inputs` Fields
- `repo_root`
- `scan_roots`
- `files_scanned_total`
- `files_scanned_l0`
- `files_scanned_l1`
- `contract_hash`
- `source_hash`
- `generated_at_utc`
- `feature_profile`

#### 2.1.C Required `symbols[]` Fields
- `key` (`PACKAGE::SYMBOL`)
- `package_name`
- `symbol_name`
- `roles[]` (sorted)
- `bindable` (boolean)
- `provenance[]` (sorted, deterministic)

`provenance[]` entry fields:
- `source_kind` (`level0|level1|contract`)
- `file`
- `line`
- `column` (if available)
- `role`
- `form`

#### 2.1.D Required `counts` Fields
- `symbols_total`
- `bindable_total`
- `by_role` map
- `by_package` map
- `excluded_uninterned_total`
- `excluded_unsupported_reader_total`

### 2.2 Resolution Artifact Schema (`startup_symbol_resolution_v1`)

#### 2.2.A Task
I will define exact output schema and statuses for resolver results.

- File: `ccl/doc/wasm/js/make-real-image.mjs` (or helper imported into it)
- Output fields:
  - `schema_version`
  - `generator_version`
  - `inputs_hash`
  - `symbols[]`
  - `counts`
  - `duration_ms`

#### 2.2.B `symbols[]` Required Fields
- `key`
- `status` (`resolved|unresolved|probe-error|invalid-input`)
- `symbol_raw`
- `probe_status`
- `probe_status_name`
- `fcell_raw`
- `fentry`
- `vcell_raw`
- `vcell_bound`
- `required_class` (`required-callable|required-special|optional|none`)
- `reason` (if unresolved)

#### 2.2.C `counts` Required Fields
- `total`
- `resolved`
- `unresolved`
- `function_capable`
- `vcell_bound`
- `required_unresolved`
- `optional_unresolved`

### 2.3 Determinism Rules

#### 2.3.A Task
I will enforce deterministic ordering rules for all generated JSON structures.

Rules:
- `symbols[]` sorted by `key` ascending
- `roles[]` sorted lexicographically
- `provenance[]` sorted by `(file,line,column,role)`
- `by_role` and `by_package` keys emitted sorted

Acceptance criteria:
- identical repository state yields byte-identical artifacts.

---

## 3. Phase 3: Source Scanner Implementation (New Tool)

### 3.1 New Scanner Tool

#### 3.1.A Task
I will write tool `ccl/scripts/wasm/collect-startup-symbol-scope.lisp` in Common Lisp (host CCL).

It will:
- parse specific directories/files:
  - `ccl/level-0/*.lisp` (non-recursive)
  - `ccl/level-1/**/*.lisp` (recursive)
  - `ccl/doc/wasm/js/bootstrap-l0-contract.mjs`
- produce expected output:
  - `startup_symbol_scope_v1` JSON object
  - optional file output via `--out <path>`

#### 3.1.B CLI Interface
Proposed:
```bash
ccl --no-init --batch \
  -l ccl/scripts/wasm/collect-startup-symbol-scope.lisp \
  -- \
  --repo-root ccl \
  --out /tmp/startup-symbol-scope.json \
  --feature-profile wasm32-target-v1
```

Output:
- JSON artifact file when `--out` is provided
- machine-readable summary line:
  - `STARTUP_SYMBOL_SCOPE_BUILD {...}`
- non-zero exit with reason-coded error object when scan fails

### 3.2 Reader/Parser Behavior

#### 3.2.A Task
I will implement scanner extraction using the real Common Lisp reader with controlled read options and deterministic traversal semantics.

Must handle:
- line comments: `; ...`
- block comments: `#| ... |#` (nested)
- strings with escapes
- quoted forms: `'x`
- function designator forms: `#'x`, `(function x)`
- `in-package`
- reader conditionals: `#+` / `#-` using provided feature profile
- escaped symbols: `|Foo Bar|`

#### 3.2.B Unsupported Reader Forms Policy
I will explicitly classify unsupported forms with deterministic behavior:
- default policy: record and skip symbol contribution
- reason code examples:
  - `unsupported-reader-dispatch`
  - `reader-parse-error`
  - `unterminated-block-comment`
  - `read-eval-disabled`

Acceptance criteria:
- scanner never silently drops parse failures.
- counts include exclusion totals by reason.
- scanner runs with read-eval disabled (`*read-eval*` false) for safety.

### 3.3 Symbol Role Extraction Rules

#### 3.3.A Task
I will implement role extraction rules with exact mapping.

Roles:
- `defined-function`: from defining forms
- `defined-special`: from special/global defining forms
- `call-head`: symbol in callable head position
- `function-designator`: from `#'x` and `(function x)`
- `symbol-atom`: fallback symbol atom sightings
- `contract-required`: from bootstrap contract

#### 3.3.B Definition Forms Coverage
Initial explicit form set:
- function definitions:
  - `defun`, `defmacro`, `define-compiler-macro`, `defsetf`, `define-setf-expander`
- special/global definitions:
  - `defvar`, `defparameter`, `def-standard-initial-binding`, `defglobal` (if present)

### 3.4 Canonicalization Rules

#### 3.4.A Task
I will implement exact canonicalization in Common Lisp to produce bindable keys.

Rules:
- canonical key: `PACKAGE::SYMBOL`
- package aliases normalized (`CL` -> `COMMON-LISP`, etc.)
- unqualified symbols resolve via current `in-package`
- keyword symbols map to `KEYWORD::<name>`
- uninterned `#:` excluded from bindable set

Acceptance criteria:
- canonicalizer has standalone tests for edge cases.

### 3.5 Scanner Tests

#### 3.5.A Task
I will add scanner fixture tests.

- Location proposal:
  - `ccl/scripts/wasm/collect-startup-symbol-scope.lisp` self-test entrypoint or companion test file
  - optional Node harness for fixture invocation and JSON golden comparisons
- Fixtures include:
  - package transitions
  - escaped symbols
  - reader conditionals
  - unsupported dispatch forms
  - comments + strings interaction

Acceptance criteria:
- tests validate role extraction and deterministic output ordering.

### 3.6 Compile Pipeline Integration (Artifact-First)

#### 3.6.A Task
I will integrate the scanner into the existing compile pipeline where host CCL is already a required dependency.

Integration points:
- `ccl/scripts/wasm/compile-wasm-fasls.sh` (or equivalent pipeline entry that already runs CCL)
- `ccl/scripts/wasm/repro-startup-pipeline.sh` deterministic run sequence

Expected behavior:
- scope artifact is generated before `make-real-image.mjs` starts
- artifact path is stable and explicitly passed forward
- pipeline fails fast if scope artifact generation fails

#### 3.6.B Task
I will keep `make-real-image.mjs` as a consumer/resolver/apply-only stage.

Rules:
- do not invoke the Lisp scanner from inside `make-real-image.mjs`
- require scope artifact path input (explicit arg or deterministic default)
- fail with machine-readable reason if artifact is missing/invalid

Acceptance criteria:
- Node-only `make-real-image` run remains reproducible from prebuilt artifacts
- no direct Lisp parsing path exists in Node runtime

---

## 4. Phase 4: Runtime Resolution Pass

### 4.1 Resolver Entry Point

#### 4.1.A Task
I will add a resolver pass in `ccl/doc/wasm/js/make-real-image.mjs` to process scoped symbols from the prebuilt scope artifact after runtime bootstrap exports are ready and before map build/apply.

Input:
- `startup_symbol_scope_v1.symbols[]` loaded from scanner-produced artifact file

Output:
- `startup_symbol_resolution_v1`
- diagnostic line:
  - `STARTUP_SYMBOL_RESOLUTION_BUILD {...}`

### 4.2 Exact Probe Rules

#### 4.2.A Task
I will enforce exact package+symbol probe only.

Rules:
- probe symbol by provided `package_name` + `symbol_name`
- no symbol-name-only fallback
- no package-agnostic rescue path

### 4.3 Resolution Status Rules

#### 4.3.A Task
I will implement explicit status + reason classification.

Examples:
- `resolved`
- `unresolved` with reason `symbol-missing`
- `probe-error` with `probe_status`
- `invalid-input` with reason `empty-symbol-name`

### 4.4 Resolver Tests

#### 4.4.A Task
I will add unit-level tests (mocked probe results) for status classification and counts.

Acceptance criteria:
- required/optional unresolved classification is correct.

---

## 5. Phase 5: Binding Map Generation Refactor

### 5.1 Replace Inclusion Logic Source

#### 5.1.A Task
I will refactor startup map generation so inclusion source-of-truth is scope+resolution artifacts only.

File:
- `ccl/doc/wasm/js/startup-binding-map.mjs`

Must remove from decision path:
- runtime metadata bulk callable seeds
- transitive closure as inclusion source-of-truth
- ambiguity heuristic filters as primary inclusion criteria
- JS regex/source parser logic used to derive startup symbol scope from Lisp files

### 5.2 Entry Construction Rules

#### 5.2.A Task
I will implement explicit entry mapping rules.

Function (`fcell`) entries:
- include if symbol has callable role signal and resolver indicates callable fentry.

Special variable (`vcell`) entries:
- always include contract required specials.
- include optional bound globals from source scope as non-required.

Availability mapping:
- `entry-backed`: resolved and directly initializable
- `deferred`: unresolved/unsupported now

### 5.3 Required vs Optional Failure Policy

#### 5.3.A Task
I will enforce:
- required unresolved before gate => explicit failure path
- optional unresolved => deferred with reason, no silent drop

### 5.4 Compatibility During Migration

#### 5.4.A Task
I will keep one temporary compatibility branch only if required for incremental rollout, guarded by explicit mode, then remove it.

Restriction:
- compatibility branch must not include an alternate JS Lisp parser; only artifact-source switching is permitted temporarily.

Acceptance criteria:
- final state has one active code path.

---

## 6. Phase 6: Apply Path Initializer Expansion

### 6.1 New Initializer Kinds

#### 6.1.A Task
I will extend apply logic in `ccl/doc/wasm/js/make-real-image.mjs` to support:
- `literal-symbol`
- `literal-keyword`

In addition to existing:
- `literal-fixnum`
- `literal-nil`
- `entry-function`

### 6.2 Semantics

#### 6.2.A Task
I will implement apply-time symbol literal resolution by exact package+name.

- no raw pointer persistence/replay
- preserve required binding checks

### 6.3 Apply Tests

#### 6.3.A Task
I will add tests for successful/failed apply scenarios per initializer kind.

Acceptance criteria:
- unsupported initializer kinds emit machine-readable failure reasons.

---

## 7. Phase 7: Diagnostics, Auditability, And Logs

### 7.1 Required Diagnostic Lines

#### 7.1.A Task
I will preserve existing required diagnostics:
- `STARTUP_BINDING_MAP_BUILD`
- `STARTUP_BINDING_MAP_PREINSTALL`
- `STARTUP_BINDING_MAP_APPLY`
- `L0_BOOTSTRAP_CONTRACT`
- `REQUIRED_FASLOAD_BOUNDARY`

#### 7.1.B Task
I will add new diagnostics:
- `STARTUP_SYMBOL_PIPELINE`
- `STARTUP_SYMBOL_SCOPE_BUILD`
- `STARTUP_SYMBOL_RESOLUTION_BUILD`

### 7.2 Failure Object Standard

#### 7.2.A Task
I will standardize failure objects to include:
- `schema_version`
- `status`
- `reason`
- `first_failure`
- `counts`
- `sample`/`examples` where large

Acceptance criteria:
- logs alone can reconstruct failure phase and reason.

---

## 8. Phase 8: Preinstall And Memory Guardrails

### 8.1 Deterministic Preinstall Set

#### 8.1.A Task
I will define preinstall set as:
- all contract-required const pools
- plus only anchor pools needed for required entries

Not allowed:
- broad closure-driven expansion
- all-runtime-callables preinstall

### 8.2 Budget Guard

#### 8.2.A Task
I will add deterministic budget checks on preinstall count.

Formula example:
- `max_preinstall = required_const_pool_count + required_anchor_pool_count + fixed_margin`

If exceeded:
- fail with reason `preinstall-budget-exceeded`

### 8.3 Memory Signature Gate

#### 8.3.A Task
I will require validation logs contain none of:
- `WASM misc_alloc: reserve failed`
- `wasm_memory_grow_and_relocate failed`

### 8.4 Startup Temp Table Lifecycle

#### 8.4.A Task
I will enforce startup temp/shadow table cleanup timing so required fasload resolution is not regressed.

Rule:
- startup temp/shadow tables used by const-pool install + deferred startup binding apply remain live through required fasload boundary.
- cleanup is allowed only after `REQUIRED_FASLOAD_BOUNDARY` first-required pass is crossed and no additional required fasloads will run in that process.
- cleanup before boundary is forbidden because it can reintroduce unresolved deferred startup bindings.

---

## 9. Phase 9: Caching And Invalidation

### 9.1 Scope Cache Design

#### 9.1.A Task
I will add optional on-disk cache for scope artifact in the scanner stage (Common Lisp producer), not in `make-real-image.mjs`.

- Location proposal:
  - `ccl/doc/wasm/repro/cache/startup-symbol-scope-v1.json`
- Key inputs:
  - schema version
  - generator version
  - feature profile
  - file list + hashes for scanned sources
  - contract hash
  - host CCL version string
  - scanner script hash

### 9.2 Invalidation Rules

#### 9.2.A Task
I will invalidate cache when any key input changes, and I will treat cache misses as normal (not errors).

Acceptance criteria:
- warm path is used only when safe and identical.

### 9.3 Cache Diagnostics

#### 9.3.A Task
I will emit cache status in `STARTUP_SYMBOL_SCOPE_BUILD`:
- `cache_hit`
- `cache_reason`
- `cache_key`

---

## 10. Phase 10: Validation Matrix (Exact Commands)

This plan uses two validation styles:
1. direct lane commands for focused startup diagnostics
2. full repro pipeline script for deterministic artifact runs

### 10.1 Focused Lane Commands

#### 10.1.0 Scope Artifact Build (required pre-step)
```bash
ccl --no-init --batch \
  -l ccl/scripts/wasm/collect-startup-symbol-scope.lisp \
  -- \
  --repo-root ccl \
  --out /tmp/startup-symbol-scope.source_scope_v1.json \
  --feature-profile wasm32-target-v1 \
  --contract-json ccl/doc/wasm/bootstrap-l0-contract.v1.json \
  > /tmp/collect-startup-symbol-scope.source_scope_v1.log 2>&1
```

#### 10.1.A top4488 Lane (direct)
```bash
CCL_WASM_TRACE=1 \
CCL_WASM_DIAG_PRE_FASLOAD_TOPLFUNC_ENTRY=4488 \
node ccl/doc/wasm/js/make-real-image.mjs \
  --startup-symbol-scope /tmp/startup-symbol-scope.source_scope_v1.json \
  > /tmp/make-real-image.trace.top4488.source_scope_v1.log 2>&1 || true
```

#### 10.1.B smoke lane (direct)
```bash
CCL_WASM_TRACE=1 \
node ccl/doc/wasm/js/make-real-image.mjs \
  --startup-symbol-scope /tmp/startup-symbol-scope.source_scope_v1.json \
  > /tmp/make-real-image.trace.smoke.source_scope_v1.log 2>&1 || true
```

#### 10.1.C Evidence Extraction
```bash
echo "=== /tmp/collect-startup-symbol-scope.source_scope_v1.log"
rg -n "STARTUP_SYMBOL_SCOPE_BUILD|FAIL|error|reason" /tmp/collect-startup-symbol-scope.source_scope_v1.log

for f in \
  /tmp/make-real-image.trace.top4488.source_scope_v1.log \
  /tmp/make-real-image.trace.smoke.source_scope_v1.log
  do
  echo "=== $f"
  rg -n "STARTUP_SYMBOL_PIPELINE|STARTUP_SYMBOL_SCOPE_BUILD|STARTUP_SYMBOL_RESOLUTION_BUILD|STARTUP_BINDING_MAP_BUILD|STARTUP_BINDING_MAP_PREINSTALL|STARTUP_BINDING_MAP_APPLY|L0_BOOTSTRAP_CONTRACT|REQUIRED_FASLOAD_BOUNDARY|WASM misc_alloc|wasm_memory_grow_and_relocate failed" "$f"
done
```

Note:
- `STARTUP_SYMBOL_SCOPE_BUILD` in `make-real-image` logs is a relay summary of the prebuilt artifact metadata (source/hash/counts), not an in-process scanner execution.

### 10.2 Full Repro Pipeline

#### 10.2.A Task
I will run deterministic repro script and archive outputs.

Command:
```bash
cd ccl
scripts/wasm/repro-startup-pipeline.sh
```

Expected generated artifacts:
- `ccl/doc/wasm/repro/startup-pipeline-<timestamp>-<sha>/startup-repro-run-manifest.json`
- step logs under `.../logs/`
- command history `.../commands.ndjson`
- scope scanner step log showing `STARTUP_SYMBOL_SCOPE_BUILD`
- scope artifact path recorded in run manifest or step metadata

### 10.3 Validation Assertions

#### 10.3.A Required Assertions (both lanes)
- has `STARTUP_SYMBOL_PIPELINE` with source scope mode.
- has `STARTUP_SYMBOL_SCOPE_BUILD` with full L0/L1 counts.
- has `STARTUP_SYMBOL_RESOLUTION_BUILD` with deterministic counts.
- `STARTUP_BINDING_MAP_APPLY` status is `pass`.
- `L0_BOOTSTRAP_CONTRACT` status is `pass`.
- scanner log shows successful scope artifact generation before `make-real-image`.
- no log evidence that `make-real-image` attempted to parse Lisp source directly.

#### 10.3.B Boundary Assertions
- no failure reason indicating startup symbol omission.
- if boundary still fails, first failure reason must be explicit and not regress earlier phase.

#### 10.3.C Memory Assertions
- none of memory growth failure signatures appear.

---

## 11. Phase 11: Legacy Path Removal And Cleanup

### 11.1 Remove Legacy Knobs

#### 11.1.A Task
I will remove legacy env knobs and dead branches after parity:
- legacy emit-all-functions env toggle
- bulk closure emission counters and related dead diagnostics
- symbol-name fallback logic in resolver path

### 11.2 Final Single Path Check

#### 11.2.A Task
I will ensure only one active startup symbol pipeline remains and it is source scope v1.

Verification:
- code search returns no executable references to removed legacy path.

### 11.3 Documentation Update

#### 11.3.A Task
I will update `ccl/doc/wasm/build.md` to reflect final architecture and commands.

Must include:
- new diagnostics lines
- schema summary
- exact validation commands
- explicit statement that legacy bulk path is removed

---

## 12. Work Breakdown By File

### 12.1 `ccl/scripts/wasm/collect-startup-symbol-scope.lisp` (new)
- implement scanner using Common Lisp reader semantics
- implement role extraction
- implement canonicalization
- implement deterministic JSON serializer
- implement optional cache read/write
- emit `STARTUP_SYMBOL_SCOPE_BUILD`
- enforce read safety (`*read-eval*` false)

### 12.2 `ccl/doc/wasm/js/startup-binding-map.mjs`
- consume scope+resolution artifacts
- remove legacy inclusion logic from decision path
- remove in-file JS Lisp/regex scanner helpers from active execution path
- map role/resolution -> binding entries
- keep explicit entry statuses/reasons

### 12.3 `ccl/doc/wasm/js/make-real-image.mjs`
- emit `STARTUP_SYMBOL_PIPELINE`
- load and validate prebuilt scope artifact
- run resolver
- emit `STARTUP_SYMBOL_RESOLUTION_BUILD`
- extend apply initializers for symbol/keyword literals
- preserve gate order and semantics
- never parse Lisp source directly for scope generation

### 12.4 `ccl/scripts/wasm/compile-wasm-fasls.sh` and/or pipeline wrapper
- invoke `collect-startup-symbol-scope.lisp` as part of compile pipeline
- write artifact to deterministic path
- pass artifact path forward to image builder steps
- fail fast on scan errors

### 12.5 `ccl/doc/wasm/build.md`
- update architecture narrative
- update validation commands
- add diagnostic reference for new lines
- document rollback policy and removal date
- document artifact-first flow and no-dual-parser policy

---

## 13. Risk Register And Mitigations

### 13.1 Parser Completeness Risk
Risk:
- scanner extraction logic still under-captures roles even though reader semantics come from Common Lisp.

Mitigation:
- rely on host CCL reader semantics instead of reimplementing reader in JS
- explicit unsupported form reason codes
- fixture-driven tests for extraction corner cases
- coverage metrics in scope build log

### 13.2 Host Toolchain Availability Risk
Risk:
- scanner requires host CCL in compile/repro environment.

Mitigation:
- invoke scanner only in pipeline stages that already require host CCL
- fail early with clear dependency error
- keep `make-real-image` artifact-consumer-only for Node reproducibility

### 13.3 Over/Under-Inclusion Risk
Risk:
- too many symbols reintroduce memory pressure, or too few symbols fail boundary.

Mitigation:
- strict source-bounded universe
- deterministic preinstall bound
- required/optional unresolved split with hard fail for required

### 13.4 Behavior Drift Risk
Risk:
- legacy path accidentally re-enabled.

Mitigation:
- startup mode diagnostic + CI grep assertion
- dead-code removal after parity

### 13.5 Cache Staleness Risk
Risk:
- stale scope artifact applied to changed source.

Mitigation:
- strong cache key including file hashes + schema/generator versions + host CCL version + scanner script hash
- explicit cache miss reasons in logs

---

## 14. Audit Checklist (External Reviewer)

The reviewer must be able to confirm each item from logs + code:
1. L0/L1 source coverage is complete and deterministic.
2. Scope artifact roles include all required categories.
3. Resolver uses exact package+name only.
4. Required unresolved symbols fail pre-gate explicitly.
5. Apply/gate sequence order unchanged.
6. Boundary failure reason (if any) is explicit and not due to silent drop.
7. No memory growth failure signatures.
8. Legacy bulk/closure path removed or inert and non-default.
9. Artifact JSON output deterministic on unchanged tree.
10. Scope scanner is implemented in Common Lisp and integrated in compile pipeline.
11. `make-real-image.mjs` consumes scope artifact and does not perform Lisp source parsing.

---

## 15. Execution Sequence (Practical Task Order)

1. Freeze parser implementation language and decision register (no JS scanner semantics path).
2. Lock schemas/constants and deterministic serialization contracts.
3. Implement/verify Common Lisp scanner + tests.
4. Integrate scanner into compile/repro pipeline artifact generation flow.
5. Implement resolver + tests (resolution build line).
6. Refactor binding map generation to scope+resolution.
7. Add initializer expansion in apply.
8. Add preinstall bound checks.
9. Run focused top4488 + smoke validations.
10. Run full repro pipeline validation.
11. Remove legacy branches/knobs.
12. Update docs and finalize audit evidence.

---

## 16. Deliverables

Required deliverables from this plan execution:
- Code changes in target files listed above
- New Common Lisp scanner tool and tests
- Updated diagnostics in logs
- Updated `ccl/doc/wasm/build.md`
- Validation evidence bundle:
  - scanner artifact generation log excerpt
  - smoke and top4488 log excerpts
  - repro run manifest path
  - summary of resolved/unresolved counts
  - confirmation that memory failure signatures are absent

---

## 17. Detailed Step Specs (Compromise Addendum)

Because the implementation surface spans scanner semantics, pipeline wiring, runtime resolver behavior, and reproducibility contracts, detailed step specs are maintained in companion documents.

- `ccl/doc/wasm/startup-symbol-pipeline-spec/README.md`
- `ccl/doc/wasm/startup-symbol-pipeline-spec/step-01-to-04-foundation-spec.md`
- `ccl/doc/wasm/startup-symbol-pipeline-spec/step-05-to-08-runtime-spec.md`
- `ccl/doc/wasm/startup-symbol-pipeline-spec/step-09-to-12-validation-cleanup-spec.md`
- `ccl/doc/wasm/startup-symbol-pipeline-spec/contradiction-ledger.md`
- `ccl/doc/wasm/startup-symbol-pipeline-spec/spec-closure-v1.md`
- `ccl/doc/wasm/startup-symbol-pipeline-spec/spec-closure-checklist.md`

Execution policy:
- these subdocuments are normative extensions of this plan for ambiguity resolution
- no task deletion is permitted when applying these addenda
- unresolved blocking decisions from the addendum decision register must be closed before claiming end-to-end completion

---

## 18. Zero-Surprise Execution Protocol (Operator Rules)

This section is mandatory execution behavior for this plan. It exists to stop
"20% progress then major redirect" failure mode.

### 18.1 Non-Negotiable Rules

1. Do not start a phase unless all gate inputs from the prior phase exist and
   are validated.
2. Every phase ends with one explicit gate command set and one pass/fail
   decision line in work notes.
3. If a gate fails, execute the mapped blocker playbook in this document;
   do not re-scope the architecture.
4. No unplanned "quick workaround" is allowed if it introduces a second parser
   semantics path.
5. Any new ambiguity discovered during implementation must be resolved by adding
   a decision entry to the related spec docs before code changes continue.
6. Every microstep must leave concrete evidence: artifact path, log line, grep
   output, or test result.
7. A passed microstep ID is immutable for the active run. Remediation discovered
   later must be recorded as substeps on the current microstep ID; do not reopen
   earlier passed IDs.
8. For pipeline wiring cards (`M-021`..`M-025`), grep-only presence checks are
   non-authoritative; pass requires semantic evidence of argument wiring and
   execution order.

### 18.2 Fixed Artifact Paths For Execution

Use these defaults unless a lane-specific override is explicitly documented:
- Scope artifact: `ccl/doc/wasm/startup-symbol-scope.source_scope_v1.json`
- Contract sidecar: `ccl/doc/wasm/bootstrap-l0-contract.v1.json`
- Focused lane scope temp:
  `/tmp/startup-symbol-scope.source_scope_v1.json`
- Focused lane scanner log:
  `/tmp/collect-startup-symbol-scope.source_scope_v1.log`
- Focused lane image logs:
  - `/tmp/make-real-image.trace.top4488.source_scope_v1.log`
  - `/tmp/make-real-image.trace.smoke.source_scope_v1.log`

### 18.3 Gate Output Record Format

After each gate, write one machine-parseable line in work notes:

```text
PLAN_GATE {"gate":"G-<id>","status":"pass|fail","evidence":["<path-or-command>"],"next":"<next-step-id|playbook-id>"}
```

---

## 19. Atomic Microstep Ledger (Authoritative)

Each microstep below is atomic: one change or one verification action. Execute
in order. Do not skip gate rows.

### 19.1 Track A: Freeze And Schema Lock (Steps 01-02)

#### Step 01: Language/Architecture Freeze

- `M-001` Add `STARTUP_SYMBOL_PIPELINE` mode emission in
  `ccl/doc/wasm/js/make-real-image.mjs` with
  `mode:"source_scope_v1"` and `legacy_enabled:false`.
- `M-002` Add hard assertion path that rejects JS source-scan fallback in
  active mode.
- `M-003` Add/update comments in
  `ccl/doc/wasm/js/startup-binding-map.mjs` declaring artifact-only inputs.
- `M-004` Add grep-based single-path check command to docs:
  `rg -n 'buildStartupBindingMapArtifact\\|startup symbol scope|single-path check' ccl/doc/wasm/startup-symbol-pipeline-implementation-plan.md`.
- `M-005` Gate `G-01`: run grep and confirm no active JS source parser path in
  startup execution path.

If `G-01` fails:
- Run Playbook `PB-01` (legacy parser isolation) before continuing.

#### Step 02: Schema + Determinism Lock

- `M-006` Define `startup_symbol_scope_v1` producer constants in scanner file.
- `M-007` Define matching consumer validators in
  `ccl/doc/wasm/js/make-real-image.mjs`.
- `M-008` Define `startup_symbol_resolution_v1` schema constants and counters.
- `M-009` Implement canonical JSON ordering rules and identity-hash exclusion of
  `generated_at_utc`.
- `M-010` Lock required field lists in docs and add explicit schema validation
  reasons for missing/invalid artifacts and fields:
  `startup-symbol-scope-missing`,
  `startup-symbol-scope-missing-required-field`,
  `startup-symbol-scope-invalid-schema`,
  `startup-symbol-resolution-missing-required-field`,
  `startup-symbol-resolution-invalid-schema`.
- `M-011` Gate `G-02`: validate schema checker rejects one synthetic invalid
  artifact and accepts one valid fixture.

If `G-02` fails:
- Run Playbook `PB-02` (schema mismatch reconciliation) before continuing.

#### Step 02R: Track A Remediation Addendum (Additive, No Reorder)

This addendum is strictly additive. It does not reorder, renumber, or replace
existing `M-001`..`M-067` cards. Use these remediation cards to close Track A
verification holes while preserving current execution order and completion
history.

- `M-008R1` Define and verify prerequisite that
  `ccl/doc/wasm/js/make-real-image.mjs` must parse `--startup-symbol-scope`
  before any `G-02` command using that flag is executed.
- `M-008R2` Add a corrected `G-02` verification command that proves both:
  invalid fixture rejection and valid fixture acceptance (no
  `startup-symbol-scope-invalid-schema` on valid fixture).
- `M-008R3` Add explicit precondition text: `M-006` and `M-009` are valid in
  Step 02 only when `ccl/scripts/wasm/collect-startup-symbol-scope.lisp` exists
  in repository baseline; if missing, create file per `M-012` first, then
  continue without renumbering/reordering Track A cards. `M-012` remains in
  Step 03 unchanged.

### 19.2 Track B: Scanner + Pipeline Insertion (Steps 03-04)

#### Step 03: Implement Common Lisp Scanner

- `M-012` Create `ccl/scripts/wasm/collect-startup-symbol-scope.lisp`.
- `M-013` Implement CLI parse: `--repo-root`, `--out`,
  `--feature-profile`, `--contract-json`.
- `M-014` Enforce read safety (`*read-eval*` nil), deterministic file order, and
  recoverable parse-failure recording.
- `M-015` Implement role extraction (`defined-function`, `defined-special`,
  `call-head`, `function-designator`, `symbol-atom`, `contract-required`).
- `M-016` Implement canonicalization rules to emit `PACKAGE::SYMBOL` keys.
- `M-017` Implement `STARTUP_SYMBOL_SCOPE_BUILD` emission with counts and
  exclusion reasons.
- `M-018` Add fixture tests for package transitions, reader conditionals,
  escaped symbols, unsupported reader dispatch.
- `M-019` Gate `G-03`: scanner command exits zero, emits one scope artifact, and
  fixture tests pass.

If `G-03` fails:
- Run Playbook `PB-03` (scanner read/feature profile failures).

#### Step 04: Integrate Scanner Into Compile/Repro

- `M-020` Add contract sidecar generation step that writes
  `ccl/doc/wasm/bootstrap-l0-contract.v1.json`.
- `M-021` Wire scanner invocation into
  `ccl/scripts/wasm/compile-wasm-fasls.sh` after module compile and before image
  build.
  - `M-021.1` declare scanner script and deterministic scope artifact path in
    `compile-wasm-fasls.sh`.
  - `M-021.2` require scanner invocation flags:
    `--repo-root`, `--out`, `--feature-profile`, `--contract-json`.
  - `M-021.3` require scanner invocation ordering:
    module compile -> contract sidecar generation -> scanner -> bundle/image
    handoff.
  - `M-021.4` require fail-fast guard when scanner script is missing.
- `M-022` Add CLI forwarding in `ccl/scripts/wasm/make-real-image.lisp` for:
  `--startup-symbol-scope`, `--startup-symbol-resolution-out`,
  `--startup-symbol-contract`.
- `M-023` Add equivalent wiring to
  `ccl/scripts/wasm/repro-startup-pipeline.sh` with fail-fast behavior.
- `M-024` Record scope artifact path/hash in repro run manifest.
- `M-025` Gate `G-04`: repro dry-run shows scanner step before make-root-image
  and manifest includes scope artifact hash entry.

If `G-04` fails:
- Run Playbook `PB-04` (pipeline ordering and CLI propagation).

### 19.3 Track C: Resolver/Map/Apply/Preinstall (Steps 05-08)

#### Step 05: Resolver + Resolution Artifact

- `M-026` Add resolver stage in `make-real-image.mjs` after runtime exports are
  available and before map synthesis.
- `M-027` Implement exact package+symbol probe only; remove name-only fallback.
- `M-028` Implement required-class mapping table:
  `required-callable|required-special|optional|none`.
- `M-029` Emit `startup_symbol_resolution_v1` with deterministic counts/status.
- `M-030` Emit `STARTUP_SYMBOL_RESOLUTION_BUILD` log line.
- `M-031` Add unit tests for status taxonomy and required/optional unresolved
  counts.
- `M-032` Gate `G-05`: test suite and one smoke run show resolution artifact +
  log line present.

If `G-05` fails:
- Run Playbook `PB-05` (resolver authority consistency).

#### Step 06: Binding Map Refactor To Artifact Inputs

- `M-033` Refactor `startup-binding-map.mjs` to consume only scope + resolution
  artifacts for inclusion decisions.
- `M-034` Remove JS source scan helpers from active execution path (retain only
  non-executable migration shims if required).
- `M-035` Implement deterministic entry synthesis matrix:
  `(role, required_class, status) -> target_cell/binding_class/availability`.
- `M-036` Preserve `startup_binding_map_v1` and `startup_shadow_table_v1`
  shapes for migration cut.
- `M-037` Enforce unresolved policy: required unresolved fails pre-gate; optional
  unresolved becomes deferred with reason.
- `M-038` Gate `G-06`: map generation executes without scanning Lisp and emits
  expected entry/deferred counts.

If `G-06` fails:
- Run Playbook `PB-06` (map synthesis divergence).

#### Step 07: Apply Initializer Expansion

- `M-039` Add initializer kinds `literal-symbol` and `literal-keyword`.
- `M-040` Add runtime export checks for symbol/keyword literal initializers.
- `M-041` Enforce required vs optional behavior when export missing:
  fail required, defer optional.
- `M-042` Add apply-time exact package+symbol resolution tests.
- `M-043` Gate `G-07`: apply tests pass for all initializer kinds and failure
  reasons are explicit.

If `G-07` fails:
- Run Playbook `PB-07` (initializer ABI mismatch).

#### Step 08: Preinstall Budget And Memory Guards

- `M-044` Add deterministic budget formula fields in preinstall diagnostics.
- `M-045` Enforce `preinstall-budget-exceeded` fail path with overrun metadata.
- `M-046` Confirm required contract roots are never pruned by budget logic.
- `M-047` Add memory signature assertion grep to validation scripts.
- `M-048` Gate `G-08`: preinstall log includes budget object and no false prune
  of required roots.

If `G-08` fails:
- Run Playbook `PB-08` (budget calibration without architecture change).

### 19.4 Track D: Validation, Cleanup, And Evidence (Steps 09-12)

#### Step 09: Focused Lane Validation

- `M-049` Build scope artifact with scanner command from Section `10.1.0`.
- `M-050` Run top4488 lane command from Section `10.1.A`.
- `M-051` Run smoke lane command from Section `10.1.B`.
- `M-052` Run evidence extraction command from Section `10.1.C`.
- `M-053` Gate `G-09`: both lanes show pass for
  `STARTUP_BINDING_MAP_APPLY` and `L0_BOOTSTRAP_CONTRACT`.

If `G-09` fails:
- Run Playbook `PB-09` (lane-specific failure triage) and rerun Step 09 only.

#### Step 10: Repro Pipeline Validation

- `M-054` Run `scripts/wasm/repro-startup-pipeline.sh`.
- `M-055` Verify scanner step exists before make-root-image in step logs.
- `M-056` Verify run manifest includes scope artifact path/size/sha256.
- `M-057` Verify resolution artifact recorded when configured.
- `M-058` Gate `G-10`: repro completes with startup artifacts and required
  diagnostics.

If `G-10` fails:
- Run Playbook `PB-10` (repro graph and manifest closure).

#### Step 11: Legacy Path Removal

- `M-059` Remove legacy emit-all-functions env toggle usage.
- `M-060` Remove runtime fallback map-generation branches in make-real-image.
- `M-061` Remove pack-time JS source-scan startup map generation.
- `M-062` Add final grep assertions for removed symbols/flags.
- `M-063` Gate `G-11`: grep assertions confirm single active source-scope path.

If `G-11` fails:
- Run Playbook `PB-11` (legacy path purge completion).

#### Step 12: Documentation + Evidence Bundle Finalization

- `M-064` Update `ccl/doc/wasm/build.md` startup pipeline sections to describe
  artifact-first architecture.
- `M-065` Update spec docs/checklists with closure status and evidence pointers.
- `M-066` Produce evidence bundle manifest with commands, hashes, and key log
  excerpts.
- `M-067` Gate `G-12`: reviewer can reproduce pass/fail assertions from bundle
  alone.

If `G-12` fails:
- Run Playbook `PB-12` (evidence bundle completion), not architecture changes.

---

## 20. Blocker Playbooks (Do Not Re-Scope Architecture)

### PB-01 Legacy Parser Isolation

- Goal: ensure any remaining JS scanner code is inert and non-default.
- Actions:
  - add explicit mode guards (`source_scope_v1` only),
  - fail fast if artifact missing instead of fallback generation,
  - document temporary compatibility horizon with expiry criteria.

### PB-02 Schema Mismatch Reconciliation

- Goal: keep producer/consumer schema in lockstep.
- Actions:
  - generate one canonical fixture from scanner,
  - run consumer validator against fixture,
  - patch one side only after diffing expected keys/types,
  - rerun `G-02`.

### PB-03 Scanner Read/Feature Failures

- Goal: recover without reducing reader correctness guarantees.
- Actions:
  - verify `--feature-profile` mapping table,
  - classify parse errors with reason codes,
  - keep scanner running across recoverable file errors,
  - rerun scanner fixtures.

### PB-04 Pipeline Ordering/CLI Propagation

- Goal: guarantee scanner artifact precedes image build in every lane.
- Actions:
  - trace args in `compile-wasm-fasls.sh` and `make-real-image.lisp`,
  - assert repro step ordering explicitly,
  - fail pipeline if scope artifact path is absent.

### PB-05 Resolver Authority Consistency

- Goal: keep one status taxonomy across metadata and kernel probe stages.
- Actions:
  - centralize status/reason enums,
  - ensure required-class assignment occurs before map build,
  - rerun resolver unit tests and smoke lane.

### PB-06 Map Synthesis Divergence

- Goal: prevent map entry drift or accidental re-scan dependency.
- Actions:
  - diff map outputs before/after refactor on same scope artifact,
  - inspect deferred/required failure partitions,
  - ensure shadow table recompute happens once after augmentation.

### PB-07 Initializer ABI Mismatch

- Goal: avoid hidden runtime failures for symbol/keyword initializers.
- Actions:
  - verify required kernel export surface,
  - ensure required entries fail explicitly when missing export,
  - ensure optional entries defer with reason.

### PB-08 Budget Calibration

- Goal: tune preinstall bounds without reintroducing closure explosion.
- Actions:
  - compute observed required roots + anchors,
  - adjust fixed margin only,
  - rerun top4488 and smoke memory assertions.

### PB-09 Focused Lane Failure Triage

- Goal: isolate lane-specific failure quickly.
- Actions:
  - inspect first failing required symbol and reason,
  - confirm scope artifact contains the symbol and role,
  - confirm resolver classification for the symbol,
  - patch smallest upstream phase and rerun Step 09 only.

### PB-10 Repro Graph/Manifest Closure

- Goal: ensure deterministic repro evidence for startup artifacts.
- Actions:
  - verify scanner step writes artifact to canonical path,
  - verify manifest schema accepts startup artifact entries,
  - rerun repro pipeline with clean run id.

### PB-11 Legacy Path Purge Completion

- Goal: remove hidden re-entry points for old semantics.
- Actions:
  - run grep assertions across runtime, pack, compact, and docs,
  - remove stale flags/exports,
  - rerun focused validations.

### PB-12 Evidence Bundle Completion

- Goal: make handoff reviewer-independent.
- Actions:
  - include command history, artifact hashes, key diagnostics, and gate lines,
  - include unresolved count summary and memory assertion summary,
  - include final single-path grep results.

---

## 21. Decision Lock Map (D1-D12 -> Fixed Outcome)

These decisions are now fixed for execution and must not be re-litigated unless
a blocker proves the decision impossible to implement.

1. `D1` Contract source: generated JSON sidecar
   `bootstrap-l0-contract.v1.json`.
2. `D2` Feature profile semantics: explicit scanner-owned mapping table;
   unknown profile fails.
3. `D3` Scope artifact paths: fixed compile/repro canonical paths in Section
   `18.2`.
4. `D4` Manifest policy: migration may read legacy embedded map, but no JS
   source scan generation.
5. `D5` Resolver authority: staged hybrid (metadata then kernel verification).
6. `D6` Scope/resolution schema fields and required fields: locked exactly as
   specified in `startup-symbol-pipeline-spec/spec-closure-v1.md`, with
   explicit schema failure reasons:
   `startup-symbol-scope-missing`,
   `startup-symbol-scope-missing-required-field`,
   `startup-symbol-scope-invalid-schema`,
   `startup-symbol-resolution-missing-required-field`,
   `startup-symbol-resolution-invalid-schema`.
7. `D7` Shadow table ownership: map builder continues producing
   `startup_shadow_table_v1` in migration cut.
8. `D8` Unresolved policy: required unresolved is fatal; optional unresolved is
   deferred with explicit reason.
9. `D9` Symbol/keyword initializer ABI: required export checks, explicit failure
   reasons.
10. `D10` Preinstall budget constants: deterministic formula with logged inputs.
11. `D11` Repro manifest coverage: include startup scope/resolution hashes.
12. `D12` Migration horizon: compatibility path expires after two consecutive
    passing repro runs and single-path grep pass.

---

## 21.1 Stub-Dependency Hardening Addendum (Startup Path)

This addendum is required to guarantee startup does not silently rely on
earlier-development stubs.

### 21.1.A Required Policy

1. Required startup bindings must never pass with implicit fallback when a
   kernel export is missing.
2. Required startup bindings must never remain on initializer kinds that are
   unsupported at apply-time.
3. Startup lane validation must include explicit grep assertions for:
   - `missing-kernel-export`
   - `initializer-kind-unsupported-at-apply`
   - trap signatures in startup lane logs.

### 21.1.B Additional Microsteps

- `M-068` Add startup ABI assertion for required initializer kinds and required
  target cells.
- `M-069` Integrate `scripts/wasm/check-startup-semantics.sh` into validation
  flow for startup-path policy checks.
- `M-070` Add focused startup-lane grep assertions that fail on:
  - `missing-kernel-export` for required bindings,
  - `initializer-kind-unsupported-at-apply` for required bindings,
  - startup-time trap signatures from stubbed paths.
- `M-071` Gate `G-13`: startup lanes and repro lane prove no required binding
  depends on missing/stubbed startup ABI.

---

## 22. Copy/Paste Execution Cards (Per Microstep)

This section expands every microstep (`M-001`..`M-067`) into:
- target file(s),
- exact verification command,
- expected evidence line.

### 22.0 Session Setup (run once)

```bash
cd /Users/buildsomething/Source
export CCL_REPO=/Users/buildsomething/Source/ccl
export SCOPE_JSON=/tmp/startup-symbol-scope.source_scope_v1.json
export SCOPE_LOG=/tmp/collect-startup-symbol-scope.source_scope_v1.log
export CONTRACT_JSON=/Users/buildsomething/Source/ccl/doc/wasm/bootstrap-l0-contract.v1.json
export MRI_TOP=/tmp/make-real-image.trace.top4488.source_scope_v1.log
export MRI_SMOKE=/tmp/make-real-image.trace.smoke.source_scope_v1.log
```

Expected evidence line:
- shell exits `0` and env vars resolve with `echo "$CCL_REPO" "$SCOPE_JSON" "$CONTRACT_JSON"`.

### 22.1 Track A Cards (`M-001`..`M-011`)

#### M-001
- Files: `ccl/doc/wasm/js/make-real-image.mjs`
- Command:
```bash
rg -n 'STARTUP_SYMBOL_PIPELINE|source_scope_v1|legacy_enabled' ccl/doc/wasm/js/make-real-image.mjs
```
- Expected evidence line:
- `STARTUP_SYMBOL_PIPELINE {"schema_version":"startup_symbol_pipeline_v1","mode":"source_scope_v1","legacy_enabled":false...}`

#### M-002
- Files: `ccl/doc/wasm/js/make-real-image.mjs`
- Command:
```bash
rg -n 'startup-symbol-scope-missing|startup-symbol-scope-invalid-schema|hard-fail' ccl/doc/wasm/js/make-real-image.mjs
```
- Expected evidence line:
- failure reason includes `startup-symbol-scope-missing` when scope artifact is absent.

#### M-003
- Files: `ccl/doc/wasm/js/startup-binding-map.mjs`
- Command:
```bash
rg -n 'scope artifact|resolution artifact|artifact-only|no JS source scan' ccl/doc/wasm/js/startup-binding-map.mjs
```
- Expected evidence line:
- active path text explicitly states scope+resolution artifacts are the source of truth.

#### M-004
- Files: `ccl/doc/wasm/startup-symbol-pipeline-implementation-plan.md`
- Command:
```bash
rg -n 'buildStartupBindingMapArtifact\\|startup symbol scope|single-path check' ccl/doc/wasm/startup-symbol-pipeline-implementation-plan.md
```
- Expected evidence line:
- grep assertion command for single-path verification is present in plan text.

#### M-005 (G-01)
- Files: `ccl/doc/wasm/js/make-real-image.mjs`, `ccl/scripts/wasm/pack-inline-bundle-v2.mjs`
- Command:
```bash
rg -n 'buildStartupBindingMapArtifact\(' ccl/doc/wasm/js/make-real-image.mjs ccl/scripts/wasm/pack-inline-bundle-v2.mjs || true
```
- Expected evidence line:
- no active runtime/pack-time fallback path remains (no executable call sites).

#### M-006
- Files: `ccl/scripts/wasm/collect-startup-symbol-scope.lisp`
- Command:
```bash
rg -n 'startup_symbol_scope_v1|schema_version|generator_version' ccl/scripts/wasm/collect-startup-symbol-scope.lisp
```
- Expected evidence line:
- scope producer emits schema version `startup_symbol_scope_v1`.

#### M-007
- Files: `ccl/doc/wasm/js/make-real-image.mjs`
- Command:
```bash
rg -n 'startup_symbol_scope_v1|startup-symbol-scope-invalid-schema|validate.*scope' ccl/doc/wasm/js/make-real-image.mjs
```
- Expected evidence line:
- consumer-side validator rejects invalid scope schema with explicit reason.

#### M-008
- Files: `ccl/doc/wasm/js/make-real-image.mjs`
- Command:
```bash
rg -n 'startup_symbol_resolution_v1|required_unresolved|optional_unresolved|probe-error|invalid-input' ccl/doc/wasm/js/make-real-image.mjs
```
- Expected evidence line:
- resolution artifact schema and deterministic counters are defined.

#### M-009
- Files: `ccl/scripts/wasm/collect-startup-symbol-scope.lisp`, `ccl/doc/wasm/js/make-real-image.mjs`
- Command:
```bash
rg -n 'generated_at_utc|identity hash|canonical|sorted|lexicographic' ccl/scripts/wasm/collect-startup-symbol-scope.lisp ccl/doc/wasm/js/make-real-image.mjs
```
- Expected evidence line:
- identity hash excludes `generated_at_utc` and deterministic ordering rules are explicit.

#### M-010
- Files: `ccl/doc/wasm/startup-symbol-pipeline-spec/spec-closure-v1.md`, `ccl/doc/wasm/startup-symbol-pipeline-implementation-plan.md`
- Command:
```bash
rg -n 'startup_symbol_scope_v1|startup_symbol_resolution_v1|required fields|invalid-schema' ccl/doc/wasm/startup-symbol-pipeline-spec/spec-closure-v1.md ccl/doc/wasm/startup-symbol-pipeline-implementation-plan.md
```
- Expected evidence line:
- required field lists are locked and explicit missing/invalid schema reasons
  are defined in docs.

#### M-011 (G-02)
- Files: `/tmp/invalid.scope.json`, `/tmp/valid.scope.json` (fixtures)
- Command:
```bash
node -e 'const fs=require("fs");fs.writeFileSync("/tmp/invalid.scope.json",JSON.stringify({schema_version:"broken"}));fs.writeFileSync("/tmp/valid.scope.json",JSON.stringify({schema_version:"startup_symbol_scope_v1",generator_version:"fixture-v1"}));'
node ccl/doc/wasm/js/make-real-image.mjs --startup-symbol-scope /tmp/invalid.scope.json > /tmp/mri.invalid-scope.log 2>&1 || true
node ccl/doc/wasm/js/make-real-image.mjs --startup-symbol-scope /tmp/valid.scope.json > /tmp/mri.valid-scope.log 2>&1 || true
rg -n 'startup-symbol-scope-invalid-schema' /tmp/mri.invalid-scope.log
! rg -n 'startup-symbol-scope-invalid-schema' /tmp/mri.valid-scope.log
```
- Expected evidence line:
- invalid fixture emits `startup-symbol-scope-invalid-schema` and valid fixture
  does not emit that reason.

### 22.1.A Track A Remediation Addendum Cards (`M-008R1`..`M-008R3`)

#### M-008R1
- Files: `ccl/doc/wasm/startup-symbol-pipeline-implementation-plan.md`
- Command:
```bash
rg -n 'M-008R1|--startup-symbol-scope|must parse|G-02' ccl/doc/wasm/startup-symbol-pipeline-implementation-plan.md
```
- Expected evidence line:
- remediation text explicitly states parser prerequisite for
  `--startup-symbol-scope` before `G-02` execution.

#### M-008R2
- Files: `/tmp/invalid.scope.json`, `/tmp/valid.scope.json` (fixtures)
- Command:
```bash
node -e 'const fs=require("fs");fs.writeFileSync("/tmp/invalid.scope.json",JSON.stringify({schema_version:"broken"}));fs.writeFileSync("/tmp/valid.scope.json",JSON.stringify({schema_version:"startup_symbol_scope_v1",generator_version:"fixture-v1"}));'
node ccl/doc/wasm/js/make-real-image.mjs --startup-symbol-scope /tmp/invalid.scope.json > /tmp/mri.invalid-scope.log 2>&1 || true
node ccl/doc/wasm/js/make-real-image.mjs --startup-symbol-scope /tmp/valid.scope.json > /tmp/mri.valid-scope.log 2>&1 || true
rg -n 'startup-symbol-scope-invalid-schema' /tmp/mri.invalid-scope.log
! rg -n 'startup-symbol-scope-invalid-schema' /tmp/mri.valid-scope.log
```
- Expected evidence line:
- invalid fixture emits `startup-symbol-scope-invalid-schema` and valid fixture
  does not emit that reason.

#### M-008R3
- Files: `ccl/doc/wasm/startup-symbol-pipeline-implementation-plan.md`
- Command:
```bash
rg -n 'M-008R3|M-006|M-009|M-012|repository baseline|if missing, create file per M-012 first' ccl/doc/wasm/startup-symbol-pipeline-implementation-plan.md
```
- Expected evidence line:
- precondition text explicitly resolves `M-006`/`M-009` scanner file existence
  dependency without changing Track A ordering.

### 22.2 Track B Cards (`M-012`..`M-025`)

#### M-012
- Files: `ccl/scripts/wasm/collect-startup-symbol-scope.lisp`
- Command:
```bash
test -f ccl/scripts/wasm/collect-startup-symbol-scope.lisp && echo 'scanner-file-present'
```
- Expected evidence line:
- `scanner-file-present`

#### M-013
- Files: `ccl/scripts/wasm/collect-startup-symbol-scope.lisp`
- Command:
```bash
rg -n -- '--repo-root|--out|--feature-profile|--contract-json' ccl/scripts/wasm/collect-startup-symbol-scope.lisp
```
- Expected evidence line:
- all four CLI flags are recognized in scanner CLI parser.

#### M-014
- Files: `ccl/scripts/wasm/collect-startup-symbol-scope.lisp`
- Command:
```bash
rg -n '\\*read-eval\\*|sort|deterministic|unsupported-reader-dispatch|reader-parse-error' ccl/scripts/wasm/collect-startup-symbol-scope.lisp
```
- Expected evidence line:
- scanner binds `*read-eval*` to `nil` and records read failures by reason.

#### M-015
- Files: `ccl/scripts/wasm/collect-startup-symbol-scope.lisp`, `$SCOPE_JSON`
- Command:
```bash
rg -n 'defined-function|defined-special|call-head|function-designator|symbol-atom|contract-required' ccl/scripts/wasm/collect-startup-symbol-scope.lisp
```
- Expected evidence line:
- role extraction includes all six role classes.

#### M-016
- Files: `$SCOPE_JSON`
- Command:
```bash
node -e 'const fs=require("fs");const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));const bad=j.symbols.filter(s=>!/^[A-Z0-9+*<>=!?._:-]+::[A-Z0-9+*<>=!?._:-]+$/.test(s.key));console.log("bad_keys",bad.length);process.exit(bad.length?1:0);' "$SCOPE_JSON"
```
- Expected evidence line:
- `bad_keys 0`

##### M-016R1 (Blocker Remediation: Session Variables)
- Objective:
- establish required session variables so `M-016` can address a real artifact path.
- Actions:
- apply Section `22.0 Session Setup` values for `CCL_REPO`, `SCOPE_JSON`, and `SCOPE_LOG`.
- verify variables are non-empty in the active shell session.
- Expected evidence line:
- session has concrete values for `CCL_REPO`, `SCOPE_JSON`, and `SCOPE_LOG`.

##### M-016R2 (Blocker Remediation: Scope Artifact Materialization)
- Objective:
- ensure `$SCOPE_JSON` exists and is populated before `M-016` validation.
- Actions:
- run the scanner build flow using existing plan defaults (`repo-root ccl`, feature profile `wasm32-target-v1`, contract sidecar `ccl/doc/wasm/bootstrap-l0-contract.v1.json`).
- write artifact to `$SCOPE_JSON` and scanner diagnostics to `$SCOPE_LOG`.
- confirm scope artifact file exists and is non-empty.
- Expected evidence line:
- scope artifact exists at `$SCOPE_JSON` and scanner diagnostics are present in `$SCOPE_LOG`.

##### M-016R3 (Blocker Remediation: Resume Gate Path)
- Objective:
- re-enter normal execution cards without changing `M-016`/`M-017` definitions.
- Actions:
- execute `M-016` unchanged against the now-materialized `$SCOPE_JSON`.
- on success (`bad_keys 0`), execute `M-017` unchanged against `$SCOPE_LOG`.
- if `M-016` fails, stop and remediate canonicalization in `collect-startup-symbol-scope.lisp` before retry.
- Expected evidence line:
- `M-016` reports `bad_keys 0` and `M-017` reports one `STARTUP_SYMBOL_SCOPE_BUILD {...}` line.

#### M-017
- Files: `$SCOPE_LOG`
- Command:
```bash
rg -n 'STARTUP_SYMBOL_SCOPE_BUILD' "$SCOPE_LOG"
```
- Expected evidence line:
- one `STARTUP_SYMBOL_SCOPE_BUILD {...}` summary line with counts/reasons.

#### M-018
- Files: `ccl/scripts/wasm/tests/startup-symbol-scope-fixtures/` (or equivalent)
- Command:
```bash
rg -n 'package transitions|reader conditionals|escaped symbols|unsupported reader dispatch' ccl/doc/wasm/startup-symbol-pipeline-implementation-plan.md ccl/doc/wasm/startup-symbol-pipeline-spec/spec-closure-v1.md
```
- Expected evidence line:
- fixture classes are explicitly listed and covered by scanner tests.

#### M-019 (G-03)
- Files: `$SCOPE_LOG`, `$SCOPE_JSON`
- Command:
```bash
test -s "$SCOPE_JSON" && rg -n 'STARTUP_SYMBOL_SCOPE_BUILD' "$SCOPE_LOG" && ! rg -n 'STARTUP_SYMBOL_SCOPE_BUILD_FAIL|reader-parse-error-fatal' "$SCOPE_LOG"
```
- Expected evidence line:
- scanner command exits successfully and artifact exists with diagnostics.

#### M-020
- Files: `ccl/doc/wasm/bootstrap-l0-contract.v1.json`
- Command:
```bash
test -f ccl/doc/wasm/bootstrap-l0-contract.v1.json && node -e 'const fs=require("fs");const j=JSON.parse(fs.readFileSync("ccl/doc/wasm/bootstrap-l0-contract.v1.json","utf8"));console.log("keys",Object.keys(j).sort().join(","));'
```
- Expected evidence line:
- contract sidecar exists and includes required callable/special/const-pool keys.

#### M-021
- Files: `ccl/scripts/wasm/compile-wasm-fasls.sh`
- Command set (all required):
```bash
node -e 'const fs=require("fs");const s=fs.readFileSync("ccl/scripts/wasm/compile-wasm-fasls.sh","utf8");const req=["STARTUP_SYMBOL_SCOPE_SCRIPT=\"$ROOT_DIR/scripts/wasm/collect-startup-symbol-scope.lisp\"","STARTUP_SYMBOL_SCOPE_OUT=\"$ROOT_DIR/doc/wasm/startup-symbol-scope.source_scope_v1.json\"","--repo-root \"$ROOT_DIR\"","--out \"$STARTUP_SYMBOL_SCOPE_OUT\"","--feature-profile wasm32-target-v1","--contract-json \"$CONTRACT_SIDECAR_OUT\""];const miss=req.filter(x=>!s.includes(x));if(miss.length){console.error("m021_missing_tokens",miss.join(","));process.exit(1);}console.log("m021_required_tokens_ok",req.length);'
```
```bash
awk '/run "\$CCL_BIN" --no-init --batch -l "\$SCRIPT"/{compile=NR}/run node "\$CONTRACT_SIDECAR_SCRIPT"/{sidecar=NR}/run "\$CCL_BIN" --no-init --batch -l "\$STARTUP_SYMBOL_SCOPE_SCRIPT"/{scanner=NR}/run node "\$PACK_SCRIPT"/{pack=NR} END{ok=(compile&&sidecar&&scanner&&pack&&compile<sidecar&&sidecar<scanner&&scanner<pack); if(!ok){printf("m021_order_fail compile=%s sidecar=%s scanner=%s pack=%s\n",compile,sidecar,scanner,pack); exit 1} printf("m021_order_ok compile=%s sidecar=%s scanner=%s pack=%s\n",compile,sidecar,scanner,pack)}' ccl/scripts/wasm/compile-wasm-fasls.sh
```
```bash
rg -n 'if \[ ! -f "\$STARTUP_SYMBOL_SCOPE_SCRIPT" \]|error: missing \$STARTUP_SYMBOL_SCOPE_SCRIPT' ccl/scripts/wasm/compile-wasm-fasls.sh
```
- Expected evidence line:
- `m021_required_tokens_ok 6` is printed.
- `m021_order_ok ...` is printed with `compile < sidecar < scanner < pack`.
- scanner missing-file guard exists and exits with `error: missing $STARTUP_SYMBOL_SCOPE_SCRIPT`.
- compile pipeline scanner wiring is semantically verified, not grep-only.

#### M-022
- Files: `ccl/scripts/wasm/make-real-image.lisp`
- Command:
```bash
rg -n 'startup-symbol-scope|startup-symbol-resolution-out|startup-symbol-contract' ccl/scripts/wasm/make-real-image.lisp
```
- Expected evidence line:
- Lisp wrapper forwards all new startup symbol flags.

#### M-023
- Files: `ccl/scripts/wasm/repro-startup-pipeline.sh`
- Command:
```bash
rg -n 'collect-startup-symbol-scope|startup-symbol-scope|fail fast|set -e' ccl/scripts/wasm/repro-startup-pipeline.sh
```
- Expected evidence line:
- repro script contains scanner step and fail-fast behavior.

#### M-024
- Files: repro run manifest
- Command:
```bash
RUN_DIR=$(ls -td ccl/doc/wasm/repro/startup-pipeline-* 2>/dev/null | head -n1); test -n "$RUN_DIR" && rg -n 'startup-symbol-scope|sha256|bytes' "$RUN_DIR/startup-repro-run-manifest.json"
```
- Expected evidence line:
- manifest records startup scope artifact path, bytes, and sha256.

#### M-025 (G-04)
- Files: `ccl/scripts/wasm/repro-startup-pipeline.sh`
- Command:
```bash
nl -ba ccl/scripts/wasm/repro-startup-pipeline.sh | rg -n 'collect-startup-symbol-scope|make-root-image'
```
- Expected evidence line:
- scanner step line number is lower than `make-root-image` line number.

### 22.3 Track C Cards (`M-026`..`M-048`)

#### M-026
- Files: `ccl/doc/wasm/js/make-real-image.mjs`
- Command:
```bash
nl -ba ccl/doc/wasm/js/make-real-image.mjs | rg -n 'STARTUP_SYMBOL_RESOLUTION_BUILD|resolution|build.*binding map|startup binding map'
```
- Expected evidence line:
- resolver stage appears before map synthesis in execution order.

#### M-027
- Files: `ccl/doc/wasm/js/make-real-image.mjs`
- Command:
```bash
rg -n 'package_name|symbol_name|exact package\\+name|no symbol-name-only fallback' ccl/doc/wasm/js/make-real-image.mjs
```
- Expected evidence line:
- resolver probes exact package+symbol only.

#### M-028
- Files: `ccl/doc/wasm/js/make-real-image.mjs`
- Command:
```bash
rg -n 'required-callable|required-special|optional|none' ccl/doc/wasm/js/make-real-image.mjs
```
- Expected evidence line:
- required-class mapping table includes all four classes.

#### M-029
- Files: `ccl/doc/wasm/js/make-real-image.mjs`
- Command:
```bash
rg -n 'startup_symbol_resolution_v1|resolver_source|counts|required_unresolved|optional_unresolved' ccl/doc/wasm/js/make-real-image.mjs
```
- Expected evidence line:
- resolution artifact serializer emits full schema fields and counters.

#### M-030
- Files: `ccl/doc/wasm/js/make-real-image.mjs`
- Command:
```bash
rg -n 'STARTUP_SYMBOL_RESOLUTION_BUILD' ccl/doc/wasm/js/make-real-image.mjs
```
- Expected evidence line:
- one resolution diagnostic line is emitted per run.

#### M-031
- Files: `ccl/doc/wasm/js/tests/` (new resolver tests)
- Command:
```bash
rg -n 'required_unresolved|optional_unresolved|probe-error|invalid-input' ccl/doc/wasm/js/tests || true
```
- Expected evidence line:
- resolver tests assert status taxonomy and required/optional splits.

#### M-032 (G-05)
- Files: resolver tests + smoke log
- Command:
```bash
node --test ccl/doc/wasm/js/tests/*.test.mjs > /tmp/startup-symbol-tests.log 2>&1 || true
rg -n 'STARTUP_SYMBOL_RESOLUTION_BUILD' "$MRI_SMOKE" /tmp/startup-symbol-tests.log
```
- Expected evidence line:
- tests pass and smoke lane contains `STARTUP_SYMBOL_RESOLUTION_BUILD`.

#### M-033
- Files: `ccl/doc/wasm/js/startup-binding-map.mjs`
- Command:
```bash
rg -n 'scope artifact|resolution artifact|source-of-truth|input' ccl/doc/wasm/js/startup-binding-map.mjs
```
- Expected evidence line:
- inclusion logic is driven by scope+resolution artifacts.

#### M-034
- Files: `ccl/doc/wasm/js/startup-binding-map.mjs`
- Command:
```bash
rg -n 'readFileSync\\(|level-0|level-1|regex|lisp parser|source scan' ccl/doc/wasm/js/startup-binding-map.mjs || true
```
- Expected evidence line:
- no active source-scan helper remains in execution path.

#### M-035
- Files: `ccl/doc/wasm/js/startup-binding-map.mjs`
- Command:
```bash
rg -n 'entry-backed|deferred|required-special|required-callable|initializer\\.kind|target_cell|binding_class' ccl/doc/wasm/js/startup-binding-map.mjs
```
- Expected evidence line:
- deterministic entry synthesis matrix fields are explicit.

#### M-036
- Files: `ccl/doc/wasm/js/startup-binding-map.mjs`
- Command:
```bash
rg -n 'startup_binding_map_v1|startup_shadow_table_v1|preinstall_const_pool_entries|entry_backed_binding_count' ccl/doc/wasm/js/startup-binding-map.mjs
```
- Expected evidence line:
- migration cut preserves map/shadow schema versions and key fields.

#### M-037
- Files: `ccl/doc/wasm/js/startup-binding-map.mjs`, `ccl/doc/wasm/js/make-real-image.mjs`
- Command:
```bash
rg -n 'required-symbol-unresolved|required unresolved|deferred with reason|optional unresolved' ccl/doc/wasm/js/startup-binding-map.mjs ccl/doc/wasm/js/make-real-image.mjs
```
- Expected evidence line:
- required unresolved is fatal; optional unresolved is deferred with reason.

#### M-038 (G-06)
- Files: `$MRI_SMOKE`
- Command:
```bash
rg -n 'STARTUP_BINDING_MAP_BUILD|STARTUP_BINDING_MAP_APPLY|status\":\"pass\"|source scope' "$MRI_SMOKE"
```
- Expected evidence line:
- map builds/applies without JS source scanning and reports deterministic counts.

#### M-039
- Files: `ccl/doc/wasm/js/make-real-image.mjs`
- Command:
```bash
rg -n 'literal-symbol|literal-keyword|literal-fixnum|literal-nil|entry-function' ccl/doc/wasm/js/make-real-image.mjs
```
- Expected evidence line:
- apply path supports all five initializer kinds.

#### M-040
- Files: `ccl/doc/wasm/js/make-real-image.mjs`
- Command:
```bash
rg -n 'missing-kernel-export|initializer-kind-not-supported|symbol literal|keyword literal' ccl/doc/wasm/js/make-real-image.mjs
```
- Expected evidence line:
- symbol/keyword initializers are guarded by explicit export checks.

#### M-041
- Files: `ccl/doc/wasm/js/make-real-image.mjs`
- Command:
```bash
rg -n 'required.*missing-kernel-export|optional.*initializer-kind-not-supported|defer' ccl/doc/wasm/js/make-real-image.mjs
```
- Expected evidence line:
- required entries fail; optional entries defer when initializer ABI is unavailable.

#### M-042
- Files: `ccl/doc/wasm/js/tests/` (apply tests)
- Command:
```bash
rg -n 'literal-symbol|literal-keyword|exact package\\+name|apply-time' ccl/doc/wasm/js/tests || true
```
- Expected evidence line:
- apply tests cover exact package+symbol behavior for new initializer kinds.

#### M-043 (G-07)
- Files: apply tests
- Command:
```bash
node --test ccl/doc/wasm/js/tests/*.test.mjs > /tmp/startup-apply-tests.log 2>&1 || true
rg -n 'pass|ok|missing-kernel-export|initializer-kind-not-supported' /tmp/startup-apply-tests.log
```
- Expected evidence line:
- apply test suite passes and failure reasons are explicit when exercised.

#### M-044
- Files: `ccl/doc/wasm/js/make-real-image.mjs`
- Command:
```bash
rg -n 'budget\\.max_preinstall|budget\\.required_roots|budget\\.required_anchors|budget\\.fixed_margin|budget\\.over_by' ccl/doc/wasm/js/make-real-image.mjs
```
- Expected evidence line:
- preinstall diagnostics include full budget telemetry object.

#### M-045
- Files: `ccl/doc/wasm/js/make-real-image.mjs`
- Command:
```bash
rg -n 'preinstall-budget-exceeded' ccl/doc/wasm/js/make-real-image.mjs
```
- Expected evidence line:
- explicit fail reason `preinstall-budget-exceeded` exists.

#### M-046
- Files: `$MRI_SMOKE`, `$MRI_TOP`
- Command:
```bash
rg -n 'startup-shadow-table-missing-contract-root-entries|required_roots|required_anchors' "$MRI_SMOKE" "$MRI_TOP" || true
```
- Expected evidence line:
- no contract-root pruning failure appears in lane logs.

#### M-047
- Files: validation scripts/docs
- Command:
```bash
rg -n 'WASM misc_alloc: reserve failed|wasm_memory_grow_and_relocate failed' ccl/doc/wasm/startup-symbol-pipeline-implementation-plan.md ccl/scripts/wasm
```
- Expected evidence line:
- memory-failure signature checks are present in validation path.

#### M-048 (G-08)
- Files: `$MRI_SMOKE`, `$MRI_TOP`
- Command:
```bash
rg -n 'STARTUP_BINDING_MAP_PREINSTALL|budget|preinstall-budget-exceeded|startup-shadow-table-missing-contract-root-entries' "$MRI_SMOKE" "$MRI_TOP"
```
- Expected evidence line:
- preinstall budget object appears and required roots remain intact.

### 22.4 Track D Cards (`M-049`..`M-067`)

#### M-049
- Files: scanner output/log
- Command:
```bash
ccl --no-init --batch \
  -l ccl/scripts/wasm/collect-startup-symbol-scope.lisp \
  -- \
  --repo-root ccl \
  --out "$SCOPE_JSON" \
  --feature-profile wasm32-target-v1 \
  --contract-json "$CONTRACT_JSON" \
  > "$SCOPE_LOG" 2>&1
```
- Expected evidence line:
- `$SCOPE_LOG` contains `STARTUP_SYMBOL_SCOPE_BUILD`.

#### M-050
- Files: `$MRI_TOP`
- Command:
```bash
CCL_WASM_TRACE=1 \
CCL_WASM_DIAG_PRE_FASLOAD_TOPLFUNC_ENTRY=4488 \
node ccl/doc/wasm/js/make-real-image.mjs \
  --startup-symbol-scope "$SCOPE_JSON" \
  > "$MRI_TOP" 2>&1 || true
```
- Expected evidence line:
- top4488 log contains `STARTUP_SYMBOL_PIPELINE`.

#### M-051
- Files: `$MRI_SMOKE`
- Command:
```bash
CCL_WASM_TRACE=1 \
node ccl/doc/wasm/js/make-real-image.mjs \
  --startup-symbol-scope "$SCOPE_JSON" \
  > "$MRI_SMOKE" 2>&1 || true
```
- Expected evidence line:
- smoke log contains `STARTUP_SYMBOL_PIPELINE`.

#### M-052
- Files: `$SCOPE_LOG`, `$MRI_TOP`, `$MRI_SMOKE`
- Command:
```bash
echo "=== $SCOPE_LOG"
rg -n 'STARTUP_SYMBOL_SCOPE_BUILD|FAIL|error|reason' "$SCOPE_LOG"
for f in "$MRI_TOP" "$MRI_SMOKE"; do
  echo "=== $f"
  rg -n 'STARTUP_SYMBOL_PIPELINE|STARTUP_SYMBOL_SCOPE_BUILD|STARTUP_SYMBOL_RESOLUTION_BUILD|STARTUP_BINDING_MAP_BUILD|STARTUP_BINDING_MAP_PREINSTALL|STARTUP_BINDING_MAP_APPLY|L0_BOOTSTRAP_CONTRACT|REQUIRED_FASLOAD_BOUNDARY|WASM misc_alloc|wasm_memory_grow_and_relocate failed' "$f"
done
```
- Expected evidence line:
- both lane logs include all required startup diagnostics.

#### M-053 (G-09)
- Files: `$MRI_TOP`, `$MRI_SMOKE`
- Command:
```bash
for f in "$MRI_TOP" "$MRI_SMOKE"; do
  rg -n 'STARTUP_BINDING_MAP_APPLY.*"status":"pass"' "$f"
  rg -n 'L0_BOOTSTRAP_CONTRACT.*"status":"pass"' "$f"
done
```
- Expected evidence line:
- both logs show `STARTUP_BINDING_MAP_APPLY.status == pass` and `L0_BOOTSTRAP_CONTRACT.status == pass`.

#### M-054
- Files: repro run directory
- Command:
```bash
cd ccl && scripts/wasm/repro-startup-pipeline.sh
```
- Expected evidence line:
- new run directory created at `ccl/doc/wasm/repro/startup-pipeline-<timestamp>-<sha>/`.

#### M-055
- Files: latest repro `commands.ndjson` or step logs
- Command:
```bash
RUN_DIR=$(ls -td /Users/buildsomething/Source/ccl/doc/wasm/repro/startup-pipeline-* | head -n1)
rg -n 'collect-startup-symbol-scope|make-root-image' "$RUN_DIR/commands.ndjson"
```
- Expected evidence line:
- `collect-startup-symbol-scope` appears before `make-root-image`.

#### M-056
- Files: latest repro manifest
- Command:
```bash
RUN_DIR=$(ls -td /Users/buildsomething/Source/ccl/doc/wasm/repro/startup-pipeline-* | head -n1)
rg -n 'startup-symbol-scope|sha256|bytes|path' "$RUN_DIR/startup-repro-run-manifest.json"
```
- Expected evidence line:
- manifest has startup scope artifact entry with path/bytes/sha256.

#### M-057
- Files: latest repro manifest
- Command:
```bash
RUN_DIR=$(ls -td /Users/buildsomething/Source/ccl/doc/wasm/repro/startup-pipeline-* | head -n1)
rg -n 'startup-symbol-resolution|sha256|bytes|path' "$RUN_DIR/startup-repro-run-manifest.json" || true
```
- Expected evidence line:
- when resolution artifact emission is enabled, manifest includes its hash entry.

#### M-058 (G-10)
- Files: repro logs + manifest
- Command:
```bash
RUN_DIR=$(ls -td /Users/buildsomething/Source/ccl/doc/wasm/repro/startup-pipeline-* | head -n1)
rg -n 'STARTUP_SYMBOL_PIPELINE|STARTUP_SYMBOL_SCOPE_BUILD|STARTUP_SYMBOL_RESOLUTION_BUILD|STARTUP_BINDING_MAP_APPLY|L0_BOOTSTRAP_CONTRACT' "$RUN_DIR"/logs/* || true
rg -n 'startup-symbol-scope|sha256' "$RUN_DIR/startup-repro-run-manifest.json"
```
- Expected evidence line:
- repro run includes required startup diagnostics and startup artifact hashes.

#### M-059
- Files: repository-wide
- Command:
```bash
rg -n 'emit-all-functions|startup binding map.*env toggle' ccl/doc/wasm/js ccl/scripts/wasm || true
```
- Expected evidence line:
- no remaining executable references to removed legacy env toggle.

#### M-060
- Files: `ccl/doc/wasm/js/make-real-image.mjs`
- Command:
```bash
node ccl/doc/wasm/js/make-real-image.mjs > /tmp/mri.no-scope.log 2>&1 || true
rg -n 'startup-symbol-scope-missing' /tmp/mri.no-scope.log
```
- Expected evidence line:
- missing scope artifact fails fast instead of runtime fallback generation.

#### M-061
- Files: `ccl/scripts/wasm/pack-inline-bundle-v2.mjs`
- Command:
```bash
rg -n 'buildStartupBindingMapArtifact\\(|scan.*lisp|startup map.*from source' ccl/scripts/wasm/pack-inline-bundle-v2.mjs || true
```
- Expected evidence line:
- pack script has no active source-scan startup-map generation path.

#### M-062
- Files: repository-wide final grep set
- Command:
```bash
rg -n 'buildStartupBindingMapArtifact\(' ccl/doc/wasm/js/make-real-image.mjs ccl/scripts/wasm/pack-inline-bundle-v2.mjs || true
rg -n 'emit-all-functions|startup binding map.*env toggle' ccl/doc/wasm/js ccl/scripts/wasm || true
rg -n 'scan.*lisp|startup map.*from source' ccl/scripts/wasm/pack-inline-bundle-v2.mjs || true
```
- Expected evidence line:
- all final grep assertions return no matches in active JS/script paths.

#### M-063 (G-11)
- Files: focused lane logs + grep outputs
- Command:
```bash
for f in "$MRI_TOP" "$MRI_SMOKE"; do
  rg -n 'STARTUP_SYMBOL_PIPELINE.*source_scope_v1' "$f"
done
rg -n 'buildStartupBindingMapArtifact\(' ccl/doc/wasm/js/make-real-image.mjs ccl/scripts/wasm/pack-inline-bundle-v2.mjs || true
```
- Expected evidence line:
- one active source-scope path remains and legacy re-entry points are absent.

#### M-064
- Files: `ccl/doc/wasm/build.md`
- Command:
```bash
rg -n 'Common Lisp scanner|artifact-first|startup_symbol_scope_v1|STARTUP_SYMBOL_PIPELINE|no JS source scan' ccl/doc/wasm/build.md
```
- Expected evidence line:
- build docs describe scanner-owned artifact-first architecture.

#### M-065
- Files: spec docs
- Command:
```bash
rg -n 'implementation closed|G-01|G-12|Decision Register \\(Locked For Execution\\)' ccl/doc/wasm/startup-symbol-pipeline-spec/*.md
```
- Expected evidence line:
- spec docs/checklists are updated with closure and gate tracking surfaces.

#### M-066
- Files: evidence bundle manifest under repro run dir
- Command:
```bash
RUN_DIR=$(ls -td /Users/buildsomething/Source/ccl/doc/wasm/repro/startup-pipeline-* | head -n1)
test -f "$RUN_DIR/evidence-manifest.json" && rg -n 'commands|artifacts|diagnostics|assertions|sha256' "$RUN_DIR/evidence-manifest.json"
```
- Expected evidence line:
- evidence manifest includes commands, artifact hashes, diagnostics, assertions.

#### M-067 (G-12)
- Files: evidence bundle + logs
- Command:
```bash
RUN_DIR=$(ls -td /Users/buildsomething/Source/ccl/doc/wasm/repro/startup-pipeline-* | head -n1)
rg -n 'G-01|G-02|G-03|G-04|G-05|G-06|G-07|G-08|G-09|G-10|G-11|G-12' "$RUN_DIR"/evidence-manifest.json "$RUN_DIR"/logs/* 2>/dev/null || true
```
- Expected evidence line:
- reviewer can confirm all gate outcomes from bundle alone.

### 22.5 Gate Log Template (required after each gate)

Use this exact line after each gate run:

```text
PLAN_GATE {"gate":"G-<id>","status":"pass|fail","evidence":["<path-or-command>"],"next":"<next-step-id|playbook-id>"}
```

### 22.6 Stub-Dependency Cards (`M-068`..`M-071`)

#### M-068
- Files: `ccl/doc/wasm/js/make-real-image.mjs`
- Command:
```bash
rg -n 'missing-kernel-export|initializer-kind-unsupported-at-apply|required-symbol-unresolved' ccl/doc/wasm/js/make-real-image.mjs
```
- Expected evidence line:
- apply path has explicit required-binding failure reasons; no implicit fallback for missing ABI.

#### M-069
- Files: `ccl/scripts/wasm/check-startup-semantics.sh`
- Command:
```bash
test -x ccl/scripts/wasm/check-startup-semantics.sh && ccl/scripts/wasm/check-startup-semantics.sh
```
- Expected evidence line:
- script exits `0` and reports no forbidden startup bypass pattern regressions.

#### M-070
- Files: `$MRI_TOP`, `$MRI_SMOKE`
- Command:
```bash
for f in "$MRI_TOP" "$MRI_SMOKE"; do
  echo "=== $f"
  rg -n 'missing-kernel-export|initializer-kind-unsupported-at-apply|required-symbol-unresolved' "$f" || true
  ! rg -n 'trap from unimplemented subprim|wasm_subprims_trap|unimplemented subprim' "$f"
done
```
- Expected evidence line:
- no startup-lane trap signature from stubbed path; no required-binding ABI failure.

#### M-071 (G-13)
- Files: latest repro logs + focused lane logs
- Command:
```bash
RUN_DIR=$(ls -td /Users/buildsomething/Source/ccl/doc/wasm/repro/startup-pipeline-* | head -n1)
for f in "$MRI_TOP" "$MRI_SMOKE"; do
  ! rg -n 'missing-kernel-export|initializer-kind-unsupported-at-apply' "$f"
done
rg -n 'missing-kernel-export|initializer-kind-unsupported-at-apply' "$RUN_DIR"/logs/* || true
```
- Expected evidence line:
- required startup bindings are free of missing/stubbed ABI failures across focused and repro lanes.

### 22.7 Resume Closure Recompute Verification (`M-072`..`M-074`)

#### M-072
- Files: `ccl/scripts/wasm/recompute-resume-closure-matrix.sh`
- Command:
```bash
test -x ccl/scripts/wasm/recompute-resume-closure-matrix.sh || chmod +x ccl/scripts/wasm/recompute-resume-closure-matrix.sh
```
- Expected evidence line:
- checked-in recompute verifier is executable and available for unattended runs.

#### M-073
- Files: `/private/tmp/step93.doccheck.*`
- Command:
```bash
ccl/scripts/wasm/recompute-resume-closure-matrix.sh --output-prefix /private/tmp/step93.doccheck
wc -c /private/tmp/step93.doccheck.diff.signatures.txt /private/tmp/step93.doccheck.diff.trace-map.txt /private/tmp/step93.doccheck.diff.matrix.txt /private/tmp/step93.doccheck.diff.violations.txt /private/tmp/step93.doccheck.diff.profile-counts.txt /private/tmp/step93.doccheck.diff.trace-profiles.txt
```
- Expected evidence line:
- verifier exits `0` and all positive-parity diff files are `0` bytes.

#### M-074
- Files: `/private/tmp/step93.doccheck.negative.*`
- Command:
```bash
set +e
ccl/scripts/wasm/recompute-resume-closure-matrix.sh --output-prefix /private/tmp/step93.doccheck.negative --log /private/tmp/make-real-image.resume.applycontinue.reqfasload9.trace.log
echo "negative_exit=$?"
set -e
wc -c /private/tmp/step93.doccheck.negative.diff.signatures.txt /private/tmp/step93.doccheck.negative.diff.trace-map.txt /private/tmp/step93.doccheck.negative.diff.matrix.txt /private/tmp/step93.doccheck.negative.diff.violations.txt /private/tmp/step93.doccheck.negative.diff.profile-counts.txt /private/tmp/step93.doccheck.negative.diff.trace-profiles.txt
```
- Expected evidence line:
- verifier exits non-zero and negative diff output is non-empty on at least one artifact.
