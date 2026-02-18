import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  applyRuntimeMessage
} from "../src/index.mjs";

function buildSnapshotMessage() {
  return {
    version: 1,
    kind: "debugger.snapshot",
    jobId: "job-debugger",
    streamId: "debugger",
    requestId: null,
    seq: 11,
    ts: 1011,
    payload: {
      errorId: "err-77",
      taskId: "task-1",
      condition: {
        id: "err-77",
        kind: "error",
        message: "Division by zero",
        summary: "Attempted (/ 1 0)",
        sections: [{ id: "sec-1", title: "What happened", text: "Cannot divide by zero." }]
      },
      frames: [
        {
          frameId: "frm-1",
          label: "FOO",
          function: "FOO",
          location: { file: "src/foo.lisp", line: 42, column: 7 },
          locals: [{ bindingId: "bind-1", name: "X", valueSummary: "0", presentationId: "pres-bind-1" }]
        }
      ],
      restarts: [
        {
          id: "rst-1",
          title: "Use Value",
          description: "Provide a replacement denominator.",
          safety: "safe",
          argSchema: [{ name: "value", type: "number", required: true }],
          preview: { text: "Will retry with provided value." },
          recommended: true,
          recommendedReason: "Most likely successful."
        }
      ],
      selectedFrameId: "frm-1"
    },
    error: null
  };
}

test("runtime bridge ingests debugger.snapshot and opens debugger with metadata", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });

  const applied = applyRuntimeMessage(state, buildSnapshotMessage(), {
    openDebuggerOnDebuggerSnapshot: true
  });
  assert.equal(applied.handled, true);
  assert.deepEqual(applied.errors, []);

  const nextState = applied.state;
  const error = nextState.errors.find((entry) => entry.id === "err-77");
  assert.ok(error, "error is upserted");
  assert.equal(error.report.summary, "Attempted (/ 1 0)");
  assert.equal(error.stack.length, 1);
  assert.equal(error.debuggerTarget.selectedFrameId, "frm-1");
  assert.equal(error.restarts.length, 1);
  assert.equal(error.restarts[0].recommendedReason, "Most likely successful.");

  const debuggerWindow = Object.values(nextState.windows).find((window) => window.metadata?.role === "debugger");
  assert.ok(debuggerWindow, "debugger window exists");
  assert.equal(debuggerWindow.metadata.errorId, "err-77");
  const restartListId = debuggerWindow.metadata.widgets.restartsId;
  const firstItem = nextState.widgets[restartListId].props.items[0];
  assert.equal(firstItem.restartId, "rst-1");
  assert.ok(firstItem.label.includes("Most likely successful."));
  assert.ok(firstItem.label.includes("preview: Will retry with provided value."));
  assert.ok(firstItem.className.includes("has-args"));
  assert.ok(firstItem.className.includes("has-preview"));
});

test("runtime bridge applies debugger.restart set and invoked updates", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = applyRuntimeMessage(state, buildSnapshotMessage(), {
    openDebuggerOnDebuggerSnapshot: true
  }).state;

  const setMessage = {
    version: 1,
    kind: "debugger.restart",
    jobId: "job-debugger",
    streamId: "debugger",
    requestId: null,
    seq: 12,
    ts: 1012,
    payload: {
      type: "set",
      errorId: "err-77",
      restarts: [{ id: "rst-2", title: "Abort", safety: "destructive", argSchema: [] }]
    },
    error: null
  };
  const setApplied = applyRuntimeMessage(state, setMessage);
  assert.equal(setApplied.handled, true);
  state = setApplied.state;
  const errorAfterSet = state.errors.find((entry) => entry.id === "err-77");
  assert.equal(errorAfterSet.restarts.length, 1);
  assert.equal(errorAfterSet.restarts[0].id, "rst-2");

  const invokedMessage = {
    version: 1,
    kind: "debugger.restart",
    jobId: "job-debugger",
    streamId: "debugger",
    requestId: null,
    seq: 13,
    ts: 1013,
    payload: {
      type: "invoked",
      errorId: "err-77",
      restartId: "rst-2",
      summary: "Abort selected"
    },
    error: null
  };
  const invokedApplied = applyRuntimeMessage(state, invokedMessage);
  assert.equal(invokedApplied.handled, true);
  state = invokedApplied.state;
  const errorAfterInvoked = state.errors.find((entry) => entry.id === "err-77");
  assert.equal(errorAfterInvoked.debuggerTarget.lastInvokedRestartId, "rst-2");
  assert.equal(errorAfterInvoked.debuggerTarget.lastRestartSummary, "Abort selected");

  const debuggerWindow = Object.values(state.windows).find((window) => window.metadata?.role === "debugger");
  assert.ok(debuggerWindow, "debugger window persists");
  const summaryId = debuggerWindow.metadata.widgets.summaryId;
  const summaryText = state.widgets[summaryId].props.text;
  assert.ok(summaryText.includes("last restart: Abort selected"));
});
