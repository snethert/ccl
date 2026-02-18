import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  addWindow,
  addWidget,
  updateListSelection,
  registerListSelectionCommands,
  LIST_SELECTION_UPDATE_COMMAND
} from "../src/state.mjs";
import { createRegistry, executeCommand } from "../src/commands.mjs";

function createListState() {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWidget(state, { id: "root", kind: "container", windowId: "win-1" });
  state = addWidget(state, {
    id: "list-1",
    kind: "list",
    parentId: "root",
    props: {
      items: [
        { id: "alpha", label: "Alpha" },
        { id: "beta", label: "Beta" },
        { id: "gamma", label: "Gamma" },
        { id: "delta", label: "Delta" }
      ]
    }
  });
  return state;
}

test("updateListSelection supports replace/toggle/range for multi-select lists", () => {
  let state = createListState();

  state = updateListSelection(state, {
    listId: "list-1",
    itemId: "alpha",
    mode: "replace",
    multiple: true
  });
  assert.deepEqual(state.selection.targetIds, ["alpha"]);

  state = updateListSelection(state, {
    listId: "list-1",
    itemId: "gamma",
    mode: "toggle",
    multiple: true
  });
  assert.deepEqual(state.selection.targetIds, ["alpha", "gamma"]);

  state = updateListSelection(state, {
    listId: "list-1",
    itemId: "delta",
    mode: "range",
    multiple: true
  });
  assert.deepEqual(state.selection.targetIds, ["gamma", "delta"]);
  assert.equal(state.selection.metadata.listId, "list-1");
});

test("registerListSelectionCommands wires ui.list.selection.update", () => {
  const registry = createRegistry();
  registerListSelectionCommands(registry);

  let state = createListState();
  let result = executeCommand(registry, LIST_SELECTION_UPDATE_COMMAND, {
    state,
    listId: "list-1",
    itemId: "beta",
    selectionMode: "replace",
    multiple: true
  });
  assert.equal(result.ok, true);
  state = result.result;
  assert.deepEqual(state.selection.targetIds, ["beta"]);

  result = executeCommand(registry, LIST_SELECTION_UPDATE_COMMAND, {
    state,
    listId: "list-1",
    itemId: "delta",
    selectionMode: "toggle",
    multiple: true
  });
  assert.equal(result.ok, true);
  state = result.result;
  assert.deepEqual(state.selection.targetIds, ["beta", "delta"]);
});

test("updateListSelection ignores non-selectable targets outside listItemIds", () => {
  let state = createListState();
  state = updateListSelection(state, {
    listId: "list-1",
    itemId: "header-row",
    mode: "replace",
    multiple: true,
    listItemIds: ["alpha", "beta", "gamma", "delta"]
  });
  assert.equal(state.selection, null);
});
