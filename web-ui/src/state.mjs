import { allocateId, initIdCounters } from "./ids.mjs";
import { normalizeEventLog, recordEvent as recordEventLog } from "./event-log.mjs";
import { normalizeSelection } from "./selection.mjs";
import {
  normalizeLayout,
  createLayout,
  splitLayoutNode,
  wrapInTabsNode,
  setActiveTabNode,
  dockLayoutNode
} from "./layout.mjs";
import { normalizeFocusTarget, normalizeFocusHistory, setFocus as setFocusCore } from "./focus.mjs";
import { registerCommand, executeCommand, bindKey, resolveKeyWithTrace } from "./commands.mjs";

const ID_KINDS = ["workspace", "task", "window", "widget", "presentation", "layout", "reason", "error", "job"];
export const COMMAND_PALETTE_FILTER_COMMAND = "ui.command-palette.filter";
export const COMMAND_PALETTE_EXECUTE_COMMAND = "ui.command-palette.execute";
export const COMMAND_PALETTE_SELECT_NEXT_COMMAND = "ui.command-palette.select-next";
export const COMMAND_PALETTE_SELECT_PREV_COMMAND = "ui.command-palette.select-prev";
export const COMMAND_PALETTE_EXECUTE_SELECTION_COMMAND = "ui.command-palette.execute-selected";
export const COMMAND_PALETTE_OPEN_COMMAND = "ui.command-palette.open";
export const COMMAND_PALETTE_CLOSE_COMMAND = "ui.command-palette.close";
export const KEYBINDINGS_OPEN_COMMAND = "ui.keybindings.open";
export const KEYBINDINGS_CLOSE_COMMAND = "ui.keybindings.close";

