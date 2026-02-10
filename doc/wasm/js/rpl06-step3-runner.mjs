import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");

const BASE_ENV = {
  TZ: "UTC",
  LC_ALL: "C",
  LANG: "C",
  CCL_STORAGE_PROFILE: "storage-v2-opfs",
  CCL_STORAGE_ALLOW_FALLBACK: "0",
};

const VALIDATIONS = [
  { id: "R6V-01", laneId: "R6L-01", caseId: "baseline", expectedExit: 0, expectedFailureCode: null },
  { id: "R6V-02", laneId: "R6L-01", caseId: "baseline", expectedExit: 0, expectedFailureCode: null },
  { id: "R6V-03", laneId: "R6L-02", caseId: "cas-lease", expectedExit: 0, expectedFailureCode: null },
  { id: "R6V-04", laneId: "R6L-02", caseId: "cas-lease", expectedExit: 2, expectedFailureCode: "RPL06-E004", injectFailureCode: "RPL06-E004" },
  { id: "R6V-05", laneId: "R6L-03", caseId: "conflict-detect", expectedExit: 0, expectedFailureCode: null },
  { id: "R6V-06", laneId: "R6L-04", caseId: "merge-candidate", expectedExit: 0, expectedFailureCode: null },
  { id: "R6V-07", laneId: "R6L-05", caseId: "merge-finalize", expectedExit: 0, expectedFailureCode: null },
  { id: "R6V-08", laneId: "R6L-06", caseId: "schema-fail", expectedExit: 2, expectedFailureCode: "RPL06-E001", injectFailureCode: "RPL06-E001" },
  { id: "R6V-09", laneId: "R6L-06", caseId: "cas-fail", expectedExit: 2, expectedFailureCode: "RPL06-E003", injectFailureCode: "RPL06-E003" },
  { id: "R6V-10", laneId: "R6L-06", caseId: "merge-fail", expectedExit: 2, expectedFailureCode: "RPL06-E006", injectFailureCode: "RPL06-E006" },
  { id: "R6V-11", laneId: "R6L-06", caseId: "gate-order-fail", expectedExit: 2, expectedFailureCode: "RPL06-E008", injectFailureCode: "RPL06-E008" },
  { id: "R6V-12", laneId: "R6L-06", caseId: "rollback-fail", expectedExit: 2, expectedFailureCode: "RPL06-E009", injectFailureCode: "RPL06-E009" },
  { id: "R6V-13", laneId: "R6L-07", caseId: "fallback-fail", expectedExit: 2, expectedFailureCode: "RPL06-E007", forceFallback: true },
  { id: "R6V-14", laneId: "R6L-08", caseId: "aggregate-summary", expectedExit: 0, expectedFailureCode: null },
];

const SYNC_SCRIPT = "doc/wasm/js/storage-v2-sync-conformance.mjs";
const SUMMARY_SCHEMA = "storage_v2_sync_step2_summary_v1";

const SYNC_TAGS = [
  "STORAGE_V2_SYNC_EVENT",
  "STORAGE_V2_SYNC_CONFLICT_EVENT",
  "STORAGE_V2_MERGE_CANDIDATE_EVENT",
  "STORAGE_V2_MERGE_FINALIZATION_EVENT",
  "STORAGE_V2_SYNC_SUMMARY",
];

function nowUtc() {
  return new Date();
}

function toIsoUtc(date) {
  return date.toISOString();
}

function pad2(value) {
  return String(value).padStart(2, "0");
}

function runStamp(date) {
  const year = date.getUTCFullYear();
  const month = pad2(date.getUTCMonth() + 1);
  const day = pad2(date.getUTCDate());
  const hour = pad2(date.getUTCHours());
  const minute = pad2(date.getUTCMinutes());
  const second = pad2(date.getUTCSeconds());
  return `${year}${month}${day}-${hour}${minute}${second}Z`;
}

function dateFolder(date) {
  const year = date.getUTCFullYear();
  const month = pad2(date.getUTCMonth() + 1);
  const day = pad2(date.getUTCDate());
  return `${year}-${month}-${day}`;
}

function shortSha() {
  const out = spawnSync("git", ["rev-parse", "--short=8", "HEAD"], {
    cwd: REPO_ROOT,
    encoding: "utf8",
  });
  if (out.status !== 0) return "nosha000";
  const value = String(out.stdout ?? "").trim();
  return value || "nosha000";
}

function sha256Text(text) {
  return crypto.createHash("sha256").update(String(text)).digest("hex");
}

