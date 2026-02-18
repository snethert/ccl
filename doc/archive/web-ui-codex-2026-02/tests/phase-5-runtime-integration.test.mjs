import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  openInspectorWindow,
  applyRuntimeMessage
} from "../src/index.mjs";

test("phase-5 integration: evaluate -> inspector snapshot -> place edit -> re-evaluate", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = openInspectorWindow(state, { taskId: "task-1" });

  let applied = applyRuntimeMessage(state, {
    version: 1,
    kind: "runtime.output",
    jobId: "job-1",
    streamId: "repl",
    requestId: null,
    seq: 100,
    ts: 8100,
    payload: {
      recording: { id: "rec-1", jobId: "job-1", streamId: "repl" },
      entry: {
        id: "ent-1",
        recordingId: "rec-1",
        kind: "text",
        streamId: "stdout",
        seq: 100,
        ts: 8100,
        text: "#<FOO 3>",
        presentationId: "pres-foo"
      },
      anchor: { id: "anc-1", entryId: "ent-1", range: { start: 0, end: 8 }, path: [] }
    },
    error: null
  });
  state = applied.state;
  assert.ok(state.recordingStore.recordings["rec-1"]);
  assert.ok(state.recordingStore.entries["ent-1"]);

  applied = applyRuntimeMessage(state, {
    version: 1,
    kind: "inspector.update",
    jobId: "job-1",
    streamId: "inspector",
    requestId: null,
    seq: 101,
    ts: 8101,
    payload: {
      type: "snapshot",
      taskId: "task-1",
      targetId: "pres-foo",
      targetType: "clos-object",
      view: {
        type: "clos-object",
        summary: "#<FOO 3>",
        sections: [
          {
            id: "slots",
            title: "Slots",
            rows: [
              {
                id: "slot-x",
                label: "X",
                valueSummary: "3",
                place: { placeId: "pl-slot-x", description: "Slot X", editable: true }
              }
            ]
          }
        ]
      }
    },
    error: null
  });
  state = applied.state;
  assert.equal(state.runtimeInspector.targetId, "pres-foo");

  applied = applyRuntimeMessage(state, {
    version: 1,
    kind: "inspector.update",
    jobId: "job-1",
    streamId: "inspector",
    requestId: null,
    seq: 102,
    ts: 8102,
    payload: {
      type: "edit-group",
      taskId: "task-1",
      editGroup: {
        id: "edit-1",
        label: "Set slot X",
        status: "staged",
        edits: [{ placeId: "pl-slot-x", before: "3", after: "4" }]
      }
    },
    error: null
  });
  state = applied.state;
  assert.equal(state.editGroups[0].status, "staged");

  applied = applyRuntimeMessage(state, {
    version: 1,
    kind: "inspector.update",
    jobId: "job-1",
    streamId: "inspector",
    requestId: null,
    seq: 103,
    ts: 8103,
    payload: {
      type: "edit-group",
      taskId: "task-1",
      editGroup: {
        id: "edit-1",
        label: "Set slot X",
        status: "applied",
        edits: [{ placeId: "pl-slot-x", before: "3", after: "4" }]
      }
    },
    error: null
  });
  state = applied.state;
  assert.equal(state.editGroups[0].status, "applied");

  applied = applyRuntimeMessage(state, {
    version: 1,
    kind: "runtime.output",
    jobId: "job-2",
    streamId: "repl",
    requestId: null,
    seq: 110,
    ts: 8110,
    payload: {
      recording: { id: "rec-2", jobId: "job-2", streamId: "repl" },
      entry: {
        id: "ent-2",
        recordingId: "rec-2",
        kind: "text",
        streamId: "stdout",
        seq: 110,
        ts: 8110,
        text: "#<FOO 4>",
        presentationId: "pres-foo"
      },
      anchor: { id: "anc-2", entryId: "ent-2", range: { start: 0, end: 8 }, path: [] }
    },
    error: null
  });
  state = applied.state;
  assert.ok(state.recordingStore.recordings["rec-2"]);
  assert.ok(state.recordingStore.entries["ent-2"]);
  assert.equal(state.editGroups[0].status, "applied");
  assert.equal(state.runtimeInspector.targetId, "pres-foo");
});
