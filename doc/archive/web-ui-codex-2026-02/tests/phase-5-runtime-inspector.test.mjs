import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  openInspectorWindow,
  applyRuntimeMessage
} from "../src/index.mjs";

function buildSnapshotMessage() {
  return {
    version: 1,
    kind: "inspector.update",
    jobId: "job-inspector",
    streamId: "inspector",
    requestId: "req-insp-1",
    seq: 31,
    ts: 3031,
    payload: {
      type: "snapshot",
      taskId: "task-1",
      targetId: "pres-9",
      targetType: "clos-object",
      stale: false,
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
                presentationId: "pres-slot-x",
                place: { placeId: "pl-slot-x", description: "Slot X", editable: true }
              }
            ]
          }
        ]
      },
      watches: [
        {
          id: "watch-1",
          presentationId: "pres-9",
          label: "Result",
          valueSummary: "#<FOO 3>",
          updatedAt: 3031
        }
      ]
    },
    error: null
  };
}

test("runtime bridge ingests inspector snapshot and refreshes inspector window", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = openInspectorWindow(state, { taskId: "task-1" });
  const inspectorWindow = Object.values(state.windows).find((window) => window.metadata?.role === "inspector");
  assert.ok(inspectorWindow, "inspector window exists");

  const applied = applyRuntimeMessage(state, buildSnapshotMessage());
  assert.equal(applied.handled, true);
  assert.deepEqual(applied.errors, []);

  state = applied.state;
  assert.equal(state.runtimeInspector.targetId, "pres-9");
  assert.equal(state.runtimeInspector.targetType, "clos-object");
  assert.equal(state.runtimeInspector.view.type, "clos-object");
  assert.equal(state.watches.length, 1);
  assert.equal(state.watches[0].id, "watch-1");
  assert.equal(state.watches[0].presentationId, "pres-9");

  const runtimeInspectorListId = inspectorWindow.metadata.widgets.sections.runtimeInspector.listId;
  const items = state.widgets[runtimeInspectorListId].props.items;
  assert.ok(items.some((item) => item.label.includes("pres-9")));
  assert.ok(items.some((item) => item.label.includes("Slot")));
});

test("runtime bridge ingests inspector watch sync updates", () => {
  let state = createState({ watches: [{ id: "watch-1", label: "Old", valueSummary: "1", pinned: true }] });
  state = addTask(state, { id: "task-1", title: "Task" });

  const applied = applyRuntimeMessage(state, {
    version: 1,
    kind: "inspector.update",
    jobId: "job-inspector",
    streamId: "inspector",
    requestId: null,
    seq: 32,
    ts: 3032,
    payload: {
      type: "watch.sync",
      taskId: "task-1",
      watches: [
        { id: "watch-1", label: "Old", valueSummary: "2", pinned: true, updatedAt: 3032 },
        { id: "watch-2", label: "New", valueSummary: "42", pinned: true, updatedAt: 3032 }
      ]
    },
    error: null
  });
  assert.equal(applied.handled, true);
  assert.equal(applied.errors.length, 0);
  state = applied.state;
  assert.equal(state.watches.length, 2);
  assert.equal(state.watches.find((watch) => watch.id === "watch-1")?.valueSummary, "2");
  assert.equal(state.watches.find((watch) => watch.id === "watch-2")?.valueSummary, "42");
});
