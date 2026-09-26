# Complete level-0 FASL reader proposal

**21 compiled / 21 cross-loaded / 0 target-loaded of 167**, up from 20/20/0.
All 21 level-0 files compile whole. Target `LOAD` still needs the Wasm code
installer for opcode 72. This is a pinned delta over the hash/I/O proposal
at `fe93c6ed`; neither proposal is integrated or accepted.

The patch replaces native FASL buffer pointers with octet vectors and a
cursor, lowers `%WORD-TO-INT`, validates immediate FASL values, and rejects
native code/function opcodes. Native code-coverage notes remain refused.
The bootstrap entry clears its target function cell instead of a native TCR
slot. The redundant target `MACPTRP` definition is removed in favor of the
shared predicate. Documentation and binding-index tables use the previously
adopted Stage 1 strong-retention policy at their constructors.

The Wasm cross-loader now reserves geometric scratch headroom for code
records. It preserves addresses and expression-table references. The original
slow run and a stack trace identify repeated `XLOAD-MORE-SPACE` copying;
the first corrected complete cross-load took 21.49 seconds. That measures
host cross-loading, not target execution or startup performance.

Shared drivers accept explicit witnesses, cases, controls and load checks.
The ordered driver uses `cross-compile-level-0`; a fresh process cross-loads
all unique FASLs after their production sources have been removed. The two
target support files are counted once even though both directory compilers
encounter them. Selected support definitions receive no whole-file credit.

```sh
python3 tests/wasm/stage1/loader-fasl/run.py <managed-output>
python3 tests/wasm/stage1/loader-fasl/exercise.py <managed-output>
python3 tests/wasm/stage1/loader-fasl/qualify.py native <managed-native-output>
python3 tests/wasm/stage1/loader-fasl/qualify.py readers <managed-reader-output>
python3 tests/wasm/stage1/loader-fasl/qualify.py corpus <managed-corpus-output>
python3 tests/wasm/stage1/loader-fasl/replay.py <managed-replay-workspace> <managed-output>
```

Use `/private/tmp/ccl-work/<agent>/<packet>/` workspaces. `packet.py` verifies
final identities, retains reports and original failures, references regenerable
binaries by hash, and removes the retained run directories.

Admission has not been recounted; the last comparable count is 2,050/2,231.
Accepted original execution remains 575/535 (executed / non-NIL witness),
and the ledger remains 21 accepted / 12 missing. No target `LOAD`, complete
bootstrap, native-pointer, code-coverage or weak-table semantics are claimed.

Execution remains **INCOMPLETE**: **143/147 native rows match** in each of four
placement/collection modes, with **136 controls**, **1,186 modules**, and
**63/66 initializers executed**. The modes perform 9/220 collections. All 21
new successful parser rows match native; three new condition-delivery rows and
the inherited PUTHASH row remain unmatched.

A Git-free rebuild under a different root reproduces all **3,593** FASL, WAT,
Wasm and binary artifacts and all four modes' observations, controls, failures,
initializer outcomes and collection counts.

Native R6/R6a passes 21,843 tests with 164 FASLs restored and identical decoded
existing-target code. Reader comparisons pass for six files across all 17
existing target profiles (102 comparisons). The exact proposed sources and
inherited strong-vector collector pass 26,048 fresh compiler/runtime comparisons.
The parent packet's 54 collector checks are reused by unchanged collector
identity. Product Lisp delta: **125 added / 8 removed**, plus one duplicated
architecture-fixture constant.

The new startup boundaries are callable `EQL` (the package-reference table),
its dependent package-registration initializer, and callable `STRING=` / `ASSOC`
(the force-export package closure). The two parent weak-table refusals are
removed by the adopted strong-retention constructors. Native `PUTHASH` still
needs the GC-lock functions. Three malformed-input cases raise checked errors
but do not reach their Lisp `ERROR` handler as the native cases do; these rows
retain their native expected values and receive no match credit.

Deferred coverage includes real descriptor reads/refills/seeks, platform and
invalid-immediate guard isolation, and new guard mutants. Area metrics and
hash-header guard isolation remain parent obligations. The in-memory parser
witnesses do not establish host file I/O or complete target `LOAD`.

[Retained packet](../../../../../ccl-evidence/2026-09-25-loader-fasl-r1/packet.json)
contains final input identities, reports, original failures and the replay
comparison; regenerable binaries are represented by hashes.
Packet SHA-256: `70efd188f81351d2c5b354efbf04729cbdd23a7b47f89c160a185b8c83fad704`.
