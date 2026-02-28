/*
 * Deterministic launcher: boots CCL from pre-built artifacts with zero
 * dynamic discovery.  Uses startup-plan.json to wire the function table
 * and modules.bin for compiled-module WASM binaries.
 *
 * Usage:
 *   node scripts/wasm/lib/deterministic-launch.mjs [--images-dir DIR]
 *
 * Required artifacts in images-dir:
 *   startup-plan.json   — function table map (from make-real-image Phase 2)
 *   root.image           — Lisp heap image
 *   modules.bin          — flat concatenation of merged WASM module binaries
 *
 * Required build artifacts (resolved relative to repo root):
 *   build/wasm32/kernel/wasmcl.wasm
 *   build/wasm32/subprims/subprims.wasm
 *   build/wasm32/subprims-map.json
 */

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  createCclImports,
  createSharedCclRuntime,
  instantiateWasm,
  fillNullTableSlots,
} from "./ccl-loader.mjs";
import { WASM_BOOT_ENTRY_INDEX } from "./abi-constants.mjs";
import { createMicrokernel } from "./microkernel.mjs";
import { createInMemoryPersistenceStore } from "./persist-service.mjs";

/* ── Paths ────────────────────────────────────────────────────────── */

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "../../..");

let imagesDir = path.join(repoRoot, "build/wasm32/images");
let imagePathArg = null;
for (let i = 2; i < process.argv.length; i++) {
  if (process.argv[i] === "--images-dir" && process.argv[i + 1]) {
    imagesDir = path.resolve(process.argv[++i]);
    continue;
  }
  if (!process.argv[i].startsWith("-") && imagePathArg === null) {
    imagePathArg = path.resolve(process.argv[i]);
  }
}

const t0 = performance.now();
const log = (msg) => console.error(`[${((performance.now() - t0) / 1000).toFixed(2)}s] ${msg}`);

async function mountHostImageFile({ hostPath, mountPath }) {
  const store = createInMemoryPersistenceStore({ chunkSize: 256 * 1024 });
  const chunkIds = [];
  const fh = await fs.open(hostPath, "r");
  const chunkSize = store.chunkSize >>> 0;
  const readBuf = Buffer.allocUnsafe(chunkSize);
  let total = 0;

  try {
    while (true) {
      const { bytesRead } = await fh.read(readBuf, 0, readBuf.length, total);
      if (bytesRead === 0) break;
      const id = `c${store.nextChunkId++}`;
      const chunk = new Uint8Array(bytesRead);
      chunk.set(new Uint8Array(readBuf.buffer, readBuf.byteOffset, bytesRead));
      store.chunks.set(id, chunk);
      chunkIds.push(id);
      total += bytesRead;
    }
  } finally {
    await fh.close();
  }

  if (total > 0xffffffff) {
    throw new Error(`image too large for WASM32 persistence metadata: ${total}`);
  }

  store.meta.set(mountPath, {
    path: mountPath,
    type: "file",
    size: total >>> 0,
    mtime: Date.now(),
    readonly: true,
    content: {
      chunk_size: chunkSize,
      chunk_count: chunkIds.length >>> 0,
      chunk_ids: chunkIds,
      etag: null,
    },
  });
  store.readonly = true;
  return { store, total, chunks: chunkIds.length };
}

/* ── 1. Read startup plan ─────────────────────────────────────────── */

const plan = JSON.parse(await fs.readFile(path.join(imagesDir, "startup-plan.json"), "utf-8"));
if (plan.schemaVersion !== 1) {
  console.error(`unsupported startup-plan schema version ${plan.schemaVersion}`);
  process.exit(1);
}
log(`startup-plan: ${plan.functionTable.entries.length} entries, table size ${plan.functionTable.size}`);

/* ── 2. Load binary artifacts ─────────────────────────────────────── */

