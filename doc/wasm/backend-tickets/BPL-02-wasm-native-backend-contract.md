# BPL-02 - WASM-Native Backend Contract

Status: done  
Priority: P0  
Owner: Compiler/backend migration track  
Last Updated: 2026-02-09  
Parent Plan: `doc/wasm/backend-migration-master-plan.md`

## Scope

In scope:

- Define the WASM-native backend contract surface (calling/value/memory/control-flow invariants).
- Bind backend contract assumptions to frozen runtime startup-gate IDs.
- Produce deterministic evidence to clear dependency row `X-01`.

Out of scope:

- Backend lowering/codegen implementation (BPL-04/BPL-05).
- Runtime startup-gate definition changes (RPL-01 ownership).
- Runtime worker topology design (RPL-02 ownership).

## Dependencies

- BPL-01 assumption inventory (source assumptions and strategy posture).
- RPL-01 startup-gate contract (`SRG-01`..`SRG-12` frozen IDs).

## Deliverables

1. WASM-native backend contract outline with normative invariant sections.
2. Assumption-to-startup-gate linkage table with explicit `SRG-*` references.
3. Evolution policy and compatibility constraints for contract revisions.
4. Cross-track evidence package sufficient to clear dependency row `X-01`.

## Exit Criteria

- Contract draft explicitly references all required runtime startup-gate IDs.
- No backend/runtime assumption linkage relies on unnamed or implicit capability claims.
- `X-01` clear criteria are met and synchronized in dependency matrix + both master plans.
- Follow-on contract drafting steps are defined without reopening `SRG-*` identifier semantics.

## Current Notes

- `X-01` required explicit BPL-02 references to frozen runtime checks.
- RPL-01 Step 6 froze handoff identifiers (`SRG-*`, `RPL01-E*`, `LHI-*`, `VRG-*`) for downstream use.
- Step 1 linkage output in this ticket now provides explicit `SRG-01`..`SRG-12` references for contract consumption.
- Step 2 closure is complete: `CON-01`..`CON-08` now have explicit `BCL-01`..`BCL-12` traceability coverage with no uncovered linkage rows.

## Immediate Next Step

- Action: consume finalized contract baseline (`CON-01`..`CON-08`) in downstream backend tickets (`BPL-03`, `BPL-04`, `BPL-05`) and keep revisions additive.
- Why now: Step 2 closure is complete, so highest-value work is implementation-slice planning against a stable contract baseline.
- Success evidence: downstream backend ticket outputs reference `CON-*` and `BCL-*` IDs directly without reopening frozen startup-gate semantics.

## Step 1 Output - Startup-Gate Linkage Matrix (`X-01` Evidence v1)

This table is the normative BPL-02 linkage proof used to clear dependency row `X-01`.

| linkage_id | runtime startup gate | backend contract dependency assertion | linked BPL-01 assumptions | contract impact lane |
| --- | --- | --- | --- | --- |
| BCL-01 | `SRG-01` | Shared-memory backend ABI paths are valid only in cross-origin-isolated startup contexts. | `ARM-ASSUMP-006`, `ARM-ASSUMP-014` | calling + runtime boundary |
| BCL-02 | `SRG-02` | Shared command/response buffers require SAB constructor/allocation capability at startup. | `ARM-ASSUMP-002`, `ARM-ASSUMP-011`, `ARM-ASSUMP-014` | calling + memory |
| BCL-03 | `SRG-03` | Blocking call-boundary coordination requires worker-safe Atomics wait/notify behavior. | `ARM-ASSUMP-006`, `ARM-ASSUMP-014` | calling + control-flow |
| BCL-04 | `SRG-04` | Thread-aware backend contract assumes WASM shared-memory/thread primitives are available. | `ARM-ASSUMP-006`, `ARM-ASSUMP-011` | calling + lowering boundary |
| BCL-05 | `SRG-05` | Backend/runtime call ownership presumes required runtime worker roles are live before entry. | `ARM-ASSUMP-006`, `ARM-ASSUMP-014` | runtime boundary |
| BCL-06 | `SRG-06` | Persistent backend metadata/artifact lanes rely on OPFS-capable worker storage path. | `ARM-ASSUMP-011`, `ARM-ASSUMP-014` | memory + persistence boundary |
| BCL-07 | `SRG-07` | Durable metadata mutation semantics assume SyncAccessHandle worker path availability. | `ARM-ASSUMP-011`, `ARM-ASSUMP-014` | memory + persistence boundary |
| BCL-08 | `SRG-08` | Hot-path backend call transport is shared-memory-first, not copy/message fallback. | `ARM-ASSUMP-002`, `ARM-ASSUMP-007`, `ARM-ASSUMP-011` | calling + transport |
| BCL-09 | `SRG-09` | Backend-visible bridge effects in hot paths must remain compatible with shared-channel routing. | `ARM-ASSUMP-006`, `ARM-ASSUMP-011` | runtime boundary + effects |
| BCL-10 | `SRG-10` | Replacement-lane contract semantics assume Storage V2 profile, not memory-snapshot-default mode. | `ARM-ASSUMP-011`, `ARM-ASSUMP-014` | persistence profile |
| BCL-11 | `SRG-11` | Contract forbids degraded/fallback execution semantics in replacement lanes. | `ARM-ASSUMP-002`, `ARM-ASSUMP-006`, `ARM-ASSUMP-014` | contract policy |
| BCL-12 | `SRG-12` | Contract explicitly assumes required runtime thread capability while CL thread semantics remain deferred. | `ARM-ASSUMP-006`, `ARM-ASSUMP-011` | thread model boundary |

