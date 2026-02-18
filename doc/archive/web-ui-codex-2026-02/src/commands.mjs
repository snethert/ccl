import { normalizeCommandSpec, materializeInvocation, executeTypedCommand } from "./typed-commands.mjs";

const DEFAULT_PRECEDENCE = ["global", "task", "context", "widget"];
const DEFAULT_NAMESPACE_POLICY = "allow";

function normalizeCreateArgs(args) {
  if (Array.isArray(args)) {
    return { precedence: args };
  }
  if (args && typeof args === "object") {
    return args;
  }
  return {};
}

export function createRegistry(options = DEFAULT_PRECEDENCE) {
  const resolved = normalizeCreateArgs(options);
  const precedence = resolved.precedence ?? DEFAULT_PRECEDENCE;
  return {
    precedence,
    namespacePolicy: resolved.namespacePolicy ?? DEFAULT_NAMESPACE_POLICY,
    version: resolved.version ?? "0",
    commands: new Map(),
    presentationTranslators: new Map(),
    keymapConflicts: [],
    keymaps: {
      global: new Map(),
      task: new Map(),
      context: new Map(),
      widget: new Map()
    }
  };
}

function presentationKey(type, gesture) {
  return `${type ?? "unknown"}:${gesture ?? "default"}`;
}

function validateCommandId(registry, id) {
  if (!id || typeof id !== "string") {
    throw new Error("Command must have a string id");
  }
  if (registry.namespacePolicy === "require-dot" && !id.includes(".")) {
    throw new Error(`Command id must be namespaced: ${id}`);
  }
}

export function normalizeCommand(command) {
  if (!command || typeof command !== "object") {
    throw new Error("Command must be an object");
  }
  const typed = normalizeCommandSpec({
    ...command,
    scope: command.scope ?? "global"
  });
  return {
    id: typed.id,
    title: command.title ?? typed.title ?? typed.id,
    doc: command.doc ?? typed.doc ?? null,
    scope: command.scope ?? typed.scope ?? "global",
    capability: command.capability ?? typed.capability ?? null,
    enabled: command.enabled ?? typed.enabled ?? null,
    exec: command.exec ?? typed.exec ?? null,
    args: typed.args ?? [],
    metadata: command.metadata ?? typed.metadata ?? {}
  };
}

export function registerCommand(registry, command) {
  const normalized = normalizeCommand(command);
  validateCommandId(registry, normalized.id);
  if (registry.commands.has(normalized.id)) {
    throw new Error(`Command already registered: ${normalized.id}`);
  }
  registry.commands.set(normalized.id, normalized);
  return registry;
}

export function bindKey(registry, scope, key, commandId, scopeId = null) {
  if (!registry.keymaps[scope]) {
    throw new Error(`Unknown scope: ${scope}`);
  }
  if (scope === "global") {
    const prior = registry.keymaps.global.get(key);
    if (prior && prior !== commandId) {
      registry.keymapConflicts.push({
        id: `bind-conflict-global-${key}`,
        key,
        winner: { scope: "global", scopeId: null, key, commandId },
        shadowed: { scope: "global", scopeId: null, key, commandId: prior },
        reason: "override"
      });
    }
    registry.keymaps.global.set(key, commandId);
    return registry;
  }
  if (!scopeId) {
    throw new Error(`Scope id required for scope: ${scope}`);
  }
  const scoped = registry.keymaps[scope];
  if (!scoped.has(scopeId)) {
    scoped.set(scopeId, new Map());
  }
  const map = scoped.get(scopeId);
  const prior = map.get(key);
  if (prior && prior !== commandId) {
    registry.keymapConflicts.push({
      id: `bind-conflict-${scope}-${scopeId}-${key}`,
      key,
      winner: { scope, scopeId, key, commandId },
      shadowed: { scope, scopeId, key, commandId: prior },
      reason: "override"
    });
  }
  map.set(key, commandId);
  return registry;
}

export function resolveKey(registry, key, ctx) {
  for (const scope of registry.precedence) {
    if (scope === "global") {
      const cmd = registry.keymaps.global.get(key);
      if (cmd) return cmd;
      continue;
    }
    const scopeId = ctx[`${scope}Id`];
    if (!scopeId) continue;
    const scoped = registry.keymaps[scope].get(scopeId);
    if (!scoped) continue;
    const cmd = scoped.get(key);
    if (cmd) return cmd;
  }
  return null;
}

