# BPL-03 - Frame and Debug Metadata Model

Status: done  
Priority: P0  
Owner: Compiler/backend migration track  
Last Updated: 2026-02-09  
Parent Plan: `doc/wasm/backend-migration-master-plan.md`

## Scope

In scope:

- Define frame/debug metadata contract for the WASM-native backend path.
- Consume frozen runtime worker topology/lifecycle artifacts from RPL-02.
- Produce explicit mapping evidence required to clear dependency row `X-02`.

Out of scope:

- Runtime worker topology or lifecycle design changes (RPL-02 ownership).
- Shared-memory IPC wire-protocol design (RPL-03 ownership).
- Numeric/lowering modernization implementation (BPL-04/BPL-05 ownership).

## Dependencies

- BPL-02 contract baseline (`CON-01`..`CON-08`, `BCL-01`..`BCL-12`).
- RPL-02 frozen Step 1/Step 2 IDs (`WTOP-*`, `WSEQ-*`, `WLCS-*`, `WLCT-*`, `WLCR-*`).

## Deliverables

1. Explicit runtime-artifact consumption map for frame/debug model design.
2. Frame ownership and capture-point rules tied to runtime role boundaries.
3. Lifecycle-aware debug/state validity rules tied to transition and policy IDs.
4. Evidence package sufficient to satisfy dependency row `X-02` clear criteria.

## Exit Criteria

- Every required RPL-02 ID class (`WTOP-*`, `WSEQ-*`, `WLCS-*`, `WLCT-*`, `WLCR-*`) is consumed by explicit BPL-03 mapping IDs.
- Consumption rules are deterministic and test-lane assertable.
- `X-02` clear evidence is synchronized across this ticket, runtime ticket, dependency matrix, and both master plans.

## Current Notes

- Step 1 consumption mapping v1 is now published in this ticket with explicit IDs (`B3R-*`, `B3S-*`, `B3L-*`, `B3T-*`, `B3P-*`).
- Mapping consumes all required RPL-02 artifact classes and preserves strict no-fallback semantics.
- `X-02` evidence package now has explicit backend-consumption proof and can be treated as cleared for dependency gating.
- Step 2 closure is complete: `FDC-01`..`FDC-10` now have explicit `B3*` class coverage validation with hardened clause wording.

## Immediate Next Step

- Action: consume finalized frame/debug contract baseline (`FDC-01`..`FDC-10`) in downstream backend tickets (`BPL-04`, `BPL-05`, `BPL-06`) and keep revisions additive.
- Why now: Step 2 closure criteria are satisfied and `X-02` is clear, so this ticket shifts to additive-only maintenance.
- Success evidence: downstream planning/implementation artifacts reference `FDC-*` and `B3*` IDs directly without reopening frozen runtime ID semantics.

## Step 1 Output - RPL-02 Consumption Mapping (v1)

### Worker Role Boundary Consumption

| consumption_id | runtime_input_id | consumed as | deterministic BPL-03 rule | test-lane assertion |
| --- | --- | --- | --- | --- |
| B3R-01 | WTOP-01 | startup-orchestrator frame authority | Startup/control frame records MUST be attributed to orchestrator role only. | Orchestrator events never carry runtime/kernel/storage role ownership tags. |
| B3R-02 | WTOP-02 | runtime-execution frame owner | Executable Lisp/runtime frames MUST be attributed to runtime worker role. | Runtime call stacks fail validation if top frame owner is not `WTOP-02`. |
| B3R-03 | WTOP-03 | kernel-service frame boundary | Kernel service frames MUST remain isolated from runtime-execution frame namespace. | Kernel I/O trace rows never reuse runtime frame-class identifiers. |
| B3R-04 | WTOP-04 | storage-durability frame boundary | Storage durability operations MUST emit storage-owned frame/debug metadata. | OPFS/SyncAccessHandle traces carry `WTOP-04` owner tag only. |
| B3R-05 | WTOP-05 | UI-bridge frame boundary | UI bridge hot-path frames MUST be attributed to bridge role in UI lanes. | UI lane traces fail if required bridge frames are absent or misattributed. |

### Startup Sequence Consumption

