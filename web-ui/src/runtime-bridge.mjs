import {
  appendRecording,
  appendRecordingEntry,
  attachRecordingAnchor,
  patchCommandInvocation,
  upsertCommandInvocation,
  upsertRuntimeDebuggerSnapshot,
  applyRuntimeDebuggerRestartUpdate
} from "./state.mjs";
import { dispatchCommandOutput } from "./command-effects.mjs";

function normalizePayloadList(value, fallbackItem) {
  if (Array.isArray(value)) return value;
  if (value) return [value];
  if (fallbackItem) return [fallbackItem];
  return [];
}

export function applyRuntimeOutput(state, payload = {}, options = {}) {
  let nextState = state;
  const errors = [];
  const recordings = normalizePayloadList(payload.recordings, payload.recording);
  const entries = normalizePayloadList(payload.entries, payload.entry);
  const anchors = normalizePayloadList(payload.anchors, payload.anchor);
  const onError = typeof options.onError === "function" ? options.onError : null;

  recordings.forEach((recording) => {
    try {
      nextState = appendRecording(nextState, recording);
    } catch (err) {
      const message = err?.message ?? String(err);
      errors.push({ kind: "recording", message, recording });
      if (onError) onError({ kind: "recording", message, recording });
    }
  });

  entries.forEach((entry) => {
    try {
      nextState = appendRecordingEntry(nextState, entry);
    } catch (err) {
      const message = err?.message ?? String(err);
      errors.push({ kind: "entry", message, entry });
      if (onError) onError({ kind: "entry", message, entry });
    }
  });

  anchors.forEach((anchor) => {
    try {
      nextState = attachRecordingAnchor(nextState, anchor);
    } catch (err) {
      const message = err?.message ?? String(err);
      errors.push({ kind: "anchor", message, anchor });
      if (onError) onError({ kind: "anchor", message, anchor });
    }
  });

  return { state: nextState, errors };
}

function normalizeInvocationId(message, payload = {}) {
  if (typeof payload?.invocationId === "string" && payload.invocationId.length > 0) return payload.invocationId;
  if (typeof message?.requestId === "string" && message.requestId.length > 0) return message.requestId;
  return null;
}

function settleCommandClient(message, options = {}) {
  const client = options.commandClient ?? null;
  if (!client || typeof client.handleRuntimeMessage !== "function") return null;
  try {
    return client.handleRuntimeMessage(message);
  } catch (_err) {
    return null;
  }
}

export function applyRuntimeCommandResult(state, message, options = {}) {
  const payload = message?.payload ?? {};
  const invocationId = normalizeInvocationId(message, payload);
  let nextState = state;
  const errors = [];
  if (invocationId) {
    const durationMs = Number.isInteger(payload?.durationMs) ? payload.durationMs : null;
    const diagnostics = Array.isArray(payload?.diagnostics) ? payload.diagnostics : [];
    const resultPayload = {
      ok: true,
      value: payload?.result ?? null,
      diagnostics,
      durationMs,
      status: "succeeded"
    };
    const existing =
      Array.isArray(nextState.commandHistory) &&
      nextState.commandHistory.some((entry) => entry?.id === invocationId);
    if (existing || !(typeof payload?.commandId === "string" && payload.commandId.length > 0)) {
      nextState = patchCommandInvocation(nextState, invocationId, {
        result: resultPayload
      });
    } else {
      nextState = upsertCommandInvocation(nextState, {
        id: invocationId,
        commandId: payload.commandId,
        ts: Number.isInteger(message?.ts) ? message.ts : null,
        result: resultPayload
      });
    }
  }

  const output = payload?.effects?.output ?? null;
  if (output && options.commandEffectHandlers && typeof options.commandEffectHandlers === "object") {
    const dispatchResult = dispatchCommandOutput(output, options.commandEffectHandlers, {
      kind: "runtime.command.result",
      invocationId
    });
    if (!dispatchResult.handled && dispatchResult.reason) {
      errors.push({ kind: "command.effect", message: dispatchResult.reason, output });
    }
  }

  settleCommandClient(message, options);
  if (typeof options.onCommandResult === "function") {
    options.onCommandResult({ message, payload, invocationId });
  }
  return { state: nextState, errors };
}

