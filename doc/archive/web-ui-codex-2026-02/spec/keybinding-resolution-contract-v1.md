# Keybinding Resolution Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Deterministic keybinding registration, lookup, trace reporting, and conflict analysis for `web-ui` command dispatch  
Depends on: `web-ui/spec/command-schema-v1.json`, `web-ui/spec/ui-state-schema-v1.json`, `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/src/commands.mjs`, `web-ui/src/state.mjs`  
Compatibility: `v1.x` preserves scope identifiers, precedence traversal semantics, trace reason vocabulary, and conflict tie-break ordering; incompatible changes require `v2`.

## 1. Purpose

This contract defines canonical behavior for keybinding registration and resolution in `web-ui`.
It is normative for keybinding maps, precedence lookup, trace reporting, conflict diagnostics, and command-surface defaults.

## 2. Canonical Model

## 2.1 Scope Set

Conformant scope IDs are a closed set:

1. `global`
2. `task`
3. `context`
4. `widget`

## 2.2 Default Precedence

Unless explicitly overridden at registry creation, precedence <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-DF47338328"></a>MUST be:

1. `global`
2. `task`
3. `context`
4. `widget`

## 2.3 Keymap Lanes

Registry keymaps <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-683958A733"></a>MUST expose:

1. `keymaps.global`: map of `key -> commandId`.
2. `keymaps.task`: map of `taskId -> (key -> commandId)`.
3. `keymaps.context`: map of `contextId -> (key -> commandId)`.
4. `keymaps.widget`: map of `widgetId -> (key -> commandId)`.

`commandId` values SHOULD reference registered command IDs from `command-schema-v1.json`.

## 3. Binding Algorithm (`bindKey`)

Given `(registry, scope, key, commandId, scopeId?)`:

1. Unknown `scope` <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-57EF46629E"></a>MUST throw.
2. For `global`, `scopeId` <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-DC814EC413"></a>MUST be ignored.
3. For non-global scopes, missing `scopeId` <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-E062F8470B"></a>MUST throw.
4. If an existing binding at the same key slot is replaced with a different command:
- Binding <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-FEC42B986D"></a>MUST still be updated to the new command.
- A conflict record <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-E9D24307ED"></a>MUST be appended to `registry.keymapConflicts` with:
  1. deterministic `id` (`bind-conflict-*` pattern),
  2. `key`,
  3. `winner` entry (new command),
  4. `shadowed` entry (previous command),
  5. `reason = "override"`.

## 4. Resolution Algorithm (`resolveKey`)

Given `(registry, key, ctx)`:

1. Resolver <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-A12F529D35"></a>MUST traverse scopes in `registry.precedence` order.
2. For `global`, resolver <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-AB48988727"></a>MUST test `keymaps.global[key]`.
3. For non-global scope `S`, resolver <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-280C062BF6"></a>MUST read `ctx[S + "Id"]` as scope lane ID.
4. Missing scope ID <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-E545562D0C"></a>MUST skip that scope without error.
5. Missing scope map for supplied scope ID <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-65C71789F7"></a>MUST skip that scope without error.
6. First matching command in traversal order <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-638B5E6E6D"></a>MUST win.
7. If no match exists, resolver <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-BD4A509432"></a>MUST return `null`.

## 5. Trace Algorithm (`resolveKeyWithTrace`)

`resolveKeyWithTrace` <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-74A16ECDF3"></a>MUST emit ordered per-scope trace entries with:

1. `scope`
2. `scopeId`
3. `key`
4. `commandId`
5. `matched`
6. `reason`

Closed-set `reason` values are:

1. `unbound`
2. `missing-scope-id`
3. `no-scope-map`
4. `null` (on match)

Rules:

1. Trace <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-D1942B4026"></a>MUST follow precedence order until match or exhaustion.
2. On match, traversal <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-9344F7D613"></a>MUST stop and return `{ commandId, trace }`.
3. On miss, return <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-0C55FBB029"></a>MUST be `{ commandId: null, trace }`.
4. Command-surface trace views MAY append post-match pseudo-entries with `reason = "skipped-after-match"` for explainability, but core resolver output <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-27098E750B"></a>MUST remain as above.

