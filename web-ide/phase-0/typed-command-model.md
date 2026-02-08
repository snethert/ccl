# Phase 0 Spec: Typed Command Model (v0)

## Version
Schema version: `0`

## Purpose
Unify mouse-first and keyboard-first interaction by routing all actions through typed, replayable command objects.

## Goals
- Commands have typed arguments with defaults and validation.
- Commands are serializable and replayable.
- Command history stores structured arguments, not strings.
- DWIM defaults are explicit and visible before execution.

## Non-Goals
- Full Lisp macro expansion semantics.
- Distributed command execution (handled by bridge).

## Command Schema
```json
{
  "id": "editor.goto-definition",
  "title": "Go to Definition",
  "doc": "Jump to the definition of a symbol.",
  "scope": "context",
  "capability": "source.read",
  "args": [
    { "name": "symbol", "type": "symbol", "required": true }
  ],
  "enabled": "function",
  "exec": "function",
  "metadata": {}
}
```

### Argument Types (Initial Set)
- `string`, `number`, `boolean`
- `symbol`, `package`
- `file`, `location`
- `presentation`, `selection`
- `frame`, `binding`, `place`
- `command` (for do-again)
- `list`, `map`

### Argument Schema
```json
{
  "name": "symbol",
  "type": "symbol",
  "required": true,
  "default": null,
  "defaultFrom": ["selection", "presentation", "lastResult"],
  "coerce": "function",
  "validate": "function"
}
```

## Invocation Model
```json
{
  "id": "inv-0001",
  "commandId": "editor.goto-definition",
  "args": { "symbol": { "name": "FOO", "package": "CL-USER" } },
  "defaults": { "symbol": { "source": "selection" } },
  "ts": 1710012345000,
  "source": "palette",
  "result": { "ok": true }
}
```

### Argument Resolution (DWIM Order)
1. Explicit args supplied by caller.
2. Presentation clicked (if available).
3. Current selection or focus target.
4. Context defaults (package, last definition, last result).
5. Prompt user for missing arguments.

Every command must expose the inferred defaults before execution.

## Command History
- Stored as structured invocations.
- Supports "do again" and "do again with args".
- Persisted in workspace snapshots.

## Execution Pipeline
1. Resolve command by id.
2. Check enablement and capability gates.
3. Resolve arguments (DWIM).
4. Execute command.
5. Record invocation and result.

## Serialization
- Commands and invocations serialize to JSON.
- Functions are not serialized; `commandId` is the reference.
- Arguments must be serializable types or references to presentations.

## Invariants
- A command with the same id and args should produce the same effect given the same state.
- Command execution must be auditable via history entries.

## Phase 0 Decisions
- Argument coercion is pluggable by type through a coercer registry, with optional per-argument override.
- The command palette must show inferred defaults in a preview row before execute, including source (`selection`, `presentation`, `lastResult`, `context`).
