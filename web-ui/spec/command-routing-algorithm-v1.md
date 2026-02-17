# Command Routing Algorithm v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Deterministic key-to-command resolution, enablement, and execution flow for `web-ui` command dispatch  
Depends on: `web-ui/spec/command-schema-v1.json`, `web-ui/spec/ui-state-schema-v1.json`, `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/src/commands.mjs`  
Compatibility: `v1.x` preserves precedence traversal, enablement ordering, trace reasons, and runtime dispatch gates; incompatible routing changes require `v2`.

## 1. Purpose

This contract defines the authoritative routing and execution algorithm for `web-ui` commands.
It is normative for keybinding lookup, command enablement checks, command execution, and routing traces.

## 2. Inputs and Model

Routing operates over a command registry and context.

Required registry lanes:

1. `precedence`: ordered scopes (default `global`, `task`, `context`, `widget`).
2. `commands`: registered command specs.
3. `keymaps`: keybinding maps for each scope.
4. `namespacePolicy`: `allow` or `require-dot`.

Required context lanes:

1. Scope IDs as applicable (`taskId`, `contextId`, `widgetId`).
2. `state` lane for capability and beginner-mode checks.
3. Optional typed-invocation seed lanes (`args`, `payload`, `item`, `invocation`, `selection`, `presentation`).

## 3. Key Resolution (`resolveKey`)

Given `(registry, key, ctx)`, resolution <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-5B76B9B5E4"></a>MUST iterate scopes exactly in `registry.precedence` order.

Rules:

1. For `global`, resolver <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-5D25EADE69"></a>MUST read `keymaps.global[key]` and return immediately on first match.
2. For scoped lanes (`task`, `context`, `widget`), resolver <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-7B99E36D3C"></a>MUST derive scope ID from `ctx[scope + "Id"]`.
3. If scope ID is missing, that scope <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-ABF35A84FA"></a>MUST be skipped.
4. If scope map does not exist for scope ID, that scope <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-70E0595956"></a>MUST be skipped.
5. First matched command ID in precedence order <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-6EF7F09D8B"></a>MUST win.
6. If no scope matches, resolver <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-E2EEC482B0"></a>MUST return `null`.

## 4. Trace Resolution (`resolveKeyWithTrace`)

`resolveKeyWithTrace` <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-72E4E5FF88"></a>MUST produce deterministic trace entries for each visited scope, in traversal order, until a match is found or scopes are exhausted.

Trace `reason` values are closed set:

1. `unbound`
2. `missing-scope-id`
3. `no-scope-map`
4. `null` (only when matched)

A successful match <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-1639C6FB23"></a>MUST stop traversal and return `{ commandId, trace }`.
A miss <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-E24F49DF8E"></a>MUST return `{ commandId: null, trace }`.

## 5. Conflict Analysis (`analyzeKeybindingConflicts`)

For a fixed key:

1. Candidate entries <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-DC45D2D7D9"></a>MUST be sorted by:
- Scope precedence index (`registry.precedence` order).
- Lexical `scopeId` (null treated as empty string).
- Lexical `commandId`.
2. First sorted entry is `winner`.
3. Remaining entries <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-767C91C319"></a>MUST be emitted as conflicts against that winner.
4. Conflict reason <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-130E8DB4D3"></a>MUST be:
- `duplicate-binding` when scope and scopeId equal winner.
- `shadowed-by-precedence` otherwise.
5. Prior bind-time overrides in `keymapConflicts` <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-94AD24A7C7"></a>MUST be appended as additional conflict records.

## 6. Enablement Algorithm (`commandEnabled`)

Given `(registry, commandId, ctx)`, evaluation order is normative:

1. Unknown command -> disabled (`Unknown command`).
2. Beginner policy hidden gate -> disabled (`Hidden in Beginner Mode`).
3. Capability gate:
- If safe mode active, disabled (`Safe mode`).
- If required capability missing, disabled (`Missing capability: <capability>`).
4. Typed command preflight:
- Materialize invocation defaults from context.
- If required args missing, disabled (`Missing required args: ...`).
5. Command-level `enabled` predicate:
- Normalize result to `{enabled, reason}` using boolean/tuple/object forms.
6. If no predicate blocks, command is enabled.

The gate order above <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-E3E2DC822B"></a>MUST NOT be reordered.

## 7. Execution Algorithm (`executeCommand`)

Given `(registry, commandId, ctx)`, execution order is normative:

