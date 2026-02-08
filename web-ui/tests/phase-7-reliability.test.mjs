import { test } from "node:test";
import assert from "node:assert/strict";

import {
  createState,
  createQualityCollector,
  applyRuntimeMessage,
  createSnapshot,
  restoreStateFromSnapshot
} from "../src/index.mjs";
import { replayEvents } from "./replay-harness.mjs";
import { stableStringify } from "./snapshot.mjs";

test("phase-7 reliability malformed runtime payloads degrade safely without unhandled exceptions", () => {
  const collector = createQualityCollector({
    budgets: {
      reliability: {
        maxUnhandledRuntimeFaults: 10
      }
    }
  });
  let state = createState();

  const malformedMessages = [
    null,
    42,
    { kind: "runtime.output", payload: { recording: {} } },
    { kind: "runtime.output", payload: { entry: { id: "ent-1" } } },
    { kind: "runtime.output", payload: { anchor: { id: "anc-1" } } }
  ];

  for (const message of malformedMessages) {
    assert.doesNotThrow(() => {
      const result = applyRuntimeMessage(state, message, { qualityCollector: collector });
      assert.ok(result && typeof result === "object");
      assert.ok(Array.isArray(result.errors));
      state = result.state ?? state;
    });
  }

  const reliabilitySamples = collector.snapshot().samples.reliability;
  assert.equal(reliabilitySamples.some((entry) => entry.kind === "runtime-fault"), true);
  const report = collector.evaluate();
  assert.equal(report.ok, true);
});

test("phase-7 reliability replay remains deterministic across repeated runs", () => {
  const events = [
    { seq: 1, type: "ui:signal.enqueue", payload: { signal: { type: "input:key", payload: { key: "A" } } } },
    { seq: 2, type: "ui:turn.begin", payload: { commitPolicy: "rAF" } },
    { seq: 3, type: "ui:turn.phase", payload: { phase: "commands" } },
    { seq: 4, type: "ui:turn.end", payload: {} }
  ];

  const runA = replayEvents({}, events);
  const runB = replayEvents({}, events);
  assert.equal(stableStringify(runA.state), stableStringify(runB.state));

  const collector = createQualityCollector();
  collector.recordReliability({
    kind: "replay-run",
    deterministic: true,
    handled: true,
    details: { eventCount: events.length }
  });
  const report = collector.evaluate();
  assert.equal(report.ok, true);
});

test("phase-7 reliability gates detect nondeterministic replay regressions", () => {
  const collector = createQualityCollector();
  collector.recordReliability({
    kind: "replay-run",
    deterministic: false,
    handled: true,
    details: { seed: "phase-7" }
  });

  const report = collector.evaluate();
  assert.equal(report.ok, false);
  const failedIds = report.failedChecks.map((entry) => entry.id);
  assert.equal(failedIds.includes("reliability-deterministic-replay"), true);
});

test("phase-7 reliability session restore tolerates stale presentation references", () => {
  const initial = createState({
    presentations: {
      "pres-1": {
        id: "pres-1",
        type: "value",
        metadata: { summary: "stale target" }
      }
    },
    selection: {
      id: "sel-1",
      kind: "presentation",
      targetIds: ["pres-1"],
      anchorId: "pres-1",
      metadata: {}
    }
  });
  const snapshot = createSnapshot(initial, { now: () => 100 });
  delete snapshot.state.presentations["pres-1"];

  const restored = restoreStateFromSnapshot(snapshot);
  assert.ok(restored);
  assert.equal(restored.state.selection?.anchorId ?? null, "pres-1");
  assert.equal(restored.state.presentations["pres-1"] ?? null, null);
});

