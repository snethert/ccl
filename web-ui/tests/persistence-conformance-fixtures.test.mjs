import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { stableStringify } from "./snapshot.mjs";
import {
  runPersistenceFixtureSet,
  validatePersistenceFixtureSet
} from "./persistence-fault-harness.mjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");

function readSpecJson(relPath) {
  const fullPath = path.resolve(repoRoot, relPath);
  return JSON.parse(fs.readFileSync(fullPath, "utf8"));
}

function requiredScenarios(fixtureSet) {
  return (fixtureSet.scenarios ?? []).filter(
    (scenario) => String(scenario.status ?? "required") === "required"
  );
}

function pendingScenarios(fixtureSet) {
  return (fixtureSet.scenarios ?? []).filter(
    (scenario) => String(scenario.status ?? "required") === "pending"
  );
}

function formatFailures(report) {
  const lines = [];
  for (const result of report.results ?? []) {
    if (result.status === "passed") continue;
    lines.push(`scenario ${result.id} failed`);
    for (const diagnostic of result.diagnostics ?? []) {
      lines.push(`  diagnostic ${diagnostic.code}: ${diagnostic.message}`);
    }
    for (const error of result.errors ?? []) {
      lines.push(`  error ${error.code} @ ${error.op_id}${error.phase ? `:${error.phase}` : ""}`);
    }
  }
  return lines.join("\n");
}

test("persistence conformance fixture set validates and covers required classes", () => {
  const fixtureSet = readSpecJson("web-ui/spec/persistence-conformance-fixtures-v1.json");
  const validation = validatePersistenceFixtureSet(fixtureSet);
  assert.equal(validation.ok, true, `fixture set validation failed: ${stableStringify(validation.errors)}`);

  const required = requiredScenarios(fixtureSet);
  assert.ok(required.length >= 6, "expected at least six required persistence scenarios");

  const classes = new Set(required.map((scenario) => String(scenario.class ?? "")));
  for (const classId of ["crash", "lease", "sync"]) {
    assert.equal(classes.has(classId), true, `missing required scenario class coverage: ${classId}`);
  }
});

test("persistence conformance required scenarios pass", () => {
  const fixtureSet = readSpecJson("web-ui/spec/persistence-conformance-fixtures-v1.json");
  const report = runPersistenceFixtureSet(fixtureSet, {
    seed: "persistence-conformance-v1",
    requiredOnly: true
  });

  const requiredCount = requiredScenarios(fixtureSet).length;
  assert.equal(report.summary.scenarioCount, requiredCount);
  assert.equal(report.summary.failed, 0, formatFailures(report));
  assert.equal(report.ok, true, formatFailures(report));

  for (const result of report.results) {
    assert.equal(result.status, "passed", `${result.id} did not pass`);
    assert.equal(Array.isArray(result.events), true);
    assert.equal(Array.isArray(result.errors), true);
    assert.equal(result.snapshot?.local?.refs ? true : false, true);
  }
});

test("persistence conformance replay is deterministic for fixed seed", () => {
  const fixtureSet = readSpecJson("web-ui/spec/persistence-conformance-fixtures-v1.json");
  const reportA = runPersistenceFixtureSet(fixtureSet, {
    seed: "deterministic-seed-1",
    requiredOnly: true
  });
  const reportB = runPersistenceFixtureSet(fixtureSet, {
    seed: "deterministic-seed-1",
    requiredOnly: true
  });

  assert.equal(stableStringify(reportA), stableStringify(reportB));
});

test("persistence conformance includes P1 scaffold scenarios from failure matrix", () => {
  const fixtureSet = readSpecJson("web-ui/spec/persistence-conformance-fixtures-v1.json");
  const pending = pendingScenarios(fixtureSet);
  const pendingIds = new Set(pending.map((scenario) => String(scenario.id ?? "")));

  const expectedP1ScenarioIds = [
    "pending.crash.object_split_before_manifest.v1",
    "pending.crash.reftxn_prepared.v1",
    "pending.crash.recovery_scanner_restart.v1",
    "pending.lease.heartbeat_loss_before_write.v1",
    "pending.lease.double_takeover_tiebreak.v1",
    "pending.sync.push.cas_mismatch_divergence.v1",
    "pending.sync.pull.hash_mismatch_reject.v1",
    "pending.sync.push.retry_idempotent_timeout.v1"
  ];

  for (const id of expectedP1ScenarioIds) {
    assert.equal(pendingIds.has(id), true, `missing pending P1 scaffold scenario: ${id}`);
  }
});