const [kernelBytes, subprimsBytes, subprimsMap, modulesBinBuf] = await Promise.all([
  fs.readFile(path.join(repoRoot, "build/wasm32/kernel/wasmcl.wasm")),
  fs.readFile(path.join(repoRoot, "build/wasm32/subprims/subprims.wasm")),
  fs.readFile(path.join(repoRoot, "build/wasm32/subprims-map.json"), "utf-8").then(JSON.parse),
  fs.readFile(path.join(imagesDir, "modules.bin")),
]);
const modulesBin = new Uint8Array(modulesBinBuf.buffer, modulesBinBuf.byteOffset, modulesBinBuf.byteLength);
/* Image is loaded later via streaming read (may exceed Node.js 2 GiB fs.readFile limit). */
const imagePath = imagePathArg ?? path.join(imagesDir, "root.image");
const imageStat = await fs.stat(imagePath);
const imageLen = imageStat.size;
log(`artifacts loaded: kernel=${kernelBytes.length} subprims=${subprimsBytes.length} image=${imageLen} modules.bin=${modulesBin.length}`);
const kernelImagePath = "/wasmcl.image";
const imageMount = await mountHostImageFile({ hostPath: imagePath, mountPath: kernelImagePath });
log(`image mounted: ${imageMount.total} bytes at ${kernelImagePath} (${imageMount.chunks} chunks)`);

/* ── 3. Create shared runtime ─────────────────────────────────────── */

const pageSize = 65536;
const cstackSize = 1 << 20; // 1 MiB
/* Start with small initial memory (16 MiB). The image blob is placed at the
   top of this space.  The kernel's create_reserved_area grows WASM memory to
   ~4 GB for the heap layout (nil at 64 MiB, dynamic at 68 MiB, etc.).
   If we start too large, the blob placement overlaps with the restore addresses. */
const initialPages = 256; // 16 MiB — matches original loader

const runtime = createSharedCclRuntime({
  memoryInitialPages: initialPages,
  subprimsTableInitial: plan.functionTable.size,
});

const microkernel = createMicrokernel({
  memory: runtime.memory,
  writeStdout: (bytes) => process.stdout.write(bytes),
  writeStderr: (bytes) => process.stderr.write(bytes),
  persistence: {
    readOnlyMounts: [{ prefix: "/", store: imageMount.store }],
  },
});

/* ── 4. Instantiate kernel ────────────────────────────────────────── */

const kernel = await instantiateWasm(kernelBytes, createCclImports({
  memory: runtime.memory,
  subprimsTable: runtime.subprimsTable,
  microkernel,
}));
const ex = kernel.instance.exports;
log("kernel instantiated");

/* ── 5. Instantiate subprims ──────────────────────────────────────── */

const subprims = await instantiateWasm(subprimsBytes, createCclImports({
  memory: runtime.memory,
  subprimsTable: runtime.subprimsTable,
  microkernel,
  extra: { ccl: ex },
}));
log("subprims instantiated");

/* ── 6. Wire subprim table slots from startup plan ────────────────── */

const spExports = subprims.instance.exports;
const table = runtime.subprimsTable;

// Ensure table is large enough
while (table.length < plan.functionTable.size) {
  table.grow(plan.functionTable.size - table.length);
}

let subprimsWired = 0;
for (const entry of plan.functionTable.entries) {
  if (entry.source !== "subprims" && entry.source !== "kernel") continue;
  const fn = spExports[entry.export] ?? ex[entry.export];
  if (typeof fn === "function") {
    table.set(entry.index, fn);
    subprimsWired++;
  }
}
log(`subprims wired: ${subprimsWired}`);

/* ── 7. Load image via persistence service ───────────────────────── */

const needBytes = cstackSize + (4 << 20); // cstack + 4 MiB slack
let haveBytes = runtime.memory.buffer.byteLength;
if (needBytes > haveBytes) {
  const growPages = Math.ceil((needBytes - haveBytes) / pageSize);
  runtime.memory.grow(growPages);
}
const memoryTop = runtime.memory.buffer.byteLength;
ex.wasm_set_cstack_bounds(memoryTop, cstackSize);

/* Force kernel load path through lisp_open/read from persistence. */
const loadRc = ex.wasm_ccl_load_image(0, 0);
const nil = ex.wasm_get_lisp_nil() >>> 0;
const postLoadMem = runtime.memory.buffer.byteLength;
log(`image loaded: rc=${loadRc} nil=0x${nil.toString(16)} memory=${(postLoadMem/(1024*1024)).toFixed(0)} MiB`);

