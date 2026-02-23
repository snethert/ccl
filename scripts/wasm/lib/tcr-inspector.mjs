/**
 * TCR State Inspector — reads kernel state from WASM linear memory.
 *
 * Provides non-invasive state inspection for debugging the CCL WASM kernel.
 * All reads go through DataView on WebAssembly.Memory.buffer, so no kernel
 * cooperation is needed beyond the exported wasm_get_current_tcr() and
 * wasm_debug_tcr_offset() functions.
 *
 * See doc/wasm/debugging.md for workflows and usage examples.
 *
 * Usage:
 *   import { createInspector } from './tcr-inspector.mjs';
 *   const inspect = createInspector(kernel.instance.exports, runtime.memory);
 *   inspect.dumpGPRs();
 *   inspect.dumpSpillStack(8);
 *   inspect.dumpCatchFrames();
 *   const snap = inspect.snapshot();
 */

import { GPR_NAMES } from "./abi-constants.mjs";

const FIELD_IDS = {
  wasm_gprs: 0,
  wasm_spill_base: 1,
  wasm_spill_sp: 2,
  wasm_pending_throw: 3,
  catch_top: 4,
  db_link: 5,
  save_vsp: 6,
  xframe: 7,
  wasm_spill_limit: 8,
  wasm_cstack_sp: 9,
  nfp: 10,
};

/**
 * Create an inspector bound to a specific kernel instance and memory.
 *
 * @param {object} exports - kernel.instance.exports
 * @param {WebAssembly.Memory} memory - shared WASM memory
 * @returns {object} inspector API
 */
export function createInspector(exports, memory) {
  // Discover TCR field offsets from the kernel at runtime.
  const offsets = {};
  for (const [name, id] of Object.entries(FIELD_IDS)) {
    const off = exports.wasm_debug_tcr_offset(id);
    if (off === 0xFFFFFFFF) {
      throw new Error(`Unknown TCR field id ${id} (${name})`);
    }
    offsets[name] = off;
  }

  function view() {
    return new DataView(memory.buffer);
  }

  function u32(addr) {
    return view().getUint32(addr, true);
  }

  function tcr() {
    return exports.wasm_get_current_tcr();
  }

  function getGPR(index) {
    const base = tcr() + offsets.wasm_gprs;
    return u32(base + index * 4);
  }

  function getAllGPRs() {
    const result = {};
    for (let i = 0; i < 16; i++) {
      result[GPR_NAMES[i]] = getGPR(i);
    }
    return result;
  }

  function getField(name) {
    return u32(tcr() + offsets[name]);
  }

  function dumpGPRs() {
    const gprs = getAllGPRs();
    console.error("=== GPRs ===");
    for (const [name, val] of Object.entries(gprs)) {
      console.error(`  ${name.padEnd(8)} = 0x${val.toString(16).padStart(8, "0")}`);
    }
  }

  function dumpSpillStack(depth = 8) {
    const sp = getField("wasm_spill_sp");
    const limit = getField("wasm_spill_limit");
    const used = (limit - sp) / 4;
    const n = Math.min(depth, used);
    console.error(`=== Spill Stack (sp=0x${sp.toString(16)} limit=0x${limit.toString(16)} depth=${used}) ===`);
    for (let i = 0; i < n; i++) {
      const addr = sp + i * 4;
      const val = u32(addr);
      console.error(`  [${i}] 0x${addr.toString(16)}: 0x${val.toString(16).padStart(8, "0")}`);
    }
  }

  function dumpVSP(depth = 8) {
    const vspVal = getGPR(10); // vsp register
    console.error(`=== VSP (0x${vspVal.toString(16)}) ===`);
    for (let i = 0; i < depth; i++) {
      const addr = vspVal + i * 4;
      const val = u32(addr);
      console.error(`  [${i}] 0x${addr.toString(16)}: 0x${val.toString(16).padStart(8, "0")}`);
    }
  }

  function dumpCatchFrames() {
    let ptr = getField("catch_top");
    console.error("=== Catch Frames ===");
    let count = 0;
    while (ptr && ptr !== 0 && count < 20) {
      const header = u32(ptr);
      const link = u32(ptr + 4);
      const mvflag = u32(ptr + 8);
      const catchTag = u32(ptr + 12);
      const dbLink = u32(ptr + 16);
      const saveVsp = u32(ptr + 32);
      const saveSpillSp = u32(ptr + 40);
      console.error(
        `  frame@0x${ptr.toString(16)}: tag=0x${catchTag.toString(16)} ` +
        `vsp=0x${saveVsp.toString(16)} spill_sp=0x${saveSpillSp.toString(16)} ` +
        `link=0x${link.toString(16)}`
      );
      ptr = link;
      count++;
    }
    if (count === 0) console.error("  (none)");
  }

  function inspectObject(addr) {
    if (!addr || addr < 0x100) {
      console.error(`  0x${(addr >>> 0).toString(16)}: not a valid object pointer`);
      return null;
    }
    const untagged = addr & ~7;  // FULLTAGMASK = 7 (3-bit tags on WASM32)
    const tag = addr & 7;
    const header = u32(untagged);
    const subtag = header & 0xFF;
    const count = header >>> 8;
    console.error(
      `  obj@0x${addr.toString(16)}: tag=${tag} header=0x${header.toString(16)} ` +
      `subtag=0x${subtag.toString(16)} count=${count}`
    );
    return { addr, tag, header, subtag, count };
  }

  function snapshot() {
    const t = tcr();
    return {
      tcr: t,
      gprs: getAllGPRs(),
      spill_sp: getField("wasm_spill_sp"),
      spill_base: getField("wasm_spill_base"),
      spill_limit: getField("wasm_spill_limit"),
      pending_throw: getField("wasm_pending_throw"),
      catch_top: getField("catch_top"),
      db_link: getField("db_link"),
      save_vsp: getField("save_vsp"),
      cstack_sp: getField("wasm_cstack_sp"),
    };
  }

  function dumpAll() {
    dumpGPRs();
    dumpSpillStack(8);
    dumpVSP(8);
    dumpCatchFrames();
  }

  return {
    getGPR,
    getAllGPRs,
    getField,
    dumpGPRs,
    dumpSpillStack,
    dumpVSP,
    dumpCatchFrames,
    inspectObject,
    snapshot,
    dumpAll,
    offsets,
    GPR_NAMES,
  };
}
