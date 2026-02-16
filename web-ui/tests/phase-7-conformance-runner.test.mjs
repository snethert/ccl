import { test } from "node:test";
import assert from "node:assert/strict";

import {
  assertConformanceReport,
  createConformanceRunner,
  evaluateConformanceAssertion,
  expandConformanceLanes,
  validateConformanceReport
} from "../src/conformance-runner.mjs";

const TEST_PATH = "web-ui/tests/phase-7-conformance-runner.test.mjs";

function makeExecutionProfile(overrides = {}) {
  return {
    seed: "seed-v1",
    viewport: {
      id: "desktop-lg",
      width: 1440,
      height: 900,
      deviceScaleFactor: 2,
      pointer: "fine",
      touch: false
    },
    viewports: [
      {
        id: "desktop-lg",
        width: 1440,
        height: 900,
        deviceScaleFactor: 2,
        pointer: "fine",
        touch: false
      },
      {
        id: "mobile",
        width: 390,
        height: 844,
        deviceScaleFactor: 3,
        pointer: "coarse",
        touch: true
      }
    ],
    modes: ["dark", "light"],
    backends: ["dom", "canvas", "webgl"],
    ...overrides
  };
}

function makeRunnerEnv(overrides = {}) {
  return {
    engine: "node",
    engineVersion: "22.0.0",
    os: "darwin",
    osVersion: "24.0",
    gpu: "test-gpu",
    buildSha: "abcdef0",
    artifactHash: `sha256:${"1".repeat(64)}`,
    fontFallback: false,
    ...overrides
  };
}

function passMetricsFromFixture(fixture) {
  const metrics = {};
  for (const assertion of fixture.assertions ?? []) {
    metrics[assertion.id] = assertion.target;
  }
  return metrics;
}

test("conformance runner executes required fixtures and emits schema-valid report", async () => {
  const fixtureSpec = {
    executionProfile: makeExecutionProfile(),
    fixtures: [
      {
        id: "snapshot.required.v1",
        status: "required",
        requiredHarness: "snapshot",
        existingTests: [TEST_PATH],
        assertions: [
          { id: "window-border-width", metric: "px", comparator: "==", target: 1, tolerance: 0 },
          { id: "button-states", metric: "state-coverage", comparator: ">=", target: 6 }
        ],
        artifacts: ["snapshot-dom-dark.json"]
      },
      {
        id: "snapshot.optional.v1",
        status: "optional",
        requiredHarness: "snapshot",
        existingTests: [TEST_PATH],
        assertions: [{ id: "unused", metric: "px", comparator: "==", target: 1 }],
        artifacts: ["optional-artifact.json"]
      }
    ]
  };

  const runner = createConformanceRunner({
    fixtureSpec,
    env: makeRunnerEnv(),
    harnesses: {
      snapshot: async ({ fixture }) => ({
        binding: { testPath: TEST_PATH },
        metrics: passMetricsFromFixture(fixture),
        artifacts: fixture.artifacts
      })
    }
  });

  const report = await runner.run({
    runId: "run-required-fixtures",
    ts: () => 1_700_000_000_000
  });

  assert.equal(report.summary.fixtureCount, 1);
  assert.equal(report.summary.status, "passed");
  assert.equal(report.summary.passed, 1);
  assert.equal(report.summary.failed, 0);
  assert.equal(report.env.mode, "mixed");
  assert.equal(report.env.backend, "mixed");
  assert.deepEqual(report.fixtures[0].artifacts, ["snapshot-dom-dark.json"]);
  assert.deepEqual(report.fixtures[0].assertions.map((entry) => entry.status), ["passed", "passed"]);

  const validation = validateConformanceReport(report);
  assert.equal(validation.ok, true, `schema validation failed: ${JSON.stringify(validation.errors, null, 2)}`);
  assert.doesNotThrow(() => assertConformanceReport(report));
});

test("conformance runner fails fixture on missing lanes and missing required artifacts", async () => {
  const fixtureSpec = {
    executionProfile: makeExecutionProfile(),
    fixtures: [
      {
        id: "geometry.required.v1",
        status: "required",
        requiredHarness: "geometry",
        modeLanes: ["dark", "ghost-mode"],
        existingTests: [TEST_PATH],
        assertions: [
          { id: "focus-ring-width", metric: "px", comparator: ">=", target: 2 }
        ],
        artifacts: ["focus-geometry-report.json"]
      }
    ]
  };

  const runner = createConformanceRunner({
    fixtureSpec,
    env: makeRunnerEnv(),
    harnesses: {
      geometry: async ({ fixture }) => ({
        metrics: passMetricsFromFixture(fixture),
        artifacts: []
      })
    }
  });

  const report = await runner.run({
    runId: "run-lane-and-artifact-failures",
    ts: () => 1_700_000_000_100
  });
  const fixture = report.fixtures[0];
  const codes = new Set((fixture.diagnostics ?? []).map((entry) => entry.code));

  assert.equal(report.summary.status, "failed");
  assert.equal(report.summary.failed, 1);
  assert.equal(fixture.status, "failed");
  assert.equal(codes.has("runner-lane-missing"), true);
  assert.equal(codes.has("runner-artifact-missing"), true);
});

