import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  addTask,
  createSession,
  renameSession,
  saveSession,
  openSession,
  deleteSession,
  openSessionListWindow,
  registerSessionCommands,
  SESSION_CREATE_COMMAND,
  SESSION_OPEN_COMMAND,
  SESSION_SAVE_COMMAND,
  SESSION_RENAME_COMMAND,
  SESSION_DELETE_COMMAND
} from "../src/state.mjs";
import { createRegistry, executeCommand } from "../src/commands.mjs";
import { extractCommandOutput } from "../src/command-effects.mjs";

test("phase-4 sessions support create, rename, save, open, delete", () => {
  let state = createState();
  state = createSession(state, { name: "Alpha", now: 10 });
  assert.equal(state.activeSessionId != null, true);
  const sessionId = state.activeSessionId;
  assert.equal(state.sessions[sessionId].name, "Alpha");

  state = renameSession(state, sessionId, "Beta");
  assert.equal(state.sessions[sessionId].name, "Beta");

  state = saveSession(state, sessionId, { now: 20 });
  assert.equal(state.sessions[sessionId].lastSavedAt, 20);

  state = openSession(state, sessionId, { now: 30 });
  assert.equal(state.sessions[sessionId].lastOpenedAt, 30);

  state = deleteSession(state, sessionId);
  assert.equal(state.sessions[sessionId], undefined);
});

test("phase-4 session list window surfaces sessions", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = createSession(state, { name: "Alpha", now: 1 });
  state = createSession(state, { name: "Beta", now: 2 });

  state = openSessionListWindow(state, { taskId: "task-1" });
  const window = Object.values(state.windows).find((win) => win.metadata?.role === "session-list");
  const listId = window.metadata.widgets.listId;
  const items = state.widgets[listId].props.items;
  assert.ok(items.some((item) => item.label.includes("Alpha")));
  assert.ok(items.some((item) => item.label.includes("Beta")));
});

test("phase-4 session commands emit runtime outputs", () => {
  const registry = createRegistry();
  registerSessionCommands(registry);

  let state = createState();
  const created = executeCommand(registry, SESSION_CREATE_COMMAND, { state, name: "Alpha" });
  assert.equal(created.ok, true);
  state = created.result?.state ?? created.result ?? state;
  const createdOutput = extractCommandOutput(created);
  assert.equal(createdOutput.kind, "session.save");

  const sessionId = state.activeSessionId;
  const opened = executeCommand(registry, SESSION_OPEN_COMMAND, { state, sessionId });
  const openedOutput = extractCommandOutput(opened);
  assert.equal(openedOutput.kind, "session.open");

  const saved = executeCommand(registry, SESSION_SAVE_COMMAND, { state, sessionId });
  const savedOutput = extractCommandOutput(saved);
  assert.equal(savedOutput.kind, "session.save");

  const renamed = executeCommand(registry, SESSION_RENAME_COMMAND, { state, sessionId, name: "Beta" });
  const renamedOutput = extractCommandOutput(renamed);
  assert.equal(renamedOutput.kind, "session.rename");

  const deleted = executeCommand(registry, SESSION_DELETE_COMMAND, { state, sessionId });
  const deletedOutput = extractCommandOutput(deleted);
  assert.equal(deletedOutput.kind, "session.delete");
});
