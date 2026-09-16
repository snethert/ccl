# Generated cons representation (S1-LL04-a)

The proposed backend adds CAR/CDR and RPLACA/RPLACD to 1A's source grammar
and lowers their real CCL acode. Nested operands get distinct i32 locals;
arguments evaluate left to right, once, before the type check. NIL reads
return NIL and NIL mutation refuses. Invalid types throw the imported Wasm
`type_error` tag with `(datum:i32, expected_kind:i32)`, where 1 is LIST and
2 is CONS. This is the typed exception boundary, **not** the Lisp condition
system, which remains 1C. The arity guard is still the initial fatal invariant.
No allocation, calls, polls, collector or cross-dumped heap is claimed.

The corpus has 19 functions and 153 native comparisons: 115 normal returns
and 38 type errors. Logical Python pairs are ordered `(car, cdr)`; independently
compiled native CCL supplies return identities, condition data/types and the
whole resulting graph. The target oracle instead seeds raw CDR-first words,
using literal offsets and unequal values. It covers dotted, proper, nested,
shared and cyclic graphs, nested mutation/evaluation order, fixnum extrema,
NIL reads and refused writes. Effects in a value operand precede a later
invalid-pair refusal, and failed operations publish no result descriptor.

All cases run at four real memory placements: low, straddling 2 GiB, above
2 GiB and at the end of a 32,769-page memory. Another 128 target-only probes
exercise all eight fulltags against four operations. These forged words are
not native Lisp comparisons. Fresh instances must write no memory. Every low
memory byte and graph guard byte is compared; high runs do not scan untouched
bytes throughout 2 GiB. JS address arithmetic uses exact numbers, not signed
bitwise operations. The loader installs the emitted bytes from `installed/`.

Fifteen single-site compiler mutants are recompiled through the real front
end. The same oracle rejects one-sided field swaps, NIL/typing errors,
aliasing temporaries, operand reordering, omitted stores, wrong return/count,
early publication on an exception and high-bit loss. They are compiler
mutations, not edited expected values or hand-built replacement modules.

`native.py` runs the complete proposed unit in pristine U1 with the backend
loaded before rebuilding. It reuses the accepted 1A baseline, repeats the
registered native suite and removal build, and the unchanged 1A qualifier
checks all 164 FASLs and R6a tables. No main-tree compiler change is made.

```sh
python3 tests/wasm/stage1/representation/native.py \
  --evidence ../ccl-evidence --work "$NEW_WORK" --output "$NEW_NATIVE"
python3 tests/wasm/stage1/registration/qualify.py \
  --output "$NEW_NATIVE" --inputs ../ccl-evidence/macos-u1-inputs \
  --kernel ../ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 \
  --destination "$NEW_QUALIFICATION"
python3 tests/wasm/stage1/representation/run.py \
  --evidence ../ccl-evidence --native "$NEW_NATIVE" \
  --qualification "$NEW_QUALIFICATION" --output "$NEW_OUTPUT"
python3 tests/wasm/stage1/representation/verify.py \
  --packet "$PACKET" --evidence ../ccl-evidence
```

The pack stores mutant details in one archive and references unchanged native
baseline artifacts. The verifier reconstructs that layout, replays native
qualification, recompiles the corpus and all mutant compilers, compares the
binaries and executes the same physical oracles. The build binds the accepted
B decision directly. The proposed backend remains under this directory until
Claude reviews it and the user accepts it.

Stores are classified explicitly: CAR/CDR writes are tagged heap-field
stores; the caller result region is a tagged stack-root store; mv_count is raw
metadata. Collector/barrier treatment remains mandatory as those paths enter
1D and Stage 2. A copying/forwarding or image-loading implementation is not
inferred from these layout tests.
