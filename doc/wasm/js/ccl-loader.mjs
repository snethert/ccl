/*
 * Minimal JS "microkernel" wiring for the CCL WASM ABI:
 * - One shared `WebAssembly.Table` for subprims (ordered like ARM sptab).
 * - (Optionally) one shared `WebAssembly.Memory`.
 *
 * This file intentionally avoids WASI; it assumes a browser/worker-like host.
 */

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

  return { ...extra, env, ccl };
}

export function createSharedCclRuntime({
  subprimsTableInitial = 256,
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

const FULLTAG_MASK = 0x7;
const TAGMASK = 0x3;
const FIXNUM_SHIFT = 2;
const FULLTAG_CONS = 0x5;
const FULLTAG_MISC = 0x6;
const FULLTAG_NODEHEADER = 0x2;
const FULLTAG_IMMHEADER = 0x7;
const NUM_SUBTAG_BITS = 8;
const SUBTAG_MASK = 0xff;
const SUBTAG_SIMPLE_VECTOR = (31 << 3) | FULLTAG_NODEHEADER;
const SUBTAG_U8_VECTOR = (24 << 3) | FULLTAG_IMMHEADER;
const SUBTAG_SIMPLE_BASE_STRING = (23 << 3) | FULLTAG_IMMHEADER;

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
    const car = readU32(view, base);
    const cdr = readU32(view, base + 4);

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

    entries.push({ moduleBytes, exportName, entryIndex, moduleVersion, constPoolBytes });

    list = cdr;
    guard++;
    if (guard > 100000) {
      throw new Error("compiled module registry appears cyclic");
    }
  }

  return entries;
}

function alignUp(value, align) {
  return (value + (align - 1)) & ~(align - 1);
}

function allocScratch(memory, size) {
  const pageSize = 65536;
  const aligned = alignUp(size, 16);
  const base = memory.buffer.byteLength;
  const pages = Math.ceil(aligned / pageSize);
  if (pages > 0) {
    memory.grow(pages);
  }
  return base;
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
  const base = allocScratch(memory, bytes.length);
  new Uint8Array(memory.buffer, base, bytes.length).set(bytes);
  return install(entryIndex >>> 0, base >>> 0, bytes.length >>> 0) >>> 0;
}

export async function installCompiledModulesFromBundle({
  bundle,
  binaryBytes = null,
  binaryReader = null,
  kernel,
  memory,
  subprimsTable,
  microkernel = null,
  extra = {},
  verbose = false,
  strict = true,
} = {}) {
  if (!memory) throw new Error("installCompiledModulesFromBundle: memory is required");
  if (!subprimsTable) throw new Error("installCompiledModulesFromBundle: subprimsTable is required");

  const kernelExports = kernel?.instance?.exports ?? kernel?.exports ?? kernel;
  if (!kernelExports) throw new Error("installCompiledModulesFromBundle: kernel exports are required");

  const modules = Array.isArray(bundle?.modules) ? bundle.modules : [];
  if (modules.length === 0) return { installed: 0, count: 0, entries: [] };

  const extraCcl = { ...(extra.ccl ?? {}), ...kernelExports };
  const imports = createCclImports({
    memory,
    subprimsTable,
    microkernel,
    extra: { ...extra, ccl: extraCcl },
  });

  let installed = 0;
  let failed = 0;
  const readBinary = typeof binaryReader === "function" ? binaryReader : null;
  for (const entry of modules) {
    let moduleBytes = entry.moduleBytes ?? null;
    let constPoolBytes = entry.constPoolBytes ?? null;
    if (!moduleBytes && binaryBytes && Number.isFinite(entry.offset) && Number.isFinite(entry.length)) {
      const start = entry.offset >>> 0;
      const end = start + (entry.length >>> 0);
      moduleBytes = binaryBytes.subarray(start, end);
    } else if (!moduleBytes && readBinary && Number.isFinite(entry.offset) && Number.isFinite(entry.length)) {
      const start = entry.offset >>> 0;
      const length = entry.length >>> 0;
      moduleBytes = await readBinary(start, length);
    }
    if (!constPoolBytes && binaryBytes &&
        Number.isFinite(entry.constPoolOffset) && Number.isFinite(entry.constPoolLength)) {
      const start = entry.constPoolOffset >>> 0;
      const end = start + (entry.constPoolLength >>> 0);
      constPoolBytes = binaryBytes.subarray(start, end);
    } else if (!constPoolBytes && readBinary &&
        Number.isFinite(entry.constPoolOffset) && Number.isFinite(entry.constPoolLength)) {
      const start = entry.constPoolOffset >>> 0;
      const length = entry.constPoolLength >>> 0;
      constPoolBytes = await readBinary(start, length);
    }

    if (!moduleBytes || moduleBytes.length === 0) {
      if (verbose) {
        // eslint-disable-next-line no-console
        console.warn(`compiled module missing bytes for ${entry.exportName}`);
      }
      failed++;
      continue;
    }

    if (constPoolBytes?.length) {
      installConstPoolBytes({
        kernelExports,
        memory,
        entryIndex: entry.entryIndex,
        constPoolBytes,
      });
    }

    const bytes = moduleBytes instanceof Uint8Array ? moduleBytes : Uint8Array.from(moduleBytes);
    let instance;
    try {
      ({ instance } = await instantiateWasm(bytes, imports));
    } catch (e) {
      failed++;
      if (verbose) {
        // eslint-disable-next-line no-console
        console.warn(`compiled module failed to instantiate ${entry.exportName}: ${e}`);
      }
      if (strict) throw e;
      continue;
    }
    const fn = instance?.exports?.[entry.exportName];
    if (typeof fn !== "function") {
      if (verbose) {
        // eslint-disable-next-line no-console
        console.warn(`compiled module missing export ${entry.exportName}`);
      }
      failed++;
      if (strict) {
        throw new Error(`compiled module missing export ${entry.exportName}`);
      }
      continue;
    }

    const idx = entry.entryIndex >>> 0;
    if (subprimsTable.length <= idx) {
      subprimsTable.grow(idx - subprimsTable.length + 1);
    }
    subprimsTable.set(idx, fn);
    installed++;
  }

  return { installed, count: modules.length, failed, entries: modules };
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
      throw new Error("installCompiledModulesFromRegistry: missing wasm_get_compiled_module_registry export");
    }
    registry = getRegistry() >>> 0;
  }
  if (nil == null) {
    const getNil = kernelExports.wasm_get_lisp_nil;
    if (typeof getNil !== "function") {
      throw new Error("installCompiledModulesFromRegistry: missing wasm_get_lisp_nil export");
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
    installed++;
  }

  return { installed, count: entries.length, entries };
}
