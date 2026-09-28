# Trusted declared accessors

The Wasm backend consumes NX1's lexical `$decl_trustdecls` policy in lambda,
binding and `%decls-body` scopes. Under that policy, CAR/CDR on a CONS become
direct loads. LIST retains its NIL result branch. SVREF on a SIMPLE-VECTOR
with a fixnum index omits representation/span checks; its unsigned bounds
check remains unless a known vector length and index type prove the access.
Checked policies and checked THE forms keep their checks. Invalid trusted
declarations have no additional runtime validation contract.

A direct read has no safepoint between its operand and its memory load.
SVREF stages operands in locals if the later operand cannot collect. An
immutable, uncaptured lexical vector can instead be read from its existing
root after index evaluation. Its read has no effects, and reloading then
observes relocation. Otherwise, the ordinary operand root frame remains.
Assignments, captures, specials and effectful object expressions therefore
preserve evaluation order and moving-GC safety. Stores and the call ABI are
outside this change.

The checked type emitter also admits `(simple-vector)`, `(simple-vector *)`
and explicit lengths in the target header's 24-bit range. The focused fixture
first exposed the missing fixed-length check at safety 3; its original
compilation refusal is retained. This allows identical declarations to be
tested in trusted and checked scopes.

`checks.lisp` has 71 native-matched rows and eight forced moving collections.
It covers both cons fields, NIL, dynamic/fixed/proven vector bounds, negative
indices, empty vectors, checked vector lengths and representation, nested
policies, assignment/capture/special effects, operand order, multiple values,
and recovery. The non-fixnum index witness is a boxed double. The initial
ratio-literal witness stopped in the unchanged core's `$FASL-RATIO` before
execution; that trace is retained as an unresolved loader limitation, without
claiming ratio-index coverage here.

`check.py` compares every row and requires direct-load and retained-check
code shapes. `controls.py` materializes five single-change mutants: wrong
cons field, wrong NIL result, wrong vector index, off-by-one bounds check,
and an omitted checked length test. Each must finish ordinary LOAD and be
rejected by the native comparison. A loader/validation failure does not kill
a mutant.

## Reproduction

Run from the repository root. Verify both RAM volumes required by `CLAUDE.md`.
Restore the accepted startup inputs with the execution benchmark's `prepare`
command, or reuse its authenticated restore chain. With `inputs` pointing to
that restore and `work=/private/tmp/ccl-work/codex/accessor-review`:

```sh
python3 tests/wasm/stage1/loader-target/build.py "$work/checks" \
  --postimage="$inputs/ready-inputs/boot-r8" \
  --source=tests/wasm/stage1/declared-accessors/checks.lisp
CCL_DEFAULT_DIRECTORY="$PWD/" "$work/checks/dx86cl64" \
  -I ../ccl-evidence/2026-09-16-stage1-1a-r2/native/baseline.image \
  --no-init --batch --load "$work/checks/benchmark.dx64fsl" \
  --eval '(ccl:quit)' > "$work/native.log" 2>&1
node tests/wasm/stage1/loader-target/boot0.mjs \
  "$inputs/ready-inputs/boot-r8" "$inputs/ready-inputs/boot-r8/runtime-binaries" \
  --bundles="$inputs/bundles" --bundles="$work/checks" \
  --startup-load=/ccl/bin/loader-benchmark.w32fsl --benchmark-events \
  '--layout={"spaceBytes":33554432}' --expect-ready \
  --report="$work/ready.json" > "$work/target.log" 2>&1
python3 tests/wasm/stage1/declared-accessors/check.py \
  "$work/native.log" "$work/ready.json" "$work/checks"
python3 tests/wasm/stage1/declared-accessors/controls.py \
  "$work/checks" "$inputs" "$work/native.log" "$work/ready.json" "$work/controls"
python3 tests/wasm/stage1/loader-level1/qualify.py corpus "$work/corpus"
python3 tests/wasm/stage1/loader-level1/qualify.py native "$work/native"
```

Rebuild and check the existing [float](../float-unboxing/README.md) and
[fixnum](../fixnum-loops/README.md) fixtures as dependencies. Their unchanged
native observations may be reused by exact fixture identity. Reader and
benchmark-observer qualifications likewise reuse unchanged sources.

After all qualification finishes, compile the unchanged execution benchmark
using `loader-target/build.py --source=tests/wasm/stage1/execution-bench/benchmarks.lisp`
and run `execution-bench/run.py measure "$work/measure" --inputs="$inputs"
--build="$work/benchmark"`. This retains all sixteen workloads, three native
processes, three per V8 tier, and three ordinary READY controls. Core archives
are unchanged: these timings measure newly compiled workloads, while the
full compiler corpus separately rebuilds with the changed backend.

Results and review state: [producer record](../../../../doc/WASM/stage1/declared-accessors-results.md).
