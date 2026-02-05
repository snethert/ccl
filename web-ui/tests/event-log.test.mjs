import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { validateEventLog } from "./event-log.mjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function loadJson(relPath) {
  const fullPath = path.join(__dirname, relPath);
  return JSON.parse(fs.readFileSync(fullPath, "utf8"));
}

test("event log schema validation passes for fixtures", () => {
  const log = loadJson("fixtures/basic-events.json");
  assert.equal(validateEventLog(log), true);
});
