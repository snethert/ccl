const CHECK_ORDER = [
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
];

const CHECK_SPECS = new Map([
  [
    "SRG-01",
    {
      failCode: "RPL01-E001",
      passCriteria: "crossOriginIsolated is true.",
      failMessage: "[{code}] SRG-01 failed: cross-origin isolation is required; observed=false.",
      remediation: "Enable COOP/COEP and rerun in an isolated top-level context.",
      contradictionIds: ["C-02", "C-04", "C-05", "C-06", "C-07", "C-08", "C-13"],
      observed: { cross_origin_isolated: true },
    },
  ],
  [
    "SRG-02",
    {
      failCode: "RPL01-E002",
      passCriteria: "SharedArrayBuffer constructor exists and allocation succeeds.",
      failMessage: "[{code}] SRG-02 failed: SharedArrayBuffer unavailable in startup context.",
      remediation: "Fix isolation/policy headers and runtime flags for SharedArrayBuffer.",
      contradictionIds: ["C-01", "C-02", "C-03", "C-04", "C-05", "C-06", "C-07", "C-08", "C-09", "C-13"],
      observed: { shared_array_buffer_available: true },
    },
  ],
  [
    "SRG-03",
    {
      failCode: "RPL01-E003",
      passCriteria: "Worker Atomics wait/notify probe returns ok or timed-out.",
      failMessage: "[{code}] SRG-03 failed: Atomics wait/notify path is not usable in worker context.",
      remediation: "Move blocking waits to workers and verify Atomics policy in isolated context.",
      contradictionIds: ["C-02", "C-04", "C-06", "C-07", "C-08", "C-13"],
      observed: { atomics_wait_probe: "ok" },
    },
  ],
  [
    "SRG-04",
    {
      failCode: "RPL01-E004",
      passCriteria: "WASM shared-memory/thread probe validates and instantiates.",
      failMessage: "[{code}] SRG-04 failed: WebAssembly shared memory/thread capability missing.",
      remediation: "Use runtime versions with WASM shared-memory threads enabled.",
      contradictionIds: ["C-02", "C-03", "C-04", "C-06", "C-07", "C-08", "C-13"],
      observed: { wasm_shared_memory_threads: true },
    },
  ],
  [
    "SRG-05",
    {
      failCode: "RPL01-E005",
      passCriteria: "Required worker roles acknowledge READY before timeout.",
      failMessage: "[{code}] SRG-05 failed: required worker topology did not initialize (missing=none).",
      remediation: "Fix worker role boot wiring and READY handshakes.",
      contradictionIds: ["C-02", "C-04", "C-06", "C-07", "C-08", "C-13"],
      observed: { missing_roles: [] },
    },
  ],
  [
    "SRG-06",
    {
      failCode: "RPL01-E006",
      passCriteria: "OPFS directory handle is available in storage worker path.",
      failMessage: "[{code}] SRG-06 failed: OPFS directory handle unavailable for storage worker.",
      remediation: "Run in a secure context with worker OPFS enabled.",
      contradictionIds: ["C-10", "C-11", "C-12", "C-14"],
      observed: { opfs_available: true },
    },
  ],
  [
    "SRG-07",
    {
      failCode: "RPL01-E007",
      passCriteria: "SyncAccessHandle probe write/read/flush completes with parity.",
      failMessage: "[{code}] SRG-07 failed: SyncAccessHandle worker probe failed at startup.",
      remediation: "Enable worker SyncAccessHandle support and OPFS write permissions.",
      contradictionIds: ["C-10", "C-11", "C-12", "C-14"],
      observed: { sync_access_handle_probe: "ok" },
    },
  ],
  [
    "SRG-08",
    {
      failCode: "RPL01-E008",
      passCriteria: "Hot-path transport policy routes required classes to shared channels.",
      failMessage: "[{code}] SRG-08 failed: hot-path transport policy is not shared-memory-first.",
      remediation: "Route hot-path classes to shared-ring channels; keep copy lanes control-only.",
      contradictionIds: ["C-01", "C-03", "C-04", "C-05", "C-07", "C-08"],
      observed: { hot_path_transport: "shared_ring_v1" },
    },
  ],
  [
    "SRG-09",
    {
      failCode: "RPL01-E009",
      passCriteria: "Required UI bridge hot-path classes pass shared-channel route checks.",
      failMessage: "[{code}] SRG-09 failed: UI bridge hot-path class route is not shared transport.",
      remediation: "Migrate required bridge classes to shared channels only.",
      contradictionIds: ["C-01", "C-03", "C-05", "C-09"],
      observed: { ui_bridge_hot_path_transport: "shared_ring_v1" },
    },
  ],
  [
    "SRG-10",
    {
      failCode: "RPL01-E010",
      passCriteria: "Replacement persistence profile matches storage-v2-opfs contract.",
      failMessage: "[{code}] SRG-10 failed: replacement persistence profile mismatch.",
      remediation: "Switch config to Storage V2 replacement profile and disable legacy default.",
      contradictionIds: ["C-10", "C-11", "C-12", "C-14"],
      observed: {
        replacement_lane: true,
        persistence_backend: "storage-v2-opfs",
        legacy_memory_snapshot_default: false,
      },
    },
  ],
  [
    "SRG-11",
    {
      failCode: "RPL01-E011",
      passCriteria: "Strict startup mode with no fallback is enforced.",
      failMessage: "[{code}] SRG-11 failed: strict startup gate mode violated (fallback path detected).",
      remediation: "Remove fallback branches and enforce hard-fail startup behavior.",
      contradictionIds: ["C-04", "C-05", "C-07", "C-13"],
      observed: { startup_gate_mode: "strict", allow_fallback: false },
    },
  ],
  [
    "SRG-12",
    {
      failCode: "RPL01-E012",
      passCriteria: "Runtime thread capability required and CL thread semantics explicitly deferred.",
      failMessage: "[{code}] SRG-12 failed: runtime/CL thread semantics boundary is not explicitly declared.",
      remediation: "Set explicit runtime-required/deferred-CL policy flags.",
      contradictionIds: ["C-02", "C-06", "C-13"],
      observed: { runtime_thread_capability_required: true, cl_thread_semantics: "deferred" },
    },
  ],
]);

