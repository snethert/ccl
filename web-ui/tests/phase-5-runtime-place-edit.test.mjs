import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  openInspectorWindow,
  applyRuntimeMessage
} from "../src/index.mjs";

function editGroupMessage(status, seq = 40, ts = 4040) {
  return {
    version: 1,
    kind: "inspector.update",
    jobId: "job-edit",
    streamId: "inspector",
    requestId: null,
    seq,
    ts,
    payload: {
      type: "edit-group",
      taskId: "task-1",
      editGroup: {
        id: "edit-1",
        label: "Set slot X",
        status,
        edits: [{ placeId: "pl-slot-x", before: "3", after: "4" }],
        updatedAt: ts
      },
      audit: { entryText: `${status} edit-1` }
    },
    error: null
  };
}

test("runtime bridge applies staged/applied/undone place-edit lifecycle", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = openInspectorWindow(state, { taskId: "task-1" });

  let applied = applyRuntimeMessage(state, editGroupMessage("staged", 40, 4040));
  assert.equal(applied.handled, true);
  state = applied.state;
  assert.equal(state.editGroups.length, 1);
  assert.equal(state.editGroups[0].status, "staged");

  applied = applyRuntimeMessage(state, editGroupMessage("applied", 41, 4041));
  state = applied.state;
  assert.equal(state.editGroups.length, 1);
  assert.equal(state.editGroups[0].status, "applied");
  assert.equal(state.editGroups[0].appliedAt, 4041);

  applied = applyRuntimeMessage(state, editGroupMessage("undone", 42, 4042));
  state = applied.state;
  assert.equal(state.editGroups.length, 1);
  assert.equal(state.editGroups[0].status, "undone");
  assert.equal(state.editGroups[0].undoneAt, 4042);
});

test("runtime bridge accepts failed place-edit updates and records audit events", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });

  const applied = applyRuntimeMessage(state, {
    version: 1,
    kind: "inspector.update",
    jobId: "job-edit",
    streamId: "inspector",
    requestId: null,
    seq: 43,
    ts: 4043,
    payload: {
      type: "edit-group",
      taskId: "task-1",
      editGroup: {
        id: "edit-404",
        label: "Apply missing place",
        status: "failed",
        edits: [],
        updatedAt: 4043,
        error: "Unknown place"
      },
      audit: { entryText: "failed edit-404" }
    },
    error: null
  });
  assert.equal(applied.handled, true);
  state = applied.state;
  assert.equal(state.editGroups.length, 1);
  assert.equal(state.editGroups[0].status, "failed");
  assert.equal(state.editGroups[0].failedAt, 4043);
  const events = state.eventLog?.entries ?? [];
  assert.ok(events.some((entry) => entry.type === "runtime:inspector.audit"));
});
