# Execution cost benchmark baseline

**Accepted as the baseline record, 28 September 2026**, after the
[user-supplied Claude review](execution-bench-review.md) found no defect.
Producer and independent verification are complete; acceptance reuses that
evidence without rerunning unchanged tests. No compiler, runtime,
calling-convention or acceptance-policy change. **Product Lisp lines changed: 0.**

The accepted backend and split-archive startup remain at audit 190 (`824f060d`). The fixture compiles ordinary source through CCL and target-loads it after the real runtime. Native reference: macOS x86-64 CCL 1.13. Engine: Node 25.6.1 / V8 14.1 on the same Xeon W-2140B host. All compilation and disposable artifacts used the verified RAM volumes.

## Measured loop costs

Nanoseconds per iteration, median of three fresh-process medians (nine samples per workload in each process). Each call row includes its loop and callee body. These are workload costs, not isolated call latencies.

| Workload | Native | Default V8 | Liftoff only | TurboFan only | Default/native |
| --- | ---: | ---: | ---: | ---: | ---: |
| Inline fixnum loop | 2.27 | 39.75 | 77.65 | 44.23 | 17.5× |
| Scalar-call loop | 2.51 | 99.00 | 255.68 | 113.74 | 39.4× |
| Reference argument | 2.15 | 87.05 | 236.52 | 103.73 | 40.5× |
| Reference live across calls | 2.42 | 98.02 | 254.71 | 110.61 | 40.5× |
| Optional arguments | 5.15 | 205.30 | 409.36 | 207.38 | 39.9× |
| Rest arguments | 42.03 | 364.83 | 773.76 | 393.29 | 8.7× |
| Keyword arguments | 10.85 | 188.04 | 403.47 | 194.57 | 17.3× |
| CAR | 2.73 | 76.35 | 148.79 | 82.62 | 28.0× |
| Typed CAR | 2.39 | 73.30 | 148.03 | 82.14 | 30.7× |
| SVREF | 3.01 | 82.55 | 162.94 | 92.87 | 27.4× |
| Typed SVREF | 3.00 | 82.52 | 162.52 | 92.43 | 27.5× |
| EQ | 2.25 | 80.40 | 163.94 | 94.13 | 35.7× |
| Generic fixnum addition | 2.12 | 59.16 | 113.59 | 67.78 | 27.9× |
| Generic double addition | 16.62 | 1726.44 | 1865.05 | 1726.72 | 103.9× |
| Typed double addition | 2.54 | 1725.56 | 1858.89 | 1735.41 | 680.1× |
| Typed single addition | 2.75 | 1716.09 | 1842.16 | 1716.58 | 622.9× |

Raw samples and all process ranges are in the [machine-readable result](execution-bench-results.json) and retained evidence. Ranges are descriptive, not confidence intervals. No timing job overlapped compilation or qualification. OS caches and unrelated system activity were uncontrolled.

## What these measurements establish

- The typed and untyped CAR, SVREF and double-add `$body` expressions are byte-identical in the emitted WAT. Those declarations currently produce no body specialization in this fixture. Native disassembly separately confirms real non-inlined calls and typed floating instructions.
- Typed double and single loops contain no `f64.add`/`f32.add`; they call `$float_slow`. The actual READY binding is the JavaScript `floatService`, with private service memory. A separately available direct Wasm scalar service was not selected by this baseline.
- Changing engine tier affects call and access loops substantially, but does not remove their compiler protocol. The optimized-tier float loop still pays for the boxed service.
- The default adaptive engine can outperform forced TurboFan on some cases. The forced configuration is a separate compilation experiment, not a universal optimum; the hand-written indirect-call reference also differs sharply between those modes.

The paired scalar-call minus inline-loop contrasts are:

| Mode | Median incremental workload cost (ns/iteration) |
| --- | ---: |
| default | 59.37 |
| liftoff | 177.67 |
| native | 0.25 |
| turbofan | 69.49 |

These are medians of within-round differences, then process medians. They include consequences of the different emitted loops and callee; they do not isolate resolver, frame checks and rooting into additive percentages. Likewise, the retained-reference row adds a final field read. Separate compiler changes and reruns are needed for causal attribution to individual checks or root stores.

## Hand-written engine references

