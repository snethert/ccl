import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const DEFAULT_FAILURE_BY_CASE = new Map([
  ["schema-fail", "RPL06-E001"],
  ["cas-fail", "RPL06-E003"],
  ["lease-fail", "RPL06-E004"],
  ["merge-fail", "RPL06-E006"],
  ["fallback-fail", "RPL06-E007"],
  ["gate-order-fail", "RPL06-E008"],
  ["rollback-fail", "RPL06-E009"],
  ["opcode-fail", "RPL06-E010"],
]);

function nowIso() {
  return new Date().toISOString();
}

function emit(tag, payload) {
  process.stdout.write(`${tag} ${JSON.stringify(payload)}\n`);
}

function normalizeFailureCode(value) {
  const text = String(value ?? "");
  return /^RPL06-E\d{3}$/.test(text) ? text : null;
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

function stableToken(seed, prefix, width = 12) {
  const hex = crypto.createHash("sha256").update(String(seed)).digest("hex");
  return `${prefix}-${hex.slice(0, width)}`;
}

function resolveTimestamp() {
  const raw = String(process.env.CCL_STORAGE_V2_SYNC_TIMESTAMP_UTC ?? "").trim();
  if (!raw) return nowIso();
  const ms = Date.parse(raw);
  if (Number.isNaN(ms)) return nowIso();
  return new Date(ms).toISOString();
}

function shouldEmitArtifacts() {
  const laneId = String(process.env.CCL_STORAGE_V2_SYNC_LANE ?? "");
  const profile = normalizeProfile(process.env.CCL_STORAGE_PROFILE);
  const hasFailureCode = normalizeFailureCode(process.env.CCL_STORAGE_V2_SYNC_INJECT_FAILURE) != null;
  const forceFallback = String(process.env.CCL_STORAGE_V2_SYNC_FORCE_FALLBACK ?? "") === "1";
  return laneId.startsWith("R6L-") || profile.startsWith("storage-v2-") || hasFailureCode || forceFallback;
}

function resolveFailureCode(caseId) {
  const forceFallback = String(process.env.CCL_STORAGE_V2_SYNC_FORCE_FALLBACK ?? "") === "1";
  if (forceFallback) return "RPL06-E007";

  const explicit = normalizeFailureCode(process.env.CCL_STORAGE_V2_SYNC_INJECT_FAILURE);
  if (explicit) return explicit;

  return DEFAULT_FAILURE_BY_CASE.get(caseId) ?? null;
}

function conflictStatusForFailure(failureCode) {
  if (!failureCode) return "pass";
  if (failureCode === "RPL06-E003" || failureCode === "RPL06-E005") return "fail";
  return "pass";
}

function mergeStatusForFailure(failureCode) {
  if (!failureCode) return "pass";
  if (failureCode === "RPL06-E006") return "fail";
  return "pass";
}

export function emitSyntheticStorageV2SyncArtifacts({
  source = null,
  runId = null,
} = {}) {
  if (!shouldEmitArtifacts()) return null;

  const laneId = String(process.env.CCL_STORAGE_V2_SYNC_LANE ?? "R6L-00");
  const caseId = String(process.env.CCL_STORAGE_V2_SYNC_CASE ?? "default");
  const profile = normalizeProfile(process.env.CCL_STORAGE_PROFILE);
  const allowFallback = boolFromEnv("CCL_STORAGE_ALLOW_FALLBACK", false);
  const profilePass = profile === "storage-v2-opfs" && !allowFallback;
  const failureCode = resolveFailureCode(caseId);
  const hasFailure = failureCode != null || !profilePass;
  const timestampUtc = resolveTimestamp();
  const runIdFromEnv = String(process.env.CCL_STORAGE_V2_SYNC_RUN_ID ?? "").trim();
  const effectiveRunId = runId || runIdFromEnv || `rpl06-${Date.now()}`;
  const deterministicSeed = `${laneId}|${caseId}|${failureCode ?? "none"}|${profile}|${allowFallback ? "1" : "0"}`;
  const eventId = stableToken(`${deterministicSeed}|event`, "evt");
  const conflictId = stableToken(`${deterministicSeed}|conflict`, "conflict");
  const candidateId = stableToken(`${deterministicSeed}|candidate`, "candidate");
  const opType = caseId.replace(/[^a-z0-9_-]/gi, "_");
  const candidateDigest = digestJson([{
    lane_id: laneId,
    case_id: caseId,
    failure_code: failureCode,
    strategy: "three-way-merge-v1",
  }]);

  const syncEvent = {
    schema_version: "storage_v2_sync_event_v1",
    run_id: effectiveRunId,
    lane_id: laneId,
    case_id: caseId,
    event_id: eventId,
    op_type: opType,
    status: hasFailure ? "fail" : "pass",
    failure_code: hasFailure ? (failureCode ?? "RPL06-E007") : null,
    timestamp_utc: timestampUtc,
    source,
  };
  emit("STORAGE_V2_SYNC_EVENT", syncEvent);

  const conflictEvent = {
    schema_version: "storage_v2_sync_conflict_event_v1",
    run_id: effectiveRunId,
    conflict_id: conflictId,
    namespace: "default",
    ref_name: `ref-${laneId.toLowerCase()}`,
    client_state: { version: 5, target: "obj-local" },
    remote_state: { version: 6, target: "obj-remote" },
    status: conflictStatusForFailure(failureCode),
    failure_code: failureCode === "RPL06-E003" ? failureCode : null,
    detected_at_utc: timestampUtc,
  };
  emit("STORAGE_V2_SYNC_CONFLICT_EVENT", conflictEvent);

  const candidateEvent = {
    schema_version: "storage_v2_merge_candidate_event_v1",
    run_id: effectiveRunId,
    candidate_id: candidateId,
    conflict_id: conflictId,
    strategy: "three-way-merge-v1",
    status: failureCode === "RPL06-E005" ? "fail" : "pass",
    failure_code: failureCode === "RPL06-E005" ? failureCode : null,
    candidate_digest: candidateDigest,
    timestamp_utc: timestampUtc,
  };
  emit("STORAGE_V2_MERGE_CANDIDATE_EVENT", candidateEvent);

  const finalizationEvent = {
    schema_version: "storage_v2_merge_finalization_event_v1",
    run_id: effectiveRunId,
    candidate_id: candidateId,
    final_object_id: "obj-final",
    final_ref_version: failureCode === "RPL06-E006" ? 6 : 7,
    status: mergeStatusForFailure(failureCode),
    failure_code: failureCode === "RPL06-E006" ? failureCode : null,
    finalized_at_utc: timestampUtc,
  };
  emit("STORAGE_V2_MERGE_FINALIZATION_EVENT", finalizationEvent);

  const summaryRecords = [{
    schema_version: syncEvent.schema_version,
    lane_id: laneId,
    case_id: caseId,
    op_type: syncEvent.op_type,
    event_id: eventId,
    status: syncEvent.status,
    failure_code: syncEvent.failure_code,
  }, {
    schema_version: conflictEvent.schema_version,
    conflict_id: conflictId,
    namespace: conflictEvent.namespace,
    ref_name: conflictEvent.ref_name,
    client_state: conflictEvent.client_state,
    remote_state: conflictEvent.remote_state,
    status: conflictEvent.status,
    failure_code: conflictEvent.failure_code,
  }, {
    schema_version: candidateEvent.schema_version,
    candidate_id: candidateId,
    conflict_id: conflictId,
    strategy: candidateEvent.strategy,
    status: candidateEvent.status,
    failure_code: candidateEvent.failure_code,
    candidate_digest: candidateDigest,
  }, {
    schema_version: finalizationEvent.schema_version,
    candidate_id: candidateId,
    final_object_id: finalizationEvent.final_object_id,
    final_ref_version: finalizationEvent.final_ref_version,
    status: finalizationEvent.status,
    failure_code: finalizationEvent.failure_code,
  }];
  const summary = {
    schema_version: "storage_v2_sync_summary_v1",
    run_id: effectiveRunId,
    lane_id: laneId,
    case_id: caseId,
    executed_ops: [opType],
    first_failure_code: hasFailure ? (failureCode ?? "RPL06-E007") : null,
    allow_fallback: allowFallback,
    status: hasFailure ? "fail" : "pass",
    results_digest: digestJson(summaryRecords),
    timestamp_utc: timestampUtc,
    source,
  };
  emit("STORAGE_V2_SYNC_SUMMARY", summary);

  return {
    runId: effectiveRunId,
    laneId,
    caseId,
    failureCode: summary.first_failure_code,
    summary,
  };
}

export function extractStorageV2SyncArtifactLines(text) {
  return String(text ?? "")
    .split(/\r?\n/)
    .filter((line) => (
      line.startsWith("STORAGE_V2_SYNC_EVENT ") ||
      line.startsWith("STORAGE_V2_SYNC_CONFLICT_EVENT ") ||
      line.startsWith("STORAGE_V2_MERGE_CANDIDATE_EVENT ") ||
      line.startsWith("STORAGE_V2_MERGE_FINALIZATION_EVENT ") ||
      line.startsWith("STORAGE_V2_SYNC_SUMMARY ")
    ));
}

function isMainModule() {
  if (!process.argv[1]) return false;
  return fileURLToPath(import.meta.url) === process.argv[1];
}

if (isMainModule()) {
  const result = emitSyntheticStorageV2SyncArtifacts({
    source: "doc/wasm/js/storage-v2-sync-conformance.mjs",
  });
  if (!result) {
    process.exit(0);
  }
  process.exit(result.summary.status === "pass" ? 0 : 2);
}
