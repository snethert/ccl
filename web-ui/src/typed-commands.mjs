export const ARG_TYPES = Object.freeze([
  "string",
  "number",
  "boolean",
  "symbol",
  "package",
  "file",
  "location",
  "presentation",
  "selection",
  "frame",
  "binding",
  "place",
  "command",
  "list",
  "map"
]);
export const TYPED_COMMAND_MODEL_VERSION = "0";

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === "[object Object]";
}

function normalizeString(value, fallback = null) {
  if (typeof value === "string" && value.length > 0) return value;
  return fallback;
}

function normalizeArray(value) {
  return Array.isArray(value) ? [...value] : [];
}

function normalizeEnablement(result) {
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

function resolveDefaultFromSource(source, ctx) {
  switch (source) {
    case "selection":
      return ctx.selection ?? ctx.state?.selection ?? null;
    case "presentation":
      return ctx.presentation ?? null;
    case "lastResult":
      return ctx.lastResult ?? ctx.invocation?.result ?? null;
    case "package":
      return ctx.package ?? ctx.transcriptContext?.package ?? ctx.recording?.input?.package ?? null;
    case "lastDefinition":
      return ctx.lastDefinition ?? null;
    case "sourceLocation":
      return ctx.sourceLocation ?? ctx.lastDefinition?.location ?? null;
    default:
      return undefined;
  }
}

function coerceAndValidateArg(arg, value, ctx) {
  let next = value;
  if (arg.coerce) {
    next = arg.coerce(value, { arg, ctx });
  }
  if (arg.validate) {
    const validation = arg.validate(next, { arg, ctx });
    if (typeof validation === "boolean" && !validation) {
      return { ok: false, value: next };
    }
    if (validation && typeof validation === "object" && validation.ok === false) {
      return { ok: false, value: next, reason: validation.reason ?? null };
    }
  }
  return { ok: true, value: next };
}

export function normalizeArgSpec(arg) {
  if (!arg || typeof arg !== "object") {
    throw new Error("Argument spec must be an object");
  }
  const type = ARG_TYPES.includes(arg.type) ? arg.type : "string";
  const defaultFrom = normalizeArray(arg.defaultFrom).filter((entry) => typeof entry === "string");
  return {
    name: normalizeString(arg.name, null),
    type,
    required: Boolean(arg.required),
    default: arg.default ?? null,
    defaultFrom,
    coerce: typeof arg.coerce === "function" ? arg.coerce : null,
    validate: typeof arg.validate === "function" ? arg.validate : null
  };
}

export function normalizeCommandSpec(command) {
  if (!command || typeof command !== "object") {
    throw new Error("Command spec must be an object");
  }
  const args = normalizeArray(command.args).map(normalizeArgSpec);
  return {
    id: normalizeString(command.id, null),
    title: normalizeString(command.title, command.id ?? null),
    doc: normalizeString(command.doc, null),
    scope: normalizeString(command.scope, "context"),
    capability: normalizeString(command.capability, null),
    args,
    enabled: typeof command.enabled === "function" ? command.enabled : null,
    exec: typeof command.exec === "function" ? command.exec : null,
    metadata: isPlainObject(command.metadata) ? { ...command.metadata } : {}
  };
}

export function normalizeInvocation(invocation) {
  if (!invocation || typeof invocation !== "object") {
    throw new Error("Invocation must be an object");
  }
  return {
    id: normalizeString(invocation.id, null),
    commandId: normalizeString(invocation.commandId, null),
    args: isPlainObject(invocation.args) ? { ...invocation.args } : {},
    defaults: isPlainObject(invocation.defaults) ? { ...invocation.defaults } : {},
    ts: Number.isInteger(invocation.ts) ? invocation.ts : null,
    source: normalizeString(invocation.source, null),
    result: invocation.result ?? null
  };
}

export function validateInvocation(invocation, commandSpec) {
  const normalized = normalizeInvocation(invocation);
  const spec = normalizeCommandSpec(commandSpec);
  if (!spec.id || spec.id !== normalized.commandId) {
    return { ok: false, reason: "Command mismatch", missing: [] };
  }
  const missing = [];
  for (const arg of spec.args) {
    if (!arg.required) continue;
    if (normalized.args[arg.name] === undefined || normalized.args[arg.name] === null) {
      missing.push(arg.name);
    }
  }
  return { ok: missing.length === 0, missing };
}

export function resolveArgumentDefaults(commandSpec, args = {}, ctx = {}) {
  const spec = normalizeCommandSpec(commandSpec);
  const resolvedArgs = isPlainObject(args) ? { ...args } : {};
  const defaults = {};
  const missing = [];

  for (const arg of spec.args) {
    const hasValue = !(resolvedArgs[arg.name] === undefined || resolvedArgs[arg.name] === null);
    if (!hasValue) {
      let candidate = undefined;
      let source = null;

      for (const sourceKey of arg.defaultFrom) {
        const value = resolveDefaultFromSource(sourceKey, ctx);
        if (value !== undefined && value !== null) {
          candidate = value;
          source = sourceKey;
          break;
        }
      }

      if ((candidate === undefined || candidate === null) && arg.default !== null) {
        candidate = arg.default;
        source = "default";
      }

      if (candidate !== undefined && candidate !== null) {
        const normalized = coerceAndValidateArg(arg, candidate, ctx);
        if (normalized.ok) {
          resolvedArgs[arg.name] = normalized.value;
          defaults[arg.name] = { source };
        }
      }
    }

    if (arg.required && (resolvedArgs[arg.name] === undefined || resolvedArgs[arg.name] === null)) {
      missing.push(arg.name);
    }
  }

  return { args: resolvedArgs, defaults, missing };
}

export function materializeInvocation(commandSpec, invocation, ctx = {}) {
  const spec = normalizeCommandSpec(commandSpec);
  const normalized = normalizeInvocation(invocation ?? { commandId: spec.id });
  const commandId = normalized.commandId ?? spec.id;
  const resolved = resolveArgumentDefaults(spec, normalized.args, ctx);
  return {
    spec,
    missing: resolved.missing,
    invocation: {
      ...normalized,
      commandId,
      args: resolved.args,
      defaults: {
        ...resolved.defaults,
        ...(normalized.defaults ?? {})
      }
    }
  };
}

export function executeTypedCommand(commandSpec, invocation, ctx = {}) {
  const materialized = materializeInvocation(commandSpec, invocation, ctx);
  if (materialized.missing.length > 0) {
    return {
      ok: false,
      reason: "Missing required args",
      missing: materialized.missing,
      invocation: materialized.invocation
    };
  }

  if (materialized.spec.enabled) {
    const enablement = normalizeEnablement(
      materialized.spec.enabled({
        ...ctx,
        invocation: materialized.invocation,
        args: materialized.invocation.args
      })
    );
    if (!enablement.enabled) {
      return {
        ok: false,
        reason: enablement.reason ?? "Disabled",
        invocation: materialized.invocation
      };
    }
  }

  if (!materialized.spec.exec) {
    return {
      ok: true,
      result: null,
      invocation: materialized.invocation
    };
  }

  const result = materialized.spec.exec({
    ...ctx,
    invocation: materialized.invocation,
    args: materialized.invocation.args
  });
  return {
    ok: true,
    result,
    invocation: {
      ...materialized.invocation,
      result
    }
  };
}
