# RPL-01 - Secure Runtime Gating

Status: in_progress  
Priority: P0  
Owner: Runtime/WASM replacement track  
Last Updated: 2026-02-09  
Parent Plan: `doc/wasm/runtime-replacement-master-plan.md`

## Scope

In scope:

- Define the MVP secure-only runtime startup contract.
- Specify required runtime capabilities and deterministic startup checks.
- Define explicit failure diagnostics and remediation guidance.
- Reconcile legacy portability-first language in docs with secure-only replacement direction.

Out of scope:

- Shared-memory queue implementation details (RPL-03).
- Storage V2 data model and merge logic (RPL-05/RPL-06).
- Module environment-sharing implementation (RPL-07).

## Dependencies

- RPL-00 governance process in use.

## Deliverables

1. Secure runtime gate matrix with required capabilities and boot checks.
2. Startup failure contract (error codes/messages + remediation mapping).
3. Documentation updates for secure-only MVP support policy and no-fallback behavior.
4. Validation plan for startup gate tests in smoke/harness lanes.

## Exit Criteria

- Required startup checks are defined and mapped to pass/fail behavior.
- Unsupported environments fail explicitly with actionable diagnostics.
- Docs do not simultaneously claim secure-only MVP and portability-first fallback for the same runtime lane.
- Startup gate checks are covered by deterministic validation steps.

## Current Notes

- Step 1 contradiction inventory v1 is now recorded in this ticket with line-level source references and resolution actions.
- Existing docs still include portability-first and single-runner-first assumptions in key places.
- Current ABI/microkernel docs are still baseline copy-based and optional shared-memory.
- Replacement direction requires secure-only startup posture for shared-memory and storage assumptions.

## Immediate Next Step

- Action: execute Step 2 by drafting the required capability matrix with check IDs and startup assertions derived from the Step 1 contradiction inventory.
- Why now: contradiction inventory exists; startup gate requirements can now be defined as concrete checks instead of high-level policy statements.
- Success evidence: matrix committed with check IDs, pass/fail criteria, and explicit mapping from contradiction IDs to replacement assertions.

## Step 1 Output - Contradiction Inventory (v1)

This table is the active contradiction tracker for RPL-01. Every row must keep `Status` and `Notes` current as remediation work lands.

| ID | Source | Contradiction | Required resolution action | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| C-01 | `doc/wasm/decisions.md:7` | ADR-0001 makes copy-based `kernel_request` responses the required baseline. | Supersede ADR language so shared-memory IPC is normative for hot paths; keep copy/message path only for bootstrap/control/diagnostics. | open | Primary handoff to RPL-03. |
| C-02 | `doc/wasm/decisions.md:52` | ADR-0006 defines single-runner portable baseline and deferred shared-heap threading. | Replace with secure-only MVP runtime stance: required worker/thread posture for startup, while CL thread semantics may still be deferred. | open | Handshake with RPL-02 and RPL-03. |
| C-03 | `doc/wasm/kernel-request-abi.md:3` | ABI spec is explicitly copy-based MVP with zero-copy as optional future extension. | Define ABI v2 transport contract where shared-memory channels are primary data-plane/hot-path mechanism. | open | Must remain explicit about control-plane use cases. |
| C-04 | `doc/wasm/js-microkernel-spec.md:14` | Microkernel goals and requirements retain single-thread compatibility/degrade-to-baseline behavior. | Rewrite execution modes to secure-only MVP with required capabilities and explicit unsupported-startup failure contract. | open | Include no-silent-fallback rule in failure section. |
| C-05 | `doc/wasm/project-overview.md:69` | Overview frames a portability ladder with message-passing/sandbox baseline and optional shared memory. | Reframe as secure-environment performance-first MVP; move portability/embeddable discussion to future non-MVP notes only. | open | Keep historical context only if clearly marked legacy. |
| C-06 | `doc/wasm/threads.md:7` | Threading doc marks shared-heap mode optional and single-runner as baseline target. | Rewrite to required startup threading/worker topology assumptions for MVP runtime architecture. | open | CL-level thread semantics can still remain out-of-scope for MVP. |
| C-07 | `doc/wasm/yield-resume.md:27` | Yield/resume guidance preserves portable baseline without SAB/Atomics and makes Stage 3 optional. | Re-scope document so secure capability prerequisites are assumed; treat non-secure mode as unsupported in MVP. | open | Keep explicit note if staged internals remain useful. |
| C-08 | `doc/wasm/interrupts.md:9` | Interrupt model centers portable single-runner baseline and optional shared-memory upgrade. | Align interrupt requirements with secure-only startup and required shared-memory runtime posture. | open | Ensure semantics remain deterministic at safepoints. |
| C-09 | `doc/wasm/ui-bridge-protocol.md:6` | UI bridge protocol assumes transport over copy-based `kernel_request` ABI. | Define shared-memory transport path for UI ingress/egress hot paths; retain message/copy channel only for non-hot/control paths. | open | Primary handoff to RPL-04. |
| C-10 | `doc/wasm/persistence-service-spec.md:7` | Persistence spec is memory-first snapshot + optional host backends, not Storage V2 object/ref model. | Mark this spec legacy for replacement track and author Storage V2 normative local-core contract. | open | Primary handoff to RPL-05. |
| C-11 | `doc/wasm/mvp-unattended-execution-plan.md:54` | MVP unattended plan sets `memory-snapshot` as default persistence lane. | Add explicit replacement-track override note and migration path to Storage V2/secure-runtime gating docs. | open | Keep current lane documented as legacy operational baseline until cutover. |
| C-12 | `doc/wasm/porting-status.md:60` | Current status report treats memory-snapshot persistence as default unattended posture. | Split status into current-lane vs replacement-lane and prevent old default from appearing as future architecture target. | open | Avoid deleting current facts; relabel scope. |
| C-13 | `doc/wasm/roadmap.md:18` | Roadmap defers concurrency and states single-threaded baseline first. | Update roadmap to replacement sequence where secure runtime gating and shared-memory IPC are prerequisite, not optional late-phase work. | open | Coordinate with RPL-00 governance cadence. |
| C-14 | `web-ide/phase-8/implementation-plan.md:46` | Phase 8 plan locks memory-snapshot decoupling/defaults and declares runtime architecture rewrite out-of-scope. | Add replacement-track supersession notes and explicit dependency on runtime replacement milestones before front-end release execution. | open | Keep pre-existing release work as legacy lane, not target architecture. |

