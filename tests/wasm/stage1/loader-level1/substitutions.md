# Namespace weak-table substitutions after audit 185

Audit 185 accepted the continuation at `a55b18c6`. This follow-up removes the
Wasm `*host-ftd*` ordinal-table override, restoring FTD's existing weak-value
default. Namespace support initialization preserves the weak-key `*lfun-names*`
table created by `l0-def`, including any names already registered there.

Namespace initialization leaves all eight public hash function cells intact.
The generated accessors already distinguish image-owned tables from native
runtime tables; their native path calls the public functions. Rebinding those
cells to the representation wrappers would recurse on native tables. Package
INTERN/FIND-SYMBOL bindings still use the namespace representation boundary.

The new execution witness calls the actual product namespace support initializer,
checks all eight hash bindings and the function-name table's identity, and
requires that table to remain weak-key. The existing native-matched weak-table
cases then run after that initializer. Selection of this complete initializer
adds no whole-file or full namespace-startup credit. Foreign-type whole-file
execution remains outside this loader prefix; the substitution restores the
existing constructor default rather than adding a new table implementation.

O-113: the shared retention writer now inventories saved `.image` files in
`non-reproducible.json`, with the observed hash and size. Reproducible binaries
remain in `regenerable.json`. A directed retention check varies the saved image,
requires identical reproducible inventories and validates both report packs.
The historical R2 pack is immutable; its saved host-image entries are
excluded by the bound [inventory correction](../../../../doc/WASM/stage1/audit185-inventory-correction.json).

O-116: the weak witnesses' indirect calls deliberately exercise installed public
function cells as well as the generated representation dispatch paths. Product
initializers in `l0-def` and `l1-utils` also directly call MAKE-HASH-TABLE, so the
indirect idiom is not the only constructor coverage.

The historical namespace-consumers fixture still installs its strong-only
provider. Its `%documentation` constructor is explicitly marked to regain
`:weak t` when that harness migrates to the native hash implementation. Changing
that fixture now would request a capability its provider deliberately refuses.
Runtime tables supersede the strong substitute (O-115); image-owned tables still
await builder conversion. O-114 and O-117 remain open.

Whole-file counts remain **36/36/0 of 167**; next compile stop is
`:BOOTSTRAP-TYPECHECK` in `l1-streams`. Originals remain **575/535**, ledger
**21/12**; no target LOAD, full boot or criterion credit. Product Lisp delta:
**3 added / 16 removed**. This follow-up awaits independent review.

```sh
python3 tests/wasm/stage1/loader-level1/run.py /private/tmp/ccl-work/codex/namespace-weak-final/execution
python3 tests/wasm/stage1/loader-level1/qualify.py native /private/tmp/ccl-work/codex/namespace-weak-native/run
python3 tests/wasm/stage1/loader-level1/qualify.py readers /private/tmp/ccl-work/codex/namespace-weak-readers/run
python3 tests/wasm/stage1/loader-level1/qualify.py corpus /private/tmp/ccl-work/codex/namespace-weak-corpus/run
python3 tests/wasm/stage1/loader-chain/retention-check.py /private/tmp/ccl-work/codex/namespace-weak-retention/run
```

Native R6/R6a passes all **21,843** enabled tests and restores **164** FASLs:
45 are byte-identical and 119 compare equal after the already declared code
and source-location allowances. Native qualification took **180.61 seconds**.
The reader matrix passes **238** comparisons across **17** existing profiles,
now including `lib/foreign-types.lisp`. These are validation costs, not runtime
performance measurements.

The first new namespace witness used MAPCAR and EVERY; both public cells were
unbound in this limited execution image, as the retained diagnostic confirms.
The final witness uses DOLIST to compare the same bindings. The original failure,
witness, diagnostic and exact input identities are retained in `development`.
This fixture correction changes no product source or native qualification input.

One native oracle invocation reported count 1 for dropped weak-key case
`weak-0-0`, while the target reported 0 and both reported the lookup absent.
Three fresh native-only replays from the identical witness source reported 0.
The differing oracle, target output and all three replays are retained. Its
cause remains unexplained; this is a disclosed native-oracle repeatability
limitation, not a weakened comparison or a proven product defect. The final
run regenerates the oracle and reuses the unchanged compiled target image
through the runner's checked `--resume` path.

The full corpus passes **26,112 fresh comparisons**, with no inherited or
sampled rows: preparation **416.08 seconds**, execution **227.34 seconds**.
The unchanged collector/owner qualification is reused by exact source and
binary identity: **123 checks and 17 killed mutants** from the accepted weak
pack. No new collector replay is claimed.

Final target execution passes all four modes with **1,480 modules**, **93/97
initializers**, **177 observations**, **141 controls**, and **25/299 collections**.
The namespace binding/table witness returns `(T T T)` on native and target;
all 52 weak-table comparisons still match. Five inherited pending cases and
four startup refusals keep overall execution **INCOMPLETE**. The checked resume
run took **67.51 seconds**, excluding its earlier compilation/materialization.
Evidence is retained in `ccl-evidence/2026-09-26-namespace-weak-r1`.
