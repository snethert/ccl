# Generated B call core

This proposal completes the required-argument call and result-storage core
of LL05. It receives no LL05 gate credit: optional/rest/keyword binding,
APPLY, closure objects, lazy stubs, tail transfers and the full Lisp condition
path remain. Shared source remains the accepted LL07 backend until review.

The real front end and pass 2 generate B entries and callers. Arguments
0–6, 16, 32 and 64 occupy ascending VSP words; results use the caller-owned
region and return `(value0,count)`, with `(NIL,0)` for zero values. Nested
calls, side effects, IF, scalar consumption of zero/many values, PROG1 and
MULTIPLE-VALUE-PROG1 execute against native CCL and an independent logical
model. Physical tests repeat below and above 2 GiB.

Each call reserves its argument and result regions independently. Root
records own argument slots and retained result copies; the TCR result
descriptor owns only the current output slots. An independent inspector
checks unique physical scanners at observable call boundaries. Try-table /
exnref restoration resets VSP, root head and result ownership on exceptions.
There is no collector, allocation, polling or tail transfer. Existing cons
operands can remain in Wasm locals across calls; live-local spill/reload
qualification is still LL06/1D work, not established by these root checks.

Two installation modes run the same modules: direct imports of generated
Wasm exports, and transparent host observation wrappers around those exports.
The wrappers check self and entry/return ownership; the unwrapped mode proves
those observers are not needed for execution. Indirect calls use an actual
Wasm table. Their resolver invokes the unchanged, generated LL07 slot
validator. Opaque fixture handles and owner-supplied registry metadata stand
in for future function objects and authenticated installation. No production
symbol-redefinition or closure-self claim follows from them.

Arity, designator and capacity failures use checked Wasm exception tags;
ordinary cons failures retain the accepted typed tag. These are refusal
boundaries, not the complete Lisp condition machinery promised by LL05-a.
Unused result words and caller arguments are checked for accidental writes.
The 64-argument global call produces a retained U1 metadata warning (claiming
a maximum of 63); explicit IR arity and both native and target execution
still agree. No warning is suppressed.

```sh
python3 tests/wasm/stage1/b-calls/native.py \
  --evidence ../ccl-evidence --work "$NEW_WORK" --output "$NEW_NATIVE"
python3 tests/wasm/stage1/registration/qualify.py \
  --output "$NEW_NATIVE" --inputs ../ccl-evidence/macos-u1-inputs \
  --kernel ../ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 \
  --destination "$NEW_QUALIFICATION"
python3 tests/wasm/stage1/b-calls/run.py \
  --evidence ../ccl-evidence --native "$NEW_NATIVE" \
  --qualification "$NEW_QUALIFICATION" --output "$NEW_OUTPUT"
python3 tests/wasm/stage1/b-calls/verify.py \
  --packet "$PACKET" --evidence ../ccl-evidence
```

The native run reuses the accepted pristine 1A baseline, executes a new
registered build/test and removal build, and qualifies all existing targets.
The verifier recompiles every positive and mutant module and reproduces the
oracles. Original development failures are retained in the packet.