### `X-01` Clearance Assertions (Normative)

1. All frozen runtime check IDs `SRG-01`..`SRG-12` are explicitly referenced in this ticket.
2. Cross-track-sensitive assumptions from BPL-01 (`ARM-ASSUMP-002`, `ARM-ASSUMP-006`, `ARM-ASSUMP-011`, `ARM-ASSUMP-014`) are linked to startup checks.
3. No alias IDs or renamed startup-check identifiers are introduced.
4. This satisfies the matrix clear criterion: "RPL-01 capability check IDs frozen and referenced by BPL-02."

## Detailed Work Breakdown

### Step 1 - Runtime Linkage and `X-01` Evidence

- Status: done
- Notes:
  - Startup-gate linkage matrix now references all `SRG-01`..`SRG-12` IDs explicitly.
  - Cross-track assumption anchors are linked to BPL-01 inventory IDs.
- Next:
  - Keep `SRG-*` identifiers frozen while contract invariants are authored in Step 2.

### Step 2 - Contract Invariant Drafting

- Status: done
- Notes:
  - Step 2 draft v1 matured to closure with explicit traceability validation for all linkage rows (`BCL-01`..`BCL-12`).
  - Focus areas are now finalized for v1: startup preconditions, calling/value boundary semantics, transport profile, persistence profile, and contract evolution policy.
- Next:
  - Maintain additive-only contract evolution; route any semantic changes through new `CON-*` identifiers instead of rewriting closed invariants.

### Step 2 Output - Normative Contract Invariants (v1)

| invariant_id | normative contract invariant (machine-actionable) | linkage references |
| --- | --- | --- |
| CON-01 | The backend contract **MUST** activate only when secure startup preconditions pass (`SRG-01`..`SRG-04`). If any required capability check fails, contract activation **MUST** fail fast and **MUST NOT** continue in replacement mode. | `BCL-01`, `BCL-02`, `BCL-03`, `BCL-04`, `BCL-11` |
| CON-02 | Runtime-bound backend entrypoints **MUST** execute only after required runtime ownership/lifecycle gates are satisfied (`SRG-05`, `SRG-12`). The contract **MUST NOT** assume CL-thread semantics beyond declared runtime thread capability. | `BCL-05`, `BCL-12`, `BCL-11` |
| CON-03 | Subprim dispatch **MUST** use table-index semantics and a validated compiler/provider mapping. Implementations **MUST NOT** derive executable targets from address arithmetic (`SUBPRIMS_BASE`-style behavior). Mapping mismatch **MUST** raise deterministic contract failure. | `BCL-02`, `BCL-08`, `BCL-11` |
| CON-04 | Calling/value boundary behavior **MUST** preserve contract-defined argument/result conventions and explicit runtime context ownership. Contract paths **MUST NOT** depend on undeclared implicit global state for call ownership or bridge-visible effects. | `BCL-05`, `BCL-08`, `BCL-09`, `BCL-12` |
| CON-05 | Entrypoint resolution **MUST** be manifest-driven and versioned. Fixed numeric slot assumptions are compatibility-only and **MUST NOT** be normative in contract v1. Loader/manifest disagreement **MUST** fail deterministically. | `BCL-02`, `BCL-06`, `BCL-07`, `BCL-10` |
| CON-06 | Hot-path backend transport **MUST** be shared-memory/Atomics first (`SRG-08`, `SRG-09`). Copy/message fallback on replacement lanes **MUST NOT** be treated as contract-compliant execution. | `BCL-08`, `BCL-09`, `BCL-11` |
| CON-07 | Backend persistence/profile behavior **MUST** target replacement-lane storage semantics (`SRG-06`, `SRG-07`, `SRG-10`) and **MUST NOT** silently downgrade to memory-snapshot-default semantics for replacement contract lanes. | `BCL-06`, `BCL-07`, `BCL-10`, `BCL-11` |
| CON-08 | Contract evolution **MUST** preserve frozen identifier traceability (`SRG-*`, `BCL-*`) and explicit no-fallback policy. New semantics **MUST** be introduced via additive invariant/version identifiers, and alias/rename drift **MUST NOT** occur without synchronized linkage updates. | `BCL-11`, `BCL-12` |

