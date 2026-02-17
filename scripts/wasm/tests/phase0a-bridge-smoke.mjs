/*
 * Phase 0A — WASM LAP bridge function unit tests.
 *
 * Validates that the 333 pure-Lisp bridge functions in level-0/WASM/
 * compile correctly and produce expected results when run in the
 * WASM runtime.
 *
 * Each test function takes 0 arguments and returns fixnum 1 (pass)
 * or 0 (fail).  The JS side calls each, decodes the fixnum, and
 * reports pass/fail/trap.
 *
 * Usage:
 *   node scripts/wasm/tests/phase0a-bridge-smoke.mjs
 *
 * Prerequisites:
 *   scripts/wasm/compile-phase0a-tests.sh  (generates the test bundle)
 */

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  createCclImports,
  createSharedCclRuntime,
  installSubprimsTable,
  installCompiledModulesFromBundle,
  instantiateWasm,
} from "./ccl-loader.mjs";
import { createMicrokernel } from "./microkernel.mjs";

// ── Helpers ──────────────────────────────────────────────────────────

function fail(msg) {
  console.error(`FAIL: ${msg}`);
  process.exit(1);
}

function assert(cond, msg) {
  if (!cond) fail(msg);
}

function readFileUrl(url) {
  return fs.readFile(fileURLToPath(url));
}

// ── Paths ────────────────────────────────────────────────────────────

const kernelUrl = new URL(
  "../../../build/wasm32/kernel/wasmcl.wasm",
  import.meta.url,
);
const subprimsUrl = new URL(
  "../../../build/wasm32/subprims/subprims.wasm",
  import.meta.url,
);
const subprimsMapUrl = new URL(
  "../../../build/wasm32/subprims-map.json",
  import.meta.url,
);
// Try minimal.image first, fall back to wasm-boot.image
const imageUrl = new URL(
  "../../../build/wasm32/wasm-boot.image",
  import.meta.url,
);
const bundleUrl = new URL(
  "../../../build/wasm32/modules/wasm-phase0a-tests.json",
  import.meta.url,
);

// ── Load test bundle ─────────────────────────────────────────────────

let bundle;
let bundleBinaryBytes;
let bundleIndexBytes;
try {
  bundle = JSON.parse((await readFileUrl(bundleUrl)).toString("utf8"));
  if (bundle?.format === "ccl-wasm-modules-v2") {
    if (typeof bundle?.binary !== "string" || bundle.binary.length === 0) {
      fail("wasm-phase0a-tests.json missing binary field");
    }
    if (typeof bundle?.index !== "string" || bundle.index.length === 0) {
      fail("wasm-phase0a-tests.json missing index field");
    }
    const bundleDir = path.dirname(fileURLToPath(bundleUrl));
    bundleBinaryBytes = await fs.readFile(
      path.resolve(bundleDir, bundle.binary),
    );
    bundleIndexBytes = await fs.readFile(
      path.resolve(bundleDir, bundle.index),
    );
  }
  // Else: inline v1 format, handled by installCompiledModulesFromBundle
} catch (err) {
  fail(
    `missing or invalid Phase 0A test bundle (run scripts/wasm/compile-phase0a-tests.sh): ${err?.message ?? err}`,
  );
}

// ── Create runtime ───────────────────────────────────────────────────

const runtime = createSharedCclRuntime({
  memoryInitialPages: 256,
  subprimsTableInitial: 256,
});

const microkernel = createMicrokernel({
  memory: runtime.memory,
  writeStdout: () => {},
  writeStderr: () => {},
});

// ── Instantiate kernel ───────────────────────────────────────────────

const kernelBytes = await readFileUrl(kernelUrl);
const kernel = await instantiateWasm(
  kernelBytes,
  createCclImports({
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel,
  }),
);

// ── Instantiate subprims ─────────────────────────────────────────────

const subprimsBytes = await readFileUrl(subprimsUrl);
const subprimsMap = JSON.parse(
  (await readFileUrl(subprimsMapUrl)).toString("utf8"),
);
const subprims = await instantiateWasm(
  subprimsBytes,
  createCclImports({
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel,
    extra: { ccl: kernel.instance.exports },
  }),
);

installSubprimsTable({
  table: runtime.subprimsTable,
  subprimsMap,
  providers: [
    { exports: kernel.instance.exports },
    { exports: subprims.instance.exports },
  ],
});

assert(
  typeof kernel.instance.exports.wasm_set_subprims_ready === "function",
  "missing wasm_set_subprims_ready export",
);
kernel.instance.exports.wasm_set_subprims_ready(1);

// ── Load boot image ──────────────────────────────────────────────────

const imageBytes = await readFileUrl(imageUrl);
const imageLen = imageBytes.byteLength >>> 0;

const pageSize = 65536;
const cstackSize = 1 << 20;
const reserve = 4 << 20;

const needBytes = imageLen + cstackSize + reserve;
let haveBytes = runtime.memory.buffer.byteLength;
if (needBytes > haveBytes) {
  const growPages = Math.ceil((needBytes - haveBytes) / pageSize);
  runtime.memory.grow(growPages);
  haveBytes = runtime.memory.buffer.byteLength;
}

