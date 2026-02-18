import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createRegistry,
  registerCommand,
  executeCommand,
  createState,
  addTask,
  setBeginnerMode,
  dismissGuidance,
  openCommandPaletteWindow,
  refreshCommandPaletteWindow
} from "../src/index.mjs";

function findPaletteWindow(state) {
  return Object.values(state.windows).find((window) => window.metadata?.role === "command-palette");
}

test("phase-6 beginner mode hides advanced commands in command palette", () => {
  const registry = createRegistry();
  registerCommand(registry, { id: "basic.run", title: "Basic Run", exec: () => "ok" });
  registerCommand(registry, {
    id: "advanced.run",
    title: "Advanced Run",
    metadata: { beginner: { hidden: true, advanced: true } },
    exec: () => "advanced"
  });

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = setBeginnerMode(state, true);
  state = openCommandPaletteWindow(state, { registry, taskId: "task-1" });

  const palette = findPaletteWindow(state);
  assert.ok(palette);
  const items = state.widgets[palette.metadata.widgets.listId].props.items;
  const commandIds = items.map((item) => item.targetCommandId).filter(Boolean);
  assert.equal(commandIds.includes("basic.run"), true);
  assert.equal(commandIds.includes("advanced.run"), false);
});

test("phase-6 beginner mode can require confirmation for advanced commands", () => {
  const registry = createRegistry();
  registerCommand(registry, {
    id: "danger.run",
    metadata: { beginner: { advanced: true, confirm: true } },
    exec: () => "ran"
  });

  const state = setBeginnerMode(createState(), true);
  const blocked = executeCommand(registry, "danger.run", { state });
  assert.equal(blocked.ok, false);
  assert.equal(blocked.reason, "Confirmation required");

  const confirmed = executeCommand(registry, "danger.run", { state, confirmBeginner: true });
  assert.equal(confirmed.ok, true);
  assert.equal(confirmed.result, "ran");
});

test("phase-6 guidance dismissal suppresses command preview explanation", () => {
  const registry = createRegistry();
  registerCommand(registry, {
    id: "learn.inspect",
    title: "Inspect Value",
    metadata: {
      beginner: {
        explanation: "Inspect shows structure and does not evaluate."
      }
    },
    exec: () => "ok"
  });

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = setBeginnerMode(state, true);
  state = openCommandPaletteWindow(state, { registry, taskId: "task-1", filter: "learn.inspect" });
  let palette = findPaletteWindow(state);
  assert.ok(palette);

  const previewBefore = state.widgets[palette.metadata.widgets.previewId].props.text;
  assert.ok(previewBefore.includes("Inspect shows structure and does not evaluate."));

  state = dismissGuidance(state, "command:learn.inspect");
  state = refreshCommandPaletteWindow(state, palette.id, {
    registry,
    filter: "learn.inspect"
  });
  palette = findPaletteWindow(state);

  const previewAfter = state.widgets[palette.metadata.widgets.previewId].props.text;
  assert.equal(previewAfter.includes("Inspect shows structure and does not evaluate."), false);
});
