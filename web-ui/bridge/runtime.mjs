const DEFAULT_VERSION = 1;

export const RUNTIME_BRIDGE_VERSION = DEFAULT_VERSION;

export const RUNTIME_MESSAGE_KINDS = Object.freeze({
  output: "runtime.output",
  commandInvoke: "command.invoke",
  commandResult: "command.result",
  commandError: "command.error",
  debuggerSnapshot: "debugger.snapshot",
  restart: "debugger.restart",
  inspector: "inspector.update",
  job: "job.update",
  log: "runtime.log"
});

const RUNTIME_KIND_SET = new Set(Object.values(RUNTIME_MESSAGE_KINDS));

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === "[object Object]";
}

function normalizeString(value, fallback = null) {
  if (typeof value === "string" && value.length > 0) return value;
  return fallback;
}

function normalizeInt(value, fallback = null) {
  if (Number.isInteger(value)) return value;
  return fallback;
}

function normalizeNumber(value, fallback = null) {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  return fallback;
}

function normalizeKind(kind, strict) {
  const value = normalizeString(kind, null);
  if (!value) return null;
  if (strict && !RUNTIME_KIND_SET.has(value)) {
    throw new Error(`Unsupported runtime message kind: ${value}`);
  }
  return value;
}

function normalizeError(value) {
  if (!value) return null;
  if (typeof value === "string") {
    return { code: null, message: value, details: null };
  }
  if (!isPlainObject(value)) {
    return { code: null, message: "Unknown error", details: null };
  }
  return {
    code: normalizeString(value.code, null),
    message: normalizeString(value.message, "Unknown error"),
    details: isPlainObject(value.details) ? { ...value.details } : null
  };
}

export function normalizeRuntimeMessage(message, options = {}) {
  if (!message || typeof message !== "object") {
    throw new Error("Runtime message must be an object");
  }
  const strictKinds = options.strictKinds === true;
  const version = normalizeInt(message.version, DEFAULT_VERSION);
  if (version !== DEFAULT_VERSION) {
    throw new Error(`Unsupported runtime bridge version: ${version}`);
  }
  const kind = normalizeKind(message.kind, strictKinds);
  if (!kind) {
    throw new Error("Runtime message kind is required");
  }
  const seq = normalizeInt(message.seq, null);
  if (seq === null || seq < 0) {
    throw new Error("Runtime message seq must be a non-negative integer");
  }
  const ts = normalizeNumber(message.ts, null);
  if (ts === null || ts < 0) {
    throw new Error("Runtime message ts must be a non-negative number");
  }
  return {
    version,
    kind,
    jobId: normalizeString(message.jobId ?? null, null),
    streamId: normalizeString(message.streamId ?? null, null),
    requestId: normalizeString(message.requestId ?? null, null),
    seq,
    ts,
    payload: "payload" in message ? message.payload : null,
    error: normalizeError(message.error)
  };
}

export function createRuntimeMessage(input, options = {}) {
  const now = typeof options.now === "function" ? options.now : () => Date.now();
  const message = {
    version: DEFAULT_VERSION,
    kind: input?.kind ?? null,
    jobId: input?.jobId ?? null,
    streamId: input?.streamId ?? null,
    requestId: input?.requestId ?? null,
    seq: Number.isInteger(input?.seq) ? input.seq : options.seq ?? 0,
    ts: typeof input?.ts === "number" ? input.ts : now(),
    payload: "payload" in (input ?? {}) ? input.payload : null,
    error: input?.error ?? null
  };
  return normalizeRuntimeMessage(message, { strictKinds: options.strictKinds });
}

export function encodeRuntimeMessage(message, options = {}) {
  const normalized = normalizeRuntimeMessage(message, { strictKinds: options.strictKinds });
  return JSON.stringify(normalized);
}

export function decodeRuntimeMessage(value, options = {}) {
  let parsed = value;
  if (typeof value === "string") {
    try {
      parsed = JSON.parse(value);
    } catch (err) {
      return { ok: false, error: `Invalid JSON: ${err?.message ?? String(err)}`, message: null };
    }
  }
  try {
    const normalized = normalizeRuntimeMessage(parsed, { strictKinds: options.strictKinds });
    return { ok: true, message: normalized, error: null };
  } catch (err) {
    return { ok: false, error: err?.message ?? String(err), message: null };
  }
}

export function isRuntimeMessage(value, options = {}) {
  const result = decodeRuntimeMessage(value, options);
  return result.ok;
}
