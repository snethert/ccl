import {
  DEFAULT_THEME_PRESET_ID,
  getThemePreset,
  isThemeMode,
  resolveThemeTokensFromSelection,
  sanitizeThemeOverrides
} from "./theme.mjs";

export const CUSTOMIZATION_SCHEMA_VERSION = "1";
export const CUSTOMIZATION_PROFILE_VERSION = "1";
export const CUSTOMIZATION_LAYERS = Object.freeze(["defaults", "user", "project", "session"]);
export const KEYMAP_SCOPE_KINDS = Object.freeze(["global", "task", "context", "widget"]);
export const KEYMAP_PANES = Object.freeze(["editor", "repl", "debugger"]);

export const DEFAULT_PANE_PROFILE_ASSIGNMENTS = Object.freeze({
  editor: "editor-emacs",
  repl: "repl-readline",
  debugger: "debugger-single-key"
});

export const BUILTIN_KEYMAP_PROFILES = Object.freeze({
  "editor-emacs": Object.freeze({
    id: "editor-emacs",
    pane: "editor",
    title: "Editor Emacs",
    description: "Emacs-oriented editing keys for text/code panes.",
    readOnly: true,
    bindings: Object.freeze([
      Object.freeze({
        id: "editor-emacs-eval-defun",
        pane: "editor",
        scope: "context",
        scopeId: "pane:editor",
        key: "Ctrl+Enter",
        commandId: "runtime.eval.defun",
        source: "preset"
      }),
      Object.freeze({
        id: "editor-emacs-jump-def",
        pane: "editor",
        scope: "context",
        scopeId: "pane:editor",
        key: "Alt+.",
        commandId: "lisp.jump.definition",
        source: "preset"
      })
    ])
  }),
  "repl-readline": Object.freeze({
    id: "repl-readline",
    pane: "repl",
    title: "REPL Readline",
    description: "Readline-like REPL interaction keys.",
    readOnly: true,
    bindings: Object.freeze([
      Object.freeze({
        id: "repl-readline-submit",
        pane: "repl",
        scope: "context",
        scopeId: "pane:repl",
        key: "Enter",
        commandId: "runtime.repl.submit",
        source: "preset"
      }),
      Object.freeze({
        id: "repl-readline-reverse-history",
        pane: "repl",
        scope: "context",
        scopeId: "pane:repl",
        key: "Ctrl+R",
        commandId: "runtime.repl.history.search",
        source: "preset"
      })
    ])
  }),
  "debugger-single-key": Object.freeze({
    id: "debugger-single-key",
    pane: "debugger",
    title: "Debugger Single Key",
    description: "Single-key debugger flow with source-first navigation.",
    readOnly: true,
    bindings: Object.freeze([
      Object.freeze({
        id: "debugger-single-next-frame",
        pane: "debugger",
        scope: "context",
        scopeId: "pane:debugger",
        key: "n",
        commandId: "ui.debugger.frame.next",
        source: "preset"
      }),
      Object.freeze({
        id: "debugger-single-invoke-restart",
        pane: "debugger",
        scope: "context",
        scopeId: "pane:debugger",
        key: "r",
        commandId: "ui.debugger.restart.invoke",
        source: "preset"
      })
    ])
  })
});

const DEFAULT_THEME_SECTION = Object.freeze({
  presetId: DEFAULT_THEME_PRESET_ID,
  mode: "dark",
  overrides: {}
});

const DEFAULT_KEYMAP_SECTION = Object.freeze({
  paneProfiles: { ...DEFAULT_PANE_PROFILE_ASSIGNMENTS },
  profiles: { ...BUILTIN_KEYMAP_PROFILES },
  customBindings: []
});

const DEFAULT_BEGINNER_MODE_SECTION = Object.freeze({
  enabled: false,
  showExplanations: true,
  confirmAdvanced: true,
  hiddenCommandIds: [],
  forceVisibleCommandIds: []
});

const DEFAULT_SAFETY_POLICIES_SECTION = Object.freeze({
  confirmCommands: [],
  blockedCapabilities: [],
  requireUnlock: true
});

