# Web-UI Subsystem

## Status

**Deferred (MVP-2)** — depends on MVP-1 kernel boot (FASL loading must work first).

## What This Subsystem Does

Browser-based IDE for CCL WASM. Lisp owns all UI state; JavaScript handles
rendering and input capture. Communication flows through a kernel_request-based
bridge: Lisp emits VDOM trees, JS renders them to DOM or Canvas/WebGL, and
input events flow back as batched binary payloads.

Full Runtime Mode (MVP-2) required: SharedArrayBuffer, Worker atomics, WASM
threads, secure context (COOP + COEP headers). No fallback to Library Mode.

## Dependencies

- **Requires**: Working WASM kernel with FASL loading (MVP-1, currently blocked)
- **Requires**: Runtime bridge via kernel_request ABI (kernel opcodes for UI)
- **Requires**: Secure context headers for SharedArrayBuffer
- **Provides**: Browser IDE with editing, debugging, inspection, persistence

## Component Map

```
Lisp Runner (WASM)
  │
  │  kernel_request: UI_RENDER (VDOM tree payload)
  │  kernel_request: UI_POLL   (event batch)
  │  kernel_request: UI_MEASURE_TEXT (font metrics)
  │
  ▼
JS Microkernel
  │
  ├─► Bridge Envelope     — Message framing between runtime and UI
  ├─► Wire Format Tree    — Binary VDOM encoding (UIB1)
  ├─► Renderer            — DOM or Canvas/WebGL backend
  ├─► Focus & Selection   — Focus targets, selection state, reconciliation
  ├─► Command System      — Key resolution, enablement gates, dispatch
  ├─► Text Editing        — IME lifecycle, hidden-input proxy, undo/redo
  ├─► Theme               — Token-based theming across all backends
  ├─► Persistence         — File-primary snapshots, refs, crash recovery
  └─► Security            — Startup gate, capability model, safe mode
```

## Implementation Order

Dependencies flow top-to-bottom. An AI follows this order, implementing
each contract only after its dependencies are complete.

| # | Contract | Depends On | Description |
|---|----------|------------|-------------|
| 1 | [bridge-envelope](contracts/bridge-envelope.md) | — | Message framing: 9 envelope kinds, normalization, error lane |
| 2 | [wire-format-tree](contracts/wire-format-tree.md) | — | Binary VDOM: UIB1 header, string table, node encoding |
| 3 | [theme](contracts/theme.md) | — | Shared token system for all backends |
| 4 | [renderer](contracts/renderer.md) | wire-format-tree, theme | DOM + Canvas/WebGL backends, reconciliation |
| 5 | [focus-and-selection](contracts/focus-and-selection.md) | renderer | Focus targets, selection modes, reconciliation |
| 6 | [command-system](contracts/command-system.md) | focus-and-selection | Key resolution, precedence, enablement, dispatch |
| 7 | [text-editing](contracts/text-editing.md) | renderer, command-system | IME lifecycle, hidden-input proxy, undo/redo |
| 8 | [security](contracts/security.md) | command-system | 12 startup checks, capability gating, safe mode |
| 9 | [persistence](contracts/persistence.md) | security | File-primary snapshots, refs, crash recovery |

## Key Design Decisions

Extracted from the original specification corpus (archived at
`doc/archive/web-ui-codex-2026-02/`):

1. **Lisp owns UI state** — JS is a rendering backend, not an application framework.
   Lisp builds VDOM trees, encodes them to binary, and submits via kernel_request.

2. **Binary wire format (UIB1)** — Little-endian binary with string table, not JSON.
   24-byte header, string deduplication, flat node list. Efficient for WASM↔JS boundary.

3. **Two renderer profiles** — `vdom-node-backend-v1` (DOM) and `scene-backend-v1`
   (Canvas/WebGL). Both consume shared theme tokens. DOM used for text-heavy surfaces.

4. **Determinism everywhere** — Identical inputs produce identical outputs for every
   component. Tie-breaks are explicit (visual stacking order, precedence index,
   lexical sort). No locale-dependent behavior.

5. **Capability-gated execution** — Commands require explicit capability grants.
   Safe mode blocks everything. No silent degradation.

6. **Fail-closed startup** — 12 prerequisite checks (SRG-01..SRG-12) must pass.
   Missing SharedArrayBuffer, Worker atomics, or WASM threads = hard stop.

7. **File primacy in persistence** — Files are authored units, not storage abstractions.
   Content-addressed immutable blobs. Atomic snapshot/ref model. Crash-safe.

8. **Bridge envelope framing** — All runtime↔UI messages wrapped in a 9-field
   envelope with version, kind, sequence, timestamp, payload, and error lane.

9. **Focus/selection as state machine** — Four-field focus target (task/window/widget/
   presentation). Five canonical reasons. State-graph completion for partial targets.
   Deferred reconciliation during IME composition.

10. **Command routing by precedence** — Total-order scope precedence (global → task →
    context → widget). First match wins. Enablement gates in fixed order. Runtime
    dispatch for Lisp-side commands.

11. **IME-aware text editing** — Composition lifecycle (start/update/commit/cancel)
    as separate state. Canvas/WebGL uses hidden-input proxy with cursor sync.

12. **Dark mode primary** — Independently designed (not inverted). Dark gray backgrounds,
    off-white text. Light and high-contrast lanes are tokenized and testable.

## Conformance

Run all checks:
```bash
node spec/web-ui/checks/run-all.mjs
```

Run one check:
```bash
node spec/web-ui/checks/<contract>.test.mjs
```

Check results use structured output:
```
PASS invariant.1 — Description
FAIL behavior.3 — Description
  Expected: ...
  Got: ...
```

Test IDs (`invariant.N`, `behavior.N`, `anti-pattern.N`) match numbered lists
in the corresponding contract.
