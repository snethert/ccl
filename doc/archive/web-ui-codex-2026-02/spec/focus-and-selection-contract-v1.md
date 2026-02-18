# Focus and Selection Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-16  
Scope: Deterministic focus target lifecycle, focus reconciliation, and selection semantics for `web-ui` core state  
Depends on: `web-ui/spec/ui-state-schema-v1.json`, `web-ui/spec/command-schema-v1.json`, `web-ui/spec/normative-language-and-conformance-v1.md`, `web-ui/src/focus.mjs`, `web-ui/src/selection.mjs`, `web-ui/src/state.mjs`  
Compatibility: `v1.x` preserves focus target shape, focus reason semantics, and list selection mode behavior; incompatible lifecycle changes require `v2`.

## 1. Purpose

This contract defines canonical behavior for focus and selection state in `web-ui`.
It is normative for normalization, mutation, reconciliation, and deterministic history recording.

## 2. Canonical Data Shapes

## 2.1 Focus Target

A normalized focus target <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-66CFBBDC51"></a>MUST have exactly these fields:

1. `taskId`
2. `windowId`
3. `widgetId`
4. `presentationId`

Each field is nullable.

## 2.2 Focus Reasons

Canonical reason values are:

1. `command`
2. `user`
3. `program`
4. `restore`
5. `reconcile`

## 2.3 Focus History Entry

A history entry <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-CB841B5F47"></a>MUST include:

1. `seq` (nullable integer sequence)
2. `target` (normalized focus target or null)
3. `reason` (reason string)
4. `reasonId` (nullable stable ID when reason lane is recorded)

## 2.4 Selection

A normalized selection <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-BD6701AC20"></a>MUST include:

1. `id`
2. `kind`
3. `targetIds` (ordered list)
4. `anchorId`
5. `metadata`

## 3. Normalization Rules

## 3.1 `normalizeFocusTarget`

1. `null` or `undefined` <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-67DA2013F6"></a>MUST normalize to `null`.
2. String/number target <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-0EEDAB17A2"></a>MUST normalize to `{ taskId:null, windowId:String(value), widgetId:null, presentationId:null }`.
3. Object target <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-68028508F7"></a>MUST normalize missing fields to `null`.
4. Non-object, non-scalar values <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-B925A5F499"></a>MUST raise a validation error.

## 3.2 `sameFocusTarget`

1. Equality <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-0707BA044A"></a>MUST compare all four normalized fields.
2. `null` and `null` are equal.
3. Any null/non-null mismatch is not equal.

## 3.3 `normalizeSelection`

1. `null`/falsy selection <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-2C4BB7E8EB"></a>MUST normalize to `null`.
2. String selection <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-5E52EFB572"></a>MUST normalize to one-item target with `kind="item"` and `anchorId=id`.
3. Object selection <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-19D8F22CEB"></a>MUST derive `targetIds` from `targetIds`, `targets`, `targetId`, or `target` (in that order).
4. Selection without `id` and without derivable target <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-2369F7E8CD"></a>MUST raise a validation error.
5. `anchorId` <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-74B3460419"></a>MUST default to explicit anchor, then target, then first target ID.

## 4. Focus Mutation Rules

## 4.1 `setFocus`

Given `(state, target, reason, seq)`:

1. Target <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-E903BEEEB2"></a>MUST be normalized first.
2. If `state.focusReasons` lane exists, a new `reasonId` <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-2402E56014"></a>MUST be allocated and inserted before history append.
3. History entry sequence <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-1642BEA1AF"></a>MUST be `seq` when provided; otherwise `focusHistory.length + 1`.
4. Mutation <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-F46A2932B1"></a>MUST append exactly one history entry per call.
5. Returned state <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-63B15ED4A9"></a>MUST set `focus` to the normalized target.

## 4.2 `setActiveTask` Interaction

When active task changes and `updateFocus` is not explicitly `false`:

1. Focus <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-F458BEA01B"></a>MUST update to `{ taskId, windowId:activeWindowId|null, widgetId:null, presentationId:null }`.
2. Task fallback active window <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-E1DA073E28"></a>MUST be first `windowIds[]` entry when `activeWindowId` is unset.

## 5. Focus Reconciliation Rules

Given `(state, event, options)`:

