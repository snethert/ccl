/*
 * WASM32 fixnum overflow smoke test.
 */

import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";

import {
  createCclImports,
  createSharedCclRuntime,
  installCompiledModulesFromRegistry,
  installSubprimsTable,
  instantiateWasm,
} from "./ccl-loader.mjs";
import { createMicrokernel } from "./microkernel.mjs";
import {
  FULLTAGMASK as FULLTAG_MASK,
  FULLTAG_MISC,
  SUBTAG_MASK,
  SUBTAG_BIGNUM,
  NUM_SUBTAG_BITS,
} from "./abi-constants.mjs";
import path from "node:path";
import { ensureSubprimsMap } from "../lib/ensure-subprims-map.mjs";

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

const kernelUrl = new URL("../../../build/wasm32/kernel/wasmcl.wasm", import.meta.url);
const subprimsUrl = new URL("../../../build/wasm32/subprims/subprims.wasm", import.meta.url);
const imageUrl = new URL("../../../build/wasm32/images/minimal.image", import.meta.url);

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
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const subprimsMap = await ensureSubprimsMap(repoRoot);
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

assert(typeof kernel.instance.exports.wasm_test_entry_funcall2 === "function", "missing wasm_test_entry_funcall2 export");

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

const { installed, entries } = await installCompiledModulesFromRegistry({
  kernel: kernel.instance.exports,
  memory: runtime.memory,
  subprimsTable: runtime.subprimsTable,
  microkernel,
});
assert(installed > 0, "no compiled modules installed");

function ensureEntry(entryIndex) {
  const entry = entries.find((item) => item.entryIndex === entryIndex);
  assert(entry, `missing compiled module entry ${entryIndex}`);
}

ensureEntry(204);
ensureEntry(205);
ensureEntry(207);
ensureEntry(212);

const fixnumShift = 2;
const fixnumBits = 32 - fixnumShift;
const maxFixnum = (1 << (fixnumBits - 1)) - 1;
const minFixnum = -1 << (fixnumBits - 1);

function readU32(mem, addr) {
  return new DataView(mem.buffer).getUint32(addr >>> 0, true);
}

function bignumToBigInt(mem, obj, label) {
  assert((obj & FULLTAG_MASK) === FULLTAG_MISC, `${label}: expected bignum tag`);
  const headerAddr = (obj - FULLTAG_MISC) >>> 0;
  const header = readU32(mem, headerAddr);
  const subtag = header & SUBTAG_MASK;
  const count = header >>> NUM_SUBTAG_BITS;
  assert(subtag === SUBTAG_BIGNUM, `${label}: unexpected subtag ${subtag}`);
  assert(count > 0, `${label}: invalid bignum length ${count}`);
  let value = 0n;
  for (let i = 0; i < count; i++) {
    const digit = BigInt(readU32(mem, headerAddr + 4 + i * 4));
    value += digit << (32n * BigInt(i));
  }
  const msd = readU32(mem, headerAddr + 4 + (count - 1) * 4);
  if (msd & 0x80000000) {
    value -= 1n << (32n * BigInt(count));
  }
  return value;
}

function assertBignum(mem, obj, expected, label) {
  const actual = bignumToBigInt(mem, obj, label);
  const expectedValue = BigInt(expected);
  assert(actual === expectedValue, `${label}: unexpected bignum value ${actual} expected ${expectedValue}`);
}

const addMax = kernel.instance.exports.wasm_test_entry_funcall2(204, maxFixnum, 0) >> 2;
assert(addMax === maxFixnum, `unexpected max add result: got=${addMax} expected=${maxFixnum}`);

const subMin = kernel.instance.exports.wasm_test_entry_funcall2(205, minFixnum, 0) >> 2;
assert(subMin === minFixnum, `unexpected min sub result: got=${subMin} expected=${minFixnum}`);

const negResult = kernel.instance.exports.wasm_test_entry_funcall1_raw(212, 5 << 2) >> 2;
assert(negResult === -5, `unexpected neg result: got=${negResult} expected=-5`);

const addOverflow = kernel.instance.exports.wasm_test_entry_funcall2(204, maxFixnum, 1) >>> 0;
assertBignum(runtime.memory, addOverflow, maxFixnum + 1, "add overflow");

const subOverflow = kernel.instance.exports.wasm_test_entry_funcall2(205, minFixnum, 1) >>> 0;
assertBignum(runtime.memory, subOverflow, minFixnum - 1, "sub overflow");

const negOverflow = kernel.instance.exports.wasm_test_entry_funcall1_raw(212, minFixnum << 2) >>> 0;
assertBignum(runtime.memory, negOverflow, -minFixnum, "neg overflow");

const ashOverflow = kernel.instance.exports.wasm_test_entry_funcall2(207, 1, 70) >>> 0;
assertBignum(runtime.memory, ashOverflow, 1n << 70n, "ash overflow");

const ashNegOverflow = kernel.instance.exports.wasm_test_entry_funcall2(207, -1, 40) >>> 0;
assertBignum(runtime.memory, ashNegOverflow, -1n << 40n, "ash negative overflow");

console.log("PASS: wasm fixnum overflow smoke test");
