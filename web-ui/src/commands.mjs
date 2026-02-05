const DEFAULT_PRECEDENCE = ["global", "task", "context", "widget"];

export function createRegistry(precedence = DEFAULT_PRECEDENCE) {
  return {
    precedence,
    commands: new Map(),
    keymaps: {
      global: new Map(),
      task: new Map(),
      context: new Map(),
      widget: new Map()
    }
  };
}

export function registerCommand(registry, command) {
  if (!command || !command.id) {
    throw new Error("Command must have an id");
  }
  if (registry.commands.has(command.id)) {
    throw new Error(`Command already registered: ${command.id}`);
  }
  registry.commands.set(command.id, command);
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
