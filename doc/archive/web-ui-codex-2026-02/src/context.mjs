export function makeContext(state, overrides = {}) {
  return {
    state,
    workspaceId: overrides.workspaceId ?? state.workspace?.id ?? null,
    taskId: overrides.taskId ?? null,
    windowId: overrides.windowId ?? null,
    contextId: overrides.contextId ?? null,
    widgetId: overrides.widgetId ?? null,
    presentationId: overrides.presentationId ?? null,
    selection: overrides.selection ?? state.selection ?? null
  };
}
