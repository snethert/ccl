/*
 * Shared bootstrap sanity contract for WASM image lanes.
 *
 * Contract phases:
 * - pre-start (before first start/toplevel loop)
 * - post-start (after start_lisp returns)
 *
 * This file is the code-level source of truth for startup callability policy.
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

function optionalExport(kernelExports, name) {
  const fn = kernelExports?.[name];
  return typeof fn === "function" ? fn : null;
}

function call0(fn) {
  if (typeof fn !== "function") return 0;
  return fn() >>> 0;
}

function resolvePhaseSpec(contract, phase) {
  if (!contract || typeof contract !== "object") return null;
  const phases = contract.phases;
  if (!phases || typeof phases !== "object") return null;
  return phases[phase] ?? null;
}

function formatProbeStatus(probe) {
  if (!probe) return "missing";
  if (!probe.probeAvailable) return "probe-unavailable";
  if (probe.callable) return "callable";
  if (!probe.present) return "missing";
  return "non-callable";
}

function describeProbeFailure(probe, nil) {
  if (!probe) return "probe missing";
  if (!probe.probeAvailable) {
    return probe.reason || "probe unavailable";
  }
  if (!probe.present) {
    return probe.reason || "symbol missing";
  }
  const parts = [];
  if (probe.symbolRaw != null) {
    parts.push(`sym=${toHex(probe.symbolRaw)}`);
    parts.push(`sym_subtag=${probe.symbolSubtag}`);
  }
  parts.push(`raw=${toHex(probe.raw ?? 0)}`);
  if ((probe.raw >>> 0) === (nil >>> 0)) {
    parts.push("raw=nil");
  }
  parts.push(`subtag=${probe.subtag}`);
  parts.push(`entry=${probe.entryIndex}`);
  if (probe.reason) {
    parts.push(`reason=${probe.reason}`);
  }
  return parts.join(" ");
}

function collectSymbolProbe({
  id,
  label,
  nil,
  finders,
  symbolFcell,
  miscSubtag,
  functionEntry,
}) {
  const probe = {
    id,
    label,
    kind: "symbol-fcell",
    probeAvailable: true,
    present: false,
    callable: false,
    source: null,
    reason: null,
    symbolRaw: 0,
    symbolSubtag: -1,
    raw: 0,
    subtag: -1,
    entryIndex: -1,
  };

  const finderList = Array.isArray(finders)
    ? finders.filter((entry) => entry && typeof entry.fn === "function")
    : [];

  if (!symbolFcell || !miscSubtag || !functionEntry || finderList.length === 0) {
    probe.probeAvailable = false;
    probe.reason = "probe-export-missing";
    return probe;
  }

  for (const finder of finderList) {
    const sym = call0(finder.fn);
    if (sym !== 0 && sym !== (nil >>> 0)) {
      probe.symbolRaw = sym;
      probe.source = finder.id;
      probe.present = true;
      break;
    }
  }

  if (!probe.present) {
    probe.reason = "symbol-missing";
    return probe;
  }

  probe.symbolSubtag = miscSubtag(probe.symbolRaw) | 0;
  probe.raw = symbolFcell(probe.symbolRaw) >>> 0;
  probe.subtag = miscSubtag(probe.raw) | 0;
  probe.entryIndex = functionEntry(probe.raw) | 0;

  if (probe.entryIndex >= 0) {
    probe.callable = true;
    return probe;
  }

  if ((probe.raw >>> 0) === (nil >>> 0)) {
    probe.reason = "fcell-nil";
  } else {
    probe.reason = "fcell-not-callable";
  }
  return probe;
}

export const STARTUP_PHASE_CONTRACT_V1 = Object.freeze({
  id: "startup-phase-contract-v1",
  phases: Object.freeze({
    "pre-start": Object.freeze({
      requiredCallable: Object.freeze([
        "nrs:%TOPLEVEL-FUNCTION%",
      ]),
      mayRemainUnresolved: Object.freeze([
        "symbol:TOPLEVEL",
        "symbol:COMMON-LISP:INTERN",
        "symbol:CCL::REQUIRE-STRUCTURE-TYPE",
        "symbol:%SET-TOPLEVEL",
      ]),
    }),
    "post-start": Object.freeze({
      requiredCallable: Object.freeze([]),
      mayRemainUnresolved: Object.freeze([
        "symbol:TOPLEVEL",
        "symbol:COMMON-LISP:INTERN",
        "symbol:CCL::REQUIRE-STRUCTURE-TYPE",
        "symbol:%SET-TOPLEVEL",
      ]),
    }),
  }),
});

export const STARTUP_FUNCTION_DESIGNATOR_POLICY_V1 = Object.freeze({
  id: "startup-function-designator-policy-v1",
  phases: Object.freeze({
    "pre-toplevel": Object.freeze({
      /*
       * Required function designators in const-pool function entries.
       * These must resolve to callable entry functions during bootstrap.
       */
      requiredResolveOrFail: Object.freeze([
        "TOPLEVEL",
        "RUN-READ-LOOP",
        "RUNTIME-BRIDGE-PUMP-COMMANDS",
      ]),
      /*
       * Explicitly deferred designators that may remain symbolic/UDF during
       * bootstrap and get canonicalized later in Lisp.
       */
      deferredAllowed: Object.freeze([
        "WASM-YIELD",
        "*WASM-YIELD-ON-EAGAIN*",
        "BREAK-LEVEL",
      ]),
    }),
    "post-start": Object.freeze({
      requiredResolveOrFail: Object.freeze([]),
      deferredAllowed: Object.freeze([
        "TOPLEVEL",
        "RUN-READ-LOOP",
        "RUNTIME-BRIDGE-PUMP-COMMANDS",
        "WASM-YIELD",
        "*WASM-YIELD-ON-EAGAIN*",
        "BREAK-LEVEL",
      ]),
    }),
  }),
});

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

  const consCar = optionalExport(kernelExports, "wasm_debug_cons_car_raw");
  const consCdr = optionalExport(kernelExports, "wasm_debug_cons_cdr_raw");
  const packageNamesRaw = optionalExport(kernelExports, "wasm_debug_package_names_raw");
  const symbolFcell = optionalExport(kernelExports, "wasm_debug_symbol_fcell_raw");

  const findInternPkgtable = optionalExport(kernelExports, "wasm_debug_find_symbol_intern_pkgtable_raw");
  const findInternScan = optionalExport(kernelExports, "wasm_debug_find_symbol_intern_scan_raw");
  const findRequireStructureType = optionalExport(kernelExports, "wasm_debug_find_symbol_require_structure_type_raw");
  const findPercentSetToplevel = optionalExport(kernelExports, "wasm_debug_find_symbol_percent_set_toplevel_raw");

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

  const callableProbes = {
    "nrs:%TOPLEVEL-FUNCTION%": {
      id: "nrs:%TOPLEVEL-FUNCTION%",
      label: "%TOPLEVEL-FUNCTION%",
      kind: "function-object",
      probeAvailable: true,
      present: (toplfuncRaw >>> 0) !== 0 && (toplfuncRaw >>> 0) !== (nil >>> 0),
      callable: (toplfuncEntryIndex | 0) >= 0,
      reason: (toplfuncEntryIndex | 0) >= 0 ? null : "not-callable",
      raw: toplfuncRaw,
      subtag: toplfuncSubtag,
      entryIndex: toplfuncEntryIndex,
    },
    "symbol:TOPLEVEL": collectSymbolProbe({
      id: "symbol:TOPLEVEL",
      label: "TOPLEVEL",
      nil,
      finders: [{ id: "find:toplevel", fn: findToplevelSymbol }],
      symbolFcell,
      miscSubtag,
      functionEntry,
    }),
    "symbol:COMMON-LISP:INTERN": collectSymbolProbe({
      id: "symbol:COMMON-LISP:INTERN",
      label: "COMMON-LISP:INTERN",
      nil,
      finders: [
        { id: "find:intern-pkgtable", fn: findInternPkgtable },
        { id: "find:intern-scan", fn: findInternScan },
      ],
      symbolFcell,
      miscSubtag,
      functionEntry,
    }),
    "symbol:CCL::REQUIRE-STRUCTURE-TYPE": collectSymbolProbe({
      id: "symbol:CCL::REQUIRE-STRUCTURE-TYPE",
      label: "CCL::REQUIRE-STRUCTURE-TYPE",
      nil,
      finders: [{ id: "find:require-structure-type", fn: findRequireStructureType }],
      symbolFcell,
      miscSubtag,
      functionEntry,
    }),
    "symbol:%SET-TOPLEVEL": collectSymbolProbe({
      id: "symbol:%SET-TOPLEVEL",
      label: "%SET-TOPLEVEL",
      nil,
      finders: [{ id: "find:%set-toplevel", fn: findPercentSetToplevel }],
      symbolFcell,
      miscSubtag,
      functionEntry,
    }),
  };

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
    callableProbes,
  };
}

