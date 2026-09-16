# Direct continuations for compiled B calls

This auxiliary compiler proposal removes the second argument-vector copy and
public wrapper from ordinary compiled-to-compiled calls. The public B signature,
function objects, code registry and internal three-argument entry are unchanged.
The public wrapper remains at host boundaries and still protects host-owned
argument storage.

For an ordinary call, the caller reserves its result area first, followed by
one continuation and the padded arguments. It initializes that continuation's
root record, evaluates the designator and arguments once in their existing
order, and writes each argument directly into its final slot. Nested argument
calls grow above the reservation. After resolution, the caller sets the callee's
output descriptor and enters the internal body through the checked table.
The caller's Wasm locals retain its restoration state. Normal return copies
results into the caller's scratch and restores its TCR fields; exceptional
propagation restores each surviving function at its existing body handler.
No dynamic Lisp handler/binding/cleanup extent is introduced by this unit.

APPLY keeps its evaluated prefix and list rooted while it validates the list
and determines the count. It then copies that prefix once and spreads the list
directly into the final continuation. There is no later whole-vector copy.
The evaluation roots are retired only after the final slots are filled. A
non-tail literal APPLY's temporary callable remains below its continuation;
subsequent tail transfers retain the previously qualified relocation path.

Tail calls still reuse their current continuation. A tail callee can grow its
argument area above the ordinary caller's original reservation, subject to the
stack bound; the caller discards that entire area on return. The output
reservation remains below the context throughout.

For N arguments and scratch size S, the ordinary child-call reservation changes
from `64 + 2*align16(4*N) + result_bytes + S` to
`48 + align16(4*N) + result_bytes + S`. This removes one argument root frame
and one Wasm wrapper activation per ordinary compiled call. Required capture
cells, private assigned bindings, scratch/results and APPLY prefix staging keep
their semantic storage. These are layout facts, not timing measurements.

The expanded 276-module corpus compares native CCL, the logical model and target
results. Every public table entry is replaced by a rejecting guard: the whole
corpus must pass without calling one. Internal-entry observations check the
argument pointer, count, SELF root, parent root link and result ownership.
The 100,000-step tail chains, escaped closures, long arities and results, memory
placements above 2 GiB and mutation cases remain. Compiler mutants exercise
internal dispatch, argument placement, results, roots and the inherited tail
and public-boundary mechanisms. The unchanged lazy-loader proposal is replayed
against the new generated binaries separately; no lazy-loader integration is
claimed here.

One exploratory mutant restoring an empty MV reservation between calls was not
observed before the next entry repaired the descriptor. Its original build and
passing log are retained and it is not counted as a rejected control. Actual
post-call safepoint inspection remains part of collector/poll qualification.
The correct restoration stores remain present. No collection runs in this unit.

```sh
python3 tests/wasm/stage1/b-direct-context/native.py --evidence ../ccl-evidence --work /tmp/direct-native-work --output /tmp/direct-native
python3 tests/wasm/stage1/registration/qualify.py --output /tmp/direct-native --inputs ../ccl-evidence/macos-u1-inputs --kernel ../ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 --destination /tmp/direct-qualified
python3 tests/wasm/stage1/b-direct-context/run.py --evidence ../ccl-evidence --native /tmp/direct-native --qualification /tmp/direct-qualified --output /tmp/direct-run
python3 tests/wasm/stage1/b-direct-context/verify.py --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-16-stage1-b-direct-context-r1
```

The backend is applied only in disposable pristine U1 copies with fresh
registered tests and R6/R6a restoration; the accepted pristine baseline is
reused. Claude review and user acceptance precede shared-source integration.
No complete LL05 slot, production Lisp conditions or collection is claimed.