export function resolveKeyWithTrace(registry, key, ctx = {}) {
  const trace = [];
  for (const scope of registry.precedence) {
    if (scope === "global") {
      const cmd = registry.keymaps.global.get(key) ?? null;
      trace.push({
        scope,
        scopeId: null,
        key,
        commandId: cmd,
        matched: Boolean(cmd),
        reason: cmd ? null : "unbound"
      });
      if (cmd) {
        return { commandId: cmd, trace };
      }
      continue;
    }
    const scopeId = ctx[`${scope}Id`] ?? null;
    if (!scopeId) {
      trace.push({
        scope,
        scopeId: null,
        key,
        commandId: null,
        matched: false,
        reason: "missing-scope-id"
      });
      continue;
    }
    const scoped = registry.keymaps[scope].get(scopeId);
    if (!scoped) {
      trace.push({
        scope,
        scopeId,
        key,
        commandId: null,
        matched: false,
        reason: "no-scope-map"
      });
      continue;
    }
    const cmd = scoped.get(key) ?? null;
    trace.push({
      scope,
      scopeId,
      key,
      commandId: cmd,
      matched: Boolean(cmd),
      reason: cmd ? null : "unbound"
    });
    if (cmd) {
      return { commandId: cmd, trace };
    }
  }
  return { commandId: null, trace };
}

function collectKeybindingEntries(registry) {
  const entries = [];
  if (registry?.keymaps?.global instanceof Map) {
    for (const [key, commandId] of registry.keymaps.global.entries()) {
      entries.push({ scope: "global", scopeId: null, key, commandId });
    }
  }
  for (const scope of ["task", "context", "widget"]) {
    const scoped = registry?.keymaps?.[scope];
    if (!(scoped instanceof Map)) continue;
    for (const [scopeId, map] of scoped.entries()) {
      if (!(map instanceof Map)) continue;
      for (const [key, commandId] of map.entries()) {
        entries.push({ scope, scopeId, key, commandId });
      }
    }
  }
  return entries;
}

export function analyzeKeybindingConflicts(registry, options = {}) {
  const entries = collectKeybindingEntries(registry);
  const byKey = new Map();
  for (const entry of entries) {
    const bucket = byKey.get(entry.key) ?? [];
    bucket.push(entry);
    byKey.set(entry.key, bucket);
  }
  const precedence = Array.isArray(registry?.precedence) ? registry.precedence : DEFAULT_PRECEDENCE;
  const indexOfScope = (scope) => {
    const index = precedence.indexOf(scope);
    return index === -1 ? precedence.length : index;
  };
  const conflicts = [];
  for (const [key, bucket] of byKey.entries()) {
    if (bucket.length < 2) continue;
    const sorted = [...bucket].sort((a, b) => {
      const scopeDiff = indexOfScope(a.scope) - indexOfScope(b.scope);
      if (scopeDiff !== 0) return scopeDiff;
      const idA = a.scopeId ?? "";
      const idB = b.scopeId ?? "";
      if (idA !== idB) return idA.localeCompare(idB);
      return String(a.commandId ?? "").localeCompare(String(b.commandId ?? ""));
    });
    const winner = sorted[0];
    for (let index = 1; index < sorted.length; index += 1) {
      const shadowed = sorted[index];
      const sameScopeId = winner.scope === shadowed.scope && winner.scopeId === shadowed.scopeId;
      const reason = sameScopeId ? "duplicate-binding" : "shadowed-by-precedence";
      conflicts.push({
        id: `key-conflict-${key}-${index}`,
        key,
        winner,
        shadowed,
        reason
      });
    }
  }
  if (Array.isArray(registry?.keymapConflicts) && registry.keymapConflicts.length > 0) {
    for (const conflict of registry.keymapConflicts) {
      conflicts.push({ ...conflict });
    }
  }
  if (options.key) {
    return conflicts.filter((entry) => entry.key === options.key);
  }
  return conflicts;
}

export function getCommand(registry, id) {
  return registry.commands.get(id) || null;
}

export function normalizeEnablement(result) {
  if (typeof result === "boolean") {
    return { enabled: result, reason: result ? null : "Disabled" };
  }
  if (Array.isArray(result) && result.length >= 2) {
    return { enabled: Boolean(result[0]), reason: result[1] ?? null };
  }
  if (result && typeof result === "object") {
    return {
      enabled: Boolean(result.enabled),
      reason: result.reason ?? null
    };
  }
  return { enabled: true, reason: null };
}

function normalizeCapabilities(value) {
  if (!value) return [];
  if (Array.isArray(value)) {
    return value.filter((entry) => typeof entry === "string" && entry.length > 0);
  }
  if (typeof value === "string") {
    return [value];
  }
  return [];
}

