/*
 * Pre-fasload L0 bootstrap contract.
 *
 * This contract is the host-side source of truth used by make-real-image.mjs
 * before the first required %FASLOAD call.
 */

const REQUIRED_PACKAGES = Object.freeze([
  Object.freeze({ packageName: "COMMON-LISP" }),
  Object.freeze({ packageName: "CCL" }),
  Object.freeze({ packageName: "KEYWORD" }),
]);

/*
 * Level-0 const-pools needed for the first %FASLOAD boundary.
 * The gate forces these refs to become non-NIL before %FASLOAD is allowed.
 */
const REQUIRED_CONST_POOLS = Object.freeze([
  Object.freeze({
    entryIndex: 4360,
    requiredRefs: Object.freeze([0, 1, 2, 5, 6, 7]),
    source: "fasload-simple-open",
  }),
  Object.freeze({
    entryIndex: 4372,
    requiredRefs: Object.freeze([0, 1, 2, 5, 6, 7]),
    source: "fasload-open",
  }),
  Object.freeze({
    entryIndex: 4412,
    requiredRefs: Object.freeze([0, 1, 2, 3]),
    source: "fasload-dispatch",
  }),
]);

/*
 * Seed from startup blockers plus symbols present in the level-0 const pools.
 */
const REQUIRED_SYMBOLS = Object.freeze([
  Object.freeze({ packageName: "CCL", symbolName: "%FASLOAD", source: "fasload-core" }),
  Object.freeze({ packageName: "CCL", symbolName: "%FASL-OPEN", source: "fasload-core" }),
  Object.freeze({ packageName: "CCL", symbolName: "%SIMPLE-FASL-OPEN", source: "fasload-core" }),
  Object.freeze({ packageName: "KEYWORD", symbolName: "DEFAULT", source: "entry-4412" }),
  Object.freeze({ packageName: "CCL", symbolName: "*VECTOR-OUTPUT-STREAM-DEFAULT-INITIAL-ALLOCATION*", source: "entry-4412" }),
  Object.freeze({ packageName: "CCL", symbolName: "%STRUCTURE-REFS%", source: "entry-4360/4372" }),
]);

const REQUIRED_CALLABLES = Object.freeze([
  Object.freeze({ packageName: "CCL", symbolName: "%FASLOAD" }),
  Object.freeze({ packageName: "CCL", symbolName: "%FASL-OPEN" }),
  Object.freeze({ packageName: "CCL", symbolName: "%SIMPLE-FASL-OPEN" }),
]);

const REQUIRED_SPECIALS = Object.freeze([
  Object.freeze({
    packageName: "CCL",
    symbolName: "%STRUCTURE-REFS%",
    requireNonNil: false,
  }),
  Object.freeze({
    packageName: "CCL",
    symbolName: "*VECTOR-OUTPUT-STREAM-DEFAULT-INITIAL-ALLOCATION*",
    requireNonNil: true,
  }),
  Object.freeze({
    packageName: "CCL",
    symbolName: "*FASL-API*",
    requireNonNil: false,
  }),
]);

/*
 * Plan update (artifact-first startup):
 * - startupBindingMap generation uses this contract's required special-variable
 *   set for vcell initialization and emits fcell bindings from a
 *   comprehensive level-0 function scan.
 * - The target architecture is that make-real-image applies a complete
 *   precomputed startup map and performs no broad runtime const-pool discovery.
 * - Transitional runtime derivation (if present) must remain seed-scoped,
 *   machine-bounded, and never replace strict gate/phase semantics.
 */

export const BOOTSTRAP_L0_CONTRACT_V1 = Object.freeze({
  id: "bootstrap-l0-contract-v1",
  phase: "pre-fasload",
  requiredPackages: REQUIRED_PACKAGES,
  requiredConstPools: REQUIRED_CONST_POOLS,
  requiredSymbols: REQUIRED_SYMBOLS,
  requiredCallables: REQUIRED_CALLABLES,
  requiredSpecialVariables: REQUIRED_SPECIALS,
});
