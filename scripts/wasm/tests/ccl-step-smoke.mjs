/*
 * Stage-2 stepping smoke test (wasm_ccl_step).
 *
 * Drives the exported stepping API from doc/wasm/yield-resume.md against a
 * minimal image, ensuring the toplevel loop can exit cleanly.
 */

import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { WASM_BOOT_ENTRY_INDEX } from "./abi-constants.mjs";
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

const kernelUrl = new URL("../../../build/wasm32/kernel/wasmcl.wasm", import.meta.url);
const kernelBytes = await readFileUrl(kernelUrl);

const imageUrl = new URL("../../../build/wasm32/images/minimal.image", import.meta.url);
const imageBytes = await readFileUrl(imageUrl);
const imageLen = imageBytes.byteLength >>> 0;

const subprimsUrl = new URL("../../../build/wasm32/subprims/subprims.wasm", import.meta.url);
const subprimsBytes = await readFileUrl(subprimsUrl);
const subprimsMapUrl = new URL("../../../build/wasm32/subprims-map.json", import.meta.url);
const subprimsMap = JSON.parse(await fs.readFile(fileURLToPath(subprimsMapUrl), "utf-8"));

const runtime = createSharedCclRuntime({
  memoryInitialPages: 256,
  subprimsTableInitial: 256,
  createMemory: true,
});

const stdoutChunks = [];
const microkernel = createMicrokernel({
  memory: runtime.memory,
  asyncStdin: true,
  writeStdout: (bytes) => stdoutChunks.push(new Uint8Array(bytes)),
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

const bootIndex = WASM_BOOT_ENTRY_INDEX;
assert(typeof ex.wasm_boot_entry === "function", "missing wasm_boot_entry export");
if (runtime.subprimsTable.length <= bootIndex) {
  runtime.subprimsTable.grow(bootIndex - runtime.subprimsTable.length + 1);
}
runtime.subprimsTable.set(bootIndex, ex.wasm_boot_entry);

assert(typeof ex.wasm_ccl_init === "function", "missing wasm_ccl_init export");
assert(typeof ex.wasm_ccl_step === "function", "missing wasm_ccl_step export");
assert(typeof ex.wasm_ccl_blocked_request_id === "function", "missing wasm_ccl_blocked_request_id export");
assert(typeof ex.wasm_ccl_exit_code === "function", "missing wasm_ccl_exit_code export");
assert(typeof ex.wasm_ccl_last_error === "function", "missing wasm_ccl_last_error export");

const initr = ex.wasm_ccl_init() | 0;
assert(initr === 0, `expected init success, got ${initr}`);

const st = ex.wasm_ccl_step(0) | 0;
if (st === STEP_EXITED) {
  assert((ex.wasm_ccl_exit_code() | 0) === 0, "expected exit code 0");
  assert((ex.wasm_ccl_last_error() | 0) === 0, "expected no trapped error");
  assert((ex.wasm_ccl_blocked_request_id() >>> 0) === 0, "expected no blocked request id");
} else if (st === STEP_BLOCKED) {
  const blocked = ex.wasm_ccl_blocked_request_id() >>> 0;
  assert((ex.wasm_ccl_last_error() | 0) === 0, "expected no trapped error");
  if (blocked !== 0) {
    const input = new TextEncoder().encode("hello\n");
    microkernel.feedStdin(input);
    let next = ex.wasm_ccl_step(0) | 0;
    assert(next === STEP_RUNNING || next === STEP_BLOCKED, `unexpected step after stdin feed: ${next}`);
    next = ex.wasm_ccl_step(0) | 0;
    if (next === STEP_BLOCKED) {
      microkernel.closeStdin();
      next = ex.wasm_ccl_step(0) | 0;
    }
    assert(next === STEP_EXITED, `expected exit after stdin close, got ${next}`);
    const out = Buffer.concat(stdoutChunks.map((u8) => Buffer.from(u8)));
    assert(out.toString("utf8") === "hello\n", `unexpected stdout: ${JSON.stringify(out.toString("utf8"))}`);
  }
} else {
  fail(`unexpected step status ${st}`);
}

console.log("PASS: wasm_ccl_step smoke test");
