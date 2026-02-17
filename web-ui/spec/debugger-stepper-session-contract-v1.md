# Debugger Stepper Session Contract v1

Status: Draft  
Version: 1.1.0  
Last updated: 2026-02-16  
Scope: Debugger session lifecycle, step-command protocol, and runtime/UI synchronization for `web-ui`  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/command-schema-v1.json`, `web-ui/spec/ui-state-schema-v1.json`, `web-ui/spec/debug-location-provider-contract-v1.md`, `web-ui/src/state.mjs`, `web-ui/src/runtime-bridge.mjs`, `web-ui/src/runtime-command-client.mjs`, `web-ui/bridge/runtime.mjs`, `web-ui/DEV-PLAN.md`  
Compatibility: `v1.x` preserves debugger payload normalization rules, restart-step coexistence, step command IDs, and session state vocabulary; `v1.1+` adds runner identity lanes without changing single-runner behavior.

## 1. Purpose

This contract defines canonical debugger session behavior for runtime-driven debugging in `web-ui`.
It specifies how debugger snapshots, restart updates, and step-session commands/events are normalized, applied, and replayed deterministically.

## 2. Session Model

## 2.1 Session States

Closed-set state values:

1. `idle`
2. `running`
3. `paused`

## 2.2 Pause Reasons

Closed-set pause reasons:

1. `breakpoint`
2. `step`
3. `condition`
4. `manual`
5. `internal`

## 2.3 Step Session Record

Canonical step-session shape:

1. `stepSessionId`
2. `runnerId`
2. `mode` (`source|low-level`)
3. `originFrameId`
4. `originLocationId`
5. `active`
6. `pendingCommand` (`step.into|step.over|step.out|continue|slide.next|slide.prev|none`)
7. `lastStopId`
8. `outTargetFrameId`

Identity namespace rules:

1. `stepSessionId` <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-DBFC1EB6C0"></a>MUST be unique per `runnerId`.
2. `stopId` <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-5CD50F1CD7"></a>MUST be unique within `(runnerId, stopId)` tuple space.
3. `frameId` <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-A9FC1BB001"></a>MUST be interpreted in runner scope and <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-6A23B968AA"></a>MUST NOT be assumed globally unique across runners.

## 3. Baseline Runtime Ingestion (Current `v1` Core)

## 3.1 `debugger.snapshot`

Snapshot payload application <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-1CC9E0F528"></a>MUST:

1. Reject non-object payload.
2. Normalize frame records deterministically:
- default `frameId = frame-<index+1>`,
- `function` fallback from `frame.function`, then `frame.label`, then `anonymous`,
- `locals` normalized with stable fallback IDs.
3. Normalize condition report with safe fallback when malformed.
4. Normalize restart list while ignoring malformed restart entries.
5. Derive/merge `debuggerTarget.selectedFrameId` when provided.
6. Upsert error record and refresh/open debugger window for task.

## 3.2 `debugger.restart`

Restart update payload application <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-6EB4722BBF"></a>MUST:

1. Reject non-object payload.
2. Require `errorId`; if absent, update is ignored.
3. For `type=set` with known error:
- replace restart list with normalized payload list.
4. For `type=invoked`:
- update `debuggerTarget.lastInvokedRestartId` and optional summary lanes,
- refresh debugger window summary text.
5. For unknown error with `type=set` and restart list:
- synthesize minimal error snapshot (without forced debugger-open).

## 3.3 Restart-Step Coexistence

Restart availability is non-negotiable:

1. Restart list and invoke command <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-ECA0DD80A7"></a>MUST remain available while any step session is active.
2. Step commands <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-045F3DDE0D"></a>MUST NOT suppress restart metadata or restart invocation routing.

## 4. Stepper Command Protocol

## 4.1 Required Runtime Command IDs

1. `runtime.debugger.step.into`
2. `runtime.debugger.step.over`
3. `runtime.debugger.step.out`
4. `runtime.debugger.step.continue`
5. `runtime.debugger.step.slide.next`
6. `runtime.debugger.step.slide.prev`
7. `runtime.debugger.eval.in-frame`
8. `runtime.debugger.binding.set`

Related baseline debugger command IDs:

1. `ui.debugger.restart.invoke` (UI-typed command)
2. `runtime.restart.invoke` (runtime command target for restart invocation)

## 4.2 Step Command Semantics

1. `step.into`: next valid source-correlated stop in dynamic flow; may enter callee.
2. `step.over`: next stop at same/shallower dynamic depth.
3. `step.out`: run until caller frame stop or unwind failure.
4. `continue`: resume without synthetic stepping stops.
5. `slide.next|slide.prev`: move among equivalent stop candidates without full resume.

## 4.3 Runtime Response Discipline

1. Every step command <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-DD14363DDA"></a>MUST terminate with `command.result` or `command.error`.
2. Unsupported step commands <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-3A53ADA489"></a>MUST return typed `unsupported-operation` errors.
3. Runtime command client correlation <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-D17101C41E"></a>MUST use `requestId` and/or `invocationId`.

## 5. Stepper Event Protocol

## 5.1 Required Event Kinds

1. `debugger.stop`
2. `debugger.resume`
3. `debugger.frame.selected`
4. `debugger.step.session.updated`
5. `debugger.eval.result`
6. `debugger.error`

## 5.2 `debugger.stop` Minimum Fields

1. `stopId`
2. `runnerId`
3. `frameId`
4. `reason`
5. `location` (provider-normalized)
6. `slideGroup` (`{id,candidates[]|null}`)
7. `returnValues` (required for exit-bound breakpoint stops)

## 5.3 Ordering and Correlation

1. Runtime event `sequence` <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-3302D788A3"></a>MUST be monotonic for a stream.
2. Stop/resume/session updates <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-4074D8871F"></a>MUST be applied in envelope order.
3. Frame-selection and eval-result events <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-24B6EF8FF6"></a>MUST include runner and frame correlation lanes.
4. Simultaneous stops from different runners <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-D749B2C65D"></a>MUST NOT overwrite each other; UI state tracks one active stop per runner plus one user-selected active runner.

## 6. Determinism and Replay Rules

1. UI reducers for debugger/stepper state <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-CB3068EDBA"></a>MUST be pure over `(priorState,event)`.
2. For fixed command/event log, final debugger state hash <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-9388F2629D"></a>MUST be stable.
3. Slide candidate ordering <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-3E70E40F9D"></a>MUST be deterministic and stable.
4. `step.out` unwind outcomes <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-1260CED1C1"></a>MUST produce explicit reasoned stops, not silent drops.
5. Time-based metadata MAY vary, but must be excluded from deterministic equality unless modeled as explicit lanes.

## 7. Security and Capability Requirements

1. Step/eval/mutation commands <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-9B64EE60CD"></a>MUST be capability-gated and auditable.
2. In-frame mutation (`binding.set`) <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-6279751A17"></a>MUST require explicit command intent.
3. Runtime payloads <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-FBF6AF44AC"></a>MUST be treated as untrusted and shape-validated before reducer application.
4. Restart and step command dispatch <a id="REQ-DEBUGGER-STEPPER-SESSION-CONTRACT-V1-868764F77E"></a>MUST not bypass safe-mode or capability gates in command execution.

## 8. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `debugger-stepper.invalid-payload` | Debugger snapshot/restart payload malformed. | Conditional | Correct payload schema and retry emit. |
| `debugger-stepper.error-not-found` | Update referenced unknown `errorId`. | Conditional | Emit snapshot first or correct error identity. |
| `debugger-stepper.invalid-frame` | Step/eval command referenced unavailable frame. | Conditional | Refresh frame selection/snapshot and retry. |
| `debugger-stepper.step-target-unwound` | `step.out` target frame disappeared via non-local exit. | Conditional | Continue from current stop or choose new frame/step command. |
| `debugger-stepper.mapping-unavailable` | Source-lane step target cannot be mapped. | Conditional | Switch to low-level lane or refresh mappings. |
| `debugger-stepper.unsupported-operation` | Runtime does not implement requested step command. | No | Degrade UI affordance or use supported command set. |
| `debugger-stepper.state-conflict` | Session command conflicts with current runtime session state. | Conditional | Refresh session snapshot and re-issue command if valid. |

## 9. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/debugger.test.mjs`
2. `web-ui/tests/phase-2-debugger.test.mjs`
3. `web-ui/tests/phase-5-runtime-debugger.test.mjs`
4. `web-ui/tests/phase-5-runtime-restart-invoke.test.mjs`
5. `web-ui/tests/phase-5-runtime-command-dispatch.test.mjs`

Phase 10 expansion fixtures (required for full stepper claims):

1. step-into deterministic stop fixture.
2. step-over nested-call fixture.
3. step-out unwind fixture.
4. slide-point selection fixture.
5. restart-during-step-session fixture.

Pass criteria:

1. Baseline snapshot/restart flows are deterministic and window state remains coherent.
2. Command-result/error correlation settles pending runtime commands deterministically.
3. Stepper fixtures (when present) satisfy Section 4-6 semantics.

## 10. Conformance

An implementation is conformant only if Sections 2-9 are satisfied.
