/*
 * WASM32 fixnum add smoke test.
 *
 * Validates:
 *  1) Compiled module registry installs fixnum-add entry into the table
 *  2) _SPfuncall dispatch with 2 args via arg_z/arg_y
 *  3) Optional B10C-01A-17 checkpoint mode captures compat-vs-direct
 *     latency and instruction-path deltas for fixnum add kernels.
 */

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  createCclImports,
  createSharedCclRuntime,
  installCompiledModulesFromBundle,
  installCompiledModulesFromRegistry,
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

function median(values) {
  if (!Array.isArray(values) || values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if ((sorted.length % 2) === 1) return sorted[mid];
  return (sorted[mid - 1] + sorted[mid]) / 2;
}

function round3(x) {
  return Math.round(x * 1000) / 1000;
}

function mapToSortedObject(map) {
  const entries = [...map.entries()].sort((a, b) => {
    if (a[0] < b[0]) return -1;
    if (a[0] > b[0]) return 1;
    return 0;
  });
  return Object.fromEntries(entries);
}

function readVarUint(bytes, state, label) {
  let value = 0;
  let shift = 0;
  for (let i = 0; i < 10; i++) {
    if (state.offset >= bytes.length) {
      fail(`truncated varuint while reading ${label}`);
    }
    const byte = bytes[state.offset++];
    value += (byte & 0x7f) * (2 ** shift);
    if ((byte & 0x80) === 0) {
      if (!Number.isSafeInteger(value)) {
        fail(`varuint overflow while reading ${label}`);
      }
      return value;
    }
    shift += 7;
  }
  fail(`varuint too long while reading ${label}`);
}

function readVarInt(bytes, state, bits, label) {
  let value = 0;
  let shift = 0;
  let byte = 0;
  for (let i = 0; i < 10; i++) {
    if (state.offset >= bytes.length) {
      fail(`truncated varint while reading ${label}`);
    }
    byte = bytes[state.offset++];
    value |= (byte & 0x7f) << shift;
    shift += 7;
    if ((byte & 0x80) === 0) {
      break;
    }
  }
  if ((shift < bits) && (byte & 0x40)) {
    value |= (~0 << shift);
  }
  return value;
}

function readName(bytes, state, label) {
  const len = readVarUint(bytes, state, `${label}.length`);
  if ((state.offset + len) > bytes.length) {
    fail(`truncated name while reading ${label}`);
  }
  const out = new TextDecoder("utf-8").decode(bytes.subarray(state.offset, state.offset + len));
  state.offset += len;
  return out;
}

function skipLimits(bytes, state, label) {
  const flags = readVarUint(bytes, state, `${label}.flags`);
  readVarUint(bytes, state, `${label}.min`);
  if ((flags & 0x01) !== 0) {
    readVarUint(bytes, state, `${label}.max`);
  }
}

function skipBlockType(bytes, state, label) {
  if (state.offset >= bytes.length) {
    fail(`truncated blocktype while reading ${label}`);
  }
  const b = bytes[state.offset];
  if (
    b === 0x40 ||
    b === 0x7f || b === 0x7e || b === 0x7d || b === 0x7c ||
    b === 0x7b || b === 0x70 || b === 0x6f
  ) {
    state.offset += 1;
    return;
  }
  readVarInt(bytes, state, 33, label);
}

function skipMemoryArg(bytes, state, label) {
  readVarUint(bytes, state, `${label}.align`);
  readVarUint(bytes, state, `${label}.offset`);
}

function parseExportedFunctionBody(moduleBytes, exportName) {
  const bytes = moduleBytes instanceof Uint8Array ? moduleBytes : Uint8Array.from(moduleBytes);
  if (bytes.length < 8) fail("module too short");
  if (
    bytes[0] !== 0x00 || bytes[1] !== 0x61 || bytes[2] !== 0x73 || bytes[3] !== 0x6d ||
    bytes[4] !== 0x01 || bytes[5] !== 0x00 || bytes[6] !== 0x00 || bytes[7] !== 0x00
  ) {
    fail("invalid wasm module header");
  }

  const state = { offset: 8 };
  const importFunctionNames = [];
  const exportFuncIndex = new Map();
  let codeBodies = null;

  while (state.offset < bytes.length) {
    const sectionId = bytes[state.offset++];
    const sectionSize = readVarUint(bytes, state, "section size");
    const sectionStart = state.offset;
    const sectionEnd = sectionStart + sectionSize;
    if (sectionEnd > bytes.length) {
      fail(`section ${sectionId} exceeds module size`);
    }

    if (sectionId === 2) {
      const importCount = readVarUint(bytes, state, "import count");
      for (let i = 0; i < importCount; i++) {
        const mod = readName(bytes, state, `import[${i}].module`);
        const field = readName(bytes, state, `import[${i}].field`);
        if (state.offset >= bytes.length) {
          fail(`truncated import kind at import[${i}]`);
        }
        const kind = bytes[state.offset++];
        switch (kind) {
          case 0x00:
            readVarUint(bytes, state, `import[${i}].func_type`);
            importFunctionNames.push(`${mod}.${field}`);
            break;
          case 0x01:
            state.offset += 1; // reftype
            skipLimits(bytes, state, `import[${i}].table_limits`);
            break;
          case 0x02:
            skipLimits(bytes, state, `import[${i}].memory_limits`);
            break;
          case 0x03:
            state.offset += 2; // valtype + mutability
            break;
          case 0x04:
            state.offset += 1; // tag attr
            readVarUint(bytes, state, `import[${i}].tag_type`);
            break;
          default:
            fail(`unsupported import kind ${kind} at import[${i}]`);
        }
      }
    } else if (sectionId === 7) {
      const exportCount = readVarUint(bytes, state, "export count");
      for (let i = 0; i < exportCount; i++) {
        const name = readName(bytes, state, `export[${i}].name`);
        if (state.offset >= bytes.length) fail(`truncated export kind for ${name}`);
        const kind = bytes[state.offset++];
        const index = readVarUint(bytes, state, `export[${i}].index`);
        if (kind === 0x00) {
          exportFuncIndex.set(name, index >>> 0);
        }
      }
    } else if (sectionId === 10) {
      const bodyCount = readVarUint(bytes, state, "code body count");
      const bodies = [];
      for (let i = 0; i < bodyCount; i++) {
        const bodySize = readVarUint(bytes, state, `code[${i}].size`);
        const bodyStart = state.offset;
        const bodyEnd = bodyStart + bodySize;
        if (bodyEnd > bytes.length) fail(`code body ${i} exceeds module size`);
        bodies.push(bytes.subarray(bodyStart, bodyEnd));
        state.offset = bodyEnd;
      }
      codeBodies = bodies;
    }

    state.offset = sectionEnd;
  }

  if (!exportFuncIndex.has(exportName)) {
    fail(`module missing export ${exportName}`);
  }
  const funcIndex = exportFuncIndex.get(exportName) >>> 0;
  const importFunctionCount = importFunctionNames.length >>> 0;
  if (funcIndex < importFunctionCount) {
    fail(`export ${exportName} points at imported function index ${funcIndex}`);
  }
  const definedIndex = (funcIndex - importFunctionCount) >>> 0;
  if (!codeBodies || definedIndex >= codeBodies.length) {
    fail(`code body missing for export ${exportName} (func index ${funcIndex})`);
  }

  return {
    body: codeBodies[definedIndex],
    importFunctionNames,
  };
}

function collectInstructionMetrics(moduleBytes, exportName) {
  const { body, importFunctionNames } = parseExportedFunctionBody(moduleBytes, exportName);
  const state = { offset: 0 };
  const localDecls = readVarUint(body, state, "local decl count");
  let localCount = 0;
  for (let i = 0; i < localDecls; i++) {
    localCount += readVarUint(body, state, `local[${i}].count`);
    state.offset += 1; // local type
  }

  const importCalls = new Map();
  let instructionCount = 0;
  let callCount = 0;
  let callIndirectCount = 0;
  let ifCount = 0;

  while (state.offset < body.length) {
    const op = body[state.offset++];
    instructionCount += 1;
    switch (op) {
      case 0x02: // block
      case 0x03: // loop
      case 0x04: // if
        if (op === 0x04) ifCount += 1;
        skipBlockType(body, state, "blocktype");
        break;
      case 0x0c: // br
      case 0x0d: // br_if
        readVarUint(body, state, "label index");
        break;
      case 0x0e: { // br_table
        const count = readVarUint(body, state, "br_table count");
        for (let i = 0; i <= count; i++) {
          readVarUint(body, state, "br_table label");
        }
        break;
      }
      case 0x10: { // call
        callCount += 1;
        const target = readVarUint(body, state, "call target");
        if (target < importFunctionNames.length) {
          const name = importFunctionNames[target];
          importCalls.set(name, (importCalls.get(name) ?? 0) + 1);
        }
        break;
      }
      case 0x11: // call_indirect
        callIndirectCount += 1;
        readVarUint(body, state, "call_indirect type");
        readVarUint(body, state, "call_indirect table");
        break;
      case 0x1c: { // select t*
        const tcount = readVarUint(body, state, "select type count");
        state.offset += tcount;
        break;
      }
      case 0x20:
      case 0x21:
      case 0x22:
      case 0x23:
      case 0x24:
      case 0xd2:
        readVarUint(body, state, "index immediate");
        break;
      case 0xd0:
        state.offset += 1;
        break;
      case 0x28:
      case 0x29:
      case 0x2a:
      case 0x2b:
      case 0x2c:
      case 0x2d:
      case 0x2e:
      case 0x2f:
      case 0x30:
      case 0x31:
      case 0x32:
      case 0x33:
      case 0x34:
      case 0x35:
      case 0x36:
      case 0x37:
      case 0x38:
      case 0x39:
      case 0x3a:
      case 0x3b:
      case 0x3c:
      case 0x3d:
      case 0x3e:
        skipMemoryArg(body, state, "memarg");
        break;
      case 0x3f:
      case 0x40:
        readVarUint(body, state, "memory index");
        break;
      case 0x41:
        readVarInt(body, state, 32, "i32.const");
        break;
      case 0x42:
        readVarInt(body, state, 64, "i64.const");
        break;
      case 0x43:
        state.offset += 4;
        break;
      case 0x44:
        state.offset += 8;
        break;
      case 0xfc: {
        const sub = readVarUint(body, state, "0xfc subopcode");
        switch (sub) {
          case 0:
          case 1:
          case 2:
          case 3:
          case 4:
          case 5:
          case 6:
          case 7:
            break;
          case 8:
            readVarUint(body, state, "memory.init data index");
            readVarUint(body, state, "memory.init memory index");
            break;
          case 9:
            readVarUint(body, state, "data.drop data index");
            break;
          case 10:
            readVarUint(body, state, "memory.copy dst memory");
            readVarUint(body, state, "memory.copy src memory");
            break;
          case 11:
            readVarUint(body, state, "memory.fill memory index");
            break;
          case 12:
            readVarUint(body, state, "table.init elem index");
            readVarUint(body, state, "table.init table index");
            break;
          case 13:
            readVarUint(body, state, "elem.drop elem index");
            break;
          case 14:
            readVarUint(body, state, "table.copy dst table");
            readVarUint(body, state, "table.copy src table");
            break;
          case 15:
          case 17:
            readVarUint(body, state, "table index");
            break;
          case 16:
            readVarUint(body, state, "table.grow table index");
            break;
          default:
            fail(`unsupported 0xfc subopcode ${sub}`);
        }
        break;
      }
      case 0xfd:
        fail("unsupported SIMD opcode prefix 0xfd in perf parser");
        break;
      default:
        if (
          op === 0x00 || op === 0x01 || op === 0x05 || op === 0x0b || op === 0x0f ||
          op === 0x1a || op === 0x1b || op === 0xd1 ||
          (op >= 0x45 && op <= 0xc4)
        ) {
          break;
        }
        fail(`unsupported opcode 0x${op.toString(16)}`);
    }
  }

  return {
    instructionCount: instructionCount >>> 0,
    callCount: callCount >>> 0,
    callIndirectCount: callIndirectCount >>> 0,
    ifCount: ifCount >>> 0,
    localCount: localCount >>> 0,
    importCallSites: mapToSortedObject(importCalls),
  };
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

function runEntryLoop(kernelExports, entryIndex, iterations) {
  let checksum = 0;
  for (let i = 0; i < iterations; i++) {
    const a = ((i * 13) & 255) - 128;
    const b = ((i * 7) & 255) - 128;
    const expected = a + b;
    const raw = kernelExports.wasm_test_entry_funcall2(entryIndex, a, b) >>> 0;
    const got = raw >> 2;
    if (got !== expected) {
      fail(`unexpected fixnum add loop result for entry ${entryIndex}: got=${got} expected=${expected}`);
    }
    checksum = (checksum + got) | 0;
  }
  return checksum | 0;
}

function benchmarkEntry(kernelExports, entryIndex, { warmup, iterations, rounds }) {
  runEntryLoop(kernelExports, entryIndex, warmup);
  const roundNsPerOp = [];
  let checksum = 0;
  for (let i = 0; i < rounds; i++) {
    const t0 = process.hrtime.bigint();
    checksum ^= runEntryLoop(kernelExports, entryIndex, iterations);
    const elapsedNs = Number(process.hrtime.bigint() - t0);
    roundNsPerOp.push(elapsedNs / iterations);
  }
  return {
    nsPerOpMedian: median(roundNsPerOp),
    nsPerOpMin: Math.min(...roundNsPerOp),
    nsPerOpMax: Math.max(...roundNsPerOp),
    roundNsPerOp: roundNsPerOp.map((v) => round3(v)),
    checksum: checksum | 0,
  };
}

async function collectDynamicImportCounts({
  moduleBytes,
  exportName,
  tableEntryIndex,
  runtime,
  microkernel,
  kernelExports,
  iterations,
}) {
  const tracked = [
    "wasm_pending_throw_p",
    "wasm_get_arg_z",
    "wasm_get_arg_y",
    "wasm_get_nargs",
    "wasm_set_arg_z",
    "wasm_set_arg_y",
    "wasm_set_nargs",
    "wasm_vsp_ref",
    "wasm_spill_push",
    "wasm_spill_pop",
    "wasm_return_fixnum_add",
  ];
  const counts = new Map();
  const wrapped = { ...kernelExports };
  for (const name of tracked) {
    if (typeof kernelExports[name] === "function") {
      wrapped[name] = (...fnArgs) => {
        counts.set(name, (counts.get(name) ?? 0) + 1);
        return kernelExports[name](...fnArgs);
      };
    }
  }

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
  runEntryLoop(kernelExports, tableEntryIndex, iterations);

  const perOp = new Map();
  for (const [name, count] of counts.entries()) {
    perOp.set(name, round3(count / iterations));
  }
  return {
    totalCalls: mapToSortedObject(counts),
    callsPerOperation: mapToSortedObject(perOp),
  };
}

const kernelUrl = new URL("./wasmcl.wasm", import.meta.url);
const subprimsUrl = new URL("./subprims.wasm", import.meta.url);
const subprimsMapUrl = new URL("../subprims-map.json", import.meta.url);
const imageUrl = new URL("../minimal.image", import.meta.url);
const bundleUrl = new URL("../wasm-smoke-modules.json", import.meta.url);

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

const entryIndex = 204;
const entry = entries.find((item) => item.entryIndex === entryIndex);
assert(entry, `missing compiled module entry ${entryIndex}`);

const a = 10;
const b = 12;
const result = kernel.instance.exports.wasm_test_entry_funcall2(entryIndex, a, b) >>> 0;
const resultFixnum = result >> 2;
assert(resultFixnum === a + b, `unexpected fixnum add result: got=${resultFixnum} expected=${a + b}`);

const args = process.argv.slice(2);
const perfCheckpoint = args.includes("--perf-checkpoint");
if (!perfCheckpoint) {
  console.log("PASS: wasm fixnum add smoke test");
  process.exit(0);
}

const perfIterations = readPositiveIntOption(args, "--perf-iterations", 300000);
const perfWarmup = readPositiveIntOption(args, "--perf-warmup", 60000);
const perfRounds = readPositiveIntOption(args, "--perf-rounds", 5);
const perfPathIterations = readPositiveIntOption(args, "--perf-path-iterations", 20000);
const perfOut = readOption(args, "--perf-out");

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

const bundleInstall = await installCompiledModulesFromBundle({
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
assert(bundleInstall.count > 0 && bundleInstall.installed > 0, "no modules installed from wasm-smoke-modules bundle");
assert(!bundleInstall.failed, `bundle install reported failed modules: ${bundleInstall.failed}`);

const bundleFunctions = Array.isArray(bundle.functions) ? bundle.functions : [];
const directFn = bundleFunctions.find((fn) => fn.name === "WASM-SMOKE-ADD");
assert(directFn, "missing WASM-SMOKE-ADD in wasm-smoke-modules bundle");
const directEntryIndex = directFn.entryIndex >>> 0;

const directResult = kernel.instance.exports.wasm_test_entry_funcall2(directEntryIndex, 10, 12) >>> 0;
const directFixnum = directResult >> 2;
assert(directFixnum === 22, `unexpected direct-lane add result: got=${directFixnum} expected=22`);

const directModule = await extractBundleModule(bundle, bundleBinaryBytes, bundleIndexBytes, directEntryIndex);
const compatMetrics = collectInstructionMetrics(entry.moduleBytes, entry.exportName);
const directMetrics = collectInstructionMetrics(directModule.moduleBytes, directModule.exportName);

const kernelExports = kernel.instance.exports;
const compatLatency = benchmarkEntry(kernelExports, entryIndex, {
  warmup: perfWarmup,
  iterations: perfIterations,
  rounds: perfRounds,
});
const directLatency = benchmarkEntry(kernelExports, directEntryIndex, {
  warmup: perfWarmup,
  iterations: perfIterations,
  rounds: perfRounds,
});

const compatDynamic = await collectDynamicImportCounts({
  moduleBytes: entry.moduleBytes,
  exportName: entry.exportName,
  tableEntryIndex: 940,
  runtime,
  microkernel,
  kernelExports,
  iterations: perfPathIterations,
});
const directDynamic = await collectDynamicImportCounts({
  moduleBytes: directModule.moduleBytes,
  exportName: directModule.exportName,
  tableEntryIndex: 941,
  runtime,
  microkernel,
  kernelExports,
  iterations: perfPathIterations,
});

const latencyDeltaNs = directLatency.nsPerOpMedian - compatLatency.nsPerOpMedian;
const latencyDeltaPct = compatLatency.nsPerOpMedian !== 0
  ? ((latencyDeltaNs / compatLatency.nsPerOpMedian) * 100)
  : 0;

const checkpoint = {
  capturedAt: new Date().toISOString(),
  host: {
    node: process.version,
    platform: process.platform,
    arch: process.arch,
  },
  options: {
    perfIterations,
    perfWarmup,
    perfRounds,
    perfPathIterations,
  },
  lanes: {
    beforeCompat: {
      label: "compat helper lane",
      entryIndex,
      exportName: entry.exportName,
      latency: {
        nsPerOpMedian: round3(compatLatency.nsPerOpMedian),
        nsPerOpMin: round3(compatLatency.nsPerOpMin),
        nsPerOpMax: round3(compatLatency.nsPerOpMax),
        roundNsPerOp: compatLatency.roundNsPerOp,
      },
      instructionPath: compatMetrics,
      dynamicPath: compatDynamic,
    },
    afterDirect: {
      label: "direct lowered lane",
      entryIndex: directEntryIndex,
      exportName: directModule.exportName,
      latency: {
        nsPerOpMedian: round3(directLatency.nsPerOpMedian),
        nsPerOpMin: round3(directLatency.nsPerOpMin),
        nsPerOpMax: round3(directLatency.nsPerOpMax),
        roundNsPerOp: directLatency.roundNsPerOp,
      },
      instructionPath: directMetrics,
      dynamicPath: directDynamic,
    },
  },
  deltas: {
    latencyNsPerOp: round3(latencyDeltaNs),
    latencyPct: round3(latencyDeltaPct),
    instructionCount: (directMetrics.instructionCount - compatMetrics.instructionCount) | 0,
    callCount: (directMetrics.callCount - compatMetrics.callCount) | 0,
    callIndirectCount: (directMetrics.callIndirectCount - compatMetrics.callIndirectCount) | 0,
    ifCount: (directMetrics.ifCount - compatMetrics.ifCount) | 0,
  },
};

console.log("CHECKPOINT: B10C-01A-17 fixnum-add performance evidence");
console.log(
  `  before/compat entry ${entryIndex}: ${round3(compatLatency.nsPerOpMedian)} ns/op median ` +
  `(min=${round3(compatLatency.nsPerOpMin)} max=${round3(compatLatency.nsPerOpMax)})`,
);
console.log(
  `  after/direct entry ${directEntryIndex}: ${round3(directLatency.nsPerOpMedian)} ns/op median ` +
  `(min=${round3(directLatency.nsPerOpMin)} max=${round3(directLatency.nsPerOpMax)})`,
);
console.log(
  `  delta (after-before): ${round3(latencyDeltaNs)} ns/op (${round3(latencyDeltaPct)}%)`,
);
console.log(
  "  dynamic helper calls/op (before -> after): " +
  `${checkpoint.lanes.beforeCompat.dynamicPath.callsPerOperation.wasm_return_fixnum_add ?? 0} -> ` +
  `${checkpoint.lanes.afterDirect.dynamicPath.callsPerOperation.wasm_return_fixnum_add ?? 0}`,
);

if (perfOut) {
  const outPath = path.resolve(process.cwd(), perfOut);
  await fs.mkdir(path.dirname(outPath), { recursive: true });
  await fs.writeFile(outPath, `${JSON.stringify(checkpoint, null, 2)}\n`);
  console.log(`CHECKPOINT: wrote ${outPath}`);
}

console.log("PASS: wasm fixnum add smoke test");
