export const CONFORMANCE_REPORT_VERSION = "1.0.0";

export const CONFORMANCE_HARNESS_TYPES = Object.freeze([
  "snapshot",
  "geometry",
  "contrast",
  "parity",
  "timing",
  "replay",
  "keyboard"
]);

const POINTER_LANES = new Set(["fine", "coarse"]);
const ENV_MODE_VALUES = new Set(["dark", "light", "high-contrast", "forced-colors", "mixed"]);
const ENV_BACKEND_VALUES = new Set(["dom", "canvas", "webgl", "mixed"]);
const BUILD_SHA_PATTERN = /^[0-9a-fA-F]{7,64}$/;
const ARTIFACT_HASH_PATTERN = /^sha256:[0-9a-fA-F]{64}$/;

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === "[object Object]";
}

function normalizeString(value, fallback = "") {
  return typeof value === "string" && value.length > 0 ? value : fallback;
}

function toFiniteNumber(value, fallback = 0) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return fallback;
  return numeric;
}

function toNonNegativeNumber(value, fallback = 0) {
  return Math.max(0, toFiniteNumber(value, fallback));
}

function normalizeStringList(values) {
  if (!Array.isArray(values)) return [];
  const out = [];
  const seen = new Set();
  for (const value of values) {
    if (typeof value !== "string" || value.length === 0) continue;
    if (seen.has(value)) continue;
    seen.add(value);
    out.push(value);
  }
  return out;
}

function makeDiagnostic(code, message, details = null) {
  const diagnostic = {
    code: normalizeString(code, "runner-diagnostic"),
    message: normalizeString(message, "conformance diagnostic")
  };
  if (details !== null && details !== undefined) {
    diagnostic.details = details;
  }
  return diagnostic;
}

function normalizeDiagnosticsList(diagnostics, lane = null) {
  if (!Array.isArray(diagnostics)) return [];
  const laneDetails = lane ? describeLane(lane) : null;
  const out = [];
  for (const entry of diagnostics) {
    if (typeof entry === "string") {
      out.push(makeDiagnostic("runner-harness-diagnostic", entry, laneDetails));
      continue;
    }
    if (!isPlainObject(entry)) continue;
    const normalized = makeDiagnostic(
      normalizeString(entry.code, "runner-harness-diagnostic"),
      normalizeString(entry.message, "harness diagnostic"),
      entry.details ?? null
    );
    if (laneDetails) {
      normalized.details = { ...(isPlainObject(normalized.details) ? normalized.details : {}), lane: laneDetails };
    }
    out.push(normalized);
  }
  return out;
}

function canonicalizeValue(value) {
  if (Array.isArray(value)) {
    return value.map(canonicalizeValue);
  }
  if (isPlainObject(value)) {
    const out = {};
    for (const key of Object.keys(value).sort()) {
      out[key] = canonicalizeValue(value[key]);
    }
    return out;
  }
  return value;
}

function valueEquals(a, b) {
  return JSON.stringify(canonicalizeValue(a)) === JSON.stringify(canonicalizeValue(b));
}

function normalizeActualValue(value) {
  return value === undefined ? null : value;
}

function monotonicNowFactory(nowFn = null) {
  if (typeof nowFn === "function") {
    return () => toNonNegativeNumber(nowFn(), 0);
  }
  if (typeof globalThis?.performance?.now === "function") {
    return () => toNonNegativeNumber(globalThis.performance.now(), 0);
  }
  return () => toNonNegativeNumber(Date.now(), 0);
}

function resolveReportTimestamp(tsFn = null) {
  if (typeof tsFn === "function") {
    return Math.max(0, Math.trunc(toFiniteNumber(tsFn(), Date.now())));
  }
  return Math.max(0, Math.trunc(Date.now()));
}

function assertKnownComparator(comparator) {
  return comparator === "==" || comparator === "<=" || comparator === ">=";
}

function stableHashRepeatable(actual) {
  if (actual === "repeatable" || actual === true) return true;
  if (Array.isArray(actual)) {
    if (actual.length < 2) return false;
    const first = actual[0];
    return actual.every((entry) => valueEquals(entry, first));
  }
  if (isPlainObject(actual)) {
    if (Array.isArray(actual.hashes)) return stableHashRepeatable(actual.hashes);
    if (Array.isArray(actual.values)) return stableHashRepeatable(actual.values);
    if (Object.prototype.hasOwnProperty.call(actual, "runA") && Object.prototype.hasOwnProperty.call(actual, "runB")) {
      return valueEquals(actual.runA, actual.runB);
    }
  }
  return false;
}

function evaluateNumericComparator(comparator, actual, expected, tolerance = 0) {
  const delta = Math.max(0, toFiniteNumber(tolerance, 0));
  if (comparator === "==") {
    return Math.abs(actual - expected) <= delta;
  }
  if (comparator === "<=") {
    return actual <= expected + delta;
  }
  if (comparator === ">=") {
    return actual >= expected - delta;
  }
  return false;
}