function ensureCounters(counters) {
  if (counters) {
    const next = { ...counters };
    for (const kind of ID_KINDS) {
      if (!Number.isInteger(next[kind])) {
        next[kind] = 0;
      }
    }
    return next;
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
    ...options,
    workspace: options.workspace ?? null,
    tasks: options.tasks ?? {},
    windows: options.windows ?? {},
    widgets: options.widgets ?? {},
    presentations: options.presentations ?? {},
    focus: normalizeFocusTarget(options.focus ?? null),
    focusHistory: normalizeFocusHistory(options.focusHistory ?? []),
    selection: normalizeSelection(options.selection ?? null),
    commands: options.commands ?? {},
    layout: options.layout ?? null,
    focusReasons: options.focusReasons ?? {},
    disableReasons: options.disableReasons ?? {},
    windowCauses: options.windowCauses ?? {},
    jobCauses: options.jobCauses ?? {},
    eventLog: normalizeEventLog(options.eventLog ?? null),
    errors: Array.isArray(options.errors) ? [...options.errors] : [],
    jobs: Array.isArray(options.jobs) ? [...options.jobs] : [],
    idCounters
  };
  state = ensureWorkspace(state);
  const normalized = normalizeLayout(state.layout, state.idCounters);
  state = { ...state, layout: normalized.layout, idCounters: normalized.counters };
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

function collectWidgetSubtreeIds(widgets, rootIds) {
  const childrenByParent = new Map();
  for (const [id, widget] of Object.entries(widgets ?? {})) {
    const parentId = widget.parentId;
    if (!parentId) continue;
    let list = childrenByParent.get(parentId);
    if (!list) {
      list = [];
      childrenByParent.set(parentId, list);
    }
    list.push(id);
  }
  const pending = [...new Set(rootIds.filter(Boolean))];
  const toRemove = new Set();
  while (pending.length > 0) {
    const current = pending.pop();
    if (!current || toRemove.has(current)) continue;
    toRemove.add(current);
    const children = childrenByParent.get(current);
    if (children) {
      pending.push(...children);
    }
  }
  return toRemove;
}

export function removeWindow(state, windowId, options = {}) {
  const window = state.windows?.[windowId];
  if (!window) {
    return state;
  }
  const widgets = state.widgets ?? {};
  const rootIds = [];
  if (window.rootWidgetId) {
    rootIds.push(window.rootWidgetId);
  }
  for (const [id, widget] of Object.entries(widgets)) {
    if (widget.windowId === windowId) {
      rootIds.push(id);
    }
  }
  const toRemove = collectWidgetSubtreeIds(widgets, rootIds);

  let nextWidgets = widgets;
  if (toRemove.size > 0) {
    nextWidgets = {};
    for (const [id, widget] of Object.entries(widgets)) {
      if (!toRemove.has(id)) {
        nextWidgets[id] = widget;
      }
    }
  } else {
    nextWidgets = { ...widgets };
  }

  let nextState = { ...state, widgets: nextWidgets };

  if (toRemove.size > 0 && nextState.presentations) {
    const nextPresentations = {};
    for (const [id, presentation] of Object.entries(nextState.presentations)) {
      if (presentation.widgetId && toRemove.has(presentation.widgetId)) {
        continue;
      }
      nextPresentations[id] = presentation;
    }
    nextState = { ...nextState, presentations: nextPresentations };
  }

  const nextWindows = { ...nextState.windows };
  delete nextWindows[windowId];
  nextState = { ...nextState, windows: nextWindows };

  const tasks = { ...nextState.tasks };
  const task = tasks[window.taskId];
  if (task) {
    const windowIds = task.windowIds.filter((id) => id !== windowId);
    const activeWindowId = task.activeWindowId === windowId ? (windowIds[0] ?? null) : task.activeWindowId;
    tasks[window.taskId] = { ...task, windowIds, activeWindowId };
  }
  nextState = { ...nextState, tasks };

  if (nextState.windowCauses && nextState.windowCauses[windowId]) {
    const nextCauses = { ...nextState.windowCauses };
    delete nextCauses[windowId];
    nextState = { ...nextState, windowCauses: nextCauses };
  }

  const focus = nextState.focus;
  if (focus && (focus.windowId === windowId || (focus.widgetId && toRemove.has(focus.widgetId)))) {
    nextState = setFocusCore(nextState, null, options.reason ?? "command");
  }

  return nextState;
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
  const normalized = normalizeLayout(layout, state.idCounters);
  return { ...state, layout: normalized.layout, idCounters: normalized.counters };
}

export function recordEvent(state, entry) {
  if (!entry || typeof entry !== "object") {
    throw new Error("Event entry must be an object");
  }
  const eventLog = recordEventLog(state.eventLog ?? null, entry);
  return { ...state, eventLog };
}

export function setSelection(state, selection) {
  return { ...state, selection: normalizeSelection(selection) };
}

export function setFocus(state, target, reason = "command", seq = null) {
  return setFocusCore(state, target, reason, seq);
}

export function initLayout(state, rootSpec) {
  const created = createLayout(rootSpec, state.idCounters);
  return { ...state, layout: created.layout, idCounters: created.counters };
}

export function splitLayout(state, targetId, axis = "h", ratio = 0.5, options = {}) {
  const updated = splitLayoutNode(state.layout, state.idCounters, targetId, axis, ratio, options);
  return { ...state, layout: updated.layout, idCounters: updated.counters };
}

export function wrapInTabs(state, targetId, options = {}) {
  const updated = wrapInTabsNode(state.layout, state.idCounters, targetId, options);
  return { ...state, layout: updated.layout, idCounters: updated.counters };
}

export function setActiveTab(state, tabsId, tabId) {
  const updated = setActiveTabNode(state.layout, state.idCounters, tabsId, tabId);
  return { ...state, layout: updated.layout, idCounters: updated.counters };
}

export function dockLayout(state, targetId, region) {
  const updated = dockLayoutNode(state.layout, state.idCounters, targetId, region);
  return { ...state, layout: updated.layout, idCounters: updated.counters };
}

export function setCommandState(state, id, enabled, reason = null) {
  const commands = { ...(state.commands ?? {}) };
  let reasonId = commands[id]?.reasonId ?? null;
  let nextState = state;
  if (enabled === false && reason) {
    const alloc = allocateId(state.idCounters, "reason", "reason");
    reasonId = alloc.id;
    const disableReasons = { ...(state.disableReasons ?? {}) };
    disableReasons[reasonId] = {
      id: reasonId,
      reason,
      ts: null,
      details: {}
    };
    nextState = { ...state, idCounters: alloc.counters, disableReasons };
  }
  commands[id] = {
    enabled: Boolean(enabled),
    reason: reason ?? null,
    reasonId
  };
  return { ...nextState, commands };
}

export function updateWidget(state, widgetId, patch) {
  const widget = state.widgets?.[widgetId];
  if (!widget) {
    throw new Error(`Unknown widget: ${widgetId}`);
  }
  const next = typeof patch === "function" ? patch(widget) : { ...widget, ...patch };
  return {
    ...state,
    widgets: { ...state.widgets, [widgetId]: next }
  };
}

export function updateWindow(state, windowId, patch) {
  const window = state.windows?.[windowId];
  if (!window) {
    throw new Error(`Unknown window: ${windowId}`);
  }
  const next = typeof patch === "function" ? patch(window) : { ...window, ...patch };
  return {
    ...state,
    windows: { ...state.windows, [windowId]: next }
  };
}

function allocateWidgetId(state, prefix = "widget") {
  const alloc = allocateId(state.idCounters, "widget", prefix);
  return { id: alloc.id, state: { ...state, idCounters: alloc.counters } };
}

function findWindowByRole(state, role, taskId) {
  for (const window of Object.values(state.windows ?? {})) {
    if (window.metadata?.role !== role) continue;
    if (taskId && window.taskId !== taskId) continue;
    return window;
  }
  return null;
}

function summarizeFocus(state) {
  const items = [];
  const focus = state.focus;
  if (!focus) {
    items.push({ id: "focus-none", label: "Focus: none" });
    return items;
  }
  items.push({
    id: "focus-target",
    label: `Focus: task=${focus.taskId ?? "none"} window=${focus.windowId ?? "none"} widget=${
      focus.widgetId ?? "none"
    }`
  });
  const last = state.focusHistory?.[state.focusHistory.length - 1];
  if (last?.reason) {
    items.push({ id: "focus-reason", label: `Reason: ${last.reason}` });
  }
  return items;
}

function summarizeCommands(state) {
  const items = [];
  const entries = Object.entries(state.commands ?? {}).sort(([a], [b]) => a.localeCompare(b));
  for (const [id, info] of entries) {
    if (info?.enabled === false) {
      items.push({ id: `cmd-${id}`, label: `${id}: disabled (${info.reason ?? "Disabled"})` });
    } else {
      items.push({ id: `cmd-${id}`, label: `${id}: enabled` });
    }
  }
  if (items.length === 0) {
    items.push({ id: "cmd-none", label: "No command state recorded" });
  }
  return items;
}

function buildCommandPaletteItems(registry, options = {}) {
  if (!registry) {
    return [{ id: "cmd-none", label: "No command registry available" }];
  }
  const filter = String(options.filter ?? "").trim().toLowerCase();
  const excludeIds = new Set(options.excludeIds ?? []);
  const entries = [...registry.commands.values()].sort((a, b) => a.id.localeCompare(b.id));
  const items = [];
  for (const cmd of entries) {
    if (excludeIds.has(cmd.id)) {
      continue;
    }
    if (cmd.metadata?.paletteHidden) {
      continue;
    }
    const title = cmd.title ?? cmd.id;
    const doc = cmd.doc ?? "";
    const haystack = `${cmd.id} ${title} ${doc}`.toLowerCase();
    if (filter && !haystack.includes(filter)) {
      continue;
    }
    const label = title && title !== cmd.id ? `${cmd.id} — ${title}` : cmd.id;
    items.push({
      id: `cmd-${cmd.id}`,
      label,
      targetCommandId: cmd.id
    });
  }
  if (items.length === 0) {
    items.push({ id: "cmd-empty", label: filter ? "No commands matched" : "No commands registered" });
  }
  return items;
}

function clampIndex(index, length) {
  if (length <= 0) return -1;
  if (!Number.isFinite(index)) return 0;
  return Math.max(0, Math.min(length - 1, Math.trunc(index)));
}

function applySelectionToItems(items, selectedIndex) {
  if (!Array.isArray(items) || items.length === 0) return items;
  return items.map((item, index) => ({
    ...item,
    selected: index === selectedIndex
  }));
}

function buildKeybindingItems(registry) {
  if (!registry) {
    return [{ id: "kb-none", label: "No keybindings registered" }];
  }
  const items = [];
  const scopes = Array.isArray(registry.precedence)
    ? [...registry.precedence]
    : Object.keys(registry.keymaps ?? {});
  for (const scope of scopes) {
    if (scope === "global") {
      const entries = [...registry.keymaps.global.entries()].sort(([a], [b]) => a.localeCompare(b));
      for (const [key, commandId] of entries) {
        items.push({
          id: `kb-${scope}-${key}`,
          label: `${scope}: ${key} → ${commandId ?? "unbound"}`
        });
      }
      continue;
    }
    const scoped = registry.keymaps[scope];
    if (!scoped) continue;
    const scopedEntries = [...scoped.entries()].sort(([a], [b]) => String(a).localeCompare(String(b)));
    for (const [scopeId, map] of scopedEntries) {
      const entries = [...(map?.entries?.() ?? [])].sort(([a], [b]) => a.localeCompare(b));
      for (const [key, commandId] of entries) {
        items.push({
          id: `kb-${scope}-${scopeId}-${key}`,
          label: `${scope}(${scopeId}): ${key} → ${commandId ?? "unbound"}`
        });
      }
    }
  }
  if (items.length === 0) {
    items.push({ id: "kb-empty", label: "No keybindings registered" });
  }
  return items;
}

function buildKeybindingTraceContext(options, taskId) {
  const override = options?.traceContext ?? {};
  return {
    taskId: override.taskId ?? options?.taskId ?? taskId ?? null,
    contextId: override.contextId ?? options?.contextId ?? null,
    widgetId: override.widgetId ?? options?.widgetId ?? null
  };
}

function buildKeybindingTraceItems(registry, options = {}) {
  if (!registry) {
    return [{ id: "kb-trace-none", label: "No keybinding registry available" }];
  }
  const key = options.key ?? null;
  if (!key) {
    return [{ id: "kb-trace-empty", label: "No key selected for trace" }];
  }
  const ctx = options.context ?? {};
  const resolved = resolveKeyWithTrace(registry, key, ctx);
  const trace = Array.isArray(resolved.trace) ? resolved.trace : [];
  if (trace.length === 0) {
    return [{ id: "kb-trace-empty", label: "No trace available" }];
  }
  return trace.map((entry, index) => {
    const scopeLabel = entry.scopeId ? `${entry.scope}(${entry.scopeId})` : entry.scope;
    const commandLabel = entry.commandId ?? "unbound";
    let suffix = "";
    if (entry.matched) {
      suffix = " (match)";
    } else if (entry.reason) {
      suffix = ` (${entry.reason})`;
    }
    return {
      id: `kb-trace-${index}-${entry.scope}`,
      label: `${scopeLabel}: ${entry.key} → ${commandLabel}${suffix}`
    };
  });
}

function summarizeWindows(state) {
  const items = [];
  const entries = Object.values(state.windows ?? {}).sort((a, b) => a.id.localeCompare(b.id));
  for (const window of entries) {
    items.push({
      id: `win-${window.id}`,
      label: `${window.id} (${window.kind ?? "window"}) task=${window.taskId ?? "none"}`
    });
  }
  if (items.length === 0) {
    items.push({ id: "win-none", label: "No windows" });
  }
  return items;
}

function summarizeJobs(state) {
  const items = [];
  const entries = [...(state.jobs ?? [])].sort((a, b) => (a.id ?? "").localeCompare(b.id ?? ""));
  for (const job of entries) {
    items.push({
      id: `job-${job.id ?? "unknown"}`,
      label: `${job.title ?? job.id ?? "job"} (${job.status ?? "unknown"})`
    });
  }
  if (items.length === 0) {
    items.push({ id: "job-none", label: "No jobs" });
  }
  return items;
}

function summarizeErrors(state) {
  const items = [];
  const entries = [...(state.errors ?? [])].sort((a, b) => (a.id ?? "").localeCompare(b.id ?? ""));
  for (const error of entries) {
    items.push({
      id: `err-${error.id ?? "unknown"}`,
      label: `${error.kind ?? "error"}: ${error.message ?? ""} (${error.status ?? "open"})`
    });
  }
  if (items.length === 0) {
    items.push({ id: "err-none", label: "No errors" });
  }
  return items;
}

function summarizeEventLog(state, limit = 12) {
  const entries = state.eventLog?.entries ?? [];
  const sliced = entries.slice(-limit);
  const items = sliced.map((entry) => ({
    id: `event-${entry.seq ?? "?"}`,
    label: `${entry.seq ?? "?"} ${entry.type ?? "event"}`
  }));
  if (items.length === 0) {
    items.push({ id: "event-none", label: "No events recorded" });
  }
  return items;
}

function buildInspectorSections(state) {
  return {
    focus: summarizeFocus(state),
    commands: summarizeCommands(state),
    windows: summarizeWindows(state),
    jobs: summarizeJobs(state),
    errors: summarizeErrors(state),
    eventLog: summarizeEventLog(state)
  };
}

export function openInspectorWindow(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  if (!taskId) {
    throw new Error("Inspector requires a task");
  }
  const existing = findWindowByRole(state, "inspector", taskId);
  if (existing) {
    return refreshInspectorWindow(state, existing.id);
  }

  const allocWindow = allocateId(state.idCounters, "window", "inspector");
  let nextState = {
    ...state,
    idCounters: allocWindow.counters
  };
  nextState = addWindow(nextState, {
    id: allocWindow.id,
    taskId,
    kind: "inspector",
    title: "System Inspector",
    metadata: { role: "inspector" }
  });

  const sectionItems = buildInspectorSections(nextState);

  let ids = {};
  let rootAlloc = allocateWidgetId(nextState, "inspector-root");
  nextState = addWidget(rootAlloc.state, {
    id: rootAlloc.id,
    kind: "container",
    windowId: allocWindow.id,
    props: { className: "ui-inspector-root" }
  });
  ids.rootId = rootAlloc.id;

  const sections = [
    ["focus", "Focus"],
    ["commands", "Commands"],
    ["windows", "Windows"],
    ["jobs", "Jobs"],
    ["errors", "Errors"],
    ["eventLog", "Event Log"]
  ];

  ids.sections = {};
  for (const [key, title] of sections) {
    let labelAlloc = allocateWidgetId(nextState, `inspector-${key}-label`);
    nextState = addWidget(labelAlloc.state, {
      id: labelAlloc.id,
      kind: "label",
      parentId: ids.rootId,
      props: { text: title }
    });
    let listAlloc = allocateWidgetId(nextState, `inspector-${key}-list`);
    nextState = addWidget(listAlloc.state, {
      id: listAlloc.id,
      kind: "list",
      parentId: ids.rootId,
      props: { items: sectionItems[key] ?? [] }
    });
    ids.sections[key] = { labelId: labelAlloc.id, listId: listAlloc.id };
  }

  nextState = updateWindow(nextState, allocWindow.id, (window) => ({
    ...window,
    metadata: { ...(window.metadata ?? {}), role: "inspector", widgets: ids }
  }));

  return nextState;
}

export function refreshInspectorWindow(state, windowId) {
  const window = state.windows?.[windowId];
  if (!window || window.metadata?.role !== "inspector") {
    throw new Error("Window is not an inspector");
  }
  const widgets = window.metadata?.widgets;
  if (!widgets?.sections) {
    return state;
  }
  const sections = buildInspectorSections(state);
  let nextState = state;
  for (const [key, ids] of Object.entries(widgets.sections)) {
    nextState = updateWidget(nextState, ids.listId, (widget) => ({
      ...widget,
      props: { ...(widget.props ?? {}), items: sections[key] ?? [] }
    }));
  }
  return nextState;
}

export function openCommandPaletteWindow(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  if (!taskId) {
    throw new Error("Command palette requires a task");
  }
  const existing = findWindowByRole(state, "command-palette", taskId);
  if (existing) {
    return refreshCommandPaletteWindow(state, existing.id, options);
  }

  const allocWindow = allocateId(state.idCounters, "window", "command-palette");
  let nextState = {
    ...state,
    idCounters: allocWindow.counters
  };
  nextState = addWindow(nextState, {
    id: allocWindow.id,
    taskId,
    kind: "palette",
    title: "Command Palette",
    metadata: { role: "command-palette" }
  });

  let ids = {};
  let rootAlloc = allocateWidgetId(nextState, "command-palette-root");
  nextState = addWidget(rootAlloc.state, {
    id: rootAlloc.id,
    kind: "container",
    windowId: allocWindow.id,
    props: { className: "ui-command-palette-root" }
  });
  ids.rootId = rootAlloc.id;

  let labelAlloc = allocateWidgetId(nextState, "command-palette-label");
  nextState = addWidget(labelAlloc.state, {
    id: labelAlloc.id,
    kind: "label",
    parentId: ids.rootId,
    props: { text: "Commands" }
  });
  ids.labelId = labelAlloc.id;

  const filterValue = String(options.filter ?? "");
  let filterAlloc = allocateWidgetId(nextState, "command-palette-filter");
  const filterCommandId = Object.prototype.hasOwnProperty.call(options, "filterCommandId")
    ? options.filterCommandId
    : COMMAND_PALETTE_FILTER_COMMAND;
  nextState = addWidget(filterAlloc.state, {
    id: filterAlloc.id,
    kind: "text-input",
    parentId: ids.rootId,
    props: {
      placeholder: "Filter commands",
      value: filterValue,
      command: filterCommandId
    }
  });
  ids.filterId = filterAlloc.id;

  const items = buildCommandPaletteItems(options.registry ?? null, { filter: filterValue });
  const selectedIndex = clampIndex(0, items.length);
  const selectedItems = applySelectionToItems(items, selectedIndex);
  const selectedCommandId = items[selectedIndex]?.targetCommandId ?? null;
  let listAlloc = allocateWidgetId(nextState, "command-palette-list");
  nextState = addWidget(listAlloc.state, {
    id: listAlloc.id,
    kind: "list",
    parentId: ids.rootId,
    props: { items: selectedItems, itemCommand: COMMAND_PALETTE_EXECUTE_COMMAND }
  });
  ids.listId = listAlloc.id;

  nextState = updateWindow(nextState, allocWindow.id, (window) => ({
    ...window,
    metadata: {
      ...(window.metadata ?? {}),
      role: "command-palette",
      widgets: ids,
      palette: { selectedIndex, selectedCommandId }
    }
  }));

  return nextState;
}

export function refreshCommandPaletteWindow(state, windowId, options = {}) {
  const window = state.windows?.[windowId];
  if (!window || window.metadata?.role !== "command-palette") {
    throw new Error("Window is not a command palette");
  }
  const widgets = window.metadata?.widgets;
  if (!widgets?.listId || !widgets?.filterId) {
    return state;
  }
  const paletteState = window.metadata?.palette ?? {};
  const currentFilter =
    options.filter ??
    state.widgets?.[widgets.filterId]?.props?.value ??
    "";
  const filterValue = String(currentFilter ?? "");
  const items = buildCommandPaletteItems(options.registry ?? null, { filter: filterValue });
  const hasSelectionIndex = Number.isFinite(options.selectionIndex);
  let selectedIndex = hasSelectionIndex ? options.selectionIndex : (paletteState.selectedIndex ?? 0);
  const preferredCommandId = hasSelectionIndex
    ? null
    : (options.selectedCommandId ?? paletteState.selectedCommandId ?? null);
  if (preferredCommandId) {
    const matchIndex = items.findIndex((item) => item.targetCommandId === preferredCommandId);
    if (matchIndex !== -1) {
      selectedIndex = matchIndex;
    }
  }
  selectedIndex = clampIndex(selectedIndex, items.length);
  const selectedItems = applySelectionToItems(items, selectedIndex);
  const selectedCommandId = items[selectedIndex]?.targetCommandId ?? null;
  let nextState = state;
  nextState = updateWidget(nextState, widgets.filterId, (widget) => ({
    ...widget,
    props: { ...(widget.props ?? {}), value: filterValue }
  }));
  nextState = updateWidget(nextState, widgets.listId, (widget) => ({
    ...widget,
    props: { ...(widget.props ?? {}), items: selectedItems }
  }));
  nextState = updateWindow(nextState, windowId, (nextWindow) => ({
    ...nextWindow,
    metadata: {
      ...(nextWindow.metadata ?? {}),
      palette: { selectedIndex, selectedCommandId }
    }
  }));
  return nextState;
}

export function closeCommandPaletteWindow(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  const windowId =
    options.windowId ??
    findWindowByRole(state, "command-palette", taskId)?.id ??
    null;
  if (!windowId) {
    return state;
  }
  const window = state.windows?.[windowId];
  if (!window || window.metadata?.role !== "command-palette") {
    return state;
  }
  return removeWindow(state, windowId, { reason: options.reason ?? "command" });
}

export function applyCommandPaletteFilter(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  const windowId =
    options.windowId ??
    findWindowByRole(state, "command-palette", taskId)?.id ??
    null;
  if (!windowId) {
    return state;
  }
  const filterValue = options.filter ?? options.inputValue ?? "";
  return refreshCommandPaletteWindow(state, windowId, {
    registry: options.registry ?? null,
    filter: filterValue
  });
}

export function applyCommandPaletteSelection(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  const windowId =
    options.windowId ??
    findWindowByRole(state, "command-palette", taskId)?.id ??
    null;
  if (!windowId) {
    return state;
  }
  const window = state.windows?.[windowId];
  if (!window) return state;
  const paletteState = window.metadata?.palette ?? {};
  const delta = Number.isFinite(options.delta) ? options.delta : 0;
  const selectionIndex = Number.isFinite(options.index)
    ? options.index
    : (paletteState.selectedIndex ?? 0) + delta;
  return refreshCommandPaletteWindow(state, windowId, {
    registry: options.registry ?? null,
    filter: options.filter ?? null,
    selectionIndex,
    selectedCommandId: options.commandId ?? null
  });
}

export function resolveCommandPaletteSelection(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  const windowId =
    options.windowId ??
    findWindowByRole(state, "command-palette", taskId)?.id ??
    null;
  if (!windowId) {
    return { index: -1, item: null, commandId: null };
  }
  const window = state.windows?.[windowId];
  if (!window) return { index: -1, item: null, commandId: null };
  const paletteState = window.metadata?.palette ?? {};
  const widgets = window.metadata?.widgets ?? {};
  const items = state.widgets?.[widgets.listId]?.props?.items ?? [];
  const index = clampIndex(paletteState.selectedIndex ?? 0, items.length);
  const item = items[index] ?? null;
  const commandId = item?.targetCommandId ?? null;
  return { index, item, commandId };
}

export function registerCommandPaletteCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const filterId = options.filterCommandId ?? COMMAND_PALETTE_FILTER_COMMAND;
  const executeId = options.executeCommandId ?? COMMAND_PALETTE_EXECUTE_COMMAND;
  const nextId = options.selectNextCommandId ?? COMMAND_PALETTE_SELECT_NEXT_COMMAND;
  const prevId = options.selectPrevCommandId ?? COMMAND_PALETTE_SELECT_PREV_COMMAND;
  const execSelectedId = options.executeSelectedCommandId ?? COMMAND_PALETTE_EXECUTE_SELECTION_COMMAND;

  const ensure = (id, command) => {
    if (!registry.commands.has(id)) {
      registerCommand(registry, { ...command, id });
    }
  };

  ensure(filterId, {
    doc: "Filter command palette entries.",
    metadata: { paletteHidden: true },
    exec: (ctx) =>
      applyCommandPaletteFilter(ctx.state, {
        registry,
        windowId: ctx.windowId,
        taskId: ctx.taskId,
        inputValue: ctx.inputValue
      })
  });

  ensure(nextId, {
    doc: "Select next command palette entry.",
    metadata: { paletteHidden: true },
    exec: (ctx) =>
      applyCommandPaletteSelection(ctx.state, {
        registry,
        windowId: ctx.windowId,
        taskId: ctx.taskId,
        delta: 1
      })
  });

  ensure(prevId, {
    doc: "Select previous command palette entry.",
    metadata: { paletteHidden: true },
    exec: (ctx) =>
      applyCommandPaletteSelection(ctx.state, {
        registry,
        windowId: ctx.windowId,
        taskId: ctx.taskId,
        delta: -1
      })
  });

  ensure(executeId, {
    doc: "Execute the command palette item that was activated.",
    metadata: { paletteHidden: true },
    exec: (ctx) => {
      const target = ctx.item?.targetCommandId ?? null;
      if (!target) {
        return { ok: false, reason: "No target command" };
      }
      return executeCommand(registry, target, ctx);
    }
  });

  ensure(execSelectedId, {
    doc: "Execute the currently selected command palette entry.",
    metadata: { paletteHidden: true },
    exec: (ctx) => {
      const selection = resolveCommandPaletteSelection(ctx.state, {
        taskId: ctx.taskId,
        windowId: ctx.windowId
      });
      if (!selection.commandId) {
        return { ok: false, reason: "No selection" };
      }
      return executeCommand(registry, selection.commandId, ctx);
    }
  });

  return registry;
}