test("conformance runner continues across fixtures when a harness is missing", async () => {
  const fixtureSpec = {
    executionProfile: makeExecutionProfile(),
    fixtures: [
      {
        id: "snapshot.required.v1",
        status: "required",
        requiredHarness: "snapshot",
        existingTests: [TEST_PATH],
        assertions: [{ id: "window-border-width", metric: "px", comparator: "==", target: 1 }],
        artifacts: ["snapshot-dom-dark.json"]
      },
      {
        id: "contrast.required.v1",
        status: "required",
        requiredHarness: "contrast",
        existingTests: [TEST_PATH],
        assertions: [{ id: "selection-text-contrast", metric: "contrast-ratio", comparator: ">=", target: 4.5 }],
        artifacts: ["selection-contrast-report.json"]
      }
    ]
  };

  const runner = createConformanceRunner({
    fixtureSpec,
    env: makeRunnerEnv(),
    harnesses: {
      snapshot: async ({ fixture }) => ({
        metrics: passMetricsFromFixture(fixture),
        artifacts: fixture.artifacts
      })
    }
  });

  const report = await runner.run({
    runId: "run-missing-harness",
    ts: () => 1_700_000_000_200
  });

  assert.equal(report.summary.status, "failed");
  assert.equal(report.summary.fixtureCount, 2);
  assert.equal(report.summary.passed, 1);
  assert.equal(report.summary.failed, 1);
  assert.equal(report.fixtures[0].status, "passed");
  assert.equal(report.fixtures[1].status, "failed");
  assert.equal(
    (report.fixtures[1].diagnostics ?? []).some((entry) => entry.code === "runner-harness-missing"),
    true
  );
});

test("assertion evaluator applies tolerance and stable-hash semantics", () => {
  assert.equal(
    evaluateConformanceAssertion(
      { id: "eq", metric: "px", comparator: "==", target: 8, tolerance: 1 },
      8.75
    ).passed,
    true
  );
  assert.equal(
    evaluateConformanceAssertion(
      { id: "lte", metric: "duration-ms", comparator: "<=", target: 120, tolerance: 16 },
      130
    ).passed,
    true
  );
  assert.equal(
    evaluateConformanceAssertion(
      { id: "gte", metric: "px", comparator: ">=", target: 44, tolerance: 2 },
      42
    ).passed,
    true
  );
  assert.equal(
    evaluateConformanceAssertion(
      { id: "stable", metric: "stable-hash", comparator: "==", target: "repeatable" },
      ["abc", "abc", "abc"]
    ).passed,
    true
  );
  assert.equal(
    evaluateConformanceAssertion(
      { id: "stable", metric: "stable-hash", comparator: "==", target: "repeatable" },
      ["abc", "def"]
    ).passed,
    false
  );
  assert.equal(
    evaluateConformanceAssertion(
      { id: "bool", metric: "focus-indicator-presence", comparator: "==", target: true },
      false
    ).passed,
    false
  );
});

test("lane expansion honors declared parity backend pairs and fails when pair backends are unavailable", async () => {
  const fixture = {
    id: "parity.required.v1",
    status: "required",
    requiredHarness: "parity",
    backendLanes: ["dom", "canvas"],
    parityBackendPairs: [["dom", "canvas"]],
    existingTests: [TEST_PATH],
    assertions: [{ id: "geometry-delta", metric: "px", comparator: "<=", target: 1 }],
    artifacts: ["dom-canvas-parity-report.json"]
  };
  const expanded = expandConformanceLanes(fixture, makeExecutionProfile());
  assert.equal(expanded.lanes.length, 2);
  assert.equal(expanded.lanes.every((lane) => lane.backend === "mixed"), true);
  assert.equal(
    expanded.lanes.every(
      (lane) => Array.isArray(lane.backendPair) && lane.backendPair.length === 2
    ),
    true
  );
  assert.equal(
    expanded.lanes.every((lane) => lane.backendPair[0] === "dom" && lane.backendPair[1] === "canvas"),
    true
  );

  const expandedFallback = expandConformanceLanes(
    {
      ...fixture,
      backendLanes: undefined,
      parityBackendPairs: undefined
    },
    makeExecutionProfile()
  );
  assert.equal(expandedFallback.lanes.length, 6);

  const failingRunner = createConformanceRunner({
    fixtureSpec: {
      executionProfile: makeExecutionProfile({ backends: ["dom"] }),
      fixtures: [fixture]
    },
    env: makeRunnerEnv(),
    harnesses: {
      parity: async ({ fixture: laneFixture }) => ({
        metrics: passMetricsFromFixture(laneFixture),
        artifacts: laneFixture.artifacts
      })
    }
  });
  const report = await failingRunner.run({
    runId: "run-parity-too-few-backends",
    ts: () => 1_700_000_000_300
  });

  assert.equal(report.summary.status, "failed");
  assert.equal(
    (report.fixtures[0].diagnostics ?? []).some((entry) => entry.code === "runner-lane-missing"),
    true
  );
});

test("report validator rejects invalid env mode", () => {
  const invalidReport = {
    version: "1.0.0",
    runId: "bad-report",
    ts: 1_700_000_000_000,
    env: {
      seed: "seed-v1",
      mode: "sepia",
      backend: "dom",
      fontFallback: false,
      engine: "node",
      engineVersion: "22",
      os: "darwin",
      osVersion: "24",
      gpu: "test-gpu",
      buildSha: "abcdef0",
      artifactHash: `sha256:${"1".repeat(64)}`
    },
    summary: {
      status: "passed",
      fixtureCount: 0,
      passed: 0,
      failed: 0
    },
    fixtures: []
  };

  const validation = validateConformanceReport(invalidReport);
  assert.equal(validation.ok, false);
  assert.equal(validation.errors.some((entry) => entry.path === "$.env.mode"), true);
  assert.throws(() => assertConformanceReport(invalidReport));
});
