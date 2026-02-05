import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { replayEvents } from "./replay-harness.mjs";
import { snapshotToString, stableStringify, serializeState } from "./snapshot.mjs";
import { createRegistry, registerCommand } from "../src/commands.mjs";
import {
  setSelection,
  createState,
  initLayout,
  splitLayout,
  wrapInTabs,
  setActiveTab,
  dockLayout
} from "../src/state.mjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function loadJson(relPath) {
  const fullPath = path.join(__dirname, relPath);
  return JSON.parse(fs.readFileSync(fullPath, "utf8"));
}

test("layout and selection changes are captured in snapshots", () => {
  const initialState = loadJson("fixtures/basic-state.json");
  const eventLog = loadJson("fixtures/layout-events.json");
  const expectedSnapshot = loadJson("fixtures/layout-snapshot.json");

  const registry = createRegistry();
  registerCommand(registry, {
    id: "selection.set",
    exec: (ctx) => ({ state: setSelection(ctx.state, ctx.payload.selection) })
  });
  const result = replayEvents(initialState, eventLog.events, { registry });
  const snapshot = snapshotToString(result.snapshots[0]);

  assert.equal(snapshot, stableStringify(expectedSnapshot));
});

test("layout mutations are deterministic", () => {
  const build = () => {
    let state = createState();
    state = initLayout(state, { kind: "leaf", windowId: "w1" });
    const rootId = state.layout.rootId;
    state = splitLayout(state, rootId, "h", 0.6, { windowId: "w2" });
    const splitId = state.layout.rootId;
    const leftId = state.layout.nodes[splitId].children[0];
    state = wrapInTabs(state, leftId, { newTab: { windowId: "w3" }, activateNew: true });
    const tabsId = Object.keys(state.layout.nodes)
      .sort()
      .find((id) => state.layout.nodes[id].kind === "tabs");
    const tabId = state.layout.nodes[tabsId].children[1];
    state = setActiveTab(state, tabsId, tabId);
    state = dockLayout(state, state.layout.rootId, "left");
    return state;
  };

  const first = snapshotToString(serializeState(build()));
  const second = snapshotToString(serializeState(build()));
  assert.equal(first, second);
});
