import { test } from "node:test";
import assert from "node:assert/strict";

import { createRegistry } from "../src/commands.mjs";
import {
  createState,
  addTask,
  raiseError,
  openDebuggerWindow,
  registerListSelectionCommands,
  registerDebuggerCommands,
  DEBUGGER_RESTART_INVOKE_COMMAND
} from "../src/state.mjs";
import { renderWindow } from "../src/widgets.mjs";

function findByDataAttr(node, attr, value) {
  if (!node || node.kind !== "element") return null;
  if (node.props?.[attr] === value) return node;
  for (const child of node.children ?? []) {
    const found = findByDataAttr(child, attr, value);
    if (found) return found;
  }
  return null;
}

function isStateLike(value) {
  return (
    value &&
    typeof value === "object" &&
    Object.prototype.hasOwnProperty.call(value, "workspace") &&
    Object.prototype.hasOwnProperty.call(value, "tasks") &&
    Object.prototype.hasOwnProperty.call(value, "windows")
  );
}

test("phase-2 debugger exposes restart metadata and dispatches runtime output", () => {
  const registry = createRegistry();
  registerListSelectionCommands(registry);
  registerDebuggerCommands(registry);

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = raiseError(state, {
    taskId: "task-1",
    message: "Boom",
    kind: "error",
    restarts: [
      {
        id: "rst-1",
        title: "Retry",
        description: "Try the operation again.",
        safety: "safe",
        argSchema: [{ name: "value", type: "number", required: true }],
        recommended: true,
        recommendedReason: "Auto"
      }
    ]
  });

  state = openDebuggerWindow(state, { taskId: "task-1" });
  const debuggerWindow = Object.values(state.windows).find((win) => win.metadata?.role === "debugger");
  assert.ok(debuggerWindow, "debugger window exists");
  const listId = debuggerWindow.metadata.widgets.restartsId;
  const item = state.widgets[listId].props.items[0];
  assert.equal(item.presentationType, "restart");
  assert.equal(item.restart.safety, "safe");
  assert.equal(item.restart.recommended, true);
  assert.equal(item.argSchema.length, 1);
  assert.ok(item.label.includes("recommended"));

  let runtimeOutput = null;
  let currentState = state;
  const options = {
    registry,
    commandEffectHandlers: {
      runtimeDispatch: ({ output }) => {
        runtimeOutput = output;
      }
    },
    onCommandResult: ({ result }) => {
      const value = result?.result ?? null;
      if (isStateLike(value)) {
        currentState = value;
      } else if (value && isStateLike(value.state)) {
        currentState = value.state;
      }
    }
  };

  const tree = renderWindow(currentState, debuggerWindow.id, options);
  const row = findByDataAttr(tree, "data-item-id", item.id);
  assert.ok(row, "restart row exists");
  row.props.onClick({ type: "click" });

  assert.ok(runtimeOutput, "runtime output dispatched");
  assert.equal(runtimeOutput.kind, "restart.invoke");
  assert.equal(runtimeOutput.restartId, "rst-1");
  assert.equal(currentState.commandHistory.length, 1);
  assert.equal(currentState.commandHistory[0].commandId, DEBUGGER_RESTART_INVOKE_COMMAND);
});
