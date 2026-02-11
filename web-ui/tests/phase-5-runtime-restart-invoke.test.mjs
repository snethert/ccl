import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  raiseError,
  openDebuggerWindow,
  createRegistry,
  registerDebuggerCommands,
  executeCommand,
  createRuntimeCommandClient,
  applyRuntimeMessage,
  DEBUGGER_RESTART_INVOKE_COMMAND
} from "../src/index.mjs";
import { createSabRing, SAB_RING_TRANSPORT } from "../../doc/wasm/js/sab-ring.mjs";

test("debugger restart command dispatches to runtime command client and settles history", async () => {
  const registry = createRegistry();
  registerDebuggerCommands(registry);

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = raiseError(state, {
    taskId: "task-1",
    message: "Boom",
    kind: "error",
    restarts: [{ id: "rst-1", title: "Retry", safety: "safe", argSchema: [] }]
  });
  state = openDebuggerWindow(state, { taskId: "task-1" });
  const debuggerWindow = Object.values(state.windows).find((window) => window.metadata?.role === "debugger");
  const item = state.widgets[debuggerWindow.metadata.widgets.restartsId].props.items[0];

  const ring = createSabRing({ capacity: 8192 });
  const client = createRuntimeCommandClient({
    now: () => 5000,
    timeoutMs: 5000,
    commandTransport: {
      transport: SAB_RING_TRANSPORT,
      ring
    }
  });

  const execResult = executeCommand(registry, DEBUGGER_RESTART_INVOKE_COMMAND, {
    state,
    item,
    source: "debugger",
    runtimeCommandClient: client,
    runtimeContext: { package: "CL-USER" }
  });

  assert.equal(execResult.ok, true);
  assert.equal(execResult.pending, true);
  assert.equal(execResult.runtimeDispatched, true);
  assert.equal(typeof execResult.requestId, "string");

  state = execResult.result?.state ?? execResult.result ?? state;
  assert.equal(state.commandHistory.length, 1);
  const invocation = state.commandHistory[0];
  assert.equal(invocation.commandId, DEBUGGER_RESTART_INVOKE_COMMAND);
  assert.equal(invocation.result?.status, "pending");

  const runtimeResult = {
    version: 1,
    kind: "command.result",
    jobId: "job-debugger",
    streamId: "commands",
    requestId: execResult.requestId,
    seq: 2,
    ts: 5004,
    payload: {
      invocationId: invocation.id,
      commandId: "runtime.restart.invoke",
      result: {
        restartOutcome: {
          errorId: item.errorId,
          restartId: item.restartId,
          status: "requested",
          summary: "Restart request accepted"
        }
      },
      diagnostics: [],
      durationMs: 4
    },
    error: null
  };

  const applied = applyRuntimeMessage(state, runtimeResult, { commandClient: client });
  assert.equal(applied.handled, true);
  const updated = applied.state.commandHistory.find((entry) => entry.id === invocation.id);
  assert.ok(updated, "invocation remains in history");
  assert.equal(updated.commandId, DEBUGGER_RESTART_INVOKE_COMMAND);
  assert.equal(updated.result.status, "succeeded");
  assert.equal(updated.result.value.restartOutcome.restartId, "rst-1");

  const settled = await execResult.promise;
  assert.equal(settled.ok, true);
  assert.equal(settled.commandId, "runtime.restart.invoke");
  assert.equal(settled.clientCommandId, DEBUGGER_RESTART_INVOKE_COMMAND);
});
