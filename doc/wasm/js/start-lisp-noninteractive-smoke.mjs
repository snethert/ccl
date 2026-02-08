/*
 * Non-interactive start_lisp smoke harness.
 *
 * Runs load-image.mjs in child processes with explicit timeouts so hangs
 * cannot stall unattended runs.
 */

import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

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
      resolve({ code, stdout, stderr });
    });
  });
}

const strictRoot = process.argv.includes("--strict-start-lisp-noninteractive");
const timeoutMs = 15000;

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "../../..");
const loadImageScript = path.resolve(scriptDir, "load-image.mjs");

const minimalImage = path.resolve(repoRoot, "doc/wasm/minimal.image");
const rootImage = path.resolve(repoRoot, "doc/wasm/root.image");
const rootManifest = path.resolve(repoRoot, "doc/wasm/root.image.manifest.json");
const runtimeModulesManifest = path.resolve(repoRoot, "doc/wasm/wasm-runtime-modules.json");

await runNodeCase(
  "minimal-start-lisp",
  [loadImageScript, "--mode", "start-lisp", "--expect-rc", "0", minimalImage],
  {
    timeoutMs,
    expectCode: 0,
    expectStdoutIncludes: "wasm_ccl_start_lisp rc=0",
  },
);

await runNodeCase(
  "manifest-hash-mismatch",
  [loadImageScript, "--mode", "start-lisp", "--manifest", rootManifest, minimalImage],
  {
    timeoutMs,
    expectCode: 1,
    expectStderrIncludes: "rootImage hash mismatch",
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

console.log("PASS: start-lisp non-interactive smoke test");
