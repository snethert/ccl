/*
 * WASM32 constant module smoke test.
 *
 * Validates:
 *  1) Minimal const module emitter shape (i32.const -> wasm_return_constant)
 *  2) _SPfuncall dispatch through table entry to a compiled module
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

function pushU8(buf, byte) {
  buf.push(byte & 0xff);
}

function pushUleb(buf, value) {
  let v = value >>> 0;
  do {
    let byte = v & 0x7f;
    v >>>= 7;
    if (v !== 0) byte |= 0x80;
    pushU8(buf, byte);
  } while (v !== 0);
}

function pushSleb32(buf, value) {
  let v = value | 0;
  while (true) {
    let byte = v & 0x7f;
    v >>= 7;
    const signBit = byte & 0x40;
    const done = (v === 0 && signBit === 0) || (v === -1 && signBit !== 0);
    if (!done) byte |= 0x80;
    pushU8(buf, byte);
    if (done) break;
  }
}

function pushString(buf, str) {
  pushUleb(buf, str.length);
  for (let i = 0; i < str.length; i++) {
    pushU8(buf, str.charCodeAt(i));
  }
}

function section(id, contents) {
  const out = [];
  pushU8(out, id);
  pushUleb(out, contents.length);
  out.push(...contents);
  return out;
}

function buildConstModule(constValue) {
  const out = [];
  out.push(0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00);

  const types = [];
  pushUleb(types, 2);
  pushU8(types, 0x60);
  pushUleb(types, 1);
  pushU8(types, 0x7f);
  pushUleb(types, 0);
  pushU8(types, 0x60);
  pushUleb(types, 0);
  pushUleb(types, 0);

  const imports = [];
  pushUleb(imports, 1);
  pushString(imports, "ccl");
  pushString(imports, "wasm_return_constant");
  pushU8(imports, 0x00);
  pushUleb(imports, 0);

  const funcs = [];
  pushUleb(funcs, 1);
  pushUleb(funcs, 1);

  const exports = [];
  pushUleb(exports, 1);
  pushString(exports, "ccl_const_entry");
  pushU8(exports, 0x00);
  pushUleb(exports, 1);

  const code = [];
  const body = [];
  pushUleb(body, 0);
  pushU8(body, 0x41);
  pushSleb32(body, constValue);
  pushU8(body, 0x10);
  pushUleb(body, 0);
  pushU8(body, 0x0b);
  pushUleb(code, 1);
  pushUleb(code, body.length);
  code.push(...body);

  out.push(...section(1, types));
  out.push(...section(2, imports));
  out.push(...section(3, funcs));
  out.push(...section(7, exports));
  out.push(...section(10, code));

  return new Uint8Array(out);
}

const kernelUrl = new URL("./wasmcl.wasm", import.meta.url);
const subprimsUrl = new URL("./subprims.wasm", import.meta.url);
const subprimsMapUrl = new URL("../subprims-map.json", import.meta.url);
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

assert(typeof kernel.instance.exports.wasm_return_constant === "function", "missing wasm_return_constant export");
assert(typeof kernel.instance.exports.wasm_test_entry_funcall === "function", "missing wasm_test_entry_funcall export");

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

const entryIndex = 203;
const value = 23;
const constValue = value << 2;
const moduleBytes = buildConstModule(constValue);
const constModule = await instantiateWasm(moduleBytes, {
  ccl: { wasm_return_constant: kernel.instance.exports.wasm_return_constant },
});

if (runtime.subprimsTable.length <= entryIndex) {
  runtime.subprimsTable.grow(entryIndex - runtime.subprimsTable.length + 1);
}
runtime.subprimsTable.set(entryIndex, constModule.instance.exports.ccl_const_entry);

const result = kernel.instance.exports.wasm_test_entry_funcall(entryIndex, value) >>> 0;
const resultFixnum = result >> 2;
assert(resultFixnum === value, `unexpected const module result: got=${resultFixnum} expected=${value}`);

console.log("PASS: wasm const module smoke test");
