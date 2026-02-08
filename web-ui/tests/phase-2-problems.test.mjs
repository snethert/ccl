import { test } from "node:test";
import assert from "node:assert/strict";

import { createRegistry } from "../src/commands.mjs";
import {
  createState,
  addTask,
  raiseError,
  openProblemsWindow,
  registerListSelectionCommands,
  registerProblemsCommands
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

test("phase-2 problems show severity/status and open debugger via action bar", () => {
  const registry = createRegistry();
  registerListSelectionCommands(registry);
  registerProblemsCommands(registry);

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = raiseError(state, {
    taskId: "task-1",
    message: "Bad thing",
    kind: "warning",
    severity: "warning",
    status: "open"
  });

  state = openProblemsWindow(state, { taskId: "task-1" });
  const problemsWindow = Object.values(state.windows).find((win) => win.metadata?.role === "problems");
  assert.ok(problemsWindow, "problems window exists");
  const listId = problemsWindow.metadata.widgets.listId;
  const item = state.widgets[listId].props.items[0];

  assert.equal(item.severity, "warning");
  assert.equal(item.status, "new");
  assert.ok(item.label.includes("warning"));
  assert.ok(item.label.includes("Bad thing"));

  let currentState = state;
  const options = {
    registry,
    onCommandResult: ({ result }) => {
      const value = result?.result ?? null;
      if (isStateLike(value)) {
        currentState = value;
      } else if (value && isStateLike(value.state)) {
        currentState = value.state;
      }
    }
  };

  let tree = renderWindow(currentState, problemsWindow.id, options);
  const row = findByDataAttr(tree, "data-item-id", item.id);
  assert.ok(row, "problem row exists");
  row.props.onClick({ type: "click", ctrlKey: true });

  tree = renderWindow(currentState, problemsWindow.id, options);
  const action = findByDataAttr(tree, "data-action-id", "open-debugger");
  assert.ok(action, "open debugger action exists");
  action.props.onClick({ type: "click" });

  const debuggerWindow = Object.values(currentState.windows).find((win) => win.metadata?.role === "debugger");
  assert.ok(debuggerWindow, "debugger window opened");
});
