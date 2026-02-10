/*
 * Node-first WASM32 smoke test.
 *
 * Validates:
 *  1) `call_indirect` subprims dispatch via `wasm_call_subprim_fixnum`
 *  2) manual cstack relocation across `memory.grow`
 *
 * This intentionally avoids calling `wasm_ccl_start`; this test focuses on
 * low-level subprims dispatch and cstack relocation.
 */

import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";

import {
  createCclImports,
  createSharedCclRuntime,
  installSubprimsTable,
  instantiateWasm,
} from "./ccl-loader.mjs";
import { createMicrokernel } from "./microkernel.mjs";

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

const kernelUrl = new URL("./wasmcl.wasm", import.meta.url);
const subprimsMapUrl = new URL("../subprims-map.json", import.meta.url);

const runtime = createSharedCclRuntime({
  // The module only requires 2 pages, but use something roomy for smoke tests.
  memoryInitialPages: 256, // 16 MiB
  subprimsTableInitial: 256,
  createMemory: true,
});

// The kernel now imports the kernel_request ABI; provide a minimal microkernel.
const microkernel = createMicrokernel({
  memory: runtime.memory,
  writeStdout: () => {},
  writeStderr: () => {},
});

const logs = [];
const decoder = typeof TextDecoder !== "undefined" ? new TextDecoder("utf-8") : null;
function wasm_host_log(ptr, len) {
  if (!decoder) return;
  const u8 = new Uint8Array(runtime.memory.buffer, ptr >>> 0, len >>> 0);
  logs.push(decoder.decode(u8));
}

const kernelBytes = await readFileUrl(kernelUrl);
const kernel = await instantiateWasm(
  kernelBytes,
  createCclImports({
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel,
    extra: { env: { wasm_host_log } },
  }),
);

assert(
  typeof kernel.instance.exports.wasm_get_subprims_ready === "function",
  "missing wasm_get_subprims_ready export",
);
assert(
  typeof kernel.instance.exports.wasm_set_subprims_ready === "function",
  "missing wasm_set_subprims_ready export",
);
assert(
  typeof kernel.instance.exports.wasm_set_gc_root_policy === "function",
  "missing wasm_set_gc_root_policy export",
);
assert(
  typeof kernel.instance.exports.wasm_get_gc_root_policy === "function",
  "missing wasm_get_gc_root_policy export",
);
assert(
  typeof kernel.instance.exports.wasm_set_gc_root_policy_mode === "function",
  "missing wasm_set_gc_root_policy_mode export",
);
assert(
  typeof kernel.instance.exports.wasm_get_gc_root_policy_mode === "function",
  "missing wasm_get_gc_root_policy_mode export",
);
assert(
  typeof kernel.instance.exports.wasm_set_entry_gc_root_policy_mode === "function",
  "missing wasm_set_entry_gc_root_policy_mode export",
);
assert(
  typeof kernel.instance.exports.wasm_get_entry_gc_root_policy_mode === "function",
  "missing wasm_get_entry_gc_root_policy_mode export",
);
assert(
  typeof kernel.instance.exports.wasm_clear_entry_gc_root_policy_modes === "function",
  "missing wasm_clear_entry_gc_root_policy_modes export",
);
const GC_ROOT_INCLUDE_XP_LOCATIVES = 1 << 0;
const GC_ROOT_INCLUDE_CSTACK = 1 << 1;
const GC_ROOT_INCLUDE_CSTACK_SAVEVSP = 1 << 2;
const GC_ROOT_INCLUDE_TCR_GC_CONTEXT = 1 << 3;
const GC_ROOT_INCLUDE_TCR_XFRAMES = 1 << 4;
const GC_ROOT_INCLUDE_TCR_TLB = 1 << 5;
const GC_ROOT_MODE_RUNTIME_DEFAULT = 0;
const GC_ROOT_MODE_RUNTIME_BOOTSTRAP = 1;
const GC_ROOT_MODE_HOST_MASK = 2;
const GC_ROOT_POLICY_DEFAULT =
  GC_ROOT_INCLUDE_XP_LOCATIVES |
  GC_ROOT_INCLUDE_CSTACK |
  GC_ROOT_INCLUDE_CSTACK_SAVEVSP |
  GC_ROOT_INCLUDE_TCR_GC_CONTEXT |
  GC_ROOT_INCLUDE_TCR_XFRAMES |
  GC_ROOT_INCLUDE_TCR_TLB;
const GC_ROOT_POLICY_BOOTSTRAP = GC_ROOT_POLICY_DEFAULT & ~GC_ROOT_INCLUDE_CSTACK_SAVEVSP;

