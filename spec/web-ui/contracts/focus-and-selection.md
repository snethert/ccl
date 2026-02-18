# Focus and Selection

## Status
⏸️ Not started

## Purpose

Manages focus targets and selection state across the UI. Focus is a four-field
target with five canonical reasons, reconciled against the DOM/state graph.
Selection supports replace, toggle, and range modes with list-order stability.
IME composition defers focus reconciliation.

## Depends On
- [renderer](renderer.md) — focus targets reference rendered elements

## Interface

```
FocusTarget {
  taskId:         string | null
  windowId:       string | null
  widgetId:       string | null
  presentationId: string | null
}

FocusReasons: "command" | "user" | "program" | "restore" | "reconcile"

FocusHistoryEntry {
  seq:      integer | null
  target:   FocusTarget | null
  reason:   FocusReason
  reasonId: string | null       // allocated when focusReasons lane exists
}

Selection {
  id:        string
  kind:      string
  targetIds: string[]           // ordered by list position
  anchorId:  string | null
  metadata:  object
}
```

**Focus normalization:** null/undefined → null. String/number → windowId only.
Object → normalize missing fields to null.

**Selection modes:** `replace` (set to one), `toggle` (add/remove),
`range` (anchor-to-target inclusive). `toggle` and `range` downgrade to
`replace` when `multiple=false`.

## Invariants

1. Focus target shape is exactly four nullable string fields
2. Focus history entries append in mutation call order (no reordering)
3. Reconciliation is suspended while IME composition is active
4. Selection ordering follows list item order, never insertion order
5. Range endpoints are inclusive and stable for repeated identical inputs
6. Unknown/stale IDs do not mutate state unless `allowUnknown=true`
7. Each `setFocus` call appends exactly one history entry

## Behavior

1. `setFocus`: normalize target, allocate reasonId if lane exists, append history entry
2. `setActiveTask`: when task changes and `updateFocus !== false`, focus updates to task's active window
3. `reconcileFocus`: resolve target via options.resolveTarget or DOM resolver, then complete partial targets from state graph (widgetId→windowId, windowId→taskId)
4. If reconciled target is null with `clearOnUnknown=true`, focus clears with "reconcile" reason
5. If reconciled target equals current focus, no history entry is appended
6. `normalizeSelection`: null→null, string→single-item, object→derive targetIds from targetIds/targets/targetId/target fields
7. `updateListSelection`: missing listId/itemId→unchanged; itemId not in universe→unchanged
8. Replace mode: set selection to target only, anchor to target
9. Toggle mode: add/remove target; adding moves anchor to target
10. Range mode: select inclusive anchor-to-target interval; fallback to replace if missing

## Anti-Patterns

1. Never trust DOM dataset attributes without validation
2. Never mutate focus for stale/unknown IDs without `allowUnknown=true`
3. Never append duplicate focus history entries (same target in sequence)
4. Never reorder selection items by insertion order instead of list order
5. Never reconcile focus during active composition without deferral guard
6. Never use partial focus targets without completing from state graph
7. Never persist focus/selection without schema validation on restore

## Out of Scope

- Visual focus indicators (see [renderer](renderer.md) and [doctrine](../doctrine.md))
- Key binding that triggers focus changes (see [command-system](command-system.md))
- Window z-order and modal stacking semantics

## Conformance Check
Run: `node spec/web-ui/checks/focus-and-selection.test.mjs`
