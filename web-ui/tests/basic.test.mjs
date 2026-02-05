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

test("replay is deterministic and matches expected snapshot", () => {
  const initialState = loadJson("fixtures/basic-state.json");
  const eventLog = loadJson("fixtures/basic-events.json");
  const expectedSnapshot = loadJson("fixtures/basic-snapshot.json");

  const first = replayEvents(initialState, eventLog.events);
  const second = replayEvents(initialState, eventLog.events);

  const firstSnapshot = snapshotToString(first.snapshots[0]);
  const secondSnapshot = snapshotToString(second.snapshots[0]);

  assert.equal(firstSnapshot, secondSnapshot);
  assert.equal(firstSnapshot, stableStringify(expectedSnapshot));
});