1. If `deferWhileComposing=true` and composition is active, reconciliation <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-5A20B5F3F5"></a>MUST return the original state unchanged.
2. Target resolver order <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-A38D3F7181"></a>MUST be:
- `options.resolveTarget` when provided.
- Default DOM resolver using nearest `data-widget-id`, `data-window-id`, `data-task-id`, `data-presentation-id`.
3. Partial targets <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-92918B0B59"></a>MUST be completed from state graph:
- `widgetId -> windowId` via widget lane.
- `windowId -> taskId` via window lane.
4. If resolved target is null:
- With `clearOnUnknown=true`, focus <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-FCE46E6D48"></a>MUST be set to null with reconcile reason.
- Otherwise state <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-476F801D1E"></a>MUST remain unchanged.
5. Invalid targets (missing referenced task/window/widget) <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-D5B30F60C5"></a>MUST be rejected unless `allowUnknown=true`.
6. If resolved target equals current focus, state <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-6A5687DC7F"></a>MUST remain unchanged (no duplicate history append).

## 6. Selection Mutation Rules

`setSelection` <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-A685A8026F"></a>MUST store normalized selection directly.

## 6.1 List Selection (`updateListSelection`)

For `(state, { listId, itemId, mode, multiple, listItemIds? })`:

1. Missing `listId` or `itemId` <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-862BAAC2D1"></a>MUST return state unchanged.
2. Effective item universe <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-9C52492FE9"></a>MUST be:
- Explicit `listItemIds` when provided.
- Otherwise list widget item IDs derived from `widget.props.items` then `widget.model.items`.
3. If effective universe is non-empty and `itemId` not in universe, state <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-B1D41A779A"></a>MUST remain unchanged.
4. Mode normalization:
- `toggle` and `range` <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-EAE5C0E9C6"></a>MUST downgrade to `replace` when `multiple=false`.
5. Replace mode <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-BEEBDB2AC6"></a>MUST set selection to only target item and set anchor to target.
6. Toggle mode <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-5B6A8A6859"></a>MUST add/remove target from selected set; adding target <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-96D56AADCE"></a>MUST move anchor to target.
7. Range mode <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-AEE085AE3F"></a>MUST select inclusive anchor-to-target interval when both are present; otherwise <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-3AD9851C13"></a>MUST fall back to replace behavior.
8. Selection ordering <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-9862A10773"></a>MUST follow list item order.
9. If resulting selected set is empty, selection <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-0CB8DCDDFA"></a>MUST be cleared (`null`).
10. Result metadata <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-2720560DE8"></a>MUST include `listId` and `multiple`.

## 7. Determinism and Tie-Break Rules

1. Focus target completion <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-325E100BF5"></a>MUST prefer state graph-derived IDs over ambiguous DOM ancestry.
2. Selection ordering <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-4ED4FE510B"></a>MUST be stable by list order, not insertion order.
3. Range endpoints <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-9B085D7D83"></a>MUST be inclusive and stable for repeated identical inputs.
4. Focus history append order <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-A4267D97A9"></a>MUST match mutation call order.

## 8. Security and Validation Requirements

1. Reconciliation from DOM targets <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-289F4EF7C1"></a>MUST treat dataset attributes as untrusted input.
2. Unknown or stale IDs <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-53B8A76286"></a>MUST not mutate focus unless `allowUnknown=true`.
3. Selection updates <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-803486CA71"></a>MUST reject out-of-list items when explicit `listItemIds` constraint is provided.
4. Persisted focus/selection payloads <a id="REQ-FOCUS-AND-SELECTION-CONTRACT-V1-01923BBF20"></a>MUST validate against `ui-state-schema-v1.json` before restore.

## 9. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `focus-selection.focus-target-invalid` | Focus target has invalid shape/type. | No | Correct target payload before dispatch. |
| `focus-selection.focus-target-unknown` | Target references missing task/window/widget without allow override. | Conditional | Refresh state IDs or opt into explicit unknown handling. |
| `focus-selection.selection-invalid` | Selection lacks required ID/target information. | No | Provide a valid selection payload. |
| `focus-selection.list-item-out-of-range` | Requested list item is not in constrained item universe. | Conditional | Refresh list items and retry with valid item ID. |
| `focus-selection.composition-deferred` | Focus reconciliation was deferred during composition. | Yes | Retry after composition end. |

## 10. Conformance Fixtures and Pass Criteria

Minimum required evidence:

1. `web-ui/tests/focus.test.mjs`
2. `web-ui/tests/selection.test.mjs`
3. `web-ui/tests/list-selection.test.mjs`
4. `web-ui/tests/phase-7-keyboard-focus.test.mjs`

Pass criteria:

1. Focus history sequence and reason recording are deterministic.
2. Reconciliation respects composition deferral and target completion rules.
3. Selection normalization and list selection modes (`replace`, `toggle`, `range`) match expected outputs.
4. Out-of-scope list targets do not mutate selection.

## 11. Conformance

An implementation is conformant only if:

1. Data shapes and normalization satisfy Sections 2-3.
2. Focus mutation/reconciliation satisfy Sections 4-5.
3. Selection and list selection semantics satisfy Section 6.
4. Determinism, validation, and failure semantics satisfy Sections 7-9.
