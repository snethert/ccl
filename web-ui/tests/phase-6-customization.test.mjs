import { test } from "node:test";
import assert from "node:assert/strict";

import {
  PERSISTENCE_SCHEMA_VERSION,
  createState,
  patchCustomization,
  createSnapshot,
  restoreStateFromSnapshot
} from "../src/index.mjs";
import { stableStringify } from "./snapshot.mjs";

test("phase-6 customization precedence is deterministic across layers", () => {
  let state = createState();
  state = patchCustomization(state, "user", {
    theme: { presetId: "core-light" },
    beginnerMode: { enabled: true }
  });
  state = patchCustomization(state, "project", {
    theme: { mode: "dark" },
    beginnerMode: { enabled: false },
    safetyPolicies: { confirmCommands: ["ui.session.delete"] }
  });
  state = patchCustomization(state, "session", {
    theme: { mode: "light" },
    safetyPolicies: { confirmCommands: ["ui.customization.profile.import"] }
  });

  const effective = state.customization.effective;
  assert.equal(effective.theme.presetId, "core-light");
  assert.equal(effective.theme.mode, "light");
  assert.equal(effective.theme.tokens.mode, "light");
  assert.equal(effective.beginnerMode.enabled, false);
  assert.deepEqual(effective.safetyPolicies.confirmCommands, [
    "ui.session.delete",
    "ui.customization.profile.import"
  ]);
});

test("phase-6 customization persists through snapshot restore", () => {
  let state = createState();
  state = patchCustomization(state, "session", {
    guidance: { dismissed: ["command:ui.layout.split"] },
    keymaps: {
      customBindings: [
        {
          pane: "editor",
          scope: "context",
          scopeId: "pane:editor",
          key: "Ctrl+Enter",
          commandId: "runtime.eval.defun"
        }
      ]
    }
  });

  const snapshot = createSnapshot(state, { now: () => 0 });
  assert.equal(snapshot.schemaVersion, PERSISTENCE_SCHEMA_VERSION);
  assert.ok(snapshot.state.customization);

  const restored = restoreStateFromSnapshot(snapshot);
  assert.equal(restored.snapshot.schemaVersion, PERSISTENCE_SCHEMA_VERSION);
  assert.equal(
    stableStringify(restored.state.customization),
    stableStringify(state.customization)
  );
});
