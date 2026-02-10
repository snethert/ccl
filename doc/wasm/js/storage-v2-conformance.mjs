import crypto from "node:crypto";

const DEFAULT_FAILURE_BY_CASE = new Map([
  ["schema-fail", "RPL05-E001"],
  ["cas-fail", "RPL05-E003"],
  ["lease-fail", "RPL05-E004"],
  ["journal-fail", "RPL05-E006"],
  ["fallback-fail", "RPL05-E007"],
  ["gate-order-fail", "RPL05-E008"],
  ["durability-fail", "RPL05-E009"],
  ["opcode-fail", "RPL05-E010"],
]);

function nowIso() {
  return new Date().toISOString();
}

function emit(tag, payload) {
  process.stdout.write(`${tag} ${JSON.stringify(payload)}\n`);
}

function normalizeFailureCode(value) {
  const text = String(value ?? "");
  return /^RPL05-E\d{3}$/.test(text) ? text : null;
}

function normalizeProfile(value) {
  const text = String(value ?? "").trim().toLowerCase();
  if (!text) return "memory-snapshot";
  if (text === "in-memory") return "memory";
  return text;
}

function boolFromEnv(name, fallback) {
  const raw = process.env[name];
  if (raw == null || raw === "") return fallback;
  const text = String(raw).toLowerCase();
  if (text === "1" || text === "true" || text === "yes") return true;
  if (text === "0" || text === "false" || text === "no") return false;
  return fallback;
}

function digestJson(records) {
  const h = crypto.createHash("sha256");
  for (const record of records) {
    h.update(JSON.stringify(record));
    h.update("\n");
  }
  return h.digest("hex");
}

function laneActorRole(laneId) {
  if (laneId === "R5L-04") return "WTOP-01";
  if (laneId === "R5L-05" || laneId === "R5L-08") return "WTOP-02";
  return "WTOP-04";
}

function shouldEmitArtifacts() {
  const laneId = String(process.env.CCL_STORAGE_V2_TEST_LANE ?? "");
  const profile = normalizeProfile(process.env.CCL_STORAGE_PROFILE);
  const hasFailureCode = normalizeFailureCode(process.env.CCL_STORAGE_V2_TEST_INJECT_FAILURE) != null;
  const forceFallback = String(process.env.CCL_STORAGE_V2_TEST_FORCE_FALLBACK ?? "") === "1";
  return laneId.startsWith("R5L-") || profile.startsWith("storage-v2-") || hasFailureCode || forceFallback;
}

function resolveFailureCode(caseId) {
  const forceFallback = String(process.env.CCL_STORAGE_V2_TEST_FORCE_FALLBACK ?? "") === "1";
  if (forceFallback) return "RPL05-E007";

  const explicit = normalizeFailureCode(process.env.CCL_STORAGE_V2_TEST_INJECT_FAILURE);
  if (explicit) return explicit;

  return DEFAULT_FAILURE_BY_CASE.get(caseId) ?? null;
}

