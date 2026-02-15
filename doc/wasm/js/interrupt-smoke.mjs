/*
 * Interrupt smoke test (baseline, cooperative).
 *
 * This is a minimal end-to-end harness that:
 *  - instantiates the kernel,
 *  - calls the microkernel interrupt request hook,
 *  - steps the runner once to ensure no trap,
 *  - asserts the pending flag is cleared after delivery (when wired).
 */

import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { createMicrokernel } from "./microkernel.mjs";
import {
  createCclImports,
  createSharedCclRuntime,
  instantiateWasm,
  installCompiledModulesFromRegistry,
  installSubprimsTable,
} from "./ccl-loader.mjs";

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

const STEP_RUNNING = 0;
const STEP_BLOCKED = 1;
const STEP_EXITED = 2;
const STEP_TRAPPED = 3;

const kernelUrl = new URL("./wasmcl.wasm", import.meta.url);
const kernelBytes = await readFileUrl(kernelUrl);

const imageUrl = new URL("../minimal.image", import.meta.url);
const imageBytes = await readFileUrl(imageUrl);
const imageLen = imageBytes.byteLength >>> 0;

const subprimsUrl = new URL("./subprims.wasm", import.meta.url);
const subprimsBytes = await readFileUrl(subprimsUrl);
const subprimsMapUrl = new URL("../../../build/wasm32/subprims-map.json", import.meta.url);
const subprimsMap = JSON.parse(await fs.readFile(fileURLToPath(subprimsMapUrl), "utf-8"));

const runtime = createSharedCclRuntime({
  memoryInitialPages: 256,
  subprimsTableInitial: 256,
  createMemory: true,
});

const microkernel = createMicrokernel({
  memory: runtime.memory,
  asyncStdin: false,
  writeStdout: () => {},
  writeStderr: () => {},
});

const kernel = await instantiateWasm(
  kernelBytes,
  createCclImports({
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel,
  }),
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
  providers: [{ exports: kernel.instance.exports }, { exports: subprims.instance.exports }],
});

if (typeof kernel.instance.exports.wasm_set_subprims_ready === "function") {
  kernel.instance.exports.wasm_set_subprims_ready(1);
}

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

const ex = kernel.instance.exports;
assert(typeof ex.wasm_set_cstack_bounds === "function", "missing wasm_set_cstack_bounds export");
const cstackBase = runtime.memory.buffer.byteLength;
ex.wasm_set_cstack_bounds(cstackBase, cstackSize);

const blobBase = (cstackBase - cstackSize - imageLen) & ~15;
assert(blobBase >= 0, "not enough memory to place boot image below cstack");
new Uint8Array(runtime.memory.buffer).set(imageBytes, blobBase);

assert(typeof ex.wasm_ccl_load_image === "function", "missing wasm_ccl_load_image export");
ex.wasm_ccl_load_image(blobBase, imageLen);

await installCompiledModulesFromRegistry({
  kernel: ex,
  memory: runtime.memory,
  subprimsTable: runtime.subprimsTable,
  microkernel,
});

const bootIndex = 200;
assert(typeof ex.wasm_boot_entry === "function", "missing wasm_boot_entry export");
if (runtime.subprimsTable.length <= bootIndex) {
  runtime.subprimsTable.grow(bootIndex - runtime.subprimsTable.length + 1);
}
runtime.subprimsTable.set(bootIndex, ex.wasm_boot_entry);

assert(typeof ex.wasm_ccl_init === "function", "missing wasm_ccl_init export");
assert(typeof ex.wasm_ccl_step === "function", "missing wasm_ccl_step export");
assert(typeof ex.wasm_get_current_tcr === "function", "missing wasm_get_current_tcr export");
assert(typeof ex.wasm_get_interrupt_pending_tcr === "function", "missing wasm_get_interrupt_pending_tcr export");

const initr = ex.wasm_ccl_init() | 0;
assert(initr === 0, `expected init success, got ${initr}`);

const interruptRequested = microkernel.requestInterrupt({
  exports: kernel.instance.exports,
  reason: "smoke",
});
if (!interruptRequested) {
  console.log("SKIP: interrupt delivery not wired yet (requestInterrupt returned false)");
}

const st = ex.wasm_ccl_step(0) | 0;
if (st === STEP_TRAPPED) {
  const last = typeof ex.wasm_ccl_last_error === "function" ? (ex.wasm_ccl_last_error() | 0) : 0;
  fail(`unexpected trap status ${st} (last_error=${last})`);
} else if (st === STEP_EXITED) {
  console.log("PASS: interrupt smoke test (runner exited cleanly)");
} else if (st === STEP_BLOCKED || st === STEP_RUNNING) {
  console.log("PASS: interrupt smoke test (runner stepped without trap)");
} else {
  fail(`unexpected step status ${st}`);
}

if (interruptRequested) {
  const tcr = ex.wasm_get_current_tcr() >>> 0;
  const pending = ex.wasm_get_interrupt_pending_tcr(tcr) | 0;
  assert(pending === 0, `expected interrupt_pending cleared, got ${pending}`);
}
