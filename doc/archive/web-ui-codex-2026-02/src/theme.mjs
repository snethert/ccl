const DEFAULT_THEME_MODE = "dark";
export const THEME_MODES = Object.freeze([
  "dark",
  "light",
  "high-contrast",
  "forced-colors"
]);

export function isThemeMode(value) {
  return THEME_MODES.includes(value);
}

export const DARK_THEME_TOKENS = Object.freeze({
  mode: "dark",
  color: {
    bg: "#121212",
    surface: "#1b1b1b",
    surfaceRaised: "#232323",
    surfaceSunken: "#0f0f0f",
    border: "#676767",
    text: {
      primary: "#e8e8e8",
      secondary: "#b8b8b8",
      muted: "#8a8a8a",
      inverted: "#101010"
    },
    accent: "#6fb0ff",
    accentMuted: "#355a85",
    accentText: "#0c121b",
    warning: "#f0b35b",
    error: "#f06b6b",
    success: "#6ccf8f",
    focus: "#a7c8ff",
    selection: "#2b4870",
    selectionText: "#f2f6ff",
    overlay: "rgba(0,0,0,0.35)"
  },
  elevation: {
    level1: "0 1px 4px rgba(0,0,0,0.25)",
    level2: "0 2px 8px rgba(0,0,0,0.25)",
    level3: "0 4px 12px rgba(0,0,0,0.28)",
    level4: "0 8px 20px rgba(0,0,0,0.3)"
  },
  radius: { xs: "3px", sm: "4px", md: "8px", lg: "12px" },
  space: { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 },
  font: {
    body: "Inter",
    mono: "Iosevka",
    size: { xs: 11, sm: 12, md: 14, lg: 16, xl: 20, xxl: 24 },
    weight: { regular: 400, medium: 500, bold: 600 },
    lineHeight: { tight: 1.2, normal: 1.4, relaxed: 1.6 }
  },
  motion: {
    fast: 120,
    normal: 180,
    slow: 250,
    easing: "cubic-bezier(0.2, 0, 0.2, 1)",
    reduced: false
  }
});

export const LIGHT_THEME_TOKENS = Object.freeze({
  mode: "light",
  color: {
    bg: "#f5f5f5",
    surface: "#ffffff",
    surfaceRaised: "#ffffff",
    surfaceSunken: "#ededed",
    border: "#949494",
    text: {
      primary: "#1a1a1a",
      secondary: "#444444",
      muted: "#666666",
      inverted: "#ffffff"
    },
    accent: "#2c6dd2",
    accentMuted: "#cfe0f7",
    accentText: "#ffffff",
    warning: "#af640f",
    error: "#c23b3b",
    success: "#1e7a4c",
    focus: "#2c6dd2",
    selection: "#d7e6fb",
    selectionText: "#0b1b34",
    overlay: "rgba(0,0,0,0.08)"
  },
  elevation: {
    level1: "0 1px 4px rgba(0,0,0,0.12)",
    level2: "0 2px 8px rgba(0,0,0,0.14)",
    level3: "0 4px 12px rgba(0,0,0,0.16)",
    level4: "0 8px 20px rgba(0,0,0,0.18)"
  },
  radius: { xs: "3px", sm: "4px", md: "8px", lg: "12px" },
  space: { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 },
  font: {
    body: "Inter",
    mono: "Iosevka",
    size: { xs: 11, sm: 12, md: 14, lg: 16, xl: 20, xxl: 24 },
    weight: { regular: 400, medium: 500, bold: 600 },
    lineHeight: { tight: 1.2, normal: 1.4, relaxed: 1.6 }
  },
  motion: {
    fast: 120,
    normal: 180,
    slow: 250,
    easing: "cubic-bezier(0.2, 0, 0.2, 1)",
    reduced: false
  }
});

