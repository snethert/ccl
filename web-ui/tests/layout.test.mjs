import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { replayEvents } from "./replay-harness.mjs";
import { snapshotToString, stableStringify } from "./snapshot.mjs";

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

  const result = replayEvents(initialState, eventLog.events);
  const snapshot = snapshotToString(result.snapshots[0]);

  assert.equal(snapshot, stableStringify(expectedSnapshot));
});