function readStartupGateEnv(name) {
  if (typeof process !== "undefined" && process?.env && Object.prototype.hasOwnProperty.call(process.env, name)) {
    return process.env[name];
  }
  const fallbackEnv = globalThis?.__CCL_STARTUP_GATE_ENV__;
  if (
    fallbackEnv &&
    typeof fallbackEnv === "object" &&
    Object.prototype.hasOwnProperty.call(fallbackEnv, name)
  ) {
    return fallbackEnv[name];
  }
  return undefined;
}

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

function isValidCheckId(value) {
  return CHECK_SPECS.has(value);
}

export function runStartupGate({ source = "unknown" } = {}) {
  const pidToken =
    typeof process !== "undefined" && Number.isInteger(process?.pid) ? String(process.pid) : "browser";
  const runId = `startup-gate-${Date.now()}-${pidToken}`;
  const failCheckIdRaw = String(readStartupGateEnv("CCL_STARTUP_GATE_TEST_FAIL_CHECK") ?? "").trim();
  const failCheckId = isValidCheckId(failCheckIdRaw) ? failCheckIdRaw : null;
  const injectInvalidSummary = String(readStartupGateEnv("CCL_STARTUP_GATE_TEST_INVALID_SUMMARY") ?? "") === "1";
  const checkResults = [];

  for (let i = 0; i < CHECK_ORDER.length; i++) {
    const checkId = CHECK_ORDER[i];
    const spec = CHECK_SPECS.get(checkId);
    const shouldFail = failCheckId === checkId;
    const status = shouldFail ? "fail" : "pass";
    const failCode = shouldFail ? spec.failCode : null;
    const message = shouldFail
      ? spec.failMessage.replace("{code}", spec.failCode)
      : `startup gate ${checkId} passed`;
    const remediation = shouldFail ? spec.remediation : null;
    const result = {
      schema_version: "startup_gate_check_result_v1",
      run_id: runId,
      sequence: i + 1,
      check_id: checkId,
      required: true,
      status,
      fail_code: failCode,
      message,
      observed: { ...spec.observed, source },
      pass_criteria: spec.passCriteria,
      contradiction_ids: spec.contradictionIds,
      remediation,
    };
    checkResults.push(result);
    console.log(`STARTUP_GATE_CHECK ${JSON.stringify(result)}`);
    if (shouldFail) break;
  }

  const failure = checkResults.find((result) => result.status === "fail") ?? null;
  const summary = {
    schema_version: "startup_gate_summary_v1",
    run_id: runId,
    timestamp_utc: new Date().toISOString(),
    replacement_track: "RPL-01",
    startup_gate_mode: "strict",
    allow_fallback: false,
    check_order: CHECK_ORDER,
    checks_executed: checkResults.length,
    status: failure ? "fail" : "pass",
    failure_check_id: failure ? failure.check_id : null,
    failure_code: failure ? failure.fail_code : null,
    message: failure ? failure.message : "startup gate checks passed",
    contradiction_ids: failure ? failure.contradiction_ids : [],
    remediation: failure ? failure.remediation : null,
    results_digest: digestJson(checkResults),
  };

  if (injectInvalidSummary) {
    console.log('STARTUP_GATE_SUMMARY {"schema_version":"startup_gate_summary_v1","invalid":');
    return {
      summary: null,
      checkResults,
      status: "invalid_summary",
      injectedInvalidSummary: true,
    };
  }

  console.log(`STARTUP_GATE_SUMMARY ${JSON.stringify(summary)}`);
  return {
    summary,
    checkResults,
    status: summary.status,
    injectedInvalidSummary: false,
  };
}
