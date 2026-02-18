import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createRegistry,
  registerCommand,
  resolveKey,
  executeCommand,
  createState,
  addTask,
  addWindow,
  createSession,
  setActiveTask,
  registerCommandPaletteCommands,
  registerCommandSurfaceCommands,
  registerTaskCommands,
  registerSessionCommands,
  bindCommandPaletteDefaults,
  bindCommandSurfaceDefaults,
  COMMAND_PALETTE_OPEN_COMMAND,
  COMMAND_PALETTE_SELECT_NEXT_COMMAND,
  COMMAND_PALETTE_EXECUTE_SELECTION_COMMAND,
  COMMAND_SURFACE_DISMISS_COMMAND,
  KEYBINDINGS_OPEN_COMMAND,
  TASK_LIST_COMMAND,
  TASK_SWITCH_COMMAND,
  SESSION_LIST_COMMAND,
  SESSION_CREATE_COMMAND,
  SESSION_OPEN_COMMAND
} from "../src/index.mjs";

function findWindowByRole(state, role) {
  return Object.values(state.windows ?? {}).find((window) => window.metadata?.role === role) ?? null;
}

function resultStateOrThrow(result) {
  assert.equal(result.ok, true);
  if (result.result && typeof result.result === "object" && result.result.state) {
    return result.result.state;
  }
  return result.result;
}

test("phase-7 keyboard/focus command surfaces remain keyboard-complete", () => {
  const registry = createRegistry();
  registerCommand(registry, { id: "alpha.run", title: "Alpha", exec: () => "alpha" });
  registerCommand(registry, { id: "beta.run", title: "Beta", exec: () => "beta" });
  registerCommandPaletteCommands(registry);
  registerCommandSurfaceCommands(registry);
  bindCommandPaletteDefaults(registry, { taskId: "task-1" });
  bindCommandSurfaceDefaults(registry);

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });

  const openPaletteKey = resolveKey(registry, "Ctrl+Shift+P", {});
  assert.equal(openPaletteKey, COMMAND_PALETTE_OPEN_COMMAND);

  state = resultStateOrThrow(executeCommand(registry, openPaletteKey, { state, taskId: "task-1" }));
  assert.ok(findWindowByRole(state, "command-palette"));

  state = resultStateOrThrow(executeCommand(registry, COMMAND_PALETTE_SELECT_NEXT_COMMAND, { state, taskId: "task-1" }));

  const executeSelected = executeCommand(registry, COMMAND_PALETTE_EXECUTE_SELECTION_COMMAND, { state, taskId: "task-1" });
  assert.equal(executeSelected.ok, true);
  assert.equal(executeSelected.result.ok, true);

  const dismissKey = resolveKey(registry, "Escape", {});
  assert.equal(dismissKey, COMMAND_SURFACE_DISMISS_COMMAND);
  state = resultStateOrThrow(executeCommand(registry, dismissKey, { state, taskId: "task-1" }));
  assert.equal(findWindowByRole(state, "command-palette"), null);

  const openKeybindingsKey = resolveKey(registry, "Ctrl+Shift+K", {});
  assert.equal(openKeybindingsKey, KEYBINDINGS_OPEN_COMMAND);
  state = resultStateOrThrow(executeCommand(registry, openKeybindingsKey, { state, taskId: "task-1" }));
  assert.ok(findWindowByRole(state, "keybindings"));

  state = resultStateOrThrow(executeCommand(registry, COMMAND_SURFACE_DISMISS_COMMAND, { state, taskId: "task-1" }));
  assert.equal(findWindowByRole(state, "keybindings"), null);
});

test("phase-7 keyboard/focus task and session command loops remain reachable", () => {
  const registry = createRegistry();
  registerTaskCommands(registry);
  registerSessionCommands(registry);

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task One" });
  state = addTask(state, { id: "task-2", title: "Task Two" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWindow(state, { id: "win-2", taskId: "task-2", kind: "document" });
  state = createSession(state, { name: "Session One", now: 1 });
  state = createSession(state, { name: "Session Two", now: 2 });

  state = resultStateOrThrow(executeCommand(registry, TASK_LIST_COMMAND, { state, taskId: "task-1" }));
  assert.ok(findWindowByRole(state, "task-list"));

  state = resultStateOrThrow(executeCommand(registry, TASK_SWITCH_COMMAND, {
    state,
    taskId: "task-1",
    itemId: "task-2"
  }));
  assert.equal(state.workspace.activeTaskId, "task-2");

  state = resultStateOrThrow(executeCommand(registry, SESSION_LIST_COMMAND, { state, taskId: "task-2" }));
  const sessionWindow = findWindowByRole(state, "session-list");
  assert.ok(sessionWindow);

  state = resultStateOrThrow(executeCommand(registry, SESSION_CREATE_COMMAND, {
    state,
    taskId: "task-2",
    name: "Session Three",
    now: 3
  }));
  assert.equal(Object.keys(state.sessions).length >= 3, true);

  const newestSessionId = state.activeSessionId;
  state = resultStateOrThrow(executeCommand(registry, SESSION_OPEN_COMMAND, {
    state,
    taskId: "task-2",
    sessionId: newestSessionId
  }));
  assert.equal(state.activeSessionId, newestSessionId);
});

test("phase-7 keyboard/focus rapid task switching keeps focus targets valid", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task One" });
  state = addTask(state, { id: "task-2", title: "Task Two" });
  state = addWindow(state, { id: "win-1", taskId: "task-1", kind: "document" });
  state = addWindow(state, { id: "win-2", taskId: "task-2", kind: "document" });

  for (let index = 0; index < 30; index += 1) {
    const targetTaskId = index % 2 === 0 ? "task-1" : "task-2";
    state = setActiveTask(state, targetTaskId, { reason: "keyboard", seq: index + 1 });
    assert.equal(state.workspace.activeTaskId, targetTaskId);
    const focusedWindow = state.focus?.windowId ?? null;
    if (focusedWindow) {
      assert.ok(state.windows[focusedWindow]);
      assert.equal(state.windows[focusedWindow].taskId, targetTaskId);
    }
  }

  assert.equal(state.focusHistory.length > 0, true);
  const lastFocus = state.focusHistory[state.focusHistory.length - 1];
  assert.equal(lastFocus.target.taskId, state.workspace.activeTaskId);
});