export function registerCommandSurfaceCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const paletteOpenId = options.paletteOpenCommandId ?? COMMAND_PALETTE_OPEN_COMMAND;
  const paletteCloseId = options.paletteCloseCommandId ?? COMMAND_PALETTE_CLOSE_COMMAND;
  const keybindingsOpenId = options.keybindingsOpenCommandId ?? KEYBINDINGS_OPEN_COMMAND;
  const keybindingsCloseId = options.keybindingsCloseCommandId ?? KEYBINDINGS_CLOSE_COMMAND;
  const filterCommandId = options.filterCommandId ?? COMMAND_PALETTE_FILTER_COMMAND;

  const ensure = (id, command) => {
    if (!registry.commands.has(id)) {
      registerCommand(registry, { ...command, id });
    }
  };

  ensure(paletteOpenId, {
    title: "Command Palette",
    doc: "Open the command palette.",
    metadata: { paletteHidden: true },
    exec: (ctx) =>
      openCommandPaletteWindow(ctx.state, {
        registry,
        taskId: ctx.taskId,
        filter: ctx.filter ?? ctx.inputValue ?? "",
        filterCommandId
      })
  });

  ensure(paletteCloseId, {
    title: "Close Command Palette",
    doc: "Close the command palette.",
    metadata: { paletteHidden: true },
    exec: (ctx) =>
      closeCommandPaletteWindow(ctx.state, {
        taskId: ctx.taskId,
        windowId: ctx.windowId
      })
  });

  ensure(keybindingsOpenId, {
    title: "Keybindings",
    doc: "Open the keybinding viewer.",
    metadata: { paletteHidden: true },
    exec: (ctx) =>
      openKeybindingWindow(ctx.state, {
        registry,
        taskId: ctx.taskId
      })
  });

  ensure(keybindingsCloseId, {
    title: "Close Keybindings",
    doc: "Close the keybinding viewer.",
    metadata: { paletteHidden: true },
    exec: (ctx) =>
      closeKeybindingWindow(ctx.state, {
        taskId: ctx.taskId,
        windowId: ctx.windowId
      })
  });

  return registry;
}

