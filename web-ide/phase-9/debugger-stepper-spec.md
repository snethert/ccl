# Phase 9 Debugger and Stepper Specification

## Document Control
- Status: Draft for implementation
- Last Updated: February 16, 2026
- Owner: Web IDE / Runtime Bridge
- Parent Plan: `web-ide/phase-9/implementation-plan.md`
- Related Plans:
  - `web-ide/implementation-plan.md`
  - `web-ui/DEV-PLAN.md`

## 1. Purpose
This document specifies the debugger and stepper system for the browser IDE runtime.
It is intentionally replacement-capable.

The design goal is not "add a few stepping controls". The goal is to define a coherent, restart-first debugging subsystem with deterministic behavior, expression-precise breakpoint semantics, and strong replayability.

This specification treats existing behavior as input, not as a hard constraint. If replacing existing functionality yields a cleaner and more reliable model, replacement is preferred.

## 2. Scope
### 2.1 In Scope
- Debugger state model.
- Stepper state model and stepping semantics.
- Breakpoint model, including expression entry and expression exit anchors.
- Break-on-return behavior with explicit return-value visibility.
- Runtime command/event protocol between runtime and UI bridge.
- Deterministic recording and replay contract.
- Replacement and migration strategy for existing debugger paths.

### 2.2 Out of Scope
- Concrete source-map/debug-metadata encoding format.
- Compiler IR-specific metadata layout details.
- Non-debugger runtime services unrelated to debugging.

## 3. Design Principles
1. Restart-first safety remains primary.
2. Stepper is part of debugger state, not a separate tool mode.
3. Breakpoints are source-expression aware at the UX/API layer.
4. Runtime protocol is typed, versioned, deterministic, and auditable.
5. Current behavior may be replaced where it blocks correctness or coherence.
6. The manual C-stack/simulated ARM model is leveraged as a design advantage.

## 4. Current Capability Baseline (Observed)
This section summarizes current behavior in the tree to ground migration choices.

### 4.1 CCL Debugger Capabilities Available Now
- Break-loop command shell with restart actions and frame commands:
  - backtrace, frame inspection, arg/local inspection, set arg/local, apply-in-frame, return-from-frame.
  - Source: `ccl/level-1/l1-readloop-lds.lisp`.
- Symbol-map and pc-map based local reconstruction and source-note lookup:
  - `function-symbol-map`, `pc-source-map`, `find-source-note-at-pc`.
  - Sources: `ccl/compiler/lambda-list.lisp`, `ccl/lib/backtrace.lisp`, backend compiler files.
- Compiler options controlling debug data retention:
  - `*save-local-symbols*`, `*record-pc-mapping*`, `*save-source-locations*`.
  - Source: `ccl/level-1/l1-init.lisp`.

### 4.2 CCL Gaps / Maturity Issues Relevant to Stepper
- No current first-class stepper command surface equivalent to SBCL `STEP/NEXT/OUT` model.
- Runtime debugger snapshot path currently emits empty frames payload:
  - `"frames" #()` in runtime snapshot builder.
  - Source: `ccl/level-1/l1-readloop-lds.lisp`.
- Architecture-specific frame operations are uneven:
  - x86 `register-number->saved-register-index` placeholder.
  - x86 `%apply-in-frame` marked bitrotted/not implemented for x8632.
  - ARM `apply-in-frame` explicitly not implemented.
  - Sources: `ccl/lib/x86-backtrace.lisp`, `ccl/lib/arm-backtrace.lisp`.
- Known symbol-map ordering caveat with supplied-p variables:
  - Source: `ccl/compiler/nx2.lisp`.

### 4.3 SBCL Reference Strengths
- Compiler emits explicit step instrumentation and location metadata.
- Runtime has dedicated breakpoint and single-step trap bridge hooks.
- Debugger has explicit breakpoint lifecycle, step commands, frame-local lexical eval.
- Sources: `sbcl/src/compiler/*`, `sbcl/src/code/debug-int.lisp`, `sbcl/src/code/debug.lisp`, `sbcl/src/runtime/breakpoint.c`.

### 4.4 Implication
Current CCL behavior is useful as reference behavior, but not sufficient as a canonical architecture for web IDE stepping.
The target should preserve strengths (restart-first, inspect/edit locals) and replace inconsistent/bitrotted pathways.

## 5. Replacement Policy
### 5.1 Policy Statement
Replacement is an allowed and first-class migration tool.
When an existing pathway is incomplete, architecture-fragile, or inconsistent with the deterministic protocol model, replacement is preferred over additive layering.

### 5.2 Components Eligible for Full Replacement
- Runtime debugger snapshot production path in `l1-readloop-lds` command bridge.
- Frame serialization and frame mutation transport contracts.
- Breakpoint/step command transport contract.
- UI-facing debugger state reducer and event wiring.

