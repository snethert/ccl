# Trusted declarations for accessors — producer results

**Accepted 28 September 2026** at the user's direction after [Claude audit 191](../stage0/claude-review.md), supplied at `1d4648ad`, found no defect in `c716d9f4`. The review explicitly excludes arithmetic parents `047df094` and `f38261de`, which remain producer-verified and awaiting independent review. Whole-file counts remain 82 compiled runtime files and 81 ordinary target loads; originals 575/535 and ledger 21/12 are unchanged. No criterion credit.

The reviewer reproduced the focused, arithmetic-dependency and benchmark build products byte-for-byte, reran all 26,204 corpus comparisons and 21,843 eligible native tests with R6/R6a, and matched the 71 focused rows and both dependency fixtures. All five producer controls and four of five source-level mutants were killed; omitting the LIST NIL branch is equivalent under the current layout (O-148). Nine extra probes matched native execution. A one-replica benchmark smoke measured typed CAR at 8.51 ns and typed SVREF at 15.41 ns; the full timing series was not replayed. O-149 carries the pre-existing ratio-literal loader failure, and O-150 records the trusted-declaration contract. These notes require no producer round for accessor acceptance. Completed verification is reused; unchanged tests were not rerun to record acceptance.

The Wasm backend now uses CCL’s lexical trust-declarations policy for CAR/CDR and SVREF. Declared CONS reads become direct loads; LIST retains NIL handling. A declared SIMPLE-VECTOR and fixnum index avoid representation/span checks. Bounds remain checked unless vector length and index range prove them. Checked policies and THE assertions remain active.

Operands avoid new root frames only when later evaluation cannot collect, or when an immutable uncaptured vector reference can be reloaded from its existing root after index evaluation. Other operands retain their root frame. Assignment, capture, special binding and effectful operand order are covered by native comparisons and moving collections. Stores and calls are unchanged.

Product Lisp: **106 added / 10 removed**, entirely in the Wasm backend. No shared front-end, native ABI or upstream kernel change.

## Unchanged benchmark rerun

All sixteen accepted workloads run in three fresh processes per configuration, nine samples per workload/process. The table reports medians of process medians in ns/iteration. Compilation, qualification and corruption controls finished before the serial timing series. These are complete loops, not isolated accessor instruction costs.

| Workload | Parent default | New native | New default | Liftoff only | TurboFan only | Default/native |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Inline fixnum loop | 3.02 | 2.26 | 2.99 | 7.83 | 3.03 | 1.3× |
| Scalar call | 54.77 | 2.49 | 53.61 | 169.87 | 63.84 | 21.6× |
| Reference argument | 52.04 | 2.14 | 51.54 | 163.44 | 61.46 | 24.0× |
| Reference live across calls | 54.94 | 2.41 | 53.50 | 169.38 | 61.97 | 22.2× |
| Optional arguments | 96.35 | 5.13 | 95.85 | 224.24 | 94.13 | 18.7× |
| Rest arguments | 323.01 | 41.91 | 319.64 | 433.51 | 207.01 | 7.6× |
| Keyword arguments | 82.34 | 10.94 | 82.54 | 217.96 | 89.72 | 7.5× |
| CAR | 17.79 | 2.71 | 17.74 | 34.70 | 21.13 | 6.5× |
| Typed CAR | 15.65 | 2.37 | 8.69 | 19.25 | 11.68 | 3.7× |
| SVREF | 21.83 | 3.00 | 21.81 | 49.27 | 30.20 | 7.3× |
| Typed SVREF | 23.77 | 3.00 | 15.54 | 31.49 | 19.08 | 5.2× |
| EQ | 22.35 | 2.25 | 22.25 | 50.15 | 27.27 | 9.9× |
| Generic fixnum addition | 5.34 | 2.10 | 5.32 | 6.24 | 4.75 | 2.5× |
| Generic double addition | 1680.73 | 16.53 | 1657.65 | 1926.06 | 1654.60 | 100.3× |
| Typed double addition | 2.78 | 2.53 | 2.76 | 5.11 | 3.75 | 1.1× |
| Typed single addition | 2.78 | 2.75 | 2.75 | 5.07 | 3.75 | 1.0× |

[Machine-readable results](declared-accessors-results.json) retain all process medians, observed ranges, allocation brackets, reference Wasm timings and changed body identities. Ranges are not confidence intervals; unchanged workload timing changes are not attributed to this optimization.

The unchanged 4,194,304-iteration cap leaves fast loops below the 50 ms calibration aim; the shortest default-V8 sample is 11.131 ms. Target timer resolution remains one microsecond. No workload or calibration changes were made.

## Qualification

- 71 focused native-matched rows and eight forced moving collections pass: cons fields, NIL, vector bounds/types/lengths, lexical policy, effects, aliases, multiple values and error recovery.
- Five independent emitted-code mutants are killed by native comparison after successful ordinary LOAD: wrong CAR field, wrong NIL result, wrong index, off-by-one bounds and omitted checked vector length.
- Rebuilt float and fixnum dependencies pass 83 and 125 rows, with four and six forced moving collections. Their native references are reused by exact fixture-source hashes.
- All 26,204 compiler-corpus comparisons are fresh and pass, zero sampled or inherited. `%MAP-AREAS` and `%MAP-LFUNS` retain their explicit native-enumeration skips.
- Native R6/R6a passes 21,843 eligible registered tests, with 75 upstream-disabled. All 164 FASLs restore; 42 are byte-identical and 122 receive decoded comparison. Five existing architectures and 17 module profiles retain their snapshots. Pristine U1 baseline evidence is reused by recorded identity.
- 782 reader comparisons and the accepted benchmark assessor/observer controls are reused by exact unchanged source identities.
- Final timing passes 1,728 Lisp samples, 405 hand-written Wasm samples and 36 forced moving collections.

## Ordinary READY

| Run | Launch to READY (s) | Lisp interval (s) | Collections |
| --- | ---: | ---: | ---: |
| 1 | 26.463 | 23.107 | 4 |
| 2 | 26.510 | 23.136 | 4 |
| 3 | 26.641 | 23.334 | 4 |

Median ordinary READY is **26.510 s**. All runs retain 81 loads, seven product modules, eleven instances and no open files or abandoned sessions. These controls use unchanged authenticated audit-190 core archives; this is not a core rebuild or startup optimization.

## Failures and reproduction

The first fixture compilation exposed the missing checked `(simple-vector 4)` type test. The backend now checks representation before the explicit length, with native-matched wrong-length, wrong-kind and wildcard/empty-vector witnesses. The original compilation refusal is retained.

The initial non-fixnum index literal `1/2` failed before fixture execution in the unchanged core’s `$FASL-RATIO`, with checked error 4. The retained trace identifies that loader boundary. The accessor fixture uses `0.5d0` to exercise the same non-fixnum rejection clause; ratio-literal loading remains unresolved and no ratio-index execution is claimed.

[Fixture and reproduction](../../../tests/wasm/stage1/declared-accessors/README.md). One finalized pack, `ccl-evidence/2026-09-28-stage1-declared-accessors-r1`, retains measurements, emitted bundles, focused and mutation results, compressed compiler/native qualifications, original failures and tool/source identities. `inventory.json` authenticates every artifact. Prior input trees are referenced rather than duplicated.

No reviewer was invoked. Supplied independent review remains required before acceptance.
