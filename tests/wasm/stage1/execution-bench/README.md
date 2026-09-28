# Execution cost benchmarks

This fixture measures the accepted backend through ordinary target loading after
real startup. It changes no compiler, calling convention, Lisp runtime or safety
policy. The native reference is macOS x86-64 CCL. The target uses the restored
audit-190 split archives and a newly compiled benchmark bundle.

`benchmarks.lisp` supplies the same workload definitions to both compilers:

| Workloads | Contrast |
| --- | --- |
| `eb-loop`, `eb-call` | Inline fixnum addition versus an explicitly non-inlined function call |
| `eb-reference-call`, `eb-live-reference` | Reference arguments and a reference retained across scalar calls |
| Optional, rest and keyword loops | Other calling shapes; rest includes allocation |
| `eb-car`, `eb-car-typed` | Undeclared versus declared cons/fixnum access |
| `eb-svref`, `eb-svref-typed` | Undeclared versus declared vector/index/value access |
| `eb-eq` | Identity comparison with runtime operands |
| Generic fixnum, generic double, typed double, typed single | Numeric specialization, service calls and boxing |

The runner compiles the original source through CCL's front end. Optimization
policy and NOTINLINE proclamations execute only at compile time: the current
runtime image does not contain `%PROCLAIM-OPTIMIZE`. All workloads use speed 3,
safety 1 and debug 0. Typed declarations do not imply that the Wasm backend
unboxes the operation; inspect its emitted code.

Each loop receives runtime arguments, consumes its result, and checks an
independent expected answer. Qualification includes zero and small iteration
counts. Calibrated iteration counts are multiples of four, capped at 4,194,304
to keep sums inside wasm32 fixnum bounds and floating additions exact. Calibration
aims for 50 ms; fast native loops can hit the iteration cap first. Each workload
then warms for at least 250 ms. Nine sample rounds rotate workload order. Timers
surround the Lisp loop call, excluding output and result checking. Timing includes
any natural collection. Native and Wasm timers report their actual resolution.

Three fresh processes per configuration are the default. The series rotates
native/default/Liftoff/TurboFan process order, runs serially, and records every
sample. The summary uses medians within each process, then the median across
processes. Min/max are observed ranges, not confidence intervals. The default
engine uses adaptive tiering; warm-up is not proof that every function tiered up.
The two forced configurations explicitly select Liftoff-only or TurboFan-only.
These engine flags are diagnostic configurations, not product defaults.

`reference.wat` contains separately labeled hand-written i32, f32, f64, vector
load and indirect-call loops. They have no Lisp ABI, GC, boxing or general error
semantics. They provide engine reference timings for the exact bounded inputs;
they are not an implemented compiler fast path. The optimizer may inline calls
or hoist loads. Their host batch dispatch and timer cost are included.

## Collection and code evidence

Before timings, a compiled caller holds a cons and a vector with two aliases
across four collecting calls. Each return verifies identity and both cons fields.
Native uses `gc`; Wasm emits an `EB-GC` output marker. The optional host observer
collects after the output service returns, temporarily rooting and reloading its
returned string. Every target collection must increment the real owner counter
and change semispace. This is a correctness witness, not a comparison of GC speed.

The optional observer also records collection counts and allocation-pointer
advances between BEGIN/END output markers, excluding copied live bytes. These
brackets include untimed timer/check/format bookkeeping. They are broader than
the timed interval and must not be called exact loop allocation counts. Ordinary
READY has this observer disabled. No per-call observer runs during timings.

`code_shapes.py` binds function names from compiler pools to their actual WAT.
It retains complete WAT and reports static instructions in `$body`, including
prologues, epilogues and untaken branches, excluding helper bodies. Counts are
neither dynamic instruction counts nor engine machine instruction counts.
Native disassemblies establish the non-inlined calls and numeric instructions.

The paired workloads expose incremental costs, but their differences do not
partition READY into additive percentages. In particular, retained-root cases
include their own final field read, and vector access includes index calculation.
Eliminating a check or root protocol needs a separately qualified compiler change
and another run of this set. No malformed-pointer refusal is withdrawn here.

## Reproduction

Both CCL RAM volumes must appear under a `ram://` image in `hdiutil info`.
The runner refuses outputs outside `/private/tmp/ccl-work` and records that
verification. Do not run compilation or qualification jobs during measurement.

```sh
python3 tests/wasm/stage1/execution-bench/run.py prepare /private/tmp/ccl-work/codex/execution-bench
python3 tests/wasm/stage1/execution-bench/run.py measure /private/tmp/ccl-work/codex/execution-bench/measure \
  --inputs=/private/tmp/ccl-work/codex/execution-bench/inputs \
  --build=/private/tmp/ccl-work/codex/execution-bench/build
python3 tests/wasm/stage1/execution-bench/controls.py /private/tmp/ccl-work/codex/execution-bench/measure/default-1.ready.json
node tests/wasm/stage1/execution-bench/observe-check.mjs
```

`prepare` authenticates retained prerequisite artifacts using the existing
restore scripts; it does not rebuild unchanged core archives. The loader's new
`--source=FILE --postimage=BOOT` fixture input compiles and materializes an ordinary
file without cross-loading it into the image. It also emits the native FASL and
function-name map. `measure` checks source and parent identities before use.

The default series ends with three separate ordinary READY runs at 32 MiB
semispaces, with 81 completed loads, seven product modules and eleven instances.
Benchmark runs load one additional file; their end-to-end times are not READY
startup measurements. OS file caches and other system activity are uncontrolled.

`--replicas=1 --tiers=default --ready-runs=0` is a smoke run, not the final series.
Results and retained development failures are documented in
[the result record](../../../../doc/WASM/stage1/execution-bench-results.md).
