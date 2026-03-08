/*
 * Minimal JS "microkernel" wiring for the CCL WASM ABI:
 * - One shared `WebAssembly.Table` for subprims (ordered like ARM sptab).
 * - (Optionally) one shared `WebAssembly.Memory`.
 *
 * This file intentionally avoids WASI; it assumes a browser/worker-like host.
 */

import {
  decodeModuleBundleIndexV2,
  MODULE_BUNDLE_V2_FORMAT,
  MODULE_BUNDLE_V2_DEFAULT_TEMPLATE_PREFIX,
} from "./module-bundle-v2.mjs";

import {
  FULLTAGMASK as FULLTAG_MASK,
  TAGMASK,
  FIXNUM_SHIFT,
  FULLTAG_CONS,
  FULLTAG_MISC,
  FULLTAG_NODEHEADER,
  FULLTAG_IMMHEADER,
  CONS_CDR_OFFSET,
  CONS_CAR_OFFSET,
  NUM_SUBTAG_BITS,
  SUBTAG_MASK,
  SUBTAG_SIMPLE_VECTOR,
  SUBTAG_U8_VECTOR,
  SUBTAG_SIMPLE_BASE_STRING,
} from "./abi-constants.mjs";

export function createCclImports({
  memory = null,
  subprimsTable,
  // Optional: kernel_request ABI provider. Accept either:
  //  - { imports: { kernel_request, ... } } (the object returned by createMicrokernel), or
  //  - { kernel_request, ... } (raw import function bag)
  microkernel = null,
  extra = {},
} = {}) {
  if (!subprimsTable) throw new Error("createCclImports: subprimsTable is required");

  const env = { ...extra.env };
  if (memory) env.memory = memory;
  // Most wasm toolchains use the default indirect function table name for
  // `call_indirect` (function-pointer) dispatch.
  env.__indirect_function_table = subprimsTable;
  if (!env.wasm_host_log) {
    const decoder = typeof TextDecoder !== "undefined" ? new TextDecoder("utf-8") : null;
    env.wasm_host_log = (ptr, len) => {
      try {
        if (!decoder || !memory) {
          // eslint-disable-next-line no-console
          console.error(`wasm_host_log(${ptr}, ${len})`);
          return;
        }
        const u8 = new Uint8Array(memory.buffer, ptr >>> 0, len >>> 0);
        const msg = decoder.decode(u8);
        // eslint-disable-next-line no-console
        console.error(msg);
      } catch (e) {
        // eslint-disable-next-line no-console
        console.error(`wasm_host_log failed: ${e}`);
      }
    };
  }

  // NOTE: The C side uses `import_module("ccl")`.
  // NOTE: The kernel_request ABI is copy-based for now (kernel_copy_response).
  // TODO(zero-copy): Optional future ABI extensions may write responses directly
  // into `memory` (caller-provided buffers or a shared arena/ring buffer) to avoid
  // this extra copy; the copy-based path remains the required baseline.
  const microkernelImports = microkernel ? (microkernel.imports ?? microkernel) : null;
  const ccl = {
    ...(microkernelImports ?? {}),
    ...extra.ccl,
    // Optional/compat: if your link step imports a named table, wire it here.
    subprims_table: subprimsTable,
  };
  if (typeof ccl.wasm_host_install_const_pool !== "function") {
    ccl.wasm_host_install_const_pool = () => 0;
  }
  if (typeof ccl.wasm_host_resolve_function_designator_entry !== "function") {
    ccl.wasm_host_resolve_function_designator_entry = () => -1;
  }
  if (typeof ccl.wasm_kernel_runtime_event !== "function") {
    ccl.wasm_kernel_runtime_event = () => -52; // -ENOSYS
  }
  if (typeof ccl.wasm_kernel_runtime_command_poll !== "function") {
    ccl.wasm_kernel_runtime_command_poll = (_maxBytes, _flags, _outBuf, _outCap, outLenPtr) => {
      if (memory && outLenPtr) {
        const view = new DataView(memory.buffer);
        view.setUint32(outLenPtr >>> 0, 0, true);
      }
      return -52; // -ENOSYS
    };
  }

  /* ── Type-adaptation wrappers ─────────────────────────────────────────
   * The WASM cross-compiler generates all FFI calls with i32 return type
   * (wasm2-external-call-type-index always selects an i32-returning type
   * index).  Void-returning C functions therefore need JS wrappers that
   * return 0 so the WASM import signature (i32)->i32 matches.
   *
   * Similarly, lisp_lseek/lisp_ftruncate use i64 args in C but the Lisp
   * FFI uses :signed-fullword (i32).  Those are handled by changing the
   * C signatures directly (see unix-calls.c WASM32 section).  These
   * wrappers handle only the void->i32 return-type cases where changing
   * the C signature would cause linker conflicts.
   */
  if (typeof ccl.free === "function") {
    const origFree = ccl.free;
    ccl.free = (p) => { origFree(p); return 0; };
  }
  if (typeof ccl.lisp_free === "function") {
    const origLispFree = ccl.lisp_free;
    ccl.lisp_free = (p) => { origLispFree(p); return 0; };
  }
  if (typeof ccl.lisp_bug === "function") {
    const origLispBug = ccl.lisp_bug;
    ccl.lisp_bug = (p) => { origLispBug(p); return 0; };
  }

  return { ...extra, env, ccl };
}

export function createSharedCclRuntime({
  subprimsTableInitial = 512,
  subprimsTableMaximum = undefined,
  // If you want a shared memory across multiple modules, build/link them with
  // an imported memory and pass it here.
  memoryInitialPages = 256,
  memoryMaximumPages = undefined,
  createMemory = true,
} = {}) {
  // API compatibility: some runtimes still expect `element: "anyfunc"` (older
  // name for the function reference type) instead of `"funcref"`.
  let subprimsTable;
  try {
    subprimsTable = new WebAssembly.Table({
      element: "funcref",
      initial: subprimsTableInitial,
      maximum: subprimsTableMaximum,
    });
  } catch (_e) {
    subprimsTable = new WebAssembly.Table({
      element: "anyfunc",
      initial: subprimsTableInitial,
      maximum: subprimsTableMaximum,
    });
  }

  const memory = createMemory
    ? new WebAssembly.Memory({
        initial: memoryInitialPages,
        maximum: memoryMaximumPages,
      })
    : null;

  return { memory, subprimsTable };
}

