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
const UI_TURN_PHASES = ["signals", "commands", "render", "backend", "idle"];
const UI_TURN_HISTORY_LIMIT = 8;
const DOM_ESCAPE_HISTORY_LIMIT = 32;
export const COMMAND_PALETTE_FILTER_COMMAND = "ui.command-palette.filter";
export const COMMAND_PALETTE_EXECUTE_COMMAND = "ui.command-palette.execute";
export const COMMAND_PALETTE_SELECT_NEXT_COMMAND = "ui.command-palette.select-next";
export const COMMAND_PALETTE_SELECT_PREV_COMMAND = "ui.command-palette.select-prev";
export const COMMAND_PALETTE_EXECUTE_SELECTION_COMMAND = "ui.command-palette.execute-selected";
export const COMMAND_PALETTE_OPEN_COMMAND = "ui.command-palette.open";
export const COMMAND_PALETTE_CLOSE_COMMAND = "ui.command-palette.close";
export const KEYBINDINGS_OPEN_COMMAND = "ui.keybindings.open";
export const KEYBINDINGS_CLOSE_COMMAND = "ui.keybindings.close";
export const COMMAND_SURFACE_DISMISS_COMMAND = "ui.command-surface.dismiss";
export const TASK_LIST_COMMAND = "ui.task.list";
export const TASK_SWITCH_COMMAND = "ui.task.switch";
export const TASK_CLOSE_COMMAND = "ui.task.close";
export const TASK_ARCHIVE_COMMAND = "ui.task.archive";
export const LAYOUT_SPLIT_COMMAND = "ui.layout.split";
export const LAYOUT_TABS_COMMAND = "ui.layout.tabs";
export const LAYOUT_DOCK_COMMAND = "ui.layout.dock";
export const LAYOUT_SET_ACTIVE_TAB_COMMAND = "ui.layout.set-active-tab";
export const CAPABILITY_REQUEST_COMMAND = "ui.capability.request";
export const CAPABILITY_GRANT_COMMAND = "ui.capability.grant";
export const CAPABILITY_REVOKE_COMMAND = "ui.capability.revoke";
export const SAFE_MODE_ENABLE_COMMAND = "ui.safe-mode.enable";
export const SAFE_MODE_DISABLE_COMMAND = "ui.safe-mode.disable";
export const DOM_ESCAPE_COMMAND = "ui.dom.escape";

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

function sanitizeDomEscapeDetail(detail) {
  if (detail === null || detail === undefined) return {};
  const type = typeof detail;
  if (type === "string" || type === "number" || type === "boolean") {
    return { value: detail };
  }
  if (Array.isArray(detail) || type === "object") {
    try {
      return JSON.parse(JSON.stringify(detail));
    } catch (err) {
      return {};
    }
  }
  return {};
}

function normalizeDomEscape(entry, index) {
  if (!entry || typeof entry !== "object") {
    return {
      id: `dom-escape-${index + 1}`,
      kind: "dom.escape",
      target: null,
      detail: {},
      capability: "dom.escape",
      taskId: null,
      windowId: null,
      commandId: DOM_ESCAPE_COMMAND,
      ts: null
    };
  }
  return {
    id: entry.id ?? `dom-escape-${index + 1}`,
    kind: entry.kind ?? "dom.escape",
    target: entry.target ?? null,
    detail: sanitizeDomEscapeDetail(entry.detail ?? null),
    capability: entry.capability ?? "dom.escape",
    taskId: entry.taskId ?? null,
    windowId: entry.windowId ?? null,
    commandId: entry.commandId ?? DOM_ESCAPE_COMMAND,
    ts: Number.isInteger(entry.ts) ? entry.ts : null
  };
}

function normalizeDomEscapes(entries) {
  if (!Array.isArray(entries)) return [];
  return entries.map((entry, index) => normalizeDomEscape(entry, index));
}

function normalizeUiSignal(signal, index) {
  if (!signal || typeof signal !== "object") {
    return { id: `signal-${index + 1}`, type: "signal", payload: {} };
  }
  return {
    id: signal.id ?? `signal-${index + 1}`,
    type: signal.type ?? "signal",
    payload: signal.payload ?? {}
  };
}

function normalizeUiTurn(turn) {
  if (!turn || typeof turn !== "object") {
    return null;
  }
  const phase = UI_TURN_PHASES.includes(turn.phase) || turn.phase === "yielded" ? turn.phase : "signals";
  const signals = Array.isArray(turn.signals) ? turn.signals.map(normalizeUiSignal) : [];
  return {
    id: turn.id ?? "turn-0",
    phase,
    signals,
    commitPolicy: turn.commitPolicy ?? "rAF",
    yielded: Boolean(turn.yielded),
    yieldReason: turn.yieldReason ?? null
  };
}

function normalizeUiState(ui) {
  if (!ui || typeof ui !== "object") {
    return {
      queue: [],
      turn: null,
      history: [],
      nextTurnId: 1
    };
  }
  const queue = Array.isArray(ui.queue) ? ui.queue.map(normalizeUiSignal) : [];
  const history = Array.isArray(ui.history)
    ? ui.history.map((entry) => ({
        id: entry?.id ?? "turn-0",
        phase: entry?.phase ?? "idle",
        yielded: Boolean(entry?.yielded),
        commitPolicy: entry?.commitPolicy ?? "rAF"
      }))
    : [];
  const nextTurnId = Number.isInteger(ui.nextTurnId) && ui.nextTurnId > 0 ? ui.nextTurnId : 1;
  return {
    queue,
    turn: normalizeUiTurn(ui.turn),
    history,
    nextTurnId
  };
}

