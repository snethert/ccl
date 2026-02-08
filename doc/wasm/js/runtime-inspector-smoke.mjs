/*
 * Runtime inspector transport smoke test.
 *
 * Verifies inspector snapshot, watch sync, and edit-group updates flow through
 * the runtime bridge.
 */

import assert from "node:assert/strict";

import { createState, addTask, openInspectorWindow, applyRuntimeMessage } from "../../../web-ui/src/index.mjs";

let state = createState();
state = addTask(state, { id: "task-1", title: "Task" });
state = openInspectorWindow(state, { taskId: "task-1" });

state = applyRuntimeMessage(state, {
  version: 1,
  kind: "inspector.update",
  jobId: "job-inspector",
  streamId: "inspector",
  requestId: null,
  seq: 1,
  ts: 1100,
  payload: {
    type: "snapshot",
    taskId: "task-1",
    targetId: "pres-smoke",
    targetType: "value",
    view: {
      type: "value",
      summary: "42",
      sections: [
        {
          id: "value",
          title: "Value",
          rows: [{ id: "row-1", label: "Value", valueSummary: "42", place: { placeId: "pl-smoke", editable: true } }]
        }
      ]
    }
  },
  error: null
}).state;

assert.equal(state.runtimeInspector.targetId, "pres-smoke", "inspector snapshot target set");

state = applyRuntimeMessage(state, {
  version: 1,
  kind: "inspector.update",
  jobId: "job-inspector",
  streamId: "inspector",
  requestId: null,
  seq: 2,
  ts: 1101,
  payload: {
    type: "watch.sync",
    taskId: "task-1",
    watches: [{ id: "watch-smoke", presentationId: "pres-smoke", label: "Smoke Watch", valueSummary: "42", pinned: true }]
  },
  error: null
}).state;

assert.equal(state.watches.length, 1, "watch sync applied");

state = applyRuntimeMessage(state, {
  version: 1,
  kind: "inspector.update",
  jobId: "job-inspector",
  streamId: "inspector",
  requestId: null,
  seq: 3,
  ts: 1102,
  payload: {
    type: "edit-group",
    taskId: "task-1",
    editGroup: {
      id: "edit-smoke",
      label: "Smoke Edit",
      status: "applied",
      edits: [{ placeId: "pl-smoke", before: "41", after: "42" }]
    },
    audit: { entryText: "applied edit-smoke" }
  },
  error: null
}).state;

assert.equal(state.editGroups[0].status, "applied", "edit group update applied");

console.log("PASS: runtime inspector smoke");
