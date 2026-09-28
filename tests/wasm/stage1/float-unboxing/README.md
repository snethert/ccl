# Declared float arithmetic and register storage

This change lowers NX1's typed single/double `+`, `-`, `*` and `/` operators
to Wasm arithmetic when lexical floating-point safety is off. It follows the
adopted [ARM policy](../../../../doc/WASM/contracts/floating-point.v1.md):
safety 3 and the floating-point exception policy hook keep the checked service.
Lexical policy comes from the actual lambda, binding and `%decls-body` acode.
The ordinary boxed Lisp entry and result convention stays in use.

Uncaptured, non-special variables declared exactly SINGLE-FLOAT or DOUBLE-FLOAT
can occupy `f32`/`f64` locals. Arguments are checked and unboxed at entry;
assignments used for effect avoid result boxing, and Lisp value boundaries box
with the existing checked allocator. Raw float bits survive moving collection
without publication as pointers. Arithmetic stays at the declared precision.

Register promotion is deliberately conservative. If any candidate flows to an
unknown operation, store or non-register binding, the function keeps its float
variables boxed. This preserves CCL's destructive float primitives and their
destination identity. Captured variables retain their shared cells. Typed
arithmetic can still use direct Wasm instructions in these boxed functions.
The generic numeric service, mixed numeric types, float conversions and checked
arithmetic are outside this first optimization.

The focused fixture found that the ordinary READY layout left `fp_control` at
zero. The layout now initializes the adopted default mask to 7 (invalid,
division by zero, overflow). Its original failure is retained. The layout
check asserts the mask at every tested heap size, and the Lisp fixture checks
all three conditions through ordinary target loading and subsequent recovery.

## Verification

`checks.lisp` uses ordinary CCL macros and declarations. Its 83 native-matched
raw-bit rows cover all eight arithmetic operators, signed zero, subnormals,
nonfinite results, precision boundaries, assignment values, binding scopes,
closures, specials, operand order, destructive mutation through a call, and
four forced moving collections. Checked conditions retain operation/operands;
an inner safety-1 scope remains unchecked. Native hardware exceptions are
masked only for the unchecked comparisons. NaN payloads are canonicalized for
comparison; every other float bit is compared exactly. A target-only wrong-declaration
probe verifies the explicit unboxing type refusal; native low-safety behavior
for that invalid declaration is not asserted.

`check.py` compares the observations and requires the eight direct arithmetic
bodies, two checked scopes and one unchecked inner scope. `controls.py` uses
the existing target bundle materializer and launcher to test four independent
mutants: wrong arithmetic, widened single arithmetic, a removed FP check and
a removed unboxing type check. Compilation and native/corpus qualification
must finish before the final benchmark series starts.

Run from the repository root, with both RAM volumes verified as required by
`CLAUDE.md`. Choose new output directories. Restore the accepted inputs using
the benchmark's existing `prepare` command, or reuse their authenticated restore
chain. For example, with `work=/private/tmp/ccl-work/codex/float-review`:

```sh
python3 tests/wasm/stage1/execution-bench/run.py prepare "$work/benchmark"
python3 tests/wasm/stage1/loader-target/build.py "$work/checks" \
  --postimage="$work/benchmark/inputs/ready-inputs/boot-r8" \
  --source=tests/wasm/stage1/float-unboxing/checks.lisp
CCL_DEFAULT_DIRECTORY="$PWD/" "$work/checks/dx86cl64" \
  -I ../ccl-evidence/2026-09-16-stage1-1a-r2/native/baseline.image \
  --no-init --batch --load "$work/checks/benchmark.dx64fsl" \
  --eval '(ccl:quit)' > "$work/native.log" 2>&1
node tests/wasm/stage1/loader-target/boot0.mjs \
  "$work/benchmark/inputs/ready-inputs/boot-r8" \
  "$work/benchmark/inputs/ready-inputs/boot-r8/runtime-binaries" \
  --bundles="$work/benchmark/inputs/bundles" --bundles="$work/checks" \
  --startup-load=/ccl/bin/loader-benchmark.w32fsl --benchmark-events \
  '--layout={"spaceBytes":33554432}' --expect-ready \
  --report="$work/ready.json" > "$work/target.log" 2>&1
python3 tests/wasm/stage1/float-unboxing/check.py \
  "$work/native.log" "$work/ready.json" "$work/checks"
python3 tests/wasm/stage1/float-unboxing/controls.py \
  "$work/checks" "$work/benchmark/inputs" "$work/native.log" \
  "$work/ready.json" "$work/controls"
python3 tests/wasm/stage1/loader-level1/qualify.py corpus "$work/corpus"
python3 tests/wasm/stage1/loader-level1/qualify.py native "$work/native"
python3 tests/wasm/stage1/execution-bench/run.py measure "$work/measure" \
  --inputs="$work/benchmark/inputs" --build="$work/benchmark/build"
```

The final measurement uses the accepted sixteen-workload benchmark unchanged,
with three native processes, three processes per V8 tier and three separate
ordinary READY runs. Core boot/runtime archives remain the authenticated audit
190 artifacts; the new compiler builds the benchmark and focused bundles.
This measures newly compiled float code, not a rebuild or startup speedup of
the core runtime. The full compiler corpus separately rebuilds with the change.

Results and review state are in
[the result record](../../../../doc/WASM/stage1/float-unboxing-results.md).
