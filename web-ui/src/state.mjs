import { createIdGenerator } from "./ids.mjs";

export function createState(options = {}) {
  const nextTaskId = createIdGenerator("task");
  const nextWindowId = createIdGenerator("window");
  return {
    tasks: {},
    windows: {},
    focus: null,
    focusHistory: [],
    selection: null,
    commands: {},
    layout: null,
    idGenerators: {
      task: nextTaskId,
      window: nextWindowId
    },
    ...options
  };
}

export function addTask(state, task) {
  const tasks = { ...state.tasks };
  tasks[task.id] = task;
  return { ...state, tasks };
}

export function addWindow(state, window) {
  const windows = { ...state.windows };
  windows[window.id] = window;
  return { ...state, windows };
}

export function setLayout(state, layout) {
  return { ...state, layout };
}

export function setSelection(state, selection) {
  return { ...state, selection };
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
