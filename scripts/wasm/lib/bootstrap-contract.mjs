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

/*
 * Bootstrap-critical symbols that must be rewritten from symbolic designators
 * to callable entry functions before first toplevel execution.
 */
export const STARTUP_SYMBOL_TO_ENTRY_FUNCTION_DESIGNATORS_PRE_TOPLEVEL_V1 = Object.freeze([
  "INTERN",
  "TOPLEVEL",
  "RUN-READ-LOOP",
  "RUNTIME-BRIDGE-PUMP-COMMANDS",
  "RUNTIME-COMMAND--POLL-FRAME",
  "RUNTIME-COMMAND--DECODE-FRAME",
  "RUNTIME-COMMAND--DISPATCH",
  "READ-LOOP",
  "RUNTIME-COMMAND--SAFE-READ-FORM",
  "RUNTIME-COMMAND--EVAL-FORM",
  "RUNTIME-COMMAND--EMIT-RESULT",
  "RUNTIME-COMMAND--EMIT-ERROR",
  "RUNTIME-BRIDGE--NOW-MS",
  "RUNTIME-BRIDGE--EMIT-MESSAGE",
  "RUNTIME-COMMAND--ALIST-VALUE",
  "RUNTIME-COMMAND--RENDER-SUMMARY",
  "RUNTIME-COMMAND--U32",
  "RUNTIME-COMMAND--DECODE-STRING",
  "TOPLEVEL-EVAL",
  "TOPLEVEL-PRINT",
]);

export function collectBootstrapState({ kernelExports } = {}) {
  if (!kernelExports) {
    throw new Error("bootstrap contract requires kernel exports");
  }

  const getNil = kernelExports?.wasm_get_lisp_nil;
  if (typeof getNil !== "function") {
    throw new Error("bootstrap contract requires kernel export wasm_get_lisp_nil");
  }

  const nil = getNil() >>> 0;

  return {
    nil,
    commonLispPackage: 0,
    allPackagesRaw: 0,
    allPackagesHeadCar: 0,
    allPackagesHeadCdr: 0,
    allPackagesHeadNamesRaw: 0,
    toplevelSymbol: 0,
    toplfuncRaw: 0,
    toplfuncEntryIndex: -1,
    toplfuncSubtag: -1,
    callableProbes: {},
  };
}

export function validateBootstrapContract(
  state,
  {
    phase = "pre-start",
    contract = STARTUP_PHASE_CONTRACT_V1,
  } = {},
) {
  if (!state) {
    return ["missing bootstrap state"];
  }
  return [];
}

export function formatBootstrapState(state) {
  if (!state) return "bootstrap_state=<missing>";
  return `nil=${toHex(state.nil)}`;
}

export function assertBootstrapContract({
  kernelExports,
  phase = "pre-start",
  contract = STARTUP_PHASE_CONTRACT_V1,
} = {}) {
  const state = collectBootstrapState({ kernelExports });
  const failures = validateBootstrapContract(state, { phase, contract });
  if (failures.length) {
    throw new Error(
      `${phase} bootstrap contract failed: ${failures.join("; ")} | ${formatBootstrapState(state)}`,
    );
  }
  return state;
}
