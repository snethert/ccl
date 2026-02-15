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

function escapeRegexPattern(text) {
  return String(text).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function countSymbolOccurrences(sourceText, symbol) {
  const pattern = new RegExp(`${escapeRegexPattern(symbol)}(?![A-Za-z0-9-])`, "g");
  const matches = sourceText.match(pattern);
  return matches ? matches.length : 0;
}

function assertPhaseOrderEvidence(phaseOrder, completed) {
  assert(Array.isArray(phaseOrder) && phaseOrder.length > 0, "B10V-12: missing phaseOrder list");
  assert(Array.isArray(completed) && completed.length > 0, "B10V-12: missing completed phase list");
  let cursor = 0;
  for (const phase of completed) {
    const idx = phaseOrder.indexOf(phase);
    assert(idx >= 0, `B10V-12: completed phase not in phaseOrder: ${phase}`);
    assert(idx >= cursor, `B10V-12: out-of-order phase completion: ${phase}`);
    cursor = idx;
  }
  assert(
    completed.length === phaseOrder.length && completed.every((phase, idx) => phase === phaseOrder[idx]),
    "B10V-12: phase completion evidence is not fully closed in strict order",
  );
}

const kernelUrl = new URL("./wasmcl.wasm", import.meta.url);
const subprimsUrl = new URL("./subprims.wasm", import.meta.url);
const subprimsMapUrl = new URL("../../../build/wasm32/subprims-map.json", import.meta.url);
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

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const wasm2SourcePath = path.resolve(repoRoot, "compiler/WASM/wasm2.lisp");
const redlineGatePath = path.resolve(
  repoRoot,
  "doc/wasm/tickets/evidence/bpl-10/b10c-redline-gates-2026-02-10.json",
);

let redlineGate;
try {
  redlineGate = JSON.parse((await fs.readFile(redlineGatePath)).toString("utf8"));
} catch (err) {
  fail(`B10V-10/11/12 missing redline gate artifact ${redlineGatePath}: ${err?.message ?? err}`);
}

let wasm2SourceText;
try {
  wasm2SourceText = (await fs.readFile(wasm2SourcePath)).toString("utf8");
} catch (err) {
  fail(`B10V-10 unable to read ${wasm2SourcePath}: ${err?.message ?? err}`);
}

const emissionCaps = redlineGate?.b10v10?.maxCounts ?? null;
assert(emissionCaps && typeof emissionCaps === "object", "B10V-10: missing maxCounts baseline map");
for (const [symbol, maxCountRaw] of Object.entries(emissionCaps)) {
  const maxCount = Number.parseInt(String(maxCountRaw), 10);
  assert(Number.isFinite(maxCount) && maxCount >= 0, `B10V-10: invalid max count for ${symbol}`);
  const observed = countSymbolOccurrences(wasm2SourceText, symbol);
  assert(
    observed <= maxCount,
    `B10V-10 regression for ${symbol}: observed=${observed} baseline=${maxCount}`,
  );
}

const perfArtifacts = redlineGate?.b10v11?.artifacts ?? {};
const fixnumPerfRel = perfArtifacts?.fixnumAdd?.path;
const miscPerfRel = perfArtifacts?.miscLane?.path;
assert(typeof fixnumPerfRel === "string" && fixnumPerfRel.length > 0, "B10V-11: missing fixnum evidence path");
assert(typeof miscPerfRel === "string" && miscPerfRel.length > 0, "B10V-11: missing misc evidence path");
const fixnumPerfPath = path.resolve(repoRoot, fixnumPerfRel);
const miscPerfPath = path.resolve(repoRoot, miscPerfRel);

let fixnumPerf;
let miscPerf;
try {
  fixnumPerf = JSON.parse((await fs.readFile(fixnumPerfPath)).toString("utf8"));
} catch (err) {
  fail(`B10V-11 unable to read fixnum artifact ${fixnumPerfPath}: ${err?.message ?? err}`);
}
try {
  miscPerf = JSON.parse((await fs.readFile(miscPerfPath)).toString("utf8"));
} catch (err) {
  fail(`B10V-11 unable to read misc artifact ${miscPerfPath}: ${err?.message ?? err}`);
}

assert(
  fixnumPerf?.repeatability?.allSamplesWithinBudget === true,
  "B10V-11: fixnum evidence is outside repeatability budget",
);
assert(
  fixnumPerf?.bounds?.withinDirectFixnumAddBound === true,
  "B10V-11: fixnum helper-call bound failed",
);
assert(
  miscPerf?.bounds?.withinBound === true,
  "B10V-11: misc lane evidence bound failed",
);

assertPhaseOrderEvidence(
  redlineGate?.b10v12?.phaseOrder ?? null,
  redlineGate?.b10v12?.completed ?? null,
);

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
assert(typeof kernelExports.wasm_get_gc_root_policy_mode === "function", "missing wasm_get_gc_root_policy_mode export");
assert(typeof kernelExports.wasm_get_entry_gc_root_policy_mode === "function", "missing wasm_get_entry_gc_root_policy_mode export");
const nilValue = kernelExports.wasm_get_lisp_nil() >>> 0;
const GC_ROOT_MODE_RUNTIME_DEFAULT = 0;
const GC_ROOT_MODE_RUNTIME_BOOTSTRAP = 1;
const functions = Array.isArray(bundle.functions) ? bundle.functions : [];

function normalizeBoundaryOpsList(rawOps) {
  if (!Array.isArray(rawOps)) return [];
  const out = [];
  const seen = new Set();
  for (const op of rawOps) {
    if (typeof op !== "string") continue;
    if (op.length === 0 || seen.has(op)) continue;
    seen.add(op);
    out.push(op);
  }
  return out;
}

const gcRootPolicyModes = new Map(
  Object.entries(bundle?.gcRootPolicyModes ?? {})
    .map(([entry, mode]) => {
      const idx = Number.parseInt(String(entry), 10);
      if (!Number.isFinite(idx) || idx < 0) return null;
      if (!Number.isFinite(mode) || mode < 0) return null;
      return [idx >>> 0, mode >>> 0];
    })
    .filter(Boolean),
);
const gcRootBoundaryOps = new Map(
  Object.entries(bundle?.gcRootBoundaryOps ?? {})
    .map(([entry, ops]) => {
      const idx = Number.parseInt(String(entry), 10);
      if (!Number.isFinite(idx) || idx < 0) return null;
      if (!Array.isArray(ops)) return null;
      const normalizedOps = normalizeBoundaryOpsList(ops);
      return [idx >>> 0, normalizedOps];
    })
    .filter(Boolean),
);

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

function expectedGcRootPolicyMode(entryIndexValue) {
  const entry = entryIndexValue >>> 0;
  assert(gcRootPolicyModes.has(entry), `missing gc root policy mode for entry ${entry}`);
  return gcRootPolicyModes.get(entry);
}

function expectedGcRootPolicyModeFromBoundaryOps(entryIndexValue) {
  const entry = entryIndexValue >>> 0;
  const boundaryOps = gcRootBoundaryOps.get(entry) ?? [];
  return boundaryOps.length > 0 ? GC_ROOT_MODE_RUNTIME_DEFAULT : GC_ROOT_MODE_RUNTIME_BOOTSTRAP;
}

function assertBoundaryModeContract(entryIndexValue, label) {
  const entry = entryIndexValue >>> 0;
  const fromModeMap = expectedGcRootPolicyMode(entry);
  const fromBoundaryMap = expectedGcRootPolicyModeFromBoundaryOps(entry);
  assert(
    fromModeMap === fromBoundaryMap,
    `${label}: gc root boundary/mode mismatch for entry ${entry}: mode=${fromModeMap} boundaryMode=${fromBoundaryMap}`,
  );
}

function assertBundleBoundaryMapContract() {
  assert(gcRootBoundaryOps.size > 0, "missing gcRootBoundaryOps map in wasm-smoke-modules bundle");
  for (const fn of functions) {
    assertBoundaryModeContract(fn.entryIndex >>> 0, "bundle-contract");
  }
}

function assertAllRegisteredGcRootModes(label) {
  for (const fn of functions) {
    const entry = fn.entryIndex >>> 0;
    const expected = expectedGcRootPolicyMode(entry);
    const registered = kernelExports.wasm_get_entry_gc_root_policy_mode(entry) >>> 0;
    assert(
      registered === expected,
      `${label}: unexpected registered gc root policy mode for entry ${entry}: got=${registered} expected=${expected}`,
    );
  }
}

function assertGcRootPolicyModePublished(entryIndexValue, label) {
  const entry = entryIndexValue >>> 0;
  const expected = expectedGcRootPolicyMode(entry);
  const registered = kernelExports.wasm_get_entry_gc_root_policy_mode(entry) >>> 0;
  assert(
    registered === expected,
    `${label}: unexpected registered gc root policy mode for entry ${entry}: got=${registered} expected=${expected}`,
  );
  const active = kernelExports.wasm_get_gc_root_policy_mode() >>> 0;
  if (expected === GC_ROOT_MODE_RUNTIME_DEFAULT) {
    assert(
      active === GC_ROOT_MODE_RUNTIME_DEFAULT,
      `${label}: unexpected active gc root policy mode for default entry: got=${active} expected=${GC_ROOT_MODE_RUNTIME_DEFAULT}`,
    );
  } else {
    assert(
      active === GC_ROOT_MODE_RUNTIME_DEFAULT || active === GC_ROOT_MODE_RUNTIME_BOOTSTRAP,
      `${label}: unexpected active gc root policy mode domain for bootstrap entry: got=${active}`,
    );
  }
}

assertBundleBoundaryMapContract();
assertAllRegisteredGcRootModes("initial-install");

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
assertGcRootPolicyModePublished(constEntry, "const");

const symbolEntry = entryIndex("WASM-SMOKE-SYMBOL");
const symbolResult = kernelExports.wasm_test_entry_funcall(symbolEntry, 0) >>> 0;
assert(symbolResult !== nilValue, "unexpected symbol result: got NIL");
assertGcRootPolicyModePublished(symbolEntry, "symbol");

const ffiEntry = entryIndex("WASM-SMOKE-FFI-ADD");
const ffiResult = kernelExports.wasm_test_entry_funcall2(ffiEntry, 10, 32) >> 2;
assert(ffiResult === 42, `unexpected ffi-add result: got=${ffiResult} expected=42`);
assertGcRootPolicyModePublished(ffiEntry, "ffi-add");
const ffiSignedResult = kernelExports.wasm_test_entry_funcall2(ffiEntry, -10, 52) >> 2;
assert(ffiSignedResult === 42, `unexpected ffi-add signed result: got=${ffiSignedResult} expected=42`);
const ffiZeroResult = kernelExports.wasm_test_entry_funcall2(ffiEntry, 0, 0) >> 2;
assert(ffiZeroResult === 0, `unexpected ffi-add zero result: got=${ffiZeroResult} expected=0`);

const addEntry = entryIndex("WASM-SMOKE-ADD");
const addResult = kernelExports.wasm_test_entry_funcall2(addEntry, 10, 32) >> 2;
assert(addResult === 42, `unexpected add result: got=${addResult} expected=42`);
assertGcRootPolicyModePublished(addEntry, "add");

const subEntry = entryIndex("WASM-SMOKE-SUB");
const subResult = kernelExports.wasm_test_entry_funcall2(subEntry, 50, 8) >> 2;
assert(subResult === 42, `unexpected sub result: got=${subResult} expected=42`);
assertGcRootPolicyModePublished(subEntry, "sub");

const mulEntry = entryIndex("WASM-SMOKE-MUL");
const mulResult = kernelExports.wasm_test_entry_funcall2(mulEntry, 6, 7) >> 2;
assert(mulResult === 42, `unexpected mul result: got=${mulResult} expected=42`);
assertGcRootPolicyModePublished(mulEntry, "mul");

const ashEntry = entryIndex("WASM-SMOKE-ASH");
const ashLeft = kernelExports.wasm_test_entry_funcall2(ashEntry, 3, 2) >> 2;
assert(ashLeft === 12, `unexpected ash left result: got=${ashLeft} expected=12`);
assertGcRootPolicyModePublished(ashEntry, "ash");

const logandEntry = entryIndex("WASM-SMOKE-LOGAND");
const logandResult = kernelExports.wasm_test_entry_funcall2(logandEntry, 6, 3) >> 2;
assert(logandResult === (6 & 3), `unexpected logand result: got=${logandResult} expected=${6 & 3}`);
assertGcRootPolicyModePublished(logandEntry, "logand");

const logiorEntry = entryIndex("WASM-SMOKE-LOGIOR");
const logiorResult = kernelExports.wasm_test_entry_funcall2(logiorEntry, 6, 3) >> 2;
assert(logiorResult === (6 | 3), `unexpected logior result: got=${logiorResult} expected=${6 | 3}`);
assertGcRootPolicyModePublished(logiorEntry, "logior");

const logxorEntry = entryIndex("WASM-SMOKE-LOGXOR");
const logxorResult = kernelExports.wasm_test_entry_funcall2(logxorEntry, 6, 3) >> 2;
assert(logxorResult === (6 ^ 3), `unexpected logxor result: got=${logxorResult} expected=${6 ^ 3}`);
assertGcRootPolicyModePublished(logxorEntry, "logxor");

const lognotEntry = entryIndex("WASM-SMOKE-LOGNOT");
const lognotResult = kernelExports.wasm_test_entry_funcall1_raw(lognotEntry, fixnum(5)) >> 2;
assert(lognotResult === ~5, `unexpected lognot result: got=${lognotResult} expected=${~5}`);
assertGcRootPolicyModePublished(lognotEntry, "lognot");

const negEntry = entryIndex("WASM-SMOKE-NEG");
const negResult = kernelExports.wasm_test_entry_funcall1_raw(negEntry, fixnum(7)) >> 2;
assert(negResult === -7, `unexpected neg result: got=${negResult} expected=-7`);
assertGcRootPolicyModePublished(negEntry, "neg");

const ifEntry = entryIndex("WASM-SMOKE-IF");
const ifTrue = kernelExports.wasm_test_entry_funcall1_raw(ifEntry, fixnum(1)) >> 2;
assert(ifTrue === 11, `unexpected if true result: got=${ifTrue} expected=11`);
const ifFalse = kernelExports.wasm_test_entry_funcall1_raw(ifEntry, nilValue);
assert(ifFalse === fixnum(22), `unexpected if false result: got=0x${ifFalse.toString(16)} expected=0x${fixnum(22).toString(16)}`);
assertGcRootPolicyModePublished(ifEntry, "if");

const ifArgEntry = entryIndex("WASM-SMOKE-IF-ARG");
const ifArgTrue = kernelExports.wasm_test_entry_funcall1_raw(ifArgEntry, fixnum(9));
assert(ifArgTrue === fixnum(9), `unexpected if-arg true result: got=0x${ifArgTrue.toString(16)} expected=0x${fixnum(9).toString(16)}`);
const ifArgFalse = kernelExports.wasm_test_entry_funcall1_raw(ifArgEntry, nilValue);
assert(ifArgFalse === fixnum(17), `unexpected if-arg false result: got=0x${ifArgFalse.toString(16)} expected=0x${fixnum(17).toString(16)}`);
assertGcRootPolicyModePublished(ifArgEntry, "if-arg");

const identityEntry = entryIndex("WASM-SMOKE-IDENTITY");
const identResult = kernelExports.wasm_test_entry_funcall1_raw(identityEntry, fixnum(101));
assert(identResult === fixnum(101), `unexpected identity result: got=0x${identResult.toString(16)} expected=0x${fixnum(101).toString(16)}`);
assertGcRootPolicyModePublished(identityEntry, "identity");

const identityYEntry = entryIndex("WASM-SMOKE-IDENTITY-Y");
const identYResult = kernelExports.wasm_test_entry_funcall2(identityYEntry, 7, 42);
assert(identYResult === fixnum(42), `unexpected identity-y result: got=0x${identYResult.toString(16)} expected=0x${fixnum(42).toString(16)}`);
assertGcRootPolicyModePublished(identityYEntry, "identity-y");

const blockEntry = entryIndex("WASM-SMOKE-BLOCK");
const blockTrue = kernelExports.wasm_test_entry_funcall1_raw(blockEntry, fixnum(1)) >> 2;
assert(blockTrue === 7, `unexpected block true result: got=${blockTrue} expected=7`);
const blockFalse = kernelExports.wasm_test_entry_funcall1_raw(blockEntry, nilValue) >> 2;
assert(blockFalse === 9, `unexpected block false result: got=${blockFalse} expected=9`);
assertGcRootPolicyModePublished(blockEntry, "block");

const tagbodyEntry = entryIndex("WASM-SMOKE-TAGBODY");
const tagbodyTrue = kernelExports.wasm_test_entry_funcall1_raw(tagbodyEntry, fixnum(1)) >> 2;
assert(tagbodyTrue === 1, `unexpected tagbody true result: got=${tagbodyTrue} expected=1`);
const tagbodyFalse = kernelExports.wasm_test_entry_funcall1_raw(tagbodyEntry, nilValue) >> 2;
assert(tagbodyFalse === 2, `unexpected tagbody false result: got=${tagbodyFalse} expected=2`);
assertGcRootPolicyModePublished(tagbodyEntry, "tagbody");

// multiple-value-call execution paths are covered by mvcall-smoke.mjs.

await installBundle("reload");
assertAllRegisteredGcRootModes("reload-install");
const symbolReload = kernelExports.wasm_test_entry_funcall(symbolEntry, 0) >>> 0;
assert(symbolReload === symbolResult, "symbol identity changed across reload");
assertGcRootPolicyModePublished(symbolEntry, "symbol-reload");

console.log("PASS: wasm compiler emission smoke test");
