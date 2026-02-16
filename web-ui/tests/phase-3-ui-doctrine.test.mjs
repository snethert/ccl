import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { UI_STYLES, UI_STYLE_ID } from "../styles/ui.mjs";
import { DEFAULT_THEME_TOKENS, themeToCssVars } from "../src/theme.mjs";
import {
  createState,
  addTask,
  appendRecording,
  appendRecordingEntry,
  openTranscriptWindow,
  raiseError,
  openProblemsWindow,
  openDebuggerWindow
} from "../src/state.mjs";

const UI_DOCTRINE_TEXT = readFileSync(new URL("../ui-doctrine.md", import.meta.url), "utf8");

test("phase-3 ui doctrine includes base ui classes", () => {
  assert.ok(UI_STYLES.includes(".ui-root"));
  assert.ok(UI_STYLES.includes(".ui-window"));
  assert.ok(UI_STYLES.includes(".ui-list"));
  assert.ok(UI_STYLES.includes(".ui-table"));
  assert.ok(UI_STYLES.includes(".ui-canvas-view"));
  assert.ok(UI_STYLES.includes(".ui-webgl-view"));
  assert.ok(UI_STYLES.includes('[data-ui-theme="high-contrast"]'));
  assert.ok(UI_STYLES.includes('[data-ui-theme="forced-colors"]'));
});

test("phase-3 ui doctrine exposes css variables for core tokens", () => {
  const vars = themeToCssVars(DEFAULT_THEME_TOKENS);
  assert.equal(vars["--ui-color-bg"], DEFAULT_THEME_TOKENS.color.bg);
  assert.equal(vars["--ui-color-surface"], DEFAULT_THEME_TOKENS.color.surface);
  assert.equal(vars["--ui-color-text-primary"], DEFAULT_THEME_TOKENS.color.text.primary);
  assert.equal(vars["--ui-radius-md"], DEFAULT_THEME_TOKENS.radius.md);
});

test("phase-3 ui doctrine defines a stable style id", () => {
  assert.equal(UI_STYLE_ID, "web-ui-styles");
});

test("phase-3 ui doctrine annotates instrument list items", () => {
  let state = createState();
  state = addTask(state, { id: "task-1", title: "Task" });
  state = appendRecording(state, {
    id: "rec-1",
    context: { commandId: "repl.eval", sessionId: "s-1", workspaceId: "w-1" },
    input: { kind: "form", text: "(+ 1 2)", package: "CL-USER" }
  });
  state = appendRecordingEntry(state, {
    id: "ent-1",
    recordingId: "rec-1",
    seq: 1,
    streamId: "stdout",
    text: "3"
  });
  state = openTranscriptWindow(state, { taskId: "task-1" });
  const transcriptWindow = Object.values(state.windows).find((win) => win.metadata?.role === "transcript");
  const transcriptItems = state.widgets[transcriptWindow.metadata.widgets.listId].props.items;
  assert.ok(transcriptItems.find((item) => item.className?.includes("ui-transcript-recording")));
  assert.ok(transcriptItems.find((item) => item.className?.includes("ui-transcript-entry")));

  state = raiseError(state, { taskId: "task-1", message: "Boom", kind: "warning" });
  state = openProblemsWindow(state, { taskId: "task-1" });
  const problemsWindow = Object.values(state.windows).find((win) => win.metadata?.role === "problems");
  const problemsItem = state.widgets[problemsWindow.metadata.widgets.listId].props.items[0];
  assert.ok(problemsItem.className.includes("ui-problems-item"));
  assert.ok(problemsItem.className.includes("is-warning"));

  state = raiseError(state, {
    taskId: "task-1",
    message: "Crash",
    kind: "error",
    restarts: [{ id: "restart-1", title: "Retry", safety: "safe", recommended: true }]
  });
  state = openDebuggerWindow(state, { taskId: "task-1" });
  const debuggerWindow = Object.values(state.windows).find((win) => win.metadata?.role === "debugger");
  const restartItem = state.widgets[debuggerWindow.metadata.widgets.restartsId].props.items[0];
  assert.ok(restartItem.className.includes("ui-debugger-restart"));
  assert.ok(restartItem.className.includes("is-safe"));
  assert.ok(restartItem.className.includes("is-recommended"));
});

test("phase-3 ui doctrine remediation clauses remain explicit", () => {
  assert.ok(UI_DOCTRINE_TEXT.includes("Normative Strata and Claim Rules"));
  assert.ok(UI_DOCTRINE_TEXT.includes("No clause may be treated as a release gate"));
  assert.ok(UI_DOCTRINE_TEXT.includes("Text-only checks"));
  assert.ok(UI_DOCTRINE_TEXT.includes("ui-conformance-runner-contract-v1.md"));
  assert.ok(UI_DOCTRINE_TEXT.includes("32 px class minima"));
  assert.ok(UI_DOCTRINE_TEXT.includes("44 x 44 px"));
  assert.ok(UI_DOCTRINE_TEXT.includes("high-contrast, and forced-colors lanes MUST be tokenized and testable"));
  assert.ok(UI_DOCTRINE_TEXT.includes("logical properties"));
  assert.ok(UI_DOCTRINE_TEXT.includes("Evidence Freshness and Audit Integrity"));
});
