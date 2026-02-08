import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createRegistry,
  registerCommand,
  executeCommand,
  createState,
  addTask,
  createSession,
  saveSession,
  createSnapshot,
  restoreStateFromSnapshot,
  registerCustomizationCommands,
  CUSTOMIZATION_PROFILE_IMPORT_COMMAND,
  CUSTOMIZATION_THEME_OVERRIDES_COMMAND,
  CUSTOMIZATION_PROFILE_EXPORT_COMMAND
} from "../src/index.mjs";

test("phase-6 integration: profile import, beginner policy, session save/restore", () => {
  const registry = createRegistry();
  registerCustomizationCommands(registry);
  registerCommand(registry, { id: "basic.run", exec: () => "ok" });

  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = createSession(state, { name: "Phase 6 Session", now: () => 10 });

  const profile = {
    profileVersion: "1",
    schemaVersion: "1",
    name: "Learning",
    sections: {
      theme: { presetId: "core-light" },
      keymaps: { paneProfiles: { editor: "editor-emacs" } },
      beginnerMode: { enabled: true },
      safetyPolicies: { confirmCommands: ["ui.customization.profile.import"] }
    }
  };

  let result = executeCommand(registry, CUSTOMIZATION_PROFILE_IMPORT_COMMAND, {
    state,
    payload: { profile, layer: "user" }
  });
  assert.equal(result.ok, true);
  state = result.result.state;
  assert.equal(state.customization.effective.beginnerMode.enabled, true);
  assert.equal(state.theme.mode, "light");

  result = executeCommand(registry, "basic.run", { state });
  assert.equal(result.ok, true);
  assert.equal(result.result, "ok");

  const blocked = executeCommand(registry, CUSTOMIZATION_THEME_OVERRIDES_COMMAND, {
    state,
    payload: { overrides: { color: { accent: "#225588" } } }
  });
  assert.equal(blocked.ok, false);
  assert.equal(blocked.reason, "Confirmation required");

  result = executeCommand(registry, CUSTOMIZATION_THEME_OVERRIDES_COMMAND, {
    state,
    confirmBeginner: true,
    payload: { overrides: { color: { accent: "#225588" } } }
  });
  assert.equal(result.ok, true);
  state = result.result;
  assert.equal(state.theme.color.accent, "#225588");

  const exported = executeCommand(registry, CUSTOMIZATION_PROFILE_EXPORT_COMMAND, {
    state,
    confirmBeginner: true,
    payload: { name: "Exported Learning" }
  });
  assert.equal(exported.ok, true);
  assert.equal(exported.result.output.kind, "customization.profile.export");
  assert.equal(exported.result.output.profile.name, "Exported Learning");

  state = saveSession(state, state.activeSessionId, { now: () => 20 });
  const snapshot = createSnapshot(state, { now: () => 25 });
  const restored = restoreStateFromSnapshot(snapshot);
  assert.equal(restored.state.activeSessionId, state.activeSessionId);
  assert.equal(restored.state.customization.effective.beginnerMode.enabled, true);
  assert.equal(restored.state.theme.color.accent, "#225588");
});