export const HIGH_CONTRAST_THEME_TOKENS = Object.freeze({
  mode: "high-contrast",
  color: {
    bg: "#000000",
    surface: "#000000",
    surfaceRaised: "#0d0d0d",
    surfaceSunken: "#000000",
    border: "#ffffff",
    text: {
      primary: "#ffffff",
      secondary: "#ececec",
      muted: "#cccccc",
      inverted: "#000000"
    },
    accent: "#00ffff",
    accentMuted: "#006666",
    accentText: "#000000",
    warning: "#ffe000",
    error: "#ff5c5c",
    success: "#66ffa3",
    focus: "#ffff00",
    selection: "#ffffff",
    selectionText: "#000000",
    overlay: "rgba(0,0,0,0.65)"
  },
  elevation: {
    level1: "0 1px 4px rgba(0,0,0,0.25)",
    level2: "0 2px 8px rgba(0,0,0,0.25)",
    level3: "0 4px 12px rgba(0,0,0,0.28)",
    level4: "0 8px 20px rgba(0,0,0,0.3)"
  },
  radius: { xs: "3px", sm: "4px", md: "8px", lg: "12px" },
  space: { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 },
  font: {
    body: "Inter",
    mono: "Iosevka",
    size: { xs: 11, sm: 12, md: 14, lg: 16, xl: 20, xxl: 24 },
    weight: { regular: 400, medium: 500, bold: 600 },
    lineHeight: { tight: 1.2, normal: 1.4, relaxed: 1.6 }
  },
  motion: {
    fast: 120,
    normal: 180,
    slow: 250,
    easing: "cubic-bezier(0.2, 0, 0.2, 1)",
    reduced: false
  }
});

export const FORCED_COLORS_THEME_TOKENS = Object.freeze({
  mode: "forced-colors",
  color: {
    bg: "#000000",
    surface: "#000000",
    surfaceRaised: "#000000",
    surfaceSunken: "#000000",
    border: "#ffffff",
    text: {
      primary: "#ffffff",
      secondary: "#ffffff",
      muted: "#ffffff",
      inverted: "#000000"
    },
    accent: "#ffff00",
    accentMuted: "#666600",
    accentText: "#000000",
    warning: "#ffff00",
    error: "#ffffff",
    success: "#ffffff",
    focus: "#ffff00",
    selection: "#ffffff",
    selectionText: "#000000",
    overlay: "rgba(0,0,0,0)"
  },
  elevation: {
    level1: "0 1px 4px rgba(0,0,0,0.25)",
    level2: "0 2px 8px rgba(0,0,0,0.25)",
    level3: "0 4px 12px rgba(0,0,0,0.28)",
    level4: "0 8px 20px rgba(0,0,0,0.3)"
  },
  radius: { xs: "3px", sm: "4px", md: "8px", lg: "12px" },
  space: { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 },
  font: {
    body: "Inter",
    mono: "Iosevka",
    size: { xs: 11, sm: 12, md: 14, lg: 16, xl: 20, xxl: 24 },
    weight: { regular: 400, medium: 500, bold: 600 },
    lineHeight: { tight: 1.2, normal: 1.4, relaxed: 1.6 }
  },
  motion: {
    fast: 120,
    normal: 180,
    slow: 250,
    easing: "cubic-bezier(0.2, 0, 0.2, 1)",
    reduced: false
  }
});

export const DEFAULT_THEME_TOKENS = DARK_THEME_TOKENS;
export const DEFAULT_THEME_PRESET_ID = "core-dark";

export const THEME_PRESETS = Object.freeze({
  "core-dark": Object.freeze({
    id: "core-dark",
    title: "Core Dark",
    description: "Default dark palette for instrument-first workspaces.",
    mode: "dark",
    overrides: Object.freeze({})
  }),
  "core-light": Object.freeze({
    id: "core-light",
    title: "Core Light",
    description: "Default light palette with high text contrast.",
    mode: "light",
    overrides: Object.freeze({})
  }),
  "core-high-contrast": Object.freeze({
    id: "core-high-contrast",
    title: "Core High Contrast",
    description: "High-contrast palette for strict visual separation.",
    mode: "high-contrast",
    overrides: Object.freeze({})
  }),
  "core-forced-colors": Object.freeze({
    id: "core-forced-colors",
    title: "Core Forced Colors",
    description: "System-forced color lane with maximal cue preservation.",
    mode: "forced-colors",
    overrides: Object.freeze({})
  }),
  "slate-dark": Object.freeze({
    id: "slate-dark",
    title: "Slate Dark",
    description: "Muted dark palette optimized for long sessions.",
    mode: "dark",
    overrides: Object.freeze({
      color: {
        bg: "#0f1318",
        surface: "#171d24",
        surfaceRaised: "#1e2630",
        border: "#566886",
        accent: "#7bb6ff",
        selection: "#2f4f78"
      }
    })
  })
});

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === "[object Object]";
}

