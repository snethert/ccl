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
  return {
    id: command.id,
    title: command.title ?? command.id,
    doc: command.doc ?? null,
    scope: command.scope ?? "global",
    enabled: command.enabled ?? null,
    exec: command.exec ?? null,
    metadata: command.metadata ?? {}
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
  scoped.get(scopeId).set(key, commandId);
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

export function commandEnabled(registry, id, ctx) {
  const cmd = getCommand(registry, id);
  if (!cmd) {
    return { enabled: false, reason: "Unknown command" };
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
  const enablement = commandEnabled(registry, id, ctx);
  if (!enablement.enabled) {
    return { ok: false, reason: enablement.reason || "Disabled" };
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
