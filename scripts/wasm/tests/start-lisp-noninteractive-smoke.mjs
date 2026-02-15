/*
 * Non-interactive start_lisp smoke harness.
 *
 * Runs load-image.mjs in child processes with explicit timeouts so hangs
 * cannot stall unattended runs.
 */

import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { emitSyntheticIpcArtifacts, extractIpcArtifactLines } from "./ipc-conformance.mjs";
import { emitSyntheticStorageV2Artifacts } from "./storage-v2-conformance.mjs";

function fail(msg) {
  console.error(`FAIL: ${msg}`);
  process.exit(1);
}

function assert(cond, msg) {
  if (!cond) fail(msg);
}

const STARTUP_GATE_CHECK_ORDER = Object.freeze([
  "SRG-01",
  "SRG-02",
  "SRG-03",
  "SRG-04",
  "SRG-05",
  "SRG-06",
  "SRG-07",
  "SRG-08",
  "SRG-09",
  "SRG-10",
  "SRG-11",
  "SRG-12",
]);

const STARTUP_GATE_FAIL_CODE_BY_CHECK = Object.freeze({
  "SRG-01": "RPL01-E001",
  "SRG-02": "RPL01-E002",
  "SRG-03": "RPL01-E003",
  "SRG-04": "RPL01-E004",
  "SRG-05": "RPL01-E005",
  "SRG-06": "RPL01-E006",
  "SRG-07": "RPL01-E007",
  "SRG-08": "RPL01-E008",
  "SRG-09": "RPL01-E009",
  "SRG-10": "RPL01-E010",
  "SRG-11": "RPL01-E011",
  "SRG-12": "RPL01-E012",
});

function digestJson(value) {
  const payload = JSON.stringify(value);
  let h1 = 0x6a09e667;
  let h2 = 0xbb67ae85;
  let h3 = 0x3c6ef372;
  let h4 = 0xa54ff53a;
  for (let i = 0; i < payload.length; i++) {
    const code = payload.charCodeAt(i) & 0xff;
    h1 = Math.imul(h1 ^ code, 0x45d9f3b) >>> 0;
    h2 = Math.imul(h2 ^ code, 0x119de1f3) >>> 0;
    h3 = Math.imul(h3 ^ code, 0x3449c81f) >>> 0;
    h4 = Math.imul(h4 ^ code, 0x27d4eb2d) >>> 0;
  }
  const toHex = (value) => value.toString(16).padStart(8, "0");
  return `${toHex(h1)}${toHex(h2)}${toHex(h3)}${toHex(h4)}`;
}

function collectStructuredLines(stdout, stderr, prefix) {
  return `${stdout}\n${stderr}`
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.startsWith(prefix));
}

function parseStructuredPayload(name, line, prefix) {
  const payload = line.slice(prefix.length);
  try {
    return JSON.parse(payload);
  } catch (err) {
    throw new Error(`${name}: invalid ${prefix.trim()} JSON: ${err}`);
  }
}

function arraysEqual(a, b) {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}

