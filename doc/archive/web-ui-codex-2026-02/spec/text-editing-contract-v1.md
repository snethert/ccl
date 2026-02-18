# Text Editing Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Text input/editing semantics across DOM, Canvas, and WebGL backends  
Depends on: `web-ui/spec/keymap-localization-and-ime-policy-v1.md`, `web-ui/spec/focus-and-selection-contract-v1.md`, `web-ui/spec/command-undo-redo-contract-v1.md`, `web-ui/spec/renderer-backend-contract-v1.md`  
Compatibility: `v1.x` preserves cursor/selection model, IME lifecycle, and backend parity obligations; incompatible editing model changes require `v2`.

## 1. Purpose

This contract defines the canonical editing model for text-capable controls.

## 2. Canonical Text State

Each editable control <a id="REQ-TEXT-EDITING-CONTRACT-V1-2BCAD0FD46"></a>MUST expose:

1. `text`
2. `selectionStart`
3. `selectionEnd`
4. `selectionDirection` (`forward|backward|none`)
5. `composing` (IME composition state)
6. `revision`

Rules:

1. `selectionStart` and `selectionEnd` are UTF-16 code-unit offsets in `v1`.
2. Selection ranges <a id="REQ-TEXT-EDITING-CONTRACT-V1-ADBC2F737E"></a>MUST clamp to `[0, text.length]`.
3. Single-cursor state uses `selectionStart == selectionEnd`.

## 3. Editing Operations

Required operation family:

1. insert text
2. delete backward/forward
3. replace selection
4. move cursor by grapheme/word/line boundary
5. select all
6. set explicit selection range

Operations <a id="REQ-TEXT-EDITING-CONTRACT-V1-23DAE4618F"></a>MUST produce deterministic state transitions for fixed `(priorState, operation)`.

## 4. IME Composition Lifecycle

1. Composition start sets `composing=true`.
2. Composition updates replace provisional composition range.
3. Composition commit writes committed text and sets `composing=false`.
4. Composition cancel restores pre-composition text/selection snapshot and sets `composing=false`.

Backends <a id="REQ-TEXT-EDITING-CONTRACT-V1-B12C57C0FC"></a>MUST preserve IME semantics in all supported locales.

## 5. Backend Parity

### 5.1 DOM

DOM backends MAY use native `<input>`/`<textarea>` for base editing behavior but <a id="REQ-TEXT-EDITING-CONTRACT-V1-81D70F9491"></a>MUST normalize all emitted editing state to Section 2 shape.

### 5.2 Canvas/WebGL

Canvas/WebGL backends <a id="REQ-TEXT-EDITING-CONTRACT-V1-244E5C4FCC"></a>MUST provide hidden-input proxy strategy:

1. one focus-coupled hidden DOM input host,
2. mirrored selection and composition ranges,
3. deterministic mapping between proxy caret and rendered caret.

Rendered cursor/selection state <a id="REQ-TEXT-EDITING-CONTRACT-V1-141639E428"></a>MUST remain in sync with proxy state.

## 6. Undo/Redo Integration

Text-edit operations <a id="REQ-TEXT-EDITING-CONTRACT-V1-8A34A55B20"></a>MUST integrate with `command-undo-redo-contract-v1.md` as reversible transactions with coalescing windows defined by backend policy.

## 7. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `text-edit.invalid-selection-range` | Selection range is out of bounds. | Conditional | Clamp/repair range and retry operation. |
| `text-edit.composition-state-invalid` | Composition event sequence is malformed. | Conditional | Reset composition state and continue. |
| `text-edit.proxy-sync-lost` | Canvas/WebGL proxy and rendered state diverged. | Conditional | Rehydrate from canonical text state and restore focus. |
| `text-edit.operation-unsupported` | Backend lacks requested editing operation. | No | Disable operation or route to fallback editor surface. |

## 8. Conformance

An implementation is conformant only if Sections 2-7 are enforced.
