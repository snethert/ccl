function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

export function extractCommandOutput(result) {
  if (!result || result.ok !== true) return null;
  const value = result.result ?? null;
  if (!isPlainObject(value)) return null;
  const output = value.output ?? null;
  return isPlainObject(output) ? output : null;
}

export function formatClipboardText(output) {
  if (!isPlainObject(output)) return null;
  if (output.kind === "form") {
    return typeof output.text === "string" ? output.text : "";
  }
  if (output.kind === "form+context") {
    const text = typeof output.text === "string" ? output.text : "";
    const pkg = output.package ? `; package: ${output.package}\n` : "";
    const recording = output.recordingId ? `; recording: ${output.recordingId}\n` : "";
    return `${pkg}${recording}${text}`;
  }
  return null;
}

export function dispatchCommandOutput(output, handlers = {}, meta = {}) {
  if (!isPlainObject(output) || typeof output.kind !== "string") {
    return { handled: false, channel: null, reason: "No output" };
  }

  if (output.kind === "form" || output.kind === "form+context") {
    if (typeof handlers.clipboardWrite !== "function") {
      return { handled: false, channel: "clipboard", reason: "No clipboard handler" };
    }
    const text = formatClipboardText(output);
    handlers.clipboardWrite({ text: text ?? "", output, meta });
    return { handled: true, channel: "clipboard", reason: null };
  }

  if (output.kind === "recording.replay" || output.kind === "recording.rerun") {
    if (typeof handlers.runtimeDispatch !== "function") {
      return { handled: false, channel: "runtime", reason: "No runtime handler" };
    }
    handlers.runtimeDispatch({ output, meta });
    return { handled: true, channel: "runtime", reason: null };
  }

  if (typeof handlers.unhandled === "function") {
    handlers.unhandled({ output, meta });
    return { handled: true, channel: "unhandled", reason: null };
  }

  return { handled: false, channel: null, reason: "Unhandled output kind" };
}

export function handleCommandResultEffects(result, handlers = {}, meta = {}) {
  const output = extractCommandOutput(result);
  if (!output) {
    return { handled: false, channel: null, reason: "No command effect output" };
  }
  return dispatchCommandOutput(output, handlers, meta);
}
