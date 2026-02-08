# Phase 0 Spec: Selection and Action Model (v0)

## Purpose
Define a consistent selection model and action surface so users can select objects and apply operations without tool sprawl.

## Goals
- Single and multi-select across presentations.
- Context-aware action bar that adapts to selection.
- Multi-object operations (inspect all, describe all, compare, diff).

## Non-Goals
- Full UI layout or styling.
- Deep clipboard integration.

## Selection Schema
```json
{
  "id": "sel-001",
  "kind": "presentation",
  "targetIds": ["pres-1", "pres-2"],
  "anchorId": "pres-1",
  "metadata": {
    "source": "mouse",
    "ts": 1710012345000
  }
}
```

### Selection Rules
- A selection may contain multiple presentation ids.
- The anchor is the primary target for defaults.
- Selection is stable across re-render if presentation ids remain stable.

## Action Bar Model
The action bar is derived from the current selection:
- If selection is empty: show global actions.
- If selection contains a single item: show type-specific actions.
- If selection contains multiple items: show multi-object actions and shared actions.

### Example Multi-Select Actions
- Inspect all
- Describe all
- Trace these
- Compare
- Diff slots

## Command Integration
- Each action maps to a typed command.
- Action bar does not duplicate command palette; it is a contextual surface.

## Invariants
- Selection must never block keyboard navigation.
- Multi-select actions should degrade gracefully if some targets are stale.

## Phase 0 Decisions
- Selection is scoped to the active window and does not persist across workspace switches unless explicitly restored from snapshot.
- Multi-type selection actions are computed by set intersection first, then stable priority ordering: `inspect`, `describe`, `open-source`, `do-again`, followed by alphabetic fallback.