export function bindCommandPaletteDefaults(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const scope = options.scope ?? "task";
  const taskId = options.taskId ?? null;
  const hasScopeId = scope !== "global";
  if (hasScopeId && !taskId) {
    throw new Error("Task id required for non-global palette bindings");
  }
  const bind = (key, commandId) => {
    bindKey(registry, scope, key, commandId, hasScopeId ? taskId : null);
  };
  bind("ArrowDown", COMMAND_PALETTE_SELECT_NEXT_COMMAND);
  bind("ArrowUp", COMMAND_PALETTE_SELECT_PREV_COMMAND);
  bind("Enter", COMMAND_PALETTE_EXECUTE_SELECTION_COMMAND);
  return registry;
}

export function openKeybindingWindow(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  if (!taskId) {
    throw new Error("Keybinding viewer requires a task");
  }
  const existing = findWindowByRole(state, "keybindings", taskId);
  if (existing) {
    return refreshKeybindingWindow(state, existing.id, options);
  }

  const allocWindow = allocateId(state.idCounters, "window", "keybindings");
  let nextState = {
    ...state,
    idCounters: allocWindow.counters
  };
  nextState = addWindow(nextState, {
    id: allocWindow.id,
    taskId,
    kind: "keybindings",
    title: "Keybindings",
    metadata: { role: "keybindings" }
  });

  let ids = {};
  let rootAlloc = allocateWidgetId(nextState, "keybindings-root");
  nextState = addWidget(rootAlloc.state, {
    id: rootAlloc.id,
    kind: "container",
    windowId: allocWindow.id,
    props: { className: "ui-keybindings-root" }
  });
  ids.rootId = rootAlloc.id;

  let labelAlloc = allocateWidgetId(nextState, "keybindings-label");
  nextState = addWidget(labelAlloc.state, {
    id: labelAlloc.id,
    kind: "label",
    parentId: ids.rootId,
    props: { text: "Keybindings" }
  });
  ids.labelId = labelAlloc.id;

  const items = buildKeybindingItems(options.registry ?? null);
  let listAlloc = allocateWidgetId(nextState, "keybindings-list");
  nextState = addWidget(listAlloc.state, {
    id: listAlloc.id,
    kind: "list",
    parentId: ids.rootId,
    props: { items }
  });
  ids.listId = listAlloc.id;

  const traceKey = options.traceKey ?? null;
  const traceContext = buildKeybindingTraceContext(options, taskId);
  const traceItems = buildKeybindingTraceItems(options.registry ?? null, {
    key: traceKey,
    context: traceContext
  });

  let traceLabelAlloc = allocateWidgetId(nextState, "keybindings-trace-label");
  const traceLabel = traceKey ? `Keybinding Trace: ${traceKey}` : "Keybinding Trace";
  nextState = addWidget(traceLabelAlloc.state, {
    id: traceLabelAlloc.id,
    kind: "label",
    parentId: ids.rootId,
    props: { text: traceLabel }
  });
  ids.traceLabelId = traceLabelAlloc.id;

  let traceListAlloc = allocateWidgetId(nextState, "keybindings-trace-list");
  nextState = addWidget(traceListAlloc.state, {
    id: traceListAlloc.id,
    kind: "list",
    parentId: ids.rootId,
    props: { items: traceItems }
  });
  ids.traceListId = traceListAlloc.id;

  nextState = updateWindow(nextState, allocWindow.id, (window) => ({
    ...window,
    metadata: {
      ...(window.metadata ?? {}),
      role: "keybindings",
      widgets: ids,
      trace: { key: traceKey, context: traceContext }
    }
  }));

  return nextState;
}