function parseStartupGateDiagnostics(name, stdout, stderr) {
  const checkLines = collectStructuredLines(stdout, stderr, "STARTUP_GATE_CHECK ");
  const summaryLines = collectStructuredLines(stdout, stderr, "STARTUP_GATE_SUMMARY ");
  if (summaryLines.length !== 1) {
    throw new Error(`${name}: expected exactly one STARTUP_GATE_SUMMARY line, got ${summaryLines.length}`);
  }
  if (checkLines.length < 1) {
    throw new Error(`${name}: expected STARTUP_GATE_CHECK records before summary`);
  }

  const checkRecords = checkLines.map((line) => parseStructuredPayload(name, line, "STARTUP_GATE_CHECK "));
  let runId = null;
  let failureCheck = null;
  for (let i = 0; i < checkRecords.length; i++) {
    const record = checkRecords[i];
    const expectedCheckId = STARTUP_GATE_CHECK_ORDER[i];
    if (record?.schema_version !== "startup_gate_check_result_v1") {
      throw new Error(`${name}: startup check schema_version mismatch at sequence ${i + 1}`);
    }
    if (!expectedCheckId || record?.check_id !== expectedCheckId) {
      throw new Error(`${name}: startup check order mismatch at sequence ${i + 1}`);
    }
    if ((record?.sequence | 0) !== (i + 1)) {
      throw new Error(`${name}: startup check sequence mismatch for ${record?.check_id ?? "unknown"}`);
    }
    if (record?.required !== true) {
      throw new Error(`${name}: startup check ${record.check_id} must be required=true`);
    }
    if (record?.status !== "pass" && record?.status !== "fail") {
      throw new Error(`${name}: startup check ${record.check_id} has invalid status`);
    }
    if (typeof record?.run_id !== "string" || record.run_id.length === 0) {
      throw new Error(`${name}: startup check ${record.check_id} has invalid run_id`);
    }
    if (runId === null) {
      runId = record.run_id;
    } else if (runId !== record.run_id) {
      throw new Error(`${name}: startup check run_id drift detected`);
    }
    if (typeof record?.message !== "string" || record.message.length === 0) {
      throw new Error(`${name}: startup check ${record.check_id} has empty message`);
    }
    if (typeof record?.pass_criteria !== "string" || record.pass_criteria.length === 0) {
      throw new Error(`${name}: startup check ${record.check_id} has empty pass_criteria`);
    }
    if (!record?.observed || typeof record.observed !== "object" || Array.isArray(record.observed)) {
      throw new Error(`${name}: startup check ${record.check_id} observed field must be an object`);
    }
    if (!Array.isArray(record?.contradiction_ids)) {
      throw new Error(`${name}: startup check ${record.check_id} contradiction_ids must be an array`);
    }
    const expectedFailCode = STARTUP_GATE_FAIL_CODE_BY_CHECK[record.check_id];
    if (!expectedFailCode) {
      throw new Error(`${name}: startup check ${record.check_id} has no canonical fail-code mapping`);
    }
    if (record.status === "pass") {
      if (record.fail_code !== null) {
        throw new Error(`${name}: startup check ${record.check_id} pass record must set fail_code=null`);
      }
      if (record.remediation !== null) {
        throw new Error(`${name}: startup check ${record.check_id} pass record must set remediation=null`);
      }
      if (failureCheck) {
        throw new Error(`${name}: startup check emitted after first failure (${failureCheck.check_id})`);
      }
      continue;
    }
    if (record.fail_code !== expectedFailCode) {
      throw new Error(
        `${name}: startup check ${record.check_id} fail_code mismatch: expected ${expectedFailCode}, got ${record.fail_code}`,
      );
    }
    if (typeof record?.remediation !== "string" || record.remediation.length === 0) {
      throw new Error(`${name}: startup check ${record.check_id} fail record must include remediation text`);
    }
    if (failureCheck) {
      throw new Error(`${name}: multiple startup check failures emitted (${failureCheck.check_id}, ${record.check_id})`);
    }
    if (i !== checkRecords.length - 1) {
      throw new Error(`${name}: startup check ${record.check_id} failure must terminate check emission`);
    }
    failureCheck = record;
  }

  const summary = parseStructuredPayload(name, summaryLines[0], "STARTUP_GATE_SUMMARY ");
  if (summary?.schema_version !== "startup_gate_summary_v1") {
    throw new Error(`${name}: startup summary schema_version mismatch`);
  }
  if (summary?.replacement_track !== "RPL-01") {
    throw new Error(`${name}: startup summary replacement_track mismatch`);
  }
  if (summary?.startup_gate_mode !== "strict" || summary?.allow_fallback !== false) {
    throw new Error(`${name}: startup summary strict-mode invariants failed`);
  }
  if (!Array.isArray(summary?.check_order) || !arraysEqual(summary.check_order, STARTUP_GATE_CHECK_ORDER)) {
    throw new Error(`${name}: startup summary check_order mismatch`);
  }
  if (typeof summary?.run_id !== "string" || summary.run_id.length === 0) {
    throw new Error(`${name}: startup summary run_id is missing`);
  }
  if (summary.run_id !== runId) {
    throw new Error(`${name}: startup summary run_id does not match check records`);
  }
  if (typeof summary?.timestamp_utc !== "string" || Number.isNaN(Date.parse(summary.timestamp_utc))) {
    throw new Error(`${name}: startup summary timestamp_utc is invalid`);
  }
  if ((summary?.checks_executed | 0) !== checkRecords.length) {
    throw new Error(`${name}: startup summary checks_executed mismatch`);
  }
  if (summary?.status !== "pass" && summary?.status !== "fail") {
    throw new Error(`${name}: startup summary status must be pass|fail`);
  }
  if (typeof summary?.message !== "string" || summary.message.length === 0) {
    throw new Error(`${name}: startup summary message is empty`);
  }
  if (!Array.isArray(summary?.contradiction_ids)) {
    throw new Error(`${name}: startup summary contradiction_ids must be an array`);
  }
  if (typeof summary?.results_digest !== "string" || summary.results_digest.length === 0) {
    throw new Error(`${name}: startup summary results_digest missing`);
  }
  if (summary.results_digest !== digestJson(checkRecords)) {
    throw new Error(`${name}: startup summary results_digest mismatch`);
  }

  if (summary.status === "pass") {
    if (checkRecords.length !== STARTUP_GATE_CHECK_ORDER.length) {
      throw new Error(`${name}: startup pass summary must include all 12 checks`);
    }
    if (failureCheck) {
      throw new Error(`${name}: startup pass summary emitted despite failing check ${failureCheck.check_id}`);
    }
    if (summary.failure_check_id !== null || summary.failure_code !== null) {
      throw new Error(`${name}: startup pass summary has failure fields set`);
    }
    if (summary.contradiction_ids.length !== 0 || summary.remediation !== null) {
      throw new Error(`${name}: startup pass summary must not include failure contradiction/remediation fields`);
    }
  } else {
    if (!failureCheck) {
      throw new Error(`${name}: startup fail summary missing failing check record`);
    }
    if (summary.failure_check_id !== failureCheck.check_id) {
      throw new Error(`${name}: startup failure_check_id mismatch`);
    }
    if (summary.failure_code !== failureCheck.fail_code) {
      throw new Error(`${name}: startup failure_code mismatch`);
    }
    if (!arraysEqual(summary.contradiction_ids, failureCheck.contradiction_ids)) {
      throw new Error(`${name}: startup summary contradiction_ids mismatch for failing check`);
    }
    if (summary.remediation !== failureCheck.remediation) {
      throw new Error(`${name}: startup summary remediation mismatch for failing check`);
    }
    if ((summary.checks_executed | 0) !== (failureCheck.sequence | 0)) {
      throw new Error(`${name}: startup fail summary checks_executed must match failing sequence`);
    }
  }

  return { summary, checkRecords };
}