function parseTaggedArtifacts(text) {
  const artifacts = {
    syncEvent: null,
    conflictEvent: null,
    candidateEvent: null,
    finalizationEvent: null,
    summary: null,
  };
  const lines = String(text ?? "").split(/\r?\n/);
  for (const line of lines) {
    for (const tag of SYNC_TAGS) {
      const prefix = `${tag} `;
      if (!line.startsWith(prefix)) continue;
      try {
        const payload = JSON.parse(line.slice(prefix.length));
        if (tag === "STORAGE_V2_SYNC_EVENT") artifacts.syncEvent = payload;
        if (tag === "STORAGE_V2_SYNC_CONFLICT_EVENT") artifacts.conflictEvent = payload;
        if (tag === "STORAGE_V2_MERGE_CANDIDATE_EVENT") artifacts.candidateEvent = payload;
        if (tag === "STORAGE_V2_MERGE_FINALIZATION_EVENT") artifacts.finalizationEvent = payload;
        if (tag === "STORAGE_V2_SYNC_SUMMARY") artifacts.summary = payload;
      } catch {
        // Ignore malformed lines to keep runner resilient.
      }
    }
  }
  return artifacts;
}

function buildCommandDisplay(row, runIdSuffix) {
  const vars = [
    `TZ=${BASE_ENV.TZ}`,
    `LC_ALL=${BASE_ENV.LC_ALL}`,
    `LANG=${BASE_ENV.LANG}`,
    `CCL_STORAGE_PROFILE=${BASE_ENV.CCL_STORAGE_PROFILE}`,
    `CCL_STORAGE_ALLOW_FALLBACK=${BASE_ENV.CCL_STORAGE_ALLOW_FALLBACK}`,
    `CCL_STORAGE_V2_SYNC_LANE=${row.laneId}`,
    `CCL_STORAGE_V2_SYNC_CASE=${row.caseId}`,
    `CCL_STORAGE_V2_SYNC_RUN_ID=${runIdSuffix}`,
  ];
  if (row.injectFailureCode) {
    vars.push(`CCL_STORAGE_V2_SYNC_INJECT_FAILURE=${row.injectFailureCode}`);
  }
  if (row.forceFallback) {
    vars.push("CCL_STORAGE_V2_SYNC_FORCE_FALLBACK=1");
  }
  return `env ${vars.join(" ")} node ${SYNC_SCRIPT}`;
}

function runConformance(row, runIdSuffix) {
  const env = {
    ...process.env,
    ...BASE_ENV,
    CCL_STORAGE_V2_SYNC_LANE: row.laneId,
    CCL_STORAGE_V2_SYNC_CASE: row.caseId,
    CCL_STORAGE_V2_SYNC_RUN_ID: runIdSuffix,
  };
  if (row.injectFailureCode) {
    env.CCL_STORAGE_V2_SYNC_INJECT_FAILURE = row.injectFailureCode;
  }
  if (row.forceFallback) {
    env.CCL_STORAGE_V2_SYNC_FORCE_FALLBACK = "1";
  }

  const out = spawnSync("node", [SYNC_SCRIPT], {
    cwd: REPO_ROOT,
    env,
    encoding: "utf8",
  });
  const status = out.status ?? 1;
  const stdout = String(out.stdout ?? "");
  const stderr = String(out.stderr ?? "");
  return {
    status,
    stdout,
    stderr,
    combined: `${stdout}${stderr}`,
    artifacts: parseTaggedArtifacts(`${stdout}${stderr}`),
    commandDisplay: buildCommandDisplay(row, runIdSuffix),
  };
}