function mergeDeep(base, override) {
  if (!isPlainObject(base)) return override;
  const out = { ...base };
  if (!isPlainObject(override)) return out;
  for (const [key, value] of Object.entries(override)) {
    if (isPlainObject(value) && isPlainObject(out[key])) {
      out[key] = mergeDeep(out[key], value);
    } else {
      out[key] = value;
    }
  }
  return out;
}

function pruneOverrides(value, shape) {
  if (!isPlainObject(value) || !isPlainObject(shape)) return {};
  const out = {};
  for (const [key, next] of Object.entries(value)) {
    if (!Object.prototype.hasOwnProperty.call(shape, key)) continue;
    const shapeValue = shape[key];
    if (isPlainObject(next) && isPlainObject(shapeValue)) {
      const nested = pruneOverrides(next, shapeValue);
      if (Object.keys(nested).length > 0) {
        out[key] = nested;
      }
      continue;
    }
    const type = typeof next;
    if (type === "string" || type === "number" || type === "boolean") {
      out[key] = next;
    }
  }
  return out;
}

export function sanitizeThemeOverrides(overrides) {
  return pruneOverrides(overrides ?? {}, DEFAULT_THEME_TOKENS);
}

export function getThemePreset(presetId) {
  const id = typeof presetId === "string" && presetId.length > 0 ? presetId : DEFAULT_THEME_PRESET_ID;
  return THEME_PRESETS[id] ?? THEME_PRESETS[DEFAULT_THEME_PRESET_ID];
}

export function listThemePresets() {
  return Object.values(THEME_PRESETS).map((preset) => ({
    id: preset.id,
    title: preset.title,
    description: preset.description,
    mode: preset.mode
  }));
}

function resolveBaseThemeTokens(mode) {
  switch (mode) {
    case "light":
      return LIGHT_THEME_TOKENS;
    case "high-contrast":
      return HIGH_CONTRAST_THEME_TOKENS;
    case "forced-colors":
      return FORCED_COLORS_THEME_TOKENS;
    default:
      return DARK_THEME_TOKENS;
  }
}

export function resolveThemeTokensFromSelection(selection = {}) {
  const preset = getThemePreset(selection.presetId ?? null);
  const mode = isThemeMode(selection.mode)
    ? selection.mode
    : isThemeMode(preset.mode)
      ? preset.mode
      : DEFAULT_THEME_MODE;
  const base = resolveBaseThemeTokens(mode);
  const presetOverrides = sanitizeThemeOverrides(preset.overrides ?? {});
  const userOverrides = sanitizeThemeOverrides(selection.overrides ?? {});
  const merged = mergeDeep(mergeDeep(base, presetOverrides), userOverrides);
  return normalizeThemeTokens({ ...merged, mode });
}

export function normalizeThemeTokens(tokens) {
  if (!tokens || typeof tokens !== "object") {
    return { ...DEFAULT_THEME_TOKENS };
  }
  const mode = isThemeMode(tokens.mode) ? tokens.mode : DEFAULT_THEME_MODE;
  const base = resolveBaseThemeTokens(mode);
  const merged = mergeDeep(base, sanitizeThemeOverrides(tokens));
  return { ...merged, mode };
}

export function mergeThemeTokens(base, override) {
  const normalizedBase = normalizeThemeTokens(base);
  const merged = mergeDeep(normalizedBase, override ?? {});
  return normalizeThemeTokens(merged);
}

function toPx(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return `${value}px`;
  }
  return value ?? "";
}

function toMs(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return `${value}ms`;
  }
  return value ?? "";
}

function toScalar(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }
  return value ?? "";
}

export function resolveFontString(theme, options = {}) {
  const tokens = normalizeThemeTokens(theme ?? null);
  const sizeKey = options.size ?? "md";
  const family = options.mono ? tokens.font?.mono : tokens.font?.body;
  const size = tokens.font?.size?.[sizeKey] ?? tokens.font?.size?.md ?? 14;
  return `${size}px ${family ?? "sans-serif"}`;
}

