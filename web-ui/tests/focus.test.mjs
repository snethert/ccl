import { test } from "node:test";
import assert from "node:assert/strict";

import { createState, addTask, addWindow, addWidget } from "../src/state.mjs";
import { setFocus, reconcileFocus, FOCUS_REASONS } from "../src/focus.mjs";

test("focus history records deterministic sequence", () => {
  let state = createState();
  state = setFocus(state, { windowId: "window-1" }, FOCUS_REASONS.USER, 1);
  state = setFocus(state, { windowId: "window-2" }, FOCUS_REASONS.COMMAND, 2);

  assert.deepEqual(state.focus, {
    taskId: null,
    windowId: "window-2",
    widgetId: null,
    presentationId: null
  });
  assert.equal(state.focusHistory.length, 2);
  assert.deepEqual(state.focusHistory[0], {
    seq: 1,
    target: {
      taskId: null,
      windowId: "window-1",
      widgetId: null,
      presentationId: null
    },
    reason: FOCUS_REASONS.USER,
    reasonId: "reason-0"
  });
  assert.ok(state.focusReasons["reason-0"]);
});

test("reconcileFocus updates focus from resolver", () => {
  let state = createState();
  state = addTask(state, { id: "task-1" });
  state = addWindow(state, { id: "win-1", taskId: "task-1" });
  state = addWidget(state, { id: "widget-1", kind: "button", windowId: "win-1" });

  const event = { target: { id: "mock" }, seq: 10 };
  const next = reconcileFocus(state, event, {
    resolveTarget: () => ({ widgetId: "widget-1" })
  });

  assert.deepEqual(next.focus, {
    taskId: "task-1",
    windowId: "win-1",
    widgetId: "widget-1",
    presentationId: null
  });
  assert.equal(next.focusHistory.length, 1);
  assert.equal(next.focusHistory[0].reason, FOCUS_REASONS.RECONCILE);
});

test("reconcileFocus defers while composing", () => {
  let state = createState();
  state = addTask(state, { id: "task-1" });
  state = addWindow(state, { id: "win-1", taskId: "task-1" });
  state = addWidget(state, { id: "widget-1", kind: "button", windowId: "win-1" });

  const event = { target: { id: "mock" }, isComposing: true, seq: 5 };
  const next = reconcileFocus(state, event, {
    deferWhileComposing: true,
    resolveTarget: () => ({ widgetId: "widget-1" })
  });

  assert.equal(next.focus, null);
  assert.equal(next.focusHistory.length, 0);
});