// Diagnostic: check nrs_WASM_CONST_POOLS.vcell after image load
// nrs_symbol(34).vcell = (nil - fulltag_nil + dnode_size) + 34*sizeof(lispsymbol) + 8
// fulltag_nil=1, dnode_size=8, sizeof(lispsymbol)=32, vcell offset=8
{
  const nrsBase = nil - 1 + 8; // nil_value - fulltag_nil + dnode_size
  const sym34Addr = nrsBase + 34 * 32; // nrs_symbol(34) = WASM_CONST_POOLS
  const vcellAddr = sym34Addr + 8; // vcell is 3rd field (after header=0, pname=4)
  const dv = new DataView(runtime.memory.buffer);
  const vcellVal = dv.getUint32(vcellAddr, true);
  const headerVal = dv.getUint32(sym34Addr, true);
  const pnameVal = dv.getUint32(sym34Addr + 4, true);
  log(`nrs_WASM_CONST_POOLS: addr=0x${sym34Addr.toString(16)} hdr=0x${headerVal.toString(16)} pname=0x${pnameVal.toString(16)} vcell=0x${vcellVal.toString(16)} (nil=0x${nil.toString(16)})`);
  if (vcellVal === nil || vcellVal === 0) {
    log(`WARN: nrs_WASM_CONST_POOLS.vcell is nil/zero — pools not baked in image!`);
  } else {
    // Check the table object header
    const tableRawAddr = vcellVal - 6; // untag fulltag_misc
    const tableHdr = dv.getUint32(tableRawAddr, true);
    const subtag = tableHdr & 0xff;
    const elementCount = tableHdr >>> 8;
    log(`  table: rawAddr=0x${tableRawAddr.toString(16)} hdr=0x${tableHdr.toString(16)} subtag=${subtag} count=${elementCount}`);
    // Check if header looks like a forwarding pointer
    // subtag_simple_vector = 250 = 0xFA on WASM32
    const SUBTAG_SV = 0xFA;
    const headerSubtag = tableHdr & 0xFF;
    log(`  header subtag=0x${headerSubtag.toString(16)} (expected 0xfa for simple_vector)`);
    if (headerSubtag !== SUBTAG_SV && (tableHdr & 7) === 6) {
      // Header looks like a tagged misc pointer → forwarding pointer from GC compaction!
      const fwdTarget = (tableHdr - 6) >>> 0; // untag
      const fwdHdr = dv.getUint32(fwdTarget, true);
      const fwdSubtag = fwdHdr & 0xFF;
      const fwdCount = fwdHdr >>> 8;
      log(`  FORWARDING PTR: 0x${tableHdr.toString(16)} → addr=0x${fwdTarget.toString(16)} hdr=0x${fwdHdr.toString(16)} subtag=0x${fwdSubtag.toString(16)} count=${fwdCount}`);
      if (fwdSubtag === SUBTAG_SV && fwdCount > 8954) {
        const fwdData = fwdTarget + 4;
        const pool8954 = dv.getUint32(fwdData + 8954 * 4, true);
        log(`  FWD table[8954]=0x${pool8954.toString(16)} (pool for RESTORE-LISP-POINTERS)`);
        if (pool8954 !== nil && (pool8954 & 7) === 6) {
          const poolRaw = (pool8954 - 6) >>> 0;
          const poolHdr = dv.getUint32(poolRaw, true);
          log(`  pool obj hdr=0x${poolHdr.toString(16)} subtag=0x${(poolHdr & 0xFF).toString(16)} count=${poolHdr >>> 8}`);
        }
      }
    }
  }
}

/* NOTE: Do NOT call wasm_reset_root_image_runtime_state here.
   The image has pre-baked const pools and we want to preserve them,
   along with nrs_WASM_COMPILED_MODULES and TCR state. */

/* ── 8. Instantiate compiled modules from modules.bin ─────────────── */

// Group entries by offset to instantiate each merged module once.
const moduleEntries = plan.functionTable.entries.filter(e => e.source === "modules");
const byOffset = new Map(); // offset → { length, entries: [] }
for (const entry of moduleEntries) {
  const key = entry.offset;
  if (!byOffset.has(key)) {
    byOffset.set(key, { length: entry.length, entries: [] });
  }
  byOffset.get(key).entries.push(entry);
}

const moduleImports = createCclImports({
  memory: runtime.memory,
  subprimsTable: runtime.subprimsTable,
  microkernel,
  extra: { ccl: ex },
});

let modulesWired = 0;
let modulesInstantiated = 0;
for (const [offset, group] of byOffset) {
  const wasmBytes = modulesBin.subarray(offset, offset + group.length);
  const mod = await instantiateWasm(wasmBytes, moduleImports);
  modulesInstantiated++;

  for (const entry of group.entries) {
    const fn = mod.instance.exports[entry.export];
    if (typeof fn === "function") {
      table.set(entry.index, fn);
      modulesWired++;
    }
  }
}
log(`modules: ${modulesInstantiated} instantiated, ${modulesWired} entries wired`);

/* ── 9. Post-module setup ─────────────────────────────────────────── */

