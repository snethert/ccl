import { createRuntimeMessage, RUNTIME_MESSAGE_KINDS } from "../bridge/runtime.mjs";
import { materializeInvocation } from "./typed-commands.mjs";
import { SAB_RING_TRANSPORT } from "./runtime-transport.mjs";

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function resolveRuntimeCommandId(commandSpec) {
  const metadata = commandSpec?.metadata ?? null;
  if (typeof metadata?.runtimeCommandId === "string" && metadata.runtimeCommandId.length > 0) {
    return metadata.runtimeCommandId;
  }
  if (isPlainObject(metadata?.runtime) && typeof metadata.runtime.commandId === "string") {
    return metadata.runtime.commandId;
  }
  return null;
}

const _textEncoder = typeof TextEncoder !== "undefined" ? new TextEncoder() : null;

function encodeUtf8(text) {
  if (_textEncoder) return _textEncoder.encode(String(text));
  const s = String(text);
  const out = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i) & 0xff;
  return out;
}

function encodeLispString(text) {
  const s = String(text);
  let out = "\"";
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    switch (ch) {
      case "\\":
        out += "\\\\";
        break;
      case "\"":
        out += "\\\"";
        break;
      case "\n":
        out += "\\n";
        break;
      case "\r":
        out += "\\r";
        break;
      case "\t":
        out += "\\t";
        break;
      default:
        out += ch;
        break;
    }
  }
  out += "\"";
  return out;
}

function encodeLispForm(value) {
  if (value === null || value === undefined) return ":null";
  if (value === true) return ":true";
  if (value === false) return ":false";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return encodeLispString(String(value));
    return String(value);
  }
  if (typeof value === "string") return encodeLispString(value);
  if (Array.isArray(value)) {
    return `(${value.map((entry) => encodeLispForm(entry)).join(" ")})`;
  }
  if (typeof value === "object") {
    const pairs = [];
    for (const [key, nested] of Object.entries(value)) {
      pairs.push(`(${encodeLispString(key)} . ${encodeLispForm(nested)})`);
    }
    return `(${pairs.join(" ")})`;
  }
  return encodeLispString(String(value));
}

function encodeRuntimeCommandFrameFromEnvelope(envelope) {
  const payload = envelope?.payload ?? {};
  const invocation = payload?.invocation ?? {};
  const invocationId = typeof invocation?.id === "string" && invocation.id.length > 0 ? invocation.id : null;
  const commandId = typeof invocation?.commandId === "string" && invocation.commandId.length > 0 ? invocation.commandId : null;
  if (!invocationId || !commandId) {
    return null;
  }
  const argsForm = encodeLispForm(invocation?.args ?? {});
  const contextForm = encodeLispForm(payload?.context ?? {});
  const invocationIdBytes = encodeUtf8(invocationId);
  const commandIdBytes = encodeUtf8(commandId);
  const argsBytes = encodeUtf8(argsForm);
  const contextBytes = encodeUtf8(contextForm);
  const headerSize = 24;
  const totalSize =
    headerSize +
    invocationIdBytes.length +
    commandIdBytes.length +
    argsBytes.length +
    contextBytes.length;
  const buffer = new ArrayBuffer(totalSize);
  const dv = new DataView(buffer);
  dv.setUint32(0, 1, true); // frame_version
  dv.setUint32(4, invocationIdBytes.length, true);
  dv.setUint32(8, commandIdBytes.length, true);
  dv.setUint32(12, argsBytes.length, true);
  dv.setUint32(16, contextBytes.length, true);
  dv.setUint32(20, 0, true);
  const out = new Uint8Array(buffer);
  let offset = headerSize;
  out.set(invocationIdBytes, offset);
  offset += invocationIdBytes.length;
  out.set(commandIdBytes, offset);
  offset += commandIdBytes.length;
  out.set(argsBytes, offset);
  offset += argsBytes.length;
  out.set(contextBytes, offset);
  return {
    frame: out,
    invocationId,
    commandId
  };
}

