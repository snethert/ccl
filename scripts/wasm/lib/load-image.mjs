/*
 * CCL WASM — Phase 3 deterministic launcher.
 *
 * Load plan → load image → fill table → start Lisp.
 * Const pools installed on demand from modules.bin at runtime.
 * Zero bundle parsing. Zero function designator resolution.
 * 36 merged module binaries compiled in parallel, 8675 table entries filled.
 *
 * Usage:
 *   node scripts/wasm/lib/load-image.mjs [OPTIONS]
 *
 * Options:
 *   --startup-plan PATH   startup-plan.json (default: build/wasm32/images/startup-plan.json)
 *   --start-lisp          call wasm_ccl_start_lisp (default)
 *   --run                 call wasm_run_toplevel after start_lisp
 *   --stdin-text TEXT     feed UTF-8 text to stdin before start
 *   --stdin-script PATH   feed file bytes to stdin before start
 *   --close-stdin         close stdin after preload
 *   --expect-rc N         exit 5 if return code != N
 */

import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

import { createCclImports, instantiateWasm } from "./ccl-loader.mjs";
import { WASM_BOOT_ENTRY_INDEX } from "./abi-constants.mjs";
import { createMicrokernel } from "./microkernel.mjs";

// ── Utilities ──────────────────────────────────────────────────────────────

function fail(msg) {
  console.error(`FAIL: ${msg}`);
  process.exit(1);
}

function sha256Hex(buf) {
  return crypto.createHash("sha256").update(buf).digest("hex");
}

// ── Arg parsing ────────────────────────────────────────────────────────────

const opts = {
  planPath: null,
  runToplevel: false,
  stdinText: null,
  stdinScriptPath: null,
  closeStdin: false,
  expectRc: null,
};

const argv = process.argv.slice(2);
for (let i = 0; i < argv.length; i++) {
  const arg = argv[i];
  switch (arg) {
    case "--startup-plan": opts.planPath = argv[++i]; break;
    case "--start-lisp":   /* default, no-op */ break;
    case "--run":          opts.runToplevel = true; break;
    case "--stdin-text":   opts.stdinText = String(argv[++i] ?? ""); break;
    case "--stdin-script": opts.stdinScriptPath = argv[++i]; break;
    case "--close-stdin":  opts.closeStdin = true; break;
    case "--expect-rc":    opts.expectRc = parseInt(String(argv[++i] ?? ""), 10) | 0; break;
    case "--help": case "-h":
      console.error(
        "Usage: load-image.mjs [--startup-plan PATH] [--run]\n" +
        "       [--stdin-text TEXT | --stdin-script PATH] [--close-stdin]\n" +
        "       [--expect-rc N]"
      );
      process.exit(0);
    default:
      if (arg.startsWith("--")) fail(`Unknown option: ${arg}`);
      break;
  }
}

// ── Paths ──────────────────────────────────────────────────────────────────

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const defaultPlanPath = path.resolve(scriptDir, "../../../build/wasm32/images/startup-plan.json");
const planPath = opts.planPath ? path.resolve(opts.planPath) : defaultPlanPath;
const imagesDir  = path.dirname(planPath);
const buildDir   = path.dirname(imagesDir);   // build/wasm32/
const kernelPath  = path.join(buildDir, "kernel",  "wasmcl.wasm");
const subprimsPath = path.join(buildDir, "subprims", "subprims.wasm");

// ── Read and validate startup plan ────────────────────────────────────────

const plan = JSON.parse(await fs.readFile(planPath, "utf8"));

if (plan.schemaVersion !== 1) {
  fail(`Unsupported startup-plan schema version: ${plan.schemaVersion}`);
}
if (!plan.constPools || !plan.constPools.baked) {
  fail("startup-plan.json: constPools not baked — rebuild required (run rebuild-everything.sh)");
}
if (plan.constPools.baked === true) {
  console.log(`const pools: ${plan.constPools.bakedCount ?? "all"} pre-baked in image`);
} else {
  console.log(`WARN: constPools.baked=${plan.constPools.baked} — expected true`);
}

const imageSize    = plan.memory.imageSize >>> 0;
const initialPages = plan.memory.initialPages >>> 0;
const tableSize    = plan.functionTable.size >>> 0;
const entries      = plan.functionTable.entries;

// ── Validate startup plan ──────────────────────────────────────────────────

for (const e of entries) {
  if ((e.index >>> 0) >= tableSize) {
    fail(`startup-plan entry index ${e.index} >= functionTable.size ${tableSize}`);
  }
}

// ── Load binary artifacts ──────────────────────────────────────────────────

const [kernelBytes, subprimsBytes, modulesBin] = await Promise.all([
  fs.readFile(kernelPath),
  fs.readFile(subprimsPath),
  fs.readFile(path.join(imagesDir, "modules.bin")),
]);