| consumption_id | runtime_input_id | consumed as | deterministic BPL-03 rule | test-lane assertion |
| --- | --- | --- | --- | --- |
| B3S-01 | WSEQ-01 | preflight capture gate | Debug/frame capture MUST be marked pre-runtime until preflight passes. | No runtime frame-class records before successful preflight marker. |
| B3S-02 | WSEQ-02 | storage-readiness gate | Storage-bound frame classes become valid only after storage readiness. | Storage frame records before `STORAGE_READY` are treated invalid. |
| B3S-03 | WSEQ-03 | kernel-readiness gate | Kernel-bound frame classes become valid only after kernel readiness. | Kernel frame records before `KERNEL_IO_READY` fail schema checks. |
| B3S-04 | WSEQ-04 | runtime-readiness gate | Runtime frame capture begins only after runtime ownership handshake. | Runtime frame-class records require `RUNTIME_READY` checkpoint. |
| B3S-05 | WSEQ-05 | ui-bridge readiness gate | UI bridge frame capture is mandatory only in `ui_runtime` lane after bridge readiness. | `ui_runtime` runs fail if bridge frame-class events lack ready checkpoint. |
| B3S-06 | WSEQ-06 | topology-commit gate | Frame/debug model must consume only sessions with terminal topology summary. | Sessions without terminal topology artifact are rejected from BPL-03 fixtures. |

### Lifecycle State Consumption

| consumption_id | runtime_input_id | consumed as | deterministic BPL-03 rule | test-lane assertion |
| --- | --- | --- | --- | --- |
| B3L-01 | WLCS-01 | pending-state debug contract | `START_PENDING` roles MUST emit no executable frame payloads. | Pending-state events have empty frame-payload fields. |
| B3L-02 | WLCS-02 | starting-state debug contract | `STARTING` roles MAY emit startup diagnostics but no steady-state frame claims. | Starting-state frames are flagged as provisional. |
| B3L-03 | WLCS-03 | ready-state debug contract | `READY` is the only non-fatal state permitting steady-state frame validity. | Ready-state traces are required for pass-lane fixtures. |
| B3L-04 | WLCS-04 | degraded-state debug contract | `DEGRADED` traces MUST be marked unstable and transition-bound. | Degraded traces fail if marked as stable frames. |
| B3L-05 | WLCS-05 | restarting-state debug contract | `RESTARTING` traces MUST version frame ownership by restart attempt. | Restarted sessions require incremented restart-attempt tags. |
| B3L-06 | WLCS-06 | fatal-state terminal contract | `FATAL` state MUST terminate frame/debug stream for the session. | No non-terminal frame events allowed after fatal marker. |

### Lifecycle Transition Consumption

| consumption_id | runtime_input_id | consumed as | deterministic BPL-03 rule | test-lane assertion |
| --- | --- | --- | --- | --- |
| B3T-01 | WLCT-01 | pending-to-starting transition hook | Frame stream MUST open startup-provisional channel at transition entry. | Transition event required before any `STARTING` frame record. |
| B3T-02 | WLCT-02 | starting-to-ready transition hook | Transition MUST flip frame validity from provisional to steady-state. | Ready-frame records require prior `WLCT-02` event. |
| B3T-03 | WLCT-03 | startup-fail terminal transition | Startup-failure transition MUST emit terminal debug marker and stop stream. | No post-failure steady-state frames after `WLCT-03`. |
| B3T-04 | WLCT-04 | ready-to-degraded transition | Transition MUST downgrade frame stability classification. | First degraded record must reference `WLCT-04`. |
| B3T-05 | WLCT-05 | degraded-to-restarting transition | Transition MUST start restart-attempt frame namespace. | Restart namespace version increments at `WLCT-05`. |
| B3T-06 | WLCT-06 | degraded-to-fatal transition | Transition MUST hard-stop frame stream with terminal fail code context. | Fatal summary includes `WLCT-06` transition reference. |
| B3T-07 | WLCT-07 | restarting-to-ready transition | Transition MUST re-enable steady-state frame validity for same role identity. | Post-restart steady-state frames require `WLCT-07` checkpoint. |
| B3T-08 | WLCT-08 | restart-fail terminal transition | Transition MUST terminate stream and preserve restart-failure context. | No frame records allowed after `WLCT-08` terminal event. |
| B3T-09 | WLCT-09 | ownership-violation terminal transition | Transition MUST mark ownership breach and invalidate further frame trust. | Ownership violation triggers immediate terminal classification. |
| B3T-10 | WLCT-10 | fallback-violation terminal transition | Transition MUST encode policy-violation terminal reason and abort stream. | Presence of `WLCT-10` requires terminal `allow_fallback=false` summary. |
| B3T-11 | WLCT-11 | lane-invariant terminal transition | Transition MUST mark lane-role mismatch as terminal frame/debug failure. | Lane mismatch transition requires terminal error summary. |