export function evaluateConformanceAssertion(assertion, actualValue) {
  const metric = normalizeString(assertion?.metric, "unknown");
  const comparator = normalizeString(assertion?.comparator, "==");
  const expected = assertion?.target;
  const tolerance = Number.isFinite(assertion?.tolerance) ? Number(assertion.tolerance) : null;
  const actual = normalizeActualValue(actualValue);

  let passed = false;
  if (!assertKnownComparator(comparator)) {
    passed = false;
  } else if (metric === "stable-hash" && comparator === "==" && expected === "repeatable") {
    passed = stableHashRepeatable(actual);
  } else if (typeof actual === "boolean" || typeof expected === "boolean") {
    passed = comparator === "==" && actual === expected;
  } else if (Number.isFinite(actual) && Number.isFinite(expected)) {
    passed = evaluateNumericComparator(comparator, Number(actual), Number(expected), tolerance ?? 0);
  } else if (comparator === "==") {
    passed = valueEquals(actual, expected);
  } else {
    passed = false;
  }

  return {
    passed,
    id: normalizeString(assertion?.id, "unknown-assertion"),
    metric,
    comparator,
    expected,
    actual,
    tolerance
  };
}

function resolveBackendPairs(backends) {
  const pairs = [];
  for (let i = 0; i < backends.length; i += 1) {
    for (let j = i + 1; j < backends.length; j += 1) {
      pairs.push([backends[i], backends[j]]);
    }
  }
  return pairs;
}

