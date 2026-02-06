import { createState } from "../state.mjs";
import { normalizeFocusTarget } from "../focus.mjs";
import { normalizeSelection } from "../selection.mjs";
import { allocateId, initIdCounters } from "../ids.mjs";
import { SCHEMA_VERSION } from "./schema.mjs";
import { applyMigrations } from "./migrate.mjs";

const ID_KINDS = ["workspace", "task", "window", "widget", "presentation", "layout", "reason", "error", "job"];

const DEFAULT_ALLOWLIST = {
  workspace: true,
  tasks: true,
  windows: true,
  widgets: true,
  layout: true,
  selection: true,
  focus: true,
  presentations: false,
  idCounters: true
};

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === "[object Object]";
}

function sanitizeValue(value, seen = new Set()) {
  if (value === null || value === undefined) return value;
  const type = typeof value;
  if (type === "string" || type === "number" || type === "boolean") return value;
  if (type === "function" || type === "symbol") return undefined;
  if (value instanceof Date) return value.toISOString();
  if (value instanceof Uint8Array) return Array.from(value);
  if (ArrayBuffer.isView(value)) return Array.from(new Uint8Array(value.buffer, value.byteOffset, value.byteLength));
  if (value instanceof ArrayBuffer) return Array.from(new Uint8Array(value));
  if (value && typeof value.nodeType === "number") return undefined;
  if (Array.isArray(value)) {
    const out = [];
    for (const entry of value) {
      const sanitized = sanitizeValue(entry, seen);
      if (sanitized !== undefined) out.push(sanitized);
    }
    return out;
  }
  if (!isPlainObject(value)) return undefined;
  if (seen.has(value)) return undefined;
  seen.add(value);
  const out = {};
  for (const [key, entry] of Object.entries(value)) {
    const sanitized = sanitizeValue(entry, seen);
    if (sanitized !== undefined) out[key] = sanitized;
  }
  seen.delete(value);
  return out;
}

function sanitizeRecord(record) {
  if (!record || typeof record !== "object") return {};
  const out = {};
  for (const [key, value] of Object.entries(record)) {
    const sanitized = sanitizeValue(value);
    if (sanitized !== undefined) out[key] = sanitized;
  }
  return out;
}

function sanitizeMap(map) {
  if (!map || typeof map !== "object") return {};
  const out = {};
  for (const [key, value] of Object.entries(map)) {
    out[key] = sanitizeRecord(value);
  }
  return out;
}

function sanitizeCounters(counters) {
  const out = initIdCounters(ID_KINDS);
  if (!counters || typeof counters !== "object") return out;
  for (const kind of ID_KINDS) {
    if (Number.isInteger(counters[kind]) && counters[kind] >= 0) {
      out[kind] = counters[kind];
    }
  }
  return out;
}

function ensureTaskExists(state) {
  const taskIds = Object.keys(state.tasks ?? {});
  if (taskIds.length > 0) return state;
  if (!state.windows || Object.keys(state.windows).length === 0) return state;
  const counters = sanitizeCounters(state.idCounters);
  const alloc = allocateId(counters, "task", "task");
  const taskId = alloc.id;
  const task = {
    id: taskId,
    title: "Restored Task",
    windowIds: [],
    activeWindowId: null,
    metadata: {}
  };
  return {
    ...state,
    idCounters: alloc.counters,
    tasks: { [taskId]: task },
    workspace: {
      ...(state.workspace ?? {}),
      id: state.workspace?.id ?? "workspace-0",
      taskIds: [taskId],
      activeTaskId: taskId
    }
  };
}

function normalizeWorkspace(state) {
  const workspace = state.workspace ?? { id: "workspace-0", title: "Workspace" };
  const taskIds = Array.isArray(workspace.taskIds) ? workspace.taskIds.filter((id) => state.tasks?.[id]) : [];
  const missing = Object.keys(state.tasks ?? {}).filter((id) => !taskIds.includes(id));
  const nextTaskIds = [...taskIds, ...missing];
  const activeTaskId = nextTaskIds.includes(workspace.activeTaskId) ? workspace.activeTaskId : nextTaskIds[0] ?? null;
  return {
    ...workspace,
    taskIds: nextTaskIds,
    activeTaskId
  };
}

function normalizeWindows(state) {
  const tasks = state.tasks ?? {};
  const fallbackTaskId = state.workspace?.activeTaskId ?? Object.keys(tasks)[0] ?? null;
  const windows = {};
  for (const [id, window] of Object.entries(state.windows ?? {})) {
    const taskId = window.taskId && tasks[window.taskId] ? window.taskId : fallbackTaskId;
    if (!taskId) continue;
    windows[id] = { ...window, taskId };
  }
  return windows;
}

function normalizeWindowRoots(state, windows, widgets) {
  const next = {};
  for (const [id, window] of Object.entries(windows)) {
    let rootWidgetId = window.rootWidgetId;
    if (rootWidgetId && !widgets[rootWidgetId]) {
      rootWidgetId = null;
    }
    if (!rootWidgetId) {
      rootWidgetId =
        Object.values(widgets).find((widget) => widget.windowId === id && !widget.parentId)?.id ?? null;
    }
    next[id] = { ...window, rootWidgetId };
  }
  return next;
}

