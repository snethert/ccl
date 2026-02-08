import {
  appendRecording,
  appendRecordingEntry,
  attachRecordingAnchor
} from "./state.mjs";

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

export function applyRuntimeMessage(state, message, options = {}) {
  if (!message || typeof message !== "object") {
    return { state, handled: false, errors: [{ kind: "message", message: "Invalid runtime message" }] };
  }
  if (message.kind === "runtime.output") {
    const result = applyRuntimeOutput(state, message.payload ?? {}, options);
    return { ...result, handled: true };
  }
  if (typeof options.onUnhandled === "function") {
    options.onUnhandled(message);
  }
  return { state, handled: false, errors: [] };
}
