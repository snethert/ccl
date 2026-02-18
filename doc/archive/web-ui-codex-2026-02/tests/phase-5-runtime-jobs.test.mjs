import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  openInspectorWindow,
  applyRuntimeMessage
} from "../src/index.mjs";

test("runtime bridge ingests job.update lifecycle events", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = openInspectorWindow(state, { taskId: "task-1" });
  const inspectorWindow = Object.values(state.windows).find((window) => window.metadata?.role === "inspector");

  const applyJob = (payload, seq, ts) =>
    applyRuntimeMessage(state, {
      version: 1,
      kind: "job.update",
      jobId: "job-77",
      streamId: "jobs",
      requestId: null,
      seq,
      ts,
      payload,
      error: null
    });

  let applied = applyJob(
    {
      id: "job-77",
      taskId: "task-1",
      kind: "compile",
      label: "Compile project",
      status: "queued",
      progress: { current: 0, total: 3 }
    },
    11,
    7011
  );
  assert.equal(applied.handled, true);
  state = applied.state;
  assert.equal(state.jobs.length, 1);
  assert.equal(state.jobs[0].status, "queued");

  applied = applyJob(
    {
      id: "job-77",
      taskId: "task-1",
      kind: "compile",
      label: "Compile project",
      status: "progress",
      progress: { current: 2, total: 3 }
    },
    12,
    7012
  );
  state = applied.state;
  assert.equal(state.jobs[0].status, "progress");
  assert.equal(state.jobs[0].progress.current, 2);

  applied = applyJob(
    {
      id: "job-77",
      taskId: "task-1",
      kind: "compile",
      label: "Compile project",
      status: "completed",
      progress: { current: 3, total: 3 }
    },
    13,
    7013
  );
  state = applied.state;
  assert.equal(state.jobs[0].status, "completed");
  assert.equal(state.jobs[0].progress.total, 3);

  const jobsListId = inspectorWindow.metadata.widgets.sections.jobs.listId;
  const jobItems = state.widgets[jobsListId].props.items;
  assert.ok(jobItems.some((item) => item.label.includes("Compile project")));
  assert.ok(jobItems.some((item) => item.label.includes("3/3")));
});
