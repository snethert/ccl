# Phase 0 Spec: Presentation Taxonomy (v0)

## Version
Schema version: `0`

## Purpose
Define the set of presentation types and metadata so the UI can attach actions to structured values early.

## Goals
- Presentations are typed and actionable.
- Default actions are predictable and discoverable.
- Presentations connect REPL output, Inspector, and command system.

## Non-Goals
- Full object serialization of runtime values.
- UI layout or styling decisions.

## Base Presentation Schema
```json
{
  "id": "pres-0001",
  "type": "value",
  "objectId": "obj-123",
  "entryId": "ent-001",
  "widgetId": "widget-42",
  "label": "#<HASH-TABLE 3/6>",
  "bounds": null,
  "metadata": {},
  "actions": []
}
```

### Fields
- `id`: stable presentation id.
- `type`: one of the defined types below.
- `objectId`: runtime object identity (may become stale).
- `entryId`: recording entry that emitted this presentation.
- `label`: human-readable summary.
- `actions`: optional explicit actions (command + args).

## Core Types and Required Metadata

### value
Generic value presentation.
- Required metadata: `summary`.
- Default actions: inspect, describe.

### symbol
A Lisp symbol.
- Required metadata: `name`, `package`.
- Default actions: go-to-definition, find-references, describe, inspect.

### definition
A definition target.
- Required metadata: `name`, `kind` (function, macro, class, generic), `location`.
- Default actions: open-source, describe.

### command
A command object.
- Required metadata: `commandId`, `args` (structured), `title`.
- Default actions: do-again, do-again-with-args.

### frame
A stack frame.
- Required metadata: `frameId`, `function`, `location`, `locals` (list of bindings).
- Default actions: inspect-frame, jump-to-source.

### binding
A local or special binding.
- Required metadata: `name`, `valueId`, `scope`.
- Default actions: inspect, watch.

### place
A setf-able place.
- Required metadata: `placeId`, `description`, `setter`, `valueId`, `editable`.
- Default actions: edit, inspect.

### condition-section
A section of an error/condition report.
- Required metadata: `errorId`, `sectionKey`, `text`.
- Default actions: explain, open-doc.

### restart
A restart option.
- Required metadata: `restartId`, `title`, `safety`, `argSchema`.
- Default actions: invoke-restart.

### doc
Documentation node.
- Required metadata: `subject`, `docKind`, `links`.
- Default actions: open-doc, inspect-subject.

### location
A source location.
- Required metadata: `file`, `line`, `column`.
- Default actions: open-source.

## Gesture Mapping
Presentation gestures are mapped to commands via translators:
- `type + gesture -> commandId`
- Gesture examples: `click`, `hover`, `context`, `open`.

This is implemented via the presentation translator registry.

## Selection Model
Selections may reference one or many presentation ids:
```json
{
  "id": "sel-1",
  "kind": "presentation",
  "targetIds": ["pres-0001", "pres-0002"],
  "anchorId": "pres-0001"
}
```

## Invariants
- Presentations must be stable across re-render for a given recording.
- Presentation metadata must be sufficient to provide at least one meaningful action.

## Phase 0 Decisions
- No additional package/file/module presentation types in v0; represent these through `symbol`, `definition`, and `location` metadata.
- Restarts remain a distinct top-level `restart` presentation and are referenced from condition reports.
