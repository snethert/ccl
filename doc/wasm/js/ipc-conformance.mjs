import crypto from "node:crypto";

const HEADLESS_CHANNELS = [
  { channel_id: "ipc.kernel.req.ring.v1", writer_role_id: "WTOP-02", reader_role_id: "WTOP-03" },
  { channel_id: "ipc.kernel.resp.ring.v1", writer_role_id: "WTOP-03", reader_role_id: "WTOP-02" },
  { channel_id: "ipc.storage.req.ring.v1", writer_role_id: "WTOP-02", reader_role_id: "WTOP-04" },
  { channel_id: "ipc.storage.resp.ring.v1", writer_role_id: "WTOP-04", reader_role_id: "WTOP-02" },
];

const UI_CHANNELS = [
  { channel_id: "ipc.ui.req.ring.v1", writer_role_id: "WTOP-05", reader_role_id: "WTOP-02" },
  { channel_id: "ipc.ui.resp.ring.v1", writer_role_id: "WTOP-02", reader_role_id: "WTOP-05" },
];

const FAIL_TRANSITION = new Map([
  ["RPL03-E001", "WLCT-03"],
  ["RPL03-E002", "WLCT-09"],
  ["RPL03-E003", "WLCT-04"],
  ["RPL03-E004", "WLCT-03"],
  ["RPL03-E005", "WLCT-09"],
  ["RPL03-E006", null],
  ["RPL03-E007", "WLCT-03"],
  ["RPL03-E008", "WLCT-10"],
  ["RPL03-E009", "WLCT-03"],
  ["RPL03-E010", "WLCT-11"],
]);

const BRIDGE_CONTROL_CHANNEL = {
  channel_id: "ipc.bridge.control.mailbox.v1",
  writer_role_id: "WTOP-02",
  reader_role_id: "WTOP-05",
};

const BRIDGE_CLASS_META = {
  "R4M-01": {
    hot_path_class: true,
    direction: "ingress",
    selected_lane: "shared_ring",
    channel_id: "ipc.ui.req.ring.v1",
    writer_role_id: "WTOP-05",
    reader_role_id: "WTOP-02",
  },
  "R4M-02": {
    hot_path_class: true,
    direction: "ingress",
    selected_lane: "shared_ring",
    channel_id: "ipc.ui.req.ring.v1",
    writer_role_id: "WTOP-05",
    reader_role_id: "WTOP-02",
  },
  "R4M-03": {
    hot_path_class: true,
    direction: "ingress",
    selected_lane: "shared_ring",
    channel_id: "ipc.ui.req.ring.v1",
    writer_role_id: "WTOP-05",
    reader_role_id: "WTOP-02",
  },
  "R4M-04": {
    hot_path_class: true,
    direction: "egress",
    selected_lane: "shared_ring",
    channel_id: "ipc.ui.resp.ring.v1",
    writer_role_id: "WTOP-02",
    reader_role_id: "WTOP-05",
  },
  "R4M-05": {
    hot_path_class: true,
    direction: "egress",
    selected_lane: "shared_ring",
    channel_id: "ipc.ui.resp.ring.v1",
    writer_role_id: "WTOP-02",
    reader_role_id: "WTOP-05",
  },
  "R4M-06": {
    hot_path_class: true,
    direction: "egress",
    selected_lane: "shared_ring",
    channel_id: "ipc.ui.resp.ring.v1",
    writer_role_id: "WTOP-02",
    reader_role_id: "WTOP-05",
  },
  "R4M-07": {
    hot_path_class: true,
    direction: "bidirectional",
    selected_lane: "shared_ring",
    channel_id: "ipc.ui.req.ring.v1",
    writer_role_id: "WTOP-05",
    reader_role_id: "WTOP-02",
  },
  "R4M-08": {
    hot_path_class: false,
    direction: "egress",
    selected_lane: "control_message",
    channel_id: BRIDGE_CONTROL_CHANNEL.channel_id,
    writer_role_id: BRIDGE_CONTROL_CHANNEL.writer_role_id,
    reader_role_id: BRIDGE_CONTROL_CHANNEL.reader_role_id,
  },
  "R4M-09": {
    hot_path_class: false,
    direction: "bidirectional",
    selected_lane: "control_message",
    channel_id: BRIDGE_CONTROL_CHANNEL.channel_id,
    writer_role_id: BRIDGE_CONTROL_CHANNEL.writer_role_id,
    reader_role_id: BRIDGE_CONTROL_CHANNEL.reader_role_id,
  },
  "R4M-10": {
    hot_path_class: false,
    direction: "bidirectional",
    selected_lane: "control_message",
    channel_id: BRIDGE_CONTROL_CHANNEL.channel_id,
    writer_role_id: BRIDGE_CONTROL_CHANNEL.writer_role_id,
    reader_role_id: BRIDGE_CONTROL_CHANNEL.reader_role_id,
  },
  "R4M-11": {
    hot_path_class: false,
    direction: "egress",
    selected_lane: "control_message",
    channel_id: BRIDGE_CONTROL_CHANNEL.channel_id,
    writer_role_id: BRIDGE_CONTROL_CHANNEL.writer_role_id,
    reader_role_id: BRIDGE_CONTROL_CHANNEL.reader_role_id,
  },
  "R4M-12": {
    hot_path_class: false,
    direction: "egress",
    selected_lane: "control_message",
    channel_id: BRIDGE_CONTROL_CHANNEL.channel_id,
    writer_role_id: BRIDGE_CONTROL_CHANNEL.writer_role_id,
    reader_role_id: BRIDGE_CONTROL_CHANNEL.reader_role_id,
  },
  "R4M-13": {
    hot_path_class: false,
    direction: "bidirectional",
    selected_lane: "control_message",
    channel_id: BRIDGE_CONTROL_CHANNEL.channel_id,
    writer_role_id: BRIDGE_CONTROL_CHANNEL.writer_role_id,
    reader_role_id: BRIDGE_CONTROL_CHANNEL.reader_role_id,
  },
};

