# UI Interaction and Window Management Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Cross-window interaction semantics for `web-ui` across DOM/Canvas/WebGL  
Depends on: `web-ui/ui-doctrine.md`, `web-ide/ide-doctrine.md`

## 1. Purpose

This contract defines normative system interaction behavior that is intentionally out-of-scope for presentation doctrine:

- Window layering and `z-order`.
- Modal stacking and interaction blocking.
- Resize governance and bounds behavior.
- Focus ownership and handoff between windows/surfaces.

## 2. Conformance

An implementation is conformant only if all rules below hold:

1. Window ordering is deterministic and stable under replay.
2. Modal semantics are strict: blocked surfaces are non-interactive.
3. Resize behavior respects deterministic bounds and focus safety.
4. Focus handoff is explicit, lossless, and recoverable.
5. Equivalent interaction inputs produce equivalent state outcomes across backends.

## 3. Layering and Z-Order

### 3.1 Layer Classes

Window/surface layers MUST resolve in this priority order (lowest -> highest):

1. `base-surface`
2. `primary-window`
3. `floating-panel`
4. `modal`
5. `critical-overlay`

Rules:

1. A lower-priority layer MUST NOT occlude a higher-priority layer.
2. Within the same layer, ordering MUST be deterministic by activation timestamp, then stable id as tie-breaker.
3. At most one non-modal window per active task MAY be `active` at a time; if one exists, it MUST be topmost within its layer scope.
4. Programmatic re-ordering MUST preserve deterministic ordering rules and MUST emit a diagnostic event when rejected.

## 4. Modal Stacking

Rules:

1. Modal windows MUST be represented as an explicit stack per task/workspace scope.
2. Only the topmost modal is interactive; all lower stack entries and background layers MUST be inert.
3. Opening a modal MUST move focus into that modal before user input is processed.
4. Closing a modal MUST restore focus to the previously focused valid target in the parent scope.
5. Non-modal windows MUST NOT be promoted above a modal while any modal remains open in that scope.
6. Nested modals MUST declare a parent modal id; orphan modal entries are invalid.

## 5. Resize Governance

Rules:

1. Window resize operations (pointer, keyboard, or command) MUST clamp to declared min/max bounds.
2. If bounds cannot be fully satisfied due to viewport limits, the system MUST preserve title/chrome visibility and one primary interaction affordance.
3. Resize updates MUST be monotonic with input deltas and MUST settle deterministically after input end.
4. Resize-induced reflow MUST NOT drop focus when the focused target remains mounted and enabled.
5. If resize invalidates the focused target, focus MUST hand off according to section 6.

## 6. Focus Ownership and Handoff

Rules:

1. Focus transitions MUST carry an explicit reason code (`user-pointer`, `user-keyboard`, `command`, `restore`, `modal-open`, `modal-close`, `window-close`).
2. Window activation MUST atomically update active task, active window, and focus target.
3. On `modal-open`, focus MUST move to the first valid focus target in the modal, or modal root fallback.
4. On `modal-close`, focus MUST restore to last valid target outside the modal; if absent, fallback to active window root.
5. On window close/removal, focus MUST transfer to the next deterministic target in the same task before cross-task fallback.
6. Focus MUST never reference a non-existent or disabled target after state commit.

## 7. Failure Semantics

If interaction arbitration cannot be satisfied:

1. The system MUST fall back to a deterministic safe target (`active-window-root` or `workspace-root`).
2. The system MUST preserve input operability and avoid dead focus.
3. A structured diagnostic event MUST be emitted with reason and rejected transition metadata.

## 8. Backend Parity

1. DOM, Canvas, and WebGL backends MUST converge to equivalent active-window, modal-stack, and focus state for the same interaction trace.
2. Divergence in ordering, modal blocking, or focus ownership is a conformance failure.
3. Backend-specific optimization MAY change internal implementation, but not externally observable interaction semantics.
