# Declared float unboxing — producer results

Producer verification completed 28 September 2026; **independent review pending**. Whole-file counts stay at 82 compiled runtime files and 81 ordinary target loads; seven product modules / eleven instances. Historical originals 575/535 and ledger 21/12 are unchanged; no criterion credit.

Typed double addition falls from **1,725.56 to 32.93 ns/iteration** (52.4× faster); typed single falls from **1,716.09 to 33.14 ns** (51.8×). These are complete loop costs under default V8. The remaining loop, fixnum and call protocol stays in place.

Product Lisp: **194 added / 6 removed**, in the Wasm backend. One runtime layout initialization also changes. The native ABI and upstream kernel are unchanged.

## Implementation and scope

NX1 already supplies typed single/double arithmetic operators and lexical floating-point policy. The backend now emits `f32`/`f64` add, subtract, multiply and divide when that policy permits unchecked arithmetic. Eligible uncaptured, non-special declared variables stay in float locals, with checked unboxing at entry/binding and boxing at Lisp value boundaries. Assignment results discarded by a loop no longer allocate a box each iteration. Raw float bits survive calls and moving collection without becoming GC roots.

Promotion is conservative: if a candidate flows into an unknown operation, store or non-register binding, all candidate variables in that function retain boxed storage. This preserves destructive float destination identity. Captured and special bindings remain boxed. Safety-3 scopes and the FP safety hook retain the checked service, including operation/operand conditions and recovery. Single arithmetic rounds at every single-precision operation.

The focused test exposed a pre-existing READY layout error: `fp_control` initialized to 0. This change initializes the adopted default 7 (invalid, division by zero, overflow). The old baseline is retained with its original mask; this runtime difference is explicit. The optimized benchmark arithmetic uses unchecked policy, so the mask does not turn its checks off.

Only the two typed float benchmark `$body` expressions change by hash; every other benchmark body is byte-identical to baseline. Their loops now contain `f64.add` / `f32.add`. The remaining `$float_slow` site in each loop belongs to the generic loop-index fallback, not the declared float addition. Eight isolated arithmetic bodies contain their direct instructions and no float-service call.

## Accepted benchmark rerun

Nanoseconds per iteration: median of three fresh-process medians, nine samples per workload/process. The accepted sixteen-workload source and measurement harness are unchanged. Native macOS x86-64 CCL 1.13 and Node 25.6.1 / V8 14.1 run on the same host. Compilation, full qualification and mutation runs finished before this serial timing series. All disposable builds used the verified RAM volumes.

| Workload | Baseline default | New native | New default | Liftoff only | TurboFan only | New default/native |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Inline fixnum loop | 39.75 | 2.27 | 39.67 | 76.92 | 44.49 | 17.5× |
| Scalar call | 99.00 | 2.47 | 98.87 | 253.01 | 114.50 | 40.0× |
| Reference argument | 87.05 | 2.15 | 86.98 | 233.39 | 104.25 | 40.4× |
| Reference live across calls | 98.02 | 2.39 | 97.42 | 254.93 | 110.33 | 40.7× |
| Optional arguments | 205.30 | 5.51 | 203.37 | 403.21 | 207.94 | 36.9× |
| Rest arguments | 364.83 | 42.19 | 364.84 | 773.67 | 392.33 | 8.6× |
| Keyword arguments | 188.04 | 11.51 | 186.76 | 397.88 | 194.28 | 16.2× |
| CAR | 76.35 | 2.69 | 75.01 | 147.51 | 82.73 | 27.9× |
| Typed CAR | 73.30 | 2.36 | 73.22 | 147.38 | 82.46 | 31.0× |
| SVREF | 82.55 | 2.75 | 82.47 | 161.94 | 92.77 | 30.0× |
| Typed SVREF | 82.52 | 2.74 | 82.21 | 162.38 | 92.68 | 30.0× |
| EQ | 80.40 | 1.37 | 79.94 | 163.75 | 94.50 | 58.5× |
| Generic fixnum addition | 59.16 | 2.08 | 59.59 | 113.11 | 67.83 | 28.7× |
| Generic double addition | 1726.44 | 15.93 | 1732.12 | 1865.69 | 1719.79 | 108.7× |
| Typed double addition | 1725.56 | 2.50 | 32.93 | 62.43 | 37.28 | 13.2× |
| Typed single addition | 1716.09 | 2.75 | 33.14 | 62.45 | 36.07 | 12.1× |

