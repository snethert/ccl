import { createRuntimeMessage, RUNTIME_MESSAGE_KINDS } from "../bridge/runtime.mjs";
import { materializeInvocation } from "./typed-commands.mjs";

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

export function createRuntimeCommandClient(options = {}) {
  const send = typeof options.send === "function" ? options.send : null;
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
    if (!send) {
      return { ok: false, reason: "Runtime command client send handler is missing" };
    }

    const materialized = materializeInvocation(commandSpec, invocation, ctx);
    if (materialized.missing.length > 0) {
      return {
        ok: false,
        reason: "Missing required args",
        missing: materialized.missing,
        invocation: materialized.invocation
      };
    }

    const invocationId =
      typeof materialized.invocation?.id === "string" && materialized.invocation.id.length > 0
        ? materialized.invocation.id
        : null;
    const runtimeCommandId = resolveRuntimeCommandId(materialized.spec);
    const runtimeInvocation = runtimeCommandId
      ? { ...materialized.invocation, commandId: runtimeCommandId }
      : materialized.invocation;
    const requestId = allocateRequestId(invocationId);

    let resolvePromise;
    let rejectPromise;
    const promise = new Promise((resolve, reject) => {
      resolvePromise = resolve;
      rejectPromise = reject;
    });

    const pending = {
      requestId,
      invocationId,
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
          invocationId,
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
    if (invocationId) {
      requestByInvocationId.set(invocationId, requestId);
    }

    try {
      send(message, {
        requestId,
        invocation: runtimeInvocation,
        commandId: runtimeInvocation.commandId ?? materialized.spec.id,
        clientCommandId: materialized.spec.id
      });
    } catch (err) {
      clearPending(pending);
      rejectPromise({
        ok: false,
        requestId,
        invocationId,
        commandId: runtimeInvocation.commandId ?? materialized.spec.id,
        clientCommandId: materialized.spec.id,
        reason: err?.message ?? String(err)
      });
      return { ok: false, reason: err?.message ?? String(err), invocation: materialized.invocation };
    }

    return {
      ok: true,
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
