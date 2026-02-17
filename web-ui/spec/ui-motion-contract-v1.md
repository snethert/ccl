# UI Motion Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Motion semantics for `web-ui` across DOM/Canvas/WebGL  
Depends on: `web-ui/spec/ui-visual-tokens-v1.json`
Compatibility: `v1.x` preserves normative requirements and failure semantics; incompatible changes require `v2`.

## 1. Purpose

This contract defines motion as semantic explanation, not decoration.
All motion behavior <a id="REQ-UI-MOTION-CONTRACT-V1-771CF5ECE1"></a>MUST remain deterministic under replay and <a id="REQ-UI-MOTION-CONTRACT-V1-B4B3BDA288"></a>MUST be suppressible for reduced-motion users.

## 2. Conformance

An implementation is conformant if:

1. Only approved transition classes are animated.
2. Explicit no-animation classes never animate in any mode.
3. Duration and easing map to token values.
4. Motion can be globally reduced with no loss of state meaning.
5. Input remains responsive during transitions.

## 3. Approved Transition Classes

Only the following classes MAY animate when not overridden by section 3.1:

1. `surface-enter`: window/panel appears.
2. `surface-exit`: window/panel dismisses.
3. `focus-shift`: focus indicator moves between targets.
4. `selection-shift`: list/tree/table selection changes.
5. `expand-collapse`: disclosure rows and sections.
6. `inline-state-change`: button/input hover/active/focus transitions.

All other classes are prohibited unless added to this contract.

## 3.1 Explicit No-Animation Classes

The following classes <a id="REQ-UI-MOTION-CONTRACT-V1-73F9506C59"></a>MUST NOT animate and <a id="REQ-UI-MOTION-CONTRACT-V1-A9123E94E8"></a>MUST snap to final state:

1. `critical-alert`: safety/destructive/error interrupts requiring immediate clarity.
2. `rapid-command-feedback`: command feedback expected to complete within a single UI turn.
3. `high-frequency-update`: continuously changing metrics/log streams.

Rules:

1. Duration for these classes <a id="REQ-UI-MOTION-CONTRACT-V1-3465C6842F"></a>MUST resolve to `0ms` in all modes.
2. If a no-animation class overlaps an approved animated class, no-animation behavior <a id="REQ-UI-MOTION-CONTRACT-V1-2508ABA8BA"></a>MUST win.
3. Visual clarity <a id="REQ-UI-MOTION-CONTRACT-V1-04ACE1CB64"></a>MUST come from state contrast, iconography, and text, not temporal interpolation.

## 4. Durations and Curves

Default durations:

- fast: `120ms`
- normal: `180ms`
- slow: `250ms`

Default curve:

- standard: `cubic-bezier(0.2, 0.0, 0.2, 1.0)`

Rules:

1. `inline-state-change` <a id="REQ-UI-MOTION-CONTRACT-V1-ACB593DADD"></a>MUST use `fast`.
2. `focus-shift` <a id="REQ-UI-MOTION-CONTRACT-V1-2243D11A48"></a>MUST use `fast` or `normal`.
3. `surface-enter` and `surface-exit` SHOULD use `normal`.
4. `expand-collapse` SHOULD use `normal` and <a id="REQ-UI-MOTION-CONTRACT-V1-9DE1F0B8AC"></a>MUST NOT exceed `slow`.
5. No transition MAY exceed `300ms`.
6. `critical-alert`, `rapid-command-feedback`, and `high-frequency-update` <a id="REQ-UI-MOTION-CONTRACT-V1-B3482F279C"></a>MUST use `0ms`.

## 5. Reduced-Motion Contract

When reduced motion is enabled:

1. Duration <a id="REQ-UI-MOTION-CONTRACT-V1-AB70B54759"></a>MUST resolve to `0ms` for transforms and positional animation.
2. Opacity change MAY remain but <a id="REQ-UI-MOTION-CONTRACT-V1-F96B4D003B"></a>MUST complete in <= `80ms`.
3. State meaning <a id="REQ-UI-MOTION-CONTRACT-V1-B124350972"></a>MUST remain unambiguous without relying on animation.
4. Focus and selection changes <a id="REQ-UI-MOTION-CONTRACT-V1-D03C2D479C"></a>MUST still expose explicit visual indicators.

## 6. Interaction Safety

1. Motion <a id="REQ-UI-MOTION-CONTRACT-V1-3E8C64C0A1"></a>MUST NOT block pointer or keyboard input handling.
2. Input-to-visual-response latency <a id="REQ-UI-MOTION-CONTRACT-V1-15E40A602E"></a>MUST remain within the active UI turn budget.
3. Interrupted transitions <a id="REQ-UI-MOTION-CONTRACT-V1-1D99FED174"></a>MUST settle to final state deterministically.
4. Concurrent transitions on the same element <a id="REQ-UI-MOTION-CONTRACT-V1-568F1A7D4C"></a>MUST use last-writer-wins semantics.
5. High-frequency update lanes <a id="REQ-UI-MOTION-CONTRACT-V1-849FB7D4B1"></a>MUST avoid animation queue buildup and <a id="REQ-UI-MOTION-CONTRACT-V1-6BE5595FB1"></a>MUST snap stale frames.

## 7. Backend Parity

1. Start and end geometry <a id="REQ-UI-MOTION-CONTRACT-V1-649BC65086"></a>MUST match across backends within +/- 1 px.
2. Measured duration drift across backends <a id="REQ-UI-MOTION-CONTRACT-V1-18B2501713"></a>MUST be <= 16 ms.
3. Easing approximation differences <a id="REQ-UI-MOTION-CONTRACT-V1-0A8BE2009B"></a>MUST preserve monotonic progression.
4. If a backend cannot animate a class, it <a id="REQ-UI-MOTION-CONTRACT-V1-598C0BF3E8"></a>MUST snap to end state and log a diagnostic.

## 8. Failure Semantics

If motion cannot be executed:

1. The system <a id="REQ-UI-MOTION-CONTRACT-V1-E8453BAB4D"></a>MUST render final state immediately.
2. Focus and selection indicators <a id="REQ-UI-MOTION-CONTRACT-V1-A3CFBB1C46"></a>MUST remain visible.
3. A structured reliability sample <a id="REQ-UI-MOTION-CONTRACT-V1-71C236F328"></a>MUST be emitted with transition class and reason.

## 9. Required Conformance Fixtures

1. Transition timing fixture for each approved animated class and each explicit no-animation class.
2. Reduced-motion fixture proving semantic parity with non-reduced mode.
3. Interrupted-transition fixture validating deterministic end state.
4. Cross-backend parity fixture for focus and selection transitions.

Canonical fixture IDs and assertion definitions are in:
- `web-ui/spec/ui-conformance-fixtures-v1.json`
- `web-ui/spec/ui-conformance-fixture-catalog-v1.md`
- `web-ui/spec/ui-conformance-matrix-v1.md`
