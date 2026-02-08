/*
 * WASM32 compiler emission smoke test.
 *
 * Validates:
 *  1) Host CCL emits real WASM modules for basic forms.
 *  2) JS loader installs compiled modules into the shared table.
 *  3) Basic forms execute end-to-end (constants, fixnum ops, control flow, FFI).
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
const subprimsMapUrl = new URL("../subprims-map.json", import.meta.url);
const imageUrl = new URL("../minimal.image", import.meta.url);
const bundleUrl = new URL("../wasm-smoke-modules.json", import.meta.url);

let bundle;
let bundleBinaryBytes;
let bundleIndexBytes;
try {
  bundle = JSON.parse((await readFileUrl(bundleUrl)).toString("utf8"));
  if (bundle?.format !== "ccl-wasm-modules-v2") {
    fail("wasm-smoke-modules.json must be ccl-wasm-modules-v2");
  }
  if (typeof bundle?.binary !== "string" || bundle.binary.length === 0) {
    fail("wasm-smoke-modules.json missing binary field");
  }
  if (typeof bundle?.index !== "string" || bundle.index.length === 0) {
    fail("wasm-smoke-modules.json missing index field");
  }
  const bundleDir = path.dirname(fileURLToPath(bundleUrl));
  bundleBinaryBytes = await fs.readFile(path.resolve(bundleDir, bundle.binary));
  bundleIndexBytes = await fs.readFile(path.resolve(bundleDir, bundle.index));
} catch (err) {
  fail(`missing or invalid wasm-smoke-modules bundle (run scripts/wasm/compile-smoke-modules.sh): ${err?.message ?? err}`);
}

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

const kernelExports = kernel.instance.exports;
assert(typeof kernelExports.wasm_get_lisp_nil === "function", "missing wasm_get_lisp_nil export");
const nilValue = kernelExports.wasm_get_lisp_nil() >>> 0;
const functions = Array.isArray(bundle.functions) ? bundle.functions : [];

async function installBundle(label) {
  const { installed, count, failed } = await installCompiledModulesFromBundle({
    bundle,
    binaryBytes: bundleBinaryBytes,
    indexBytes: bundleIndexBytes,
    kernel,
    memory: runtime.memory,
    subprimsTable: runtime.subprimsTable,
    microkernel,
    strict: true,
    installConstPools: true,
  });
  if (count === 0 || installed === 0) {
    fail(`no compiled modules installed from bundle (${label})`);
  }
  if (failed) {
    fail(`compiled modules failed during install (${label}): ${failed}`);
  }
  return installed;
}

await installBundle("initial");

function entryIndex(name) {
  const item = functions.find((fn) => fn.name === name);
  assert(item, `missing compiled function ${name}`);
  return item.entryIndex >>> 0;
}

assert(typeof kernelExports.wasm_test_entry_funcall === "function", "missing wasm_test_entry_funcall export");
assert(typeof kernelExports.wasm_test_entry_funcall2 === "function", "missing wasm_test_entry_funcall2 export");
assert(typeof kernelExports.wasm_test_entry_funcall1_raw === "function", "missing wasm_test_entry_funcall1_raw export");

const fixnumShift = 2;
function fixnum(n) {
  return (n << fixnumShift) >>> 0;
}

const constEntry = entryIndex("WASM-SMOKE-CONST");
const constResult = kernelExports.wasm_test_entry_funcall(constEntry, 0) >> 2;
assert(constResult === 23, `unexpected const result: got=${constResult} expected=23`);

const symbolEntry = entryIndex("WASM-SMOKE-SYMBOL");
const symbolResult = kernelExports.wasm_test_entry_funcall(symbolEntry, 0) >>> 0;
assert(symbolResult !== nilValue, "unexpected symbol result: got NIL");

const ffiEntry = entryIndex("WASM-SMOKE-FFI-ADD");
const ffiResult = kernelExports.wasm_test_entry_funcall2(ffiEntry, 10, 32) >> 2;
assert(ffiResult === 42, `unexpected ffi-add result: got=${ffiResult} expected=42`);

const addEntry = entryIndex("WASM-SMOKE-ADD");
const addResult = kernelExports.wasm_test_entry_funcall2(addEntry, 10, 32) >> 2;
assert(addResult === 42, `unexpected add result: got=${addResult} expected=42`);

const subEntry = entryIndex("WASM-SMOKE-SUB");
const subResult = kernelExports.wasm_test_entry_funcall2(subEntry, 50, 8) >> 2;
assert(subResult === 42, `unexpected sub result: got=${subResult} expected=42`);

const mulEntry = entryIndex("WASM-SMOKE-MUL");
const mulResult = kernelExports.wasm_test_entry_funcall2(mulEntry, 6, 7) >> 2;
assert(mulResult === 42, `unexpected mul result: got=${mulResult} expected=42`);

const ashEntry = entryIndex("WASM-SMOKE-ASH");
const ashLeft = kernelExports.wasm_test_entry_funcall2(ashEntry, 3, 2) >> 2;
assert(ashLeft === 12, `unexpected ash left result: got=${ashLeft} expected=12`);

const logandEntry = entryIndex("WASM-SMOKE-LOGAND");
const logandResult = kernelExports.wasm_test_entry_funcall2(logandEntry, 6, 3) >> 2;
assert(logandResult === (6 & 3), `unexpected logand result: got=${logandResult} expected=${6 & 3}`);

const logiorEntry = entryIndex("WASM-SMOKE-LOGIOR");
const logiorResult = kernelExports.wasm_test_entry_funcall2(logiorEntry, 6, 3) >> 2;
assert(logiorResult === (6 | 3), `unexpected logior result: got=${logiorResult} expected=${6 | 3}`);

const logxorEntry = entryIndex("WASM-SMOKE-LOGXOR");
const logxorResult = kernelExports.wasm_test_entry_funcall2(logxorEntry, 6, 3) >> 2;
assert(logxorResult === (6 ^ 3), `unexpected logxor result: got=${logxorResult} expected=${6 ^ 3}`);

const lognotEntry = entryIndex("WASM-SMOKE-LOGNOT");
const lognotResult = kernelExports.wasm_test_entry_funcall1_raw(lognotEntry, fixnum(5)) >> 2;
assert(lognotResult === ~5, `unexpected lognot result: got=${lognotResult} expected=${~5}`);

const negEntry = entryIndex("WASM-SMOKE-NEG");
const negResult = kernelExports.wasm_test_entry_funcall1_raw(negEntry, fixnum(7)) >> 2;
assert(negResult === -7, `unexpected neg result: got=${negResult} expected=-7`);

const ifEntry = entryIndex("WASM-SMOKE-IF");
const ifTrue = kernelExports.wasm_test_entry_funcall1_raw(ifEntry, fixnum(1)) >> 2;
assert(ifTrue === 11, `unexpected if true result: got=${ifTrue} expected=11`);
const ifFalse = kernelExports.wasm_test_entry_funcall1_raw(ifEntry, nilValue);
assert(ifFalse === fixnum(22), `unexpected if false result: got=0x${ifFalse.toString(16)} expected=0x${fixnum(22).toString(16)}`);

const ifArgEntry = entryIndex("WASM-SMOKE-IF-ARG");
const ifArgTrue = kernelExports.wasm_test_entry_funcall1_raw(ifArgEntry, fixnum(9));
assert(ifArgTrue === fixnum(9), `unexpected if-arg true result: got=0x${ifArgTrue.toString(16)} expected=0x${fixnum(9).toString(16)}`);
const ifArgFalse = kernelExports.wasm_test_entry_funcall1_raw(ifArgEntry, nilValue);
assert(ifArgFalse === fixnum(17), `unexpected if-arg false result: got=0x${ifArgFalse.toString(16)} expected=0x${fixnum(17).toString(16)}`);

const identityEntry = entryIndex("WASM-SMOKE-IDENTITY");
const identResult = kernelExports.wasm_test_entry_funcall1_raw(identityEntry, fixnum(101));
assert(identResult === fixnum(101), `unexpected identity result: got=0x${identResult.toString(16)} expected=0x${fixnum(101).toString(16)}`);

const identityYEntry = entryIndex("WASM-SMOKE-IDENTITY-Y");
const identYResult = kernelExports.wasm_test_entry_funcall2(identityYEntry, 7, 42);
assert(identYResult === fixnum(42), `unexpected identity-y result: got=0x${identYResult.toString(16)} expected=0x${fixnum(42).toString(16)}`);

const blockEntry = entryIndex("WASM-SMOKE-BLOCK");
const blockTrue = kernelExports.wasm_test_entry_funcall1_raw(blockEntry, fixnum(1)) >> 2;
assert(blockTrue === 7, `unexpected block true result: got=${blockTrue} expected=7`);
const blockFalse = kernelExports.wasm_test_entry_funcall1_raw(blockEntry, nilValue) >> 2;
assert(blockFalse === 9, `unexpected block false result: got=${blockFalse} expected=9`);

const tagbodyEntry = entryIndex("WASM-SMOKE-TAGBODY");
const tagbodyTrue = kernelExports.wasm_test_entry_funcall1_raw(tagbodyEntry, fixnum(1)) >> 2;
assert(tagbodyTrue === 1, `unexpected tagbody true result: got=${tagbodyTrue} expected=1`);
const tagbodyFalse = kernelExports.wasm_test_entry_funcall1_raw(tagbodyEntry, nilValue) >> 2;
assert(tagbodyFalse === 2, `unexpected tagbody false result: got=${tagbodyFalse} expected=2`);

const mvcallEntry = entryIndex("WASM-SMOKE-MVCALL");
const mvcallResult = kernelExports.wasm_test_entry_funcall(mvcallEntry, 0) >> 2;
assert(mvcallResult === 42, `unexpected mvcall result: got=${mvcallResult} expected=42`);

await installBundle("reload");
const symbolReload = kernelExports.wasm_test_entry_funcall(symbolEntry, 0) >>> 0;
assert(symbolReload === symbolResult, "symbol identity changed across reload");

console.log("PASS: wasm compiler emission smoke test");