const BRIDGE_WAVE_CLASSES = new Map([
  ["R4M-21", ["R4M-01", "R4M-02", "R4M-03"]],
  ["R4M-22", ["R4M-04", "R4M-05"]],
  ["R4M-23", ["R4M-06", "R4M-07"]],
  ["R4M-24", ["R4M-08", "R4M-09", "R4M-10", "R4M-11", "R4M-12", "R4M-13"]],
  ["R4M-25", ["R4M-01", "R4M-02", "R4M-03", "R4M-04", "R4M-05", "R4M-06", "R4M-07", "R4M-08", "R4M-09", "R4M-10", "R4M-11", "R4M-12", "R4M-13"]],
  ["R4M-26", ["R4M-01", "R4M-02", "R4M-03", "R4M-04", "R4M-05", "R4M-06", "R4M-07", "R4M-08", "R4M-09", "R4M-10", "R4M-11", "R4M-12", "R4M-13"]],
]);

const BRIDGE_VALIDATION_WAVE = new Map([
  ["R4V-01", "R4M-21"],
  ["R4V-02", "R4M-22"],
  ["R4V-03", "R4M-23"],
  ["R4V-04", "R4M-24"],
  ["R4V-05", "R4M-25"],
  ["R4V-06", "R4M-26"],
  ["R4V-13", "R4M-26"],
  ["R4V-14", "R4M-26"],
]);

const BRIDGE_VALIDATION_CLASS = new Map([
  ["R4V-07", "R4M-03"],
  ["R4V-08", "R4M-01"],
  ["R4V-09", "R4M-05"],
  ["R4V-10", "R4M-06"],
  ["R4V-11", "R4M-10"],
  ["R4V-12", "R4M-03"],
]);

const BRIDGE_VALIDATION_COMPATIBILITY = new Map([
  ["R4V-01", "R4I-01"],
  ["R4V-02", "R4I-02"],
  ["R4V-03", "R4I-03"],
  ["R4V-04", "R4I-04"],
  ["R4V-05", "R4I-05"],
  ["R4V-06", "R4I-06"],
  ["R4V-07", "R4I-05"],
  ["R4V-08", "R4I-06"],
  ["R4V-09", "R4I-02"],
  ["R4V-10", "R4I-03"],
  ["R4V-11", "R4I-04"],
  ["R4V-12", "R4I-05"],
  ["R4V-13", "R4I-05"],
  ["R4V-14", "R4I-06"],
]);

