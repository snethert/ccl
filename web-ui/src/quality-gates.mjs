export const QUALITY_GATES_SCHEMA_VERSION = "1";

export const DEFAULT_QUALITY_BUDGETS = Object.freeze({
  uiTurn: Object.freeze({
    p95Ms: 16,
    p99Ms: 32
  }),
  render: Object.freeze({
    forbidFullRedrawWithDirtyHints: true
  }),
  virtualization: Object.freeze({
    enforceVisibleWindowBounds: true
  }),
  transcript: Object.freeze({
    minSupportedEntries: 10000
  }),
  reliability: Object.freeze({
    maxUnhandledRuntimeFaults: 0,
    requireDeterministicReplay: true
  })
});

const DEFAULT_METRIC_LIMITS = Object.freeze({
  uiTurns: 512,
  renders: 1024,
  virtualization: 1024,
  transcript: 128,
  reliability: 256
});

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === "[object Object]";
}

function toFiniteNumber(value, fallback = null) {
  if (value === null || value === undefined || value === "") return fallback;
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return fallback;
  return numeric;
}

function toPositiveInt(value, fallback) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return fallback;
  return Math.max(1, Math.trunc(numeric));
}

function toNonNegativeInt(value, fallback = 0) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return fallback;
  return Math.max(0, Math.trunc(numeric));
}

function cloneSample(sample) {
  try {
    return JSON.parse(JSON.stringify(sample ?? {}));
  } catch (_err) {
    return {};
  }
}

function appendBounded(list, entry, limit) {
  list.push(entry);
  if (list.length > limit) {
    list.splice(0, list.length - limit);
  }
}

function nowMs(nowFn) {
  return toFiniteNumber(nowFn?.(), Date.now());
}

function resolveSampleTimestamp(sample, nowFn) {
  const explicit = toFiniteNumber(sample?.ts, null);
  if (explicit !== null) {
    return explicit;
  }
  return nowMs(nowFn);
}

export function resolveQualityBudgets(overrides = null) {
  const next = {
    uiTurn: { ...DEFAULT_QUALITY_BUDGETS.uiTurn },
    render: { ...DEFAULT_QUALITY_BUDGETS.render },
    virtualization: { ...DEFAULT_QUALITY_BUDGETS.virtualization },
    transcript: { ...DEFAULT_QUALITY_BUDGETS.transcript },
    reliability: { ...DEFAULT_QUALITY_BUDGETS.reliability }
  };
  if (!isPlainObject(overrides)) {
    return next;
  }
  if (isPlainObject(overrides.uiTurn)) {
    if (Number.isFinite(overrides.uiTurn.p95Ms)) {
      next.uiTurn.p95Ms = Math.max(0, Number(overrides.uiTurn.p95Ms));
    }
    if (Number.isFinite(overrides.uiTurn.p99Ms)) {
      next.uiTurn.p99Ms = Math.max(0, Number(overrides.uiTurn.p99Ms));
    }
  }
  if (isPlainObject(overrides.render)) {
    if (typeof overrides.render.forbidFullRedrawWithDirtyHints === "boolean") {
      next.render.forbidFullRedrawWithDirtyHints = overrides.render.forbidFullRedrawWithDirtyHints;
    }
  }
  if (isPlainObject(overrides.virtualization)) {
    if (typeof overrides.virtualization.enforceVisibleWindowBounds === "boolean") {
      next.virtualization.enforceVisibleWindowBounds = overrides.virtualization.enforceVisibleWindowBounds;
    }
  }
  if (isPlainObject(overrides.transcript)) {
    if (Number.isFinite(overrides.transcript.minSupportedEntries)) {
      next.transcript.minSupportedEntries = Math.max(0, Math.trunc(overrides.transcript.minSupportedEntries));
    }
  }
  if (isPlainObject(overrides.reliability)) {
    if (Number.isFinite(overrides.reliability.maxUnhandledRuntimeFaults)) {
      next.reliability.maxUnhandledRuntimeFaults = Math.max(0, Math.trunc(overrides.reliability.maxUnhandledRuntimeFaults));
    }
    if (typeof overrides.reliability.requireDeterministicReplay === "boolean") {
      next.reliability.requireDeterministicReplay = overrides.reliability.requireDeterministicReplay;
    }
  }
  return next;
}