const DEFAULT_GUIDANCE_SECTION = Object.freeze({
  dismissed: []
});

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === "[object Object]";
}

function cloneValue(value) {
  if (Array.isArray(value)) return value.map(cloneValue);
  if (!isPlainObject(value)) return value;
  const out = {};
  for (const [key, entry] of Object.entries(value)) {
    out[key] = cloneValue(entry);
  }
  return out;
}

function normalizeString(value, fallback = null) {
  if (typeof value === "string" && value.trim().length > 0) return value.trim();
  return fallback;
}

function normalizeMode(value, fallback = null) {
  if (isThemeMode(value)) return value;
  return fallback;
}

function uniqueStrings(values) {
  if (!Array.isArray(values)) return [];
  const out = [];
  const seen = new Set();
  for (const value of values) {
    if (typeof value !== "string" || value.length === 0 || seen.has(value)) continue;
    seen.add(value);
    out.push(value);
  }
  return out;
}

function deepMerge(base, override) {
  if (!isPlainObject(base)) return cloneValue(override);
  const out = { ...base };
  if (!isPlainObject(override)) return out;
  for (const [key, value] of Object.entries(override)) {
    if (isPlainObject(value) && isPlainObject(out[key])) {
      out[key] = deepMerge(out[key], value);
      continue;
    }
    out[key] = cloneValue(value);
  }
  return out;
}

function normalizeThemeSection(value, options = {}) {
  const sparse = options.sparse === true;
  if (!isPlainObject(value)) {
    if (sparse) {
      return {
        presetId: null,
        mode: null,
        overrides: {}
      };
    }
    return {
      presetId: DEFAULT_THEME_SECTION.presetId,
      mode: DEFAULT_THEME_SECTION.mode,
      overrides: {}
    };
  }
  return {
    presetId: normalizeString(value.presetId, sparse ? null : DEFAULT_THEME_SECTION.presetId),
    mode: normalizeMode(value.mode, sparse ? null : DEFAULT_THEME_SECTION.mode),
    overrides: sanitizeThemeOverrides(value.overrides ?? {})
  };
}

function normalizePaneProfiles(value, options = {}) {
  const sparse = options.sparse === true;
  if (!isPlainObject(value)) {
    return sparse ? {} : { ...DEFAULT_PANE_PROFILE_ASSIGNMENTS };
  }
  const out = sparse ? {} : { ...DEFAULT_PANE_PROFILE_ASSIGNMENTS };
  for (const pane of KEYMAP_PANES) {
    if (!Object.prototype.hasOwnProperty.call(value, pane)) continue;
    const profileId = normalizeString(value[pane], null);
    if (profileId) {
      out[pane] = profileId;
    } else if (!sparse) {
      out[pane] = DEFAULT_PANE_PROFILE_ASSIGNMENTS[pane];
    }
  }
  return out;
}

function normalizeKeyBinding(binding, index, options = {}) {
  if (!isPlainObject(binding)) return null;
  const pane = normalizeString(binding.pane, options.pane ?? null);
  if (pane && !KEYMAP_PANES.includes(pane)) return null;
  const scope = KEYMAP_SCOPE_KINDS.includes(binding.scope) ? binding.scope : "context";
  const key = normalizeString(binding.key, null);
  const commandId = normalizeString(binding.commandId, null);
  if (!key || !commandId) return null;
  const id = normalizeString(binding.id, `binding-${index + 1}`);
  const scopeId =
    normalizeString(binding.scopeId, null) ??
    (scope === "context" && pane ? `pane:${pane}` : null);
  return {
    id,
    pane: pane ?? null,
    scope,
    scopeId,
    key,
    commandId,
    source: normalizeString(binding.source, "custom")
  };
}

function normalizeBindings(value, options = {}) {
  if (!Array.isArray(value)) return [];
  const out = [];
  for (let index = 0; index < value.length; index += 1) {
    const normalized = normalizeKeyBinding(value[index], index, options);
    if (normalized) {
      out.push(normalized);
    }
  }
  return out;
}

