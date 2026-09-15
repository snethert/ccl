# Native method registry checkpoint — 14 September 2026

Status: executed diagnostic; reviewed by Claude's fifty-third audit at `22d1a9f1` without defect. Claude's independent reproduction shows the stale dcode follows any removal that empties the method list. No gate credit.

The next registry witness captures the actual native generic-function population
and its installed methods. It also exposes a U1 dispatch defect: removing the
last universally applicable method leaves its direct dcode installed, so the
generic function still calls the removed method. A separate native process,
loading neither observer nor inspector, reproduces that behavior.

This is negative evidence for treating the installed method list as a callee
bound. The expected empty-registry behavior is `NO-APPLICABLE-METHOD`; the
observed call returns the removed method's two values, `10` and `11`. The
packet labels the defect **REPRODUCED_UNFIXED**. No shared CCL source is changed,
and no Wasm or census gate credit is claimed.

## Captured state

A fresh process starts the pinned release bootstrap image in a disposable U1
archive. The inspector copies `%all-gfs%`, retains the actual objects with
session-local identities, and reads the standard GF and method slots through
U1 accessors. It records the subtype predicate and function bits, slot-vector
owner, selected dcode, dispatch-table identity, dispatch argument and precedence,
method-combination identity, and every installed method's owner, function,
qualifiers and specializer identities. Method/class objects are not printed
through `PRINT-OBJECT` to obtain their labels.

| Captured item | Count |
| --- | ---: |
| Native registry entries | 582 |
| Initialized standard generic functions | 581 |
| Uninitialized standard generic function | 1 |
| Installed methods / distinct method functions | 1,514 / 1,514 |
| Distinct selected dcode functions | 8 |
| GFs whose dcode is an installed method function | 3 |
| Referenced function records, including the private probes | 2,111 |

All 581 initialized entries use the standard method-combination object. The
anonymous uninitialized entry has unbound name, methods and method-combination
slots; it remains explicit instead of becoming a falsely empty callable.
Its slots are tested against U1's unbound marker before the normal accessors
could signal `SLOT-UNBOUND`.

These identities belong to this fresh capture. They are **not** joined to the
465 original-build prototypes by names or coincident numeric IDs. An explicit
bridge between registry state and the corresponding execution is still needed.
The original native population can include browser-excluded modules; recording
native evidence creates no Swink implementation obligation.

## Mutation and subtype witnesses

Twelve calls exercise the real `ENSURE-GENERIC-FUNCTION`, `DEFMETHOD` and
`REMOVE-METHOD` paths: an empty GF, a universal method, warmed dispatch, an
integer specialization, replacement, removal, an EQL specialization and miss,
an around method with `CALL-NEXT-METHOD`, and removal of all methods. Eleven
calls have the expected ordinary behavior, including every returned value.
The twelfth is the retained native defect. Eight actual changes invalidate the
preceding checkpoint comparison. Four isolated mutations independently change
the method function, qualifiers, specializers and dcode, with restoration
checked after each mutation.

The snapshot comparison covers those recorded fields at sequential checkpoints.
It is not a concurrent runtime guard. It does not decode cached effective-method
objects, class hierarchy/slot changes, custom method-combination internals or
future method installation. No exhaustive callee list follows from this snapshot.

An ordinary compiled function containing exactly one literal,
`%%ONE-ARG-DCODE`, is also tested and refused by the GF reader. This qualifies
the preceding audit's subtype inference: a dcode literal is a reference, not a
type certificate. The fresh native predicate and function-bit observations
establish the subtype here; the old literal-only objects keep their previous
scope.

## Source explanation and verification

In U1 `level-1/l1-clos-boot.lisp`,
`%remove-standard-method-from-containing-gf` removes the method, updates both
method lists, clears obsolete combined methods and calls `compute-dcode`.
But `compute-dcode` changes dispatch inside a `when methods` form. Once the
list is empty, it leaves the prior dcode intact, whether direct or table-based.
Claude's independent removal of both methods from a two-method GF confirms
that the required disposition covers every empty registry. The direct path
is selected by `dcode-for-universally-applicable-singleton` in `l1-clos.lisp`.
The minimal [inspector-free reproduction](../../../tests/wasm/native-census/dispatch-registry/removal-probe.lisp)
demonstrates this without the registry reader or its temporary mutations.

Two complete native captures reproduce byte-for-byte. The independent process
reproduces the defect. Twenty-three checker controls reject missing/duplicated
registry records, owner/function substitutions, missed live-field changes,
discarded values, hidden negative evidence, subtype promotion and false
original-build or callee-bound claims. The retained verifier runs the native
sessions again and replays six outputs. Kernel and image bytes remain unchanged;
the five inspected upstream sources equal U1. Verification is limited to the
new packet and direct inputs.

Development retention includes the first run's unbound-slot refusal, the second
run's unsuccessful counterexample construction (`#'name` compiled as a function
cell lookup), and the third run that first exposed the empty-method escape.
The corrected counterexample quotes the actual function object. Original
captures, failures, commands and executed fixture sources are retained.

The plan now groups this work with the struct-slot/vector and other registry
bounds. The next join must cover installation/invalidation, effective-method
caches and the execution identity bridge before replacing a widening edge.
Capture registry state and mutation events alongside the call/IR observations
in the same execution, so object identities can join directly. The independent
snapshots here must not be retroactively assigned to vanished build objects.
The port must not inherit the empty-method dispatch behavior as correct Lisp
semantics; this case needs an explicit reviewed disposition before it enters
native-versus-Wasm comparisons. The ledger remains **40 accepted, 8 missing,
0 unreviewed of 48**;
the checkpoint was reviewed without defect in Claude's fifty-third audit.
The subsequent [same-execution witness](registry-flow.md) now joins real method
installations to compiler bodies during a native source reload; it keeps its
new namespace separate from the original build.