// Install boot entry (wasm_boot_entry at WASM_BOOT_ENTRY_INDEX = 200)
const bootEntry = ex.wasm_boot_entry;
if (typeof bootEntry === "function") {
  if (table.length <= WASM_BOOT_ENTRY_INDEX) {
    table.grow(WASM_BOOT_ENTRY_INDEX - table.length + 1);
  }
  table.set(WASM_BOOT_ENTRY_INDEX, bootEntry);
}

// Signal subprims ready — required before malloc/const pool install
if (typeof ex.wasm_set_subprims_ready === "function") {
  ex.wasm_set_subprims_ready(1);
}

const mallocFn = ex.malloc;
const freeFn = ex.free;

/* Const pools are pre-baked in the saved image — no installation needed. */

// Repair NRS function vcells broken by GC compaction.
// The build's GC compactor moves objects in the dynamic heap but doesn't
// update NRS symbol vcells in the static nil area.
const setSymFn = ex.wasm_set_symbol_function_entry;
const enc = new TextEncoder();
const namedFunctions = plan.namedFunctions ?? [];
const entryByName = new Map(namedFunctions.map(e => [e.name, e.entryIndex]));

// Phase 1: Fix TOPLFUNC and RESTORE-LISP-POINTERS (needed before Lisp rehash)
if (typeof ex.wasm_set_toplfunc_entry === "function") {
  const rc = ex.wasm_set_toplfunc_entry(plan.toplevelIndex >>> 0);
  if (rc !== 0) log(`WARN: wasm_set_toplfunc_entry(${plan.toplevelIndex}) rc=${rc}`);
}

// slot: 0 = fcell (defun), 1 = vcell (defvar with function value)
function setSymbolEntry(name, slot = 0) {
  const idx = entryByName.get(name);
  if (idx == null) return;
  const nameBytes = enc.encode(name);
  const scratchPtr = mallocFn(256) >>> 0;
  if (scratchPtr === 0) return;
  new Uint8Array(runtime.memory.buffer, scratchPtr, nameBytes.length).set(nameBytes);
  const rc = setSymFn(scratchPtr, nameBytes.length, idx >>> 0, slot);
  freeFn(scratchPtr);
  if (rc !== 0) log(`nrs fixup ${name}(${idx}) slot=${slot}: rc=${rc}`);
}

if (typeof setSymFn === "function" && typeof mallocFn === "function") {
  // RESTORE-LISP-POINTERS is a defvar (vcell), not a defun (fcell)
  setSymbolEntry("RESTORE-LISP-POINTERS", 1);
}

// Fill null table slots with trap stub for diagnostic funcall errors
const trapFn = spExports._SPentry_not_installed;
if (typeof trapFn === "function") {
  const { filled } = fillNullTableSlots({ subprimsTable: table, trapFn });
  log(`filled ${filled} null table slots with trap stub`);
}

/* ── 9b. No-op WASM-irrelevant functions in function table ─────────── */
// On WASM there are no Pascal functions, callbacks, or external entrypoints.
// The compiled code for restore-pascal-functions, reset-callback-storage, etc.
// has stale const-pool references to function objects from the build phase.
// Rather than patching all stale references, replace their function table
// entries with wasm_boot_entry (a clean no-op that returns nil).
{
  const noopFns = [
    // "RESTORE-LISP-POINTERS" — removed to test crash diagnostics
    "RESTORE-PASCAL-FUNCTIONS",  // calls reset-callback-storage, revives macptrs
    "RESET-CALLBACK-STORAGE",    // clears callback vector
    "REFRESH-EXTERNAL-ENTRYPOINTS", // resolves foreign function pointers
    // "INITIALIZE-INTERACTIVE-STREAMS" — REMOVED: needed for REPL I/O
  ];
  const noopEntry = ex.wasm_boot_entry;
  if (typeof noopEntry === "function") {
    for (const name of noopFns) {
      const idx = entryByName.get(name);
      if (idx != null && idx < table.length) {
        table.set(idx, noopEntry);
      }
    }
    log(`no-op'd ${noopFns.length} WASM-irrelevant function table entries`);
  }
}

