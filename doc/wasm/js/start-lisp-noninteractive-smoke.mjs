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

function runNodeCase(name, args, { timeoutMs, expectCode, expectStdoutIncludes = null, expectStderrIncludes = null } = {}) {
  return new Promise((resolve, reject) => {
    let stdout = "";
    let stderr = "";
    let timedOut = false;

    const child = spawn(process.execPath, args, {
      stdio: ["ignore", "pipe", "pipe"],
      env: process.env,
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
      const artifactLines = [
        ...extractIpcArtifactLines(stdout),
        ...extractIpcArtifactLines(stderr),
      ];
      for (const line of artifactLines) {
        console.log(line);
      }
      resolve({ code, stdout, stderr });
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

await runNodeCase(
  "minimal-start-lisp-contract-enforced",
  [loadImageScript, "--mode", "start-lisp", "--expect-rc", "0", minimalImage],
  {
    timeoutMs,
    expectCode: 1,
    expectStderrIncludes: "pre-start bootstrap contract failed",
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
  },
);

await runNodeCase(
  "manifest-hash-mismatch",
  [loadImageScript, "--mode", "start-lisp", "--manifest", rootManifest, minimalImage],
  {
    timeoutMs,
    expectCode: 1,
    expectStderrIncludes: "hash mismatch",
  },
);

if (strictRoot) {
  await runNodeCase(
    "root-start-lisp-noninteractive",
    [
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
    ],
    {
      timeoutMs,
      expectCode: 0,
      expectStdoutIncludes: "wasm_ccl_start_lisp rc=0",
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
