# Level-1 continuation and runtime weak tables

Whole-file counts advance **29/24/0 → 36/36/0 of 167**. The additional complete
files are `l1-numbers`, `l1-aprims`, `l1-sort`, `l1-dcode`, `l1-clos-boot`,
`l1-clos` and `l1-unicode`. Cross-loading now reaches the same 36-file prefix,
with sources removed. Compilation stops in `l1-streams` at
`:BOOTSTRAP-TYPECHECK`. Audit 185 (`fd385a5f`) found no defect; the user
accepted this continuation and its runtime weak tables.

The cross-loader admits the exact `(SETF-FUNCTION-NAME (QUOTE symbol))` form
through its optional target evaluator. Independently compiled files share the
same canonical setter symbol, which remains visible to target lookup through
symbol properties. Thirteen malformed forms refuse before changing loader
state; equal-named uninterned bases stay distinct and repeated lookups agree.
The code-record format also carries target special-variable indices and
reserves nested code identities before resolving sibling imports. Execution
covers locally declared specials, mutual LABELS calls and setter calls across
separate FASLs.

Wasm random seeding uses the embedding's `*wasm-random-source*` callable,
requiring an unsigned 32-bit result. No host entropy is serialized; installing
a real entropy provider remains an embedding obligation. Ordinary CCL random
state and list sorting definitions now compile and execute. The target's
31-bit generator can return bignums, so the numeric boundary admits wide byte
types and bignum LDB; Wasm random operations preserve those bits and construct
state vectors without unavailable coercion paths. Native platform branches
remain unchanged.

Runtime-created weak-key and weak-value tables now use the collector's
fixed-point traversal and native Lisp hash operations, as described in
[weak hash support](weak-hash.md). This prefix's lambda-list variable is unbound
in the serialized image, so its restored weak DEFVAR constructor executes at
runtime (O-110). Owner-built metadata tables keep their existing representation.
The collector qualification is reused by exact collector/owner/binary identity
from `2026-09-26-weak-hash-r1`: 123 checks and 17 killed mutations. The final
continuation pack references that record and its original weak-table failures.

O-106 uses quoted calls plus local function-type declarations for the two
late-bound cross-loader functions. A focused compile showed that quoted calls
alone still warn; the failed build and the warning-free declaration probe are
retained. O-107 changes HOST-PLATFORM's CPU to `:wasm`, making the conventional
formatted name `WasmWASM32`; the target witness requires that CPU family.
The version formatter itself is not executed by this prefix.

O-108 remains an explicit limitation: accounting observations see declaration
NIL, not evaluation of the accounting value expression. Of 176 successful
observations per mode, 169 use native-computed results (one fresh-RNG case has
an explicit equivalent native seed setup) and seven use literal target
expectations: platform, metrics, metadata and four seed boundary/collection
rows. The earlier weak-pack summary's 173/3 split was a reporting error; it
omitted the four seed rows. Its raw observations and all 52 weak comparisons
are unchanged.

The execution image contains all level-0 files and whole `l1-utils`,
`l1-numbers` and `l1-sort`, plus selected original support forms and witnesses.
Its enumerated file list is separate from the 36-file cross-load. Five pending
cases remain: non-lock-free PUTHASH's GC-lock dependency, three malformed-FASL
condition cases and seed-condition delivery. Four startup refusals remain:
STRING= package export, %TYPE-OF, and the two accounting registrations.
Complete execution stays INCOMPLETE. O-109's boot-default witnesses and
O-112's boot-order obligation remain open; no target LOAD or full boot is claimed.

O-111's reader qualification now reads the pinned pristine U1 source archive,
verifies its hash and compares all 13 modified shared files across 17 existing
target profiles. It no longer invokes Git. The runner also asserts the dispatch
report directly. Native R6 separately names the three compiler-driver functions,
the appended cross-loader slot and FASL-EVAL dispatch; existing accessors and
all undeclared executable content must compare equal.

```sh
python3 tests/wasm/stage1/loader-level1/run.py /private/tmp/ccl-work/codex/level1-review/execution
python3 tests/wasm/stage1/loader-level1/qualify.py native /private/tmp/ccl-work/codex/level1-review-native/run
python3 tests/wasm/stage1/loader-level1/qualify.py readers /private/tmp/ccl-work/codex/level1-review-readers/run
python3 tests/wasm/stage1/loader-level1/qualify.py corpus /private/tmp/ccl-work/codex/level1-review-corpus/run
```

The original accepted-prefix report remains in [README.md](README.md).
Accepted originals remain **575/535**, admission **2,050/2,231** (not recounted),
and the Stage 1 ledger **21 accepted / 12 missing**. Product Lisp delta against
the accepted prefix: **337 added / 69 removed**; collector C: **78 added /
17 removed**. The weak-only delta and its lack of separate whole-file credit
remain documented in the earlier weak report.

Final target execution passes all four modes: 1,478 modules, 93/97
initializers, 176 observations and 141 controls per mode, with 25/298
collections. All 52 weak-table comparisons match the native oracle. Native
R6/R6a passes 21,843 tests and restores 164 FASLs; 45 registered FASLs are
byte-identical and 119 pass decoded comparison with declared changes and
permitted source locations. The two dispatcher warnings are absent.
Reader qualification passes 221 comparisons across 17 existing profiles;
dispatch checks pass for those profiles plus Wasm. Final target execution took
340.36 seconds and native qualification 181.65 seconds. These are verification
costs, not measurements of runtime performance.

The full compiler/runtime corpus passes **26,112 fresh comparisons**, with
zero inherited or sampled results. Preparation took 421.78 seconds and
execution 228.07 seconds. Final evidence is retained in
`ccl-evidence/2026-09-26-loader-level1-r2`, with exact source/tool identities,
original development failures and references to the unchanged collector pack.
Generated binaries are inventoried by hash. No acceptance replay is added.