// Hash validation (skip root.image — kernel validates magic/integrity internally).
function assertHash(label, bytes, expected) {
  if (!expected) return;
  const actual = sha256Hex(bytes);
  if (actual !== expected) {
    fail(`${label} hash mismatch:\n  expected ${expected}\n  actual   ${actual}`);
  }
}
assertHash("kernelWasm",  kernelBytes,   plan.artifacts?.kernelWasm?.sha256);
assertHash("subprimsWasm", subprimsBytes, plan.artifacts?.subprimsWasm?.sha256);
assertHash("modulesBin",   modulesBin,    plan.artifacts?.modulesBin?.sha256);

// ── Create WASM memory and function table ──────────────────────────────────

// Allocate memory at the exact size used during the build so that blobBase is
// identical (same formula = same address = bias 0, no relocation walk).
const memory = new WebAssembly.Memory({ initial: initialPages });
const subprimsTable = new WebAssembly.Table({ initial: tableSize, element: "anyfunc" });

// blobBase: image placed below the C-stack at the top of memory.
// Matches the formula in make-real-image.mjs exactly.  Uses plain arithmetic
// (not bitwise) to avoid sign issues with values > 2^31.
const cstackSize  = 1 << 20;   // 1 MiB
const memSize     = initialPages * 65536;
const blobBaseRaw = memSize - cstackSize - imageSize;
const blobBase    = blobBaseRaw - (blobBaseRaw % 16);  // align down to 16 bytes
if (blobBase < 0) {
  fail(`blobBase underflow: memSize=${memSize} cstackSize=${cstackSize} imageSize=${imageSize}`);
}

// ── Load root.image into WASM memory ──────────────────────────────────────

{
  const gib = (imageSize / (1024 ** 3)).toFixed(2);
  console.log(`loading root.image (${gib} GiB) at 0x${blobBase.toString(16)}...`);
  const fh = await fs.open(path.join(imagesDir, "root.image"), "r");
  const dest = new Uint8Array(memory.buffer);
  const CHUNK = 64 * 1024 * 1024;  // 64 MiB per read
  let offset = 0;
  while (offset < imageSize) {
    const toRead = Math.min(CHUNK, imageSize - offset);
    const buf = Buffer.allocUnsafe(toRead);
    const { bytesRead } = await fh.read(buf, 0, toRead, offset);
    if (bytesRead === 0) fail(`short read on root.image at offset ${offset}`);
    dest.set(new Uint8Array(buf.buffer, buf.byteOffset, bytesRead), blobBase + offset);
    offset += bytesRead;
  }
  await fh.close();
  console.log("root.image loaded");
}

// ── Microkernel ────────────────────────────────────────────────────────────

const microkernel = createMicrokernel({
  memory,
  writeStdout: (buf) => process.stdout.write(buf),
  writeStderr: (buf) => process.stderr.write(buf),
});

if (opts.stdinScriptPath) {
  microkernel.feedStdin(await fs.readFile(path.resolve(opts.stdinScriptPath)));
}
if (opts.stdinText != null) {
  microkernel.feedStdin(new TextEncoder().encode(opts.stdinText));
}
if (opts.closeStdin || opts.stdinScriptPath || opts.stdinText != null) {
  microkernel.closeStdin?.();
}

// Const pools are pre-baked in the image — no on-demand installation needed.

const noopDesignator = () => -1;
// Stub: if the kernel still imports wasm_host_install_const_pool, return 0
// to signal "not available" (should never be called with pre-baked pools).
const noopConstPool = () => 0;

function makeImports(extraCcl = {}) {
  return createCclImports({
    memory,
    subprimsTable,
    microkernel,
    extra: {
      ccl: {
        wasm_host_install_const_pool: noopConstPool,
        wasm_host_resolve_function_designator_entry: noopDesignator,
        ...extraCcl,
      },
    },
  });
}

// ── Instantiate kernel + subprims ──────────────────────────────────────────

const kernel  = await instantiateWasm(kernelBytes,  makeImports());
const subprims = await instantiateWasm(subprimsBytes, makeImports(kernel.instance.exports));

// ── Fill subprims table entries (indices 0–131) ────────────────────────────

for (const e of entries) {
  if (e.source !== "subprims") continue;
  const fn = subprims.instance.exports[e.export] ?? kernel.instance.exports[e.export];
  if (!fn) fail(`subprims missing export: ${e.export} (index ${e.index})`);
  subprimsTable.set(e.index, fn);
}

// Boot entry: kernel export, not in startup-plan.json.
const bootEntry = kernel.instance.exports.wasm_boot_entry;
if (typeof bootEntry !== "function") fail("kernel missing export wasm_boot_entry");
subprimsTable.set(WASM_BOOT_ENTRY_INDEX, bootEntry);

// ── Set C-stack bounds (required before wasm_ccl_load_image) ──────────────

// cstackBase = top of memory; cstack grows downward from there.
// Value is passed as i32 — the kernel treats it as uint32_t.
const cstackBase = memory.buffer.byteLength;  // = initialPages × 65536
kernel.instance.exports.wasm_set_cstack_bounds(cstackBase, cstackSize);

// ── Load image and reset runtime state ────────────────────────────────────