1. Unknown command -> `{ ok:false, reason:"Unknown command" }`.
2. Beginner hidden gate -> `{ ok:false, reason:"Hidden in Beginner Mode" }`.
3. Beginner confirmation gate -> `{ ok:false, reason:"Confirmation required", confirmation:{...} }` unless `ctx.confirmBeginner=true`.
4. Run `commandEnabled`; if disabled, return `{ ok:false, reason }`.
5. Typed commands:
- Materialize invocation.
- Execute typed command pipeline.
- On typed failure, return `{ ok:false, reason, missing?, invocation? }`.
- If command is runtime-scoped (`metadata.runtime=true` or `id` starts with `runtime.`) and runtime command client exists, dispatch through runtime client.
- Runtime dispatch success <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-27BABD9C60"></a>MUST return `{ ok:true, pending:true, runtimeDispatched:true, requestId, promise?, result, invocation }`.
- Runtime dispatch failure <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-128E138435"></a>MUST return `{ ok:false, reason:"Runtime dispatch failed" | dispatched.reason, invocation }`.
6. Non-typed commands:
- If no `exec`, return `{ ok:true, result:null }`.
- Otherwise return `{ ok:true, result: exec(ctx) }`.

## 8. Presentation Translation

`resolvePresentationCommand` <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-947C3EEEA4"></a>MUST evaluate translators by key `<type>:<gesture>` where missing values normalize to `unknown` and `default` for lookup.

Translator return mapping:

1. String -> `{ commandId:<string>, context:ctx }`.
2. Object with `commandId` or `id` -> `{ commandId, context: result.context ?? ctx }`.
3. Falsy or unsupported shape -> `null`.

`executePresentationCommand` <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-0420C85E87"></a>MUST call `executeCommand` with resolved command ID and injected `presentation` in context.

## 9. Determinism and Tie-Break Rules

1. Precedence order <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-5F098D288B"></a>MUST be treated as total order.
2. Resolution <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-3C9DF947B8"></a>MUST be pure for fixed `(registry snapshot, key, ctx)`.
3. Conflict analysis sorting keys <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-974C92C6AA"></a>MUST remain stable and lexical.
4. Invocation default materialization sources <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-733E38A833"></a>MUST be evaluated in declared `defaultFrom` order.
5. A later scope <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-3905249F5E"></a>MUST never override an earlier successful scope match.

## 10. Security and Capability Requirements

1. Commands that mutate external host/runtime state SHOULD declare explicit capability requirements.
2. Safe mode <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-06CAA9F96E"></a>MUST block capability-gated commands regardless of individual grants.
3. Runtime dispatch <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-70C0E58369"></a>MUST pass explicit runtime context lane (`ctx.runtimeContext ?? ctx.context ?? {}`) and <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-522AD1AEF8"></a>MUST NOT infer privileged context implicitly.
4. Command IDs <a id="REQ-COMMAND-ROUTING-ALGORITHM-V1-CA09624F64"></a>MUST obey namespace policy when registry is configured with `require-dot`.

## 11. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `command-routing.command-unknown` | Command ID is not registered. | No | Register or correct command ID. |
| `command-routing.key-unbound` | No keybinding resolved for supplied key/context. | Conditional | Bind key or adjust focus/context IDs. |
| `command-routing.scope-id-missing` | Scoped lookup skipped due to missing scope ID. | Conditional | Provide appropriate `taskId`/`contextId`/`widgetId`. |
| `command-routing.missing-required-args` | Typed command lacks required arguments after defaulting. | Conditional | Supply missing args or add default sources. |
| `command-routing.capability-denied` | Safe mode or capability grant check failed. | Conditional | Exit safe mode or grant required capability. |
| `command-routing.beginner-confirmation-required` | Beginner policy requires explicit confirmation. | Yes | Re-dispatch with explicit confirmation. |
| `command-routing.runtime-dispatch-failed` | Runtime command dispatch rejected/failed. | Conditional | Inspect runtime transport/client state and retry if safe. |

## 12. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/commands.test.mjs`
2. `web-ui/tests/typed-commands.test.mjs`
3. `web-ui/tests/phase-5-runtime-command-dispatch.test.mjs`
4. `web-ui/tests/phase-7-keyboard-focus.test.mjs`

Pass criteria:

1. Deterministic precedence and trace assertions pass with no flaky outcomes.
2. Capability/safe-mode/beginner gates produce stable reasons.
3. Runtime-typed command dispatch path returns pending envelope and request ID.
4. Missing-args typed commands fail deterministically with explicit arg names.

## 13. Conformance

An implementation is conformant only if all conditions hold:

1. Key resolution and traces satisfy Sections 3-4.
2. Conflict analysis ordering satisfies Section 5.
3. Enablement and execution order satisfy Sections 6-7.
4. Determinism, security, and failure semantics satisfy Sections 9-11.
