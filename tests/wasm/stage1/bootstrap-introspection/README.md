# Bootstrap numeric and CLOS introspection

Original definitions executed against native CCL rise **470 → 484**, with **439 → 451** non-NIL witnesses. Twenty more 32-bit destructive single-float definitions execute against 64-bit non-destructive counterparts, counted separately. The run passes **17,480 comparisons** at both placements with movement, and **50 keyword-metadata refusals**. Admission remains **2,043 of 2,231** in the fixed cohort.

This is an unintegrated proposal. No shared compiler, runtime or CCL source is changed. It makes no LL15, CLOS dispatch, or complete-image claim.

## Implementation

The derivation starts with the accepted shared backend, without a patch stack. Two target-only source branches are proposed:

- `lfun-keyvect` reads an ordinary function's keyword vector from element 6 of the accepted seven-element arity record. It checks the function shape, pool identity, metadata schema, flags and vector bounds. A function without `&key` returns NIL; an empty `&key` returns an empty vector. Funcallable objects refuse rather than exposing their class-wrapper word as keyword metadata. This addresses audit 158 O-6 for keyword names only; coverage notes, native code vectors and trampoline reflection remain outside this interface.
- `%non-standard-instance-slots` uses the accepted funcallable slots field on this target. Ordinary instances retain their existing path. Unsupported shapes remain errors; malformed function shapes meet the checked boundary. This is storage access, not a generic-function method dispatcher.

There is no new C or JavaScript runtime implementation. The runtime bytes are the accepted shared files.

## Execution

Ten slot-definition getters receive real native `standard-direct-slot-definition` instances. The native CLASS field is explicitly initialized to NIL, rather than treating an unbound slot as an answer. The transport projects the native slot fields into an instance and native-shaped slot vector. Its wrapper and slot backpointer are omitted, and none of these getter witnesses reads them.

A separate class/wrapper fixture starts with an instance of a real native class. It asserts native wrapper/class identity, the class's own-wrapper link, and the instance-slot backpointer before serializing. The target graph preserves these cycles and the observed class name, slot names and value. Generated code keeps the graph through collection and observes it using CCL's accessors. Unobserved metaclass and class fields are NIL in this bounded projection; it does not establish that a complete CLOS image can be serialized or dispatched.

Keyword cases cover no keys, rest only, empty keys, aliased keys, allow-other-keys, closures and evaluation order with collection. Native closures have a trampoline that the target does not have. The closure observer explicitly unwraps it with `closure-function`, as the accepted callable-metadata oracle does. Top-level `lfun-keyvect` comparisons call the native function directly.

The numeric recipes execute three double-float hyperbolic entries against their actual native entries. Twenty 32-bit destructive single-float entries use observers that allocate the destination and call the original body. The 64-bit reference is the real non-destructive entry (ordinary CL arithmetic for the four short-float arithmetic operations). These twenty are reported separately from same-definition native execution. The input domain is finite and non-trapping; transcendental identities are exact and general libm accuracy continues to use the accepted two-ULP corpus. Both inputs and results are compared before and after movement.

Compiling L1-APRIMS must not replace the reference for an earlier selected numeric definition with a later definition of the same name. Its whole-file native compilation therefore preserves pre-existing oracle bindings except `lfun-keyvect`. The earlier `UPGRADED-COMPLEX-PART-TYPE` failure is retained.

## Remaining requested work

`requested-frontier.json` gives the per-file numeric and CLOS definitions, executed modules, missing recipes and dependency blockers. Admission is not callee closure. The requested 175 numeric bodies and roughly 90 CLOS accessors cannot all be enabled by input recipes alone.

Still open: full class/wrapper behavior and generic dispatch; the remaining numeric dependencies; definition-level FFI exclusions; condition-class coverage; owner-backed kernel globals; heap constants; and spread kinds, in that order after the current execution work. Internal bignum scratch allocation is not automatically an excluded foreign subsystem merely because its current implementation uses `%NEW-PTR`.

## Replay

From the source checkout with its sibling evidence store:

```
python3 tests/wasm/stage1/bootstrap-introspection/packet.py verify \
  --packet ../ccl-evidence/2026-09-22-stage1-bootstrap-introspection-r1 \
  --output /tmp/introspection-review
```

The verifier re-derives the proposal, recompiles whole-file environments and the execution corpus, runs both placements and metadata refusals, and compares deterministic artifacts. Native R6/R6a is reused only after checking the exact final proposal bytes: 21,843 tests, 141 of 164 FASLs byte-identical, all 164 restored. Existing-target local reader proofs cover both source branches at all 17 profiles; byte inversion proves the rest of each file unchanged, and decoded native code comparisons cover the final files.