const loadRc = kernel.instance.exports.wasm_ccl_load_image(blobBase, imageSize) | 0;
const nil    = kernel.instance.exports.wasm_get_lisp_nil?.() >>> 0;
console.log(`wasm_ccl_load_image rc=${loadRc} nil=0x${nil.toString(16)}`);

const resetFn = kernel.instance.exports.wasm_reset_root_image_runtime_state;
if (typeof resetFn === "function") {
  const resetRc = resetFn() | 0;
  if (resetRc !== 0) fail(`wasm_reset_root_image_runtime_state returned ${resetRc}`);
}

// ── Compile and instantiate merged module binaries ─────────────────────────

const moduleEntries = entries.filter(e => e.source === "modules");

// Deduplicate: 8675 entries map to 36 unique binary spans.
const spanKey = (e) => `${e.offset}:${e.length}`;
const spanMap = new Map();   // spanKey → first matching entry (offset + length)
for (const e of moduleEntries) {
  if (!spanMap.has(spanKey(e))) spanMap.set(spanKey(e), e);
}
const uniqueSpans = [...spanMap.values()];
console.log(`compiling ${uniqueSpans.length} module binaries (${moduleEntries.length} table entries)...`);

// Compile all unique spans in parallel.
const compiled = await Promise.all(
  uniqueSpans.map(e => WebAssembly.compile(modulesBin.subarray(e.offset, e.offset + e.length)))
);

// Instantiate all compiled modules in parallel.  All share the same import set.
const moduleImports = makeImports(kernel.instance.exports);
const instances = await Promise.all(
  compiled.map(mod => WebAssembly.instantiate(mod, moduleImports))
);

// Build a key → instance lookup.
// WebAssembly.instantiate(Module, imports) resolves to a WebAssembly.Instance.
const keyToInst = new Map(uniqueSpans.map((e, i) => [spanKey(e), instances[i]]));

// Fill all 8675 module table entries.
for (const e of moduleEntries) {
  const inst = keyToInst.get(spanKey(e));
  const fn = inst.exports[e.export];
  if (!fn) fail(`module missing export: ${e.export} (entry ${e.index})`);
  subprimsTable.set(e.index, fn);
}
console.log(`filled ${moduleEntries.length} module table entries`);

// ── Mark subprims ready ────────────────────────────────────────────────────

kernel.instance.exports.wasm_set_subprims_ready?.(1);

// ── Assert critical symbols are fbound ─────────────────────────────────────
// With pre-baked pools, symbols should be correctly bound from the saved image.
// No launch-time repair pass needed.

{
  const ex = kernel.instance.exports;
  if (typeof ex.wasm_check_symbol_fbound === "function") {
    const encoder = new TextEncoder();
    const critical = ["TOPLEVEL-LOOP", "RESTORE-LISP-POINTERS"];
    for (const name of critical) {
      const nameBytes = encoder.encode(name);
      const ptr = memory.buffer.byteLength;
      memory.grow(1);
      new Uint8Array(memory.buffer, ptr, nameBytes.length).set(nameBytes);
      const rc = ex.wasm_check_symbol_fbound(ptr >>> 0, nameBytes.length >>> 0) | 0;
      if (rc !== 1) {
        fail(`critical symbol ${name} is not fbound (rc=${rc}) — startup will fail`);
      }
    }
    console.log("critical symbol fbound check passed");
  }
}

// ── Pre-start heap telemetry ────────────────────────────────────────────────

{
  const ex = kernel.instance.exports;
  const memBytes = memory.buffer.byteLength;
  console.log(`pre-start: WASM memory ${(memBytes / (1024*1024)).toFixed(0)} MiB`);
  if (typeof ex.wasm_heap_profile === "function") {
    const liveBytes = ex.wasm_heap_profile() >>> 0;
    console.log(`pre-start: heap live ${(liveBytes / (1024*1024)).toFixed(1)} MiB`);
  }
}

// ── Start ──────────────────────────────────────────────────────────────────

let entryRc = null;

{
  const startFn = kernel.instance.exports.wasm_ccl_start_lisp;
  if (typeof startFn !== "function") fail("kernel missing export wasm_ccl_start_lisp");
  try {
    entryRc = startFn() | 0;
    console.log(`wasm_ccl_start_lisp rc=${entryRc}`);
  } catch (e) {
    console.error(`wasm_ccl_start_lisp trapped: ${e}`);
    if (e instanceof Error && e.stack) console.error(e.stack);
    process.exit(4);
  }
}

if (opts.runToplevel) {
  const runFn = kernel.instance.exports.wasm_run_toplevel;
  if (typeof runFn !== "function") fail("kernel missing export wasm_run_toplevel");
  try {
    entryRc = runFn() | 0;
    console.log(`wasm_run_toplevel rc=${entryRc}`);
  } catch (e) {
    console.error(`wasm_run_toplevel trapped: ${e}`);
    process.exit(4);
  }
}

if (opts.expectRc != null && entryRc != null) {
  if ((entryRc | 0) !== (opts.expectRc | 0)) {
    console.error(`FAIL: rc mismatch: expected ${opts.expectRc}, got ${entryRc}`);
    process.exit(5);
  }
}