function resolveMetricLimits(overrides = null) {
  const next = { ...DEFAULT_METRIC_LIMITS };
  if (!isPlainObject(overrides)) return next;
  next.uiTurns = toPositiveInt(overrides.uiTurns, next.uiTurns);
  next.renders = toPositiveInt(overrides.renders, next.renders);
  next.virtualization = toPositiveInt(overrides.virtualization, next.virtualization);
  next.transcript = toPositiveInt(overrides.transcript, next.transcript);
  next.reliability = toPositiveInt(overrides.reliability, next.reliability);
  return next;
}

function normalizeUiTurnSample(sample, fallbackTs) {
  const durationMs = toFiniteNumber(sample?.durationMs, null);
  return {
    turnId: typeof sample?.turnId === "string" ? sample.turnId : null,
    phase: typeof sample?.phase === "string" ? sample.phase : null,
    yielded: Boolean(sample?.yielded),
    commitPolicy: typeof sample?.commitPolicy === "string" ? sample.commitPolicy : null,
    signalCount: toNonNegativeInt(sample?.signalCount, 0),
    durationMs: durationMs !== null ? Math.max(0, durationMs) : null,
    ts: toFiniteNumber(sample?.ts, fallbackTs)
  };
}

function normalizeRenderSample(sample, fallbackTs) {
  const durationMs = toFiniteNumber(sample?.durationMs, null);
  const dirtyHintCount = toNonNegativeInt(sample?.dirtyHintCount, 0);
  const dirtyRectCount = toNonNegativeInt(sample?.dirtyRectCount, 0);
  return {
    surface: typeof sample?.surface === "string" ? sample.surface : "unknown",
    backend: typeof sample?.backend === "string" ? sample.backend : "unknown",
    operation: typeof sample?.operation === "string" ? sample.operation : null,
    fullRedraw: Boolean(sample?.fullRedraw),
    dirtyHintCount,
    dirtyRectCount,
    drawnNodeCount: toNonNegativeInt(sample?.drawnNodeCount, 0),
    totalNodeCount: toNonNegativeInt(sample?.totalNodeCount, 0),
    durationMs: durationMs !== null ? Math.max(0, durationMs) : null,
    ts: toFiniteNumber(sample?.ts, fallbackTs)
  };
}

function normalizeVirtualizationSample(sample, fallbackTs) {
  return {
    widgetKind: typeof sample?.widgetKind === "string" ? sample.widgetKind : "unknown",
    widgetId: typeof sample?.widgetId === "string" ? sample.widgetId : null,
    totalCount: toNonNegativeInt(sample?.totalCount, 0),
    visibleCount: toNonNegativeInt(sample?.visibleCount, 0),
    start: toNonNegativeInt(sample?.start, 0),
    end: toNonNegativeInt(sample?.end, 0),
    expectedMaxVisible: toNonNegativeInt(sample?.expectedMaxVisible, 0),
    rowHeight: toFiniteNumber(sample?.rowHeight, null),
    viewportHeight: toFiniteNumber(sample?.viewportHeight, null),
    overscan: toNonNegativeInt(sample?.overscan, 0),
    ts: toFiniteNumber(sample?.ts, fallbackTs)
  };
}

function normalizeTranscriptSample(sample, fallbackTs) {
  return {
    entryCount: toNonNegativeInt(sample?.entryCount, 0),
    recordingCount: toNonNegativeInt(sample?.recordingCount, 0),
    truncatedEntries: toNonNegativeInt(sample?.truncatedEntries, 0),
    mode: typeof sample?.mode === "string" ? sample.mode : "unknown",
    ts: toFiniteNumber(sample?.ts, fallbackTs)
  };
}

function normalizeReliabilitySample(sample, fallbackTs) {
  return {
    kind: typeof sample?.kind === "string" ? sample.kind : "unknown",
    deterministic: sample?.deterministic === undefined ? null : Boolean(sample?.deterministic),
    handled: sample?.handled === undefined ? null : Boolean(sample?.handled),
    message: typeof sample?.message === "string" ? sample.message : null,
    details: cloneSample(sample?.details ?? null),
    ts: toFiniteNumber(sample?.ts, fallbackTs)
  };
}

