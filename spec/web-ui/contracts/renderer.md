# Renderer

## Status
⏸️ Not started

## Purpose

Renders decoded VDOM trees to the browser. Two backend profiles: DOM-oriented
(`vdom-node-backend-v1`) for text-heavy surfaces and Canvas/WebGL-oriented
(`scene-backend-v1`) for graphical views. Both consume shared theme tokens.
Reconciliation is key-based with deterministic output.

## Depends On
- [wire-format-tree](wire-format-tree.md) — provides decoded VDOM trees
- [theme](theme.md) — provides shared token system

## Interface

**Profile 1: `vdom-node-backend-v1` (DOM)**
```
createElement(tag): node
createText(text): node
appendChild(parent, child): void
insertBefore(parent, child, anchor): void
removeChild(parent, child): void
setText(node, text): void
setProp(node, name, value, prev?): void
removeProp(node, name, prev?): void
replaceChild(parent, next, prev): void    // optional
destroy(node): void                        // optional
```

**Profile 2: `scene-backend-v1` (Canvas/WebGL)**
```
render(scene, options?): void
hitTest(point): {nodeId, x, y} | null
measureText(text, options?): {width, height, ascent, descent}
captureEvents(target, handlers, options?): unsubscribeFn
invalidate(callback): void
setTheme(theme): void                      // optional
getScene(): Scene                          // optional
```

## Invariants

1. Implementations MUST conform to at least one profile
2. For fixed (input tree, backend state, options), output is identical (deterministic)
3. Child keys MUST be unique per sibling set; duplicates fail reconciliation
4. After reconciliation, child order MUST match the next tree exactly
5. Hit-test tie-breaks follow visual stacking order (topmost wins, deterministic)
6. Font choice is deterministic: options → backend theme → profile fallback

## Behavior

1. Keyed children with same type patch in place
2. Keyed children with type change are replaced (unmount + mount)
3. Missing keyed children in next tree are removed/unmounted
4. Unkeyed children use stable fallback key by index
5. Multiple renders before flush coalesce to the latest tree
6. Explicit `flush()` applies the pending render synchronously
7. `captureEvents` returns an unsubscribe function removing all listeners from that call
8. `invalidate` schedules callback on animation frame or timeout; cancellation is idempotent
9. When dirty hints are provided, redraw restricts scope; otherwise full redraw
10. Measurement with missing font context degrades deterministically to zeros

## Anti-Patterns

1. Never produce non-deterministic render output for the same input
2. Never allow duplicate sibling keys
3. Never patch across incompatible node types
4. Never use locale-dependent measurement
5. Never produce non-deterministic key fallback for unkeyed children
6. Never change child order after reconciliation

## Out of Scope

- Wire format encoding/decoding (see [wire-format-tree](wire-format-tree.md))
- Theme token definitions (see [theme](theme.md))
- Focus management during rendering (see [focus-and-selection](focus-and-selection.md))

## Conformance Check
Run: `node spec/web-ui/checks/renderer.test.mjs`
