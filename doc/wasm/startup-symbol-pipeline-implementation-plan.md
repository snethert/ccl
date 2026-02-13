# WASM Startup Symbol Pipeline: Detailed Implementation Plan (Source-Scope v1)

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
- `CCL_WASM_STARTUP_BINDING_MAP_EMIT_ALL_FUNCTIONS`
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

1. Switch parser implementation language to Common Lisp scanner first, preserving JSON schema + diagnostics contracts.
2. Implement/verify schemas and constants.
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