### Step 2 Closure Output - Linkage Traceability Validation (v1)

| linkage_id | covered_by_invariants | closure_result | note |
| --- | --- | --- | --- |
| BCL-01 | `CON-01` | covered | Startup precondition lane covered with explicit fail-fast/no-fallback semantics. |
| BCL-02 | `CON-01`, `CON-03`, `CON-05` | covered | Memory/dispatch/manifest lanes covered without numeric-slot normativity. |
| BCL-03 | `CON-01` | covered | Atomics coordination requirement is contract-gated at activation boundary. |
| BCL-04 | `CON-01` | covered | Thread/shared-memory primitive requirement is startup-gated and explicit. |
| BCL-05 | `CON-02`, `CON-04` | covered | Runtime ownership prerequisites and call-boundary semantics are both explicit. |
| BCL-06 | `CON-05`, `CON-07` | covered | OPFS-backed persistence contract is explicit in entrypoint and profile lanes. |
| BCL-07 | `CON-05`, `CON-07` | covered | Durable mutation semantics preserved via manifest + storage profile requirements. |
| BCL-08 | `CON-03`, `CON-04`, `CON-06` | covered | Transport and dispatch lanes enforce shared-memory-first contract path. |
| BCL-09 | `CON-04`, `CON-06` | covered | Bridge-visible effects remain bounded to shared-channel contract behavior. |
| BCL-10 | `CON-05`, `CON-07` | covered | Storage V2 profile requirement is explicit and no silent downgrade is allowed. |
| BCL-11 | `CON-01`, `CON-02`, `CON-03`, `CON-06`, `CON-07`, `CON-08` | covered | No-fallback policy is reinforced across activation, transport, persistence, and evolution lanes. |
| BCL-12 | `CON-02`, `CON-04`, `CON-08` | covered | Runtime thread-capability boundary is explicit and alias/rename drift is disallowed. |

Closure assertions:

1. All linkage rows `BCL-01`..`BCL-12` are covered by at least one `CON-*` invariant.
2. No fallback-policy ambiguity remains: `CON-01`, `CON-06`, `CON-07`, and `CON-08` explicitly prohibit degraded replacement-lane execution semantics.
3. Revision policy is additive-only for v1 baseline semantics (`CON-08`), preventing silent contract drift.

### Step 3 - Master/Matrix Synchronization

- Status: done
- Notes:
  - `X-01` evidence change requires synchronized updates to dependency matrix and both master plans.
- Next:
  - Preserve synchronized update discipline for all subsequent BPL-02 revisions.

## Test and Validation Plan

- Linkage validation:
  - Verify all `SRG-01`..`SRG-12` IDs are referenced by explicit row in Step 1 output.
- Consistency validation:
  - Verify linked BPL-01 assumption IDs are valid inventory rows.
- Governance validation:
  - Verify `X-01` row status/notes match this ticket and both master plans in the same change.

## Risks and Mitigations

- Risk: contract text drifts from frozen runtime-gate identifiers.
  - Mitigation: require all normative sections to reference Step 1 linkage IDs.
- Risk: partial assumption mapping leads to false `X-01` closure.
  - Mitigation: require explicit linkage for all `SRG-01`..`SRG-12` and targeted BPL-01 assumption anchors.
- Risk: later contract edits reintroduce fallback semantics.
  - Mitigation: keep `SRG-11`/no-fallback assertion explicit in contract policy section.

## Change Log

- 2026-02-09: Initial BPL-02 subplan created with runtime linkage matrix and explicit `X-01` clearance assertions.
- 2026-02-09: Published Step 2 draft v1 normative invariants (`CON-01`..`CON-08`) with MUST/MUST NOT contract language and explicit linkage references.
- 2026-02-09: Closed Step 2 with explicit `BCL-01`..`BCL-12` traceability validation and promoted `CON-01`..`CON-08` to v1 contract baseline.