kernel.instance.exports.wasm_set_subprims_ready(1);
assert(kernel.instance.exports.wasm_get_subprims_ready() === 1, "subprims ready flag set failed");
assert(
  (kernel.instance.exports.wasm_get_gc_root_policy_mode() >>> 0) === GC_ROOT_MODE_RUNTIME_DEFAULT,
  "gc root policy mode did not switch to runtime default",
);
assert(
  (kernel.instance.exports.wasm_get_gc_root_policy() >>> 0) === GC_ROOT_POLICY_DEFAULT,
  "gc root policy did not switch to runtime default mask",
);
kernel.instance.exports.wasm_set_subprims_ready(0);
assert(kernel.instance.exports.wasm_get_subprims_ready() === 0, "subprims ready flag clear failed");
assert(
  (kernel.instance.exports.wasm_get_gc_root_policy_mode() >>> 0) === GC_ROOT_MODE_RUNTIME_BOOTSTRAP,
  "gc root policy mode did not switch to runtime bootstrap",
);
assert(
  (kernel.instance.exports.wasm_get_gc_root_policy() >>> 0) === GC_ROOT_POLICY_BOOTSTRAP,
  "gc root policy did not switch to runtime bootstrap mask",
);
kernel.instance.exports.wasm_set_subprims_ready(1);
assert(kernel.instance.exports.wasm_get_subprims_ready() === 1, "subprims ready flag restore failed");
{
  const initialPolicy = kernel.instance.exports.wasm_get_gc_root_policy() >>> 0;
  const nonDefaultPolicy = (initialPolicy ^ GC_ROOT_INCLUDE_XP_LOCATIVES) >>> 0;
  const publishedPolicy = kernel.instance.exports.wasm_set_gc_root_policy(nonDefaultPolicy) >>> 0;
  assert(publishedPolicy === nonDefaultPolicy, "gc root policy publish failed");
  assert((kernel.instance.exports.wasm_get_gc_root_policy() >>> 0) === nonDefaultPolicy, "gc root policy readback failed");
  assert(
    (kernel.instance.exports.wasm_get_gc_root_policy_mode() >>> 0) === GC_ROOT_MODE_HOST_MASK,
    "gc root policy mode did not switch to host mask",
  );
  kernel.instance.exports.wasm_set_gc_root_policy_mode(GC_ROOT_MODE_RUNTIME_DEFAULT);
  assert(
    (kernel.instance.exports.wasm_get_gc_root_policy_mode() >>> 0) === GC_ROOT_MODE_RUNTIME_DEFAULT,
    "gc root policy mode restore failed",
  );
  assert(
    (kernel.instance.exports.wasm_get_gc_root_policy() >>> 0) === initialPolicy,
    "gc root policy restore failed",
  );
}
{
  const testEntryIndex = 321 >>> 0;
  assert(
    (kernel.instance.exports.wasm_get_entry_gc_root_policy_mode(testEntryIndex) >>> 0) === GC_ROOT_MODE_RUNTIME_DEFAULT,
    "entry gc root policy mode default lookup failed",
  );
  assert(
    (kernel.instance.exports.wasm_set_entry_gc_root_policy_mode(testEntryIndex, GC_ROOT_MODE_RUNTIME_BOOTSTRAP) >>> 0) ===
      GC_ROOT_MODE_RUNTIME_BOOTSTRAP,
    "entry gc root policy mode set failed",
  );
  assert(
    (kernel.instance.exports.wasm_get_entry_gc_root_policy_mode(testEntryIndex) >>> 0) === GC_ROOT_MODE_RUNTIME_BOOTSTRAP,
    "entry gc root policy mode readback failed",
  );
  kernel.instance.exports.wasm_clear_entry_gc_root_policy_modes();
  assert(
    (kernel.instance.exports.wasm_get_entry_gc_root_policy_mode(testEntryIndex) >>> 0) === GC_ROOT_MODE_RUNTIME_DEFAULT,
    "entry gc root policy mode clear failed",
  );
}

const subprimsMap = JSON.parse((await readFileUrl(subprimsMapUrl)).toString("utf8"));

const providers = [{ exports: kernel.instance.exports }];
const { installed, needed } = installSubprimsTable({
  table: runtime.subprimsTable,
  subprimsMap,
  providers,
  verbose: false,
});
assert(installed > 0, `installed 0/${needed} subprims`);

