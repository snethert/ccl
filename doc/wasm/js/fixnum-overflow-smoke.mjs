/*
 * WASM32 fixnum overflow smoke test.
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

function assertTrap(fn, msg) {
  let trapped = false;
  try {
    fn();
  } catch (err) {
    trapped = true;
  }
  assert(trapped, msg);
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

function buildCallModule(importName, exportName) {
  const out = [];
  out.push(0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00);

  const types = [];
  pushUleb(types, 1);
  pushU8(types, 0x60);
  pushUleb(types, 0);
  pushUleb(types, 0);

  const imports = [];
  pushUleb(imports, 1);
  pushString(imports, "ccl");
  pushString(imports, importName);
  pushU8(imports, 0x00);
  pushUleb(imports, 0);

  const funcs = [];
  pushUleb(funcs, 1);
  pushUleb(funcs, 0);

  const exports = [];
  pushUleb(exports, 1);
  pushString(exports, exportName);
  pushU8(exports, 0x00);
  pushUleb(exports, 1);

  const code = [];
  const body = [];
  pushUleb(body, 0);
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

assert(typeof kernel.instance.exports.wasm_test_entry_funcall2 === "function", "missing wasm_test_entry_funcall2 export");
assert(typeof kernel.instance.exports.wasm_return_fixnum_neg === "function", "missing wasm_return_fixnum_neg export");

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

function installOp(entryIndex, importName, exportName, helper) {
  const moduleBytes = buildCallModule(importName, exportName);
  return instantiateWasm(moduleBytes, { ccl: { [importName]: helper } }).then((mod) => {
    if (runtime.subprimsTable.length <= entryIndex) {
      runtime.subprimsTable.grow(entryIndex - runtime.subprimsTable.length + 1);
    }
    runtime.subprimsTable.set(entryIndex, mod.instance.exports[exportName]);
  });
}

await installOp(
  204,
  "wasm_return_fixnum_add",
  "ccl_fixnum_add_entry",
  kernel.instance.exports.wasm_return_fixnum_add,
);

await installOp(
  205,
  "wasm_return_fixnum_sub",
  "ccl_fixnum_sub_entry",
  kernel.instance.exports.wasm_return_fixnum_sub,
);

await installOp(
  212,
  "wasm_return_fixnum_neg",
  "ccl_fixnum_neg_entry",
  kernel.instance.exports.wasm_return_fixnum_neg,
);

const fixnumShift = 2;
const fixnumBits = 32 - fixnumShift;
const maxFixnum = (1 << (fixnumBits - 1)) - 1;
const minFixnum = -1 << (fixnumBits - 1);

const addMax = kernel.instance.exports.wasm_test_entry_funcall2(204, maxFixnum, 0) >> 2;
assert(addMax === maxFixnum, `unexpected max add result: got=${addMax} expected=${maxFixnum}`);

const subMin = kernel.instance.exports.wasm_test_entry_funcall2(205, minFixnum, 0) >> 2;
assert(subMin === minFixnum, `unexpected min sub result: got=${subMin} expected=${minFixnum}`);

const negResult = kernel.instance.exports.wasm_test_entry_funcall2(212, 5, 0) >> 2;
assert(negResult === -5, `unexpected neg result: got=${negResult} expected=-5`);

assertTrap(
  () => kernel.instance.exports.wasm_test_entry_funcall2(204, maxFixnum, 1),
  "expected add overflow trap",
);

assertTrap(
  () => kernel.instance.exports.wasm_test_entry_funcall2(205, minFixnum, 1),
  "expected sub overflow trap",
);

assertTrap(
  () => kernel.instance.exports.wasm_test_entry_funcall2(212, minFixnum, 0),
  "expected neg overflow trap",
);

console.log("PASS: wasm fixnum overflow smoke test");
