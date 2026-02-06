import { serializeState } from "./snapshot.mjs";
import { validateEvents } from "./event-log.mjs";
import { setFocus } from "../src/focus.mjs";
import {
  createState,
  setLayout,
  recordEvent,
  setCommandState,
  enqueueUiSignal,
  beginUiTurn,
  advanceUiTurn,
  yieldUiTurn,
  endUiTurn
} from "../src/state.mjs";
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
    "command:enable": (state, payload) => setCommandState(state, payload.id, true, null),
    "command:disable": (state, payload) => setCommandState(state, payload.id, false, payload.reason || ""),
    "layout:set": (state, payload) => setLayout(state, payload.layout),
    "ui:signal.enqueue": (state, payload) => enqueueUiSignal(state, payload.signal ?? payload),
    "ui:turn.begin": (state, payload) =>
      beginUiTurn(state, {
        commitPolicy: payload.commitPolicy ?? null,
        drainSignals: payload.drainSignals
      }),
    "ui:turn.phase": (state, payload) => advanceUiTurn(state, payload.phase),
    "ui:turn.yield": (state, payload) => yieldUiTurn(state, payload.reason ?? null),
    "ui:turn.end": (state) => endUiTurn(state)
  };
}

export function replayEvents(initialState, events, options = {}) {
  validateEvents(events);

  const resolved = normalizeReplayOptions(options);
  const registry = resolved.registry ?? null;
  const handlers = resolved.handlers ?? defaultHandlers(registry);

  let state = createState(deepClone(initialState));
  const snapshots = [];

  for (const event of events) {
    if (event.type === "snapshot") {
      snapshots.push(serializeState(state));
      continue;
    }
    state = recordEvent(state, event);
    const handler = handlers[event.type];
    if (!handler) {
      throw new Error(`No handler for event type: ${event.type}`);
    }
    state = handler(state, event.payload || {}, event);
  }

  return { state, snapshots };
}
