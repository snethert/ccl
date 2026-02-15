/*
 * WASM32 multiple-value-call + unwind-protect MV smoke test.
 *
 * Validates:
 *  1) _SPsave_values/_SPadd_values/_SPrecover_values preserve MV order
 *  2) unwind-protect-style cleanup does not clobber saved MV sets
 *  3) wasm_get_nargs reflects reconstructed MV count
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
const subprimsUrl = new URL("./subprims.wasm", import.meta.url);
const subprimsMapUrl = new URL("../../../build/wasm32/subprims-map.json", import.meta.url);
const imageUrl = new URL("../minimal.image", import.meta.url);

const runtime = createSharedCclRuntime({
  memoryInitialPages: 256,
  subprimsTableInitial: 256,
});

const microkernel = createMicrokernel({
  memory: runtime.memory,
  writeStdout: () => {},
  writeStderr: () => {},
});

const kernelBytes = await readFileUrl(kernelUrl);
const kernel = await instantiateWasm(
  kernelBytes,
  createCclImports({
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel,
  }),
);

const subprimsBytes = await readFileUrl(subprimsUrl);
const subprimsMap = JSON.parse((await readFileUrl(subprimsMapUrl)).toString("utf8"));
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

assert(typeof kernel.instance.exports.wasm_set_subprims_ready === "function", "missing wasm_set_subprims_ready export");
kernel.instance.exports.wasm_set_subprims_ready(1);

const canRun = typeof subprims.instance.exports._SPsave_values === "function";
if (!canRun) {
  console.log("SKIP: mvcall smoke test (subprims.wasm missing _SPsave_values)");
} else {
  assert(typeof kernel.instance.exports.wasm_call_subprim_fixnum === "function", "missing wasm_call_subprim_fixnum export");
  assert(typeof kernel.instance.exports.wasm_set_arg_z === "function", "missing wasm_set_arg_z export");
  assert(typeof kernel.instance.exports.wasm_set_nargs === "function", "missing wasm_set_nargs export");
  const getNargs = kernel.instance.exports.wasm_get_nargs ?? null;
  assert(typeof kernel.instance.exports.wasm_get_mv === "function", "missing wasm_get_mv export");
  assert(typeof kernel.instance.exports.wasm_restore_vsp === "function", "missing wasm_restore_vsp export");
  assert(typeof kernel.instance.exports.wasm_return_values2 === "function", "missing wasm_return_values2 export");
  assert(typeof kernel.instance.exports.wasm_return_values3 === "function", "missing wasm_return_values3 export");
  assert(typeof kernel.instance.exports.wasm_return_values4 === "function", "missing wasm_return_values4 export");

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

assert(typeof kernel.instance.exports.wasm_set_cstack_bounds === "function", "missing wasm_set_cstack_bounds export");
const cstackBase = runtime.memory.buffer.byteLength;
kernel.instance.exports.wasm_set_cstack_bounds(cstackBase, cstackSize);

const blobBase = (cstackBase - cstackSize - imageLen) & ~15;
assert(blobBase >= 0, "not enough memory to place boot image below cstack");
new Uint8Array(runtime.memory.buffer).set(imageBytes, blobBase);

assert(typeof kernel.instance.exports.wasm_ccl_load_image === "function", "missing wasm_ccl_load_image export");
kernel.instance.exports.wasm_ccl_load_image(blobBase, imageLen);

const fixnumShift = 2;
const nilValue = kernel.instance.exports.wasm_get_lisp_nil() >>> 0;

function fixnum(n) {
  return (n << fixnumShift) >>> 0;
}

function setValues(values) {
  if (values.length === 0) {
    kernel.instance.exports.wasm_set_arg_z(nilValue);
    kernel.instance.exports.wasm_set_nargs(0);
    return;
  }
  if (values.length === 1) {
    kernel.instance.exports.wasm_set_arg_z(values[0]);
    kernel.instance.exports.wasm_set_nargs(1);
    return;
  }
  if (values.length === 2) {
    kernel.instance.exports.wasm_return_values2(values[0], values[1]);
    return;
  }
  if (values.length === 3) {
    kernel.instance.exports.wasm_return_values3(values[0], values[1], values[2]);
    return;
  }
  if (values.length === 4) {
    kernel.instance.exports.wasm_return_values4(values[0], values[1], values[2], values[3]);
    return;
  }
  fail(`setValues does not support ${values.length} values`);
}

function subprimIndex(name) {
  const idx = subprimsMap.symbols.indexOf(name);
  assert(idx >= 0, `missing ${name} in subprims map`);
  return idx;
}

const saveIndex = subprimIndex("_SPsave_values");
const addIndex = subprimIndex("_SPadd_values");
const recoverIndex = subprimIndex("_SPrecover_values");

const saveFixnum = fixnum(saveIndex);
const addFixnum = fixnum(addIndex);
const recoverFixnum = fixnum(recoverIndex);

// Multi-form multiple-value-call: accumulate values from two forms.
const firstValues = [fixnum(10), fixnum(20), fixnum(30)];
const secondValues = [fixnum(40), fixnum(50)];
const combined = [...firstValues, ...secondValues];

setValues(firstValues);
kernel.instance.exports.wasm_call_subprim_fixnum(saveFixnum);

setValues(secondValues);
kernel.instance.exports.wasm_call_subprim_fixnum(addFixnum);

kernel.instance.exports.wasm_call_subprim_fixnum(recoverFixnum);
if (getNargs) {
  const totalNargs = getNargs() >>> 0;
  assert(totalNargs === combined.length, `unexpected nargs after recover: got=${totalNargs} expected=${combined.length}`);
}
for (let i = 0; i < combined.length; i++) {
  const got = kernel.instance.exports.wasm_get_mv(i) >>> 0;
  assert(got === combined[i], `mv[${i}] mismatch: got=0x${got.toString(16)} expected=0x${combined[i].toString(16)}`);
}
const mvPast = kernel.instance.exports.wasm_get_mv(combined.length) >>> 0;
assert(mvPast === nilValue, "mv beyond count should be NIL");

kernel.instance.exports.wasm_restore_vsp();

// Unwind-protect style: cleanup clobbers arg_z/nargs, recover restores original MV set.
const protectedValues = [fixnum(11), fixnum(22), fixnum(33), fixnum(44)];

setValues(protectedValues);
kernel.instance.exports.wasm_call_subprim_fixnum(saveFixnum);

// Simulated cleanup clobbering values.
setValues([fixnum(777), fixnum(999)]);

kernel.instance.exports.wasm_call_subprim_fixnum(recoverFixnum);
if (getNargs) {
  const protectedNargs = getNargs() >>> 0;
  assert(
    protectedNargs === protectedValues.length,
    `unexpected nargs after unwind-protect recover: got=${protectedNargs} expected=${protectedValues.length}`,
  );
}
for (let i = 0; i < protectedValues.length; i++) {
  const got = kernel.instance.exports.wasm_get_mv(i) >>> 0;
  assert(got === protectedValues[i], `unwind mv[${i}] mismatch: got=0x${got.toString(16)} expected=0x${protectedValues[i].toString(16)}`);
}

kernel.instance.exports.wasm_restore_vsp();

console.log("PASS: wasm multiple-value-call/unwind-protect smoke test");
}
