# Ordered level-1 bootstrap prefix

Implemented directly on `wasm2`; awaiting Claude's adversarial review.
Whole-file compilation and cross-loading are reported independently of acceptance.
Counts advance from **21/21/0 to 29/24/0 of 167** (compiled / cross-loaded /
target-loaded). The retained report is
`ccl-evidence/2026-09-26-loader-level1-r1`; its identity is in the source
evidence index. No acceptance or criterion credit is added.

The module compiler now invokes the registered Wasm compiler. Existing targets
retain `COMPILE-FILE`; directed dispatch and unchanged-input skip checks cover
all 17 existing profiles plus Wasm. Level-0 and level-1 run as separate compiler
sessions, retaining both stop-preserving phase records. The first combined
session's duplicate-definition failure is retained, not treated as a success.

The target boot branches report `:WASM / 32 / :WASM32`, omit the unavailable
`home:` directory initialization, default to batch mode, and leave native GC
accounting buffers unavailable (`NIL`). The native foreign `+NULL-PTR+` constant
is not defined for Wasm. Lambda-list metadata uses the already adopted strong
retention policy. Native branches and upstream kernel sources are unchanged.

The ordered compiler completes eight level-1 files: `level-1`, `l1-cl-package`,
`l1-boot-1`, `l1-boot-2`, `l1-boot-3`, `l1-utils`, `l1-init`, and `l1-symhash`.
It stops at `%CURRENT-TCR` in `l1-numbers`' random-state seeding. Source-free
cross-loading stops earlier: `l1-boot-2` contains FASL-EVAL expressions for
`(SETF-FUNCTION-NAME 'INPUT-STREAM-SHARED-RESOURCE)` and
`(SETF-FUNCTION-NAME 'STREAM-EXTERNAL-FORMAT)`. Canonical setter identity is
not yet implemented by the cold loader. The original failed complete load is
retained; the final cross-load explicitly ends before that file.

The execution image contains all level-0 files and the complete `l1-utils`
FASL, plus the existing selected support definitions and new witnesses.
Complete original forms for `HOST-PLATFORM` and the two accounting variables
are selected from their product files. Selection rewrites no definition body
and adds no whole-file credit. `execution-files.json` lists every deferred
production file. Platform/accounting/retention rows have explicit target
expectations on their native sides; utility rows use the native CCL oracle.
Batch-mode and directory boot initializers are compiled, not executed here.
No target LOAD, full boot, RNG, foreign pointer or GC timing service is claimed.

All four execution modes complete: plain, collecting, relocated, and relocated
with collection. Each uses 1,343 modules, executes 86/93 initializers, produces
151/155 expected observations and passes 141 controls. Of the 151 observations,
148 match native behavior and three use the explicit target expectations above.
Plain modes perform 14 collections; collecting modes perform 259. The four
previously pending rows remain: PUTHASH's GC-lock dependency and three malformed
FASL-input cases that have not reached native condition delivery. The execution
summary therefore remains `INCOMPLETE`.

Seven startup refusals are explicit: the package-reference table needs callable
EQL; package registration needs that table; force-export needs callable STRING=;
the pathname escape DEFSTATIC initializer is not ready; the TYPE-OF alias needs
callable %TYPE-OF; and both accounting variables' pointer-function registrations
are not ready. The pathname and registration failures are retained as checked
refusals without claiming a complete dependency diagnosis. Accounting values
are witnessed independently as NIL; registration and complete boot stay open.

```sh
python3 tests/wasm/stage1/bootstrap-validation/run.py gc
python3 tests/wasm/stage1/loader-level1/run.py /private/tmp/ccl-work/codex/loader-level1/execution
python3 tests/wasm/stage1/loader-level1/qualify.py native /private/tmp/ccl-work/codex/loader-level1-native/run
python3 tests/wasm/stage1/loader-level1/qualify.py readers /private/tmp/ccl-work/codex/loader-level1-readers/run
python3 tests/wasm/stage1/loader-level1/qualify.py corpus /private/tmp/ccl-work/codex/loader-level1-corpus/run
```

Reader qualification compares the four modified level-1 files with their
pre-change Git revision `3bf0b390`. Exact unchanged foreign-call subforms are
retained and omitted symmetrically because macOS has no Windows interface
database; changed forms and their reader conditionals stay intact. This
handles foreign calls nested in the large boot-file MACROLET. Native R6
decodes every changed artifact, separately names the three intentional shared
compiler functions, and requires all other executable code and data to match.

Qualification passes 21,843 native tests, restores all 164 FASLs, compares
68 reader results across 17 profiles, and runs all 26,048 compiler/runtime
comparisons freshly (zero inherited or sampled results). The dispatcher checks
all 18 target entries and their unchanged-input skip paths. Collector and owner
checks are reused from audit 183 by exact source/runtime identity: 82 checks and
ten killed faults. No second integration replay or Git-free replay is claimed.

Product Lisp delta: **22 added / 10 removed** across five files. Final execution
took 253.16 seconds, native qualification 180.38 seconds, corpus preparation
410.67 seconds and corpus execution 215.89 seconds. These are local verification
costs, not performance claims. Original failed probes, the first complete-load
failure, and the metadata witness's unavailable HASH-TABLE-WEAK-P call are
retained under `development`; final inputs and toolchain hashes are recorded.
Generated binaries are inventoried by hash instead of duplicated in retention.

Accepted originals remain 575 executed / 535 non-NIL; comparable admission
remains 2,050/2,231 (not recounted), and the Stage 1 ledger remains 21/12.
O-104's restored-image hash witness and O-105's target-FASL obligations remain
open. The collector and owner are unchanged and retain their audit-183 checks.