function resolveCapabilityState(ctx) {
  const capabilities = ctx?.capabilities ?? ctx?.state?.capabilities ?? null;
  return {
    safeMode: Boolean(capabilities?.safeMode),
    granted: Array.isArray(capabilities?.granted) ? capabilities.granted : []
  };
}

function checkCapabilities(ctx, required) {
  const resolved = resolveCapabilityState(ctx);
  if (resolved.safeMode) {
    return { enabled: false, reason: "Safe mode" };
  }
  for (const capability of required) {
    if (!resolved.granted.includes(capability)) {
      return { enabled: false, reason: `Missing capability: ${capability}` };
    }
  }
  return { enabled: true, reason: null };
}

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === "[object Object]";
}

function isTypedCommand(command) {
  return Boolean(Array.isArray(command?.args) && command.args.length > 0);
}

function resolveBeginnerState(ctx) {
  const beginner = ctx?.state?.customization?.effective?.beginnerMode ?? null;
  if (!beginner) {
    return {
      enabled: false,
      showExplanations: true,
      confirmAdvanced: true,
      hiddenCommandIds: [],
      forceVisibleCommandIds: []
    };
  }
  return {
    enabled: Boolean(beginner.enabled),
    showExplanations: beginner.showExplanations !== false,
    confirmAdvanced: beginner.confirmAdvanced !== false,
    hiddenCommandIds: Array.isArray(beginner.hiddenCommandIds) ? beginner.hiddenCommandIds : [],
    forceVisibleCommandIds: Array.isArray(beginner.forceVisibleCommandIds) ? beginner.forceVisibleCommandIds : []
  };
}

function resolveBeginnerPolicy(command, ctx) {
  const beginner = resolveBeginnerState(ctx);
  const metadata = isPlainObject(command?.metadata?.beginner) ? command.metadata.beginner : {};
  const hiddenIds = new Set(beginner.hiddenCommandIds);
  const forceVisibleIds = new Set(beginner.forceVisibleCommandIds);
  let hidden = Boolean(metadata.hidden) || hiddenIds.has(command?.id ?? "");
  if (forceVisibleIds.has(command?.id ?? "")) {
    hidden = false;
  }
  const advanced = Boolean(metadata.advanced);
  const requiresConfirmation = Boolean(metadata.confirm) || (beginner.confirmAdvanced && advanced);
  return {
    beginnerEnabled: beginner.enabled,
    hidden,
    requiresConfirmation,
    explanation:
      typeof metadata.explanation === "string" && metadata.explanation.length > 0
        ? metadata.explanation
        : null
  };
}

function isRuntimeScopedCommand(command) {
  if (!command || typeof command !== "object") return false;
  if (command.metadata?.runtime === true) return true;
  return typeof command.id === "string" && command.id.startsWith("runtime.");
}

function buildTypedInvocation(command, ctx = {}) {
  const invocation = isPlainObject(ctx.invocation) ? { ...ctx.invocation } : {};
  const args = {};
  const payload = isPlainObject(ctx.payload) ? ctx.payload : {};
  const item = isPlainObject(ctx.item) ? ctx.item : null;
  const payloadItem = isPlainObject(payload.item) ? payload.item : null;
  if (isPlainObject(payload.args)) {
    Object.assign(args, payload.args);
  }
  if (isPlainObject(ctx.args)) {
    Object.assign(args, ctx.args);
  }
  for (const arg of command.args ?? []) {
    if (!arg?.name || Object.prototype.hasOwnProperty.call(args, arg.name)) continue;
    if (Object.prototype.hasOwnProperty.call(ctx, arg.name)) {
      args[arg.name] = ctx[arg.name];
      continue;
    }
    if (Object.prototype.hasOwnProperty.call(payload, arg.name)) {
      args[arg.name] = payload[arg.name];
      continue;
    }
    if (item && Object.prototype.hasOwnProperty.call(item, arg.name)) {
      args[arg.name] = item[arg.name];
      continue;
    }
    if (payloadItem && Object.prototype.hasOwnProperty.call(payloadItem, arg.name)) {
      args[arg.name] = payloadItem[arg.name];
    }
  }
  return {
    ...invocation,
    commandId: invocation.commandId ?? command.id,
    args: { ...(invocation.args ?? {}), ...args },
    source: invocation.source ?? ctx.source ?? null,
    ts: invocation.ts ?? ctx.ts ?? null
  };
}