function normalizeKeymapProfile(value, profileId, options = {}) {
  if (!isPlainObject(value)) return null;
  const id = normalizeString(value.id, normalizeString(profileId, null));
  if (!id) return null;
  const pane = KEYMAP_PANES.includes(value.pane) ? value.pane : options.defaultPane ?? null;
  const bindings = normalizeBindings(value.bindings, { pane });
  return {
    id,
    pane,
    title: normalizeString(value.title, id),
    description: normalizeString(value.description, null),
    readOnly: Boolean(value.readOnly),
    bindings
  };
}

function normalizeProfiles(value, options = {}) {
  const sparse = options.sparse === true;
  const out = {};
  if (!sparse) {
    for (const [id, profile] of Object.entries(BUILTIN_KEYMAP_PROFILES)) {
      out[id] = {
        id: profile.id,
        pane: profile.pane,
        title: profile.title,
        description: profile.description,
        readOnly: true,
        bindings: normalizeBindings(profile.bindings, { pane: profile.pane })
      };
    }
  }
  if (!isPlainObject(value)) return out;
  for (const [id, profile] of Object.entries(value)) {
    const normalized = normalizeKeymapProfile(profile, id);
    if (!normalized) continue;
    if (out[normalized.id]?.readOnly) {
      continue;
    }
    out[normalized.id] = normalized;
  }
  return out;
}

function normalizeKeymapsSection(value, options = {}) {
  const sparse = options.sparse === true;
  if (!isPlainObject(value)) {
    return {
      paneProfiles: sparse ? {} : { ...DEFAULT_PANE_PROFILE_ASSIGNMENTS },
      profiles: sparse ? {} : normalizeProfiles({}, { sparse: false }),
      customBindings: []
    };
  }
  return {
    paneProfiles: normalizePaneProfiles(value.paneProfiles, { sparse }),
    profiles: normalizeProfiles(value.profiles, { sparse }),
    customBindings: normalizeBindings(value.customBindings)
  };
}

function normalizeBeginnerModeSection(value, options = {}) {
  const sparse = options.sparse === true;
  if (!isPlainObject(value)) {
    if (sparse) {
      return {
        enabled: null,
        showExplanations: null,
        confirmAdvanced: null,
        hiddenCommandIds: [],
        forceVisibleCommandIds: []
      };
    }
    return cloneValue(DEFAULT_BEGINNER_MODE_SECTION);
  }
  return {
    enabled: typeof value.enabled === "boolean" ? value.enabled : sparse ? null : DEFAULT_BEGINNER_MODE_SECTION.enabled,
    showExplanations:
      typeof value.showExplanations === "boolean"
        ? value.showExplanations
        : sparse
          ? null
          : DEFAULT_BEGINNER_MODE_SECTION.showExplanations,
    confirmAdvanced:
      typeof value.confirmAdvanced === "boolean"
        ? value.confirmAdvanced
        : sparse
          ? null
          : DEFAULT_BEGINNER_MODE_SECTION.confirmAdvanced,
    hiddenCommandIds: uniqueStrings(value.hiddenCommandIds),
    forceVisibleCommandIds: uniqueStrings(value.forceVisibleCommandIds)
  };
}

function normalizeSafetyPoliciesSection(value, options = {}) {
  const sparse = options.sparse === true;
  if (!isPlainObject(value)) {
    if (sparse) {
      return {
        confirmCommands: [],
        blockedCapabilities: [],
        requireUnlock: null
      };
    }
    return cloneValue(DEFAULT_SAFETY_POLICIES_SECTION);
  }
  return {
    confirmCommands: uniqueStrings(value.confirmCommands),
    blockedCapabilities: uniqueStrings(value.blockedCapabilities),
    requireUnlock:
      typeof value.requireUnlock === "boolean"
        ? value.requireUnlock
        : sparse
          ? null
          : DEFAULT_SAFETY_POLICIES_SECTION.requireUnlock
  };
}

function normalizeGuidanceSection(value) {
  if (!isPlainObject(value)) {
    return cloneValue(DEFAULT_GUIDANCE_SECTION);
  }
  return {
    dismissed: uniqueStrings(value.dismissed)
  };
}