## Detailed Work Breakdown

### Step 1 - Contradiction Inventory

- Status: done
- Notes:
  - Contradiction inventory v1 is recorded in this document (`C-01` through `C-14`).
  - Each contradiction now has a required resolution action and status marker for resumable execution.
- Next:
  - Keep this table updated as remediation PRs land; mark each item `in_progress` then `done` with evidence notes.

### Step 2 - Required Capability Matrix Definition

- Status: planned
- Notes:
  - Matrix must distinguish mandatory vs optional capabilities for MVP.
  - Must encode browser support policy consistent with replacement goals.
- Next:
  - Author capability table with startup check IDs and required runtime assertions.

### Step 3 - Failure Semantics and Diagnostics

- Status: planned
- Notes:
  - Failure outputs must be explicit and actionable; no silent degradation.
  - Must include remediation guidance per failed check.
- Next:
  - Define diagnostic schema and message contract for startup failure handling.

### Step 4 - Loader/Harness Integration Plan

- Status: planned
- Notes:
  - Startup checks must be integrated into loader/harness entrypoints.
  - Must preserve deterministic unattended behavior in supported secure deployments.
- Next:
  - Define where checks execute and how failures are surfaced in existing smoke harnesses.

### Step 5 - Validation and Regression Gates

- Status: planned
- Notes:
  - Need deterministic test lanes for both pass and fail cases.
- Next:
  - Add startup-gate validation checklist and required command set.

### Step 6 - Master-Plan Sync and Handoff

- Status: planned
- Notes:
  - Ticket changes must update RPL-01 block in master plan in the same change.
- Next:
  - Update master plan after each step completion with precise next-step evidence.

## Test and Validation Plan

- Spec validation:
  - Verify required checks and failure rules are fully enumerated.
- Integration validation:
  - Confirm loader/harness emits defined failure diagnostics when checks fail.
- Regression validation:
  - Confirm supported secure environment still passes startup gates deterministically.

## Risks and Mitigations

- Risk: ambiguous capability requirements cause inconsistent startup behavior.
  - Mitigation: define check IDs, required outcomes, and fixed diagnostics schema.
- Risk: doc contradictions remain and cause implementation drift.
  - Mitigation: maintain explicit contradiction inventory and resolution status.
- Risk: test lanes do not cover unsupported-startup paths.
  - Mitigation: include explicit fail-case tests and expected error assertions.

## Change Log

- 2026-02-09: Initial subplan scaffold created; execution steps and evidence criteria defined.
- 2026-02-09: Step 1 contradiction inventory v1 added (`C-01`..`C-14`); ticket moved to `in_progress`.
