import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createRegistry,
  resolveKey,
  analyzeKeybindingConflicts,
  createState,
  addTask,
  setPaneKeymapProfile,
  patchCustomization,
  applyCustomizationKeymapsToRegistry,
  openKeybindingWindow
} from "../src/index.mjs";

test("phase-6 pane profile assignment applies dispatch bindings", () => {
  const registry = createRegistry();
  let state = createState();
  state = setPaneKeymapProfile(state, "editor", "editor-emacs");

  applyCustomizationKeymapsToRegistry(state, registry);
  const resolved = resolveKey(registry, "Ctrl+Enter", { contextId: "pane:editor" });
  assert.equal(resolved, "runtime.eval.defun");
});

test("phase-6 keymap conflict diagnostics record deterministic winners", () => {
  const registry = createRegistry();
  let state = createState();
  state = patchCustomization(state, "session", {
    keymaps: {
      customBindings: [
        {
          pane: "editor",
          scope: "context",
          scopeId: "pane:editor",
          key: "Ctrl+Enter",
          commandId: "command.first"
        },
        {
          pane: "editor",
          scope: "context",
          scopeId: "pane:editor",
          key: "Ctrl+Enter",
          commandId: "command.second"
        }
      ]
    }
  });

  applyCustomizationKeymapsToRegistry(state, registry);
  const conflicts = analyzeKeybindingConflicts(registry, { key: "Ctrl+Enter" });
  assert.ok(conflicts.length >= 1);
  assert.equal(conflicts[0].reason, "override");
});

test("phase-6 keybinding window shows profile and conflict sections", () => {
  const registry = createRegistry();
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = patchCustomization(state, "session", {
    keymaps: {
      customBindings: [
        {
          pane: "editor",
          scope: "context",
          scopeId: "pane:editor",
          key: "Ctrl+Enter",
          commandId: "command.first"
        },
        {
          pane: "editor",
          scope: "context",
          scopeId: "pane:editor",
          key: "Ctrl+Enter",
          commandId: "command.second"
        }
      ]
    }
  });
  applyCustomizationKeymapsToRegistry(state, registry);

  state = openKeybindingWindow(state, { registry, taskId: "task-1" });
  const window = Object.values(state.windows).find((entry) => entry.metadata?.role === "keybindings");
  assert.ok(window);
  const widgets = window.metadata.widgets;

  const keybindingItems = state.widgets[widgets.listId].props.items;
  assert.ok(keybindingItems.some((item) => String(item.label).includes("profile(editor)")));

  const conflictItems = state.widgets[widgets.conflictListId].props.items;
  assert.ok(conflictItems.some((item) => String(item.label).includes("replaces")));
});