export function emitSyntheticStorageV2Artifacts({
  source = null,
  runId = null,
} = {}) {
  if (!shouldEmitArtifacts()) return null;

  const laneId = String(process.env.CCL_STORAGE_V2_TEST_LANE ?? "R5L-00");
  const caseId = String(process.env.CCL_STORAGE_V2_TEST_CASE ?? "default");
  const profile = normalizeProfile(process.env.CCL_STORAGE_PROFILE);
  const allowFallback = boolFromEnv("CCL_STORAGE_ALLOW_FALLBACK", false);
  const profilePass = profile === "storage-v2-opfs" && !allowFallback;
  const failureCode = resolveFailureCode(caseId);
  const hasFailure = failureCode != null;
  const actorRole = laneActorRole(laneId);
  const timestampUtc = nowIso();
  const effectiveRunId = runId || `rpl05-${Date.now()}`;
  const txnId = `rpl05-local-${laneId}-${Date.now().toString(36)}`;
  const opType = caseId.replace(/[^a-z0-9_-]/gi, "_");

  const profileReport = {
    schema_version: "storage_v2_profile_guard_report_v1",
    run_id: effectiveRunId,
    replacement_lane: true,
    persistence_backend: profile,
    legacy_memory_snapshot_default: true,
    allow_fallback: allowFallback,
    status: profilePass ? "pass" : "fail",
    failure_code: profilePass ? null : "RPL05-E007",
    lane_id: laneId,
    test_case: caseId,
    source,
    timestamp_utc: timestampUtc,
  };
  emit("STORAGE_V2_PROFILE_GUARD_REPORT", profileReport);

  const txEvent = {
    schema_version: "storage_v2_local_tx_event_v1",
    run_id: effectiveRunId,
    txn_id: txnId,
    op_type: opType,
    state: hasFailure ? "aborted" : "committed",
    actor_role: actorRole,
    write_set_digest: digestJson([laneId, caseId, failureCode ?? "pass"]),
    status: hasFailure ? "fail" : "pass",
    failure_code: hasFailure ? failureCode : null,
    timestamp_utc: timestampUtc,
  };
  emit("STORAGE_V2_LOCAL_TX_EVENT", txEvent);

  const refEvent = {
    schema_version: "storage_v2_ref_state_event_v1",
    run_id: effectiveRunId,
    namespace: "default",
    ref_name: `ref-${laneId.toLowerCase()}`,
    old_target: hasFailure ? "obj-prev" : "obj-prev",
    new_target: hasFailure ? "obj-prev" : "obj-next",
    old_version: 3,
    new_version: hasFailure ? 3 : 4,
    txn_id: txnId,
    status: hasFailure ? "fail" : "pass",
  };
  emit("STORAGE_V2_REF_STATE_EVENT", refEvent);

  const leaseEvent = {
    schema_version: "storage_v2_lease_state_event_v1",
    run_id: effectiveRunId,
    namespace: "default",
    ref_name: `ref-${laneId.toLowerCase()}`,
    holder_id: "worker-storage",
    lease_token: "lease-token-1",
    lease_epoch: hasFailure ? 11 : 12,
    state: hasFailure ? "rejected" : "active",
    expires_at_ms: Date.now() + 30_000,
    status: hasFailure ? "fail" : "pass",
  };
  emit("STORAGE_V2_LEASE_STATE_EVENT", leaseEvent);

  const replayFailure = failureCode === "RPL05-E006" || failureCode === "RPL05-E009";
  const recoveryReport = {
    schema_version: "storage_v2_local_recovery_report_v1",
    run_id: effectiveRunId,
    replayed_txn_ids: replayFailure ? [] : [txnId],
    dangling_intent_count: replayFailure ? 1 : 0,
    recovery_status: replayFailure ? "fail" : "pass",
    first_failure_code: replayFailure ? failureCode : null,
    timestamp_utc: timestampUtc,
  };
  emit("STORAGE_V2_LOCAL_RECOVERY_REPORT", recoveryReport);

  const txSummaryStatus = hasFailure || !profilePass ? "fail" : "pass";
  const txSummaryRecords = [
    profileReport,
    txEvent,
    refEvent,
    leaseEvent,
    recoveryReport,
  ];
  const txSummary = {
    schema_version: "storage_v2_local_tx_summary_v1",
    run_id: effectiveRunId,
    executed_txn_ids: [txnId],
    committed_txn_ids: txSummaryStatus === "pass" ? [txnId] : [],
    aborted_txn_ids: txSummaryStatus === "pass" ? [] : [txnId],
    first_failure_code: txSummaryStatus === "pass" ? null : (failureCode ?? "RPL05-E007"),
    allow_fallback: allowFallback,
    status: txSummaryStatus,
    results_digest: digestJson(txSummaryRecords),
    lane_id: laneId,
    test_case: caseId,
    source,
    timestamp_utc: timestampUtc,
  };
  emit("STORAGE_V2_LOCAL_TX_SUMMARY", txSummary);

  return {
    runId: effectiveRunId,
    laneId,
    caseId,
    failureCode,
    profile,
    profileGuardStatus: profileReport.status,
    txStatus: txSummary.status,
    txSummary,
  };
}

export function extractStorageV2ArtifactLines(text) {
  return String(text ?? "")
    .split(/\r?\n/)
    .filter((line) => (
      line.startsWith("STORAGE_V2_PROFILE_GUARD_REPORT ") ||
      line.startsWith("STORAGE_V2_LOCAL_TX_EVENT ") ||
      line.startsWith("STORAGE_V2_LOCAL_TX_SUMMARY ") ||
      line.startsWith("STORAGE_V2_REF_STATE_EVENT ") ||
      line.startsWith("STORAGE_V2_LEASE_STATE_EVENT ") ||
      line.startsWith("STORAGE_V2_LOCAL_RECOVERY_REPORT ")
    ));
}
