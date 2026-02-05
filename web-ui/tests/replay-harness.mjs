import { serializeState } from "./snapshot.mjs";
import { validateEvents } from "./event-log.mjs";
import { setFocus } from "../src/focus.mjs";
import { executeCommand } from "../src/commands.mjs";
import { makeContext } from "../src/context.mjs";

function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

function normalizeReplayOptions(options) {
  if (options && typeof options === "object") {
    if (options.handlers) {
      return options;
    }
    const values = Object.values(options);
    if (values.length > 0 && values.every((value) => typeof value === "function")) {
      return { handlers: options };
    }
    if ("registry" in options) {
      return { handlers: null, registry: options.registry };
    }
  }
  return { handlers: null, registry: null };
}

export function defaultHandlers(registry = null) {
  return {
    "state:init": (state, payload) => ({ ...state, ...payload }),
    "focus:set": (state, payload, event) =>
      setFocus(state, payload.target ?? null, payload.reason, event?.seq ?? null),
    "command:execute": (state, payload) => {
      if (!registry) {
        throw new Error("Command registry required for command execution");
      }
      const ctx = makeContext(state, payload.context ?? {});
      const execCtx = { ...ctx, payload };
      const result = executeCommand(registry, payload.id, execCtx);
      if (!result.ok) {
        throw new Error(result.reason || `Command failed: ${payload.id}`);
      }
      if (result.result && result.result.state) {
        return result.result.state;
      }
      return state;
    },
    "command:enable": (state, payload) => {
      const commands = { ...(state.commands || {}) };
      commands[payload.id] = { enabled: true, reason: null };
      return { ...state, commands };
    },
    "command:disable": (state, payload) => {
      const commands = { ...(state.commands || {}) };
      commands[payload.id] = { enabled: false, reason: payload.reason || "" };
      return { ...state, commands };
    },
    "layout:set": (state, payload) => ({ ...state, layout: payload.layout })
  };
}

export function replayEvents(initialState, events, options = {}) {
  validateEvents(events);

  const resolved = normalizeReplayOptions(options);
  const registry = resolved.registry ?? null;
  const handlers = resolved.handlers ?? defaultHandlers(registry);

  let state = deepClone(initialState);
  const snapshots = [];

  for (const event of events) {
    if (event.type === "snapshot") {
      snapshots.push(serializeState(state));
      continue;
    }
    const handler = handlers[event.type];
    if (!handler) {
      throw new Error(`No handler for event type: ${event.type}`);
    }
    state = handler(state, event.payload || {}, event);
  }

  return { state, snapshots };
}