function nearestRank(values, percentile) {
  if (!Array.isArray(values) || values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const rank = Math.ceil((Math.max(0, Math.min(100, percentile)) / 100) * sorted.length);
  return sorted[Math.max(0, Math.min(sorted.length - 1, rank - 1))];
}

function makeCheck(id, ok, actual, expected, details = {}) {
  return {
    id,
    ok: Boolean(ok),
    actual,
    expected,
    details: cloneSample(details)
  };
}

export function createQualityMetrics(options = {}) {
  return {
    schemaVersion: QUALITY_GATES_SCHEMA_VERSION,
    budgets: resolveQualityBudgets(options.budgets ?? null),
    limits: resolveMetricLimits(options.limits ?? null),
    samples: {
      uiTurns: [],
      renders: [],
      virtualization: [],
      transcript: [],
      reliability: []
    },
    counters: {
      uiTurns: 0,
      renders: 0,
      virtualization: 0,
      transcript: 0,
      reliability: 0
    }
  };
}

export function snapshotQualityMetrics(metrics) {
  return cloneSample(metrics ?? createQualityMetrics());
}

export function evaluateQualityBudgets(metrics, budgets = null) {
  const source = isPlainObject(metrics) ? metrics : createQualityMetrics();
  const resolvedBudgets = resolveQualityBudgets(budgets ?? source.budgets ?? null);
  const checks = [];

  const uiDurations = (source.samples?.uiTurns ?? [])
    .map((entry) => toFiniteNumber(entry?.durationMs, null))
    .filter((value) => value !== null && value >= 0);
  const p95 = nearestRank(uiDurations, 95);
  const p99 = nearestRank(uiDurations, 99);
  checks.push(
    makeCheck(
      "ui-turn-p95",
      p95 === null || p95 <= resolvedBudgets.uiTurn.p95Ms,
      p95,
      resolvedBudgets.uiTurn.p95Ms,
      { sampleCount: uiDurations.length }
    )
  );
  checks.push(
    makeCheck(
      "ui-turn-p99",
      p99 === null || p99 <= resolvedBudgets.uiTurn.p99Ms,
      p99,
      resolvedBudgets.uiTurn.p99Ms,
      { sampleCount: uiDurations.length }
    )
  );

  const renderViolations = (source.samples?.renders ?? []).filter(
    (entry) => entry?.dirtyHintCount > 0 && Boolean(entry?.fullRedraw)
  );
  checks.push(
    makeCheck(
      "render-no-full-redraw-with-dirty-hints",
      !resolvedBudgets.render.forbidFullRedrawWithDirtyHints || renderViolations.length === 0,
      renderViolations.length,
      0,
      { sampleCount: (source.samples?.renders ?? []).length }
    )
  );

  const virtualizationViolations = (source.samples?.virtualization ?? []).filter((entry) => {
    if (!resolvedBudgets.virtualization.enforceVisibleWindowBounds) return false;
    if (!Number.isFinite(entry?.expectedMaxVisible)) return false;
    return toNonNegativeInt(entry.visibleCount, 0) > toNonNegativeInt(entry.expectedMaxVisible, 0);
  });
  checks.push(
    makeCheck(
      "virtualization-visible-window-bounds",
      virtualizationViolations.length === 0,
      virtualizationViolations.length,
      0,
      { sampleCount: (source.samples?.virtualization ?? []).length }
    )
  );

  const transcriptCounts = (source.samples?.transcript ?? [])
    .map((entry) => toNonNegativeInt(entry?.entryCount, 0));
  const maxTranscriptEntries = transcriptCounts.length > 0 ? Math.max(...transcriptCounts) : null;
  checks.push(
    makeCheck(
      "transcript-supported-scale",
      maxTranscriptEntries === null || maxTranscriptEntries >= resolvedBudgets.transcript.minSupportedEntries,
      maxTranscriptEntries,
      resolvedBudgets.transcript.minSupportedEntries,
      { sampleCount: transcriptCounts.length }
    )
  );

  const reliabilitySamples = source.samples?.reliability ?? [];
  const runtimeFaults = reliabilitySamples.filter((entry) => entry?.kind === "runtime-fault");
  checks.push(
    makeCheck(
      "reliability-unhandled-runtime-faults",
      runtimeFaults.length <= resolvedBudgets.reliability.maxUnhandledRuntimeFaults,
      runtimeFaults.length,
      resolvedBudgets.reliability.maxUnhandledRuntimeFaults
    )
  );
  const replayRuns = reliabilitySamples.filter((entry) => entry?.kind === "replay-run");
  const nondeterministicRuns = replayRuns.filter((entry) => entry?.deterministic === false);
  checks.push(
    makeCheck(
      "reliability-deterministic-replay",
      !resolvedBudgets.reliability.requireDeterministicReplay || nondeterministicRuns.length === 0,
      nondeterministicRuns.length,
      0,
      { sampleCount: replayRuns.length }
    )
  );

  const failedChecks = checks.filter((check) => !check.ok);
  return {
    ok: failedChecks.length === 0,
    checks,
    failedChecks,
    summary: {
      totalChecks: checks.length,
      passedChecks: checks.length - failedChecks.length,
      failedChecks: failedChecks.length
    }
  };
}

export function createQualityCollector(options = {}) {
  const now = typeof options.now === "function" ? options.now : () => Date.now();
  const metrics = createQualityMetrics({
    budgets: options.budgets ?? null,
    limits: options.limits ?? null
  });

  function recordUiTurn(sample = {}) {
    const entry = normalizeUiTurnSample(sample, resolveSampleTimestamp(sample, now));
    appendBounded(metrics.samples.uiTurns, entry, metrics.limits.uiTurns);
    metrics.counters.uiTurns += 1;
    return entry;
  }

  function recordRender(sample = {}) {
    const entry = normalizeRenderSample(sample, resolveSampleTimestamp(sample, now));
    appendBounded(metrics.samples.renders, entry, metrics.limits.renders);
    metrics.counters.renders += 1;
    return entry;
  }

  function recordVirtualization(sample = {}) {
    const entry = normalizeVirtualizationSample(sample, resolveSampleTimestamp(sample, now));
    appendBounded(metrics.samples.virtualization, entry, metrics.limits.virtualization);
    metrics.counters.virtualization += 1;
    return entry;
  }

  function recordTranscript(sample = {}) {
    const entry = normalizeTranscriptSample(sample, resolveSampleTimestamp(sample, now));
    appendBounded(metrics.samples.transcript, entry, metrics.limits.transcript);
    metrics.counters.transcript += 1;
    return entry;
  }

  function recordReliability(sample = {}) {
    const entry = normalizeReliabilitySample(sample, resolveSampleTimestamp(sample, now));
    appendBounded(metrics.samples.reliability, entry, metrics.limits.reliability);
    metrics.counters.reliability += 1;
    return entry;
  }

  function beginUiTurn(sample = {}) {
    return {
      turnId: typeof sample.turnId === "string" ? sample.turnId : null,
      phase: typeof sample.phase === "string" ? sample.phase : null,
      commitPolicy: typeof sample.commitPolicy === "string" ? sample.commitPolicy : null,
      signalCount: toNonNegativeInt(sample.signalCount, 0),
      startedAt: toFiniteNumber(sample.startedAt, nowMs(now))
    };
  }

  function endUiTurn(token, sample = {}) {
    const startedAt = toFiniteNumber(token?.startedAt, null);
    const endedAt = toFiniteNumber(sample.endedAt, nowMs(now));
    const durationMs = startedAt === null ? null : Math.max(0, endedAt - startedAt);
    return recordUiTurn({
      turnId: sample.turnId ?? token?.turnId ?? null,
      phase: sample.phase ?? token?.phase ?? null,
      yielded: sample.yielded ?? false,
      commitPolicy: sample.commitPolicy ?? token?.commitPolicy ?? null,
      signalCount: sample.signalCount ?? token?.signalCount ?? 0,
      durationMs,
      ts: endedAt
    });
  }

  function reset() {
    metrics.samples.uiTurns = [];
    metrics.samples.renders = [];
    metrics.samples.virtualization = [];
    metrics.samples.transcript = [];
    metrics.samples.reliability = [];
    metrics.counters.uiTurns = 0;
    metrics.counters.renders = 0;
    metrics.counters.virtualization = 0;
    metrics.counters.transcript = 0;
    metrics.counters.reliability = 0;
  }

  return {
    schemaVersion: QUALITY_GATES_SCHEMA_VERSION,
    budgets: metrics.budgets,
    limits: metrics.limits,
    metrics,
    now,
    beginUiTurn,
    endUiTurn,
    recordUiTurn,
    recordRender,
    recordVirtualization,
    recordTranscript,
    recordReliability,
    evaluate() {
      return evaluateQualityBudgets(metrics, metrics.budgets);
    },
    snapshot() {
      return snapshotQualityMetrics(metrics);
    },
    reset
  };
}

