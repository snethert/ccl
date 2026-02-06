import { allocateId } from "./ids.mjs";

export const FOCUS_REASONS = {
  COMMAND: "command",
  USER: "user",
  PROGRAM: "program",
  RESTORE: "restore",
  RECONCILE: "reconcile"
};

export function normalizeFocusTarget(target) {
  if (target === null || target === undefined) return null;
  if (typeof target === "string" || typeof target === "number") {
    return {
      taskId: null,
      windowId: String(target),
      widgetId: null,
      presentationId: null
    };
  }
  if (typeof target !== "object") {
    throw new Error("Focus target must be an object or string");
  }
  return {
    taskId: target.taskId ?? null,
    windowId: target.windowId ?? null,
    widgetId: target.widgetId ?? null,
    presentationId: target.presentationId ?? null
  };
}

export function normalizeFocusHistory(history = []) {
  if (!Array.isArray(history)) return [];
  return history.map((entry) => ({
    seq: entry.seq ?? null,
    target: normalizeFocusTarget(entry.target),
    reason: entry.reason ?? FOCUS_REASONS.COMMAND
  }));
}

export function sameFocusTarget(a, b) {
  const left = normalizeFocusTarget(a);
  const right = normalizeFocusTarget(b);
  if (!left && !right) return true;
  if (!left || !right) return false;
  return (
    left.taskId === right.taskId &&
    left.windowId === right.windowId &&
    left.widgetId === right.widgetId &&
    left.presentationId === right.presentationId
  );
}

function completeTargetFromState(state, target) {
  const next = { ...target };
  if (next.widgetId && (!next.windowId || !next.taskId)) {
    const widget = state.widgets?.[next.widgetId];
    if (widget?.windowId && !next.windowId) {
      next.windowId = widget.windowId;
    }
  }
  if (next.windowId && !next.taskId) {
    const window = state.windows?.[next.windowId];
    if (window?.taskId) {
      next.taskId = window.taskId;
    }
  }
  return next;
}

function isValidTarget(state, target) {
  if (!target) return false;
  if (target.taskId && !state.tasks?.[target.taskId]) return false;
  if (target.windowId && !state.windows?.[target.windowId]) return false;
  if (target.widgetId && !state.widgets?.[target.widgetId]) return false;
  return true;
}

export function setFocus(state, target, reason = FOCUS_REASONS.COMMAND, seq = null) {
  const normalized = normalizeFocusTarget(target);
  let nextState = state;
  let reasonId = null;
  if (state?.focusReasons) {
    const alloc = allocateId(state.idCounters ?? {}, "reason", "reason");
    reasonId = alloc.id;
    const focusReasons = { ...(state.focusReasons ?? {}) };
    focusReasons[reasonId] = {
      id: reasonId,
      reason,
      ts: null,
      details: {}
    };
    nextState = { ...state, idCounters: alloc.counters, focusReasons };
  }
  const entry = {
    seq: seq ?? nextState.focusHistory.length + 1,
    target: normalized,
    reason,
    reasonId
  };
  return {
    ...nextState,
    focus: normalized,
    focusHistory: [...nextState.focusHistory, entry]
  };
}

export function focusHistory(state) {
  return state.focusHistory;
}

function findClosestWithAttribute(element, attribute) {
  if (!element) return null;
  if (typeof element.closest === "function") {
    const found = element.closest(`[${attribute}]`);
    if (found) return found.getAttribute(attribute) ?? found.dataset?.[attribute.replace("data-", "")] ?? null;
  }
  let current = element;
  while (current) {
    if (typeof current.getAttribute === "function") {
      const value = current.getAttribute(attribute);
      if (value !== null && value !== undefined) {
        return value;
      }
    }
    if (current.dataset) {
      const key = attribute.replace("data-", "").replace(/-([a-z])/g, (_, c) => c.toUpperCase());
      if (current.dataset[key]) {
        return current.dataset[key];
      }
    }
    current = current.parentElement ?? current.parentNode ?? null;
  }
  return null;
}

export function resolveFocusTargetFromElement(element, state, options = {}) {
  if (!element) return null;
  if (typeof options.resolve === "function") {
    return normalizeFocusTarget(options.resolve(element, state));
  }
  const widgetId = findClosestWithAttribute(element, "data-widget-id");
  const windowId = findClosestWithAttribute(element, "data-window-id");
  const taskId = findClosestWithAttribute(element, "data-task-id");
  const presentationId = findClosestWithAttribute(element, "data-presentation-id");

  let target = normalizeFocusTarget({
    taskId: taskId ?? null,
    windowId: windowId ?? null,
    widgetId: widgetId ?? null,
    presentationId: presentationId ?? null
  });

  if (state) {
    target = completeTargetFromState(state, target);
  }
  return target;
}

export function reconcileFocus(state, event, options = {}) {
  const resolver =
    options.resolveTarget ??
    ((element) => resolveFocusTargetFromElement(element, state, options));
  const target = normalizeFocusTarget(resolver(event?.target ?? null, state));
  if (!target) {
    if (options.clearOnUnknown) {
      return setFocus(state, null, options.reason ?? FOCUS_REASONS.RECONCILE, event?.seq ?? null);
    }
    return state;
  }

  const completed = completeTargetFromState(state, target);
  if (!isValidTarget(state, completed) && !options.allowUnknown) {
    return state;
  }
  if (sameFocusTarget(state.focus, completed)) {
    return state;
  }
  return setFocus(state, completed, options.reason ?? FOCUS_REASONS.RECONCILE, event?.seq ?? null);
}
