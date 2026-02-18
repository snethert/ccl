# Command System

## Status
⏸️ Not started

## Purpose

Key resolution, command enablement, and dispatch. Uses a total-order scope
precedence model (global → task → context → widget) where the first match
wins. Enablement gates execute in fixed order. Runtime-scoped commands
dispatch to the Lisp runner via kernel_request.

## Depends On
- [focus-and-selection](focus-and-selection.md) — provides routing context (active task/window/widget)

## Interface

```
CommandRegistry {
  precedence:     string[]        // total-order scope list
  commands:       {[id]: CommandSpec}
  keymaps:        {global: {}, [scopeId]: {}}
  namespacePolicy: "allow" | "require-dot"
}

CommandSpec {
  id:       string
  metadata: {runtime?: boolean, ...}
  exec?:    (ctx) => result
  enabled?: (ctx) => {enabled, reason}
  capability?: string
  hiddenInBeginnerMode?: boolean
  confirmBeginnerMode?:  boolean
}

RoutingContext {
  taskId?:    string
  contextId?: string
  widgetId?:  string
  state:      object              // required for capability/beginner checks
  args?:      object
  payload?:   any
}
```

**Execution result:**
```
{ok: boolean, reason?: string, pending?: boolean,
 runtimeDispatched?: boolean, requestId?: string,
 result?: any, invocation?: object}
```

## Invariants

1. `registry.precedence` is a complete total order — no ties
2. Same (registry snapshot, key, context) always resolves to the same command
3. Enablement gates execute in fixed order: unknown → beginner → capability → args → predicate
4. Safe mode blocks all capability-gated commands regardless of grants
5. Runtime-scoped commands return a pending envelope with requestId
6. Trace reasons are a closed set: `unbound`, `missing-scope-id`, `no-scope-map`, `null`

## Behavior

**Key resolution:**
1. Iterate scopes in `registry.precedence` order exactly
2. For `global` scope: check `keymaps.global[key]`, return on match
3. For scoped entries: derive scope ID from `ctx[scope+"Id"]`; missing ID skips scope
4. First match in precedence order wins; no match returns null
5. Trace entries are produced for each visited scope in traversal order

**Conflict analysis:**
6. Sort candidates by: scope precedence index, lexical scopeId (null as ""), lexical commandId
7. First sorted = winner; remaining = conflicts (duplicate-binding or shadowed-by-precedence)

**Enablement:**
8. Unknown command → disabled ("Unknown command")
9. Beginner-hidden command → disabled ("Hidden in Beginner Mode")
10. Safe mode active → disabled ("Safe mode")
11. Required capability missing → disabled ("Missing capability: <capability>")
12. Missing required args → disabled; command-level enabled predicate runs last

**Execution:**
13. Unknown/beginner-hidden/disabled commands fail with reason
14. Beginner confirmation gate returns `{ok:false, confirmation:{...}}` unless confirmed
15. Runtime commands (metadata.runtime=true or id starts with "runtime.") dispatch via runtime client
16. Non-typed commands without exec succeed with null result
17. Non-typed commands with exec succeed with exec(ctx) result

## Anti-Patterns

1. Never reorder enablement gates (the fixed order is normative)
2. Never skip a scope in precedence order during resolution
3. Never allow a later-precedence scope to override an earlier match
4. Never infer runtime context implicitly — it must be explicit
5. Never silently downgrade runtime dispatch to sync local execution
6. Never pass capability check when safe mode is active

## Out of Scope

- Key capture and event handling (browser-level concern)
- Command UI (menus, palettes) — visual concern
- Undo/redo integration (see [text-editing](text-editing.md))

## Conformance Check
Run: `node spec/web-ui/checks/command-system.test.mjs`