These exact bounded arithmetic/load loops have no Lisp ABI, collector, boxing or general error paths. They are not compiler-generated optimized Lisp. Host batch dispatch and timer overhead are included, and the engine may inline calls or hoist loads.

| Reference | Default V8 (ns) | Liftoff only (ns) | TurboFan only (ns) |
| --- | ---: | ---: | ---: |
| i32 | 0.292 | 1.558 | 0.295 |
| call | 0.373 | 7.435 | 2.372 |
| svref | 0.490 | 1.828 | 0.495 |
| f64 | 0.994 | 2.311 | 1.005 |
| f32 | 0.998 | 2.255 | 0.999 |

The gap to these references is diagnostic headroom, not a measured speedup from a proposed compiler change.

## Review disposition and next work

Claude verified all 198 evidence files against the inventory, reproduced the
numbers from raw samples, and confirmed the native and target code shapes,
controls, moving-collection witnesses and ordinary READY runs. The disclosed
post-measurement inspector change produces the same report. The review's two
observations are non-blocking; no producer follow-up is required for acceptance.

The review recommends unboxed numerics under declarations first, declared CAR
and SVREF specialization second, and the call convention third. Each substantive
change should rerun this set. These are priorities for subsequent compiler work;
the measurement limits above still apply to causal attribution and projected
speedups.

## Correctness, allocation and READY

All 1,728 timed Lisp samples and 405 hand-written Wasm samples pass their expected-result checks. The nine target processes complete **36 forced moving collections**, preserving a cons, a vector, two aliases and both cons fields across compiled calls. Every forced collection increments the owner counter and switches semispace. Native runs execute the corresponding four `gc` calls per process.

Six assessor controls reject wrong answers, missing/duplicate samples, missing completion, missing collection witnesses and zero-duration samples. Observer controls check fragmented output, allocation accounting across copying, collection counts and missing-collection/orphan-end refusals.

Allocation observations bracket BEGIN/END output markers and exclude copied live bytes. They include untimed timer/check/format bookkeeping, so they are not exact loop-only allocation counts. Natural collections remain included in timed workloads; all raw counts are retained. No per-call trace runs during timing.

| Ordinary READY run | Launch to READY (s) | Lisp interval (s) | Collections |
| --- | ---: | ---: | ---: |
| 1 | 26.164 | 22.816 | 4 |
| 2 | 26.025 | 22.710 | 4 |
| 3 | 26.391 | 23.094 | 4 |

Median READY: **26.164 s**. Each fresh run completes 81 loads, seven product modules and eleven instances, with no open files or abandoned sessions. These runs disable the benchmark observer and exclude the additional benchmark bundle. There is no before/after compiler change in this deliverable, so this is a baseline, not a startup-speedup claim.

## Reproduction and evidence

[Fixture and commands](../../../tests/wasm/stage1/execution-bench/README.md). One retained pack: `ccl-evidence/2026-09-28-stage1-execution-bench-r1` beside the checkout. `inventory.json` authenticates raw measurements, exact benchmark FASLs/bundle/records, emitted WAT, native disassemblies, source/tool identities, controls and development failures. Accepted core prerequisites are referenced through their authenticated restore chain rather than duplicated.

The evidence pack is committed at `d75fedc81d7b7eda28b97ed8b34c31f9c3a25c0a`
in `ccl-evidence`; inventory SHA-256:
`b328b2bae15d95b666aa699f7ad42799f8de7c142ee90fef8e879ad3dbc9631d`.
Its original producer reports retain their historical pending-review state;
this result record and the linked review record the subsequent acceptance.

Development evidence retains the unsupported rational metadata literal, two fixture reader errors, native disassembler package lookup failure, a Python filename collision, and the traced load-time `%PROCLAIM-OPTIMIZE` absence. The final fixture uses integer expectations and compile-time-only policy proclamations; it does not add an in-image compiler or alter runtime refusals. A passing smoke run preceded the final series.

Existing R6/R6a qualification remains applicable to unchanged product sources. Only benchmark/tooling code changed; no milestone or compatibility obligation is marked accepted.

After measurement, the code inspector's assertions requiring the existing
resolver and float-service calls were removed so future fast paths can be
measured without rejection. Reinspection produces the identical code-shape
report. The measured and final inspector versions are separately pinned in
the evidence pack; no execution or timing code changed.