### 5.3 Components to Preserve Semantically
- Restart-first debugger flow.
- Ability to inspect frame arguments and locals.
- Ability to perform in-frame evaluation where safe.
- Auditability of mutation and restart actions.

## 6. Target Architecture

### 6.1 Layers
1. Execution Engine Layer
- Owns simulated ARM execution and manual C-stack model.
- Emits low-level execution stop signals.

2. Debug Core Layer
- Maintains canonical debug model (frames, scopes, locations, breakpoints, step session).
- Converts low-level stops into typed `debugger.stop` events.

3. Runtime Bridge Layer
- Exposes typed command API.
- Emits typed event stream.
- Records deterministic event log entries.

4. UI State Layer
- Applies event stream into debugger/stepper UI state.
- Never derives debugger state from ad-hoc DOM state.

### 6.2 Required Property
The Debug Core layer must be host-stack-independent. It must consume the runtime's own frame model and not require architecture-specific native frame walking semantics.

## 7. Canonical Data Model
All model records are versioned and serializable.

### 7.1 DebuggerSession
```json
{
  "schemaVersion": 1,
  "sessionId": "dbg-uuid",
  "state": "idle|paused|running",
  "pauseReason": "breakpoint|step|condition|manual|internal",
  "selectedFrameId": "frm-...",
  "frameOrder": ["frm-top", "frm-next"],
  "frames": {"frm-top": {"...": "..."}},
  "restarts": ["rst-continue", "rst-abort"],
  "stepSession": {"...": "..."},
  "breakpoints": {"bp-...": {"...": "..."}}
}
```

### 7.2 FrameRecord
```json
{
  "frameId": "frm-uuid",
  "ordinal": 0,
  "function": {
    "name": "MY-FUN",
    "package": "CL-USER",
    "kind": "global|local|closure|internal"
  },
  "locationId": "loc-uuid",
  "location": {
    "sourceRef": "src-...",
    "anchor": "entry|exit|internal|unknown",
    "displayLabel": "(my-fun x y)",
    "canStepSource": true,
    "canStepLowLevel": true
  },
  "scopeIds": ["scp-args", "scp-locals"],
  "canRestartFrame": true,
  "canEvalInFrame": true,
  "capabilities": {
    "setLocal": true,
    "setArg": true,
    "returnFromFrame": true
  }
}
```

### 7.3 ScopeRecord
```json
{
  "scopeId": "scp-uuid",
  "kind": "arguments|locals|closed-over|specials",
  "bindings": [
    {
      "name": "X",
      "bindingId": "bnd-uuid",
      "valueRef": "val-uuid",
      "availability": "valid|invalid|unknown",
      "mutable": true,
      "source": "register|stack|closure|synthetic"
    }
  ]
}
```

### 7.4 ValueRefRecord
```json
{
  "valueRef": "val-uuid",
  "summary": "#<HASH-TABLE ...>",
  "type": "hash-table",
  "presentationId": "prs-...",
  "expandable": true,
  "stableIdentity": "obj-identity-token-or-null"
}
```

### 7.5 LocationRecord
```json
{
  "locationId": "loc-uuid",
  "sourceRef": "src-uuid",
  "anchorKind": "entry|exit|internal|unknown",
  "formId": "form-uuid-or-null",
  "offset": {
    "line": 120,
    "column": 18,
    "charStart": 2501,
    "charEnd": 2524
  },
  "isAmbiguous": false,
  "slideGroupId": "slide-uuid-or-null"
}
```

### 7.6 BreakpointRecord
```json
{
  "breakpointId": "bp-uuid",
  "sourceRef": "src-uuid",
  "anchorKind": "entry|exit",
  "anchor": {
    "formId": "form-uuid",
    "line": 42,
    "column": 17
  },
  "enabled": true,
  "policy": {
    "mode": "always|once|conditional|hit-count",
    "condition": "(> x 10)",
    "hitCount": 5,
    "currentHits": 0
  },
  "actions": {
    "inspectLocals": false,
    "pinValues": [],
    "probeForms": []
  },
  "createdBy": "ui|runtime|import",
  "createdAt": "timestamp"
}
```

### 7.7 StepSessionRecord
```json
{
  "stepSessionId": "stp-uuid",
  "mode": "source|low-level",
  "originFrameId": "frm-uuid",
  "originLocationId": "loc-uuid",
  "active": false,
  "pendingCommand": "step.into|step.over|step.out|continue|slide.next|none",
  "lastStopId": "stop-uuid",
  "outTargetFrameId": "frm-uuid-or-null"
}
```

