import { test } from "node:test";
import assert from "node:assert/strict";

import { DEFAULT_THEME_TOKENS, normalizeThemeTokens, mergeThemeTokens } from "../src/theme.mjs";

test("normalizeThemeTokens returns defaults for null", () => {
  const tokens = normalizeThemeTokens(null);
  assert.equal(tokens.mode, "dark");
  assert.equal(tokens.color.bg, DEFAULT_THEME_TOKENS.color.bg);
});

test("mergeThemeTokens overrides nested values", () => {
  const merged = mergeThemeTokens(DEFAULT_THEME_TOKENS, { color: { bg: "#000" } });
  assert.equal(merged.color.bg, "#000");
  assert.equal(merged.color.surface, DEFAULT_THEME_TOKENS.color.surface);
});