export function refreshKeybindingWindow(state, windowId, options = {}) {
  const window = state.windows?.[windowId];
  if (!window || window.metadata?.role !== "keybindings") {
    throw new Error("Window is not a keybinding viewer");
  }
  const widgets = window.metadata?.widgets;
  if (!widgets?.listId) {
    return state;
  }
  const items = buildKeybindingItems(options.registry ?? null);
  let nextState = updateWidget(state, widgets.listId, (widget) => ({
    ...widget,
    props: { ...(widget.props ?? {}), items }
  }));

  const existingTrace = window.metadata?.trace ?? {};
  const traceKey = options.traceKey ?? existingTrace.key ?? null;
  const traceContext = buildKeybindingTraceContext(
    { ...options, traceContext: options.traceContext ?? existingTrace.context ?? {} },
    window.taskId
  );
  if (widgets.traceLabelId) {
    const traceLabel = traceKey ? `Keybinding Trace: ${traceKey}` : "Keybinding Trace";
    nextState = updateWidget(nextState, widgets.traceLabelId, (widget) => ({
      ...widget,
      props: { ...(widget.props ?? {}), text: traceLabel }
    }));
  }
  if (widgets.traceListId) {
    const traceItems = buildKeybindingTraceItems(options.registry ?? null, {
      key: traceKey,
      context: traceContext
    });
    nextState = updateWidget(nextState, widgets.traceListId, (widget) => ({
      ...widget,
      props: { ...(widget.props ?? {}), items: traceItems }
    }));
  }

  return updateWindow(nextState, windowId, (nextWindow) => ({
    ...nextWindow,
    metadata: {
      ...(nextWindow.metadata ?? {}),
      trace: { key: traceKey, context: traceContext }
    }
  }));
}

