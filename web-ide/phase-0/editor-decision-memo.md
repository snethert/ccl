# Phase 0 Memo: Editor Runtime Decision

## Decision Status
- Status: Locked
- Date: February 8, 2026
- Runtime selected: CodeMirror 6

## Context
The IDE requires a text editor with strong IME support, reliable selection and clipboard behavior, high performance on large buffers, and extensibility for Lisp structural editing. This must work inside a DOM surface while still conforming to the UI Doctrine.

## Candidates
1. CodeMirror 6
2. Monaco
3. Custom editor (DOM or canvas)

## Evaluation Criteria
- IME correctness (CJK, dead keys, composition)
- Selection fidelity and multi-cursor support
- Clipboard and undo/redo correctness
- Accessibility and screen reader support
- Extensibility for Lisp structural editing (paredit, structural navigation)
- Performance on large buffers
- Theming and visual integration with UI Doctrine
- Bundle size and complexity

## Summary Assessment

### CodeMirror 6
Strengths:
- Strong modularity and composability.
- Good IME and selection behavior in practice.
- Flexible syntax parsing and extension model.
- Easier to integrate Lisp structural editing.

Risks:
- Requires deliberate configuration for a11y and performance.
- Needs a disciplined theming layer to avoid default aesthetics.

### Monaco
Strengths:
- Excellent editor UX out of the box.
- Strong LSP integration and editor features.

Risks:
- Heavy bundle size and integration overhead.
- Less flexible for structural editing workflows.
- Harder to fully align with custom UI Doctrine without visible seams.

### Custom Editor
Strengths:
- Full control over UX and integration.

Risks:
- High engineering cost for IME, selection, clipboard, and a11y.
- Likely to slow development and introduce regressions.

## Recommendation (Final)
Adopt CodeMirror 6 as the default editor runtime for v1.
Rationale:
- It satisfies IME, selection, clipboard, and accessibility requirements with lower integration cost than Monaco.
- It is the best fit for Lisp structural editing extensions without maintaining a custom editor core.
- It can be themed to match the UI Doctrine while keeping bundle and integration complexity within Phase 1-2 goals.

## Scope Lock
- Monaco is not a Phase 1 runtime target.
- A custom editor is not a v1 target.
- Reopening this decision requires a documented regression against mandatory requirements (IME, selection fidelity, clipboard/undo, or accessibility).

## Spike Plan
Build a minimal editor prototype for the top two candidates:
- Load and edit a 10,000+ line file.
- Verify IME behavior (CJK input and composition).
- Exercise multi-cursor editing and selection semantics.
- Verify clipboard, undo/redo, and accessibility.
- Implement a minimal Lisp structural edit command (e.g., forward-sexp).

## Exit Criteria
- One editor meets all criteria with acceptable theming effort.
- Decision memo updated with final choice and rationale.
- Runtime selected: CodeMirror 6.