export function normalizeCustomizationLayer(layer, options = {}) {
  const sparse = options.sparse === true;
  return {
    theme: normalizeThemeSection(layer?.theme, { sparse }),
    keymaps: normalizeKeymapsSection(layer?.keymaps, { sparse }),
    beginnerMode: normalizeBeginnerModeSection(layer?.beginnerMode, { sparse }),
    safetyPolicies: normalizeSafetyPoliciesSection(layer?.safetyPolicies, { sparse }),
    guidance: normalizeGuidanceSection(layer?.guidance)
  };
}

function createDefaultLayers() {
  return {
    defaults: normalizeCustomizationLayer({}, { sparse: false }),
    user: normalizeCustomizationLayer({}, { sparse: true }),
    project: normalizeCustomizationLayer({}, { sparse: true }),
    session: normalizeCustomizationLayer({}, { sparse: true })
  };
}

function mergeBindings(baseBindings, incomingBindings) {
  const byFingerprint = new Map();
  const toFingerprint = (binding) =>
    [
      binding.pane ?? "",
      binding.scope ?? "",
      binding.scopeId ?? "",
      binding.key ?? ""
    ].join("|");
  for (const binding of baseBindings) {
    byFingerprint.set(toFingerprint(binding), binding);
  }
  for (const binding of incomingBindings) {
    byFingerprint.set(toFingerprint(binding), binding);
  }
  return [...byFingerprint.values()];
}

function mergeProfiles(baseProfiles, incomingProfiles) {
  const next = { ...baseProfiles };
  for (const [id, profile] of Object.entries(incomingProfiles ?? {})) {
    if (next[id]?.readOnly) continue;
    next[id] = {
      ...(next[id] ?? {}),
      ...profile,
      bindings: normalizeBindings(profile.bindings ?? [])
    };
  }
  return next;
}

function applyLayerToEffective(effective, layer) {
  const next = cloneValue(effective);
  if (layer.theme.presetId) {
    next.theme.presetId = layer.theme.presetId;
    if (!layer.theme.mode) {
      next.theme.mode = getThemePreset(layer.theme.presetId)?.mode ?? next.theme.mode;
    }
  }
  if (layer.theme.mode) next.theme.mode = layer.theme.mode;
  next.theme.overrides = deepMerge(next.theme.overrides, layer.theme.overrides);

  next.keymaps.paneProfiles = { ...next.keymaps.paneProfiles, ...(layer.keymaps.paneProfiles ?? {}) };
  next.keymaps.profiles = mergeProfiles(next.keymaps.profiles, layer.keymaps.profiles);
  next.keymaps.customBindings = mergeBindings(next.keymaps.customBindings, layer.keymaps.customBindings ?? []);

  if (typeof layer.beginnerMode.enabled === "boolean") next.beginnerMode.enabled = layer.beginnerMode.enabled;
  if (typeof layer.beginnerMode.showExplanations === "boolean") {
    next.beginnerMode.showExplanations = layer.beginnerMode.showExplanations;
  }
  if (typeof layer.beginnerMode.confirmAdvanced === "boolean") {
    next.beginnerMode.confirmAdvanced = layer.beginnerMode.confirmAdvanced;
  }
  next.beginnerMode.hiddenCommandIds = uniqueStrings([
    ...next.beginnerMode.hiddenCommandIds,
    ...(layer.beginnerMode.hiddenCommandIds ?? [])
  ]);
  next.beginnerMode.forceVisibleCommandIds = uniqueStrings([
    ...next.beginnerMode.forceVisibleCommandIds,
    ...(layer.beginnerMode.forceVisibleCommandIds ?? [])
  ]);
  if (next.beginnerMode.forceVisibleCommandIds.length > 0) {
    const visible = new Set(next.beginnerMode.forceVisibleCommandIds);
    next.beginnerMode.hiddenCommandIds = next.beginnerMode.hiddenCommandIds.filter((id) => !visible.has(id));
  }

  next.safetyPolicies.confirmCommands = uniqueStrings([
    ...next.safetyPolicies.confirmCommands,
    ...(layer.safetyPolicies.confirmCommands ?? [])
  ]);
  next.safetyPolicies.blockedCapabilities = uniqueStrings([
    ...next.safetyPolicies.blockedCapabilities,
    ...(layer.safetyPolicies.blockedCapabilities ?? [])
  ]);
  if (typeof layer.safetyPolicies.requireUnlock === "boolean") {
    next.safetyPolicies.requireUnlock = layer.safetyPolicies.requireUnlock;
  }

  next.guidance.dismissed = uniqueStrings([...next.guidance.dismissed, ...(layer.guidance.dismissed ?? [])]);
  return next;
}

