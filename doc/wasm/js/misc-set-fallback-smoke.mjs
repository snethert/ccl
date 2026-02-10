/*
 * WASM32 misc-set fallback smoke/checkpoint.
 *
 * Validates:
 *  1) Targeted smoke entry executes the shared `.SPmisc-set` fallback lane.
 *  2) Optional checkpoint mode captures dynamic calls/op for `_SPmisc_set`
 *     through `wasm_call_subprim_fixnum`.
 */

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  createCclImports,
  createSharedCclRuntime,
  installCompiledModulesFromBundle,
  installSubprimsTable,
  instantiateWasm,
} from "./ccl-loader.mjs";
import { decodeModuleBundleIndexV2 } from "./module-bundle-v2.mjs";
import { createMicrokernel } from "./microkernel.mjs";

function fail(msg) {
  console.error(`FAIL: ${msg}`);
  process.exit(1);
}

function assert(cond, msg) {
  if (!cond) fail(msg);
}

function round3(x) {
  return Math.round(x * 1000) / 1000;
}

function readFileUrl(url) {
  return fs.readFile(fileURLToPath(url));
}

function readOption(args, name) {
  const idx = args.indexOf(name);
  if (idx === -1) return null;
  const value = args[idx + 1];
  if (value == null || value.startsWith("--")) {
    fail(`missing value for ${name}`);
  }
  return value;
}

function readPositiveIntOption(args, name, fallback) {
  const raw = readOption(args, name);
  if (raw == null) return fallback;
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n) || n <= 0) {
    fail(`invalid positive integer for ${name}: ${raw}`);
  }
  return n >>> 0;
}

function readNumberOption(args, name, fallback) {
  const raw = readOption(args, name);
  if (raw == null) return fallback;
  const n = Number.parseFloat(raw);
  if (!Number.isFinite(n)) {
    fail(`invalid number for ${name}: ${raw}`);
  }
  return n;
}

async function decodeMaybeCompressed(bytes, encoding, expectedLength, label) {
  if (!encoding) return bytes;
  const zlib = await import("node:zlib");
  let decoded;
  switch (String(encoding)) {
    case "br":
      decoded = zlib.brotliDecompressSync(bytes);
      break;
    case "gzip":
      decoded = zlib.gunzipSync(bytes);
      break;
    case "deflate":
      decoded = zlib.inflateSync(bytes);
      break;
    case "deflate-raw":
      decoded = zlib.inflateRawSync(bytes);
      break;
    default:
      fail(`unsupported bundle encoding ${encoding} (${label})`);
  }
  if (Number.isFinite(expectedLength) && expectedLength >= 0 && decoded.length !== expectedLength) {
    fail(`${label} length mismatch after decode: expected=${expectedLength} got=${decoded.length}`);
  }
  return decoded;
}

async function extractBundleModule(bundle, binaryBytes, indexBytes, entryIndex) {
  const templatePrefix =
    typeof bundle?.exportNameTemplatePrefix === "string" && bundle.exportNameTemplatePrefix.length > 0
      ? bundle.exportNameTemplatePrefix
      : "ccl_generic_entry_";
  const index = decodeModuleBundleIndexV2(indexBytes, { templatePrefix });
  const moduleEntry = index?.modules?.find((entry) => (entry.entryIndex >>> 0) === (entryIndex >>> 0));
  assert(moduleEntry, `missing bundle module entry ${entryIndex}`);
  const offset = moduleEntry.offset >>> 0;
  const storedLength = Number.isFinite(moduleEntry.moduleStoredLength)
    ? (moduleEntry.moduleStoredLength >>> 0)
    : (moduleEntry.length >>> 0);
  const end = offset + storedLength;
  assert(end <= binaryBytes.length, `bundle module ${entryIndex} exceeds binary length`);
  const storedBytes = binaryBytes.subarray(offset, end);
  const moduleBytes = await decodeMaybeCompressed(
    storedBytes,
    moduleEntry.moduleEncoding ?? null,
    moduleEntry.length >>> 0,
    `bundle module ${entryIndex}`,
  );
  return {
    entryIndex: entryIndex >>> 0,
    exportName: moduleEntry.exportName,
    moduleBytes: moduleBytes instanceof Uint8Array ? moduleBytes : Uint8Array.from(moduleBytes),
  };
}

function runMiscSetFallbackLoop(kernelExports, entryIndex, iterations) {
  let checksum = 0;
  for (let i = 0; i < iterations; i++) {
    const arg = i & 1;
    const raw = kernelExports.wasm_test_entry_funcall(entryIndex, arg) >>> 0;
    const got = raw >> 2;
    if (got !== 77) {
      fail(`unexpected misc-set fallback result for entry ${entryIndex}: got=${got} expected=77`);
    }
    checksum = (checksum + got + arg) | 0;
  }
  return checksum | 0;
}

