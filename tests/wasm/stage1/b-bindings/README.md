# Generated optional and keyword binding

This unit extends the reviewed B call core with `&optional`, `&key`,
explicit keyword aliases, supplied-p variables and `&allow-other-keys`.
It is a reversible proposal in disposable clean U1 copies. It claims no
complete LL05 inventory slot and is not integrated pending external review.

Pass 2 consumes CCL's actual lambda-list IR. Defaults run once, in parameter
order, only for missing arguments; they may read earlier parameters and call
generated functions. Bound values and supplied-p flags live in the callee's
published root frame. Keyword search uses first occurrence, including the
first `:allow-other-keys` pair. Odd lists, unknown keys and argument-count
errors take the existing checked exception boundary. Exceptional defaults
restore the B call core's VSP, roots and multiple-value ownership.

The corpus retains all 34 required-argument core functions and adds 17
binding functions. A separate Python source interpreter and native CCL
agree on 248 cases. Generated Wasm repeats these below and above 2 GiB,
with direct imports and transparent observation wrappers (992 comparisons).
The inspector derives the bound-root population from source lambda lists,
independently of pass 2. Twenty resource checks cover bound-frame space and
the complete dynamic incoming argument extent as well as inherited checks.
Sixteen compiler mutants and nineteen source refusals test the boundaries.

Keyword names in this slice must have ordinary uppercase ASCII spelling;
escaped lowercase and mixed-case names are refused before they can collide
in the import map. Keyword identities are explicit, fixed fixture imports, not native addresses
or production symbol objects. Function designators remain opaque handles.
There is no collection, allocation, polling or production condition system.
`&rest`, `&aux`, APPLY, closures, lazy stubs and tail transfers remain outside
this slice. The source validator refuses unsupported forms before host
macroexpansion can hide them. Root coverage at inspection points does not
qualify moving-GC spill/reload behavior.

```sh
python3 tests/wasm/stage1/b-bindings/native.py \
  --evidence ../ccl-evidence --work "$NEW_WORK" --output "$NEW_NATIVE"
python3 tests/wasm/stage1/registration/qualify.py \
  --output "$NEW_NATIVE" --inputs ../ccl-evidence/macos-u1-inputs \
  --kernel ../ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 \
  --destination "$NEW_QUALIFICATION"
python3 tests/wasm/stage1/b-bindings/run.py \
  --evidence ../ccl-evidence --native "$NEW_NATIVE" \
  --qualification "$NEW_QUALIFICATION" --output "$NEW_OUTPUT"
python3 tests/wasm/stage1/b-bindings/verify.py \
  --packet "$PACKET" --evidence ../ccl-evidence
```

R6 reuses the pinned pristine 1A baseline and performs fresh registered and
removal builds with native tests and R6a qualification. The verifier repeats
qualification, recompiles every positive and mutant compiler, compares bytes,
and re-executes the unchanged oracles. One packet retains new evidence and
original development failures, with references for unchanged baseline files.