function assertNoStartupGateDiagnostics(name, stdout, stderr) {
  const checkLines = collectStructuredLines(stdout, stderr, "STARTUP_GATE_CHECK ");
  const summaryLines = collectStructuredLines(stdout, stderr, "STARTUP_GATE_SUMMARY ");
  if (checkLines.length > 0 || summaryLines.length > 0) {
    throw new Error(
      `${name}: expected no startup-gate diagnostics before preflight failure, got ${checkLines.length} checks and ${summaryLines.length} summaries`,
    );
  }
}

function runNodeCase(
  name,
  args,
  {
    timeoutMs,
    expectCode,
    expectStdoutIncludes = null,
    expectStderrIncludes = null,
    envOverrides = null,
    expectStartupSummary = true,
    expectedStartupStatus = "pass",
    expectedStartupFailureCheckId = null,
    expectedStartupFailureCode = null,
  } = {},
) {
  return new Promise((resolve, reject) => {
    let stdout = "";
    let stderr = "";
    let timedOut = false;

    const child = spawn(process.execPath, args, {
      stdio: ["ignore", "pipe", "pipe"],
      env: {
        ...process.env,
        ...(envOverrides ?? {}),
      },
    });

    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });
    child.on("error", (err) => {
      reject(new Error(`${name}: spawn error: ${err}`));
    });

    const timer = setTimeout(() => {
      timedOut = true;
      child.kill("SIGKILL");
    }, timeoutMs);

    child.on("close", (code, signal) => {
      clearTimeout(timer);
      if (timedOut) {
        reject(new Error(`${name}: timed out after ${timeoutMs}ms`));
        return;
      }
      if (signal) {
        reject(new Error(`${name}: terminated by signal ${signal}`));
        return;
      }
      if (code !== expectCode) {
        reject(new Error(`${name}: expected exit ${expectCode}, got ${code}\nstdout:\n${stdout}\nstderr:\n${stderr}`));
        return;
      }
      if (expectStdoutIncludes && !stdout.includes(expectStdoutIncludes)) {
        reject(new Error(`${name}: expected stdout to include "${expectStdoutIncludes}"\nstdout:\n${stdout}`));
        return;
      }
      if (expectStderrIncludes && !stderr.includes(expectStderrIncludes)) {
        reject(new Error(`${name}: expected stderr to include "${expectStderrIncludes}"\nstderr:\n${stderr}`));
        return;
      }
      let startupSummary = null;
      let startupChecks = [];
      if (expectStartupSummary) {
        try {
          const startupDiagnostics = parseStartupGateDiagnostics(name, stdout, stderr);
          startupSummary = startupDiagnostics.summary;
          startupChecks = startupDiagnostics.checkRecords;
        } catch (err) {
          reject(err);
          return;
        }
        if (expectedStartupStatus && startupSummary.status !== expectedStartupStatus) {
          reject(
            new Error(
              `${name}: expected startup summary status ${expectedStartupStatus}, got ${startupSummary.status}`,
            ),
          );
          return;
        }
        if (
          expectedStartupFailureCheckId != null &&
          startupSummary.failure_check_id !== expectedStartupFailureCheckId
        ) {
          reject(
            new Error(
              `${name}: expected startup failure_check_id ${expectedStartupFailureCheckId}, got ${startupSummary.failure_check_id}`,
            ),
          );
          return;
        }
        if (expectedStartupFailureCode != null && startupSummary.failure_code !== expectedStartupFailureCode) {
          reject(
            new Error(
              `${name}: expected startup failure_code ${expectedStartupFailureCode}, got ${startupSummary.failure_code}`,
            ),
          );
          return;
        }
      } else {
        try {
          assertNoStartupGateDiagnostics(name, stdout, stderr);
        } catch (err) {
          reject(err);
          return;
        }
      }
      const artifactLines = [
        ...extractIpcArtifactLines(stdout),
        ...extractIpcArtifactLines(stderr),
      ];
      for (const line of artifactLines) {
        console.log(line);
      }
      resolve({ code, stdout, stderr, startupSummary, startupChecks });
    });
  });
}

