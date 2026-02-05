import { serializeState } from "./snapshot.mjs";
import { validateEvents } from "./event-log.mjs";

function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

export function defaultHandlers() {
  return {
    "state:init": (state, payload) => ({ ...state, ...payload }),
    "focus:set": (state, payload) => ({ ...state, focus: payload.target }),
    "selection:set": (state, payload) => ({ ...state, selection: payload.target }),
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

export function replayEvents(initialState, events, handlers = defaultHandlers()) {
  validateEvents(events);

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
    state = handler(state, event.payload || {});
  }

  return { state, snapshots };
}
