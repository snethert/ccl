# Drag and Drop Interaction Contract v1

Status: Draft  
Version: 1.0.0  
Last updated: 2026-02-17  
Scope: Drag source/target negotiation and drop semantics for windows, tabs, docking, and list reordering  
Depends on: `web-ui/spec/focus-and-selection-contract-v1.md`, `web-ui/spec/ui-interaction-window-management-contract-v1.md`, `web-ui/spec/command-schema-v1.json`  
Compatibility: `v1.x` preserves session lifecycle, target negotiation vocabulary, and deterministic drop resolution; incompatible protocol changes require `v2`.

## 1. Purpose

This contract defines cross-backend drag-and-drop behavior.

## 2. Drag Session Lifecycle

Each drag gesture <a id="REQ-DRAG-AND-DROP-INTERACTION-CONTRACT-V1-34BB4FB6BD"></a>MUST create a `dragSession` with:

1. `dragSessionId`
2. `sourceId`
3. `sourceType`
4. `payloadDescriptor`
5. `startedAtSeq`

Lifecycle states:

1. `idle`
2. `dragging`
3. `hover-target`
4. `dropped`
5. `cancelled`

## 3. Target Negotiation

Drop targets declare accepted payload kinds and operation modes (`move|copy|link|none`).

Rules:

1. Target matching <a id="REQ-DRAG-AND-DROP-INTERACTION-CONTRACT-V1-CD7B18B243"></a>MUST be deterministic by geometry and z-order precedence.
2. If multiple targets match, tie-break <a id="REQ-DRAG-AND-DROP-INTERACTION-CONTRACT-V1-23749BD447"></a>MUST use stable priority then lexical target ID.
3. Target negotiation <a id="REQ-DRAG-AND-DROP-INTERACTION-CONTRACT-V1-05FF74F3D5"></a>MUST return explicit rejection reason when `none`.

## 4. Visual and Accessibility Feedback

While dragging, system <a id="REQ-DRAG-AND-DROP-INTERACTION-CONTRACT-V1-2CAA9DDE48"></a>MUST expose:

1. active drag affordance,
2. current drop-zone highlight,
3. keyboard equivalent actions for accessible workflows.

Non-DOM surfaces <a id="REQ-DRAG-AND-DROP-INTERACTION-CONTRACT-V1-F29E85F07E"></a>MUST mirror feedback through accessibility proxy lanes.

## 5. Drop Commit Semantics

1. Drop commit is command-driven and transactional.
2. Failed drop commit <a id="REQ-DRAG-AND-DROP-INTERACTION-CONTRACT-V1-0502B46978"></a>MUST leave source and target state unchanged.
3. Successful drop commit SHOULD produce undoable transaction through undo/redo contract.

## 6. Failure Semantics

| Code | Meaning | Retryability | Caller obligation |
|---|---|---|---|
| `drag-drop.target-unavailable` | No eligible target at drop point. | Yes | Keep dragging, cancel, or choose valid target. |
| `drag-drop.operation-rejected` | Target rejected requested operation mode. | Conditional | Retry with accepted mode. |
| `drag-drop.payload-invalid` | Drag payload descriptor malformed/stale. | No | Recreate drag session with valid payload. |
| `drag-drop.commit-failed` | Drop transaction failed during apply. | Conditional | Surface reason and allow retry/cancel. |

## 7. Conformance

An implementation is conformant only if Sections 2-6 are enforced.
