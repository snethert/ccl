import { handleCommandResultEffects } from "../src/command-effects.mjs";

function defaultClipboardWrite(text) {
  if (typeof navigator === "object" && navigator?.clipboard && typeof navigator.clipboard.writeText === "function") {
    return navigator.clipboard.writeText(text);
  }
  return null;
}

export function createCommandEffectBridge(options = {}) {
  const writeClipboard = typeof options.writeClipboard === "function" ? options.writeClipboard : defaultClipboardWrite;
  const dispatchRuntime = typeof options.dispatchRuntime === "function" ? options.dispatchRuntime : null;
  const onUnhandled = typeof options.onUnhandled === "function" ? options.onUnhandled : null;

  const handlers = {
    clipboardWrite: ({ text, output, meta }) => writeClipboard(text, { output, meta }),
    runtimeDispatch: dispatchRuntime
      ? ({ output, meta }) => dispatchRuntime(output, meta)
      : null,
    unhandled: onUnhandled
      ? ({ output, meta }) => onUnhandled(output, meta)
      : null
  };

  return {
    commandEffectHandlers: handlers,
    handle: (result, meta = {}) => handleCommandResultEffects(result, handlers, meta)
  };
}
