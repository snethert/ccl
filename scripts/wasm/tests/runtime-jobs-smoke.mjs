/*
 * Runtime jobs transport smoke test.
 *
 * Verifies job lifecycle updates are consumed by the runtime bridge.
 */

import assert from "node:assert/strict";

import { createState, addTask, applyRuntimeMessage } from "../../../web-ui/src/index.mjs";

let state = createState();
state = addTask(state, { id: "task-1", title: "Task" });

const applyJob = (payload, seq, ts) =>
  applyRuntimeMessage(state, {
    version: 1,
    kind: "job.update",
    jobId: "job-smoke",
    streamId: "jobs",
    requestId: null,
    seq,
    ts,
    payload,
    error: null
  }).state;

state = applyJob(
  {
    id: "job-smoke",
    taskId: "task-1",
    kind: "compile",
    label: "Compile Smoke",
    status: "queued",
    progress: { current: 0, total: 2 }
  },
  1,
  1200
);
state = applyJob(
  {
    id: "job-smoke",
    taskId: "task-1",
    kind: "compile",
    label: "Compile Smoke",
    status: "completed",
    progress: { current: 2, total: 2 }
  },
  2,
  1201
);

assert.equal(state.jobs.length, 1, "job upserted");
assert.equal(state.jobs[0].status, "completed", "job completed status applied");
assert.equal(state.jobs[0].progress.current, 2, "job progress applied");

console.log("PASS: runtime jobs smoke");
