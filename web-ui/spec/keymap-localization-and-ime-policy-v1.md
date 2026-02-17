# Keymap Localization and IME Policy v1

Status: Draft  
Version: 1.1.0  
Last updated: 2026-02-17  
Scope: Pane keymap profile semantics, localization behavior, and IME/dead-key event policy for `web-ui`  
Depends on: `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/spec/command-schema-v1.json`, `web-ui/src/customization.mjs`, `web-ui/src/state.mjs`, `web-ui/src/focus.mjs`, `web-ui/bridge/ui-bridge.mjs`, `web-ui/bridge/codec.mjs`  
Compatibility: `v1.x` preserves pane IDs, profile IDs, binding normalization semantics, composition phase encoding, and IME/dead-key handling behavior; incompatible policy changes require `v2`.

## 1. Purpose

This contract defines how `web-ui` keymaps are normalized and merged across customization layers, and how localized/IME keyboard input is captured and propagated.
It is normative for keymap profiles, active binding materialization, locale behavior, and composition/dead-key handling.

## 2. Canonical Keymap Model

## 2.1 Closed Sets

Conformant pane IDs:

1. `editor`
2. `repl`
3. `debugger`

Conformant keybinding scopes:

1. `global`
2. `task`
3. `context`
4. `widget`

## 2.2 Default Pane Profile Assignments

Default pane profile map <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-B4213B7A4C"></a>MUST be:

1. `editor -> editor-emacs`
2. `repl -> repl-readline`
3. `debugger -> debugger-single-key`

## 2.3 Built-in Read-Only Profiles

Built-in profile IDs <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-44459A36F4"></a>MUST exist and be read-only:

1. `editor-emacs`
2. `repl-readline`
3. `debugger-single-key`

At minimum, these default bindings <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-4E64EB80CF"></a>MUST remain:

1. `editor-emacs`: `Ctrl+Enter -> runtime.eval.defun`, `Alt+. -> lisp.jump.definition`.
2. `repl-readline`: `Enter -> runtime.repl.submit`, `Ctrl+R -> runtime.repl.history.search`.
3. `debugger-single-key`: `n -> ui.debugger.frame.next`, `r -> ui.debugger.restart.invoke`.

## 3. Layer Merge Semantics

Effective customization <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-A116F5C163"></a>MUST apply layers in strict order:

1. `defaults`
2. `user`
3. `project`
4. `session`

Rules:

1. `paneProfiles` merge by object overlay (later layer wins per pane key).
2. `profiles` merge by profile ID; attempts to override read-only built-ins <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-E21A96DAA7"></a>MUST be ignored.
3. `customBindings` merge by fingerprint:
- `pane|scope|scopeId|key`
- later layer binding replaces earlier binding for the same fingerprint.
4. Effective output <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-757E3A26CB"></a>MUST be deterministic for fixed inputs.

## 4. Binding Normalization Rules

Given raw binding object:

1. Binding <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-0212170625"></a>MUST be discarded when not an object.
2. `pane` <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-AA052AF9FF"></a>MUST be one of Section 2.1 panes when present; otherwise binding <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-26B398502A"></a>MUST be discarded.
3. `scope` defaults to `context` when missing/invalid.
4. `key` and `commandId` <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-5A47E13E89"></a>MUST be non-empty strings; otherwise binding <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-0A1D86DC50"></a>MUST be discarded.
5. `id` defaults to `binding-<index+1>` when missing.
6. `scopeId` defaults to:
- supplied `scopeId` when valid string, else
- `pane:<pane>` when `scope=context` and pane is known, else
- `null`.
7. `source` defaults to `custom`.

Profile normalization rules:

1. Invalid/non-object profiles <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-4D7198B304"></a>MUST be discarded.
2. `id` <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-79786B2F29"></a>MUST resolve from explicit `id` or profile-map key.
3. `pane` <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-AA198F739B"></a>MUST be valid pane or explicit profile default pane.
4. `bindings` <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-F38D776466"></a>MUST be normalized with the same rules above.