export function validateBootstrapContract(
  state,
  {
    phase = "pre-start",
    requireToplfunc = (phase === "pre-start"),
    contract = STARTUP_PHASE_CONTRACT_V1,
  } = {},
) {
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

  const phaseSpec = resolvePhaseSpec(contract, phase);
  const required = new Set(Array.isArray(phaseSpec?.requiredCallable) ? phaseSpec.requiredCallable : []);
  if (!requireToplfunc) {
    required.delete("nrs:%TOPLEVEL-FUNCTION%");
  }

  for (const callableId of required) {
    const probe = state.callableProbes?.[callableId] ?? null;
    if (!probe || !probe.callable) {
      const label = probe?.label ?? callableId;
      failures.push(`${label} is not callable (${describeProbeFailure(probe, state.nil)})`);
    }
  }

  return failures;
}

export function formatBootstrapState(state) {
  if (!state) return "bootstrap_state=<missing>";
  const probes = state.callableProbes ?? {};
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
    `callable_toplfunc=${formatProbeStatus(probes["nrs:%TOPLEVEL-FUNCTION%"])}`,
    `callable_toplevel=${formatProbeStatus(probes["symbol:TOPLEVEL"])}`,
    `callable_intern=${formatProbeStatus(probes["symbol:COMMON-LISP:INTERN"])}`,
    `callable_require_structure_type=${formatProbeStatus(probes["symbol:CCL::REQUIRE-STRUCTURE-TYPE"])}`,
    `callable_%set_toplevel=${formatProbeStatus(probes["symbol:%SET-TOPLEVEL"])}`,
  ].join(" ");
}

export function assertBootstrapContract({
  kernelExports,
  phase = "pre-start",
  requireToplfunc = (phase === "pre-start"),
  contract = STARTUP_PHASE_CONTRACT_V1,
} = {}) {
  const state = collectBootstrapState({ kernelExports });
  const failures = validateBootstrapContract(state, { phase, requireToplfunc, contract });
  if (failures.length) {
    throw new Error(
      `${phase} bootstrap contract failed: ${failures.join("; ")} | ${formatBootstrapState(state)}`,
    );
  }
  return state;
}
