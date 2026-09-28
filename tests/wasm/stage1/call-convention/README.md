# Calling convention subtraction

These tests exercise the ordinary compiled call path. They do not add an entry,
direct call, cache at a call site, or a different multiple-value budget.

`checks.lisp` supplies 69 native-matched observations: fixed arities 0–6 and 16,
arity/designator conditions, replacement function bindings, optional/rest/key
and APPLY calls, static/dynamic multiple values, unwinding and recovery, and
nine forced moving collections with argument, returned, retained, closure and
pool references, including collection during cleanup and 64 retained dynamic
values. The same constant-pool expression is evaluated before and
after collection, comparing against a separately rooted reference.

`boundaries.py` extracts actual generated entries and runtime helpers. Its
only positive-build substitution replaces Lisp error signaling with an observed
checked exception, allowing deterministic stack thresholds without booting the
condition system. It checks public refusal before any memory write, dynamic
resolver state, zero/one/four/five/64 static results with explicit capacities,
the unchanged kind-3 capacity refusal, the overflow reentrancy bit, and a
100,000-step tail chain in 2 KiB. An unconditional-helper control must produce
the identical overflow depth. Removing zero-slot, version or reentrancy-bit
checks must fail a named assertion.
`publication.py` corrupts producer metadata before serialization and requires
a checked compiler refusal.

`controls.py` rejects changed answers, missing rows and missing moving-GC
witnesses. It then loads a bundle whose public entries all trap: every ordinary
compiled call must still complete through internal entries. Two emitted-code
mutants remove argument rooting or retain a pool in an untraced local. Both
must reach actual moving collection and differ from native results. A mere
materialization failure is not a killed mutant.

Run from the repository root after verifying the two RAM mounts required by
`CLAUDE.md`. Use separate directories for compiler outputs and final evidence.
The full boot and runtime rebuild matters: startup measurements using old core
archives do not measure this change. The ABI remains version 1. Phase 2 was measured and rejected; its
context-only delivery contract and adapter changes are not present.

```sh
work=/private/tmp/ccl-work/codex/call-convention-replay
python3 tests/wasm/stage1/loader-target/build.py "$work/boot" --boot0
python3 tests/wasm/stage1/loader-target/build.py "$work/bundles" --level1
python3 tests/wasm/stage1/loader-target/build.py "$work/checks" \
  --postimage="$work/boot" --source=tests/wasm/stage1/call-convention/checks.lisp
CCL_DEFAULT_DIRECTORY="$PWD/" "$work/checks/dx86cl64" \
  -I ../ccl-evidence/2026-09-16-stage1-1a-r2/native/baseline.image \
  --no-init --batch --load "$work/checks/benchmark.dx64fsl" \
  --eval '(ccl:quit)' > "$work/native.log" 2>&1
node tests/wasm/stage1/loader-target/boot0.mjs "$work/boot" "$work/boot/runtime-binaries" \
  --bundles="$work/bundles" --bundles="$work/checks" \
  --startup-load=/ccl/bin/loader-benchmark.w32fsl --benchmark-events \
  '--layout={"spaceBytes":33554432}' --expect-ready --report="$work/focused.json" \
  > "$work/focused.log" 2>&1
python3 tests/wasm/stage1/call-convention/check.py "$work/native.log" "$work/focused.json"
python3 tests/wasm/stage1/call-convention/boundaries.py "$work/checks" "$work/boundaries"
python3 tests/wasm/stage1/call-convention/publication.py "$work/boot" "$work/publication"
mkdir -p "$work/inputs/ready-inputs"
ln -s "$work/boot" "$work/inputs/ready-inputs/boot-r8"
ln -s "$work/bundles" "$work/inputs/bundles"
python3 tests/wasm/stage1/call-convention/controls.py "$work/checks" "$work/inputs" \
  "$work/native.log" "$work/focused.json" "$work/controls"
python3 tests/wasm/stage1/loader-level1/qualify.py corpus "$work/corpus"
python3 tests/wasm/stage1/loader-target/build.py "$work/benchmark" \
  --postimage="$work/boot" --source=tests/wasm/stage1/execution-bench/benchmarks.lisp
# Finish all compilation/qualification before starting measurements.
python3 tests/wasm/stage1/execution-bench/run.py measure "$work/measure" \
  --inputs="$work/inputs" --build="$work/benchmark"
```

The corpus's disposable compiler image is approximately 4 GiB; plan RAM usage
before starting another build. Publication controls use the unchanged loader's
authenticated smoke fixture and the commands in the module-consolidation pack.
Results, invariant producers and the complete TCR reader inventory are recorded
in [the producer record](../../../../doc/WASM/stage1/call-convention-results.md).

The corpus harness and service adapters are unchanged. The Phase 2 failure,
repair and complete measurement artifacts remain in the rejection evidence;
none of those protocol changes is required to reproduce the retained Phase 1.
