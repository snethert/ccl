/*
 * Shared bootstrap sanity contract for WASM image lanes.
 *
 * Contract (pre-start):
 * - COMMON-LISP package lookup is non-NIL
 * - TOPLEVEL symbol lookup is non-NIL/non-zero
 * - %TOPLEVEL-FUNCTION% decodes as a callable function object
 *
 * Contract (post-start):
 * - COMMON-LISP package lookup is non-NIL
 * - TOPLEVEL symbol lookup is non-NIL/non-zero
 */

function toHex(value) {
  return `0x${(value >>> 0).toString(16)}`;
}

function requireExport(kernelExports, name) {
  const fn = kernelExports?.[name];
  if (typeof fn !== "function") {
    throw new Error(`bootstrap contract requires kernel export ${name}`);
  }
  return fn;
}

export function collectBootstrapState({ kernelExports } = {}) {
  if (!kernelExports) {
    throw new Error("bootstrap contract requires kernel exports");
  }

  const getNil = requireExport(kernelExports, "wasm_get_lisp_nil");
  const findCommonLisp = requireExport(kernelExports, "wasm_debug_find_package_common_lisp_raw");
  const allPackagesRawFn = requireExport(kernelExports, "wasm_debug_all_packages_raw");
  const findToplevelSymbol = requireExport(kernelExports, "wasm_debug_find_symbol_toplevel_raw");
  const getToplfunc = requireExport(kernelExports, "wasm_debug_get_nrs_toplfunc_raw");
  const functionEntry = requireExport(kernelExports, "wasm_debug_function_entry_index");
  const miscSubtag = requireExport(kernelExports, "wasm_debug_misc_subtag");
  const consCar = typeof kernelExports?.wasm_debug_cons_car_raw === "function"
    ? kernelExports.wasm_debug_cons_car_raw
    : null;
  const consCdr = typeof kernelExports?.wasm_debug_cons_cdr_raw === "function"
    ? kernelExports.wasm_debug_cons_cdr_raw
    : null;
  const packageNamesRaw = typeof kernelExports?.wasm_debug_package_names_raw === "function"
    ? kernelExports.wasm_debug_package_names_raw
    : null;

  const nil = getNil() >>> 0;
  const commonLispPackage = findCommonLisp() >>> 0;
  const allPackagesRaw = allPackagesRawFn() >>> 0;
  const allPackagesHeadCar = consCar ? (consCar(allPackagesRaw) >>> 0) : 0;
  const allPackagesHeadCdr = consCdr ? (consCdr(allPackagesRaw) >>> 0) : 0;
  const allPackagesHeadNamesRaw = packageNamesRaw ? (packageNamesRaw(allPackagesHeadCar) >>> 0) : 0;
  const toplevelSymbol = findToplevelSymbol() >>> 0;
  const toplfuncRaw = getToplfunc() >>> 0;
  const toplfuncEntryIndex = functionEntry(toplfuncRaw) | 0;
  const toplfuncSubtag = miscSubtag(toplfuncRaw) | 0;

  return {
    nil,
    commonLispPackage,
    allPackagesRaw,
    allPackagesHeadCar,
    allPackagesHeadCdr,
    allPackagesHeadNamesRaw,
    toplevelSymbol,
    toplfuncRaw,
    toplfuncEntryIndex,
    toplfuncSubtag,
  };
}

export function validateBootstrapContract(state, { phase = "pre-start", requireToplfunc = (phase === "pre-start") } = {}) {
  const failures = [];
  if (!state) {
    failures.push("missing bootstrap state");
    return failures;
  }

  if ((state.commonLispPackage >>> 0) === (state.nil >>> 0)) {
    failures.push(`COMMON-LISP package is NIL (${toHex(state.commonLispPackage)})`);
  }

  if ((state.toplevelSymbol >>> 0) === 0 || (state.toplevelSymbol >>> 0) === (state.nil >>> 0)) {
    failures.push(`TOPLEVEL symbol missing (raw=${toHex(state.toplevelSymbol)})`);
  }

  if (requireToplfunc && (state.toplfuncEntryIndex | 0) < 0) {
    failures.push(
      `%TOPLEVEL-FUNCTION% is not callable (raw=${toHex(state.toplfuncRaw)}, subtag=${state.toplfuncSubtag}, entry=${state.toplfuncEntryIndex})`,
    );
  }

  return failures;
}

export function formatBootstrapState(state) {
  if (!state) return "bootstrap_state=<missing>";
  return [
    `nil=${toHex(state.nil)}`,
    `cl=${toHex(state.commonLispPackage)}`,
    `allpkgs=${toHex(state.allPackagesRaw)}`,
    `allpkgs_car=${toHex(state.allPackagesHeadCar)}`,
    `allpkgs_cdr=${toHex(state.allPackagesHeadCdr)}`,
    `allpkgs_names=${toHex(state.allPackagesHeadNamesRaw)}`,
    `toplevel_sym=${toHex(state.toplevelSymbol)}`,
    `toplfunc_raw=${toHex(state.toplfuncRaw)}`,
    `toplfunc_entry=${state.toplfuncEntryIndex}`,
    `toplfunc_subtag=${state.toplfuncSubtag}`,
  ].join(" ");
}

export function assertBootstrapContract({
  kernelExports,
  phase = "pre-start",
  requireToplfunc = (phase === "pre-start"),
} = {}) {
  const state = collectBootstrapState({ kernelExports });
  const failures = validateBootstrapContract(state, { phase, requireToplfunc });
  if (failures.length) {
    throw new Error(
      `${phase} bootstrap contract failed: ${failures.join("; ")} | ${formatBootstrapState(state)}`,
    );
  }
  return state;
}
