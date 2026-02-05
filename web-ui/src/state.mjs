import { allocateId, initIdCounters } from "./ids.mjs";
import { normalizeSelection } from "./selection.mjs";

const ID_KINDS = ["workspace", "task", "window", "widget", "presentation", "layout"];

function ensureCounters(counters) {
  if (counters) {
    return counters;
  }
  return initIdCounters(ID_KINDS);
}

function ensureWorkspace(state) {
  if (state.workspace) {
    return state;
  }
  const alloc = allocateId(state.idCounters, "workspace");
  const workspace = createWorkspace({ id: alloc.id });
  return {
    ...state,
    idCounters: alloc.counters,
    workspace
  };
}

function normalizeTask(task) {
  return {
    id: task.id,
    title: task.title ?? "Untitled",
    windowIds: Array.isArray(task.windowIds) ? [...task.windowIds] : [],
    activeWindowId: task.activeWindowId ?? null,
    metadata: task.metadata ?? {}
  };
}

function normalizeWindow(window) {
  return {
    id: window.id,
    taskId: window.taskId,
    title: window.title ?? "Window",
    kind: window.kind ?? "document",
    rootWidgetId: window.rootWidgetId ?? null,
    metadata: window.metadata ?? {}
  };
}

function normalizeWidget(widget) {
  return {
    id: widget.id,
    kind: widget.kind ?? "container",
    parentId: widget.parentId ?? null,
    windowId: widget.windowId ?? null,
    childIds: Array.isArray(widget.childIds) ? [...widget.childIds] : [],
    props: widget.props ?? {},
    model: widget.model ?? {}
  };
}

function normalizePresentation(presentation) {
  return {
    id: presentation.id,
    type: presentation.type ?? "presentation",
    objectId: presentation.objectId ?? null,
    widgetId: presentation.widgetId ?? null,
    bounds: presentation.bounds ?? null,
    metadata: presentation.metadata ?? {}
  };
}

export function createWorkspace({ id, title, taskIds, activeTaskId, metadata } = {}) {
  return {
    id,
    title: title ?? "Workspace",
    taskIds: Array.isArray(taskIds) ? [...taskIds] : [],
    activeTaskId: activeTaskId ?? null,
    metadata: metadata ?? {}
  };
}

export function createState(options = {}) {
  const idCounters = ensureCounters(options.idCounters);
  let state = {
    workspace: options.workspace ?? null,
    tasks: options.tasks ?? {},
    windows: options.windows ?? {},
    widgets: options.widgets ?? {},
    presentations: options.presentations ?? {},
    focus: options.focus ?? null,
    focusHistory: Array.isArray(options.focusHistory) ? [...options.focusHistory] : [],
    selection: normalizeSelection(options.selection ?? null),
    commands: options.commands ?? {},
    layout: options.layout ?? null,
    idCounters,
    ...options
  };
  state = ensureWorkspace(state);
  return state;
}

export function addTask(state, task) {
  if (!task) {
    throw new Error("Task is required");
  }
  const alloc = task.id ? { id: task.id, counters: state.idCounters } : allocateId(state.idCounters, "task");
  const normalized = normalizeTask({ ...task, id: alloc.id });
  const tasks = { ...state.tasks, [normalized.id]: normalized };
  const workspace = state.workspace ?? createWorkspace({ id: "workspace-0" });
  const existingTaskIds = Array.isArray(workspace.taskIds) ? workspace.taskIds : [];
  const taskIds = existingTaskIds.includes(normalized.id)
    ? existingTaskIds
    : [...existingTaskIds, normalized.id];
  const activeTaskId = workspace.activeTaskId ?? normalized.id;
  return {
    ...state,
    idCounters: alloc.counters,
    tasks,
    workspace: { ...workspace, taskIds, activeTaskId }
  };
}

export function addWindow(state, window) {
  if (!window) {
    throw new Error("Window is required");
  }
  const taskId = window.taskId ?? state.workspace?.activeTaskId ?? null;
  if (!taskId || !state.tasks[taskId]) {
    throw new Error("Window must reference an existing task");
  }
  const alloc = window.id ? { id: window.id, counters: state.idCounters } : allocateId(state.idCounters, "window");
  const normalized = normalizeWindow({ ...window, id: alloc.id, taskId });
  const windows = { ...state.windows, [normalized.id]: normalized };
  const task = state.tasks[taskId];
  const existingWindowIds = Array.isArray(task.windowIds) ? task.windowIds : [];
  const windowIds = existingWindowIds.includes(normalized.id)
    ? existingWindowIds
    : [...existingWindowIds, normalized.id];
  const activeWindowId = task.activeWindowId ?? normalized.id;
  return {
    ...state,
    idCounters: alloc.counters,
    windows,
    tasks: {
      ...state.tasks,
      [taskId]: { ...task, windowIds, activeWindowId }
    }
  };
}

export function addWidget(state, widget) {
  if (!widget) {
    throw new Error("Widget is required");
  }
  const alloc = widget.id ? { id: widget.id, counters: state.idCounters } : allocateId(state.idCounters, "widget");
  const normalized = normalizeWidget({ ...widget, id: alloc.id });
  const widgets = { ...state.widgets, [normalized.id]: normalized };
  if (normalized.parentId) {
    const parent = widgets[normalized.parentId];
    if (!parent) {
      throw new Error(`Unknown parent widget: ${normalized.parentId}`);
    }
    const parentChildIds = Array.isArray(parent.childIds) ? parent.childIds : [];
    if (!parentChildIds.includes(normalized.id)) {
      widgets[normalized.parentId] = {
        ...parent,
        childIds: [...parentChildIds, normalized.id]
      };
    }
  }
  let windows = state.windows;
  if (normalized.windowId) {
    const window = windows[normalized.windowId];
    if (window && !window.rootWidgetId) {
      windows = {
        ...windows,
        [normalized.windowId]: { ...window, rootWidgetId: normalized.id }
      };
    }
  }
  return {
    ...state,
    idCounters: alloc.counters,
    widgets,
    windows
  };
}

export function addPresentation(state, presentation) {
  if (!presentation) {
    throw new Error("Presentation is required");
  }
  const alloc = presentation.id
    ? { id: presentation.id, counters: state.idCounters }
    : allocateId(state.idCounters, "presentation");
  const normalized = normalizePresentation({ ...presentation, id: alloc.id });
  const presentations = { ...state.presentations, [normalized.id]: normalized };
  return { ...state, idCounters: alloc.counters, presentations };
}

export function setLayout(state, layout) {
  return { ...state, layout };
}

export function setSelection(state, selection) {
  return { ...state, selection: normalizeSelection(selection) };
}

export function setFocus(state, target, reason = "command", seq = null) {
  const entry = {
    seq: seq ?? state.focusHistory.length + 1,
    target,
    reason
  };
  return {
    ...state,
    focus: target,
    focusHistory: [...state.focusHistory, entry]
  };
}
