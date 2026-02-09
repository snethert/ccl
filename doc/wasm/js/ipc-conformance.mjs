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

function nowIso() {
  return new Date().toISOString();
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

export function getIpcInjectConfig(defaultLaneClass) {
  const env = process.env;
  const failureCodeRaw = env.CCL_IPC_TEST_INJECT_FAILURE;
  const failureCode = /^RPL03-E\d{3}$/.test(String(failureCodeRaw ?? ""))
    ? String(failureCodeRaw)
    : null;
  return {
    failureCode,
    failureChannelId: env.CCL_IPC_TEST_INJECT_CHANNEL || null,
    laneClass: normalizeLaneClass(env.CCL_IPC_TEST_INJECT_LANE_CLASS, defaultLaneClass),
    requestedLaneClass: normalizeLaneClass(env.CCL_IPC_TEST_INJECT_LANE_CLASS, null),
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
  const inject = getIpcInjectConfig(defaultLaneClass);
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

  const firstFailedEvent = eventRecords.find((event) => event.status === "fail") ?? null;
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

  return {
    runId: effectiveRunId,
    laneClass,
    status: conformanceSummary.status,
    x03ClearReady: conformanceSummary.x03_clear_ready,
    failureCode: selectedFailureCode,
    transitionId,
    conformanceSummary,
  };
}

export function extractIpcArtifactLines(text) {
  const lines = String(text ?? "").split(/\r?\n/);
  return lines.filter((line) => line.startsWith("IPC_PROTOCOL_READY ") ||
    line.startsWith("IPC_CHANNEL_EVENT ") ||
    line.startsWith("IPC_CHANNEL_SUMMARY ") ||
    line.startsWith("IPC_CONFORMANCE_SUMMARY "));
}