### Role Policy Consumption

| consumption_id | runtime_input_id | consumed as | deterministic BPL-03 rule | test-lane assertion |
| --- | --- | --- | --- | --- |
| B3P-01 | WLCR-01 | orchestrator policy boundary | Orchestrator frame/debug stream MUST be non-restartable (`restart_budget=0`). | Orchestrator traces reject restart-attempt values > 0. |
| B3P-02 | WLCR-02 | runtime policy boundary | Runtime-execution frame validity MUST terminate on first policy/health breach. | Runtime role traces reject restart transitions entirely. |
| B3P-03 | WLCR-03 | kernel policy boundary | Kernel role MAY restart once with bounded restart-attempt semantics. | Kernel traces allow max one restart-attempt increment. |
| B3P-04 | WLCR-04 | storage policy boundary | Storage role MUST be terminal on durability breach (no fallback profile). | Storage traces reject non-fatal post-breach continuation. |
| B3P-05 | WLCR-05 | bridge policy boundary | Bridge role MAY restart once in UI lanes; repeat failure is terminal. | UI bridge traces enforce restart budget of one. |

### `X-02` Consumption Assertions (Normative)

1. All required RPL-02 identifier classes are now consumed by explicit BPL-03 IDs (`B3R-*`, `B3S-*`, `B3L-*`, `B3T-*`, `B3P-*`).
2. Every consumption rule is deterministic and includes a corresponding test-lane assertion.
3. No new runtime identifier aliases were introduced; frozen runtime IDs are referenced directly.

## Step 2 Output - Normative Frame/Debug Contract (draft v1)