export function closeKeybindingWindow(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  const windowId =
    options.windowId ??
    findWindowByRole(state, "keybindings", taskId)?.id ??
    null;
  if (!windowId) {
    return state;
  }
  const window = state.windows?.[windowId];
  if (!window || window.metadata?.role !== "keybindings") {
    return state;
  }
  return removeWindow(state, windowId, { reason: options.reason ?? "command" });
}

export function raiseError(state, error, options = {}) {
  const taskId = error.taskId ?? state.workspace?.activeTaskId ?? null;
  if (!taskId) {
    throw new Error("Error must reference a task");
  }
  const coalesceKey = error.coalesceKey ?? `${error.kind ?? "error"}:${error.message ?? ""}`;
  const errors = [...(state.errors ?? [])];
  const existingIndex = errors.findIndex(
    (entry) => entry.taskId === taskId && entry.coalesceKey === coalesceKey && entry.status !== "resolved"
  );

  let nextState = state;
  let errorId = null;
  if (existingIndex !== -1) {
    const existing = errors[existingIndex];
    const count = (existing.count ?? 1) + 1;
    errors[existingIndex] = {
      ...existing,
      count,
      lastTs: error.ts ?? existing.lastTs ?? null,
      message: error.message ?? existing.message,
      restarts: error.restarts ?? existing.restarts ?? []
    };
    nextState = { ...state, errors };
    errorId = existing.id;
  } else {
    const alloc = allocateId(state.idCounters, "error", "error");
    errorId = alloc.id;
    const entry = {
      id: errorId,
      taskId,
      kind: error.kind ?? "error",
      message: error.message ?? "",
      restarts: Array.isArray(error.restarts) ? [...error.restarts] : [],
      coalesceKey,
      ts: error.ts ?? null,
      lastTs: error.ts ?? null,
      status: "open",
      count: 1
    };
    errors.push(entry);
    nextState = { ...state, idCounters: alloc.counters, errors };
  }

  if (options.openDebugger) {
    return openDebuggerWindow(nextState, { taskId, errorId });
  }
  return nextState;
}