## 6. Conflict Analysis (`analyzeKeybindingConflicts`)

For each key, analyzer <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-114389B203"></a>MUST:

1. Collect all bound entries across global, task, context, and widget maps.
2. Sort entries by:
- precedence index,
- lexical `scopeId` (`null` treated as empty string),
- lexical `commandId`.
3. Treat first sorted entry as `winner`.
4. Emit each remaining entry as `shadowed` against `winner`.
5. Set conflict reason:
- `duplicate-binding` when `winner.scope == shadowed.scope` and `winner.scopeId == shadowed.scopeId`,
- `shadowed-by-precedence` otherwise.
6. Append existing `registry.keymapConflicts` records (bind-time overrides).
7. When `options.key` is supplied, return only conflicts for that key.

## 7. Command Surface Default Bindings

## 7.1 Palette Navigation Defaults

`bindCommandPaletteDefaults` <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-C4E7060D7E"></a>MUST bind:

1. `ArrowDown -> ui.command-palette.select-next`
2. `ArrowUp -> ui.command-palette.select-prev`
3. `Enter -> ui.command-palette.execute-selection`

Default scope is `task`; non-global use requires `taskId`.

## 7.2 Surface Open/Close Defaults

`bindCommandSurfaceDefaults` <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-2C707F28A6"></a>MUST bind:

1. `Ctrl+Shift+P -> ui.command-palette.open`
2. `Ctrl+Shift+K -> ui.keybindings.open`
3. `Escape -> ui.command-surface.dismiss`

Default scope is `global`; non-global use requires `taskId`.

## 8. Determinism and Tie-Break Rules

1. Precedence traversal <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-8FA516F2CD"></a>MUST be deterministic for fixed `(registry snapshot, key, ctx)`.
2. Resolver <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-6D4BBA6BED"></a>MUST NOT continue searching after first match.
3. Conflict sort order <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-6E4199B643"></a>MUST remain stable and lexical as in Section 6.
4. Override diagnostics <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-06DE8C2674"></a>MUST preserve append order in `keymapConflicts`.
5. Keybinding view ordering SHOULD be lexical by key (and lexical by scope ID for scoped maps).

## 9. Security and Validation Requirements

1. Command IDs SHOULD be namespaced (`require-dot`) when registry policy requires it.
2. Key values <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-2F3A9CCB4D"></a>MUST be treated as untrusted input strings; dispatch <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-04758BD702"></a>MUST require explicit exact map hits.
3. Scopes outside Section 2.1 are invalid input and <a id="REQ-KEYBINDING-RESOLUTION-CONTRACT-V1-B16749AFE0"></a>MUST be rejected in binding APIs.
4. Command-surface shortcuts SHOULD remain capability-gated through command execution gates, not via keymap bypass.

## 10. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `keybinding-resolution.unknown-scope` | Binding requested against unsupported scope. | No | Use one of `global/task/context/widget`. |
| `keybinding-resolution.scope-id-required` | Non-global bind attempted without scope ID. | Yes | Supply `taskId/contextId/widgetId` lane ID. |
| `keybinding-resolution.key-unbound` | No binding matched for key/context. | Conditional | Bind key or adjust context lanes. |
| `keybinding-resolution.scope-id-missing` | Scoped lookup skipped due to missing lane ID. | Conditional | Provide required scope lane in context. |
| `keybinding-resolution.no-scope-map` | Scoped lookup skipped because scope map absent. | Conditional | Initialize scope map (bind at that scope ID). |
| `keybinding-resolution.binding-overridden` | Existing binding replaced by a newer bind operation. | N/A | Inspect conflict diagnostics if override was unintended. |

## 11. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/commands.test.mjs`
2. `web-ui/tests/phase-6-keymaps.test.mjs`
3. `web-ui/tests/command-ui.test.mjs`
4. `web-ui/tests/phase-7-keyboard-focus.test.mjs`

Pass criteria:

1. Precedence and custom precedence routing produce deterministic winners.
2. Trace output reasons match Section 5 and remain stable.
3. Conflict analyzer reasons and ordering match Section 6.
4. Default command-surface shortcuts resolve to expected command IDs.

## 12. Conformance

An implementation is conformant only if Sections 2-11 are satisfied.
