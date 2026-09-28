# Fixnum locals and loop arithmetic — producer results

Producer verification completed 28 September 2026; **independent review pending** for this change and its declared-float parent `047df094`. Whole-file counts remain 82 compiled runtime files and 81 ordinary target loads, seven product modules and eleven instances. Historical originals 575/535 and ledger 21/12 are unchanged; no criterion credit.

Inline fixnum addition falls from **39.67 to 3.02 ns/iteration** (13.1× faster than the float-optimization parent). Typed double falls again, **32.93 → 2.78 ns**, through the loop changes. These are complete loop timings, not isolated instruction costs.

Product Lisp: **114 added / 9 removed**, entirely in the Wasm backend. No runtime layout, native ABI, shared front-end or upstream kernel change.

## Implementation and correctness boundary

Required/local variables with a target fixnum type occupy tagged `i32` locals when uncaptured and non-special. Every binding/assignment checks the tag before retaining the value. Declared fixnum arithmetic uses local operand staging; general arithmetic also has a scalar fast path when both operands are simple non-collecting reads. Operands evaluate once, left to right. General nodes are rooted before any fallback that can collect. A promoted float read can box, and a checked type assertion can call Lisp; neither is treated as a simple read.

General add/subtract/multiply widen to `i64` and test whether the tagged result fits `i32`. Overflow reaches the existing bignum service; other numeric types retain the existing service. CCL’s explicit no-overflow operators keep their direct `i32` semantics. Declaring only the operands fixnums never discards overflow handling. Checked result assertions remain active.

DOTIMES leaves its index untyped in the front-end IR. Its increment now takes the general scalar fast path with runtime tag/overflow guards; no induction proof is claimed. IF/PROGN used for effect avoid publishing discarded multiple values. Captured/special variables retain shared storage. Accessor checks, loop polling and the call convention are not redesigned. Static WAT body counts still include prologues and cold fallback/error paths; they are not dynamic instruction counts.

## Accepted benchmark rerun

The accepted sixteen-workload source and harness are unchanged. Each entry is the median of three fresh-process medians, with nine samples per workload/process. Compilation, qualification and mutation runs finished before the final serial timing series. Native macOS x86-64 CCL and default/Liftoff-only/TurboFan-only V8 use the same host; exact tool identities are retained.

| Workload | Accepted default baseline | Float parent default | New native | New default | Liftoff only | TurboFan only | Default/native |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Inline fixnum loop | 39.75 | 39.67 | 2.23 | 3.02 | 7.85 | 3.00 | 1.4× |
| Scalar call | 99.00 | 98.87 | 2.49 | 54.77 | 171.71 | 62.98 | 22.0× |
| Reference argument | 87.05 | 86.98 | 2.15 | 52.04 | 164.04 | 61.39 | 24.2× |
| Reference live across calls | 98.02 | 97.42 | 2.41 | 54.94 | 170.54 | 62.05 | 22.8× |
| Optional arguments | 205.30 | 203.37 | 5.14 | 96.35 | 223.00 | 94.50 | 18.8× |
| Rest arguments | 364.83 | 364.84 | 42.15 | 323.01 | 441.23 | 207.40 | 7.7× |
| Keyword arguments | 188.04 | 186.76 | 10.86 | 82.34 | 221.90 | 89.62 | 7.6× |
| CAR | 76.35 | 75.01 | 2.71 | 17.79 | 34.61 | 21.30 | 6.6× |
| Typed CAR | 73.30 | 73.22 | 2.37 | 15.65 | 34.38 | 20.08 | 6.6× |
| SVREF | 82.55 | 82.47 | 3.00 | 21.83 | 50.53 | 30.64 | 7.3× |
| Typed SVREF | 82.52 | 82.21 | 3.03 | 23.77 | 52.47 | 29.91 | 7.9× |
| EQ | 80.40 | 79.94 | 2.25 | 22.35 | 50.16 | 27.34 | 9.9× |
| Generic fixnum addition | 59.16 | 59.59 | 2.10 | 5.34 | 6.24 | 4.78 | 2.5× |
| Generic double addition | 1726.44 | 1732.12 | 16.65 | 1680.73 | 1828.55 | 1659.70 | 101.0× |
| Typed double addition | 1725.56 | 32.93 | 2.52 | 2.78 | 5.09 | 3.76 | 1.1× |
| Typed single addition | 1716.09 | 33.14 | 2.75 | 2.78 | 5.07 | 3.76 | 1.0× |