### 7.8 StopRecord
```json
{
  "stopId": "stop-uuid",
  "reason": "breakpoint|step|condition|manual|internal",
  "locationId": "loc-uuid",
  "frameId": "frm-uuid",
  "breakpointId": "bp-uuid-or-null",
  "returnValues": ["val-1", "val-2"],
  "timestamp": "...",
  "sequence": 1024
}
```

## 8. Stepper Semantics

### 8.1 Step Modes
- `step.into`
- `step.over`
- `step.out`
- `continue`
- `slide.next`
- `slide.prev`

### 8.2 Source Lane vs Low-Level Lane
- Source lane is default and preferred.
- Low-level lane is explicit and opt-in when source mapping is unavailable/ambiguous.
- A stop event must include `lane: source|low-level`.
- Any lane switch is explicit, logged, and visible.

### 8.3 Required Behavior: `step.into`
- Stop at the next valid source-correlated stop in dynamic control flow.
- If entering callee with source mapping, callee entry is eligible.
- If no valid source stop exists, stop in low-level lane with explicit reason.

### 8.4 Required Behavior: `step.over`
- Compute dynamic depth baseline from current frame.
- Execute until next stop at same or shallower depth in current lexical line-of-interest.
- Breakpoints remain active unless explicitly suppressed.

### 8.5 Required Behavior: `step.out`
- Capture target frame = caller of selected frame at issue time.
- Stop when control returns to target frame at next valid stop.
- If target frame disappears by non-local exit, emit stop with `reason=step-target-unwound`.

### 8.6 Required Behavior: `continue`
- Resume execution with no synthetic stepping stops.
- User breakpoints remain active.

### 8.7 Slide Point Behavior
- Applies when runtime reports multiple equivalent candidate source stops for a single execution frontier.
- `slide.next`/`slide.prev` select adjacent candidate without full resume.
- Selection updates location + source highlight + command history deterministically.

## 9. Breakpoint Semantics

### 9.1 Anchor Kinds
- `entry`: before form evaluation.
- `exit`: after form evaluation, with captured return values.

### 9.2 Closing Paren Behavior
UI placement on closing parenthesis must create `anchorKind=exit`.
Stopping at an exit breakpoint must include `returnValues` in stop payload.

### 9.3 Policy Modes
- `always`: break every hit.
- `once`: break first hit then auto-disable.
- `conditional`: evaluate predicate in frame context.
- `hit-count`: break on configured count/modulo semantics.

### 9.4 Conditional Evaluation Rules
- Condition form runs in debugger-safe evaluation context.
- Failures in condition evaluation are reported as condition-eval diagnostics.
- Policy default on condition error is configurable; default is `break-on-error=true`.

### 9.5 Breakpoint Actions
Actions run in deterministic order after stop is decided:
1. evaluate probe forms marked side-effect-free (if policy allows)
2. collect pinned values
3. emit inspect locals payload

## 10. Restart Integration

### 10.1 Non-negotiable Contract
Restart visibility and invocation must remain available while stepping.
Stepping cannot hide or replace restart-first recovery.

### 10.2 Restart Metadata
Each restart includes:
- id
- title
- description
- safety classification
- argument schema
- recommended flag + explanation (optional)

### 10.3 Frame Restart-Stepping
- From selected frame, user can request restart-frame then enter stepping.
- Runtime must report if operation is unavailable for current frame.

## 11. In-Step Evaluation Contract

### 11.1 Capabilities
- Evaluate forms in selected frame context.
- Read locals/args.
- Optionally mutate locals/args when runtime marks mutable.

### 11.2 Auditability
All in-step eval/mutation operations must be logged as typed command entries with:
- command id
- frame id
- location id
- argument payload
- result or error

### 11.3 Safety
Mutating operations must be explicit commands, never implicit side effects of inspection.

## 12. Runtime Command Protocol

### 12.1 Versioning
All messages include:
- `protocolVersion`
- `schemaVersion`
- `sequence`
- `timestamp`

### 12.2 Commands
Required command IDs:
- `runtime.debugger.open`
- `runtime.debugger.frame.select`
- `runtime.debugger.restart.invoke`
- `runtime.debugger.step.into`
- `runtime.debugger.step.over`
- `runtime.debugger.step.out`
- `runtime.debugger.step.continue`
- `runtime.debugger.step.slide.next`
- `runtime.debugger.step.slide.prev`
- `runtime.debugger.breakpoint.upsert`
- `runtime.debugger.breakpoint.delete`
- `runtime.debugger.breakpoint.enable`
- `runtime.debugger.breakpoint.disable`
- `runtime.debugger.eval.in-frame`
- `runtime.debugger.binding.set`