// --- 1) call_indirect dispatch ---
const unused1Index = subprimsMap.symbols.indexOf("_SPunused1");
const unused2Index = subprimsMap.symbols.indexOf("_SPunused2");
assert(unused1Index >= 0, "subprims map missing _SPunused1");
assert(unused2Index >= 0, "subprims map missing _SPunused2");

assert(typeof kernel.instance.exports.wasm_call_subprim_fixnum === "function", "missing wasm_call_subprim_fixnum export");
assert(typeof kernel.instance.exports._SPunused1 === "function", "missing _SPunused1 export");
assert(typeof kernel.instance.exports._SPunused2 === "function", "missing _SPunused2 export");

// Fixnum representation on wasm32 follows ARM32: low 2 bits are tag.
const fixnumShift = 2;
const unused1Fixnum = unused1Index << fixnumShift;
const unused2Fixnum = unused2Index << fixnumShift;
kernel.instance.exports.wasm_call_subprim_fixnum(unused1Fixnum);
kernel.instance.exports.wasm_call_subprim_fixnum(unused2Fixnum);

// Negative test: a null table slot should trap on `call_indirect`.
runtime.subprimsTable.set(unused2Index, null);
let trapped = false;
try {
  kernel.instance.exports.wasm_call_subprim_fixnum(unused2Fixnum);
} catch (_e) {
  trapped = true;
}
assert(trapped, "expected call_indirect trap for null subprim entry");

// --- 2) cstack relocation across memory.grow ---
assert(typeof kernel.instance.exports.wasm_set_cstack_bounds === "function", "missing wasm_set_cstack_bounds export");
assert(typeof kernel.instance.exports.wasm_get_cstack_pointer === "function", "missing wasm_get_cstack_pointer export");
assert(
  typeof kernel.instance.exports.wasm_memory_grow_and_relocate === "function",
  "missing wasm_memory_grow_and_relocate export (export it from lisp-kernel/wasm32/Makefile)",
);

const cstackSize = 1 << 20; // 1 MiB
const oldBase = runtime.memory.buffer.byteLength;
assert(oldBase >= cstackSize, `memory too small for cstack: base=${oldBase}, size=${cstackSize}`);

const oldLow = oldBase - cstackSize;
const sentinel = Uint8Array.from([0x53, 0x4d, 0x4f, 0x4b, 0x45, 0x2d, 0x54, 0x45, 0x53, 0x54, 0x00, 0xff]);
{
  const u8 = new Uint8Array(runtime.memory.buffer);
  u8.set(sentinel, oldLow);
}

kernel.instance.exports.wasm_set_cstack_bounds(oldBase, cstackSize);
assert(kernel.instance.exports.wasm_get_cstack_pointer() === oldBase, "unexpected cstack SP after set bounds");

const growPages = 16; // 1 MiB; chosen to avoid overlap with a 1 MiB cstack region.
const oldPages = kernel.instance.exports.wasm_memory_grow_and_relocate(growPages);
assert(oldPages !== -1, "wasm_memory_grow_and_relocate failed (returned -1)");

const newBase = runtime.memory.buffer.byteLength;
const expectedNewBase = oldBase + growPages * 65536;
assert(newBase === expectedNewBase, `unexpected new memory size: got=${newBase} expected=${expectedNewBase}`);
assert(kernel.instance.exports.wasm_get_cstack_pointer() === newBase, "unexpected cstack SP after relocate");

const newLow = newBase - cstackSize;
{
  const u8 = new Uint8Array(runtime.memory.buffer);
  const got = u8.slice(newLow, newLow + sentinel.length);
  const ok = got.length === sentinel.length && got.every((b, i) => b === sentinel[i]);
  assert(ok, "cstack relocation sentinel mismatch");
}

// Ensure subprim dispatch still works after relocation.
kernel.instance.exports.wasm_call_subprim_fixnum(unused1Fixnum);

// --- 3) Bug/Fatal logging hook ---
logs.length = 0;
const plusIndex = subprimsMap.symbols.indexOf("_SPbuiltin_plus");
assert(plusIndex >= 0, "subprims map missing _SPbuiltin_plus");
let bugTrapped = false;
try {
  kernel.instance.exports.wasm_call_subprim_fixnum(plusIndex << fixnumShift);
} catch (_e) {
  bugTrapped = true;
}
assert(bugTrapped, "expected trap from unimplemented subprim");
const logText = logs.join("");
assert(logText.includes("WASM subprim not implemented"), "missing Bug() log output");
assert(logText.includes("_SPbuiltin_plus"), "Bug() output missing subprim name");

console.log("PASS: wasm32 smoke test");
