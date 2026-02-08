# Phase 0 Spec: Restart and Condition Contract (v0)

## Purpose
Define the metadata contract for restarts and condition reports so the debugger can be restart-first and transparent.

## Goals
- Restarts are actionable with schema and safety metadata.
- Condition reports are structured into actionable sections.
- The debugger can show a recommended restart without hiding alternatives.

## Non-Goals
- Full debugger UI layout.
- Runtime-specific error taxonomy.

## Condition Report Schema
```json
{
  "id": "err-001",
  "kind": "error",
  "message": "Division by zero",
  "summary": "Attempted (/ 1 0)",
  "sections": [
    {"id": "sec-1", "title": "What happened", "text": "...", "actions": []},
    {"id": "sec-2", "title": "Location", "location": {"file": "src/foo.lisp", "line": 12}}
  ],
  "stack": [
    {"frameId": "frame-1", "function": "FOO", "location": {"file": "src/foo.lisp", "line": 12}}
  ],
  "restarts": ["rst-1", "rst-2"]
}
```

## Restart Schema
```json
{
  "id": "rst-1",
  "title": "Use value",
  "description": "Provide a replacement value for the division.",
  "safety": "safe",
  "argSchema": [
    {"name": "value", "type": "number", "required": true}
  ],
  "preview": {"text": "Will replace the divisor with 1."},
  "recommended": true
}
```

### Safety Levels
- `safe`: reversible or low-risk.
- `destructive`: modifies state, but reversible.
- `irreversible`: may discard or commit changes.

## Presentation Integration
- Each restart is a `restart` presentation with its metadata.
- Each condition section is a `condition-section` presentation.

## Invariants
- Recommended restarts are always transparent and optional.
- Every restart exposes its arg schema and safety level.
- Condition sections remain readable even if stack frames are stale.

## Phase 0 Decisions
- Recommended restart selection is runtime-hinted and client-policy filtered; the shown recommendation must include a visible reason.
- Restarts with complex arguments use `argSchema` plus `uiHint` metadata, with a guaranteed generic form fallback.
