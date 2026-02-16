# Phase 9 Detailed Plan: Stepper and Breakpoint Experience

## Document Control
- Status: Planned
- Last Updated: February 16, 2026
- Parent Plan: `web-ide/implementation-plan.md`
- Authoritative Specification: `web-ide/phase-9/debugger-stepper-spec.md`
- Doctrine Sources:
  - `web-ide/ide-doctrine.md`
  - `web-ui/ui-doctrine.md`
  - `web-ide/phase-0/`
  - `web-ide/phase-2/implementation-plan.md`
  - `web-ide/phase-5/implementation-plan.md`

## Phase 9 Outcome
Deliver a high-trust, restart-first stepper with expression-precise breakpoints and deterministic behavior across editor, debugger, transcript, and inspector surfaces.

## Scope
### In Scope
- Source-surface breakpoint UX with expression-level precision.
- Breakpoint kinds for form entry and form exit.
- Closing-paren break-on-return behavior with explicit return-value presentation.
- Dual-lane stepping (source-form lane plus low-level lane) with explicit handoff.
- Slide-point navigation for ambiguous stepping locations.
- Debugger frame stepping integration and restart-first recovery continuity.
- In-step REPL interactions with lexical-context inspection.
- Typed command and recording/event-log support for step/breakpoint actions.
- Deterministic replay and acceptance tests for stepper workflows.

### Out of Scope
- Compiler/runtime source-map or debug-metadata encoding decisions.
- Runtime architecture changes unrelated to stepping and breakpoints.
- Multi-user or remote debugging features.

## Implementation Policy
- Replacement is explicitly permitted and often preferred for debugger/stepper plumbing that is incomplete or inconsistent.
- Preserving restart-first behavior and inspectability is required; preserving legacy transport/state shapes is not required.
- Phase 9 implementation decisions should align with `web-ide/phase-9/debugger-stepper-spec.md` for protocol and state contracts.

## Design Anchors (Best-of-Class Synthesis)
- LispWorks: expression-precise breakpoints and return-time stopping.
- Genera/Open Genera: break-loop inspectability and debugger-centric flow.
- Franz/Allegro: source-stepper + low-level stepping with slide-point behavior.

## UX and State Contract

### Breakpoint Semantics
- Every source breakpoint has an explicit `kind`:
  - `entry` (before form evaluation)
  - `exit` (after form evaluation, with return values)
- Editor placement maps directly:
  - Opening parenthesis anchor -> `entry`
  - Closing parenthesis anchor -> `exit`
- Breakpoints carry explicit policy metadata:
  - `always`
  - `once`
  - `conditional` (predicate expression)
- Optional breakpoint actions are structured and auditable:
  - inspect locals
  - pin/watch value
  - evaluate side-effect-free probe command

### Stepping Modes
- Source lane:
  - `step.into`
  - `step.over`
  - `step.out`
  - `continue`
- Low-level lane:
  - instruction/entry stepping for ambiguous or unmapped transitions
  - explicit user handoff back to source lane
- Slide-point behavior:
  - when multiple valid stops exist, users can slide to adjacent valid source-correlated points without resuming full execution.

### Debugger Integration
- Stepper state lives inside debugger state, not in an unrelated modal tool.
- From any selected frame, users can start frame-local stepping ("restart frame stepping").
- Restart actions remain first-class and visible while stepping.
- Stepping history links to transcript/output recordings for replayable context.

### In-Step REPL Contract
- In-step REPL can inspect locals, evaluate expressions, and produce recording entries.
- Override/mutation actions must be explicit, auditable, and reversible where supported.
- REPL effects are logged as typed command entries with provenance.

## Runtime/UI Contract (Draft)
- New runtime event kinds (draft):
  - `stepper.snapshot`
  - `stepper.stop`
  - `breakpoint.update`
- New command IDs (draft):
  - `ui.debug.step.into`
  - `ui.debug.step.over`
  - `ui.debug.step.out`
  - `ui.debug.step.continue`
  - `ui.debug.step.slide.next`
  - `ui.debug.breakpoint.toggle`
  - `ui.debug.breakpoint.set-entry`
  - `ui.debug.breakpoint.set-exit`
  - `ui.debug.breakpoint.set-policy`

## Milestones
- M1 `ST1`: Stepper and breakpoint domain model with typed command contracts.
- M2 `ST2`: Editor and source-surface breakpoint placement UX (`entry`/`exit`).
- M3 `ST3`: Debugger integration for stepping controls, frame stepping, and in-step REPL shell.
- M4 `ST4`: Runtime bridge envelope additions and deterministic state merge.
- M5 `ST5`: Slide-point interaction model and command handling.
- M6 `ST6`: Deterministic replay, integration tests, and acceptance gates.

## Deferred Decision Gate (TBD Next Step)
- DM1: Compiler/runtime source-map and debug-metadata representation.
- This gate is intentionally deferred for follow-up design work.
- Phase 9 implementations should target stable UX/command/state interfaces and use fixture adapters or mocked mappings until DM1 is resolved.

## Phase 9 Success Criteria
- Breakpoint placement supports entry/exit semantics at expression granularity.
- Closing-paren break-on-return behavior is available in the user-facing model and tests.
- Stepping can switch between source and low-level lanes without losing debugger context.
- Step/breakpoint actions are replayable and deterministic in automated suites.
- Restart-first debugger behavior remains intact during stepping workflows.