All numbers are ns/iteration. The [machine-readable record](fixnum-loops-results.json) retains process medians, observed ranges, allocation brackets, hand-written engine references and changed body hashes. Ranges are not confidence intervals. The call/accessor improvements include faster surrounding arithmetic and loop bookkeeping; they do not demonstrate a new call or accessor implementation.

Default scalar-call process medians vary more than the arithmetic rows: 53.19, 57.81, 54.77 ns. The reported result uses their median; no extra runs were selected to narrow that range.

Fast target loops now reach the unchanged 4,194,304-iteration calibration cap before the 50 ms aim. The shortest default-V8 timed sample is 11.301 ms; the timer still reports microseconds. This differs from the original slower target baseline's minimum interval and is retained explicitly. No iteration cap or benchmark source changed.

## Qualification and READY

- 125 focused native-matched observations pass, including overflow, signed comparisons, logical operations, binding/assignment values, captures/specials, evaluation order, cleanup/early exit, generic floats/bignums, checked errors and recovery. Six forced moving collections preserve immediates and boxed references.
- Four independent emitted-code mutants are killed: wrong arithmetic, missing overflow guard, unsigned comparison and missing register type refusal. They load normally; comparisons/assertions detect the defects.
- The existing float fixture is rebuilt with this compiler: 83 native-matched rows and four forced moving collections pass. Its unchanged native observations are reused by exact fixture-source identity.
- All 26,204 compiler-corpus comparisons are fresh and pass, zero sampled and zero inherited. Explicit native skips remain `%MAP-AREAS` and `%MAP-LFUNS`, whose target collector enumeration has no matching native operation.
- Native R6/R6a passes all 21,843 eligible registered tests (75 upstream-disabled); 164 FASLs restore. Forty-two compare byte-identically and 122 undergo decoded comparison with only the four existing compiler-driver differences allowed. Five existing architectures and 17 module profiles retain their snapshots. The pristine U1 baseline suite is reused by recorded identity.
- The 782 reader comparisons and accepted benchmark assessor/observer controls are reused by exact unchanged source hashes.
- The final benchmark passes 1,728 timed Lisp samples, 405 hand-written Wasm samples and 36 forced moving collections.

| Ordinary READY run | Launch to READY (s) | Lisp interval (s) | Collections |
| --- | ---: | ---: | ---: |
| 1 | 26.738 | 23.380 | 4 |
| 2 | 27.197 | 23.696 | 4 |
| 3 | 26.509 | 23.161 | 4 |

Median ordinary READY is **26.738 s**. All runs retain 81 loads, seven modules, eleven instances and no open files or abandoned sessions. These use the unchanged authenticated audit-190 core archives. Newly compiled benchmark/focused bundles load separately; the full corpus independently rebuilds with the new compiler. No core rebuild or startup speedup is claimed.

## Failure evidence and reproduction

The first focused fixture completed its integer rows but stopped while FORMAT attempted to print a float, a pre-existing READY limitation. The fixture now compares exact float bits. The original source, source hashes, native output and target failure remain in the evidence pack. Preliminary smoke timings overlapped qualification and are excluded from the results above.

[Fixture and reproduction commands](../../../tests/wasm/stage1/fixnum-loops/README.md). One finalized pack, `ccl-evidence/2026-09-28-stage1-fixnum-loops-r1`, retains raw measurements, emitted code, new bundles, focused/mutation observations, compressed full corpus and native comparisons, original failure evidence and source/tool identities. `inventory.json` authenticates every artifact. Existing prerequisite trees are referenced by committed identity rather than duplicated.

Next: supplied independent review, then declared accessor specialization before changing the call convention. No reviewer was invoked.