| invariant_id | normative frame/debug contract invariant (machine-actionable) | mapping anchors | source anchors |
| --- | --- | --- | --- |
| FDC-01 | Every frame/debug event **MUST** include `role_owner_id`, and that field **MUST** be one of `WTOP-01`..`WTOP-05` with lane-class validity from RPL-02 (`headless_runtime` allows `WTOP-01`..`WTOP-04`; `ui_runtime` allows `WTOP-01`..`WTOP-05`). Events **MUST NOT** cross-attribute runtime, kernel, storage, and bridge ownership domains. | `B3R-01`..`B3R-05` | `doc/wasm/tickets/RPL-02-worker-topology-and-thread-bootstrap.md:64`; `doc/wasm/tickets/RPL-02-worker-topology-and-thread-bootstrap.md:68` |
| FDC-02 | Frame/debug capture **MUST** include `startup_checkpoint_id` and obey startup sequencing gates. Runtime, kernel, storage, and UI bridge frame classes **MUST NOT** appear before their corresponding readiness checkpoints (`WSEQ-02`..`WSEQ-05`). | `B3S-01`..`B3S-06` | `doc/wasm/tickets/RPL-02-worker-topology-and-thread-bootstrap.md:83`; `doc/wasm/tickets/RPL-02-worker-topology-and-thread-bootstrap.md:88` |
| FDC-03 | Host-to-Lisp and toplevel entry/exit boundaries **MUST** maintain `last_lisp_frame` via manual cstack wrappers (`wasm_enter_lisp_frame`/`wasm_exit_lisp_frame`) for every foreign-to-Lisp transition. Frame/debug records are invalid if this boundary discipline is bypassed. | `B3R-02`, `B3S-04` | `doc/wasm/ABI.md:75`; `lisp-kernel/wasm-cstack.c:76`; `lisp-kernel/wasm-cstack.c:85`; `lisp-kernel/wasm-kernel-stubs.c:1744`; `lisp-kernel/wasm-kernel-stubs.c:2195` |
| FDC-04 | Native frame-pointer and trap-context fields are compatibility-only for WASM bring-up. Debug contracts **MUST** set `frame_pointer_source=metadata` and **MUST NOT** assume a native frame-pointer source while `%current-frame-ptr` and trap context remain placeholder-backed. | `B3L-01`..`B3L-03` | `compiler/WASM/wasm2.lisp:1371`; `compiler/WASM/wasm2.lisp:1373`; `lisp-kernel/platform-wasm32.h:42`; `lisp-kernel/platform-wasm32.h:46` |
| FDC-05 | Every frame/debug event **MUST** include `lifecycle_state_id` and classification aligned with `WLCS-*` semantics (`pending`, `provisional`, `stable`, `unstable`, `restarting`, `terminal`). State classification **MUST** preserve deterministic validity rules. | `B3L-01`..`B3L-06` | `doc/wasm/tickets/RPL-02-worker-topology-and-thread-bootstrap.md:114`; `doc/wasm/tickets/RPL-02-worker-topology-and-thread-bootstrap.md:119` |
| FDC-06 | Transition semantics **MUST** be first-class in frame/debug streams: each non-initial state change **MUST** include `transition_id` referencing the corresponding `WLCT-*` identifier, and terminal transitions **MUST** halt further non-terminal frame emission. | `B3T-01`..`B3T-11` | `doc/wasm/tickets/RPL-02-worker-topology-and-thread-bootstrap.md:125`; `doc/wasm/tickets/RPL-02-worker-topology-and-thread-bootstrap.md:135` |
| FDC-07 | Restart-attempt metadata **MUST** include integer `restart_attempt` and `restart_budget` fields aligned to role-specific policy budgets (`WLCR-*`). Implementations **MUST NOT** emit restart attempt values above policy limits for the corresponding role/lane class. | `B3P-01`..`B3P-05`, `B3T-05`, `B3T-07` | `doc/wasm/tickets/RPL-02-worker-topology-and-thread-bootstrap.md:141`; `doc/wasm/tickets/RPL-02-worker-topology-and-thread-bootstrap.md:145` |
| FDC-08 | No-fallback policy is normative for frame/debug behavior: after fallback/policy/lane-violation terminals, streams **MUST** emit one terminal summary with `terminal=true`, `allow_fallback=false`, and failure code context, and **MUST NOT** emit steady-state events thereafter. | `B3L-06`, `B3T-10`, `B3T-11`, `B3P-01`..`B3P-05` | `doc/wasm/tickets/RPL-02-worker-topology-and-thread-bootstrap.md:119`; `doc/wasm/tickets/RPL-02-worker-topology-and-thread-bootstrap.md:134`; `doc/wasm/tickets/RPL-02-worker-topology-and-thread-bootstrap.md:135`; `doc/wasm/backend-tickets/BPL-02-wasm-native-backend-contract.md:110`; `doc/wasm/backend-tickets/BPL-02-wasm-native-backend-contract.md:112` |
| FDC-09 | Dynamic-binding/unwind metadata **MUST** represent PROGV sentinel-chain boundaries for `lane_class in {headless_runtime, ui_runtime}`. Debug unwind traces **MUST NOT** assume TSP-frame semantics unless ADR-0011 is retired and replacement stack-model identifiers are published in `doc/wasm/decisions.md` with synchronized runtime/backend ticket updates. | `B3T-03`, `B3L-03`, `B3L-06` | `doc/wasm/decisions.md:94`; `doc/wasm/decisions.md:100`; `lisp-kernel/wasm-subprims-provider.c:5402`; `lisp-kernel/wasm-subprims-provider.c:5431`; `lisp-kernel/wasm-subprims-provider.c:5481` |
| FDC-10 | Tailcall/jump wrapper subprims currently execute via `_SPfuncall` without frame reuse. Frame/debug contracts **MUST** mark these paths as `tail_optimized=false`. Tail-frame reuse claims are prohibited until the wrapper entrypoints (`_SPtfuncallgen`, `_SPtfuncallslide`, `_SPjmpsym`, `_SPtcallsymgen`, `_SPtcallsymslide`, `_SPtcallnfngen`, `_SPtcallnfnslide`) no longer dispatch through `_SPfuncall` in `wasm-subprims-provider.c` and this ticket records that cutover. | `B3R-02`, `B3L-03` | `lisp-kernel/wasm-subprims-provider.c:2083`; `lisp-kernel/wasm-subprims-provider.c:2086` |

### Step 2 Closure Output - `B3*` Coverage Validation (v1)

