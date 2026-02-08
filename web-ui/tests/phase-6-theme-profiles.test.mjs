import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createRegistry,
  executeCommand,
  createState,
  setThemePreset,
  setThemeOverrides,
  resetThemeOverrides,
  registerCustomizationCommands,
  CUSTOMIZATION_THEME_PRESET_COMMAND,
  CUSTOMIZATION_THEME_OVERRIDES_COMMAND,
  listThemePresets
} from "../src/index.mjs";

test("phase-6 theme presets are discoverable", () => {
  const presets = listThemePresets();
  const ids = new Set(presets.map((preset) => preset.id));
  assert.equal(ids.has("core-dark"), true);
  assert.equal(ids.has("core-light"), true);
});

test("phase-6 setThemePreset and token overrides are reversible", () => {
  let state = createState();
  state = setThemePreset(state, "core-light");
  const baselineAccent = state.theme.color.accent;
  assert.equal(state.theme.mode, "light");

  state = setThemeOverrides(state, {
    color: { accent: "#112233" },
    unknownSection: { value: 1 }
  });
  assert.equal(state.theme.color.accent, "#112233");
  assert.equal(state.theme.unknownSection, undefined);

  state = resetThemeOverrides(state);
  assert.equal(state.theme.color.accent, baselineAccent);
  assert.equal(state.theme.mode, "light");
});

test("phase-6 customization commands apply theme preset and overrides", () => {
  const registry = createRegistry();
  registerCustomizationCommands(registry);

  let state = createState();
  let result = executeCommand(registry, CUSTOMIZATION_THEME_PRESET_COMMAND, {
    state,
    payload: { presetId: "core-light" }
  });
  assert.equal(result.ok, true);
  state = result.result;
  assert.equal(state.theme.mode, "light");

  result = executeCommand(registry, CUSTOMIZATION_THEME_OVERRIDES_COMMAND, {
    state,
    payload: { overrides: { color: { accent: "#334455" } } }
  });
  assert.equal(result.ok, true);
  state = result.result;
  assert.equal(state.theme.color.accent, "#334455");
});