export function commandEnabled(registry, id, ctx) {
  const cmd = getCommand(registry, id);
  if (!cmd) {
    return { enabled: false, reason: "Unknown command" };
  }
  const beginner = resolveBeginnerPolicy(cmd, ctx);
  if (beginner.beginnerEnabled && beginner.hidden) {
    return { enabled: false, reason: "Hidden in Beginner Mode" };
  }
  const required = normalizeCapabilities(cmd.capability);
  if (required.length > 0) {
    const capabilityCheck = checkCapabilities(ctx, required);
    if (!capabilityCheck.enabled) {
      return capabilityCheck;
    }
  }
  if (isTypedCommand(cmd)) {
    const materialized = materializeInvocation(cmd, buildTypedInvocation(cmd, ctx), ctx);
    if (materialized.missing.length > 0) {
      return {
        enabled: false,
        reason: `Missing required args: ${materialized.missing.join(", ")}`
      };
    }
    if (!cmd.enabled) {
      return { enabled: true, reason: null };
    }
    return normalizeEnablement(
      cmd.enabled({
        ...ctx,
        invocation: materialized.invocation,
        args: materialized.invocation.args
      })
    );
  }
  if (!cmd.enabled) {
    return { enabled: true, reason: null };
  }
  return normalizeEnablement(cmd.enabled(ctx));
}

export function executeCommand(registry, id, ctx) {
  const cmd = getCommand(registry, id);
  if (!cmd) {
    return { ok: false, reason: "Unknown command" };
  }
  const beginner = resolveBeginnerPolicy(cmd, ctx);
  if (beginner.beginnerEnabled && beginner.hidden) {
    return { ok: false, reason: "Hidden in Beginner Mode" };
  }
  if (beginner.beginnerEnabled && beginner.requiresConfirmation && !ctx?.confirmBeginner) {
    return {
      ok: false,
      reason: "Confirmation required",
      confirmation: {
        commandId: id,
        explanation: beginner.explanation
      }
    };
  }
  const enablement = commandEnabled(registry, id, ctx);
  if (!enablement.enabled) {
    return { ok: false, reason: enablement.reason || "Disabled" };
  }
  if (isTypedCommand(cmd)) {
    const typed = executeTypedCommand(cmd, buildTypedInvocation(cmd, ctx), ctx);
    if (!typed.ok) {
      return {
        ok: false,
        reason: typed.reason ?? "Typed command failed",
        missing: typed.missing ?? [],
        invocation: typed.invocation ?? null
      };
    }
    if (isRuntimeScopedCommand(cmd) && ctx?.runtimeCommandClient?.dispatchTypedCommand) {
      const dispatched = ctx.runtimeCommandClient.dispatchTypedCommand(
        cmd,
        typed.invocation ?? {},
        {
          ...ctx,
          context: ctx.runtimeContext ?? ctx.context ?? {}
        }
      );
      if (!dispatched?.ok) {
        return {
          ok: false,
          reason: dispatched?.reason ?? "Runtime dispatch failed",
          invocation: typed.invocation ?? null
        };
      }
      return {
        ok: true,
        pending: true,
        runtimeDispatched: true,
        requestId: dispatched.requestId ?? null,
        promise: dispatched.promise ?? null,
        result: typed.result,
        invocation: typed.invocation ?? null
      };
    }
    return {
      ok: true,
      result: typed.result,
      invocation: typed.invocation ?? null
    };
  }
  if (!cmd.exec) {
    return { ok: true, result: null };
  }
  return { ok: true, result: cmd.exec(ctx) };
}

export function registerPresentationTranslator(registry, type, gesture, translator) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  if (typeof translator !== "function") {
    throw new Error("Translator must be a function");
  }
  const key = presentationKey(type, gesture);
  if (registry.presentationTranslators.has(key)) {
    throw new Error(`Translator already registered: ${key}`);
  }
  registry.presentationTranslators.set(key, translator);
  return registry;
}

export function resolvePresentationCommand(registry, presentation, gesture, ctx = {}) {
  if (!registry) return null;
  const type = presentation?.type ?? presentation?.presentationType ?? null;
  const key = presentationKey(type, gesture);
  const translator = registry.presentationTranslators.get(key);
  if (!translator) return null;
  const result = translator(presentation, gesture, ctx);
  if (!result) return null;
  if (typeof result === "string") {
    return { commandId: result, context: ctx };
  }
  if (typeof result === "object") {
    const commandId = result.commandId ?? result.id ?? null;
    if (!commandId) return null;
    return { commandId, context: result.context ?? ctx };
  }
  return null;
}

export function executePresentationCommand(registry, presentation, gesture, ctx = {}) {
  const resolved = resolvePresentationCommand(registry, presentation, gesture, ctx);
  if (!resolved?.commandId) {
    return { ok: false, reason: "No presentation command" };
  }
  return executeCommand(registry, resolved.commandId, {
    ...ctx,
    presentation
  });
}