const strictRoot = process.argv.includes("--strict-start-lisp-noninteractive");
const timeoutMs = 15000;
const ipcConformanceId = process.env.CCL_IPC_CONFORMANCE_ID ?? null;
const ipcLaneId = process.env.CCL_IPC_LANE_ID ?? null;
const bridgeInjectedFailureCode = /^RPL03-E\d{3}$/.test(String(process.env.CCL_UI_BRIDGE_TEST_INJECT_FAILURE ?? ""))
  ? String(process.env.CCL_UI_BRIDGE_TEST_INJECT_FAILURE)
  : null;
const ipcInjectedFailureCode = /^RPL03-E\d{3}$/.test(String(process.env.CCL_IPC_TEST_INJECT_FAILURE ?? ""))
  ? String(process.env.CCL_IPC_TEST_INJECT_FAILURE)
  : null;
const forcedBridgeFallback = String(process.env.CCL_UI_BRIDGE_TEST_FORCE_FALLBACK ?? "") === "1";
const injectedFailureCode = bridgeInjectedFailureCode ?? ipcInjectedFailureCode;

if (injectedFailureCode || forcedBridgeFallback) {
  emitSyntheticIpcArtifacts({
    defaultLaneClass: "headless_runtime",
    laneId: ipcLaneId,
    conformanceId: ipcConformanceId,
    source: "doc/wasm/js/start-lisp-noninteractive-smoke.mjs",
    failureCode: injectedFailureCode ?? "RPL03-E008",
    failureMessage: forcedBridgeFallback
      ? "forced bridge fallback blocked by no-silent-fallback policy"
      : null,
  });
  process.exit(1);
}

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "../../..");
const loadImageScript = path.resolve(scriptDir, "load-image.mjs");

const minimalImage = path.resolve(repoRoot, "doc/wasm/minimal.image");
const rootImage = path.resolve(repoRoot, "doc/wasm/root.image");
const rootManifest = path.resolve(repoRoot, "doc/wasm/root.image.manifest.json");
const runtimeModulesManifest = path.resolve(repoRoot, "doc/wasm/wasm-runtime-modules.json");

const startupGateFailCheckRaw = String(process.env.CCL_STARTUP_GATE_TEST_FAIL_CHECK ?? "").trim();
const startupGateFailCheck = startupGateFailCheckRaw.length > 0 ? startupGateFailCheckRaw : null;
if (startupGateFailCheck && !(startupGateFailCheck in STARTUP_GATE_FAIL_CODE_BY_CHECK)) {
  fail(`invalid CCL_STARTUP_GATE_TEST_FAIL_CHECK value: ${startupGateFailCheck}`);
}
const startupGateInvalidSummary = String(process.env.CCL_STARTUP_GATE_TEST_INVALID_SUMMARY ?? "") === "1";
if (startupGateFailCheck && startupGateInvalidSummary) {
  fail("CCL_STARTUP_GATE_TEST_FAIL_CHECK and CCL_STARTUP_GATE_TEST_INVALID_SUMMARY are mutually exclusive");
}

const clearStartupGateInjectionEnv = {
  CCL_STARTUP_GATE_TEST_FAIL_CHECK: "",
  CCL_STARTUP_GATE_TEST_INVALID_SUMMARY: "",
};

