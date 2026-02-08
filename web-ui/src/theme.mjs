const DEFAULT_THEME_MODE = "dark";

export const DARK_THEME_TOKENS = Object.freeze({
  mode: "dark",
  color: {
    bg: "#121212",
    surface: "#1b1b1b",
    surfaceRaised: "#232323",
    surfaceSunken: "#0f0f0f",
    border: "#2a2a2a",
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
    border: "#d6d6d6",
    text: {
      primary: "#1a1a1a",
      secondary: "#444444",
      muted: "#666666",
      inverted: "#ffffff"
    },
    accent: "#2c6dd2",
    accentMuted: "#cfe0f7",
    accentText: "#ffffff",
    warning: "#b96a10",
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

export const DEFAULT_THEME_TOKENS = DARK_THEME_TOKENS;

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

export function normalizeThemeTokens(tokens) {
  if (!tokens || typeof tokens !== "object") {
    return { ...DEFAULT_THEME_TOKENS };
  }
  const mode = tokens.mode === "light" ? "light" : "dark";
  const base = mode === "light" ? LIGHT_THEME_TOKENS : DARK_THEME_TOKENS;
  const merged = mergeDeep(base, tokens);
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
    "--ui-motion-fast": toMs(tokens.motion?.fast),
    "--ui-motion-normal": toMs(tokens.motion?.normal),
    "--ui-motion-slow": toMs(tokens.motion?.slow),
    "--ui-motion-easing": tokens.motion?.easing ?? ""
  };
  return vars;
}