export async function fetchBytes(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`fetchBytes: ${res.status} ${res.statusText} (${url})`);
  return await res.arrayBuffer();
}

export async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`fetchJson: ${res.status} ${res.statusText} (${url})`);
  return await res.json();
}

export async function instantiateWasm(bytes, imports) {
  const { instance, module } = await WebAssembly.instantiate(bytes, imports);
  return { instance, module };
}

export function instantiateWasmSync(bytes, imports) {
  const module = new WebAssembly.Module(bytes);
  const instance = new WebAssembly.Instance(module, imports);
  return { instance, module };
}

export function installSubprimsTable({
  table,
  subprimsMap, // { symbols: ["_SP...", ...], count: N }
  providers, // [{ exports }, ...] in priority order; later providers override earlier
  verbose = false,
} = {}) {
  if (!table) throw new Error("installSubprimsTable: table is required");
  if (!subprimsMap?.symbols?.length) {
    throw new Error("installSubprimsTable: subprimsMap.symbols is required");
  }
  if (!Array.isArray(providers) || providers.length === 0) {
    throw new Error("installSubprimsTable: providers[] is required");
  }

  const symbols = subprimsMap.symbols;
  const needed = symbols.length;
  while (table.length < needed) table.grow(needed - table.length);

  let installed = 0;
  for (let i = 0; i < symbols.length; i++) {
    const sym = symbols[i];
    let fn = null;

    for (const p of providers) {
      const candidate = p?.exports?.[sym];
      if (typeof candidate === "function") fn = candidate;
    }

    if (fn) {
      table.set(i, fn);
      installed++;
      continue;
    }

    if (verbose) {
      // Leave null: call_indirect will trap if this subprim is invoked.
      // eslint-disable-next-line no-console
      console.warn(`subprim[${i}] ${sym}: not provided by any module`);
    }
  }

  return { installed, needed };
}

/* ABI constants now imported from abi-constants.mjs (generated from C headers) */

function u32(x) {
  return x >>> 0;
}

function readU32(view, addr) {
  return view.getUint32(u32(addr), true);
}

function isFixnum(obj) {
  return (obj & TAGMASK) === 0;
}

function fixnumValue(obj) {
  return obj >> FIXNUM_SHIFT;
}

function isCons(obj) {
  return (obj & FULLTAG_MASK) === FULLTAG_CONS;
}

function untag(obj, fulltag) {
  return u32(obj - fulltag);
}

function readMiscHeader(view, obj) {
  if ((obj & FULLTAG_MASK) !== FULLTAG_MISC) {
    throw new Error(`expected misc object, got 0x${u32(obj).toString(16)}`);
  }
  const base = untag(obj, FULLTAG_MISC);
  const header = readU32(view, base);
  return {
    base,
    header,
    subtag: header & SUBTAG_MASK,
    count: header >>> NUM_SUBTAG_BITS,
  };
}

function readSimpleVector(view, obj) {
  const { base, subtag, count } = readMiscHeader(view, obj);
  if (subtag !== SUBTAG_SIMPLE_VECTOR) {
    throw new Error(`expected simple-vector subtag, got 0x${subtag.toString(16)}`);
  }
  const out = new Array(count);
  let offset = base + 4;
  for (let i = 0; i < count; i++) {
    out[i] = readU32(view, offset);
    offset += 4;
  }
  return out;
}

function readU8Vector(view, memory, obj, expectedSubtag) {
  const { base, subtag, count } = readMiscHeader(view, obj);
  if (expectedSubtag != null && subtag !== expectedSubtag) {
    throw new Error(`unexpected u8-vector subtag 0x${subtag.toString(16)}`);
  }
  const bytes = new Uint8Array(memory.buffer, base + 4, count);
  return new Uint8Array(bytes);
}

function decodeBaseString(view, memory, obj) {
  const { base, subtag, count } = readMiscHeader(view, obj);
  if (subtag !== SUBTAG_SIMPLE_BASE_STRING) {
    throw new Error(`expected base string subtag, got 0x${subtag.toString(16)}`);
  }
  const codes = new Array(count);
  let offset = base + 4;
  for (let i = 0; i < count; i++) {
    codes[i] = readU32(view, offset) & 0xff;
    offset += 4;
  }
  if (typeof TextDecoder !== "undefined") {
    return new TextDecoder("utf-8").decode(Uint8Array.from(codes));
  }
  let out = "";
  for (let i = 0; i < codes.length; i++) {
    out += String.fromCharCode(codes[i]);
  }
  return out;
}

export function decodeCompiledModuleRegistry({ memory, registry, nil }) {
  if (!memory) throw new Error("decodeCompiledModuleRegistry: memory is required");
  if (registry == null) throw new Error("decodeCompiledModuleRegistry: registry is required");
  if (nil == null) throw new Error("decodeCompiledModuleRegistry: nil is required");

  const nilObj = u32(nil);
  let list = u32(registry);
  if (list === 0) return [];
  if (list === nilObj) return [];

  const view = new DataView(memory.buffer);
  const entries = [];
  let guard = 0;

  while (list !== nilObj) {
    if (!isCons(list)) {
      throw new Error(`compiled module registry is not a list: 0x${list.toString(16)}`);
    }
    const base = untag(list, FULLTAG_CONS);
    const car = readU32(view, base + CONS_CAR_OFFSET);
    const cdr = readU32(view, base + CONS_CDR_OFFSET);

    const vec = readSimpleVector(view, car);
    if (vec.length < 4) {
      throw new Error(`compiled module entry too short: ${vec.length}`);
    }

    const moduleBytes = readU8Vector(view, memory, vec[0], SUBTAG_U8_VECTOR);
    const exportName = decodeBaseString(view, memory, vec[1]);
    if (!isFixnum(vec[2]) || !isFixnum(vec[3])) {
      throw new Error("compiled module entry index/version must be fixnums");
    }
    const entryIndex = fixnumValue(vec[2]);
    const moduleVersion = fixnumValue(vec[3]);

    let constPoolBytes = null;
    if (vec.length >= 5 && vec[4] !== nilObj) {
      constPoolBytes = readU8Vector(view, memory, vec[4], SUBTAG_U8_VECTOR);
    }

    let gcRootPolicyMode = null;
    if (vec.length >= 6 && vec[5] !== nilObj) {
      if (!isFixnum(vec[5])) {
        throw new Error("compiled module gc root policy mode must be a fixnum");
      }
      const mode = fixnumValue(vec[5]);
      if (mode < 0) {
        throw new Error(`compiled module gc root policy mode must be non-negative: ${mode}`);
      }
      gcRootPolicyMode = mode >>> 0;
    }

    entries.push({ moduleBytes, exportName, entryIndex, moduleVersion, constPoolBytes, gcRootPolicyMode });

    list = cdr;
    guard++;
    if (guard > 100000) {
      throw new Error("compiled module registry appears cyclic");
    }
  }

  return entries;
}