const WASM_ENTRY_CALL_ABI_LEGACY = 0;
const WASM_ENTRY_CALL_ABI_UNARY_I32 = 1;
const WASM_ENTRY_CALL_ABI_BINARY_I32 = 2;

function inferEntryCallAbiKind(fn) {
  if (typeof fn !== "function") return WASM_ENTRY_CALL_ABI_LEGACY;
  if (fn.length === 1) return WASM_ENTRY_CALL_ABI_UNARY_I32;
  if (fn.length === 2) return WASM_ENTRY_CALL_ABI_BINARY_I32;
  return WASM_ENTRY_CALL_ABI_LEGACY;
}

async function collectSubprimDynamicCounts({
  moduleBytes,
  exportName,
  tableEntryIndex,
  runtime,
  microkernel,
  kernelExports,
  iterations,
  miscSetFixnum,
  subprimsSymbols,
}) {
  assert(typeof kernelExports.wasm_call_subprim_fixnum === "function", "missing wasm_call_subprim_fixnum export");
  const countsByFixnum = new Map();
  const wrapped = { ...kernelExports };

  wrapped.wasm_call_subprim_fixnum = (subprimFixnum) => {
    const raw = subprimFixnum >>> 0;
    countsByFixnum.set(raw, (countsByFixnum.get(raw) ?? 0) + 1);
    return kernelExports.wasm_call_subprim_fixnum(subprimFixnum);
  };

  const { instance } = await instantiateWasm(
    moduleBytes,
    createCclImports({
      memory: runtime.memory,
      subprimsTable: runtime.subprimsTable,
      microkernel,
      extra: { ccl: wrapped },
    }),
  );

  const fn = instance?.exports?.[exportName];
  assert(typeof fn === "function", `instrumented module missing export ${exportName}`);

  while (runtime.subprimsTable.length <= tableEntryIndex) {
    runtime.subprimsTable.grow((tableEntryIndex + 1) - runtime.subprimsTable.length);
  }
  runtime.subprimsTable.set(tableEntryIndex, fn);
  if (typeof kernelExports.wasm_set_entry_call_abi === "function") {
    kernelExports.wasm_set_entry_call_abi(
      tableEntryIndex >>> 0,
      inferEntryCallAbiKind(fn) >>> 0,
    );
  }

  const checksum = runMiscSetFallbackLoop(kernelExports, tableEntryIndex, iterations);
  const totalSubprimCalls = [...countsByFixnum.values()].reduce((sum, value) => sum + value, 0) >>> 0;
  const miscSetCalls = countsByFixnum.get(miscSetFixnum >>> 0) ?? 0;

  const sortedFixnumEntries = [...countsByFixnum.entries()].sort((a, b) => a[0] - b[0]);
  const callsBySubprimFixnum = {};
  const callsBySubprimSymbol = {};
  for (const [fixnum, count] of sortedFixnumEntries) {
    callsBySubprimFixnum[String(fixnum >>> 0)] = count >>> 0;
    const subprimIndex = (fixnum >>> 2) >>> 0;
    const symbol = subprimsSymbols[subprimIndex] ?? `#${subprimIndex}`;
    callsBySubprimSymbol[symbol] = (callsBySubprimSymbol[symbol] ?? 0) + (count >>> 0);
  }

  const callsPerOperationBySubprimSymbol = {};
  for (const [symbol, count] of Object.entries(callsBySubprimSymbol)) {
    callsPerOperationBySubprimSymbol[symbol] = round3(count / iterations);
  }

  return {
    checksum,
    totalSubprimCalls,
    totalSubprimCallsPerOperation: round3(totalSubprimCalls / iterations),
    miscSetCalls: miscSetCalls >>> 0,
    miscSetCallsPerOperation: round3(miscSetCalls / iterations),
    callsBySubprimFixnum,
    callsBySubprimSymbol,
    callsPerOperationBySubprimSymbol,
  };
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
const subprimsSymbols = Array.isArray(subprimsMap?.symbols) ? subprimsMap.symbols : [];
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
}

assert(typeof kernel.instance.exports.wasm_set_cstack_bounds === "function", "missing wasm_set_cstack_bounds export");
const cstackBase = runtime.memory.buffer.byteLength;
kernel.instance.exports.wasm_set_cstack_bounds(cstackBase, cstackSize);

const blobBase = (cstackBase - cstackSize - imageLen) & ~15;
assert(blobBase >= 0, "not enough memory to place boot image below cstack");
new Uint8Array(runtime.memory.buffer).set(imageBytes, blobBase);