function createEffectiveDefaults() {
  return {
    theme: {
      presetId: DEFAULT_THEME_SECTION.presetId,
      mode: DEFAULT_THEME_SECTION.mode,
      overrides: {}
    },
    keymaps: {
      paneProfiles: { ...DEFAULT_PANE_PROFILE_ASSIGNMENTS },
      profiles: normalizeProfiles({}, { sparse: false }),
      customBindings: []
    },
    beginnerMode: cloneValue(DEFAULT_BEGINNER_MODE_SECTION),
    safetyPolicies: cloneValue(DEFAULT_SAFETY_POLICIES_SECTION),
    guidance: cloneValue(DEFAULT_GUIDANCE_SECTION)
  };
}

function buildEffectiveCustomization(layers) {
  let effective = createEffectiveDefaults();
  effective = applyLayerToEffective(effective, layers.defaults);
  effective = applyLayerToEffective(effective, layers.user);
  effective = applyLayerToEffective(effective, layers.project);
  effective = applyLayerToEffective(effective, layers.session);
  effective.theme.tokens = resolveThemeTokensFromSelection({
    presetId: effective.theme.presetId,
    mode: effective.theme.mode,
    overrides: effective.theme.overrides
  });
  return effective;
}

export function normalizeCustomizationEnvelope(customization) {
  const source = isPlainObject(customization) ? customization : {};
  const layersIn = isPlainObject(source.layers) ? source.layers : {};
  const layers = createDefaultLayers();
  layers.defaults = normalizeCustomizationLayer(layersIn.defaults ?? source.defaults, { sparse: false });
  layers.user = normalizeCustomizationLayer(layersIn.user ?? source.user, { sparse: true });
  layers.project = normalizeCustomizationLayer(layersIn.project ?? source.project, { sparse: true });
  layers.session = normalizeCustomizationLayer(layersIn.session ?? source.session, { sparse: true });
  return {
    schemaVersion: normalizeString(source.schemaVersion, CUSTOMIZATION_SCHEMA_VERSION),
    layers,
    effective: buildEffectiveCustomization(layers)
  };
}

function mergeLayerPatch(layer, patch) {
  const patchObject = isPlainObject(patch) ? patch : {};
  const merged = deepMerge(layer, patchObject);
  if (isPlainObject(patchObject.theme) && Object.prototype.hasOwnProperty.call(patchObject.theme, "overrides")) {
    merged.theme = {
      ...(merged.theme ?? {}),
      overrides: sanitizeThemeOverrides(patchObject.theme.overrides ?? {})
    };
  }
  if (isPlainObject(patchObject.keymaps) && Array.isArray(patchObject.keymaps.customBindings)) {
    merged.keymaps = {
      ...(merged.keymaps ?? {}),
      customBindings: normalizeBindings(patchObject.keymaps.customBindings)
    };
  }
  if (isPlainObject(patchObject.guidance) && Array.isArray(patchObject.guidance.dismissed)) {
    merged.guidance = {
      ...(merged.guidance ?? {}),
      dismissed: uniqueStrings(patchObject.guidance.dismissed)
    };
  }
  return merged;
}

export function patchCustomizationLayer(customization, layerName, patch) {
  const base = normalizeCustomizationEnvelope(customization);
  const layer = CUSTOMIZATION_LAYERS.includes(layerName) ? layerName : "session";
  const sparse = layer !== "defaults";
  const patched = mergeLayerPatch(base.layers[layer], patch);
  const nextLayers = {
    ...base.layers,
    [layer]: normalizeCustomizationLayer(patched, { sparse })
  };
  return normalizeCustomizationEnvelope({
    ...base,
    layers: nextLayers
  });
}

