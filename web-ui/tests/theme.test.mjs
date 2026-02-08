import { test } from "node:test";
import assert from "node:assert/strict";

import {
  DEFAULT_THEME_TOKENS,
  DARK_THEME_TOKENS,
  LIGHT_THEME_TOKENS,
  normalizeThemeTokens,
  mergeThemeTokens,
  resolveFontString,
  themeToCssVars
} from "../src/theme.mjs";

test("normalizeThemeTokens returns defaults for null", () => {
  const tokens = normalizeThemeTokens(null);
  assert.equal(tokens.mode, "dark");
  assert.equal(tokens.color.bg, DEFAULT_THEME_TOKENS.color.bg);
});

test("normalizeThemeTokens honors light mode", () => {
  const tokens = normalizeThemeTokens({ mode: "light" });
  assert.equal(tokens.mode, "light");
  assert.equal(tokens.color.bg, LIGHT_THEME_TOKENS.color.bg);
});

test("mergeThemeTokens overrides nested values", () => {
  const merged = mergeThemeTokens(DEFAULT_THEME_TOKENS, { color: { bg: "#000" } });
  assert.equal(merged.color.bg, "#000");
  assert.equal(merged.color.surface, DEFAULT_THEME_TOKENS.color.surface);
});

test("resolveFontString uses mono family when requested", () => {
  const font = resolveFontString(DARK_THEME_TOKENS, { mono: true, size: "lg" });
  assert.ok(font.includes("16px"));
  assert.ok(font.includes(DARK_THEME_TOKENS.font.mono));
});

test("themeToCssVars maps key tokens into CSS variables", () => {
  const vars = themeToCssVars(DEFAULT_THEME_TOKENS);
  assert.equal(vars["--ui-color-bg"], DEFAULT_THEME_TOKENS.color.bg);
  assert.equal(vars["--ui-font-size-md"], "14px");
  assert.equal(vars["--ui-color-text-primary"], DEFAULT_THEME_TOKENS.color.text.primary);
});