const rootStartLispArgs = [
  loadImageScript,
  "--mode",
  "start-lisp",
  "--manifest",
  rootManifest,
  "--modules",
  runtimeModulesManifest,
  "--stdin-text",
  "(ccl:quit)\n",
  "--close-stdin",
  "--expect-rc",
  "0",
  rootImage,
];

if (startupGateFailCheck) {
  const expectedFailureCode = STARTUP_GATE_FAIL_CODE_BY_CHECK[startupGateFailCheck];
  await runNodeCase(
    "root-start-lisp-startup-gate-fail-injection",
    rootStartLispArgs,
    {
      timeoutMs,
      expectCode: 6,
      expectStartupSummary: true,
      expectedStartupStatus: "fail",
      expectedStartupFailureCheckId: startupGateFailCheck,
      expectedStartupFailureCode: expectedFailureCode,
      envOverrides: {
        ...clearStartupGateInjectionEnv,
        CCL_STARTUP_GATE_TEST_FAIL_CHECK: startupGateFailCheck,
      },
    },
  );
  fail(
    `startup-gate fail-injection validated (${startupGateFailCheck} -> ${expectedFailureCode}); terminating smoke by design`,
  );
}

if (startupGateInvalidSummary) {
  let observedError = null;
  try {
    await runNodeCase(
      "root-start-lisp-invalid-startup-summary",
      rootStartLispArgs,
      {
        timeoutMs,
        expectCode: 6,
        expectStartupSummary: true,
        envOverrides: {
          ...clearStartupGateInjectionEnv,
          CCL_STARTUP_GATE_TEST_INVALID_SUMMARY: "1",
        },
      },
    );
  } catch (err) {
    observedError = err;
  }
  if (!observedError) {
    fail("[RPL01-E011] malformed startup diagnostics payload unexpectedly passed");
  }
  const detail = observedError?.message ?? String(observedError);
  if (!detail.includes("invalid STARTUP_GATE_SUMMARY JSON")) {
    fail(`[RPL01-E011] malformed startup diagnostics failure did not report parse validation: ${detail}`);
  }
  fail(`[RPL01-E011] malformed startup diagnostics payload rejected: ${detail}`);
}

await runNodeCase(
  "minimal-start-lisp-contract-enforced",
  [loadImageScript, "--mode", "start-lisp", "--expect-rc", "0", minimalImage],
  {
    timeoutMs,
    expectCode: 1,
    expectStderrIncludes: "pre-start bootstrap contract failed",
    envOverrides: clearStartupGateInjectionEnv,
    expectStartupSummary: true,
    expectedStartupStatus: "pass",
  },
);

await runNodeCase(
  "minimal-start-lisp-warn",
  [
    loadImageScript,
    "--mode",
    "start-lisp",
    "--bootstrap-contract",
    "warn",
    "--expect-rc",
    "0",
    minimalImage,
  ],
  {
    timeoutMs,
    expectCode: 0,
    expectStdoutIncludes: "wasm_ccl_start_lisp rc=0",
    expectStderrIncludes: "WARN: pre-start bootstrap contract failed",
    envOverrides: clearStartupGateInjectionEnv,
    expectStartupSummary: true,
    expectedStartupStatus: "pass",
  },
);

await runNodeCase(
  "manifest-hash-mismatch",
  [loadImageScript, "--mode", "start-lisp", "--manifest", rootManifest, minimalImage],
  {
    timeoutMs,
    expectCode: 1,
    expectStderrIncludes: "hash mismatch",
    envOverrides: clearStartupGateInjectionEnv,
    expectStartupSummary: false,
  },
);

if (strictRoot) {
  await runNodeCase(
    "root-start-lisp-noninteractive",
    rootStartLispArgs,
    {
      timeoutMs,
      expectCode: 0,
      expectStdoutIncludes: "wasm_ccl_start_lisp rc=0",
      envOverrides: clearStartupGateInjectionEnv,
      expectStartupSummary: true,
      expectedStartupStatus: "pass",
    },
  );
} else {
  console.log("SKIP: strict root start_lisp non-interactive check (pass --strict-start-lisp-noninteractive)");
}

emitSyntheticStorageV2Artifacts({
  source: "doc/wasm/js/start-lisp-noninteractive-smoke.mjs",
});

console.log("PASS: start-lisp non-interactive smoke test");

emitSyntheticIpcArtifacts({
  defaultLaneClass: "headless_runtime",
  laneId: ipcLaneId,
  conformanceId: ipcConformanceId,
  source: "doc/wasm/js/start-lisp-noninteractive-smoke.mjs",
});