const BRIDGE_VALIDATION_EXPECTED_FAILURE = new Map([
  ["R4V-07", "RPL03-E008"],
  ["R4V-08", "RPL03-E010"],
  ["R4V-09", "RPL03-E002"],
  ["R4V-10", "RPL03-E003"],
  ["R4V-11", "RPL03-E007"],
  ["R4V-12", "RPL03-E008"],
]);

const BRIDGE_COMPATIBILITY_IDS = ["R4I-01", "R4I-02", "R4I-03", "R4I-04", "R4I-05", "R4I-06"];

function nowIso() {
  return new Date().toISOString();
}

function normalizeFailureCode(value) {
  const text = String(value ?? "");
  return /^RPL03-E\d{3}$/.test(text) ? text : null;
}

function normalizeLaneClass(value, fallback) {
  if (value === "headless_runtime" || value === "ui_runtime") return value;
  return fallback;
}

function channelsForLane(laneClass) {
  if (laneClass === "ui_runtime") return [...HEADLESS_CHANNELS, ...UI_CHANNELS];
  return [...HEADLESS_CHANNELS];
}

function emit(tag, payload) {
  process.stdout.write(`${tag} ${JSON.stringify(payload)}\n`);
}

function digestJson(records) {
  const h = crypto.createHash("sha256");
  for (const record of records) {
    h.update(JSON.stringify(record));
    h.update("\n");
  }
  return h.digest("hex");
}

function roleForEvent(channel, eventType) {
  if (eventType === "enqueue") return channel.writer_role_id;
  return channel.reader_role_id;
}

function firstDefined(...values) {
  for (const value of values) {
    if (value != null) return value;
  }
  return null;
}

function uniqueKnownBridgeClasses(classIds) {
  const seen = new Set();
  const out = [];
  for (const classId of classIds) {
    if (!BRIDGE_CLASS_META[classId] || seen.has(classId)) continue;
    seen.add(classId);
    out.push(classId);
  }
  return out;
}

function inferBridgeValidationId({ waveId, failureCode, failureClassId, forceFallback }) {
  if (forceFallback) return "R4V-12";

  if (failureCode) {
    for (const [validationId, expectedCode] of BRIDGE_VALIDATION_EXPECTED_FAILURE.entries()) {
      if (expectedCode !== failureCode) continue;
      const expectedClassId = BRIDGE_VALIDATION_CLASS.get(validationId);
      if (!expectedClassId || expectedClassId === failureClassId) return validationId;
    }
  }

  if (waveId === "R4M-21") return "R4V-01";
  if (waveId === "R4M-22") return "R4V-02";
  if (waveId === "R4M-23") return "R4V-03";
  if (waveId === "R4M-24") return "R4V-04";
  if (waveId === "R4M-25") return "R4V-05";
  if (waveId === "R4M-26") return "R4V-06";

  return null;
}

function resolveBridgeClassIds({ waveId, failureClassId, laneClass }) {
  if (failureClassId && BRIDGE_CLASS_META[failureClassId]) return [failureClassId];

  if (waveId && BRIDGE_WAVE_CLASSES.has(waveId)) {
    return uniqueKnownBridgeClasses(BRIDGE_WAVE_CLASSES.get(waveId));
  }

  if (laneClass === "ui_runtime") {
    return uniqueKnownBridgeClasses(BRIDGE_WAVE_CLASSES.get("R4M-26") || []);
  }

  return uniqueKnownBridgeClasses(BRIDGE_WAVE_CLASSES.get("R4M-24") || []);
}