function resolveCommandTransport(options = {}) {
  const raw = options.commandTransport ?? null;
  if (!raw) {
    throw new Error("Runtime command transport is required: commandTransport.sab_ring_v1");
  }
  if (raw.transport !== SAB_RING_TRANSPORT) {
    throw new Error(`Unsupported runtime command transport: ${String(raw.transport)}`);
  }
  if (typeof raw.enqueueFrame === "function") {
    return {
      transport: SAB_RING_TRANSPORT,
      enqueueFrame: raw.enqueueFrame
    };
  }
  if (raw.ring && typeof raw.ring.enqueueFrame === "function") {
    return {
      transport: SAB_RING_TRANSPORT,
      enqueueFrame: (frame, meta) => raw.ring.enqueueFrame(frame, meta)
    };
  }
  if (typeof raw.enqueue === "function") {
    return {
      transport: SAB_RING_TRANSPORT,
      enqueueFrame: raw.enqueue
    };
  }
  throw new Error("commandTransport.sab_ring_v1 requires enqueueFrame(frame) or ring.enqueueFrame(frame)");
}

export function createRuntimeCommandClient(options = {}) {
  const commandTransport = resolveCommandTransport(options);
  const now = typeof options.now === "function" ? options.now : () => Date.now();
  const streamId = typeof options.streamId === "string" && options.streamId.length > 0 ? options.streamId : "commands";
  const timeoutMs = Number.isInteger(options.timeoutMs) ? Math.max(0, options.timeoutMs) : 30000;

  let nextRequestSeq = 1;
  let nextMessageSeq = 1;
  const pendingByRequestId = new Map();
  const requestByInvocationId = new Map();

  function allocateRequestId(invocationId = null) {
    if (typeof invocationId === "string" && invocationId.length > 0) {
      return `req-${invocationId}`;
    }
    const id = `req-${nextRequestSeq}`;
    nextRequestSeq += 1;
    return id;
  }

  function clearPending(entry) {
    if (!entry) return;
    if (entry.timeoutHandle) {
      clearTimeout(entry.timeoutHandle);
    }
    pendingByRequestId.delete(entry.requestId);
    if (entry.invocationId) {
      requestByInvocationId.delete(entry.invocationId);
    }
  }

  function dispatchTypedCommand(commandSpec, invocation = {}, ctx = {}) {
    const materialized = materializeInvocation(commandSpec, invocation, ctx);
    if (materialized.missing.length > 0) {
      return {
        ok: false,
        reason: "Missing required args",
        missing: materialized.missing,
        invocation: materialized.invocation
      };
    }

    const sourceInvocationId =
      typeof materialized.invocation?.id === "string" && materialized.invocation.id.length > 0
        ? materialized.invocation.id
        : null;
    const requestId = allocateRequestId(sourceInvocationId);
    const runtimeInvocationId = sourceInvocationId ?? requestId;
    const runtimeCommandId = resolveRuntimeCommandId(materialized.spec);
    const runtimeInvocation = runtimeCommandId
      ? { ...materialized.invocation, id: runtimeInvocationId, commandId: runtimeCommandId }
      : { ...materialized.invocation, id: runtimeInvocationId };

    let resolvePromise;
    let rejectPromise;
    const promise = new Promise((resolve, reject) => {
      resolvePromise = resolve;
      rejectPromise = reject;
    });

    const pending = {
      requestId,
      invocationId: runtimeInvocationId,
      commandId: runtimeInvocation.commandId ?? materialized.spec.id,
      clientCommandId: materialized.spec.id,
      resolve: resolvePromise,
      reject: rejectPromise,
      timeoutHandle: null
    };
    if (timeoutMs > 0) {
      pending.timeoutHandle = setTimeout(() => {
        clearPending(pending);
        rejectPromise({
          ok: false,
          requestId,
          invocationId: runtimeInvocationId,
          commandId: runtimeInvocation.commandId ?? materialized.spec.id,
          clientCommandId: materialized.spec.id,
          reason: "Runtime command timeout"
        });
      }, timeoutMs);
    }

    const message = createRuntimeMessage(
      {
        kind: RUNTIME_MESSAGE_KINDS.commandInvoke,
        jobId: ctx.jobId ?? null,
        streamId,
        requestId,
        seq: nextMessageSeq++,
        ts: now(),
        payload: {
          invocation: runtimeInvocation,
          context: isPlainObject(ctx.context) ? { ...ctx.context } : {}
        },
        error: null
      },
      { strictKinds: true, now }
    );

    pendingByRequestId.set(requestId, pending);
    if (runtimeInvocationId) {
      requestByInvocationId.set(runtimeInvocationId, requestId);
    }

    try {
      const dispatchMeta = {
        requestId,
        invocation: runtimeInvocation,
        commandId: runtimeInvocation.commandId ?? materialized.spec.id,
        clientCommandId: materialized.spec.id,
        transport: commandTransport.transport
      };
      const encoded = encodeRuntimeCommandFrameFromEnvelope(message);
      if (!encoded) {
        throw new Error("command.invoke payload missing invocation id or command id");
      }
      const enqueueResult = commandTransport.enqueueFrame(encoded.frame, {
        ...dispatchMeta,
        envelope: message
      });
      if (enqueueResult && enqueueResult.ok === false) {
        throw new Error(enqueueResult.reason ?? "Runtime command SAB enqueue failed");
      }
    } catch (err) {
      clearPending(pending);
      rejectPromise({
        ok: false,
        requestId,
        invocationId: runtimeInvocationId,
        commandId: runtimeInvocation.commandId ?? materialized.spec.id,
        clientCommandId: materialized.spec.id,
        reason: err?.message ?? String(err)
      });
      return { ok: false, reason: err?.message ?? String(err), invocation: materialized.invocation };
    }

    return {
      ok: true,
      transport: commandTransport.transport,
      requestId,
      invocation: materialized.invocation,
      runtimeInvocation,
      message,
      promise
    };
  }

  function getPendingByMessage(message) {
    const directRequestId =
      typeof message?.requestId === "string" && message.requestId.length > 0 ? message.requestId : null;
    if (directRequestId && pendingByRequestId.has(directRequestId)) {
      return pendingByRequestId.get(directRequestId);
    }
    const invocationId =
      typeof message?.payload?.invocationId === "string" && message.payload.invocationId.length > 0
        ? message.payload.invocationId
        : null;
    if (invocationId && requestByInvocationId.has(invocationId)) {
      const requestId = requestByInvocationId.get(invocationId);
      if (requestId && pendingByRequestId.has(requestId)) {
        return pendingByRequestId.get(requestId);
      }
    }
    return null;
  }

  function handleRuntimeMessage(message) {
    const kind = message?.kind ?? null;
    if (kind !== RUNTIME_MESSAGE_KINDS.commandResult && kind !== RUNTIME_MESSAGE_KINDS.commandError) {
      return { handled: false, reason: "Unsupported runtime command message kind" };
    }
    const pending = getPendingByMessage(message);
    if (!pending) {
      return { handled: false, reason: "No pending runtime command request" };
    }
    clearPending(pending);
    if (kind === RUNTIME_MESSAGE_KINDS.commandResult) {
      pending.resolve({
        ok: true,
        requestId: pending.requestId,
        invocationId: pending.invocationId,
        commandId: pending.commandId,
        clientCommandId: pending.clientCommandId,
        payload: message?.payload ?? null,
        message
      });
      return { handled: true, status: "resolved", requestId: pending.requestId };
    }
    pending.reject({
      ok: false,
      requestId: pending.requestId,
      invocationId: pending.invocationId,
      commandId: pending.commandId,
      clientCommandId: pending.clientCommandId,
      payload: message?.payload ?? null,
      message
    });
    return { handled: true, status: "rejected", requestId: pending.requestId };
  }

  function cancelAll(reason = "Runtime command client reset") {
    for (const pending of pendingByRequestId.values()) {
      clearPending(pending);
      pending.reject({
        ok: false,
        requestId: pending.requestId,
        invocationId: pending.invocationId,
        commandId: pending.commandId,
        clientCommandId: pending.clientCommandId,
        reason
      });
    }
  }

  return {
    dispatchTypedCommand,
    handleRuntimeMessage,
    cancelAll,
    pendingCount: () => pendingByRequestId.size
  };
}