### 12.3 Events
Required event IDs:
- `debugger.snapshot`
- `debugger.stop`
- `debugger.resume`
- `debugger.frame.selected`
- `debugger.restarts.updated`
- `debugger.breakpoint.updated`
- `debugger.breakpoint.deleted`
- `debugger.step.session.updated`
- `debugger.eval.result`
- `debugger.binding.updated`
- `debugger.error`

### 12.4 Error Model
Errors include typed `code` values:
- `unsupported-operation`
- `invalid-frame`
- `invalid-breakpoint`
- `condition-eval-failed`
- `mapping-unavailable`
- `state-conflict`
- `internal-error`

## 13. Deterministic Recording and Replay

### 13.1 Recording Requirements
Every command/event pair must be recordable and replayable with stable ordering.

### 13.2 Determinism Rules
- Runtime emits monotonically increasing sequence IDs.
- UI reducers are pure over `(previousState, event)`.
- Time-dependent fields excluded from state equality checks unless explicitly modeled.

### 13.3 Replay Fixtures
At minimum include fixtures for:
- entry breakpoint hit
- exit breakpoint hit with two return values
- step-over across nested call
- step-out target unwind
- slide point selection changes
- restart invoke during active step session
- conditional breakpoint with condition failure

## 14. Migration and Replacement Strategy

### 14.1 Strategy A: Full Replacement (Preferred)
Replace existing runtime debugger snapshot/command surface with this protocol.
- Pros: coherent model, fewer compatibility hacks, deterministic state.
- Cons: larger initial cutover.

### 14.2 Strategy B: Hybrid Bridge (Temporary)
Introduce adapter translating old runtime commands/events into new schema.
- Pros: lower short-term disruption.
- Cons: increased long-term complexity and behavior drift risk.

### 14.3 Strategy C: Compatibility Mode (Limited Time)
Expose legacy commands behind feature flag for fallback only.
- Must have explicit expiry milestone.

### 14.4 Required Deprecation Plan
1. Mark legacy debugger bridge endpoints as deprecated.
2. Route new UI exclusively through new protocol.
3. Keep compatibility adapter for bounded period.
4. Remove legacy endpoints after parity acceptance suite is green.

## 15. Implementation Guidance for Current Codebase

### 15.1 Runtime Bridge (`l1-readloop-lds`)
- Replace current debugger snapshot payload assembly that emits empty frame vectors.
- Move restart-only snapshot shape to full frame/scope/breakpoint snapshot shape.

### 15.2 Backtrace/Frame Operations
- Do not rely on architecture-fragile `apply-in-frame` implementations as canonical stepping substrate.
- For simulated ARM/manual C-stack runtime path, implement frame operations against runtime-owned stack model.

### 15.3 Compiler Metadata Dependency
- Source mapping mechanism remains deferred.
- Runtime/debugger contract must support an abstract `LocationProvider` interface:
  - `resolveExecutionPoint -> location candidates`
  - `resolveAnchor -> runtime stop target`
- Concrete provider implementation selected in next-step design.

## 16. Acceptance Criteria

### 16.1 Functional
- Users can place entry and exit breakpoints in source surfaces.
- Exit breakpoints show return values in stop payload.
- Step into/over/out/continue all function deterministically.
- Slide-point controls operate without full resume.
- Restarts remain available during stepping.

### 16.2 Protocol
- All required commands/events implemented.
- Versioned envelope validation passes.
- Unsupported operations return typed errors.

### 16.3 Replay
- Replay fixtures pass with stable final-state hash.
- Event ordering and frame selection remain deterministic.

### 16.4 Replacement
- Preferred full-replacement path can run with legacy path disabled.
- Compatibility mode, if retained, is behind explicit feature flag.

## 17. Security and Safety
- Debug commands are capability-gated.
- Mutation commands require explicit user intent and are auditable.
- Probe execution for conditional/actions is bounded and sandboxed by runtime policy.

## 18. Open Decisions (Deferred)
1. Concrete source-map/debug-metadata encoding format.
2. Exact compiler emission contract for expression anchors.
3. Cross-image persistence strategy for stable object identities.

These are intentionally deferred and do not block this protocol/state contract.

## 19. Milestone Mapping
- ST1: Domain model and protocol envelopes.
- ST2: Editor breakpoint UX for entry/exit anchors.
- ST3: Debugger stepper controls and frame integration.
- ST4: Runtime bridge command/event implementation.
- ST5: Slide-point interactions.
- ST6: Deterministic replay/acceptance suite.

## 20. Rationale Summary
This specification is replacement-forward by design because current pathways are uneven and partially architecture-bound.
Given the runtime's simulated ARM/manual C-stack model, the project can implement a cleaner debugger core than either legacy CCL pathways or host-stack-coupled designs.

The system should preserve restart-first Lisp ergonomics while replacing fragile transport and state conventions with typed, deterministic contracts.