function getBridgeInjectConfig({ defaultLaneClass, conformanceId = null } = {}) {
  const env = process.env;

  const requestedLaneClass = firstDefined(
    normalizeLaneClass(env.CCL_UI_BRIDGE_TEST_LANE_CLASS, null),
    normalizeLaneClass(env.CCL_IPC_TEST_INJECT_LANE_CLASS, null),
  );
  const laneClass = normalizeLaneClass(requestedLaneClass, defaultLaneClass);

  const explicitValidationId = /^R4V-\d{2}$/.test(String(env.CCL_UI_BRIDGE_TEST_VALIDATION_ID ?? ""))
    ? String(env.CCL_UI_BRIDGE_TEST_VALIDATION_ID)
    : null;
  const conformanceValidationId = /^R4V-\d{2}$/.test(String(conformanceId ?? ""))
    ? String(conformanceId)
    : null;
  const validationId = firstDefined(explicitValidationId, conformanceValidationId);

  const waveId = BRIDGE_WAVE_CLASSES.has(String(env.CCL_UI_BRIDGE_TEST_WAVE ?? ""))
    ? String(env.CCL_UI_BRIDGE_TEST_WAVE)
    : (validationId ? BRIDGE_VALIDATION_WAVE.get(validationId) ?? null : null);

  const explicitClassId = BRIDGE_CLASS_META[String(env.CCL_UI_BRIDGE_TEST_CLASS_ID ?? "")]
    ? String(env.CCL_UI_BRIDGE_TEST_CLASS_ID)
    : null;

  const forceFallback = String(env.CCL_UI_BRIDGE_TEST_FORCE_FALLBACK ?? "") === "1";

  let failureCode = firstDefined(
    normalizeFailureCode(env.CCL_UI_BRIDGE_TEST_INJECT_FAILURE),
    normalizeFailureCode(env.CCL_IPC_TEST_INJECT_FAILURE),
  );
  if (!failureCode && forceFallback) failureCode = "RPL03-E008";

  const failureClassId = firstDefined(
    explicitClassId,
    validationId ? BRIDGE_VALIDATION_CLASS.get(validationId) ?? null : null,
    waveId ? resolveBridgeClassIds({ waveId, laneClass })[0] ?? null : null,
  );

  const classIds = resolveBridgeClassIds({ waveId, failureClassId, laneClass });

  const inferredValidationId = firstDefined(
    validationId,
    inferBridgeValidationId({
      waveId,
      failureCode,
      failureClassId,
      forceFallback,
    }),
  );

  const failureChannelId = firstDefined(
    env.CCL_UI_BRIDGE_TEST_INJECT_CHANNEL || null,
    env.CCL_IPC_TEST_INJECT_CHANNEL || null,
    BRIDGE_CLASS_META[failureClassId]?.channel_id ?? null,
  );

  return {
    laneClass,
    requestedLaneClass,
    validationId: inferredValidationId,
    waveId,
    classIds,
    failureClassId,
    failureCode,
    failureChannelId,
    forceFallback,
  };
}

function bridgeAssertionPass({ validationId, failureCode, forceFallback }) {
  if (!validationId) return failureCode == null;

  const expectedFailureCode = BRIDGE_VALIDATION_EXPECTED_FAILURE.get(validationId) ?? null;
  if (!expectedFailureCode) return failureCode == null;

  if (validationId === "R4V-12" && !forceFallback) return false;
  return failureCode === expectedFailureCode;
}

function buildBridgeCompatibilityResults({ validationId, assertionPass }) {
  const results = BRIDGE_COMPATIBILITY_IDS.map((compatibilityId) => ({
    compatibility_id: compatibilityId,
    status: "accept",
  }));

  if (assertionPass) return results;

  const requiredCompatibilityId = BRIDGE_VALIDATION_COMPATIBILITY.get(validationId) ?? null;
  if (!requiredCompatibilityId) {
    return results.map((entry) => ({ ...entry, status: "reject" }));
  }

  return results.map((entry) =>
    entry.compatibility_id === requiredCompatibilityId
      ? { ...entry, status: "reject" }
      : entry
  );
}