| mapping_class | required_ids | required_count | covered_by_invariants | uncovered_ids | closure_result |
| --- | --- | --- | --- | --- | --- |
| `B3R-*` | `B3R-01`..`B3R-05` | 5 | `FDC-01`, `FDC-03`, `FDC-10` | none | covered |
| `B3S-*` | `B3S-01`..`B3S-06` | 6 | `FDC-02`, `FDC-03` | none | covered |
| `B3L-*` | `B3L-01`..`B3L-06` | 6 | `FDC-04`, `FDC-05`, `FDC-08`, `FDC-09` | none | covered |
| `B3T-*` | `B3T-01`..`B3T-11` | 11 | `FDC-06`, `FDC-08`, `FDC-09` | none | covered |
| `B3P-*` | `B3P-01`..`B3P-05` | 5 | `FDC-07`, `FDC-08` | none | covered |

Closure assertions:

1. Full `B3*` class coverage is satisfied across `FDC-01`..`FDC-10`.
2. No uncovered mapping class or uncovered ID set remains.
3. No-fallback and ownership clauses are now hardened with explicit field-level requirements.
4. Lane-class and tailcall cutover triggers are explicit (`FDC-01`, `FDC-09`, `FDC-10`) and no longer rely on implicit interpretation.

## Detailed Work Breakdown

### Step 1 - Runtime Artifact Intake and Mapping

- Status: done
- Notes:
  - Published explicit BPL-03 consumption mapping for all required RPL-02 ID classes.
  - Added deterministic assertions and test-lane checks for each mapping row.
- Next:
  - Keep `B3*` mapping IDs frozen while Step 2 contract sections are authored.

### Step 2 - Frame/Debug Contract Drafting

- Status: done
- Notes:
  - Step 2 closure validated full `B3*` class coverage across `FDC-01`..`FDC-10`.
  - Ambiguous clauses were hardened with explicit machine-field requirements (`role_owner_id`, `startup_checkpoint_id`, `lifecycle_state_id`, `transition_id`, `restart_attempt`, `restart_budget`, `terminal`).
- Next:
  - Preserve additive-only evolution for frame/debug contract semantics; introduce future changes via new `FDC-*` IDs.

### Step 3 - Dependency Closure and Sync

- Status: done
- Notes:
  - `X-02` dependency evidence package now includes explicit BPL-03 consumption mapping.
- Next:
  - Maintain cross-plan sync if any `B3*` mapping IDs are revised.

## Test and Validation Plan

- Mapping completeness validation:
  - Verify all required runtime ID classes (`WTOP-*`, `WSEQ-*`, `WLCS-*`, `WLCT-*`, `WLCR-*`) appear in Step 1 tables.
- Determinism validation:
  - Verify each mapping row contains one deterministic rule and one machine-test assertion.
- Dependency validation:
  - Verify dependency matrix `X-02` notes cite this ticket as explicit BPL-03 consumption evidence.
- Contract traceability validation:
  - Verify every Step 1 mapping class (`B3R-*`, `B3S-*`, `B3L-*`, `B3T-*`, `B3P-*`) is referenced by at least one `FDC-*` invariant.

## Risks and Mitigations

- Risk: frame/debug contract drifts from frozen runtime identifiers.
  - Mitigation: forbid alias IDs; require direct `WTOP-*`/`WSEQ-*`/`WLCS-*`/`WLCT-*`/`WLCR-*` references.
- Risk: mapping is documented but not testable.
  - Mitigation: require one machine assertion per mapping row.
- Risk: `X-02` appears clear without synchronized plan updates.
  - Mitigation: update dependency matrix and both master plans in the same change when mapping status changes.

## Change Log

- 2026-02-09: Initial BPL-03 subplan created with explicit RPL-02 artifact consumption mapping (`B3R-*`, `B3S-*`, `B3L-*`, `B3T-*`, `B3P-*`) and `X-02` dependency-evidence assertions.
- 2026-02-09: Published Step 2 draft v1 frame/debug contract invariants (`FDC-01`..`FDC-10`) with explicit `B3*` traceability coverage and source anchors.
- 2026-02-09: Closed Step 2 by validating full `B3*` class coverage across `FDC-01`..`FDC-10` and hardening ambiguous clauses with explicit field-level requirements.
- 2026-02-09: Re-ran Step 2 closure validation; clarified lane-class ownership and explicit cutover triggers in `FDC-01`, `FDC-09`, and `FDC-10` without changing `B3*` coverage results.
