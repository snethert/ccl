const DEFAULT_THEME_MODE = "dark";

export const DEFAULT_THEME_TOKENS = Object.freeze({
  mode: DEFAULT_THEME_MODE,
  color: {
    bg: "#121212",
    surface: "#1b1b1b",
    text: {
      primary: "#e8e8e8",
      secondary: "#b8b8b8"
    },
    accent: "#6fb0ff",
    accentMuted: "#355a85",
    warning: "#f0b35b",
    error: "#f06b6b"
  },
  elevation: {
    level1: "0 1px 4px rgba(0,0,0,0.25)",
    level2: "0 2px 8px rgba(0,0,0,0.25)",
    level3: "0 4px 12px rgba(0,0,0,0.28)",
    level4: "0 8px 20px rgba(0,0,0,0.3)"
  },
  radius: { sm: "4px", md: "8px" },
  space: { xs: 4, sm: 8, md: 12, lg: 16, xl: 24 },
  font: {
    body: "Inter",
    mono: "Iosevka",
    size: { sm: 12, md: 14, lg: 16, xl: 20 }
  },
  motion: {
    fast: 120,
    normal: 180,
    slow: 250,
    easing: "ease-out",
    reduced: false
  }
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

export function normalizeThemeTokens(tokens) {
  const base = DEFAULT_THEME_TOKENS;
  if (!tokens || typeof tokens !== "object") {
    return { ...base };
  }
  const mode = tokens.mode === "light" ? "light" : "dark";
  const merged = mergeDeep(base, tokens);
  return { ...merged, mode };
}

export function mergeThemeTokens(base, override) {
  const normalizedBase = normalizeThemeTokens(base);
  const merged = mergeDeep(normalizedBase, override ?? {});
  return normalizeThemeTokens(merged);
}