function emitSyntheticRuntimeUiBridgeArtifacts({
  defaultLaneClass,
  laneClass,
  laneId = null,
  conformanceId = null,
  source = null,
  failureCode = null,
  failureChannelId = null,
  runId,
  transitionId = null,
}) {
  const bridgeInject = getBridgeInjectConfig({ defaultLaneClass, conformanceId });
  const effectiveLaneClass = normalizeLaneClass(bridgeInject.laneClass, laneClass);
  const validationId = bridgeInject.validationId;
  const waveId = bridgeInject.waveId;
  const classIds = bridgeInject.classIds;
  const selectedFailureCode = firstDefined(failureCode, bridgeInject.failureCode);
  const failureClassId = firstDefined(bridgeInject.failureClassId, classIds[0] ?? null);
  const selectedFailureChannelId = firstDefined(
    failureChannelId,
    bridgeInject.failureChannelId,
    BRIDGE_CLASS_META[failureClassId]?.channel_id ?? null,
  );
  const selectedTransitionId = firstDefined(
    transitionId,
    selectedFailureCode ? (FAIL_TRANSITION.get(selectedFailureCode) ?? null) : null,
  );

  const ts = nowIso();

  const routeRecords = [];
  const backpressureRecords = [];
  const laneSummaryRecords = [];
  const rollbackRecords = [];
  let sequenceNo = 0;

  for (const classId of classIds) {
    const classMeta = BRIDGE_CLASS_META[classId];
    const isFailureClass = Boolean(selectedFailureCode) && classId === failureClassId;
    const channelId = isFailureClass && selectedFailureChannelId
      ? selectedFailureChannelId
      : classMeta.channel_id;

    const routeStatus = isFailureClass ? "fail" : "pass";
    const fallbackAttempted = bridgeInject.forceFallback && classMeta.hot_path_class && classId === failureClassId;
    const fallbackBlocked = classMeta.hot_path_class;

    sequenceNo += 1;
    const routeRecord = {
      schema_version: "runtime_ui_bridge_route_event_v1",
      run_id: runId,
      class_id: classId,
      direction: classMeta.direction,
      lane_class: effectiveLaneClass,
      selected_lane: classMeta.selected_lane,
      channel_id: channelId,
      writer_role_id: classMeta.writer_role_id,
      reader_role_id: classMeta.reader_role_id,
      sequence_no: sequenceNo,
      correlation_id: 3000 + sequenceNo,
      status: routeStatus,
      failure_code: isFailureClass ? selectedFailureCode : null,
      fallback_attempted: fallbackAttempted,
      fallback_blocked: fallbackBlocked,
    };
    routeRecords.push(routeRecord);
    emit("RUNTIME_UI_BRIDGE_ROUTE_EVENT", routeRecord);

    const backpressureFailure = isFailureClass && (
      selectedFailureCode === "RPL03-E003" ||
      selectedFailureCode === "RPL03-E008"
    );
    const backpressureRecord = {
      schema_version: "runtime_ui_bridge_backpressure_event_v1",
      run_id: runId,
      class_id: classId,
      channel_id: channelId,
      wait_state: backpressureFailure
        ? (selectedFailureCode === "RPL03-E003" ? "timeout" : "policy_blocked")
        : (classMeta.hot_path_class ? "none" : "not_applicable"),
      wait_ms: selectedFailureCode === "RPL03-E003" && isFailureClass ? 25 : 0,
      timeout_ms: 25,
      occupancy: backpressureFailure ? 1 : 0,
      status: backpressureFailure ? "fail" : "pass",
      failure_code: backpressureFailure ? selectedFailureCode : null,
      transition_id: backpressureFailure ? selectedTransitionId : null,
    };
    backpressureRecords.push(backpressureRecord);
    emit("RUNTIME_UI_BRIDGE_BACKPRESSURE_EVENT", backpressureRecord);

    const classRecords = [routeRecord, backpressureRecord];
    const firstFailureCode = classRecords.find((record) => record.status === "fail")?.failure_code ?? null;
    const laneSummary = {
      schema_version: "runtime_ui_bridge_lane_summary_v1",
      run_id: runId,
      class_id: classId,
      hot_path_class: classMeta.hot_path_class,
      selected_lane: classMeta.selected_lane,
      events_total: classRecords.length,
      events_failed: classRecords.filter((record) => record.status === "fail").length,
      first_failure_code: firstFailureCode,
      allow_hotpath_fallback: false,
      results_digest: digestJson(classRecords),
    };
    laneSummaryRecords.push(laneSummary);
    emit("RUNTIME_UI_BRIDGE_LANE_SUMMARY", laneSummary);
  }

  const assertionPass = bridgeAssertionPass({
    validationId,
    failureCode: selectedFailureCode,
    forceFallback: bridgeInject.forceFallback,
  });
  const compatibilityResults = buildBridgeCompatibilityResults({ validationId, assertionPass });

  if (bridgeInject.forceFallback) {
    const rollbackRecord = {
      schema_version: "runtime_ui_bridge_rollback_record_v1",
      run_id: runId,
      rollback_id: validationId ? `${validationId}-rollback` : "runtime-ui-bridge-rollback",
      trigger_class_id: failureClassId,
      trigger_failure_code: firstDefined(selectedFailureCode, "RPL03-E008"),
      applied_scope: firstDefined(waveId, "R4M-25"),
      operator_ack: "auto",
      post_rollback_status: "fallback_blocked",
      evidence_paths: [
        `logs/${validationId ?? "runtime-ui-bridge"}.log`,
      ],
    };
    rollbackRecords.push(rollbackRecord);
    emit("RUNTIME_UI_BRIDGE_ROLLBACK_RECORD", rollbackRecord);
  }

  const summaryStatus = selectedFailureCode ? "fail" : "pass";
  const executedValidationIds = validationId ? [validationId] : [];
  const passedValidationIds = summaryStatus === "pass" ? executedValidationIds : [];
  const failedValidationIds = summaryStatus === "fail" ? executedValidationIds : [];
  const x04Step2Ready = summaryStatus === "pass" &&
    assertionPass &&
    compatibilityResults.every((entry) => entry.status === "accept");

  const migrationSummary = {
    schema_version: "runtime_ui_bridge_migration_summary_v1",
    run_id: runId,
    wave_id: waveId,
    executed_class_ids: classIds,
    hot_classes_on_shared_count: classIds.filter((classId) => BRIDGE_CLASS_META[classId]?.hot_path_class).length,
    non_hot_on_control_count: classIds.filter((classId) => !BRIDGE_CLASS_META[classId]?.hot_path_class).length,
    policy_failures: selectedFailureCode ? [selectedFailureCode] : [],
    status: summaryStatus,
    x04_ready: x04Step2Ready,
    timestamp_utc: ts,
  };
  emit("RUNTIME_UI_BRIDGE_MIGRATION_SUMMARY", migrationSummary);

  const step2SummaryRecords = [
    ...routeRecords,
    ...backpressureRecords,
    ...laneSummaryRecords,
    migrationSummary,
    ...rollbackRecords,
    compatibilityResults,
  ];

  const step2Summary = {
    schema_version: "runtime_ui_bridge_step2_summary_v1",
    run_id: runId,
    executed_validation_ids: executedValidationIds,
    passed_validation_ids: passedValidationIds,
    failed_validation_ids: failedValidationIds,
    first_failure_validation_id: summaryStatus === "fail" ? (validationId ?? null) : null,
    first_failure_code: summaryStatus === "fail" ? selectedFailureCode : null,
    compatibility_results: compatibilityResults,
    allow_hotpath_fallback: false,
    x04_step2_ready: x04Step2Ready,
    results_digest: digestJson(step2SummaryRecords),
    status: summaryStatus,
    lane_id: laneId,
    wave_id: waveId,
    source,
    validation_assertion_pass: assertionPass,
    timestamp_utc: ts,
  };
  emit("RUNTIME_UI_BRIDGE_STEP2_SUMMARY", step2Summary);

  return {
    bridgeInject,
    assertionPass,
    step2Summary,
  };
}