## 5. Active Binding Materialization and Registry Application

## 5.1 Active Binding Build

Active bindings <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-B904F721F4"></a>MUST be materialized by:

1. Expanding assigned pane profile bindings for each pane with source `profile:<profileId>`.
2. Appending `customBindings` with source defaulting to `custom`.
3. Filtering to entries with string `key` and string `commandId`.

## 5.2 Registry Projection (`applyCustomizationKeymapsToRegistry`)

Rules:

1. By default, existing context maps for pane scopes (`pane:editor`, `pane:repl`, `pane:debugger`) <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-5B1866E9B9"></a>MUST be cleared before re-apply.
2. `clearExisting=false` MAY disable this clearing behavior.
3. `paneContextIds` MAY override default `pane:<pane>` context IDs.
4. Non-global bindings <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-3598CDBE95"></a>MUST resolve a scope ID before bind; unresolved IDs <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-CBEAFBDA9B"></a>MUST be skipped.
5. Each materialized binding <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-F665040DB6"></a>MUST be passed through `bindKey` with normalized scope and resolved scope ID.

## 5.3 Keymap Conflict Diagnostics

Conflict diagnostics <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-C877CE1F38"></a>MUST fingerprint entries by:

1. `pane`
2. `scope`
3. `scopeId`
4. `key`

For repeated fingerprints with differing command IDs, last binding <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-571D19E30F"></a>MUST win and diagnostics <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-98D6E42732"></a>MUST record:

1. replaced command/source
2. winning command/source
3. deterministic conflict ID

## 6. Localization Policy (`v1`)

1. Key resolution is exact-string matching; no locale remapping or translation layer is applied in `v1`.
2. Binding keys <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-28CBA18DF5"></a>MUST be interpreted as symbolic key tokens (for example `Ctrl+Enter`, `Alt+.`) supplied by the integration layer.
3. Physical key mapping <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-54C4693C30"></a>MUST implement the minimal interoperable subset in Section 6.1.
4. Locale-dependent key differences <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-2CADFE8882"></a>MUST be handled through explicit profile/custom bindings.
5. Implementations SHOULD prefer modifier+non-text shortcuts for cross-locale portability.

### 6.1 Minimal Physical-Key Interoperable Subset (`v1`)

Canonical token source rules:

1. For non-printable keys, tokenization <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-3CC910A0CC"></a>MUST use `KeyboardEvent.code`.
2. For printable text keys, tokenization <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-0C20E8B340"></a>MUST use normalized `KeyboardEvent.key` (single code point or named token).
3. Modifier ordering in emitted binding tokens <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-88CED55220"></a>MUST be `Ctrl+Alt+Shift+Meta+<base>`.
4. Dead-key sequences <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-CACD7C68DC"></a>MUST preserve `key=\"Dead\"` identity and <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-24A5959ACB"></a>MUST NOT emit synthetic printable command tokens until composition commit.

Required non-printable base-key coverage:

1. `Enter`, `Escape`, `Tab`, `Backspace`, `Delete`, `Space`
2. Arrow keys: `ArrowUp`, `ArrowDown`, `ArrowLeft`, `ArrowRight`
3. Function keys: `F1`-`F12`
4. Navigation keys: `Home`, `End`, `PageUp`, `PageDown`

Interoperability boundary:

1. Implementations MAY add locale- or hardware-specific mappings beyond this subset.
2. Extensions <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-CC6EDA726F"></a>MUST NOT redefine semantics of required subset tokens.

## 7. IME and Composition Policy

## 7.1 Bridge Event Capture

UI bridge <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-96A93399AA"></a>MUST capture, in document capture phase:

1. `keydown`
2. `keyup`
3. `compositionstart`
4. `compositionupdate`
5. `compositionend`
6. `beforeinput`

Key event payload <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-E39ACA1BE5"></a>MUST include:

1. `key`
2. `code`
3. `modifiers`
4. `repeat`
5. `location`
6. `isComposing`
7. `text` (single-character key only)

Composition payload <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-2CFFC598FE"></a>MUST include:

1. `phase` (`0=start`, `1=update`, `2=end`)
2. `data`

Text-event capture policy:

1. `beforeinput` with non-empty `data` <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-06AD8016CB"></a>MUST emit a text event.
2. Empty text payloads <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-EDC52F1B72"></a>MUST be ignored.

## 7.2 Focus Interaction During Composition

When focus reconciliation is invoked with `deferWhileComposing=true` and composition is active:

1. Focus state <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-EAA7B2B2D0"></a>MUST remain unchanged.
2. No focus-history entry <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-F959EEC7B5"></a>MUST be appended.

Composition activity MAY be supplied through:

1. `options.isComposing`
2. `options.compositionActive`
3. `options.compositionState.active`
4. `event.isComposing`

## 7.3 IME/Dead-Key Behavioral Expectations

Conformant behavior <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-8EB654FAA2"></a>MUST preserve:

1. Baseline composition sequence (`start -> update -> end`) with committed value propagation.
2. Cancelled composition semantics (no unintended commit).
3. Multi-step composition updates before final commit.
4. Selection-range stability during active composition.
5. Dead-key identity (`key = "Dead"` on keydown/keyup).
6. Mobile text input through `beforeinput`/`input` insert-text flow.

## 8. Determinism and Tie-Break Rules

1. Layer merge order <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-9E4368D1AD"></a>MUST remain fixed as Section 3.
2. Binding replacement for duplicate fingerprints <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-53CF2F7F0C"></a>MUST be last-writer-wins.
3. Registry re-apply output <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-3C05B734B8"></a>MUST be deterministic for fixed state and pane context mapping.
4. Composition phase encoding <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-02A29B5647"></a>MUST remain stable (`0/1/2`) across producers and consumers.

## 9. Security and Validation Requirements

1. Keyboard/composition payloads <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-14C025B6F8"></a>MUST be treated as untrusted input and validated by shape/type.
2. Invalid pane/scope/binding records <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-B2E2FD9ECA"></a>MUST be dropped rather than partially applied.
3. Read-only built-in profiles <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-4EB87C331B"></a>MUST NOT be mutable through customization merge.
4. IME/dead-key events <a id="REQ-KEYMAP-LOCALIZATION-AND-IME-POLICY-V1-39F6F4CD50"></a>MUST not bypass command capability/safety gates.

## 10. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `keymap-l10n.binding-dropped` | Invalid binding payload omitted during normalization. | Conditional | Correct binding fields and reapply profile/layer. |
| `keymap-l10n.readonly-profile-ignored` | Attempt to overwrite read-only built-in profile was ignored. | No | Use custom profile ID instead of built-in override. |
| `keymap-l10n.scope-id-unresolved` | Non-global binding could not resolve scope ID and was skipped. | Conditional | Supply `scopeId` or pane context mapping. |
| `keymap-l10n.locale-key-unmapped` | Locale-specific key token has no configured binding. | Conditional | Add locale-appropriate custom binding/profile. |
| `keymap-l10n.composition-deferred` | Focus reconciliation deferred while composing. | Yes | Retry reconcile after composition end. |
| `keymap-l10n.bridge-event-overflow` | Event batch exceeded poll limits (`E2BIG`). | Yes | Increase poll budget or drain more frequently. |

## 11. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/phase-6-customization.test.mjs`
2. `web-ui/tests/phase-6-keymaps.test.mjs`
3. `web-ui/tests/phase-6-integration.test.mjs`
4. `web-ui/tests/focus.test.mjs`
5. `web-ui/tests/bridge-codec.test.mjs`
6. `web-ui/tests/browser.test.mjs`

Pass criteria:

1. Keymap layer precedence and pane profile assignment are deterministic.
2. Conflicting fingerprint replacements are deterministic and diagnosable.
3. IME composition, cancellation, multi-step input, selection stability, dead keys, and mobile input paths pass harness checks.
4. Composition-aware focus deferral behavior is stable and non-destructive.

## 12. Conformance

An implementation is conformant only if Sections 2-11 are satisfied.
