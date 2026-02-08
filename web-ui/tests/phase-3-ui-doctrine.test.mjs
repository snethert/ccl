import { test } from "node:test";
import assert from "node:assert/strict";

import { UI_STYLES, UI_STYLE_ID } from "../styles/ui.mjs";
import { DEFAULT_THEME_TOKENS, themeToCssVars } from "../src/theme.mjs";

test("phase-3 ui doctrine includes base ui classes", () => {
  assert.ok(UI_STYLES.includes(".ui-root"));
  assert.ok(UI_STYLES.includes(".ui-window"));
  assert.ok(UI_STYLES.includes(".ui-list"));
  assert.ok(UI_STYLES.includes(".ui-table"));
  assert.ok(UI_STYLES.includes(".ui-canvas-view"));
  assert.ok(UI_STYLES.includes(".ui-webgl-view"));
});

test("phase-3 ui doctrine exposes css variables for core tokens", () => {
  const vars = themeToCssVars(DEFAULT_THEME_TOKENS);
  assert.equal(vars["--ui-color-bg"], DEFAULT_THEME_TOKENS.color.bg);
  assert.equal(vars["--ui-color-surface"], DEFAULT_THEME_TOKENS.color.surface);
  assert.equal(vars["--ui-color-text-primary"], DEFAULT_THEME_TOKENS.color.text.primary);
  assert.equal(vars["--ui-radius-md"], DEFAULT_THEME_TOKENS.radius.md);
});

test("phase-3 ui doctrine defines a stable style id", () => {
  assert.equal(UI_STYLE_ID, "web-ui-styles");
});
