/*
 * Runtime debugger transport smoke test.
 *
 * Verifies debugger snapshot and restart updates flow through runtime bridge handlers.
 */

import assert from "node:assert/strict";

import { createState, addTask, applyRuntimeMessage } from "../../../web-ui/src/index.mjs";

let state = createState();
state = addTask(state, { id: "task-1", title: "Task" });

state = applyRuntimeMessage(
  state,
  {
    version: 1,
    kind: "debugger.snapshot",
    jobId: "job-debugger",
    streamId: "debugger",
    requestId: null,
    seq: 1,
    ts: 1000,
    payload: {
      errorId: "err-smoke",
      taskId: "task-1",
      condition: {
        id: "err-smoke",
        kind: "error",
        message: "Boom",
        summary: "Boom summary",
        sections: [{ id: "sec-1", title: "What happened", text: "Smoke test condition." }]
      },
      restarts: [{ id: "rst-smoke", title: "Retry", safety: "safe", argSchema: [] }]
    },
    error: null
  },
  { openDebuggerOnDebuggerSnapshot: true }
).state;

const error = state.errors.find((entry) => entry.id === "err-smoke");
assert.ok(error, "runtime debugger snapshot upserts error");

state = applyRuntimeMessage(state, {
  version: 1,
  kind: "debugger.restart",
  jobId: "job-debugger",
  streamId: "debugger",
  requestId: null,
  seq: 2,
  ts: 1001,
  payload: {
    type: "invoked",
    errorId: "err-smoke",
    restartId: "rst-smoke",
    summary: "Retry requested"
  },
  error: null
}).state;

const updated = state.errors.find((entry) => entry.id === "err-smoke");
assert.equal(updated.debuggerTarget.lastInvokedRestartId, "rst-smoke", "restart invocation metadata applied");

console.log("PASS: runtime debugger smoke");