assert(
  typeof kernel.instance.exports.wasm_set_cstack_bounds === "function",
  "missing wasm_set_cstack_bounds export",
);
const cstackBase = runtime.memory.buffer.byteLength;
kernel.instance.exports.wasm_set_cstack_bounds(cstackBase, cstackSize);

const blobBase = (cstackBase - cstackSize - imageLen) & ~15;
assert(blobBase >= 0, "not enough memory to place boot image below cstack");
new Uint8Array(runtime.memory.buffer).set(imageBytes, blobBase);

assert(
  typeof kernel.instance.exports.wasm_ccl_load_image === "function",
  "missing wasm_ccl_load_image export",
);
kernel.instance.exports.wasm_ccl_load_image(blobBase, imageLen);

// ── Install test modules ─────────────────────────────────────────────

// Provide stubs for imports that may not exist in a stale kernel build.
// These are needed when wasm2.lisp uncommitted changes add new IR instructions
// but the kernel hasn't been rebuilt yet.
const mem = runtime.memory;
const extraCcl = {};
if (typeof kernel.instance.exports.wasm_lisp_word_set !== "function") {
  extraCcl.wasm_lisp_word_set = (base, offset, value) => {
    const addr = ((base >> 2) + (offset >> 2)) << 2;  // fixnum decode
    new DataView(mem.buffer).setInt32(addr, value, true);
    return value;
  };
}
if (typeof kernel.instance.exports.wasm_lisp_word_ref !== "function") {
  extraCcl.wasm_lisp_word_ref = (base, offset) => {
    const addr = ((base >> 2) + (offset >> 2)) << 2;
    return new DataView(mem.buffer).getInt32(addr, true);
  };
}

const { installed, count, failed } = await installCompiledModulesFromBundle({
  bundle,
  binaryBytes: bundleBinaryBytes,
  indexBytes: bundleIndexBytes,
  kernel,
  memory: runtime.memory,
  subprimsTable: runtime.subprimsTable,
  microkernel,
  extra: { ccl: extraCcl },
  strict: true,
  installConstPools: true,
});

if (count === 0 || installed === 0) {
  fail(`no test modules installed from Phase 0A bundle`);
}
if (failed) {
  fail(`test modules failed during install: ${failed}`);
}

// ── Staleness check ─────────────────────────────────────────────────
// Warn if key artifacts are out of sync (kernel/subprims newer than test bundle)

{
  const { statSync } = await import("node:fs");
  const checkFiles = [
    { label: "kernel", path: fileURLToPath(kernelUrl) },
    { label: "subprims", path: fileURLToPath(subprimsUrl) },
  ];
  const bundlePath = fileURLToPath(bundleUrl);
  try {
    const bundleMtime = statSync(bundlePath).mtimeMs;
    const stale = checkFiles.filter((f) => {
      try {
        return statSync(f.path).mtimeMs > bundleMtime;
      } catch {
        return false;
      }
    });
    if (stale.length > 0) {
      const names = stale.map((s) => s.label).join(", ");
      console.error(
        `\n⚠️  STALE TEST MODULES: ${names} newer than test bundle.` +
          `\n   Results may be unreliable. Run: scripts/wasm/compile-phase0a-tests.sh\n`,
      );
    }
  } catch {
    // Ignore stat errors
  }
}

// ── Run tests ────────────────────────────────────────────────────────

const kernelExports = kernel.instance.exports;
assert(
  typeof kernelExports.wasm_test_entry_funcall === "function",
  "missing wasm_test_entry_funcall export",
);

const functions = Array.isArray(bundle.functions) ? bundle.functions : [];
assert(functions.length > 0, "no test functions in bundle");

const fixnumShift = 2;
let passed = 0;
let failures = 0;
let traps = 0;
const failedTests = [];

for (const fn of functions) {
  const name = fn.name;
  const entry = fn.entryIndex >>> 0;

  try {
    const rawResult = kernelExports.wasm_test_entry_funcall(entry, 0);
    const result = rawResult >> fixnumShift;

    if (result === 1) {
      passed++;
    } else {
      failures++;
      failedTests.push({ name, result, reason: "returned 0 (assertion failed)" });
    }
  } catch (err) {
    traps++;
    failedTests.push({ name, result: null, reason: `trap: ${err?.message ?? err}` });
  }
}

// ── Report ───────────────────────────────────────────────────────────

const total = functions.length;
console.log(`\nPhase 0A Bridge Tests: ${total} total`);
console.log(`  PASS:  ${passed}`);
console.log(`  FAIL:  ${failures}`);
console.log(`  TRAP:  ${traps}`);

if (failedTests.length > 0) {
  console.log(`\nFailed tests:`);
  for (const t of failedTests) {
    console.log(`  ${t.name}: ${t.reason}`);
  }
}

if (failures === 0 && traps === 0) {
  console.log(`\nAll ${total} Phase 0A bridge tests passed.`);
} else {
  console.log(
    `\n${failedTests.length} test(s) failed or trapped out of ${total}.`,
  );
  process.exit(1);
}
