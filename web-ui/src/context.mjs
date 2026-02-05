export function makeContext(state, overrides = {}) {
  return {
    state,
    taskId: overrides.taskId ?? null,
    windowId: overrides.windowId ?? null,
    contextId: overrides.contextId ?? null,
    widgetId: overrides.widgetId ?? null,
    selection: overrides.selection ?? state.selection ?? null
  };
}
