# Audit 182: hash collection protocol repairs

**21 compiled / 21 cross-loaded / 0 target-loaded of 167**, unchanged.
This is a pinned delta over the hash/FASL proposal stack. It addresses O-97
and O-98 before joint integration; the repair itself awaits Claude review.
The shared product paths and accepted contracts remain unchanged.

The collector owner's copying service publishes a real monotonic count with
each successful collection. `%GET-GC-COUNT` exposes it to target Lisp, and the
three shared hash-table stores use their original expressions. Exhaustion
refuses before copying instead of wrapping into an old table stamp. The
[TCR extension](counter.md) binds the new raw field to the existing schema.

O-101 is repaired by restoring native constructor flags: `track_keys` is no
longer forced on every native hash vector. The tests exercise both tracking
and component-address states, repeated movement, resetting the GC stamp, and
an explicit rehash request. Actual `PUTHASH` remains blocked by the GC-lock
functions; a collect-then-GETHASH test is still owed when that boundary lands.

O-98 controls cover each initialized and uninitialized native-vector admission
clause, including finalization, cache-index type/range, odd widths, capacity,
GC-stamp type, deletion/count type and sum, and tracking-disabled movement.
The individual `deleted <= capacity` and `count <= capacity` clauses are
implied by `deleted + count <= capacity` after both unsigned tagged counts
are admitted; MC9 removes the deleted bound and sum together to expose it.
All nine audit mutations and a counter-exhaustion mutation must be killed by
the named directed control. Counter tests also cover refusal recovery,
non-root scalar storage, two-copy growth, and the final representable count.

O-100 adds the allocator's upper-limit refusal and an isolated parser-offset
refusal with zero copy length. Descriptor refills, seeks, `%FASLOAD`'s allocated
buffer, and immediate-character limit controls remain open with target LOAD.
O-99 requires target encoding (or explicit refusal) in the host immediate
dumper before that installer lands. Neither observation is claimed closed.

For O-102, final execution starts in a fresh directory, binds the producer's
complete output inventory, and retains only declared phase outputs. Exploratory
files stay in development evidence. Raw logs retain workspace paths; replay
compares semantic records and reproducible binaries, not path-bearing logs.

```sh
python3 tests/wasm/stage1/loader-gc/baseline.py <original-failure-output>
python3 tests/wasm/stage1/loader-gc/run.py <fresh-output>
python3 tests/wasm/stage1/loader-gc/exercise.py <output>
python3 tests/wasm/stage1/loader-gc/collector.py <collector-output>
python3 tests/wasm/stage1/loader-gc/qualify.py native <native-output>
python3 tests/wasm/stage1/loader-gc/qualify.py readers <reader-output>
python3 tests/wasm/stage1/loader-gc/qualify.py corpus <corpus-output>
python3 tests/wasm/stage1/loader-gc/replay.py <replay-workspace> <output>
```

Use fresh `/private/tmp/ccl-work/<agent>/<packet>/` workspaces. Keep native,
reader and corpus roots distinct so their leases do not serialize the jobs.
The packet writer checks final source/runtime identities, original O-97
failures, killed collector faults and the Git-free replay before retention.

The repaired image has **1,197 modules**. In each of four placement/collection
modes, **145/149** native rows match, **141 controls** pass, and **66/69**
initializers execute. Plain/collecting modes perform **13/229 collections**.
The four pending rows and three startup refusals are inherited: GC-lock
functions for PUTHASH, malformed-input condition delivery, and callable EQL,
STRING= and ASSOC. The original stack reproduces the new `gc-fresh` failure
in all four modes; its native result is two NILs.

Final product sources pass **21,843 native tests**, all **164 restored FASLs**
and decoded-code equality, **102 reader comparisons across 17 profiles**, and
the full **26,048-case compiler/runtime corpus**. Collector qualification
passes **82 checks and ten killed faults**. Development evidence preserves
the initial constant-package compile failure, the first witness's unrelated
LOGANDC2 failure, and the run rejected because a control changed after its
input hash was captured. The final run binds unchanged input and output
inventories; those failed iterations receive no verification credit.

The final different-root, Git-free replay matches all **3,628 regenerable
artifacts**, including `nfcomp.dx64fsl` and the extensionless saved compiler
image `dx86cl64`, plus every result in all four modes.

[Retained packet](../../../../../ccl-evidence/2026-09-26-loader-gc-r1/packet.json):
`f8d4c671ba05b7665d1e3532733b7d588fa5b6c491d1241635862847d931eae5`.
Evidence size: **114,538,636 bytes**; regenerable binaries are inventoried by
hash. Disposable build and replay workspaces were removed after retention.
Native qualification took 179.73 seconds; corpus execution took 230.16 seconds.
Product Lisp delta is **19 added / 6 removed**, plus three fixture-architecture
lines, three collector C lines and four owner lines. Author editing and
reading were not separately timed; no reviewer or target-startup timing is
claimed.

Accepted original execution stays **575/535**, admission **2,050/2,231**
(not recounted), and the Stage 1 ledger **21 accepted / 12 missing**. No
target LOAD, weak-table semantics, complete boot, or acceptance credit.