function normalizeGcRootPolicyMode(value) {
  if (!Number.isFinite(value) || value < 0) return null;
  return value >>> 0;
}

function parseGcRootPolicyModes(rawMap) {
  const out = new Map();
  if (!rawMap || typeof rawMap !== "object") return out;
  for (const [key, value] of Object.entries(rawMap)) {
    const entryIndex = Number.parseInt(String(key), 10);
    if (!Number.isFinite(entryIndex) || entryIndex < 0) continue;
    const mode = normalizeGcRootPolicyMode(value);
    if (mode == null) continue;
    out.set(entryIndex >>> 0, mode);
  }
  return out;
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

function registerEntryCallAbi(setEntryCallAbi, entryIndex, fn) {
  if (typeof setEntryCallAbi !== "function") return;
  setEntryCallAbi(entryIndex >>> 0, inferEntryCallAbiKind(fn) >>> 0);
}

function alignUp(value, align) {
  return (value + (align - 1)) & ~(align - 1);
}

/* Scratch allocation state for reuse.  After wasm_const_pool_install
   returns, the scratch bytes at lastScratchBase are no longer needed and
   can be overwritten by the next call. */
let lastScratchBase = 0;
let lastScratchSize = 0;

function allocScratch(memory, size, kernelExports = null) {
  const pageSize = 65536;
  const aligned = alignUp(size, 16);
  /* Reuse previous scratch region if it is large enough. */
  if (lastScratchBase !== 0 && aligned <= lastScratchSize &&
      lastScratchBase + aligned <= memory.buffer.byteLength) {
    return lastScratchBase;
  }
  const base = memory.buffer.byteLength;
  const pages = Math.ceil(aligned / pageSize);
  if (pages > 0) {
    const growAndRelocate = kernelExports?.wasm_memory_grow_and_relocate;
    if (typeof growAndRelocate === "function") {
      const oldPages = growAndRelocate(pages >>> 0);
      if (oldPages === -1 || oldPages === 0xffffffff) {
        throw new Error(`wasm_memory_grow_and_relocate failed for ${pages} pages`);
      }
    } else {
      memory.grow(pages);
    }
  }
  lastScratchBase = base;
  lastScratchSize = pages * pageSize;
  return base;
}

export function normalizeBundleEncoding(value, fieldName = "encoding") {
  if (value == null || value === "" || value === "raw") return null;
  const normalized = String(value).toLowerCase();
  if (normalized === "br" || normalized === "brotli") return "br";
  if (normalized === "gzip" || normalized === "gz") return "gzip";
  if (normalized === "deflate") return "deflate";
  if (normalized === "deflate-raw") return "deflate-raw";
  throw new Error(`unsupported ${fieldName}: ${value}`);
}

function asU8(bytes) {
  if (bytes instanceof Uint8Array) return bytes;
  if (bytes instanceof ArrayBuffer) return new Uint8Array(bytes);
  if (ArrayBuffer.isView(bytes)) return new Uint8Array(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  return Uint8Array.from(bytes ?? []);
}

async function decompressBytes(bytes, encoding) {
  const input = asU8(bytes);
  if (!encoding) return input;

  if (typeof process !== "undefined" && process?.versions?.node) {
    const zlib = await import("node:zlib");
    switch (encoding) {
      case "br":
        return asU8(zlib.brotliDecompressSync(input));
      case "gzip":
        return asU8(zlib.gunzipSync(input));
      case "deflate":
        return asU8(zlib.inflateSync(input));
      case "deflate-raw":
        return asU8(zlib.inflateRawSync(input));
      default:
        throw new Error(`unsupported compression encoding: ${encoding}`);
    }
  }

  if (typeof DecompressionStream !== "undefined" && typeof Response !== "undefined") {
    const format = encoding === "gzip"
      ? "gzip"
      : encoding === "deflate"
        ? "deflate"
        : encoding === "br"
          ? "br"
          : null;
    if (!format) {
      throw new Error(`encoding ${encoding} requires node:zlib in this environment`);
    }
    let stream;
    try {
      stream = new Response(input).body?.pipeThrough(new DecompressionStream(format));
    } catch (e) {
      throw new Error(`cannot decode compressed bytes (${encoding}) with DecompressionStream: ${e}`);
    }
    if (!stream) throw new Error("decompression stream unavailable");
    const out = await new Response(stream).arrayBuffer();
    return new Uint8Array(out);
  }

  throw new Error(`cannot decode compressed bytes (${encoding}) in this environment`);
}

export function storedLengthFor(entry, rawField, storedField) {
  if (Number.isFinite(entry?.[storedField])) return entry[storedField] >>> 0;
  if (Number.isFinite(entry?.[rawField])) return entry[rawField] >>> 0;
  return 0;
}

export async function decodeBundleBytes(bytes, encodingField, expectedLength, kind) {
  const encoding = normalizeBundleEncoding(encodingField, `${kind} encoding`);
  const decoded = await decompressBytes(bytes, encoding);
  if (Number.isFinite(expectedLength)) {
    const expected = expectedLength >>> 0;
    if (decoded.length !== expected) {
      throw new Error(`${kind} length mismatch: expected ${expected}, got ${decoded.length}`);
    }
  }
  return decoded;
}

export function decodeBundleBytesSync(bytes, encodingField, expectedLength, kind, zlibImpl = null) {
  const encoding = normalizeBundleEncoding(encodingField, `${kind} encoding`);
  const input = asU8(bytes);
  let decoded = input;
  if (encoding) {
    if (!zlibImpl) {
      throw new Error(`cannot decode compressed bytes (${encoding}) without zlib implementation`);
    }
    switch (encoding) {
      case "br":
        decoded = asU8(zlibImpl.brotliDecompressSync(input));
        break;
      case "gzip":
        decoded = asU8(zlibImpl.gunzipSync(input));
        break;
      case "deflate":
        decoded = asU8(zlibImpl.inflateSync(input));
        break;
      case "deflate-raw":
        decoded = asU8(zlibImpl.inflateRawSync(input));
        break;
      default:
        throw new Error(`unsupported compression encoding: ${encoding}`);
    }
  }
  if (Number.isFinite(expectedLength)) {
    const expected = expectedLength >>> 0;
    if (decoded.length !== expected) {
      throw new Error(`${kind} length mismatch: expected ${expected}, got ${decoded.length}`);
    }
  }
  return decoded;
}

const bundleIndexCache = new WeakMap();

function isBundleV2(bundle) {
  if (!bundle || typeof bundle !== "object") return false;
  if (bundle.format === MODULE_BUNDLE_V2_FORMAT) return true;
  if (typeof bundle.index === "string" && bundle.index.length > 0) return true;
  return false;
}

async function readAllFromReader(reader, chunkSize = 1 << 20) {
  const chunks = [];
  let offset = 0;
  for (;;) {
    const chunk = await reader(offset, chunkSize);
    const bytes = asU8(chunk);
    if (bytes.length === 0) break;
    chunks.push(bytes);
    offset += bytes.length;
  }
  let total = 0;
  for (const chunk of chunks) total += chunk.length;
  const out = new Uint8Array(total);
  let cursor = 0;
  for (const chunk of chunks) {
    out.set(chunk, cursor);
    cursor += chunk.length;
  }
  return out;
}

export async function resolveBundleEntries({
  bundle,
  indexBytes = null,
  indexReader = null,
} = {}) {
  if (!bundle || typeof bundle !== "object") {
    return { modules: [], constPools: [] };
  }

  if (!isBundleV2(bundle)) {
    throw new Error("resolveBundleEntries: unsupported bundle format (only ccl-wasm-modules-v2 is supported)");
  }

  if (bundleIndexCache.has(bundle)) {
    return bundleIndexCache.get(bundle);
  }

  let indexBlob = indexBytes ?? bundle.indexBytes ?? null;
  if (!indexBlob && typeof indexReader === "function") {
    indexBlob = await readAllFromReader(indexReader);
  }
  if (!indexBlob) {
    throw new Error("resolveBundleEntries: v2 bundle requires index bytes");
  }

  const templatePrefix =
    typeof bundle.exportNameTemplatePrefix === "string" && bundle.exportNameTemplatePrefix.length > 0
      ? bundle.exportNameTemplatePrefix
      : MODULE_BUNDLE_V2_DEFAULT_TEMPLATE_PREFIX;
  const resolved = decodeModuleBundleIndexV2(indexBlob, { templatePrefix });
  bundleIndexCache.set(bundle, resolved);
  return resolved;
}

export function installConstPoolBytes({
  kernel = null,
  kernelExports = null,
  memory,
  entryIndex,
  constPoolBytes,
} = {}) {
  if (!memory) throw new Error("installConstPoolBytes: memory is required");

  const exports = kernelExports ?? kernel?.instance?.exports ?? kernel?.exports ?? kernel;
  if (!exports) throw new Error("installConstPoolBytes: kernel exports are required");

  const install = exports.wasm_const_pool_install;
  if (typeof install !== "function") {
    throw new Error("installConstPoolBytes: missing wasm_const_pool_install export");
  }

  if (!constPoolBytes || constPoolBytes.length === 0) return 0;
  const bytes = constPoolBytes instanceof Uint8Array
    ? constPoolBytes
    : Uint8Array.from(constPoolBytes);
  const base = allocScratch(memory, bytes.length, exports);
  new Uint8Array(memory.buffer, base, bytes.length).set(bytes);
  return install(entryIndex >>> 0, base >>> 0, bytes.length >>> 0) >>> 0;
}

export async function installCompiledModulesFromBundle({
  bundle,
  binaryBytes = null,
  binaryReader = null,
  indexBytes = null,
  indexReader = null,
  kernel,
  memory,
  subprimsTable,
  microkernel = null,
  extra = {},
  verbose = false,
  strict = true,
  installConstPools = true,
  excludeEntries = null,
  clearEntryFnCache = true,
} = {}) {
  if (!memory) throw new Error("installCompiledModulesFromBundle: memory is required");
  if (!subprimsTable) throw new Error("installCompiledModulesFromBundle: subprimsTable is required");

  const kernelExports = kernel?.instance?.exports ?? kernel?.exports ?? kernel;
  if (!kernelExports) throw new Error("installCompiledModulesFromBundle: kernel exports are required");

  const resolved = await resolveBundleEntries({ bundle, indexBytes, indexReader });
  const modules = Array.isArray(resolved?.modules) ? resolved.modules : [];
  const bundleGcRootModes = parseGcRootPolicyModes(bundle?.gcRootPolicyModes);
  for (const entry of modules) {
    const idx = Number.isFinite(entry?.entryIndex) ? (entry.entryIndex >>> 0) : null;
    if (idx == null) continue;
    const explicitMode = normalizeGcRootPolicyMode(entry?.gcRootPolicyMode);
    if (explicitMode != null) {
      entry.gcRootPolicyMode = explicitMode;
      bundleGcRootModes.set(idx, explicitMode);
      continue;
    }
    const mappedMode = bundleGcRootModes.get(idx);
    if (mappedMode != null) {
      entry.gcRootPolicyMode = mappedMode;
    }
  }
  if (modules.length === 0) return { installed: 0, count: 0, entries: [] };

  const extraCcl = { ...(extra.ccl ?? {}), ...kernelExports };
  const imports = createCclImports({
    memory,
    subprimsTable,
    microkernel,
    extra: { ...extra, ccl: extraCcl },
  });
  const nilValue = typeof kernelExports.wasm_get_lisp_nil === "function"
    ? (kernelExports.wasm_get_lisp_nil() >>> 0)
    : null;
  const hasPendingThrowProbe = typeof kernelExports.wasm_pending_throw_p === "function";
  const setEntryGcRootPolicyMode = typeof kernelExports.wasm_set_entry_gc_root_policy_mode === "function"
    ? kernelExports.wasm_set_entry_gc_root_policy_mode
    : null;
  const setEntryCallAbi = typeof kernelExports.wasm_set_entry_call_abi === "function"
    ? kernelExports.wasm_set_entry_call_abi
    : null;

  let installed = 0;
  let failed = 0;
  const readBinary = typeof binaryReader === "function" ? binaryReader : null;
  const bundleConstPoolBlob =
    Number.isFinite(bundle?.constPoolBlobOffset) && Number.isFinite(bundle?.constPoolBlobLength)
      ? {
          offset: bundle.constPoolBlobOffset >>> 0,
          length: bundle.constPoolBlobLength >>> 0,
          storedLength: Number.isFinite(bundle?.constPoolBlobStoredLength)
            ? (bundle.constPoolBlobStoredLength >>> 0)
            : (bundle.constPoolBlobLength >>> 0),
          encoding: normalizeBundleEncoding(bundle?.constPoolBlobEncoding ?? null, "const pool shared blob encoding"),
        }
      : null;
  const spanKey = (offset, storedLength, encoding, rawLength) =>
    `${offset >>> 0}:${storedLength >>> 0}:${encoding ?? "raw"}:${Number.isFinite(rawLength) ? (rawLength >>> 0) : 0}`;
  const bumpRef = (table, key) => {
    table.set(key, (table.get(key) ?? 0) + 1);
  };
  const moduleSpanRefCounts = new Map();
  const constPoolSpanRefCounts = new Map();
  const constPoolEntriesById = new Map();
  for (const entry of modules) {
    const moduleStoredLength = storedLengthFor(entry, "length", "moduleStoredLength");
    const moduleEncoding = normalizeBundleEncoding(entry?.moduleEncoding ?? null, "module encoding");
    if (Number.isFinite(entry?.offset) && moduleStoredLength > 0) {
      const key = spanKey(entry.offset, moduleStoredLength, moduleEncoding, entry.length);
      bumpRef(moduleSpanRefCounts, key);
    }

    const constPoolStoredLength = storedLengthFor(entry, "constPoolLength", "constPoolStoredLength");
    const constPoolEncoding = normalizeBundleEncoding(entry?.constPoolEncoding ?? null, "const pool encoding");
    if (Number.isFinite(entry?.constPoolOffset) && constPoolStoredLength > 0) {
      const key = spanKey(entry.constPoolOffset, constPoolStoredLength, constPoolEncoding, entry.constPoolLength);
      bumpRef(constPoolSpanRefCounts, key);
    }

    if (Number.isFinite(entry?.constPoolId)) {
      const poolId = entry.constPoolId >>> 0;
      if (!constPoolEntriesById.has(poolId)) {
        constPoolEntriesById.set(poolId, entry);
      }
    }
  }

  const moduleSpanCache = new Map();
  const constPoolSpanCache = new Map();
  const constPoolDecodedById = new Map();
  const constPoolInstalledByPoolId = new Map(); // poolId -> first entryIndex that installed it
  let aliasCount = 0;
  const constPoolDecodeInFlight = new Set();
  let constPoolSharedBlobRaw = null;
  let constPoolSharedBlobRawInFlight = null;

  async function loadConstPoolSharedBlobRaw() {
    if (!bundleConstPoolBlob) return null;
    if (constPoolSharedBlobRaw) return constPoolSharedBlobRaw;
    if (constPoolSharedBlobRawInFlight) return constPoolSharedBlobRawInFlight;

    constPoolSharedBlobRawInFlight = (async () => {
      let storedBytes;
      if (binaryBytes) {
        const start = bundleConstPoolBlob.offset;
        const end = start + bundleConstPoolBlob.storedLength;
        if (end > binaryBytes.length) {
          throw new Error(
            `const pool shared blob span out of bounds: ${start}+${bundleConstPoolBlob.storedLength} > ${binaryBytes.length}`,
          );
        }
        storedBytes = binaryBytes.subarray(start, end);
      } else if (readBinary) {
        storedBytes = await readBinary(bundleConstPoolBlob.offset, bundleConstPoolBlob.storedLength);
      } else {
        throw new Error("const pool shared blob requires binary bytes or binaryReader");
      }
      constPoolSharedBlobRaw = await decodeBundleBytes(
        storedBytes,
        bundleConstPoolBlob.encoding,
        bundleConstPoolBlob.length,
        "const pool shared blob",
      );
      return constPoolSharedBlobRaw;
    })();
    try {
      return await constPoolSharedBlobRawInFlight;
    } finally {
      constPoolSharedBlobRawInFlight = null;
    }
  }

  async function loadModuleBytes(entry) {
    let moduleBytes = entry.moduleBytes ?? null;
    const moduleStoredLength = storedLengthFor(entry, "length", "moduleStoredLength");
    const moduleEncoding = normalizeBundleEncoding(entry.moduleEncoding ?? null, "module encoding");
    if (!moduleBytes && binaryBytes && Number.isFinite(entry.offset) && moduleStoredLength > 0) {
      const start = entry.offset >>> 0;
      const end = start + moduleStoredLength;
      const cacheKey = spanKey(start, moduleStoredLength, moduleEncoding, entry.length);
      const shouldCache = (moduleSpanRefCounts.get(cacheKey) ?? 0) > 1;
      if (shouldCache && moduleSpanCache.has(cacheKey)) {
        moduleBytes = moduleSpanCache.get(cacheKey);
      } else {
        const rawBytes = binaryBytes.subarray(start, end);
        moduleBytes = await decodeBundleBytes(rawBytes, moduleEncoding, entry.length, "module");
        if (shouldCache) moduleSpanCache.set(cacheKey, moduleBytes);
      }
    } else if (!moduleBytes && readBinary && Number.isFinite(entry.offset) && moduleStoredLength > 0) {
      const start = entry.offset >>> 0;
      const cacheKey = spanKey(start, moduleStoredLength, moduleEncoding, entry.length);
      const shouldCache = (moduleSpanRefCounts.get(cacheKey) ?? 0) > 1;
      if (shouldCache && moduleSpanCache.has(cacheKey)) {
        moduleBytes = moduleSpanCache.get(cacheKey);
      } else {
        const rawBytes = await readBinary(start, moduleStoredLength);
        moduleBytes = await decodeBundleBytes(rawBytes, moduleEncoding, entry.length, "module");
        if (shouldCache) moduleSpanCache.set(cacheKey, moduleBytes);
      }
    } else if (moduleBytes && moduleEncoding) {
      moduleBytes = await decodeBundleBytes(moduleBytes, moduleEncoding, entry.length, "module");
    }
    return moduleBytes;
  }

  async function loadConstPoolRawBytes(entry) {
    let constPoolBytes = entry.constPoolBytes ?? null;
    const constPoolStoredLength = storedLengthFor(entry, "constPoolLength", "constPoolStoredLength");
    const constPoolEncoding = normalizeBundleEncoding(entry.constPoolEncoding ?? null, "const pool encoding");
    if (!constPoolBytes && bundleConstPoolBlob &&
        Number.isFinite(entry.constPoolOffset) && constPoolStoredLength > 0) {
      const start = entry.constPoolOffset >>> 0;
      const end = start + constPoolStoredLength;
      const cacheKey = spanKey(start, constPoolStoredLength, constPoolEncoding, entry.constPoolLength);
      const shouldCache = (constPoolSpanRefCounts.get(cacheKey) ?? 0) > 1;
      if (shouldCache && constPoolSpanCache.has(cacheKey)) {
        constPoolBytes = constPoolSpanCache.get(cacheKey);
      } else {
        const sharedRaw = await loadConstPoolSharedBlobRaw();
        if (!sharedRaw) {
          throw new Error("const pool shared blob metadata present but blob is unavailable");
        }
        if (end > sharedRaw.length) {
          throw new Error(
            `const pool span out of bounds in shared blob: ${start}+${constPoolStoredLength} > ${sharedRaw.length}`,
          );
        }
        const rawBytes = sharedRaw.subarray(start, end);
        constPoolBytes = await decodeBundleBytes(rawBytes, constPoolEncoding, entry.constPoolLength, "const pool");
        if (shouldCache) constPoolSpanCache.set(cacheKey, constPoolBytes);
      }
    } else if (!constPoolBytes && binaryBytes &&
        Number.isFinite(entry.constPoolOffset) && constPoolStoredLength > 0) {
      const start = entry.constPoolOffset >>> 0;
      const end = start + constPoolStoredLength;
      const cacheKey = spanKey(start, constPoolStoredLength, constPoolEncoding, entry.constPoolLength);
      const shouldCache = (constPoolSpanRefCounts.get(cacheKey) ?? 0) > 1;
      if (shouldCache && constPoolSpanCache.has(cacheKey)) {
        constPoolBytes = constPoolSpanCache.get(cacheKey);
      } else {
        const rawBytes = binaryBytes.subarray(start, end);
        constPoolBytes = await decodeBundleBytes(rawBytes, constPoolEncoding, entry.constPoolLength, "const pool");
        if (shouldCache) constPoolSpanCache.set(cacheKey, constPoolBytes);
      }
    } else if (!constPoolBytes && readBinary &&
        Number.isFinite(entry.constPoolOffset) && constPoolStoredLength > 0) {
      const start = entry.constPoolOffset >>> 0;
      const cacheKey = spanKey(start, constPoolStoredLength, constPoolEncoding, entry.constPoolLength);
      const shouldCache = (constPoolSpanRefCounts.get(cacheKey) ?? 0) > 1;
      if (shouldCache && constPoolSpanCache.has(cacheKey)) {
        constPoolBytes = constPoolSpanCache.get(cacheKey);
      } else {
        const rawBytes = await readBinary(start, constPoolStoredLength);
        constPoolBytes = await decodeBundleBytes(rawBytes, constPoolEncoding, entry.constPoolLength, "const pool");
        if (shouldCache) constPoolSpanCache.set(cacheKey, constPoolBytes);
      }
    } else if (constPoolBytes && constPoolEncoding) {
      constPoolBytes = await decodeBundleBytes(constPoolBytes, constPoolEncoding, entry.constPoolLength, "const pool");
    }
    return constPoolBytes;
  }

  async function resolveConstPoolBytes(entry) {
    const hasPoolFields =
      Number.isFinite(entry?.constPoolOffset) ||
      Number.isFinite(entry?.constPoolLength) ||
      (entry?.constPoolBytes != null);
    if (!hasPoolFields) return null;

    const poolId = Number.isFinite(entry?.constPoolId) ? (entry.constPoolId >>> 0) : null;
    if (poolId != null && constPoolDecodedById.has(poolId)) {
      return constPoolDecodedById.get(poolId);
    }
    if (poolId != null) {
      if (constPoolDecodeInFlight.has(poolId)) {
        throw new Error(`const pool decode cycle at id ${poolId}`);
      }
      constPoolDecodeInFlight.add(poolId);
    }

    try {
      let constPoolBytes = await loadConstPoolRawBytes(entry);
      if (!constPoolBytes || constPoolBytes.length === 0) {
        if (poolId != null) constPoolDecodedById.set(poolId, constPoolBytes);
        return constPoolBytes;
      }

      const baseId = Number.isFinite(entry?.constPoolDeltaBaseId)
        ? (entry.constPoolDeltaBaseId >>> 0)
        : null;
      const deltaOp = entry?.constPoolDeltaOp ?? null;
      if (baseId != null) {
        if (deltaOp !== "xor") {
          throw new Error(`unsupported const pool delta op: ${deltaOp ?? "<missing>"}`);
        }
        const baseEntry = constPoolEntriesById.get(baseId);
        if (!baseEntry) {
          throw new Error(`missing const pool delta base id: ${baseId}`);
        }
        const baseBytes = await resolveConstPoolBytes(baseEntry);
        if (!baseBytes || baseBytes.length !== constPoolBytes.length) {
          throw new Error(
            `const pool delta size mismatch: base ${baseBytes?.length ?? 0}, delta ${constPoolBytes.length}`,
          );
        }
        const out = new Uint8Array(constPoolBytes.length);
        for (let i = 0; i < constPoolBytes.length; i++) {
          out[i] = constPoolBytes[i] ^ baseBytes[i];
        }
        constPoolBytes = out;
      }

      if (Number.isFinite(entry?.constPoolLength)) {
        const expected = entry.constPoolLength >>> 0;
        if (constPoolBytes.length !== expected) {
          throw new Error(`const pool length mismatch: expected ${expected}, got ${constPoolBytes.length}`);
        }
      }

      if (poolId != null) constPoolDecodedById.set(poolId, constPoolBytes);
      return constPoolBytes;
    } finally {
      if (poolId != null) constPoolDecodeInFlight.delete(poolId);
    }
  }

  const moduleInstanceCache = new Map();
  const compilationPromises = new Map(); // cacheKey -> Promise<instance>
  let _moduleInstallCount = 0;
  const _moduleTotal = modules.length;
  let excluded = 0;

  // Parallel prefetch+compile, sequential registration.
  // resolveConstPoolBytes uses constPoolDecodeInFlight cycle detection
  // and is NOT safe for concurrent calls, so it stays in Phase 2.
  const BATCH_SIZE = 64;
  for (let batchStart = 0; batchStart < modules.length; batchStart += BATCH_SIZE) {
    const batch = modules.slice(batchStart, batchStart + BATCH_SIZE);

    // Phase 1: parallel load + compile (no kernel state touched)
    const prepared = await Promise.all(batch.map(async (entry) => {
      if (excludeEntries && excludeEntries.has(entry.entryIndex >>> 0)) {
        return { entry, excluded: true };
      }
      try {
        const moduleBytes = await loadModuleBytes(entry);
        if (!moduleBytes || moduleBytes.length === 0) {
          return { entry, error: new Error(`compiled module missing bytes for ${entry.exportName}`) };
        }

        const instCacheKey = Number.isFinite(entry?.offset) ? `${entry.offset}:${entry.length}` : null;
        let instance = instCacheKey ? moduleInstanceCache.get(instCacheKey) : undefined;
        if (!instance) {
          // Deduplicate in-flight compilations across the batch
          let promise = instCacheKey ? compilationPromises.get(instCacheKey) : undefined;
          if (!promise) {
            const bytes = moduleBytes instanceof Uint8Array ? moduleBytes : Uint8Array.from(moduleBytes);
            promise = instantiateWasm(bytes, imports).then(r => {
              if (instCacheKey) moduleInstanceCache.set(instCacheKey, r.instance);
              return r.instance;
            });
            if (instCacheKey) compilationPromises.set(instCacheKey, promise);
          }
          instance = await promise;
        }
        return { entry, instance, error: null };
      } catch (e) {
        return { entry, error: e };
      }
    }));

    // Phase 2: sequential const-pool resolution + registration (kernel state)
    for (const item of prepared) {
      const { entry } = item;
      if (item.excluded) {
        excluded++;
        _moduleInstallCount++;
        continue;
      }
      if (item.error) {
        failed++;
        _moduleInstallCount++;
        // eslint-disable-next-line no-console
        console.warn(`[module-fail] entry=${entry.entryIndex} export=${entry.exportName}: ${item.error.message ?? item.error}`);
        if (strict) {
          throw new Error(
            `compiled module install failed ${entry.exportName} (entry ${entry.entryIndex}): ${item.error}`,
            { cause: item.error },
          );
        }
        continue;
      }

      try {
        const constPoolBytes = await resolveConstPoolBytes(entry);

        if (installConstPools && constPoolBytes?.length) {
          const poolId = Number.isFinite(entry?.constPoolId) ? (entry.constPoolId >>> 0) : null;
          const aliasSource = undefined; // aliasing disabled — shared elements cause cold-boot-init mutation conflicts
          if (aliasSource != null && typeof kernelExports.wasm_const_pool_alias === "function") {
            // Same pool bytes already installed for another entry — alias instead of reinstalling
            const aliasResult = kernelExports.wasm_const_pool_alias(entry.entryIndex >>> 0, aliasSource >>> 0);
            aliasCount++;
            if (nilValue != null && (aliasResult >>> 0) === nilValue) {
              throw new Error(`const pool alias returned NIL for entry ${entry.entryIndex} (source ${aliasSource})`);
            }
          } else {
            const installResult = installConstPoolBytes({
              kernelExports,
              memory,
              entryIndex: entry.entryIndex,
              constPoolBytes,
            });
            if (nilValue != null && (installResult >>> 0) === nilValue) {
              throw new Error(`const pool install returned NIL for entry ${entry.entryIndex}`);
            }
            if (hasPendingThrowProbe && (kernelExports.wasm_pending_throw_p() >>> 0)) {
              throw new Error(`const pool install signaled pending throw for entry ${entry.entryIndex}`);
            }
            if (poolId != null) {
              constPoolInstalledByPoolId.set(poolId, entry.entryIndex >>> 0);
            }
          }
        }

        if (setEntryGcRootPolicyMode) {
          const mode = normalizeGcRootPolicyMode(entry?.gcRootPolicyMode);
          if (mode != null) {
            setEntryGcRootPolicyMode(entry.entryIndex >>> 0, mode);
          }
        }

        const fn = item.instance?.exports?.[entry.exportName];
        if (typeof fn !== "function") {
          throw new Error(`compiled module missing export ${entry.exportName}`);
        }

        const idx = entry.entryIndex >>> 0;
        if (subprimsTable.length <= idx) {
          subprimsTable.grow(idx - subprimsTable.length + 1);
        }
        subprimsTable.set(idx, fn);
        registerEntryCallAbi(setEntryCallAbi, idx, fn);
        installed++;
        _moduleInstallCount++;
        if (_moduleInstallCount % 500 === 0) {
          // eslint-disable-next-line no-console
          console.error(`[progress] modules: ${_moduleInstallCount}/${_moduleTotal} installed (entry ${idx})`);
        }
      } catch (e) {
        failed++;
        _moduleInstallCount++;
        // eslint-disable-next-line no-console
        console.warn(`[module-fail] entry=${entry.entryIndex} export=${entry.exportName}: ${e.message ?? e}`);
        if (strict) {
          throw new Error(
            `compiled module install failed ${entry.exportName} (entry ${entry.entryIndex}): ${e}`,
            { cause: e },
          );
        }
        continue;
      }
    }
  }

  // Release the entry-function dedup cache now that all pools are installed
  if (clearEntryFnCache && typeof kernelExports.wasm_entry_fn_cache_clear === "function") {
    kernelExports.wasm_entry_fn_cache_clear();
  }
  if (aliasCount > 0) {
    console.log(`[stage] const pool aliasing: ${aliasCount} aliased, ${constPoolInstalledByPoolId.size} unique`);
  }

  return { installed, count: modules.length, failed, excluded, entries: modules };
}

/**
 * Fill all null slots in the indirect-function table with a trap stub.
 * Converts opaque `RuntimeError: unreachable` from WASM call_indirect on
 * null table entries into diagnosable Lisp XNOTFUN errors.
 *
 * @param {WebAssembly.Table} subprimsTable
 * @param {Function} trapFn — typically subprims.exports._SPentry_not_installed
 * @returns {{ filled: number }}
 */
export function fillNullTableSlots({ subprimsTable, trapFn }) {
  let filled = 0;
  for (let i = 0; i < subprimsTable.length; i++) {
    if (subprimsTable.get(i) === null) {
      subprimsTable.set(i, trapFn);
      filled++;
    }
  }
  return { filled };
}

export async function installCompiledModulesFromRegistry({
  kernel,
  memory,
  subprimsTable,
  microkernel = null,
  extra = {},
  registry = null,
  nil = null,
  verbose = false,
} = {}) {
  if (!memory) throw new Error("installCompiledModulesFromRegistry: memory is required");
  if (!subprimsTable) throw new Error("installCompiledModulesFromRegistry: subprimsTable is required");

  const kernelExports = kernel?.instance?.exports ?? kernel?.exports ?? kernel;
  if (!kernelExports) throw new Error("installCompiledModulesFromRegistry: kernel exports are required");

  if (registry == null) {
    const getRegistry = kernelExports.wasm_get_compiled_module_registry;
    if (typeof getRegistry !== "function") {
      return { installed: 0, count: 0, entries: [], skipped: "no registry export" };
    }
    registry = getRegistry() >>> 0;
  }
  if (nil == null) {
    const getNil = kernelExports.wasm_get_lisp_nil;
    if (typeof getNil !== "function") {
      return { installed: 0, count: 0, entries: [], skipped: "no nil export" };
    }
    nil = getNil() >>> 0;
  }

  /* The registry may contain an unbound marker or other non-list value
     (e.g. when the symbol exists in the boot image but was never assigned
     a value).  Only attempt to decode when the value is nil or a cons. */
  if (registry !== 0 && registry !== nil && !isCons(registry)) {
    return { installed: 0, count: 0, entries: [], skipped: "registry is not a list" };
  }
  const entries = decodeCompiledModuleRegistry({ memory, registry, nil });
  if (entries.length === 0) return { installed: 0, count: 0, entries: [] };

  const extraCcl = { ...(extra.ccl ?? {}), ...kernelExports };
  const imports = createCclImports({
    memory,
    subprimsTable,
    microkernel,
    extra: { ...extra, ccl: extraCcl },
  });
  const setEntryGcRootPolicyMode = typeof kernelExports.wasm_set_entry_gc_root_policy_mode === "function"
    ? kernelExports.wasm_set_entry_gc_root_policy_mode
    : null;
  const setEntryCallAbi = typeof kernelExports.wasm_set_entry_call_abi === "function"
    ? kernelExports.wasm_set_entry_call_abi
    : null;

  let installed = 0;
  for (const entry of entries) {
    if (entry.constPoolBytes?.length) {
      installConstPoolBytes({
        kernelExports,
        memory,
        entryIndex: entry.entryIndex,
        constPoolBytes: entry.constPoolBytes,
      });
    }
    if (setEntryGcRootPolicyMode) {
      const mode = normalizeGcRootPolicyMode(entry?.gcRootPolicyMode);
      if (mode != null) {
        setEntryGcRootPolicyMode(entry.entryIndex >>> 0, mode);
      }
    }
    const { instance } = await instantiateWasm(entry.moduleBytes, imports);
    const fn = instance?.exports?.[entry.exportName];
    if (typeof fn !== "function") {
      if (verbose) {
        // eslint-disable-next-line no-console
        console.warn(`compiled module missing export ${entry.exportName}`);
      }
      continue;
    }

    if (subprimsTable.length <= entry.entryIndex) {
      subprimsTable.grow(entry.entryIndex - subprimsTable.length + 1);
    }
    subprimsTable.set(entry.entryIndex, fn);
    registerEntryCallAbi(setEntryCallAbi, entry.entryIndex, fn);
    installed++;
  }

  return { installed, count: entries.length, entries };
}

export function installCompiledModulesFromRegistrySync({
  kernel,
  memory,
  subprimsTable,
  microkernel = null,
  extra = {},
  registry = null,
  nil = null,
  verbose = false,
} = {}) {
  if (!memory) throw new Error("installCompiledModulesFromRegistrySync: memory is required");
  if (!subprimsTable) throw new Error("installCompiledModulesFromRegistrySync: subprimsTable is required");

  const kernelExports = kernel?.instance?.exports ?? kernel?.exports ?? kernel;
  if (!kernelExports) throw new Error("installCompiledModulesFromRegistrySync: kernel exports are required");

  if (registry == null) {
    const getRegistry = kernelExports.wasm_get_compiled_module_registry;
    if (typeof getRegistry !== "function") {
      throw new Error("installCompiledModulesFromRegistrySync: missing wasm_get_compiled_module_registry export");
    }
    registry = getRegistry() >>> 0;
  }
  if (nil == null) {
    const getNil = kernelExports.wasm_get_lisp_nil;
    if (typeof getNil !== "function") {
      throw new Error("installCompiledModulesFromRegistrySync: missing wasm_get_lisp_nil export");
    }
    nil = getNil() >>> 0;
  }

  const entries = decodeCompiledModuleRegistry({ memory, registry, nil });
  if (entries.length === 0) return { installed: 0, count: 0, entries: [] };

  const extraCcl = { ...(extra.ccl ?? {}), ...kernelExports };
  const imports = createCclImports({
    memory,
    subprimsTable,
    microkernel,
    extra: { ...extra, ccl: extraCcl },
  });
  const setEntryGcRootPolicyMode = typeof kernelExports.wasm_set_entry_gc_root_policy_mode === "function"
    ? kernelExports.wasm_set_entry_gc_root_policy_mode
    : null;
  const setEntryCallAbi = typeof kernelExports.wasm_set_entry_call_abi === "function"
    ? kernelExports.wasm_set_entry_call_abi
    : null;

  let installed = 0;
  for (const entry of entries) {
    if (entry.constPoolBytes?.length) {
      installConstPoolBytes({
        kernelExports,
        memory,
        entryIndex: entry.entryIndex,
        constPoolBytes: entry.constPoolBytes,
      });
    }
    if (setEntryGcRootPolicyMode) {
      const mode = normalizeGcRootPolicyMode(entry?.gcRootPolicyMode);
      if (mode != null) {
        setEntryGcRootPolicyMode(entry.entryIndex >>> 0, mode);
      }
    }
    const { instance } = instantiateWasmSync(entry.moduleBytes, imports);
    const fn = instance?.exports?.[entry.exportName];
    if (typeof fn !== "function") {
      if (verbose) {
        // eslint-disable-next-line no-console
        console.warn(`compiled module missing export ${entry.exportName}`);
      }
      continue;
    }

    if (subprimsTable.length <= entry.entryIndex) {
      subprimsTable.grow(entry.entryIndex - subprimsTable.length + 1);
    }
    subprimsTable.set(entry.entryIndex, fn);
    registerEntryCallAbi(setEntryCallAbi, entry.entryIndex, fn);
    installed++;
  }

  return { installed, count: entries.length, entries };
}