/* ── 9c. JS-side memory scan to rebind named function symbols ─────── */
// After image load, package tables are unreliable and the C area chain
// doesn't cover all loaded memory. Scan entire WASM memory for symbol
// headers, match pnames against namedFunctions, and patch fcells.
{
  const SYMBOL_HDR = 0x0000073A;  // (7 << 8) | subtag_symbol
  const FULLTAG_MISC = 6;
  const FN_HDR_3SLOT = 0x0000032A; // (3 << 8) | subtag_function

  const rebindMap = new Map();
  for (const e of namedFunctions) {
    if (!e?.name || !Number.isFinite(e?.entryIndex)) continue;
    if (e.name.startsWith("(:INTERNAL")) continue;
    rebindMap.set(e.name, e.entryIndex);
  }

  if (rebindMap.size > 0 && typeof mallocFn === "function") {
    const mem32 = new Uint32Array(runtime.memory.buffer);
    const totalWords = mem32.length;
    const scanStart = 0x400000 >>> 2;
    let symbolCount = 0, rebound = 0;
    const remaining = new Map(rebindMap);

    for (let w = scanStart; w < totalWords && remaining.size > 0; w += 2) {
      if (mem32[w] !== SYMBOL_HDR) continue;
      symbolCount++;

      const pnameTagged = mem32[w + 1];
      if ((pnameTagged & 7) !== FULLTAG_MISC) continue;
      const pnameUntagged = (pnameTagged - FULLTAG_MISC) >>> 0;
      const pnameWordIdx = pnameUntagged >>> 2;
      if (pnameWordIdx < 1 || pnameWordIdx >= totalWords) continue;

      const pnameHdr = mem32[pnameWordIdx];
      const pnameSubtag = pnameHdr & 0xFF;
      const pnameCount = pnameHdr >>> 8;
      if (pnameCount < 1 || pnameCount > 255) continue;
      const dataPos = pnameWordIdx + 1;

      let name = "";
      if (pnameSubtag === 0x36) {
        // SIMPLE-BASE-STRING (subtag 0x36): 4 ASCII chars packed per word
        const dataWords = ((pnameCount + 3) >>> 2);
        if (dataPos + dataWords > totalWords) continue;
        for (let i = 0; i < pnameCount; i++) {
          const wordOff = i >>> 2;
          const byteOff = i & 3;
          name += String.fromCharCode((mem32[dataPos + wordOff] >>> (byteOff * 8)) & 0xFF);
        }
      } else {
        // SIMPLE-GENERAL-STRING (subtag 0x5A): 1 char per word
        if (dataPos + pnameCount > totalWords) continue;
        for (let i = 0; i < pnameCount; i++) {
          name += String.fromCharCode(mem32[dataPos + i] & 0xFFFF);
        }
      }

      const entryIdx = remaining.get(name);
      if (entryIdx === undefined) continue;

      // Allocate 3-slot function object (16 bytes)
      const fnPtr = mallocFn(16) >>> 0;
      if (fnPtr === 0) continue;
      const m32 = new Uint32Array(runtime.memory.buffer);
      const fw = fnPtr >>> 2;
      m32[fw] = FN_HDR_3SLOT;
      m32[fw + 1] = entryIdx << 2;
      m32[fw + 2] = entryIdx << 2;
      m32[fw + 3] = nil;
      m32[w + 3] = (fnPtr + FULLTAG_MISC) >>> 0;  // patch fcell
      rebound++;
      remaining.delete(name);
    }
    log(`JS rebind: ${rebound}/${rebindMap.size} (${symbolCount} syms, ${remaining.size} missing)`);
  }
}

// Call wasm_restore_lisp_pointers — now that RESTORE-LISP-POINTERS vcell
// is fixed and UDF bindings repaired, this calls the Lisp-level function
// to rehash packages, restore callbacks, initialize streams.
if (typeof ex.wasm_restore_lisp_pointers === "function") {
  const rlpRc = ex.wasm_restore_lisp_pointers();
  log(`wasm_restore_lisp_pointers rc=${rlpRc}`);
}

// Phase 2: Fix remaining NRS symbols (packages now rehashed)
if (typeof setSymFn === "function" && typeof mallocFn === "function") {
  for (const name of ["TOPLEVEL", "STARTUP-CCL", "TOPLEVEL-LOOP",
                       "%SAVE-APPLICATION-INTERNAL"]) {
    setSymbolEntry(name);
  }
  log("NRS fixups phase 2 complete");
}

log("ready");

/* ── 10. Start Lisp ──────────────────────────────────────────────── */

try {
  const rc = ex.wasm_ccl_start_lisp();
  log(`start_lisp rc=${rc}`);
  process.exitCode = rc | 0;
} catch (e) {
  console.error(`start_lisp trapped: ${e}`);
  process.exit(4);
}