function normalizeCapabilityEntry(entry, index) {
  if (!entry || typeof entry !== "object") {
    return {
      id: `capability-${index + 1}`,
      action: "unknown",
      capability: null,
      reason: null,
      taskId: null,
      windowId: null,
      commandId: null
    };
  }
  return {
    id: entry.id ?? `capability-${index + 1}`,
    action: entry.action ?? "unknown",
    capability: entry.capability ?? null,
    reason: entry.reason ?? null,
    taskId: entry.taskId ?? null,
    windowId: entry.windowId ?? null,
    commandId: entry.commandId ?? null
  };
}

function normalizeCapabilities(capabilities) {
  const granted = Array.isArray(capabilities?.granted)
    ? [...new Set(capabilities.granted.filter((cap) => typeof cap === "string"))].sort()
    : [];
  const log = Array.isArray(capabilities?.log)
    ? capabilities.log.map((entry, index) => normalizeCapabilityEntry(entry, index))
    : [];
  return {
    safeMode: Boolean(capabilities?.safeMode),
    granted,
    log
  };
}

function appendCapabilityLog(capabilities, entry) {
  const log = Array.isArray(capabilities?.log) ? capabilities.log : [];
  const normalizedEntry = normalizeCapabilityEntry(entry, log.length);
  return { ...capabilities, log: [...log, normalizedEntry] };
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
    domEscapes: normalizeDomEscapes(options.domEscapes ?? null),
    ui: normalizeUiState(options.ui ?? null),
    capabilities: normalizeCapabilities(options.capabilities ?? null),
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

function taskIsArchived(task) {
  return Boolean(task?.metadata?.archived);
}

export function setActiveTask(state, taskId, options = {}) {
  if (!taskId) {
    return state;
  }
  const tasks = state.tasks ?? {};
  const task = tasks[taskId];
  if (!task) {
    return state;
  }
  const workspace = state.workspace ?? createWorkspace({ id: "workspace-0" });
  const taskIds = Array.isArray(workspace.taskIds) ? [...workspace.taskIds] : [];
  if (!taskIds.includes(taskId) && !taskIsArchived(task)) {
    taskIds.push(taskId);
  }
  let activeWindowId = task.activeWindowId ?? null;
  let updatedTask = task;
  if (!activeWindowId && Array.isArray(task.windowIds) && task.windowIds.length > 0) {
    activeWindowId = task.windowIds[0];
    updatedTask = { ...task, activeWindowId };
  }
  let nextState = {
    ...state,
    workspace: { ...workspace, activeTaskId: taskId, taskIds },
    tasks: updatedTask === task ? tasks : { ...tasks, [taskId]: updatedTask }
  };
  if (options.updateFocus !== false) {
    const target = { taskId, windowId: activeWindowId ?? null, widgetId: null, presentationId: null };
    nextState = setFocusCore(nextState, target, options.reason ?? "command", options.seq ?? null);
  }
  return nextState;
}

export function archiveTask(state, taskId, options = {}) {
  if (!taskId) {
    return state;
  }
  const task = state.tasks?.[taskId];
  if (!task) {
    return state;
  }
  const metadata = { ...(task.metadata ?? {}), archived: true, archivedAt: options.archivedAt ?? null };
  const tasks = { ...(state.tasks ?? {}), [taskId]: { ...task, metadata } };
  const workspace = state.workspace ?? createWorkspace({ id: "workspace-0" });
  const taskIds = Array.isArray(workspace.taskIds)
    ? workspace.taskIds.filter((id) => id !== taskId)
    : [];
  const wasActive = workspace.activeTaskId === taskId;
  let nextState = {
    ...state,
    tasks,
    workspace: { ...workspace, taskIds, activeTaskId: wasActive ? (taskIds[0] ?? null) : workspace.activeTaskId }
  };
  if (wasActive) {
    if (nextState.workspace.activeTaskId) {
      nextState = setActiveTask(nextState, nextState.workspace.activeTaskId, { reason: options.reason });
    } else {
      nextState = setFocusCore(nextState, null, options.reason ?? "command");
    }
  }
  return nextState;
}

export function closeTask(state, taskId, options = {}) {
  if (!taskId) {
    return state;
  }
  const task = state.tasks?.[taskId];
  if (!task) {
    return state;
  }
  let nextState = state;
  const windowIds = Array.isArray(task.windowIds) ? [...task.windowIds] : [];
  for (const windowId of windowIds) {
    if (nextState.windows?.[windowId]) {
      nextState = removeWindow(nextState, windowId, { reason: options.reason });
    }
  }
  for (const [windowId, window] of Object.entries(nextState.windows ?? {})) {
    if (window.taskId === taskId) {
      nextState = removeWindow(nextState, windowId, { reason: options.reason });
    }
  }

  const tasks = { ...(nextState.tasks ?? {}) };
  delete tasks[taskId];
  const workspace = nextState.workspace ?? createWorkspace({ id: "workspace-0" });
  const taskIds = Array.isArray(workspace.taskIds)
    ? workspace.taskIds.filter((id) => id !== taskId)
    : [];
  const wasActive = workspace.activeTaskId === taskId;
  let activeTaskId = wasActive ? (taskIds[0] ?? null) : workspace.activeTaskId;
  nextState = {
    ...nextState,
    tasks,
    workspace: { ...workspace, taskIds, activeTaskId }
  };
  if (wasActive) {
    if (activeTaskId) {
      nextState = setActiveTask(nextState, activeTaskId, { reason: options.reason });
    } else {
      nextState = setFocusCore(nextState, null, options.reason ?? "command");
    }
  }
  return nextState;
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

  if (nextState.layout?.nodes) {
    const layout = nextState.layout;
    let changed = false;
    const nodes = {};
    for (const [id, node] of Object.entries(layout.nodes)) {
      if (node?.kind === "leaf" && node.props?.windowId === windowId) {
        nodes[id] = { ...node, props: { ...(node.props ?? {}), windowId: null } };
        changed = true;
      } else {
        nodes[id] = node;
      }
    }
    if (changed) {
      nextState = { ...nextState, layout: { ...layout, nodes } };
    }
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

export function requestCapability(state, capability, options = {}) {
  if (!capability) return state;
  const capabilities = normalizeCapabilities(state.capabilities ?? null);
  const nextCaps = appendCapabilityLog(capabilities, {
    action: "request",
    capability,
    reason: options.reason ?? null,
    taskId: options.taskId ?? null,
    windowId: options.windowId ?? null,
    commandId: options.commandId ?? null
  });
  return { ...state, capabilities: nextCaps };
}

export function grantCapability(state, capability, options = {}) {
  if (!capability) return state;
  const capabilities = normalizeCapabilities(state.capabilities ?? null);
  if (capabilities.granted.includes(capability)) {
    return state;
  }
  const granted = [...capabilities.granted, capability].sort();
  const nextCaps = appendCapabilityLog({ ...capabilities, granted }, {
    action: "grant",
    capability,
    reason: options.reason ?? null,
    taskId: options.taskId ?? null,
    windowId: options.windowId ?? null,
    commandId: options.commandId ?? null
  });
  return { ...state, capabilities: nextCaps };
}

export function revokeCapability(state, capability, options = {}) {
  if (!capability) return state;
  const capabilities = normalizeCapabilities(state.capabilities ?? null);
  if (!capabilities.granted.includes(capability)) {
    return state;
  }
  const granted = capabilities.granted.filter((entry) => entry !== capability);
  const nextCaps = appendCapabilityLog({ ...capabilities, granted }, {
    action: "revoke",
    capability,
    reason: options.reason ?? null,
    taskId: options.taskId ?? null,
    windowId: options.windowId ?? null,
    commandId: options.commandId ?? null
  });
  return { ...state, capabilities: nextCaps };
}

export function setSafeMode(state, enabled, options = {}) {
  const capabilities = normalizeCapabilities(state.capabilities ?? null);
  const nextEnabled = Boolean(enabled);
  if (capabilities.safeMode === nextEnabled) {
    return state;
  }
  const nextCaps = appendCapabilityLog({ ...capabilities, safeMode: nextEnabled }, {
    action: nextEnabled ? "safe-mode-enabled" : "safe-mode-disabled",
    reason: options.reason ?? null,
    taskId: options.taskId ?? null,
    windowId: options.windowId ?? null,
    commandId: options.commandId ?? null
  });
  return { ...state, capabilities: nextCaps };
}

export function hasCapability(state, capability) {
  if (!capability) return true;
  const capabilities = state.capabilities ?? {};
  if (capabilities.safeMode) return false;
  return Array.isArray(capabilities.granted) && capabilities.granted.includes(capability);
}

export function setLayout(state, layout) {
  const normalized = normalizeLayout(layout, state.idCounters);
  return { ...state, layout: normalized.layout, idCounters: normalized.counters };
}

export function recordDomEscape(state, entry, options = {}) {
  const escapes = normalizeDomEscapes(state.domEscapes ?? null);
  const normalized = normalizeDomEscape(
    { ...entry, ts: entry?.ts ?? options.ts ?? null },
    escapes.length
  );
  const nextEscapes = [...escapes, normalized];
  const trimmed =
    nextEscapes.length > DOM_ESCAPE_HISTORY_LIMIT
      ? nextEscapes.slice(nextEscapes.length - DOM_ESCAPE_HISTORY_LIMIT)
      : nextEscapes;
  return { ...state, domEscapes: trimmed };
}

export function recordEvent(state, entry) {
  if (!entry || typeof entry !== "object") {
    throw new Error("Event entry must be an object");
  }
  const eventLog = recordEventLog(state.eventLog ?? null, entry);
  return { ...state, eventLog };
}

function buildUiEvent(options, type, payload) {
  if (!options?.recordEvent) return null;
  if (!Number.isInteger(options.seq)) {
    throw new Error("UI event requires integer seq when recording");
  }
  const entry = {
    seq: options.seq,
    type,
    payload: payload ?? {}
  };
  if (Number.isInteger(options.ts)) {
    entry.ts = options.ts;
  }
  if (typeof options.target === "string") {
    entry.target = options.target;
  }
  return entry;
}

export function enqueueUiSignal(state, signal, options = {}) {
  const ui = normalizeUiState(state.ui ?? null);
  const normalized = normalizeUiSignal(signal, ui.queue.length);
  const nextQueue = [...ui.queue, normalized];
  let nextState = { ...state, ui: { ...ui, queue: nextQueue } };
  const event = buildUiEvent(options, "ui:signal.enqueue", {
    signal: normalized,
    queueLength: nextQueue.length
  });
  if (event) {
    nextState = recordEvent(nextState, event);
  }
  return nextState;
}

export function beginUiTurn(state, options = {}) {
  const ui = normalizeUiState(state.ui ?? null);
  if (ui.turn) {
    throw new Error("UI turn already active");
  }
  const turnId = `turn-${ui.nextTurnId}`;
  const drainSignals = options.drainSignals !== false;
  const signals = drainSignals ? ui.queue : [];
  const queue = drainSignals ? [] : ui.queue;
  const turn = {
    id: turnId,
    phase: "signals",
    signals,
    commitPolicy: options.commitPolicy ?? "rAF",
    yielded: false,
    yieldReason: null
  };
  let nextState = {
    ...state,
    ui: {
      ...ui,
      queue,
      turn,
      nextTurnId: ui.nextTurnId + 1
    }
  };
  const event = buildUiEvent(options, "ui:turn.begin", {
    turnId,
    commitPolicy: turn.commitPolicy,
    signalCount: signals.length,
    drainedSignals: drainSignals
  });
  if (event) {
    nextState = recordEvent(nextState, event);
  }
  return nextState;
}

export function advanceUiTurn(state, phase, options = {}) {
  const ui = normalizeUiState(state.ui ?? null);
  if (!ui.turn) {
    throw new Error("UI turn not active");
  }
  const nextPhase = phase ?? ui.turn.phase;
  if (!UI_TURN_PHASES.includes(nextPhase) && nextPhase !== "yielded") {
    throw new Error(`Unknown UI turn phase: ${nextPhase}`);
  }
  if (UI_TURN_PHASES.includes(nextPhase) && UI_TURN_PHASES.includes(ui.turn.phase)) {
    const currentIndex = UI_TURN_PHASES.indexOf(ui.turn.phase);
    const nextIndex = UI_TURN_PHASES.indexOf(nextPhase);
    if (nextIndex < currentIndex) {
      throw new Error("UI turn phase cannot move backwards");
    }
  }
  let nextState = { ...state, ui: { ...ui, turn: { ...ui.turn, phase: nextPhase } } };
  const event = buildUiEvent(options, "ui:turn.phase", {
    turnId: ui.turn.id,
    phase: nextPhase
  });
  if (event) {
    nextState = recordEvent(nextState, event);
  }
  return nextState;
}

export function yieldUiTurn(state, reason = null, options = {}) {
  let next = advanceUiTurn(state, "yielded", { recordEvent: false });
  const ui = normalizeUiState(next.ui ?? null);
  if (!ui.turn) return next;
  next = {
    ...next,
    ui: {
      ...ui,
      turn: { ...ui.turn, yielded: true, yieldReason: reason }
    }
  };
  const event = buildUiEvent(options, "ui:turn.yield", {
    turnId: ui.turn.id,
    reason
  });
  if (event) {
    next = recordEvent(next, event);
  }
  return next;
}

export function endUiTurn(state, options = {}) {
  const ui = normalizeUiState(state.ui ?? null);
  if (!ui.turn) return state;
  const turnId = ui.turn.id;
  const turnPhase = ui.turn.phase;
  const turnYielded = ui.turn.yielded;
  const historyEntry = {
    id: turnId,
    phase: turnPhase,
    yielded: turnYielded,
    commitPolicy: ui.turn.commitPolicy
  };
  const history = [...ui.history, historyEntry];
  const trimmed =
    history.length > UI_TURN_HISTORY_LIMIT
      ? history.slice(history.length - UI_TURN_HISTORY_LIMIT)
      : history;
  let nextState = { ...state, ui: { ...ui, turn: null, history: trimmed } };
  const event = buildUiEvent(options, "ui:turn.end", {
    turnId,
    phase: turnPhase,
    yielded: turnYielded
  });
  if (event) {
    nextState = recordEvent(nextState, event);
  }
  return nextState;
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

function summarizeTasks(state) {
  const items = [];
  const tasks = state.tasks ?? {};
  const workspace = state.workspace ?? null;
  const activeId = workspace?.activeTaskId ?? null;
  const orderedIds = Array.isArray(workspace?.taskIds) ? [...workspace.taskIds] : [];
  const extraIds = Object.keys(tasks)
    .filter((id) => !orderedIds.includes(id))
    .sort((a, b) => a.localeCompare(b));
  const taskIds = [...orderedIds, ...extraIds];
  for (const id of taskIds) {
    const task = tasks[id];
    if (!task) continue;
    const flags = [];
    if (id === activeId) flags.push("active");
    if (taskIsArchived(task)) flags.push("archived");
    const suffix = flags.length > 0 ? ` (${flags.join(", ")})` : "";
    const title = task.title ?? "Untitled";
    items.push({
      id: `task-${id}`,
      label: `${title} [${id}]${suffix}`
    });
  }
  if (items.length === 0) {
    items.push({ id: "task-none", label: "No tasks" });
  }
  return items;
}

function summarizePresentations(state) {
  const items = [];
  const entries = Object.values(state.presentations ?? {}).sort((a, b) => (a.id ?? "").localeCompare(b.id ?? ""));
  for (const presentation of entries) {
    const type = presentation.type ?? "presentation";
    const objectId = presentation.objectId ?? "unknown";
    const widgetId = presentation.widgetId ?? "none";
    items.push({
      id: `pres-${presentation.id ?? "unknown"}`,
      label: `${type}(${objectId}) widget=${widgetId}`
    });
  }
  if (items.length === 0) {
    items.push({ id: "pres-none", label: "No presentations" });
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
  const baseTrace = Array.isArray(resolved.trace) ? resolved.trace : [];
  const precedence = Array.isArray(registry.precedence) ? registry.precedence : [];
  const seenScopes = new Set(baseTrace.map((entry) => entry.scope));
  const trace = [...baseTrace];
  if (resolved.commandId && baseTrace.length < precedence.length) {
    for (const scope of precedence) {
      if (seenScopes.has(scope)) continue;
      const scopeId = scope === "global" ? null : (ctx?.[`${scope}Id`] ?? null);
      trace.push({
        scope,
        scopeId,
        key,
        commandId: null,
        matched: false,
        reason: "skipped-after-match"
      });
    }
  }
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

function buildTaskListItems(state, options = {}) {
  const tasks = state.tasks ?? {};
  const workspace = state.workspace ?? null;
  const activeId = workspace?.activeTaskId ?? null;
  const includeArchived = options.includeArchived ?? false;
  const orderedIds = Array.isArray(workspace?.taskIds) ? [...workspace.taskIds] : [];
  const extraIds = Object.keys(tasks)
    .filter((id) => !orderedIds.includes(id))
    .sort((a, b) => a.localeCompare(b));
  const taskIds = [...orderedIds, ...extraIds];
  const items = [];
  for (const id of taskIds) {
    const task = tasks[id];
    if (!task) continue;
    if (taskIsArchived(task) && !includeArchived && !orderedIds.includes(id)) {
      continue;
    }
    const flags = [];
    if (id === activeId) flags.push("active");
    if (taskIsArchived(task)) flags.push("archived");
    const suffix = flags.length > 0 ? ` (${flags.join(", ")})` : "";
    const title = task.title ?? "Untitled";
    items.push({
      id,
      label: `${title} [${id}]${suffix}`,
      taskId: id,
      selected: id === activeId
    });
  }
  if (items.length === 0) {
    items.push({ id: "task-none", label: "No tasks" });
  }
  return items;
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

function summarizeUiTurn(state) {
  const ui = normalizeUiState(state.ui ?? null);
  const items = [];
  if (!ui.turn) {
    items.push({ id: "turn-idle", label: "Turn: idle" });
  } else {
    items.push({ id: `turn-${ui.turn.id}`, label: `Turn: ${ui.turn.id} (${ui.turn.phase})` });
    if (ui.turn.yielded) {
      items.push({
        id: `turn-${ui.turn.id}-yield`,
        label: `Yielded: ${ui.turn.yieldReason ?? "unspecified"}`
      });
    }
  }
  items.push({ id: "turn-queue", label: `Queued signals: ${ui.queue.length}` });
  if (ui.history.length > 0) {
    const last = ui.history[ui.history.length - 1];
    items.push({
      id: "turn-last",
      label: `Last turn: ${last.id} (${last.phase})`
    });
  }
  return items;
}

function summarizeDomEscapes(state) {
  const escapes = normalizeDomEscapes(state.domEscapes ?? null);
  if (escapes.length === 0) {
    return [{ id: "dom-escape-none", label: "No DOM escapes recorded" }];
  }
  return escapes.map((entry) => ({
    id: entry.id ?? "dom-escape",
    label: `${entry.kind ?? "dom.escape"}${entry.target ? ` → ${entry.target}` : ""}`
  }));
}

function summarizeCapabilities(state) {
  const capabilities = normalizeCapabilities(state.capabilities ?? null);
  const items = [];
  items.push({
    id: "cap-safe-mode",
    label: `Safe mode: ${capabilities.safeMode ? "enabled" : "disabled"}`
  });
  if (capabilities.granted.length === 0) {
    items.push({ id: "cap-none", label: "No capabilities granted" });
  } else {
    for (const cap of capabilities.granted) {
      items.push({ id: `cap-${cap}`, label: `Granted: ${cap}` });
    }
  }
  if (capabilities.log.length > 0) {
    for (const entry of capabilities.log) {
      const action = entry.action ?? "event";
      const capability = entry.capability ? ` ${entry.capability}` : "";
      items.push({ id: `cap-log-${entry.id}`, label: `Log: ${action}${capability}` });
    }
  }
  return items;
}

function buildInspectorSections(state) {
  return {
    tasks: summarizeTasks(state),
    focus: summarizeFocus(state),
    commands: summarizeCommands(state),
    capabilities: summarizeCapabilities(state),
    domEscapes: summarizeDomEscapes(state),
    turns: summarizeUiTurn(state),
    presentations: summarizePresentations(state),
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
    ["tasks", "Tasks"],
    ["focus", "Focus"],
    ["commands", "Commands"],
    ["capabilities", "Capabilities"],
    ["domEscapes", "DOM Escapes"],
    ["turns", "UI Turn"],
    ["presentations", "Presentations"],
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

export function openTaskListWindow(state, options = {}) {
  const taskId = options.taskId ?? state.workspace?.activeTaskId ?? null;
  if (!taskId) {
    throw new Error("Task list requires a task");
  }
  const existing = findWindowByRole(state, "task-list", taskId);
  if (existing) {
    return refreshTaskListWindow(state, existing.id, options);
  }

  const allocWindow = allocateId(state.idCounters, "window", "task-list");
  let nextState = {
    ...state,
    idCounters: allocWindow.counters
  };
  nextState = addWindow(nextState, {
    id: allocWindow.id,
    taskId,
    kind: "task-list",
    title: "Tasks",
    metadata: { role: "task-list" }
  });

  const includeArchived = options.includeArchived ?? false;
  const items = buildTaskListItems(nextState, { includeArchived });

  let ids = {};
  let rootAlloc = allocateWidgetId(nextState, "task-list-root");
  nextState = addWidget(rootAlloc.state, {
    id: rootAlloc.id,
    kind: "container",
    windowId: allocWindow.id,
    props: { className: "ui-task-list-root" }
  });
  ids.rootId = rootAlloc.id;

  let labelAlloc = allocateWidgetId(nextState, "task-list-label");
  nextState = addWidget(labelAlloc.state, {
    id: labelAlloc.id,
    kind: "label",
    parentId: ids.rootId,
    props: { text: "Tasks" }
  });
  ids.labelId = labelAlloc.id;

  let listAlloc = allocateWidgetId(nextState, "task-list");
  nextState = addWidget(listAlloc.state, {
    id: listAlloc.id,
    kind: "list",
    parentId: ids.rootId,
    props: { items, itemCommand: TASK_SWITCH_COMMAND }
  });
  ids.listId = listAlloc.id;

  nextState = updateWindow(nextState, allocWindow.id, (window) => ({
    ...window,
    metadata: {
      ...(window.metadata ?? {}),
      role: "task-list",
      widgets: ids,
      taskList: { includeArchived }
    }
  }));

  return nextState;
}

export function refreshTaskListWindow(state, windowId, options = {}) {
  const window = state.windows?.[windowId];
  if (!window || window.metadata?.role !== "task-list") {
    throw new Error("Window is not a task list");
  }
  const widgets = window.metadata?.widgets;
  if (!widgets?.listId) {
    return state;
  }
  const includeArchived =
    options.includeArchived ?? window.metadata?.taskList?.includeArchived ?? false;
  const items = buildTaskListItems(state, { includeArchived });
  let nextState = updateWidget(state, widgets.listId, (widget) => ({
    ...widget,
    props: { ...(widget.props ?? {}), items }
  }));
  return updateWindow(nextState, windowId, (nextWindow) => ({
    ...nextWindow,
    metadata: {
      ...(nextWindow.metadata ?? {}),
      taskList: { includeArchived }
    }
  }));
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

function resolveTaskTargetId(state, ctx, options = {}) {
  return (
    options.taskId ??
    ctx?.targetTaskId ??
    ctx?.item?.taskId ??
    ctx?.itemId ??
    ctx?.taskId ??
    state.workspace?.activeTaskId ??
    null
  );
}

function findLayoutLeafForWindow(layout, windowId) {
  if (!layout?.nodes || !windowId) return null;
  for (const [id, node] of Object.entries(layout.nodes)) {
    if (node?.kind === "leaf" && node.props?.windowId === windowId) {
      return id;
    }
  }
  return null;
}

function findLayoutParent(layout, childId) {
  if (!layout?.nodes || !childId) return null;
  for (const [id, node] of Object.entries(layout.nodes)) {
    const children = node?.children ?? [];
    if (children.includes(childId)) {
      return { parentId: id, parent: node };
    }
  }
  return null;
}

function resolveLayoutTargetId(state, ctx) {
  const direct =
    ctx?.layoutId ??
    ctx?.targetLayoutId ??
    ctx?.item?.layoutId ??
    ctx?.itemId ??
    null;
  if (direct) {
    return direct;
  }
  const windowId = ctx?.windowId ?? state.focus?.windowId ?? null;
  return findLayoutLeafForWindow(state.layout, windowId);
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

export function registerTaskCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const listId = options.listCommandId ?? TASK_LIST_COMMAND;
  const switchId = options.switchCommandId ?? TASK_SWITCH_COMMAND;
  const closeId = options.closeCommandId ?? TASK_CLOSE_COMMAND;
  const archiveId = options.archiveCommandId ?? TASK_ARCHIVE_COMMAND;

  const ensure = (id, command) => {
    if (!registry.commands.has(id)) {
      registerCommand(registry, { ...command, id });
    }
  };

  ensure(listId, {
    title: "List Tasks",
    doc: "Open the task list for the current workspace.",
    exec: (ctx) =>
      openTaskListWindow(ctx.state, {
        taskId: ctx.taskId ?? ctx.state.workspace?.activeTaskId ?? null,
        includeArchived: ctx.includeArchived ?? false
      })
  });

  ensure(switchId, {
    title: "Switch Task",
    doc: "Switch to the selected task.",
    enabled: (ctx) => {
      const target = resolveTaskTargetId(ctx.state, ctx);
      return target && ctx.state.tasks?.[target]
        ? { enabled: true, reason: null }
        : { enabled: false, reason: "No target task" };
    },
    exec: (ctx) => {
      const target = resolveTaskTargetId(ctx.state, ctx);
      if (!target) {
        return ctx.state;
      }
      return setActiveTask(ctx.state, target, { reason: "command" });
    }
  });

  ensure(closeId, {
    title: "Close Task",
    doc: "Close the selected task and its windows.",
    enabled: (ctx) => {
      const target = resolveTaskTargetId(ctx.state, ctx);
      return target && ctx.state.tasks?.[target]
        ? { enabled: true, reason: null }
        : { enabled: false, reason: "No target task" };
    },
    exec: (ctx) => {
      const target = resolveTaskTargetId(ctx.state, ctx);
      if (!target) {
        return ctx.state;
      }
      return closeTask(ctx.state, target, { reason: "command" });
    }
  });

  ensure(archiveId, {
    title: "Archive Task",
    doc: "Archive the selected task.",
    enabled: (ctx) => {
      const target = resolveTaskTargetId(ctx.state, ctx);
      const task = target ? ctx.state.tasks?.[target] : null;
      if (!task) {
        return { enabled: false, reason: "No target task" };
      }
      if (taskIsArchived(task)) {
        return { enabled: false, reason: "Task already archived" };
      }
      return { enabled: true, reason: null };
    },
    exec: (ctx) => {
      const target = resolveTaskTargetId(ctx.state, ctx);
      if (!target) {
        return ctx.state;
      }
      return archiveTask(ctx.state, target, { reason: "command" });
    }
  });

  return registry;
}

export function registerLayoutCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const splitId = options.splitCommandId ?? LAYOUT_SPLIT_COMMAND;
  const tabsId = options.tabsCommandId ?? LAYOUT_TABS_COMMAND;
  const dockId = options.dockCommandId ?? LAYOUT_DOCK_COMMAND;
  const activeTabId = options.activeTabCommandId ?? LAYOUT_SET_ACTIVE_TAB_COMMAND;

  const ensure = (id, command) => {
    if (!registry.commands.has(id)) {
      registerCommand(registry, { ...command, id });
    }
  };

  ensure(splitId, {
    title: "Split Layout",
    doc: "Split the active layout leaf.",
    enabled: (ctx) => {
      const target = resolveLayoutTargetId(ctx.state, ctx);
      return target ? { enabled: true, reason: null } : { enabled: false, reason: "No layout target" };
    },
    exec: (ctx) => {
      const target = resolveLayoutTargetId(ctx.state, ctx);
      if (!target) return ctx.state;
      const axis = ctx.axis ?? "h";
      const ratio = Number.isFinite(ctx.ratio) ? ctx.ratio : 0.5;
      const insert = ctx.insert ?? "after";
      const windowId = ctx.newWindowId ?? null;
      return splitLayout(ctx.state, target, axis, ratio, { insert, windowId });
    }
  });

  ensure(tabsId, {
    title: "Wrap In Tabs",
    doc: "Wrap the active layout leaf in a tabs container.",
    enabled: (ctx) => {
      const target = resolveLayoutTargetId(ctx.state, ctx);
      return target ? { enabled: true, reason: null } : { enabled: false, reason: "No layout target" };
    },
    exec: (ctx) => {
      const target = resolveLayoutTargetId(ctx.state, ctx);
      if (!target) return ctx.state;
      const newWindowId = ctx.newWindowId ?? null;
      const newTab = newWindowId ? { windowId: newWindowId } : null;
      return wrapInTabs(ctx.state, target, {
        newTab,
        insert: ctx.insert ?? "after",
        activateNew: Boolean(ctx.activateNew)
      });
    }
  });

  ensure(activeTabId, {
    title: "Activate Tab",
    doc: "Set the active tab in a tabs container.",
    enabled: (ctx) => {
      const tabsIdValue = ctx.tabsId ?? null;
      const tabId = ctx.tabId ?? resolveLayoutTargetId(ctx.state, ctx);
      if (!tabsIdValue || !tabId) {
        return { enabled: false, reason: "No tab target" };
      }
      return { enabled: true, reason: null };
    },
    exec: (ctx) => {
      const tabId = ctx.tabId ?? resolveLayoutTargetId(ctx.state, ctx);
      const layout = ctx.state.layout;
      let tabsIdValue = ctx.tabsId ?? null;
      if (!tabsIdValue && layout && tabId) {
        const parent = findLayoutParent(layout, tabId);
        if (parent?.parent?.kind === "tabs") {
          tabsIdValue = parent.parentId;
        }
      }
      if (!tabsIdValue || !tabId) return ctx.state;
      return setActiveTab(ctx.state, tabsIdValue, tabId);
    }
  });

  ensure(dockId, {
    title: "Dock Layout",
    doc: "Dock the active layout leaf into a region.",
    enabled: (ctx) => {
      const target = resolveLayoutTargetId(ctx.state, ctx);
      return target ? { enabled: true, reason: null } : { enabled: false, reason: "No layout target" };
    },
    exec: (ctx) => {
      const target = resolveLayoutTargetId(ctx.state, ctx);
      if (!target) return ctx.state;
      const region = ctx.region ?? "left";
      return dockLayout(ctx.state, target, region);
    }
  });

  return registry;
}

export function registerCapabilityCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const requestId = options.requestCommandId ?? CAPABILITY_REQUEST_COMMAND;
  const grantId = options.grantCommandId ?? CAPABILITY_GRANT_COMMAND;
  const revokeId = options.revokeCommandId ?? CAPABILITY_REVOKE_COMMAND;
  const safeModeEnableId = options.safeModeEnableCommandId ?? SAFE_MODE_ENABLE_COMMAND;
  const safeModeDisableId = options.safeModeDisableCommandId ?? SAFE_MODE_DISABLE_COMMAND;

  const resolveCapability = (ctx) => ctx.capability ?? ctx.payload?.capability ?? ctx.itemId ?? null;

  const ensure = (id, command) => {
    if (!registry.commands.has(id)) {
      registerCommand(registry, { ...command, id });
    }
  };

  ensure(requestId, {
    title: "Request Capability",
    doc: "Record a capability request for policy mediation.",
    enabled: (ctx) => {
      const capability = resolveCapability(ctx);
      return capability
        ? { enabled: true, reason: null }
        : { enabled: false, reason: "No capability specified" };
    },
    exec: (ctx) => {
      const capability = resolveCapability(ctx);
      if (!capability) return ctx.state;
      return requestCapability(ctx.state, capability, {
        reason: ctx.reason ?? ctx.payload?.reason ?? null,
        taskId: ctx.taskId ?? null,
        windowId: ctx.windowId ?? null,
        commandId: requestId
      });
    }
  });

  ensure(grantId, {
    title: "Grant Capability",
    doc: "Grant a capability after mediation.",
    enabled: (ctx) => {
      const capability = resolveCapability(ctx);
      if (!capability) {
        return { enabled: false, reason: "No capability specified" };
      }
      const granted = normalizeCapabilities(ctx.state.capabilities ?? null).granted;
      return granted.includes(capability)
        ? { enabled: false, reason: "Capability already granted" }
        : { enabled: true, reason: null };
    },
    exec: (ctx) => {
      const capability = resolveCapability(ctx);
      if (!capability) return ctx.state;
      return grantCapability(ctx.state, capability, {
        reason: ctx.reason ?? ctx.payload?.reason ?? null,
        taskId: ctx.taskId ?? null,
        windowId: ctx.windowId ?? null,
        commandId: grantId
      });
    }
  });

  ensure(revokeId, {
    title: "Revoke Capability",
    doc: "Revoke a previously granted capability.",
    enabled: (ctx) => {
      const capability = resolveCapability(ctx);
      if (!capability) {
        return { enabled: false, reason: "No capability specified" };
      }
      const granted = normalizeCapabilities(ctx.state.capabilities ?? null).granted;
      return granted.includes(capability)
        ? { enabled: true, reason: null }
        : { enabled: false, reason: "Capability not granted" };
    },
    exec: (ctx) => {
      const capability = resolveCapability(ctx);
      if (!capability) return ctx.state;
      return revokeCapability(ctx.state, capability, {
        reason: ctx.reason ?? ctx.payload?.reason ?? null,
        taskId: ctx.taskId ?? null,
        windowId: ctx.windowId ?? null,
        commandId: revokeId
      });
    }
  });

  ensure(safeModeEnableId, {
    title: "Enable Safe Mode",
    doc: "Disable all capability-granted escapes.",
    enabled: (ctx) =>
      ctx.state.capabilities?.safeMode ? { enabled: false, reason: "Safe mode already enabled" } : { enabled: true, reason: null },
    exec: (ctx) =>
      setSafeMode(ctx.state, true, {
        reason: ctx.reason ?? ctx.payload?.reason ?? null,
        taskId: ctx.taskId ?? null,
        windowId: ctx.windowId ?? null,
        commandId: safeModeEnableId
      })
  });

  ensure(safeModeDisableId, {
    title: "Disable Safe Mode",
    doc: "Re-enable capability-granted escapes.",
    enabled: (ctx) =>
      ctx.state.capabilities?.safeMode ? { enabled: true, reason: null } : { enabled: false, reason: "Safe mode already disabled" },
    exec: (ctx) =>
      setSafeMode(ctx.state, false, {
        reason: ctx.reason ?? ctx.payload?.reason ?? null,
        taskId: ctx.taskId ?? null,
        windowId: ctx.windowId ?? null,
        commandId: safeModeDisableId
      })
  });

  return registry;
}

export function registerDomEscapeCommands(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const escapeId = options.escapeCommandId ?? DOM_ESCAPE_COMMAND;
  const capability = options.capability ?? "dom.escape";

  if (!registry.commands.has(escapeId)) {
    registerCommand(registry, {
      id: escapeId,
      title: "DOM Escape",
      doc: "Execute a capability-gated DOM escape hatch.",
      capability,
      exec: (ctx) => {
        const detail = ctx.detail ?? ctx.payload?.detail ?? null;
        const target = ctx.target ?? ctx.payload?.target ?? null;
        const kind = ctx.kind ?? ctx.payload?.kind ?? "dom.escape";
        return recordDomEscape(ctx.state, {
          kind,
          target,
          detail,
          capability,
          taskId: ctx.taskId ?? null,
          windowId: ctx.windowId ?? null,
          commandId: escapeId,
          ts: ctx.ts ?? null
        });
      }
    });
  }

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
  const dismissId = options.dismissCommandId ?? COMMAND_SURFACE_DISMISS_COMMAND;
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

  ensure(dismissId, {
    title: "Dismiss Command Surface",
    doc: "Close the active command palette or keybinding viewer window.",
    metadata: { paletteHidden: true },
    exec: (ctx) => {
      const taskId = ctx.taskId ?? ctx.state.workspace?.activeTaskId ?? null;
      const palette = findWindowByRole(ctx.state, "command-palette", taskId);
      if (palette) {
        return closeCommandPaletteWindow(ctx.state, { windowId: palette.id, taskId });
      }
      const keybindings = findWindowByRole(ctx.state, "keybindings", taskId);
      if (keybindings) {
        return closeKeybindingWindow(ctx.state, { windowId: keybindings.id, taskId });
      }
      return ctx.state;
    }
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

export function bindCommandSurfaceDefaults(registry, options = {}) {
  if (!registry) {
    throw new Error("Registry is required");
  }
  const scope = options.scope ?? "global";
  const taskId = options.taskId ?? null;
  const hasScopeId = scope !== "global";
  if (hasScopeId && !taskId) {
    throw new Error("Task id required for non-global surface bindings");
  }
  const paletteOpenId = options.paletteOpenCommandId ?? COMMAND_PALETTE_OPEN_COMMAND;
  const keybindingsOpenId = options.keybindingsOpenCommandId ?? KEYBINDINGS_OPEN_COMMAND;
  const dismissId = options.dismissCommandId ?? COMMAND_SURFACE_DISMISS_COMMAND;
  const paletteKey = options.paletteKey ?? "Ctrl+Shift+P";
  const keybindingsKey = options.keybindingsKey ?? "Ctrl+Shift+K";
  const dismissKey = options.dismissKey ?? "Escape";

  const bind = (key, commandId) => {
    bindKey(registry, scope, key, commandId, hasScopeId ? taskId : null);
  };
  bind(paletteKey, paletteOpenId);
  bind(keybindingsKey, keybindingsOpenId);
  bind(dismissKey, dismissId);
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
