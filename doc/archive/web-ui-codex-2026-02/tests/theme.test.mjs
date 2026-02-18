import { test } from "node:test";
import assert from "node:assert/strict";

import {
  DEFAULT_THEME_TOKENS,
  DARK_THEME_TOKENS,
  LIGHT_THEME_TOKENS,
  HIGH_CONTRAST_THEME_TOKENS,
  FORCED_COLORS_THEME_TOKENS,
  normalizeThemeTokens,
  mergeThemeTokens,
  resolveFontString,
  themeToCssVars
} from "../src/theme.mjs";

function parseHexColor(hex) {
  const value = String(hex ?? "").trim();
  if (!value.startsWith("#")) {
    throw new Error(`Expected hex color, got: ${value}`);
  }
  const raw = value.slice(1);
  const normalized =
    raw.length === 3
      ? raw
          .split("")
          .map((char) => char + char)
          .join("")
      : raw;
  if (normalized.length !== 6) {
    throw new Error(`Unsupported hex color: ${value}`);
  }
  const int = Number.parseInt(normalized, 16);
  return {
    r: (int >> 16) & 0xff,
    g: (int >> 8) & 0xff,
    b: int & 0xff
  };
}

function srgbToLinear(channel) {
  const value = channel / 255;
  if (value <= 0.03928) return value / 12.92;
  return ((value + 0.055) / 1.055) ** 2.4;
}

function relativeLuminance(color) {
  return (
    0.2126 * srgbToLinear(color.r) +
    0.7152 * srgbToLinear(color.g) +
    0.0722 * srgbToLinear(color.b)
  );
}

function contrastRatio(foregroundHex, backgroundHex) {
  const foreground = parseHexColor(foregroundHex);
  const background = parseHexColor(backgroundHex);
  const l1 = relativeLuminance(foreground);
  const l2 = relativeLuminance(background);
  const light = Math.max(l1, l2);
  const dark = Math.min(l1, l2);
  return (light + 0.05) / (dark + 0.05);
}

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

test("normalizeThemeTokens honors high-contrast mode", () => {
  const tokens = normalizeThemeTokens({ mode: "high-contrast" });
  assert.equal(tokens.mode, "high-contrast");
  assert.equal(tokens.color.bg, HIGH_CONTRAST_THEME_TOKENS.color.bg);
  assert.equal(tokens.color.focus, HIGH_CONTRAST_THEME_TOKENS.color.focus);
});

test("normalizeThemeTokens honors forced-colors mode", () => {
  const tokens = normalizeThemeTokens({ mode: "forced-colors" });
  assert.equal(tokens.mode, "forced-colors");
  assert.equal(tokens.color.bg, FORCED_COLORS_THEME_TOKENS.color.bg);
  assert.equal(tokens.color.focus, FORCED_COLORS_THEME_TOKENS.color.focus);
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

test("theme tokens satisfy baseline accessibility contrast thresholds", () => {
  const dark = DARK_THEME_TOKENS.color;
  const light = LIGHT_THEME_TOKENS.color;

  assert.ok(
    contrastRatio(dark.text.primary, dark.bg) >= 4.5,
    "dark textPrimary/bg must meet 4.5:1"
  );
  assert.ok(
    contrastRatio(light.text.primary, light.bg) >= 4.5,
    "light textPrimary/bg must meet 4.5:1"
  );
  assert.ok(
    contrastRatio(dark.selectionText, dark.selection) >= 4.5,
    "dark selectionText/selection must meet 4.5:1"
  );
  assert.ok(
    contrastRatio(light.selectionText, light.selection) >= 4.5,
    "light selectionText/selection must meet 4.5:1"
  );

  assert.ok(
    contrastRatio(dark.border, dark.surface) >= 3,
    "dark border/surface must meet 3:1"
  );
  assert.ok(
    contrastRatio(light.border, light.surface) >= 3,
    "light border/surface must meet 3:1"
  );
  assert.ok(
    contrastRatio(light.warning, light.surface) >= 4.5,
    "light warning/surface must meet 4.5:1"
  );
});
