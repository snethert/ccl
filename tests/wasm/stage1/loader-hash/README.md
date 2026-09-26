# Whole-file hash / I/O proposal

Pinned-parent patch against `ccf4b638c4150413b8ca4e429b881fd492606bee`.
**20 compiled / 20 cross-loaded / 0 target-loaded of 167**, up from 11/11/0.
Next ordered stop: `level-0/nfasload.lisp`, `%CONSMACPTR%`.
Pending Claude review; product paths are not integrated.

The patch implements native strong hash-vector allocation and collection,
checked byte-buffer loads/stores, typed integer vector construction, and
Wasm file/area/lock boundaries. The unchanged UTF memory codecs and nine
additional complete files compile through CCL's front end. Weak tables and
collector-owned whole-image enumeration/accounting remain unavailable.

The shared `loader-chain` drivers take explicit source, witness, case and
control inputs. Complete FASLs cross-load in a fresh process after source
removal. Selected dependency definitions receive no whole-file credit.
Whole-image startup and target `LOAD` remain incomplete.

Reproduce under `/private/tmp/ccl-work/<agent>/<packet>/`:

```sh
python3 tests/wasm/stage1/loader-hash/run.py <output>
python3 tests/wasm/stage1/loader-hash/exercise.py <output>
python3 tests/wasm/stage1/loader-hash/qualify.py native <native-output>
python3 tests/wasm/stage1/loader-hash/qualify.py readers <reader-output>
python3 tests/wasm/stage1/loader-hash/qualify.py corpus <corpus-output>
python3 tests/wasm/stage1/loader-hash/collector.py <collector-output>
```

Final execution is **INCOMPLETE**, with **122/123 native rows matching** in
all four placement/collection modes, 126 controls per mode, and 10/183
collections. Strong-vector and UTF/buffer witnesses pass. Native PUTHASH
still needs `%LOCK-GC-LOCK` / `%UNLOCK-GC-LOCK`; both function cells are unbound.
Two weak-table initializers refuse (documentation and binding-index map),
so only 51/53 initializers execute. These failures remain in the reports.

Qualification: 21,843 native tests, 164 restored FASLs, identical decoded
existing-target code; 68 reader comparisons across all 17 existing target profiles;
26,048 compiler/runtime comparisons and 54 collector checks pass. Native
`%MAP-AREAS` and its `%MAP-LFUNS` caller are explicitly deferred: this target
refuses heap enumeration. A Git-free replay was not run. Minor remaining
coverage: area metrics, every hash-header clause, and new guard mutants.
Product Lisp changed: **245 added / 26 removed**; collector: 19 added / 2 removed.

[Retained packet](../../../../../ccl-evidence/2026-09-25-loader-hash-io-r1/packet.json)
contains exact final inputs, reports and original development failures;
regenerable binaries are represented by hashes.
Packet SHA-256: `f5b78e3e2bca43b1c9f9674c32b470a856d86b0b0abcd50caf81ab04dc8e93d5`.
