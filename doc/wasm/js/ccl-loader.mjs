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
