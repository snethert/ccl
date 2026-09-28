# Fixnum locals and scalar arithmetic

The Wasm backend keeps uncaptured, non-special required/local variables in
tagged `i32` locals when CCL's target-aware type information proves a fixnum
type. Every register binding/assignment checks the tag before retaining the
value; these immediates need no GC root across calls. Captured variables and
specials keep their existing shared storage. This does not add a new Lisp ABI.

Declared fixnum operators stage operands locally. General scalar `+`, `-`, `*`,
comparisons and `EQL` also have a fixnum fast path when operands are either
checked fixnums or simple reads that cannot allocate or poll. Both operands are
evaluated once, left to right. General nodes enter the existing rooted fallback
before any collecting call. Boxing a promoted float and checking a TYPED-FORM
can allocate/call Lisp, so neither qualifies as a simple read.

Arithmetic widens to `i64` and tests whether the tagged result fits `i32`;
overflow uses the existing bignum service. CCL's explicit no-overflow operators
keep their existing `i32` semantics. Merely declaring the operands fixnums does
not justify dropping overflow handling. Checked result assertions remain in
the IR and are executed.

The front end leaves ordinary DOTIMES indices untyped. Their increment uses the
general fast path, including its tag and overflow branches; no induction-range
proof or source rewrite is added. IF/PROGN forms used for effect avoid publishing
discarded multiple values. Loop safepoints, accessors and call dispatch are not
redesigned. Static body counts include cold fallbacks and therefore do not count
instructions executed on a normal fixnum iteration.

## Qualification

`checks.lisp` compiles unchanged through the native and target file compilers.
Its 125 observations cover explicit wasm32 integer boundaries, overflow,
signed comparisons, logical operations, negative/zero/positive trip counts,
binding and assignment results, captures/specials, argument order, cleanup and
early exit, generic floats/bignums, type conditions and recovery. Float results
use exact bits because READY's printer cannot yet format floats. Native and
Wasm have different fixnum widths, so overflow comparisons use numeric results,
not the host's object tag. Invalid low-safety declaration refusal is target-only.

Six forced moving collections cover live fixnum operands, aliased references,
and boxed arithmetic operands across a collecting call. `check.py` compares
every row and verifies the emitted arithmetic and retained overflow/fallback
paths. `controls.py` alters one instruction/check per bundle: addition becomes
subtraction, overflow detection is bypassed, signed comparison becomes unsigned,
or the register's type check is removed. Each mutant must be rejected by the
native comparison or an explicit Lisp assertion, rather than merely failing to
load or validate.

The existing 83-row float fixture is rebuilt as a direct dependency. The full
compiler corpus and native R6/R6a run against the final backend. Reader and
benchmark-observer qualifications can be reused by exact unchanged source
identities. The final benchmark series must start after all compilation,
qualification and mutation work finishes.

## Reproduction

Run from the repository root. Verify the two RAM mounts required by CLAUDE.md
and choose fresh output directories. Restore the audit-190 inputs using the
existing execution-bench `prepare` command, or reuse their authenticated restore
chain. With `work=/private/tmp/ccl-work/codex/fixnum-review` and `inputs` pointing
to that restore:

```sh
python3 tests/wasm/stage1/loader-target/build.py "$work/checks" \
  --postimage="$inputs/ready-inputs/boot-r8" \
  --source=tests/wasm/stage1/fixnum-loops/checks.lisp
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
python3 tests/wasm/stage1/fixnum-loops/check.py \
  "$work/native.log" "$work/ready.json" "$work/checks"
python3 tests/wasm/stage1/fixnum-loops/controls.py \
  "$work/checks" "$inputs" "$work/native.log" "$work/ready.json" "$work/controls"
python3 tests/wasm/stage1/loader-level1/qualify.py corpus "$work/corpus"
python3 tests/wasm/stage1/loader-level1/qualify.py native "$work/native"
python3 tests/wasm/stage1/loader-target/build.py "$work/benchmark" \
  --postimage="$inputs/ready-inputs/boot-r8" \
  --source=tests/wasm/stage1/execution-bench/benchmarks.lisp
python3 tests/wasm/stage1/execution-bench/run.py measure "$work/measure" \
  --inputs="$inputs" --build="$work/benchmark"
```

Use the float fixture's existing [commands](../float-unboxing/README.md) with
fresh outputs for its rebuild and comparison. The measured benchmark source
and sixteen workloads remain unchanged. Ordinary READY uses the authenticated
existing core archives; these measurements concern newly compiled workload
bundles, not a rebuilt core or startup optimization.