export function resolveCustomizationTheme(customization) {
  const normalized = normalizeCustomizationEnvelope(customization);
  return normalized.effective.theme.tokens;
}

export function normalizeCustomizationProfile(profile) {
  const source = isPlainObject(profile) ? profile : {};
  return {
    profileVersion: normalizeString(source.profileVersion, CUSTOMIZATION_PROFILE_VERSION),
    schemaVersion: normalizeString(source.schemaVersion, CUSTOMIZATION_SCHEMA_VERSION),
    name: normalizeString(source.name, "Customization Profile"),
    sections: {
      theme: normalizeThemeSection(source.sections?.theme ?? null, { sparse: true }),
      keymaps: normalizeKeymapsSection(source.sections?.keymaps ?? null, { sparse: true }),
      beginnerMode: normalizeBeginnerModeSection(source.sections?.beginnerMode ?? null, { sparse: true }),
      safetyPolicies: normalizeSafetyPoliciesSection(source.sections?.safetyPolicies ?? null, { sparse: true })
    }
  };
}

export function validateCustomizationProfile(profile) {
  const errors = [];
  if (!isPlainObject(profile)) {
    return { ok: false, errors: ["Profile must be an object"] };
  }
  if (typeof profile.sections !== "object" || profile.sections === null) {
    errors.push("Profile sections are required");
  }
  const normalized = normalizeCustomizationProfile(profile);
  const emptySections =
    !normalized.sections.theme.presetId &&
    !normalized.sections.theme.mode &&
    Object.keys(normalized.sections.theme.overrides).length === 0 &&
    Object.keys(normalized.sections.keymaps.paneProfiles).length === 0 &&
    Object.keys(normalized.sections.keymaps.profiles).length === 0 &&
    normalized.sections.keymaps.customBindings.length === 0 &&
    normalized.sections.beginnerMode.enabled === null &&
    normalized.sections.beginnerMode.showExplanations === null &&
    normalized.sections.beginnerMode.confirmAdvanced === null &&
    normalized.sections.beginnerMode.hiddenCommandIds.length === 0 &&
    normalized.sections.beginnerMode.forceVisibleCommandIds.length === 0 &&
    normalized.sections.safetyPolicies.confirmCommands.length === 0 &&
    normalized.sections.safetyPolicies.blockedCapabilities.length === 0 &&
    normalized.sections.safetyPolicies.requireUnlock === null;
  if (emptySections) {
    errors.push("Profile does not define any customization sections");
  }
  return { ok: errors.length === 0, errors, profile: normalized };
}

export function exportCustomizationProfile(customization, options = {}) {
  const normalized = normalizeCustomizationEnvelope(customization);
  const sourceLayer = CUSTOMIZATION_LAYERS.includes(options.sourceLayer) ? options.sourceLayer : "effective";
  const source = sourceLayer === "effective" ? normalized.effective : normalized.layers[sourceLayer];
  return {
    profileVersion: CUSTOMIZATION_PROFILE_VERSION,
    schemaVersion: CUSTOMIZATION_SCHEMA_VERSION,
    name: normalizeString(options.name, "Customization Profile"),
    exportedAt: Number.isInteger(options.now) ? options.now : null,
    sections: {
      theme: cloneValue(source.theme),
      keymaps: cloneValue(source.keymaps),
      beginnerMode: cloneValue(source.beginnerMode),
      safetyPolicies: cloneValue(source.safetyPolicies)
    }
  };
}

export function importCustomizationProfile(customization, profile, options = {}) {
  const validation = validateCustomizationProfile(profile);
  if (!validation.ok) {
    return {
      ok: false,
      reason: "Invalid customization profile",
      errors: validation.errors,
      customization: normalizeCustomizationEnvelope(customization)
    };
  }
  const layer = CUSTOMIZATION_LAYERS.includes(options.layer) ? options.layer : "user";
  const normalized = normalizeCustomizationEnvelope(customization);
  const rollback = cloneValue(normalized);
  const patch = validation.profile.sections;
  const next = patchCustomizationLayer(normalized, layer, patch);
  return {
    ok: true,
    customization: next,
    rollback
  };
}