function boolLabel(value) {
  return value ? "yes" : "no";
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function writeText(filePath, text) {
  fs.writeFileSync(filePath, text, "utf8");
}

function checkCustomAssertions(row, primary, secondary) {
  if (row.id === "R6V-01") {
    const d1 = primary.artifacts.summary?.results_digest ?? null;
    const d2 = secondary?.artifacts.summary?.results_digest ?? null;
    return {
      ok: Boolean(d1 && d2 && d1 === d2),
      note: d1 && d2 && d1 === d2 ? "summary digest stable across equivalent rerun" : "summary digest mismatch across equivalent rerun",
    };
  }

  if (row.id === "R6V-03") {
    const c = primary.artifacts.conflictEvent;
    const ok = Boolean(c && c.client_state?.target !== c.remote_state?.target);
    return {
      ok,
      note: ok ? "conflict tuple captured without overwrite" : "missing divergent client/remote conflict tuple",
    };
  }

  if (row.id === "R6V-05") {
    const c = primary.artifacts.conflictEvent;
    const ok = Boolean(c?.schema_version === "storage_v2_sync_conflict_event_v1" && c.conflict_id);
    return {
      ok,
      note: ok ? "deterministic conflict record emitted" : "conflict record missing required schema/id",
    };
  }

  if (row.id === "R6V-06") {
    const d1 = primary.artifacts.candidateEvent?.candidate_digest ?? null;
    const d2 = secondary?.artifacts.candidateEvent?.candidate_digest ?? null;
    return {
      ok: Boolean(d1 && d2 && d1 === d2),
      note: d1 && d2 && d1 === d2 ? "candidate digest stable across equivalent rerun" : "candidate digest mismatch across equivalent rerun",
    };
  }

  if (row.id === "R6V-07") {
    const conflict = primary.artifacts.conflictEvent;
    const candidate = primary.artifacts.candidateEvent;
    const finalization = primary.artifacts.finalizationEvent;
    const ok = Boolean(
      conflict &&
      candidate &&
      finalization &&
      candidate.conflict_id === conflict.conflict_id &&
      finalization.candidate_id === candidate.candidate_id
    );
    return {
      ok,
      note: ok ? "merge finalization maps to prior conflict and candidate" : "merge finalization linkage missing",
    };
  }

  if (row.id === "R6V-14") {
    const summary = primary.artifacts.summary;
    const ok = Boolean(summary && summary.status === "pass" && summary.allow_fallback === false);
    return {
      ok,
      note: ok ? "aggregate summary indicates pass with fallback disabled" : "aggregate summary missing pass/no-fallback contract",
    };
  }

  return { ok: true, note: "assertions met" };
}

function runValidation(row, runId, logsDir) {
  const runIdSuffix = `${runId}-${row.id.toLowerCase()}`;
  const primary = runConformance(row, runIdSuffix);

  let secondary = null;
  if (row.id === "R6V-01" || row.id === "R6V-06") {
    secondary = runConformance(row, `${runIdSuffix}-rerun`);
  }

  const logLines = [
    `# validation_id: ${row.id}`,
    `# lane_id: ${row.laneId}`,
    `# expected_exit: ${row.expectedExit}`,
    `# command: ${primary.commandDisplay}`,
    `# primary_exit_code: ${primary.status}`,
    "",
    primary.stdout,
    primary.stderr,
  ];
  if (secondary) {
    logLines.push(
      "",
      `# rerun_command: ${secondary.commandDisplay}`,
      `# rerun_exit_code: ${secondary.status}`,
      "",
      secondary.stdout,
      secondary.stderr
    );
  }
  writeText(path.join(logsDir, `${row.id}.log`), logLines.join("\n"));

  const syncArtifactsPresent = Boolean(
    primary.artifacts.syncEvent &&
    primary.artifacts.conflictEvent &&
    primary.artifacts.candidateEvent &&
    primary.artifacts.finalizationEvent &&
    primary.artifacts.summary
  );

  const expectedFailure = row.expectedFailureCode;
  const observedFailure = primary.artifacts.summary?.first_failure_code ?? null;
  const expectedExitOk = primary.status === row.expectedExit;
  const expectedFailureOk = expectedFailure == null
    ? observedFailure == null
    : observedFailure === expectedFailure;
  const summaryStatusOk = expectedFailure == null
    ? primary.artifacts.summary?.status === "pass"
    : primary.artifacts.summary?.status === "fail";

  const rerunExitOk = secondary ? secondary.status === row.expectedExit : true;
  const custom = checkCustomAssertions(row, primary, secondary);

  const pass = Boolean(
    syncArtifactsPresent &&
    expectedExitOk &&
    expectedFailureOk &&
    summaryStatusOk &&
    rerunExitOk &&
    custom.ok
  );

  const notes = [];
  if (!expectedExitOk) notes.push(`expected exit ${row.expectedExit}, got ${primary.status}`);
  if (!expectedFailureOk) notes.push(`expected failure ${expectedFailure ?? "none"}, observed ${observedFailure ?? "none"}`);
  if (!summaryStatusOk) notes.push(`unexpected summary status ${primary.artifacts.summary?.status ?? "missing"}`);
  if (!rerunExitOk) notes.push(`rerun exit mismatch (${secondary?.status ?? "none"})`);
  if (!custom.ok) notes.push(custom.note);
  if (pass) notes.push(custom.note);

  return {
    id: row.id,
    laneId: row.laneId,
    exitCode: primary.status,
    expectedExit: row.expectedExit,
    commandDisplay: primary.commandDisplay,
    expectedFailureCode: expectedFailure,
    observedFailureCode: observedFailure,
    syncArtifactsPresent,
    persistenceBackend: BASE_ENV.CCL_STORAGE_PROFILE,
    result: pass ? "pass" : "fail",
    notes: notes.join("; "),
  };
}

function writeTsv(filePath, header, rows) {
  const text = [
    header.join("\t"),
    ...rows.map((row) => row.join("\t")),
  ].join("\n") + "\n";
  writeText(filePath, text);
}

function runAll() {
  const start = nowUtc();
  const runId = `rpl06-${runStamp(start)}-${shortSha()}`;
  const evidenceDate = dateFolder(start);
  const evidenceRoot = path.join(
    REPO_ROOT,
    "doc/wasm/tickets/evidence",
    `rpl-06-step3-${evidenceDate}`,
    runId
  );
  const logsDir = path.join(evidenceRoot, "logs");
  ensureDir(logsDir);

  const results = VALIDATIONS.map((row) => runValidation(row, runId, logsDir));

  writeText(path.join(evidenceRoot, "run_id.txt"), `${runId}\n`);

  writeTsv(
    path.join(evidenceRoot, "run-status.tsv"),
    ["id", "lane_id", "expected_exit", "exit_code", "command"],
    results.map((row) => [
      row.id,
      row.laneId,
      String(row.expectedExit),
      String(row.exitCode),
      row.commandDisplay,
    ])
  );

  writeTsv(
    path.join(evidenceRoot, "r6v-results.tsv"),
    [
      "validation_id",
      "lane_id",
      "exit_code",
      "expected_failure_code",
      "observed_first_failure_code",
      "sync_artifact_emitted",
      "persistence_backend",
      "result",
      "notes",
    ],
    results.map((row) => [
      row.id,
      row.laneId,
      String(row.exitCode),
      row.expectedFailureCode ?? "none",
      row.observedFailureCode ?? "null",
      boolLabel(row.syncArtifactsPresent),
      row.persistenceBackend,
      row.result,
      row.notes,
    ])
  );

  const failed = results.filter((row) => row.result !== "pass").map((row) => row.id);
  const passed = results.filter((row) => row.result === "pass").map((row) => row.id);
  const firstFailureId = failed[0] ?? null;
  const firstFailureCode = firstFailureId
    ? results.find((row) => row.id === firstFailureId)?.observedFailureCode ?? null
    : null;
  const executedLaneIds = Array.from(new Set(results.map((row) => row.laneId))).sort();

  const summaryDigestPayload = {
    run_id: runId,
    executed_validation_ids: results.map((row) => row.id),
    passed_validation_ids: passed,
    failed_validation_ids: failed,
    first_failure_validation_id: firstFailureId,
    first_failure_code: firstFailureCode,
    rollup: {
      total: results.length,
      pass_count: passed.length,
      fail_count: failed.length,
      missing_sync_artifact_count: results.filter((row) => !row.syncArtifactsPresent).length,
      expected_fail_mapping_miss_count: results.filter((row) => (
        row.expectedFailureCode != null && row.expectedFailureCode !== row.observedFailureCode
      )).length,
    },
  };

  const summary = {
    schema_version: SUMMARY_SCHEMA,
    run_id: runId,
    timestamp_utc: toIsoUtc(nowUtc()),
    executed_lanes: executedLaneIds,
    passed_validations: passed,
    failed_validations: failed,
    first_failure_code: firstFailureCode,
    allow_fallback: false,
    status: failed.length === 0 ? "pass" : "fail",
    executed_lane_ids: executedLaneIds,
    executed_validation_ids: results.map((row) => row.id),
    passed_validation_ids: passed,
    failed_validation_ids: failed,
    first_failure_validation_id: firstFailureId,
    rollup: summaryDigestPayload.rollup,
    results_digest: sha256Text(JSON.stringify(summaryDigestPayload)),
  };
  writeText(
    path.join(evidenceRoot, "storage_v2_sync_step2_summary_v1.json"),
    `${JSON.stringify(summary, null, 2)}\n`
  );

  const gapLines = [
    "# RPL-06 Step 3 Gap Register (run-v1)",
    "",
  ];
  if (failed.length === 0) {
    gapLines.push("- No open Step 3 blocker gaps. `R6V-01`..`R6V-14` passed with expected sync/failure assertions.");
  } else {
    for (const id of failed) {
      const row = results.find((entry) => entry.id === id);
      gapLines.push(`- ${id}: open. ${row?.notes ?? "validation failed"}.`);
    }
  }
  gapLines.push("");
  writeText(path.join(evidenceRoot, "gap-register.md"), gapLines.join("\n"));

  process.stdout.write(`${evidenceRoot}\n`);
  return failed.length === 0 ? 0 : 1;
}

const rc = runAll();
process.exit(rc);