export function themeToCssVars(theme) {
  const tokens = normalizeThemeTokens(theme ?? null);
  const reducedMotion = Boolean(tokens.motion?.reduced);
  const vars = {
    "--ui-color-bg": tokens.color?.bg ?? "",
    "--ui-color-surface": tokens.color?.surface ?? "",
    "--ui-color-surface-raised": tokens.color?.surfaceRaised ?? "",
    "--ui-color-surface-sunken": tokens.color?.surfaceSunken ?? "",
    "--ui-color-border": tokens.color?.border ?? "",
    "--ui-color-text-primary": tokens.color?.text?.primary ?? "",
    "--ui-color-text-secondary": tokens.color?.text?.secondary ?? "",
    "--ui-color-text-muted": tokens.color?.text?.muted ?? "",
    "--ui-color-text-inverted": tokens.color?.text?.inverted ?? "",
    "--ui-color-accent": tokens.color?.accent ?? "",
    "--ui-color-accent-muted": tokens.color?.accentMuted ?? "",
    "--ui-color-accent-text": tokens.color?.accentText ?? "",
    "--ui-color-warning": tokens.color?.warning ?? "",
    "--ui-color-error": tokens.color?.error ?? "",
    "--ui-color-success": tokens.color?.success ?? "",
    "--ui-color-focus": tokens.color?.focus ?? "",
    "--ui-color-selection": tokens.color?.selection ?? "",
    "--ui-color-selection-text": tokens.color?.selectionText ?? "",
    "--ui-color-overlay": tokens.color?.overlay ?? "",
    "--ui-elevation-1": tokens.elevation?.level1 ?? "",
    "--ui-elevation-2": tokens.elevation?.level2 ?? "",
    "--ui-elevation-3": tokens.elevation?.level3 ?? "",
    "--ui-elevation-4": tokens.elevation?.level4 ?? "",
    "--ui-radius-xs": tokens.radius?.xs ?? "",
    "--ui-radius-sm": tokens.radius?.sm ?? "",
    "--ui-radius-md": tokens.radius?.md ?? "",
    "--ui-radius-lg": tokens.radius?.lg ?? "",
    "--ui-space-xs": toPx(tokens.space?.xs),
    "--ui-space-sm": toPx(tokens.space?.sm),
    "--ui-space-md": toPx(tokens.space?.md),
    "--ui-space-lg": toPx(tokens.space?.lg),
    "--ui-space-xl": toPx(tokens.space?.xl),
    "--ui-space-xxl": toPx(tokens.space?.xxl),
    "--ui-font-body": tokens.font?.body ?? "",
    "--ui-font-mono": tokens.font?.mono ?? "",
    "--ui-font-size-xs": toPx(tokens.font?.size?.xs),
    "--ui-font-size-sm": toPx(tokens.font?.size?.sm),
    "--ui-font-size-md": toPx(tokens.font?.size?.md),
    "--ui-font-size-lg": toPx(tokens.font?.size?.lg),
    "--ui-font-size-xl": toPx(tokens.font?.size?.xl),
    "--ui-font-size-xxl": toPx(tokens.font?.size?.xxl),
    "--ui-font-weight-regular": toScalar(tokens.font?.weight?.regular),
    "--ui-font-weight-medium": toScalar(tokens.font?.weight?.medium),
    "--ui-font-weight-bold": toScalar(tokens.font?.weight?.bold),
    "--ui-line-height-tight": toScalar(tokens.font?.lineHeight?.tight),
    "--ui-line-height-normal": toScalar(tokens.font?.lineHeight?.normal),
    "--ui-line-height-relaxed": toScalar(tokens.font?.lineHeight?.relaxed),
    "--ui-motion-fast": toMs(reducedMotion ? 0 : tokens.motion?.fast),
    "--ui-motion-normal": toMs(reducedMotion ? 0 : tokens.motion?.normal),
    "--ui-motion-slow": toMs(reducedMotion ? 0 : tokens.motion?.slow),
    "--ui-motion-easing": tokens.motion?.easing ?? "",
    "--ui-motion-reduced": reducedMotion ? "1" : "0"
  };
  return vars;
}