All process medians, observed ranges and hand-written engine references are in the [machine-readable record](float-unboxing-results.json). Ranges are not confidence intervals; OS caches and unrelated system activity are uncontrolled. Differences in unchanged workloads are not attributed to float lowering.

## Allocation and READY

| Typed loop | Baseline bytes/iteration | New bytes/iteration |
| --- | ---: | ---: |
| Double | 16.336914 | 0.005508 |
| Single | 8.336182 | 0.005493 |

These are median allocation-marker brackets, excluding copied live bytes and including untimed timer/check/output work. The code itself boxes at the result boundary instead of on every arithmetic iteration.

| Ordinary READY run | Launch to READY (s) | Lisp interval (s) | Collections |
| --- | ---: | ---: | ---: |
| 1 | 26.426 | 23.121 | 4 |
| 2 | 26.141 | 22.787 | 4 |
| 3 | 26.203 | 22.852 | 4 |

Median READY **26.203 s**, versus the accepted 26.164 s baseline. All runs retain 81 loads, seven modules, eleven instances and no leaked file/session state. Core boot/runtime archives are reused unchanged from audit 190. Ordinary READY checks the new layout and excludes the benchmark bundle; the timed benchmark runs separately load that new bundle. No core rebuild or startup optimization is claimed.

## Qualification and failure evidence

- Focused fixture: 83 native-matched raw-bit rows; eight arithmetic operators, rounding, nonfinite values, binding/assignment scopes, captures, specials, evaluation order, mutation through a call, checked FP/type conditions and recovery. NaN payloads are canonicalized; all other float bits compare exactly. Four forced moving collections pass.
- Four single-change mutants are killed: wrong arithmetic, widened single arithmetic, removed checked-FP policy, removed unboxing type validation. The READY layout check passes 22 checks, including the default mask at three heap sizes.
- Full compiler corpus: 26,204 fresh comparisons pass, zero inherited and zero sampled. The corpus is rebuilt with the final compiler.
- Native R6/R6a: 21,843 eligible registered tests pass (75 upstream-disabled); all 164 native FASLs restore. Forty-two compare byte-identically; 122 undergo decoded comparisons with only the existing four compiler-driver changes allowed. Five existing architectures and 17 module profiles retain their snapshots. The pristine U1 baseline suite is reused by its recorded identity, not rerun.
- Reader matrix: 782 comparisons / 46 files / 17 profiles reused by exact shared-source hashes. No shared reader source changed.
- Benchmark: 1,728 timed Lisp samples and 405 hand-written Wasm samples pass; 36 forced moving collections preserve the reference witnesses. The accepted assessor/observer controls remain applicable by unchanged driver hashes.

The original corpus run produced 348 failures in destructive float operations. The conservative escape rule fixes these; the final full corpus passes. The first focused run failed with the old zero FP mask. A later fixture iteration referenced unavailable `%MAKE-DFLOAT`; its original native and target failures are retained before replacement with ordinary arithmetic allocation. Preliminary smoke timings overlapped qualification and are excluded from all performance conclusions.

## Reproduction and evidence

[Fixture, scope and commands](../../../tests/wasm/stage1/float-unboxing/README.md). One pack, `ccl-evidence/2026-09-28-stage1-float-unboxing-r1`, contains raw final measurements, code shapes, newly built bundles, source/tool hashes, focused checks, mutants, complete compressed corpus observations and native comparisons, plus original failures. `inventory.json` authenticates the pack. Existing boot images, runtime archives and pristine native baseline artifacts are referenced by their accepted identities rather than duplicated.

Next: user-supplied independent review of this change. After acceptance, continue declared accessor specialization before reopening the call convention. No reviewer was invoked by the producer.