export function acknowledgeError(state, errorId) {
  const errors = [...(state.errors ?? [])];
  const index = errors.findIndex((entry) => entry.id === errorId);
  if (index === -1) return state;
  errors[index] = { ...errors[index], status: "acknowledged" };
  return { ...state, errors };
}

export function upsertJob(state, job) {
  if (!job || !job.id) {
    throw new Error("Job must include an id");
  }
  const jobs = [...(state.jobs ?? [])];
  const index = jobs.findIndex((entry) => entry.id === job.id);
  if (index === -1) {
    jobs.push({ ...job });
  } else {
    jobs[index] = { ...jobs[index], ...job };
  }
  return { ...state, jobs };
}

function buildDebuggerContent(state, errorId) {
  const error = state.errors?.find((entry) => entry.id === errorId) ?? null;
  const restarts = Array.isArray(error?.restarts) ? error.restarts : [];
  const summary = error ? `${error.kind ?? "error"}: ${error.message ?? ""}` : "No error selected";
  const items = restarts.map((restart, index) => ({
    id: restart.id ?? `restart-${index}`,
    label: restart.title ?? restart.id ?? `Restart ${index + 1}`
  }));
  if (items.length === 0) {
    items.push({ id: "restart-none", label: "No restarts available" });
  }
  return { summary, items };
}