export function applyRuntimeCommandError(state, message, options = {}) {
  const payload = message?.payload ?? {};
  const invocationId = normalizeInvocationId(message, payload);
  let nextState = state;
  if (invocationId) {
    const diagnostics = Array.isArray(payload?.diagnostics) ? payload.diagnostics : [];
    const resultPayload = {
      ok: false,
      phase: payload?.phase ?? "execute",
      retryable: Boolean(payload?.retryable),
      condition: payload?.condition ?? null,
      diagnostics,
      status: "failed"
    };
    const existing =
      Array.isArray(nextState.commandHistory) &&
      nextState.commandHistory.some((entry) => entry?.id === invocationId);
    if (existing || !(typeof payload?.commandId === "string" && payload.commandId.length > 0)) {
      nextState = patchCommandInvocation(nextState, invocationId, {
        result: resultPayload
      });
    } else {
      nextState = upsertCommandInvocation(nextState, {
        id: invocationId,
        commandId: payload.commandId,
        ts: Number.isInteger(message?.ts) ? message.ts : null,
        result: resultPayload
      });
    }
  }
  settleCommandClient(message, options);
  if (typeof options.onCommandError === "function") {
    options.onCommandError({ message, payload, invocationId });
  }
  return { state: nextState, errors: [] };
}

export function applyRuntimeDebuggerSnapshot(state, message, options = {}) {
  try {
    const nextState = upsertRuntimeDebuggerSnapshot(state, message?.payload ?? {}, {
      ts: Number.isInteger(message?.ts) ? message.ts : null,
      taskId: options.taskId ?? null,
      openDebugger: options.openDebuggerOnDebuggerSnapshot !== false
    });
    if (typeof options.onDebuggerSnapshot === "function") {
      options.onDebuggerSnapshot({ message, payload: message?.payload ?? null });
    }
    return { state: nextState, errors: [] };
  } catch (err) {
    const messageText = err?.message ?? String(err);
    if (typeof options.onError === "function") {
      options.onError({ kind: "debugger.snapshot", message: messageText, payload: message?.payload ?? null });
    }
    return { state, errors: [{ kind: "debugger.snapshot", message: messageText }] };
  }
}

export function applyRuntimeDebuggerRestart(state, message, options = {}) {
  try {
    const nextState = applyRuntimeDebuggerRestartUpdate(state, message?.payload ?? {}, {
      ts: Number.isInteger(message?.ts) ? message.ts : null,
      taskId: options.taskId ?? null
    });
    if (typeof options.onDebuggerRestart === "function") {
      options.onDebuggerRestart({ message, payload: message?.payload ?? null });
    }
    return { state: nextState, errors: [] };
  } catch (err) {
    const messageText = err?.message ?? String(err);
    if (typeof options.onError === "function") {
      options.onError({ kind: "debugger.restart", message: messageText, payload: message?.payload ?? null });
    }
    return { state, errors: [{ kind: "debugger.restart", message: messageText }] };
  }
}

export function applyRuntimeMessage(state, message, options = {}) {
  if (!message || typeof message !== "object") {
    return { state, handled: false, errors: [{ kind: "message", message: "Invalid runtime message" }] };
  }
  if (message.kind === "runtime.output") {
    const result = applyRuntimeOutput(state, message.payload ?? {}, options);
    return { ...result, handled: true };
  }
  if (message.kind === "command.result") {
    const result = applyRuntimeCommandResult(state, message, options);
    return { ...result, handled: true };
  }
  if (message.kind === "command.error") {
    const result = applyRuntimeCommandError(state, message, options);
    return { ...result, handled: true };
  }
  if (message.kind === "debugger.snapshot") {
    const result = applyRuntimeDebuggerSnapshot(state, message, options);
    return { ...result, handled: true };
  }
  if (message.kind === "debugger.restart") {
    const result = applyRuntimeDebuggerRestart(state, message, options);
    return { ...result, handled: true };
  }
  if (typeof options.onUnhandled === "function") {
    options.onUnhandled(message);
  }
  return { state, handled: false, errors: [] };
}