function normalizeParityBackendPairs(rawPairs, effectiveBackends, fixtureId, diagnostics) {
  if (!Array.isArray(rawPairs)) return null;

  const out = [];
  const seen = new Set();
  const effectiveSet = new Set(effectiveBackends);
  for (const pair of rawPairs) {
    if (!Array.isArray(pair) || pair.length !== 2 || typeof pair[0] !== "string" || typeof pair[1] !== "string") {
      diagnostics.push(
        makeDiagnostic(
          "runner-lane-missing",
          `fixture ${fixtureId} declares invalid parity backend pair`,
          { fixtureId, lane: "backend", value: pair }
        )
      );
      continue;
    }

    const left = normalizeString(pair[0], "");
    const right = normalizeString(pair[1], "");
    if (!left || !right || left === right) {
      diagnostics.push(
        makeDiagnostic(
          "runner-lane-missing",
          `fixture ${fixtureId} declares invalid parity backend pair members`,
          { fixtureId, lane: "backend", value: pair }
        )
      );
      continue;
    }

    if (!effectiveSet.has(left) || !effectiveSet.has(right)) {
      diagnostics.push(
        makeDiagnostic(
          "runner-lane-missing",
          `fixture ${fixtureId} declares parity backend pair outside effective backend lanes`,
          { fixtureId, lane: "backend", value: pair, effectiveBackends }
        )
      );
      continue;
    }

    const key = left < right ? `${left}::${right}` : `${right}::${left}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push([left, right]);
  }

  return out;
}

function describeLane(lane) {
  const details = {};
  if (typeof lane?.mode === "string") details.mode = lane.mode;
  if (typeof lane?.viewportId === "string") details.viewport = lane.viewportId;
  if (typeof lane?.pointer === "string") details.pointer = lane.pointer;
  if (Array.isArray(lane?.backendPair) && lane.backendPair.length === 2) {
    details.backendPair = [lane.backendPair[0], lane.backendPair[1]];
  } else if (typeof lane?.backend === "string") {
    details.backend = lane.backend;
  }
  return details;
}

function resolvePointerLanesForViewport(explicitPointerLanes, viewport, fixtureId, diagnostics) {
  if (Array.isArray(explicitPointerLanes)) {
    const values = [];
    for (const pointer of explicitPointerLanes) {
      if (!POINTER_LANES.has(pointer)) {
        diagnostics.push(
          makeDiagnostic("runner-lane-missing", `fixture ${fixtureId} declares unknown pointer lane: ${pointer}`, {
            fixtureId,
            lane: "pointer",
            value: pointer
          })
        );
        continue;
      }
      values.push(pointer);
    }
    return values;
  }

  const pointer = viewport?.pointer;
  if (typeof pointer === "string" && POINTER_LANES.has(pointer)) {
    return [pointer];
  }
  if (typeof pointer === "string" && !POINTER_LANES.has(pointer)) {
    diagnostics.push(
      makeDiagnostic("runner-lane-missing", `fixture ${fixtureId} resolved unsupported pointer lane: ${pointer}`, {
        fixtureId,
        lane: "pointer",
        value: pointer
      })
    );
  }
  return [null];
}

export function expandConformanceLanes(fixture, executionProfile = {}) {
  const fixtureId = normalizeString(fixture?.id, "unknown-fixture");
  const profileModes = normalizeStringList(executionProfile?.modes);
  const profileBackends = normalizeStringList(executionProfile?.backends);
  const profileViewports = Array.isArray(executionProfile?.viewports)
    ? executionProfile.viewports.filter((entry) => isPlainObject(entry) && typeof entry.id === "string" && entry.id.length > 0)
    : [];

  const viewportById = new Map(profileViewports.map((viewport) => [viewport.id, viewport]));
  const defaultViewportId = normalizeString(executionProfile?.viewport?.id, profileViewports[0]?.id ?? "");

  const requestedModes = normalizeStringList(
    Array.isArray(fixture?.modeLanes) ? fixture.modeLanes : profileModes
  );
  const requestedViewports = normalizeStringList(
    Array.isArray(fixture?.viewportLanes)
      ? fixture.viewportLanes
      : (defaultViewportId ? [defaultViewportId] : [])
  );
  const explicitPointerLanes = Array.isArray(fixture?.pointerLanes)
    ? normalizeStringList(fixture.pointerLanes)
    : null;
  const requestedBackends = normalizeStringList(
    Array.isArray(fixture?.backendLanes) ? fixture.backendLanes : profileBackends
  );

  const diagnostics = [];
  const modeSet = new Set(profileModes);
  const backendSet = new Set(profileBackends);
  const resolvedModes = [];
  const resolvedViewports = [];
  const resolvedBackends = [];

  if (requestedModes.length === 0) {
    diagnostics.push(
      makeDiagnostic("runner-lane-missing", `fixture ${fixtureId} has no mode lanes to execute`, {
        fixtureId,
        lane: "mode"
      })
    );
  }
  for (const mode of requestedModes) {
    if (!modeSet.has(mode)) {
      diagnostics.push(
        makeDiagnostic("runner-lane-missing", `fixture ${fixtureId} declares unknown mode lane: ${mode}`, {
          fixtureId,
          lane: "mode",
          value: mode
        })
      );
      continue;
    }
    resolvedModes.push(mode);
  }

  if (requestedViewports.length === 0) {
    diagnostics.push(
      makeDiagnostic("runner-lane-missing", `fixture ${fixtureId} has no viewport lanes to execute`, {
        fixtureId,
        lane: "viewport"
      })
    );
  }
  for (const viewportId of requestedViewports) {
    const viewport = viewportById.get(viewportId);
    if (!viewport) {
      diagnostics.push(
        makeDiagnostic("runner-lane-missing", `fixture ${fixtureId} declares unknown viewport lane: ${viewportId}`, {
          fixtureId,
          lane: "viewport",
          value: viewportId
        })
      );
      continue;
    }
    resolvedViewports.push(viewport);
  }

  if (requestedBackends.length === 0) {
    diagnostics.push(
      makeDiagnostic("runner-lane-missing", `fixture ${fixtureId} has no backend lanes to execute`, {
        fixtureId,
        lane: "backend"
      })
    );
  }
  for (const backend of requestedBackends) {
    if (!backendSet.has(backend)) {
      diagnostics.push(
        makeDiagnostic("runner-lane-missing", `fixture ${fixtureId} declares unknown backend lane: ${backend}`, {
          fixtureId,
          lane: "backend",
          value: backend
        })
      );
      continue;
    }
    resolvedBackends.push(backend);
  }

  const lanes = [];
  const harnessType = normalizeString(fixture?.requiredHarness, "");
  if (harnessType === "parity") {
    const declaredPairs = normalizeParityBackendPairs(
      fixture?.parityBackendPairs,
      resolvedBackends,
      fixtureId,
      diagnostics
    );
    const pairs = declaredPairs ?? resolveBackendPairs(resolvedBackends);
    if (pairs.length === 0) {
      if (declaredPairs !== null) {
        diagnostics.push(
          makeDiagnostic(
            "runner-lane-missing",
            `fixture ${fixtureId} declares no valid parity backend pairs`,
            { fixtureId, lane: "backend", value: fixture?.parityBackendPairs ?? [] }
          )
        );
      } else {
        diagnostics.push(
          makeDiagnostic(
            "runner-lane-missing",
            `fixture ${fixtureId} requires at least two backend lanes for parity comparisons`,
            { fixtureId, lane: "backend", value: resolvedBackends }
          )
        );
      }
    }
    for (const mode of resolvedModes) {
      for (const viewport of resolvedViewports) {
        const pointers = resolvePointerLanesForViewport(explicitPointerLanes, viewport, fixtureId, diagnostics);
        for (const pointer of pointers) {
          for (const pair of pairs) {
            lanes.push({
              mode,
              viewportId: viewport.id,
              pointer,
              backend: "mixed",
              backendPair: [pair[0], pair[1]]
            });
          }
        }
      }
    }
  } else {
    for (const mode of resolvedModes) {
      for (const viewport of resolvedViewports) {
        const pointers = resolvePointerLanesForViewport(explicitPointerLanes, viewport, fixtureId, diagnostics);
        for (const pointer of pointers) {
          for (const backend of resolvedBackends) {
            lanes.push({
              mode,
              viewportId: viewport.id,
              pointer,
              backend
            });
          }
        }
      }
    }
  }

  if (lanes.length === 0) {
    diagnostics.push(
      makeDiagnostic("runner-lane-missing", `fixture ${fixtureId} produced no executable lane tuples`, {
        fixtureId
      })
    );
  }

  return { lanes, diagnostics };
}

function resolveHarnessMap(harnesses) {
  if (harnesses instanceof Map) return harnesses;
  if (isPlainObject(harnesses)) return new Map(Object.entries(harnesses));
  return new Map();
}

function normalizeBindingPath(fixture, laneOutput, fallbackPath) {
  const fromHarness = normalizeString(laneOutput?.binding?.testPath, "");
  if (fromHarness) return fromHarness;

  const existingTests = normalizeStringList(fixture?.existingTests);
  if (existingTests.length > 0) return existingTests[0];

  return fallbackPath;
}

function collectLaneAssertionActuals(laneOutput) {
  const actuals = new Map();

  if (isPlainObject(laneOutput?.metrics)) {
    for (const [id, value] of Object.entries(laneOutput.metrics)) {
      if (typeof id === "string" && id.length > 0) {
        actuals.set(id, normalizeActualValue(value));
      }
    }
  }

  if (isPlainObject(laneOutput?.actuals)) {
    for (const [id, value] of Object.entries(laneOutput.actuals)) {
      if (typeof id === "string" && id.length > 0) {
        actuals.set(id, normalizeActualValue(value));
      }
    }
  }

  if (Array.isArray(laneOutput?.assertions)) {
    for (const assertion of laneOutput.assertions) {
      if (!isPlainObject(assertion)) continue;
      const id = normalizeString(assertion.id, "");
      if (!id) continue;
      actuals.set(id, normalizeActualValue(assertion.actual));
    }
  }

  return actuals;
}

function collectUnexpectedAssertionIds(laneOutput, knownAssertionIds) {
  const unknown = [];
  if (!Array.isArray(laneOutput?.assertions)) return unknown;
  for (const assertion of laneOutput.assertions) {
    if (!isPlainObject(assertion)) continue;
    const id = normalizeString(assertion.id, "");
    if (!id || knownAssertionIds.has(id)) continue;
    unknown.push(id);
  }
  return unknown;
}

function coerceArtifacts(value) {
  if (!Array.isArray(value)) return [];
  const out = [];
  const seen = new Set();
  for (const entry of value) {
    if (typeof entry !== "string" || entry.length === 0) continue;
    if (seen.has(entry)) continue;
    seen.add(entry);
    out.push(entry);
  }
  return out;
}

function aggregateActualByLane(entries) {
  if (!Array.isArray(entries) || entries.length === 0) return null;
  if (entries.length === 1) return normalizeActualValue(entries[0].actual);
  return entries.map((entry) => ({
    lane: describeLane(entry.lane),
    value: normalizeActualValue(entry.actual)
  }));
}

async function executeFixture(fixture, context) {
  const now = context.now;
  const fixtureStart = now();
  const fixtureId = normalizeString(fixture?.id, "unknown-fixture");
  const harnessType = normalizeString(fixture?.requiredHarness, "");
  const harness = context.harnesses.get(harnessType);

  const assertionSpecs = Array.isArray(fixture?.assertions)
    ? fixture.assertions.filter((entry) => isPlainObject(entry) && typeof entry.id === "string" && entry.id.length > 0)
    : [];
  const assertionIds = new Set(assertionSpecs.map((assertion) => assertion.id));
  const assertionById = new Map(assertionSpecs.map((assertion) => [assertion.id, assertion]));
  const laneAssertions = new Map(assertionSpecs.map((assertion) => [assertion.id, []]));

  const fixtureDiagnostics = [];
  const emittedArtifacts = [];
  const emittedArtifactSet = new Set();
  const observedModes = new Set();
  const observedBackends = new Set();
  let bindingPath = normalizeString(
    normalizeStringList(fixture?.existingTests)[0],
    `web-ui/tests/conformance/${fixtureId}.test.mjs`
  );
  let fixtureFailed = false;

  const laneExpansion = expandConformanceLanes(fixture, context.executionProfile);
  if (laneExpansion.diagnostics.length > 0) {
    fixtureFailed = true;
    fixtureDiagnostics.push(...laneExpansion.diagnostics);
  }

  if (!CONFORMANCE_HARNESS_TYPES.includes(harnessType)) {
    fixtureFailed = true;
    fixtureDiagnostics.push(
      makeDiagnostic(
        "runner-harness-unsupported",
        `fixture ${fixtureId} uses unsupported harness type: ${harnessType || "<missing>"}`,
        { fixtureId, harness: harnessType || null }
      )
    );
  } else if (typeof harness !== "function") {
    fixtureFailed = true;
    fixtureDiagnostics.push(
      makeDiagnostic(
        "runner-harness-missing",
        `fixture ${fixtureId} cannot execute because harness ${harnessType} is not registered`,
        { fixtureId, harness: harnessType }
      )
    );
  }

  if (typeof harness === "function") {
    for (const lane of laneExpansion.lanes) {
      if (typeof lane.mode === "string") observedModes.add(lane.mode);
      if (Array.isArray(lane.backendPair)) {
        observedBackends.add(lane.backendPair[0]);
        observedBackends.add(lane.backendPair[1]);
      } else if (typeof lane.backend === "string" && lane.backend !== "mixed") {
        observedBackends.add(lane.backend);
      }

      let laneOutput = null;
      try {
        laneOutput = await harness({
          fixture,
          lane,
          executionProfile: context.executionProfile,
          seed: context.seed,
          now
        });
      } catch (error) {
        fixtureFailed = true;
        fixtureDiagnostics.push(
          makeDiagnostic(
            "runner-harness-error",
            `fixture ${fixtureId} harness ${harnessType} threw during lane execution`,
            {
              fixtureId,
              harness: harnessType,
              lane: describeLane(lane),
              error: normalizeString(error?.message, String(error))
            }
          )
        );
        for (const assertionSpec of assertionSpecs) {
          laneAssertions.get(assertionSpec.id).push({
            lane,
            actual: null,
            passed: false
          });
        }
        continue;
      }

      const normalizedLaneOutput = isPlainObject(laneOutput) ? laneOutput : {};
      bindingPath = normalizeBindingPath(fixture, normalizedLaneOutput, bindingPath);
      fixtureDiagnostics.push(...normalizeDiagnosticsList(normalizedLaneOutput.diagnostics, lane));

      for (const artifact of coerceArtifacts(normalizedLaneOutput.artifacts)) {
        if (emittedArtifactSet.has(artifact)) continue;
        emittedArtifactSet.add(artifact);
        emittedArtifacts.push(artifact);
      }

      const unknownAssertionIds = collectUnexpectedAssertionIds(normalizedLaneOutput, assertionIds);
      for (const unknownId of unknownAssertionIds) {
        fixtureDiagnostics.push(
          makeDiagnostic(
            "runner-assertion-unknown",
            `fixture ${fixtureId} harness emitted assertion not defined in fixture spec: ${unknownId}`,
            { fixtureId, assertionId: unknownId, lane: describeLane(lane) }
          )
        );
      }

      const laneActuals = collectLaneAssertionActuals(normalizedLaneOutput);
      for (const assertionSpec of assertionSpecs) {
        const hasValue = laneActuals.has(assertionSpec.id);
        const actual = hasValue ? laneActuals.get(assertionSpec.id) : null;
        const evaluation = evaluateConformanceAssertion(assertionSpec, actual);
        laneAssertions.get(assertionSpec.id).push({
          lane,
          actual: evaluation.actual,
          passed: hasValue && evaluation.passed
        });

        if (!hasValue) {
          fixtureFailed = true;
          fixtureDiagnostics.push(
            makeDiagnostic(
              "runner-assertion-missing",
              `fixture ${fixtureId} missing assertion measurement for ${assertionSpec.id}`,
              { fixtureId, assertionId: assertionSpec.id, lane: describeLane(lane), binding: bindingPath }
            )
          );
          continue;
        }

        if (!evaluation.passed) {
          fixtureFailed = true;
          fixtureDiagnostics.push(
            makeDiagnostic(
              "runner-assertion-failed",
              `fixture ${fixtureId} assertion ${assertionSpec.id} failed`,
              {
                fixtureId,
                assertionId: assertionSpec.id,
                lane: describeLane(lane),
                binding: bindingPath,
                expected: evaluation.expected,
                actual: evaluation.actual,
                comparator: evaluation.comparator
              }
            )
          );
        }
      }
    }
  }

  const requiredArtifacts = coerceArtifacts(fixture?.artifacts);
  for (const artifactId of requiredArtifacts) {
    if (emittedArtifactSet.has(artifactId)) continue;
    fixtureFailed = true;
    fixtureDiagnostics.push(
      makeDiagnostic(
        "runner-artifact-missing",
        `fixture ${fixtureId} did not emit required artifact: ${artifactId}`,
        { fixtureId, artifact: artifactId }
      )
    );
  }

  const assertionResults = [];
  for (const assertionId of assertionIds) {
    const assertionSpec = assertionById.get(assertionId);
    const laneEntries = laneAssertions.get(assertionId) ?? [];
    const lanePassed = laneEntries.length > 0 && laneEntries.every((entry) => entry.passed);
    if (!lanePassed) {
      fixtureFailed = true;
    }
    const result = {
      id: assertionId,
      status: lanePassed ? "passed" : "failed",
      metric: normalizeString(assertionSpec.metric, "unknown"),
      comparator: normalizeString(assertionSpec.comparator, "=="),
      expected: assertionSpec.target,
      actual: aggregateActualByLane(laneEntries)
    };
    if (Object.prototype.hasOwnProperty.call(assertionSpec, "tolerance")) {
      result.tolerance = assertionSpec.tolerance;
    }
    assertionResults.push(result);
  }

  const fixtureResult = {
    id: fixtureId,
    status: fixtureFailed ? "failed" : "passed",
    durationMs: toNonNegativeNumber(now() - fixtureStart, 0),
    binding: {
      testPath: bindingPath
    },
    assertions: assertionResults,
    artifacts: emittedArtifacts
  };
  if (fixtureDiagnostics.length > 0) {
    fixtureResult.diagnostics = fixtureDiagnostics;
  }

  return {
    result: fixtureResult,
    observedModes,
    observedBackends
  };
}

function resolveEnvString(value, fallback = "unknown") {
  return normalizeString(value, fallback);
}

function resolveBuildSha(value) {
  const normalized = normalizeString(value, "");
  if (BUILD_SHA_PATTERN.test(normalized)) return normalized;
  return "0000000";
}

function resolveArtifactHash(value) {
  const normalized = normalizeString(value, "");
  if (ARTIFACT_HASH_PATTERN.test(normalized)) return normalized;
  return `sha256:${"0".repeat(64)}`;
}

function resolveSummaryStatus(failedCount) {
  return failedCount > 0 ? "failed" : "passed";
}

function resolveObservedModeValue(explicitMode, observedModes) {
  if (ENV_MODE_VALUES.has(explicitMode)) return explicitMode;
  if (observedModes.size === 1) {
    const value = [...observedModes][0];
    if (ENV_MODE_VALUES.has(value)) return value;
  }
  return "mixed";
}

function resolveObservedBackendValue(explicitBackend, observedBackends) {
  if (ENV_BACKEND_VALUES.has(explicitBackend)) return explicitBackend;
  if (observedBackends.size === 1) {
    const value = [...observedBackends][0];
    if (ENV_BACKEND_VALUES.has(value)) return value;
  }
  return "mixed";
}

function resolveEnvViewport(profileViewport, explicitViewport = null) {
  const viewport = isPlainObject(explicitViewport)
    ? explicitViewport
    : (isPlainObject(profileViewport) ? profileViewport : null);
  if (!viewport) return undefined;
  return {
    width: Math.max(1, Math.trunc(toFiniteNumber(viewport.width, 1))),
    height: Math.max(1, Math.trunc(toFiniteNumber(viewport.height, 1))),
    deviceScaleFactor: Math.max(0.0001, toFiniteNumber(viewport.deviceScaleFactor, 1))
  };
}

function pickFixtures(spec, runOptions) {
  const allFixtures = Array.isArray(spec?.fixtures) ? spec.fixtures.filter(isPlainObject) : [];
  const includeOptional = Boolean(runOptions?.includeOptional);
  const requestedIds = normalizeStringList(runOptions?.fixtureIds);
  const requestedSet = requestedIds.length > 0 ? new Set(requestedIds) : null;

  const out = [];
  for (const fixture of allFixtures) {
    const fixtureId = normalizeString(fixture?.id, "");
    if (!fixtureId) continue;
    if (!includeOptional && fixture.status !== "required") continue;
    if (requestedSet && !requestedSet.has(fixtureId)) continue;
    out.push(fixture);
  }
  return out;
}

function pushValidationError(errors, path, message) {
  errors.push({ path, message });
}

function hasOnlyKeys(value, allowedKeys) {
  if (!isPlainObject(value)) return false;
  return Object.keys(value).every((key) => allowedKeys.has(key));
}

function requireKey(value, key) {
  return isPlainObject(value) && Object.prototype.hasOwnProperty.call(value, key);
}

function validateEnv(env, errors, path) {
  if (!isPlainObject(env)) {
    pushValidationError(errors, path, "env must be an object");
    return;
  }

  const required = [
    "seed",
    "mode",
    "backend",
    "fontFallback",
    "engine",
    "engineVersion",
    "os",
    "osVersion",
    "gpu",
    "buildSha",
    "artifactHash"
  ];
  const allowed = new Set([...required, "viewport"]);

  if (!hasOnlyKeys(env, allowed)) {
    pushValidationError(errors, path, "env contains unknown properties");
  }

  for (const key of required) {
    if (!requireKey(env, key)) {
      pushValidationError(errors, `${path}.${key}`, "missing required property");
    }
  }

  if (typeof env.seed !== "string" || env.seed.length < 1) {
    pushValidationError(errors, `${path}.seed`, "must be a non-empty string");
  }
  if (!ENV_MODE_VALUES.has(env.mode)) {
    pushValidationError(errors, `${path}.mode`, "must be one of: dark, light, high-contrast, forced-colors, mixed");
  }
  if (!ENV_BACKEND_VALUES.has(env.backend)) {
    pushValidationError(errors, `${path}.backend`, "must be one of: dom, canvas, webgl, mixed");
  }
  if (typeof env.fontFallback !== "boolean") {
    pushValidationError(errors, `${path}.fontFallback`, "must be a boolean");
  }
  for (const key of ["engine", "engineVersion", "os", "osVersion", "gpu"]) {
    if (typeof env[key] !== "string" || env[key].length < 1) {
      pushValidationError(errors, `${path}.${key}`, "must be a non-empty string");
    }
  }
  if (typeof env.buildSha !== "string" || !BUILD_SHA_PATTERN.test(env.buildSha)) {
    pushValidationError(errors, `${path}.buildSha`, "must match /^[0-9a-fA-F]{7,64}$/");
  }
  if (typeof env.artifactHash !== "string" || !ARTIFACT_HASH_PATTERN.test(env.artifactHash)) {
    pushValidationError(errors, `${path}.artifactHash`, "must match /^sha256:[0-9a-fA-F]{64}$/");
  }

  if (env.viewport !== undefined) {
    if (!isPlainObject(env.viewport)) {
      pushValidationError(errors, `${path}.viewport`, "must be an object");
    } else {
      const viewportAllowed = new Set(["width", "height", "deviceScaleFactor"]);
      if (!hasOnlyKeys(env.viewport, viewportAllowed)) {
        pushValidationError(errors, `${path}.viewport`, "contains unknown properties");
      }
      for (const key of ["width", "height", "deviceScaleFactor"]) {
        if (!requireKey(env.viewport, key)) {
          pushValidationError(errors, `${path}.viewport.${key}`, "missing required property");
        }
      }
      if (!Number.isInteger(env.viewport.width) || env.viewport.width < 1) {
        pushValidationError(errors, `${path}.viewport.width`, "must be an integer >= 1");
      }
      if (!Number.isInteger(env.viewport.height) || env.viewport.height < 1) {
        pushValidationError(errors, `${path}.viewport.height`, "must be an integer >= 1");
      }
      if (!Number.isFinite(env.viewport.deviceScaleFactor) || env.viewport.deviceScaleFactor <= 0) {
        pushValidationError(errors, `${path}.viewport.deviceScaleFactor`, "must be a number > 0");
      }
    }
  }
}

function validateSummary(summary, errors, path) {
  if (!isPlainObject(summary)) {
    pushValidationError(errors, path, "summary must be an object");
    return;
  }
  const required = ["status", "fixtureCount", "passed", "failed"];
  const allowed = new Set(required);
  if (!hasOnlyKeys(summary, allowed)) {
    pushValidationError(errors, path, "summary contains unknown properties");
  }
  for (const key of required) {
    if (!requireKey(summary, key)) {
      pushValidationError(errors, `${path}.${key}`, "missing required property");
    }
  }
  if (summary.status !== "passed" && summary.status !== "failed") {
    pushValidationError(errors, `${path}.status`, "must be one of: passed, failed");
  }
  for (const key of ["fixtureCount", "passed", "failed"]) {
    if (!Number.isInteger(summary[key]) || summary[key] < 0) {
      pushValidationError(errors, `${path}.${key}`, "must be an integer >= 0");
    }
  }
}

function validateAssertion(assertion, errors, path) {
  if (!isPlainObject(assertion)) {
    pushValidationError(errors, path, "assertion must be an object");
    return;
  }
  const required = ["id", "status", "metric", "comparator", "expected", "actual"];
  const allowed = new Set([...required, "tolerance"]);
  if (!hasOnlyKeys(assertion, allowed)) {
    pushValidationError(errors, path, "assertion contains unknown properties");
  }
  for (const key of required) {
    if (!requireKey(assertion, key)) {
      pushValidationError(errors, `${path}.${key}`, "missing required property");
    }
  }
  for (const key of ["id", "metric", "comparator"]) {
    if (typeof assertion[key] !== "string" || assertion[key].length < 1) {
      pushValidationError(errors, `${path}.${key}`, "must be a non-empty string");
    }
  }
  if (assertion.status !== "passed" && assertion.status !== "failed") {
    pushValidationError(errors, `${path}.status`, "must be one of: passed, failed");
  }
}

function validateDiagnostic(diagnostic, errors, path) {
  if (!isPlainObject(diagnostic)) {
    pushValidationError(errors, path, "diagnostic must be an object");
    return;
  }
  const required = ["code", "message"];
  const allowed = new Set([...required, "details"]);
  if (!hasOnlyKeys(diagnostic, allowed)) {
    pushValidationError(errors, path, "diagnostic contains unknown properties");
  }
  for (const key of required) {
    if (!requireKey(diagnostic, key)) {
      pushValidationError(errors, `${path}.${key}`, "missing required property");
    }
  }
  if (typeof diagnostic.code !== "string" || diagnostic.code.length < 1) {
    pushValidationError(errors, `${path}.code`, "must be a non-empty string");
  }
  if (typeof diagnostic.message !== "string" || diagnostic.message.length < 1) {
    pushValidationError(errors, `${path}.message`, "must be a non-empty string");
  }
}

function validateFixtureResult(fixture, errors, path) {
  if (!isPlainObject(fixture)) {
    pushValidationError(errors, path, "fixture result must be an object");
    return;
  }
  const required = ["id", "status", "durationMs", "assertions"];
  const allowed = new Set([...required, "binding", "artifacts", "diagnostics"]);
  if (!hasOnlyKeys(fixture, allowed)) {
    pushValidationError(errors, path, "fixture result contains unknown properties");
  }
  for (const key of required) {
    if (!requireKey(fixture, key)) {
      pushValidationError(errors, `${path}.${key}`, "missing required property");
    }
  }

  if (typeof fixture.id !== "string" || fixture.id.length < 1) {
    pushValidationError(errors, `${path}.id`, "must be a non-empty string");
  }
  if (!["passed", "failed", "skipped"].includes(fixture.status)) {
    pushValidationError(errors, `${path}.status`, "must be one of: passed, failed, skipped");
  }
  if (!Number.isFinite(fixture.durationMs) || fixture.durationMs < 0) {
    pushValidationError(errors, `${path}.durationMs`, "must be a number >= 0");
  }

  if (!Array.isArray(fixture.assertions)) {
    pushValidationError(errors, `${path}.assertions`, "must be an array");
  } else {
    fixture.assertions.forEach((assertion, index) => {
      validateAssertion(assertion, errors, `${path}.assertions[${index}]`);
    });
  }

  if (fixture.binding !== undefined) {
    if (!isPlainObject(fixture.binding)) {
      pushValidationError(errors, `${path}.binding`, "must be an object");
    } else {
      const allowedBinding = new Set(["testPath"]);
      if (!hasOnlyKeys(fixture.binding, allowedBinding)) {
        pushValidationError(errors, `${path}.binding`, "contains unknown properties");
      }
      if (!requireKey(fixture.binding, "testPath")) {
        pushValidationError(errors, `${path}.binding.testPath`, "missing required property");
      }
      if (typeof fixture.binding.testPath !== "string" || fixture.binding.testPath.length < 1) {
        pushValidationError(errors, `${path}.binding.testPath`, "must be a non-empty string");
      }
    }
  }

  if (fixture.artifacts !== undefined) {
    if (!Array.isArray(fixture.artifacts)) {
      pushValidationError(errors, `${path}.artifacts`, "must be an array");
    } else {
      fixture.artifacts.forEach((artifact, index) => {
        if (typeof artifact !== "string" || artifact.length < 1) {
          pushValidationError(errors, `${path}.artifacts[${index}]`, "must be a non-empty string");
        }
      });
    }
  }

  if (fixture.diagnostics !== undefined) {
    if (!Array.isArray(fixture.diagnostics)) {
      pushValidationError(errors, `${path}.diagnostics`, "must be an array");
    } else {
      fixture.diagnostics.forEach((diagnostic, index) => {
        validateDiagnostic(diagnostic, errors, `${path}.diagnostics[${index}]`);
      });
    }
  }
}

export function validateConformanceReport(report) {
  const errors = [];
  if (!isPlainObject(report)) {
    return {
      ok: false,
      errors: [{ path: "$", message: "report must be an object" }]
    };
  }

  const required = ["version", "runId", "ts", "env", "summary", "fixtures"];
  const allowed = new Set(required);
  if (!hasOnlyKeys(report, allowed)) {
    pushValidationError(errors, "$", "report contains unknown properties");
  }
  for (const key of required) {
    if (!requireKey(report, key)) {
      pushValidationError(errors, `$.${key}`, "missing required property");
    }
  }

  if (report.version !== CONFORMANCE_REPORT_VERSION) {
    pushValidationError(errors, "$.version", `must equal ${CONFORMANCE_REPORT_VERSION}`);
  }
  if (typeof report.runId !== "string" || report.runId.length < 1) {
    pushValidationError(errors, "$.runId", "must be a non-empty string");
  }
  if (!Number.isInteger(report.ts) || report.ts < 0) {
    pushValidationError(errors, "$.ts", "must be an integer >= 0");
  }

  validateEnv(report.env, errors, "$.env");
  validateSummary(report.summary, errors, "$.summary");

  if (!Array.isArray(report.fixtures)) {
    pushValidationError(errors, "$.fixtures", "must be an array");
  } else {
    report.fixtures.forEach((fixture, index) => {
      validateFixtureResult(fixture, errors, `$.fixtures[${index}]`);
    });
  }

  return {
    ok: errors.length === 0,
    errors
  };
}

export function assertConformanceReport(report) {
  const validation = validateConformanceReport(report);
  if (validation.ok) return report;
  const details = validation.errors.map((entry) => `${entry.path}: ${entry.message}`).join("; ");
  throw new Error(`conformance report schema validation failed: ${details}`);
}

function defaultRunId(seed, ts) {
  return `conformance-${seed}-${ts}`;
}

export function createConformanceRunner(options = {}) {
  const fixtureSpec = isPlainObject(options.fixtureSpec) ? options.fixtureSpec : {};
  const executionProfile = isPlainObject(fixtureSpec.executionProfile) ? fixtureSpec.executionProfile : {};
  const harnesses = resolveHarnessMap(options.harnesses);
  const now = monotonicNowFactory(options.now);
  const strictSchema = options.strictSchema !== false;

  return {
    async run(runOptions = {}) {
      const fixtures = pickFixtures(fixtureSpec, runOptions);
      const seed = normalizeString(
        runOptions.seed,
        normalizeString(options.seed, normalizeString(executionProfile.seed, "ui-conformance"))
      );
      const reportTs = resolveReportTimestamp(runOptions.ts);
      const runId = normalizeString(
        runOptions.runId,
        normalizeString(options.runId, defaultRunId(seed, reportTs))
      );

      const observedModes = new Set();
      const observedBackends = new Set();
      const fixtureResults = [];

      for (const fixture of fixtures) {
        const executed = await executeFixture(fixture, {
          executionProfile,
          harnesses,
          seed,
          now
        });

        fixtureResults.push(executed.result);
        for (const mode of executed.observedModes) observedModes.add(mode);
        for (const backend of executed.observedBackends) observedBackends.add(backend);

        if (Boolean(runOptions.abortOnFailure) && executed.result.status === "failed") {
          break;
        }
      }

      let passed = 0;
      let failed = 0;
      for (const fixtureResult of fixtureResults) {
        if (fixtureResult.status === "passed") passed += 1;
        if (fixtureResult.status === "failed") failed += 1;
      }

      const envOverrides = isPlainObject(runOptions.env)
        ? runOptions.env
        : (isPlainObject(options.env) ? options.env : {});
      const env = {
        seed,
        mode: resolveObservedModeValue(envOverrides.mode, observedModes),
        backend: resolveObservedBackendValue(envOverrides.backend, observedBackends),
        fontFallback: Boolean(envOverrides.fontFallback),
        engine: resolveEnvString(envOverrides.engine, "unknown"),
        engineVersion: resolveEnvString(envOverrides.engineVersion, "unknown"),
        os: resolveEnvString(envOverrides.os, "unknown"),
        osVersion: resolveEnvString(envOverrides.osVersion, "unknown"),
        gpu: resolveEnvString(envOverrides.gpu, "unknown"),
        buildSha: resolveBuildSha(envOverrides.buildSha),
        artifactHash: resolveArtifactHash(envOverrides.artifactHash)
      };
      const resolvedViewport = resolveEnvViewport(executionProfile.viewport, envOverrides.viewport);
      if (resolvedViewport) {
        env.viewport = resolvedViewport;
      }

      const report = {
        version: CONFORMANCE_REPORT_VERSION,
        runId,
        ts: reportTs,
        env,
        summary: {
          status: resolveSummaryStatus(failed),
          fixtureCount: fixtureResults.length,
          passed,
          failed
        },
        fixtures: fixtureResults
      };

      const validation = validateConformanceReport(report);
      if (strictSchema && !validation.ok) {
        const details = validation.errors
          .slice(0, 8)
          .map((entry) => `${entry.path}: ${entry.message}`)
          .join("; ");
        throw new Error(`conformance runner emitted invalid report: ${details}`);
      }
      return report;
    }
  };
}