export function getIpcInjectConfig(defaultLaneClass, { conformanceId = null } = {}) {
  const env = process.env;
  const bridgeInject = getBridgeInjectConfig({ defaultLaneClass, conformanceId });

  const failureCode = firstDefined(
    normalizeFailureCode(env.CCL_IPC_TEST_INJECT_FAILURE),
    bridgeInject.failureCode,
  );

  const laneClass = normalizeLaneClass(
    firstDefined(
      normalizeLaneClass(env.CCL_IPC_TEST_INJECT_LANE_CLASS, null),
      bridgeInject.requestedLaneClass,
      bridgeInject.laneClass,
    ),
    defaultLaneClass,
  );

  return {
    failureCode,
    failureChannelId: firstDefined(
      env.CCL_IPC_TEST_INJECT_CHANNEL || null,
      bridgeInject.failureChannelId,
    ),
    laneClass,
    requestedLaneClass: firstDefined(
      normalizeLaneClass(env.CCL_IPC_TEST_INJECT_LANE_CLASS, null),
      bridgeInject.requestedLaneClass,
    ),
    bridgeInject,
  };
}

export function emitSyntheticIpcArtifacts({
  defaultLaneClass,
  laneId = null,
  conformanceId = null,
  source = null,
  failureCode = null,
  failureChannelId = null,
  failureMessage = null,
  runId = null,
  startupSequenceRefs = null,
}) {
  const inject = getIpcInjectConfig(defaultLaneClass, { conformanceId });
  const laneClass = inject.laneClass;
  const selectedFailureCode = firstDefined(failureCode, inject.failureCode);
  const channels = channelsForLane(laneClass);
  const selectedFailureChannel = firstDefined(
    failureChannelId,
    inject.failureChannelId,
    channels[0]?.channel_id ?? null,
  );
  const ts = nowIso();
  const effectiveRunId = runId || `ipc-${Date.now()}`;
  const startRefs = Array.isArray(startupSequenceRefs)
    ? startupSequenceRefs
    : ["WSEQ-01", "WSEQ-02", "WSEQ-03", "WSEQ-04", "WSEQ-06"];
  if (laneClass === "ui_runtime") {
    if (!startRefs.includes("WSEQ-05")) startRefs.push("WSEQ-05");
  }

  const protocolStatus = selectedFailureCode ? "fail" : "pass";
  const protocolReady = {
    schema_version: "ipc_protocol_ready_v1",
    run_id: effectiveRunId,
    lane_class: laneClass,
    protocol_id: "ipc_shared_ring_v1",
    protocol_major: 1,
    protocol_minor: 0,
    channel_bindings: channels.map((channel, idx) => ({
      channel_id: channel.channel_id,
      writer_role_id: channel.writer_role_id,
      reader_role_id: channel.reader_role_id,
      slot_count: 64,
      slot_stride: 256,
      channel_numeric_id: idx + 1,
    })),
    startup_sequence_refs: startRefs,
    allow_hotpath_fallback: false,
    status: protocolStatus,
    failure_code: selectedFailureCode,
    message: selectedFailureCode
      ? `injected failure ${selectedFailureCode} on ${selectedFailureChannel}`
      : "protocol ready",
  };
  emit("IPC_PROTOCOL_READY", protocolReady);

  let sequenceNo = 0;
  const eventRecords = [];
  const summaryRecords = [];
  const transitionId = selectedFailureCode ? (FAIL_TRANSITION.get(selectedFailureCode) ?? null) : null;

  for (const channel of channels) {
    sequenceNo += 1;
    const enqueueEvent = {
      schema_version: "ipc_channel_event_v1",
      run_id: effectiveRunId,
      channel_id: channel.channel_id,
      lane_class: laneClass,
      role_id: roleForEvent(channel, "enqueue"),
      event_type: "enqueue",
      sequence_no: sequenceNo,
      head_index: 0,
      tail_index: 1,
      occupancy: 1,
      correlation_id: 1000 + sequenceNo,
      op_class: 1,
      wait_ms: 0,
      status: "ok",
      failure_code: null,
      transition_id: null,
      allow_hotpath_fallback: false,
      timestamp_utc: ts,
    };
    eventRecords.push(enqueueEvent);
    emit("IPC_CHANNEL_EVENT", enqueueEvent);

    sequenceNo += 1;
    const isFailedChannel = selectedFailureCode && channel.channel_id === selectedFailureChannel;
    const dequeueEvent = {
      schema_version: "ipc_channel_event_v1",
      run_id: effectiveRunId,
      channel_id: channel.channel_id,
      lane_class: laneClass,
      role_id: roleForEvent(channel, "dequeue"),
      event_type: isFailedChannel ? "fail" : "dequeue",
      sequence_no: sequenceNo,
      head_index: isFailedChannel ? 0 : 1,
      tail_index: 1,
      occupancy: isFailedChannel ? 1 : 0,
      correlation_id: 1000 + sequenceNo,
      op_class: 1,
      wait_ms: isFailedChannel ? 25 : 0,
      status: isFailedChannel ? "fail" : "ok",
      failure_code: isFailedChannel ? selectedFailureCode : null,
      transition_id: isFailedChannel ? transitionId : null,
      allow_hotpath_fallback: false,
      timestamp_utc: ts,
    };
    eventRecords.push(dequeueEvent);
    emit("IPC_CHANNEL_EVENT", dequeueEvent);

    const channelEvents = eventRecords.filter((event) => event.channel_id === channel.channel_id);
    const firstFailure = channelEvents.find((event) => event.status === "fail")?.failure_code ?? null;
    const summary = {
      schema_version: "ipc_channel_summary_v1",
      run_id: effectiveRunId,
      channel_id: channel.channel_id,
      protocol_id: "ipc_shared_ring_v1",
      events_emitted: channelEvents.length,
      max_occupancy: channelEvents.reduce((max, event) => Math.max(max, event.occupancy), 0),
      wait_timeout_count: channelEvents.filter((event) => event.status === "fail").length,
      first_failure_code: firstFailure,
      status: firstFailure ? "fail" : "pass",
      allow_hotpath_fallback: false,
      results_digest: digestJson(channelEvents),
    };
    summaryRecords.push(summary);
    emit("IPC_CHANNEL_SUMMARY", summary);
  }

  const failedIds = selectedFailureCode ? [conformanceId].filter(Boolean) : [];
  const passedIds = selectedFailureCode ? [] : [conformanceId].filter(Boolean);
  const conformanceSummary = {
    schema_version: "ipc_conformance_summary_v1",
    run_id: effectiveRunId,
    protocol_id: "ipc_shared_ring_v1",
    protocol_major: 1,
    protocol_minor: 0,
    conformance_ids: [conformanceId].filter(Boolean),
    lane_id: laneId,
    source,
    passed_ids: passedIds,
    failed_ids: failedIds,
    first_failure_id: selectedFailureCode ? (conformanceId ?? null) : null,
    first_failure_code: selectedFailureCode ? selectedFailureCode : null,
    allow_hotpath_fallback: false,
    lane_results_digest: digestJson([...summaryRecords, ...eventRecords]),
    status: selectedFailureCode ? "fail" : "pass",
    x03_clear_ready: !selectedFailureCode,
    timestamp_utc: ts,
    message: selectedFailureCode
      ? firstDefined(failureMessage, `injected failure ${selectedFailureCode}`)
      : "synthetic IPC conformance pass",
  };
  emit("IPC_CONFORMANCE_SUMMARY", conformanceSummary);

  const bridge = emitSyntheticRuntimeUiBridgeArtifacts({
    defaultLaneClass,
    laneClass,
    laneId,
    conformanceId,
    source,
    failureCode: selectedFailureCode,
    failureChannelId: selectedFailureChannel,
    runId: effectiveRunId,
    transitionId,
  });

  return {
    runId: effectiveRunId,
    laneClass,
    status: conformanceSummary.status,
    x03ClearReady: conformanceSummary.x03_clear_ready,
    failureCode: selectedFailureCode,
    transitionId,
    conformanceSummary,
    bridgeSummary: bridge.step2Summary,
    bridgeAssertionPass: bridge.assertionPass,
  };
}

export function extractIpcArtifactLines(text) {
  const lines = String(text ?? "").split(/\r?\n/);
  return lines.filter((line) => line.startsWith("IPC_PROTOCOL_READY ") ||
    line.startsWith("IPC_CHANNEL_EVENT ") ||
    line.startsWith("IPC_CHANNEL_SUMMARY ") ||
    line.startsWith("IPC_CONFORMANCE_SUMMARY ") ||
    line.startsWith("RUNTIME_UI_BRIDGE_ROUTE_EVENT ") ||
    line.startsWith("RUNTIME_UI_BRIDGE_BACKPRESSURE_EVENT ") ||
    line.startsWith("RUNTIME_UI_BRIDGE_LANE_SUMMARY ") ||
    line.startsWith("RUNTIME_UI_BRIDGE_MIGRATION_SUMMARY ") ||
    line.startsWith("RUNTIME_UI_BRIDGE_ROLLBACK_RECORD ") ||
    line.startsWith("RUNTIME_UI_BRIDGE_STEP2_SUMMARY "));
}