function normalizeTasks(state, windows) {
  const taskWindowMap = {};
  for (const [id, window] of Object.entries(windows)) {
    if (!taskWindowMap[window.taskId]) taskWindowMap[window.taskId] = [];
    taskWindowMap[window.taskId].push(id);
  }
  const tasks = {};
  for (const [id, task] of Object.entries(state.tasks ?? {})) {
    const windowIds = taskWindowMap[id] ?? [];
    const activeWindowId = windowIds.includes(task.activeWindowId) ? task.activeWindowId : windowIds[0] ?? null;
    tasks[id] = { ...task, windowIds, activeWindowId };
  }
  return tasks;
}

function normalizeWidgets(state) {
  const widgets = sanitizeMap(state.widgets ?? {});
  for (const [id, widget] of Object.entries(widgets)) {
    const parentId = widget.parentId && widgets[widget.parentId] ? widget.parentId : null;
    const childIds = Array.isArray(widget.childIds)
      ? widget.childIds.filter((childId) => widgets[childId])
      : [];
    widgets[id] = { ...widget, parentId, childIds };
  }
  return widgets;
}

function normalizeFocus(state) {
  const focus = normalizeFocusTarget(state.focus ?? null);
  if (!focus) return null;
  if (focus.taskId && !state.tasks?.[focus.taskId]) return null;
  if (focus.windowId && !state.windows?.[focus.windowId]) return null;
  if (focus.widgetId && !state.widgets?.[focus.widgetId]) return null;
  return focus;
}

function normalizeSelectionState(selection) {
  try {
    return normalizeSelection(selection ?? null);
  } catch (err) {
    return null;
  }
}

function rebuildIdCounters(state) {
  const counters = sanitizeCounters(state.idCounters ?? {});
  const allIds = {
    workspace: [state.workspace?.id],
    task: Object.keys(state.tasks ?? {}),
    window: Object.keys(state.windows ?? {}),
    widget: Object.keys(state.widgets ?? {}),
    presentation: Object.keys(state.presentations ?? {}),
    layout: Object.keys(state.layout?.nodes ?? {}),
    reason: Object.keys(state.focusReasons ?? {}),
    error: (state.errors ?? []).map((entry) => entry?.id),
    job: (state.jobs ?? []).map((entry) => entry?.id)
  };
  for (const kind of ID_KINDS) {
    const ids = allIds[kind] ?? [];
    for (const id of ids) {
      if (typeof id !== "string") continue;
      const match = id.match(new RegExp(`^${kind}-(\\d+)$`));
      if (!match) continue;
      const value = Number.parseInt(match[1], 10);
      if (Number.isFinite(value) && value + 1 > counters[kind]) {
        counters[kind] = value + 1;
      }
    }
  }
  return counters;
}

export function sanitizeState(state, options = {}) {
  const allowlist = { ...DEFAULT_ALLOWLIST, ...(options.allowlist ?? {}) };
  const out = {};
  if (allowlist.workspace) out.workspace = sanitizeRecord(state.workspace ?? {});
  if (allowlist.tasks) out.tasks = sanitizeMap(state.tasks ?? {});
  if (allowlist.windows) out.windows = sanitizeMap(state.windows ?? {});
  if (allowlist.widgets) out.widgets = sanitizeMap(state.widgets ?? {});
  if (allowlist.layout) out.layout = sanitizeRecord(state.layout ?? {});
  if (allowlist.selection) out.selection = sanitizeValue(state.selection ?? null) ?? null;
  if (allowlist.focus) out.focus = sanitizeValue(state.focus ?? null) ?? null;
  if (allowlist.presentations) out.presentations = sanitizeMap(state.presentations ?? {});
  if (allowlist.idCounters) out.idCounters = sanitizeCounters(state.idCounters ?? {});
  return out;
}

export function createSnapshot(state, options = {}) {
  const now = options.now ?? (() => Date.now());
  const allowlist = options.allowlist ?? {};
  const sanitized = sanitizeState(state, { allowlist });
  const normalized = restoreStateFromSnapshot(
    { schemaVersion: options.schemaVersion ?? SCHEMA_VERSION, createdAt: now(), state: sanitized },
    { schemaVersion: options.schemaVersion ?? SCHEMA_VERSION, allowlist, now }
  );
  const normalizedState = normalized?.state ?? sanitized;
  const finalState = sanitizeState(normalizedState, { allowlist });
  return {
    schemaVersion: options.schemaVersion ?? SCHEMA_VERSION,
    createdAt: now(),
    workspaceId: finalState.workspace?.id ?? state.workspace?.id ?? null,
    metadata: sanitizeValue(options.metadata ?? {}) ?? {},
    state: finalState
  };
}

export function restoreStateFromSnapshot(snapshot, options = {}) {
  if (!snapshot) return null;
  const migrated = applyMigrations(snapshot, { targetVersion: options.schemaVersion ?? SCHEMA_VERSION, now: options.now });
  if (!migrated) return null;

  const sanitized = sanitizeState(migrated.state ?? {}, { allowlist: options.allowlist });
  const counters = rebuildIdCounters(sanitized);
  const baseState = createState({ ...sanitized, idCounters: counters });

  let state = ensureTaskExists(baseState);
  const windows = normalizeWindows(state);
  const tasks = normalizeTasks(state, windows);
  const workspace = normalizeWorkspace({ ...state, tasks, windows });
  const widgets = normalizeWidgets(state);
  const normalizedWindows = normalizeWindowRoots(state, windows, widgets);

  const nextState = {
    ...state,
    windows: normalizedWindows,
    tasks,
    workspace,
    widgets
  };

  const finalState = {
    ...nextState,
    selection: normalizeSelectionState(nextState.selection),
    focus: normalizeFocus(nextState),
    idCounters: rebuildIdCounters(nextState)
  };

  return { state: finalState, snapshot: migrated };
}