assert(typeof kernel.instance.exports.wasm_ccl_load_image === "function", "missing wasm_ccl_load_image export");
kernel.instance.exports.wasm_ccl_load_image(blobBase, imageLen);

const functions = Array.isArray(bundle.functions) ? bundle.functions : [];
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
assert(count > 0 && installed > 0, "no compiled modules installed from bundle");
assert(!failed, `compiled modules failed during install: ${failed}`);

function entryIndex(name) {
  const item = functions.find((fn) => fn.name === name);
  assert(item, `missing compiled function ${name}`);
  return item.entryIndex >>> 0;
}

const kernelExports = kernel.instance.exports;
assert(typeof kernelExports.wasm_test_entry_funcall === "function", "missing wasm_test_entry_funcall export");

const miscSetEntryName = "WASM-SMOKE-MISC-SET-FALLBACK";
const miscSetEntryIndex = entryIndex(miscSetEntryName);
const smokeResult0 = kernelExports.wasm_test_entry_funcall(miscSetEntryIndex, 0) >> 2;
const smokeResult1 = kernelExports.wasm_test_entry_funcall(miscSetEntryIndex, 1) >> 2;
assert(smokeResult0 === 77, `unexpected ${miscSetEntryName} result for arg=0: got=${smokeResult0} expected=77`);
assert(smokeResult1 === 77, `unexpected ${miscSetEntryName} result for arg=1: got=${smokeResult1} expected=77`);

const args = process.argv.slice(2);
const checkpoint = args.includes("--checkpoint");
if (!checkpoint) {
  console.log("PASS: wasm misc-set fallback smoke test");
  process.exit(0);
}

const iterations = readPositiveIntOption(args, "--iterations", 20000);
const maxMiscSetCallsPerOp = readNumberOption(args, "--max-misc-set-calls-per-op", 1);
const outPathOpt = readOption(args, "--checkpoint-out");

const miscSetSubprimIndex = subprimsSymbols.indexOf("_SPmisc_set");
assert(miscSetSubprimIndex >= 0, "subprims map missing _SPmisc_set symbol");
const miscSetFixnum = (miscSetSubprimIndex << 2) >>> 0;

const moduleEntry = await extractBundleModule(bundle, bundleBinaryBytes, bundleIndexBytes, miscSetEntryIndex);
const dynamic = await collectSubprimDynamicCounts({
  moduleBytes: moduleEntry.moduleBytes,
  exportName: moduleEntry.exportName,
  tableEntryIndex: 942,
  runtime,
  microkernel,
  kernelExports,
  iterations,
  miscSetFixnum,
  subprimsSymbols,
});

assert(dynamic.miscSetCalls > 0, "misc-set fallback dynamic counter stayed at zero");
const withinBound = dynamic.miscSetCallsPerOperation <= (maxMiscSetCallsPerOp + 1e-9);
assert(
  withinBound,
  `misc-set fallback calls/op exceeded bound: ${dynamic.miscSetCallsPerOperation} > ${maxMiscSetCallsPerOp}`,
);

const report = {
  capturedAt: new Date().toISOString(),
  host: {
    node: process.version,
    platform: process.platform,
    arch: process.arch,
  },
  options: {
    iterations,
    maxMiscSetCallsPerOp,
  },
  entry: {
    name: miscSetEntryName,
    entryIndex: miscSetEntryIndex,
    exportName: moduleEntry.exportName,
  },
  subprim: {
    symbol: "_SPmisc_set",
    index: miscSetSubprimIndex >>> 0,
    fixnum: miscSetFixnum >>> 0,
  },
  dynamicPath: dynamic,
  bounds: {
    withinBound,
    maxMiscSetCallsPerOp: round3(maxMiscSetCallsPerOp),
  },
};

console.log("CHECKPOINT: B10C-01A-18 misc-set fallback dynamic evidence");
console.log(
  `  entry ${miscSetEntryName} (#${miscSetEntryIndex}) _SPmisc_set calls/op=` +
  `${report.dynamicPath.miscSetCallsPerOperation} (bound<=${round3(maxMiscSetCallsPerOp)})`,
);
console.log(
  `  total subprim calls/op=${report.dynamicPath.totalSubprimCallsPerOperation} ` +
  `(iterations=${iterations})`,
);

if (outPathOpt) {
  const outPath = path.resolve(process.cwd(), outPathOpt);
  await fs.mkdir(path.dirname(outPath), { recursive: true });
  await fs.writeFile(outPath, `${JSON.stringify(report, null, 2)}\n`);
  console.log(`CHECKPOINT: wrote ${outPath}`);
}

console.log("PASS: wasm misc-set fallback smoke test");
