# Generated runtime result capacity

This auxiliary LL05 proposal removes the fixed 64-value limit. It builds on
reviewed rest/APPLY and leaves the accepted leaf and typed primitive entry
modes unchanged. The shared backend remains at the accepted rest/APPLY unit.

The incoming caller-owned output reservation supplies a resource budget.
Callee scratch space, its published root count, bound-variable offsets and
child output reservations follow that budget. At least four scratch words
permit scalar evaluation even when the final output reservation is empty.
MULTIPLE-VALUE-PROG1 retains the actual count in a runtime-sized root frame;
PROG1 retains only its primary value. All extent checks use i64 before
narrowing or writing. A capacity failure restores the incoming TCR state
and publishes no result. The accepted B entry signature is unchanged.

This is checked capacity, not automatic growth or unlimited storage. A call
can exhaust its supplied result budget even if a later expression would
discard its values. Production adapters still need a reservation policy and,
if desired, a growth/retry protocol that preserves effects. This fixture
makes no such claim. Stack cost scales with the reservation and call depth.

The corpus compares Python, native CCL and generated Wasm through 1,024
returned values, including direct/indirect calls, APPLY, nested retention,
optional/key defaults, aliased heap objects, sequential effects, zero values
and exceptional exits. Tests run with low and above-2-GiB stacks, using both
Wasm direct imports and observation wrappers. Literal capacity checks cover
undersized output, exact scratch/staging space, exhausted stack and i32
extent wraparound. Every result, heap effect, unpublished output tail and
physical root ownership is checked. Compiler mutants are recompiled through
the real front end and rejected by the same oracles.

There are no polls or collections in this unit. APPLY's two list traversals
still require no intervening execution or concurrent mutation. Callable
objects, symbol function cells, full conditions, lazy installation and tail
transfers remain work for LL05. No inventory slot is claimed here.

```sh
python3 tests/wasm/stage1/b-results/native.py \
  --evidence ../ccl-evidence --work "$NEW_WORK" --output "$NEW_NATIVE"
python3 tests/wasm/stage1/registration/qualify.py \
  --output "$NEW_NATIVE" --inputs ../ccl-evidence/macos-u1-inputs \
  --kernel ../ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 \
  --destination "$NEW_QUALIFICATION"
python3 tests/wasm/stage1/b-results/run.py \
  --evidence ../ccl-evidence --native "$NEW_NATIVE" \
  --qualification "$NEW_QUALIFICATION" --output "$NEW_OUTPUT"
python3 tests/wasm/stage1/b-results/verify.py \
  --packet "$PACKET" --evidence ../ccl-evidence
```

R6 reuses the accepted pristine baseline and executes fresh registered and
removed builds. The retained verifier requalifies those reports, recompiles
every positive and mutant module, compares bytes and reruns the oracles.