export function openDebuggerWindow(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  if (!taskId) {
    throw new Error("Debugger requires a task");
  }
  const errorId = options.errorId ?? state.errors?.[state.errors.length - 1]?.id ?? null;

  const existing = findWindowByRole(state, "debugger", taskId);
  if (existing) {
    return refreshDebuggerWindow(state, existing.id, errorId);
  }

  const allocWindow = allocateId(state.idCounters, "window", "debugger");
  let nextState = {
    ...state,
    idCounters: allocWindow.counters
  };
  nextState = addWindow(nextState, {
    id: allocWindow.id,
    taskId,
    kind: "debugger",
    title: "Debugger",
    metadata: { role: "debugger" }
  });

  let rootAlloc = allocateWidgetId(nextState, "debugger-root");
  nextState = addWidget(rootAlloc.state, {
    id: rootAlloc.id,
    kind: "container",
    windowId: allocWindow.id,
    props: { className: "ui-debugger-root" }
  });
  const rootId = rootAlloc.id;

  let titleAlloc = allocateWidgetId(nextState, "debugger-title");
  nextState = addWidget(titleAlloc.state, {
    id: titleAlloc.id,
    kind: "label",
    parentId: rootId,
    props: { text: "Debugger" }
  });

  let summaryAlloc = allocateWidgetId(nextState, "debugger-summary");
  const summary = buildDebuggerContent(nextState, errorId).summary;
  nextState = addWidget(summaryAlloc.state, {
    id: summaryAlloc.id,
    kind: "label",
    parentId: rootId,
    props: { text: summary }
  });

  let listAlloc = allocateWidgetId(nextState, "debugger-restarts");
  const items = buildDebuggerContent(nextState, errorId).items;
  nextState = addWidget(listAlloc.state, {
    id: listAlloc.id,
    kind: "list",
    parentId: rootId,
    props: { items }
  });

  nextState = updateWindow(nextState, allocWindow.id, (window) => ({
    ...window,
    metadata: {
      ...(window.metadata ?? {}),
      role: "debugger",
      widgets: { rootId, summaryId: summaryAlloc.id, restartsId: listAlloc.id },
      errorId
    }
  }));

  return nextState;
}

export function refreshDebuggerWindow(state, windowId, errorId = null) {
  const window = state.windows?.[windowId];
  if (!window || window.metadata?.role !== "debugger") {
    throw new Error("Window is not a debugger");
  }
  const widgets = window.metadata?.widgets ?? {};
  const activeErrorId = errorId ?? window.metadata?.errorId ?? null;
  if (!widgets.summaryId || !widgets.restartsId) {
    return state;
  }
  const { summary, items } = buildDebuggerContent(state, activeErrorId);
  let nextState = updateWidget(state, widgets.summaryId, (widget) => ({
    ...widget,
    props: { ...(widget.props ?? {}), text: summary }
  }));
  nextState = updateWidget(nextState, widgets.restartsId, (widget) => ({
    ...widget,
    props: { ...(widget.props ?? {}), items }
  }));
  nextState = updateWindow(nextState, windowId, (win) => ({
    ...win,
    metadata: { ...(win.metadata ?? {}), errorId: activeErrorId }
  }));
  return nextState;
}
