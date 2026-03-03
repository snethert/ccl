/*
 * Startup function-designator gate smoke test.
 *
 * Verifies strict loader mode hard-fails when a required pre-toplevel
 * function designator cannot be resolved from bootstrap metadata.
 */

import { spawn } from "node:child_process";
import path from "node:path";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "../../..");
const loadImageScript = path.join(scriptDir, "../lib/load-image.mjs");

function runNode(args, { env = {} } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(
      process.execPath,
      args,
      {
        cwd: repoRoot,
        env: {
          ...process.env,
          ...env,
        },
        stdio: ["ignore", "pipe", "pipe"],
      },
    );

    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", reject);
    child.on("close", (code, signal) => {
      resolve({
        code: code == null ? null : (code | 0),
        signal: signal ?? null,
        stdout,
        stderr,
      });
    });
  });
}

const result = await runNode(
  [
    loadImageScript,
    "--mode",
    "start-lisp",
    "--bootstrap-contract",
    "strict",
    "--modules",
    "build/wasm32/modules/wasm-runtime-modules.json",
    "--stdin-text",
    "(quit)\\n",
    "--close-stdin",
    "build/wasm32/images/root.image",
  ],
  {
    env: {
      /*
       * PRINT-OBJECT appears in function-constant entries but is not present in
       * runtime bundle function metadata, so strict gate must fail.
       */
      CCL_STARTUP_REQUIRED_FUNCTIONS: "PRINT-OBJECT",
    },
  },
);

const combined = `${result.stdout}\n${result.stderr}`;
assert.notEqual(result.code, 0, "expected strict startup function gate to fail");
assert.match(
  combined,
  /STARTUP_FUNCTION_DESIGNATOR_GATE/,
  "expected machine-readable startup function-designator gate failure output",
);
assert.match(
  combined,
  /\"symbol_name\":\"PRINT-OBJECT\"/,
  "expected PRINT-OBJECT designator failure detail",
);
assert.match(
  combined,
  /\"binding_state\":\"unresolved-required-function-designator\"/,
  "expected unresolved required binding-state marker",
);
assert.match(
  combined,
  /\"entry_index\":null/,
  "expected unresolved gate entry index marker",
);

console.log("PASS: startup function-designator gate smoke");
