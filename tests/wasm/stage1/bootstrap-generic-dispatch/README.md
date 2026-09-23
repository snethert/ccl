# Bootstrap generic-function dispatch

This proposal completes the standard dispatch path required by the pinned
bootstrap image, in one unit. The direct original-definition count rises from
549 to 550, with 515 non-NIL witnesses; the new dispatch paths run through
53 protocol callers (212 comparisons). Original CCL functions reached inside
those callers are not added to the direct-execution headline. Admission is not recounted. Nothing is integrated or awarded
LL15 credit before review.

The image census finds 581 initialized generic functions with 1,514 methods,
all using standard method combination, plus one uninitialized prototype.
`census.lisp` repeats that census on the pinned kernel and image during replay.
This is the native requirement inventory; it is not a census of a cross-dumped
Wasm image.

## Implementation

The D1 funcallable object calls an ordinary Lisp closure capturing its GF.
CCL's original `%compute-applicable-methods*`, `sort-methods`,
`compute-method-list`, combined-method functions, keyword checking and
CALL-NEXT-METHOD perform selection and invocation. These definitions compile
in their whole-file environments. ADD-METHOD, REMOVE-METHOD and the failure
protocols use CCL's actual DEFMETHOD bodies, compiled through its own method
front end. Class precedence and EQL-specializer readers are real generic
functions, including an executed override of the latter reader.

`compute-dcode` replaces the dcode after every method-list update, including
removing the final method. It deliberately recomputes applicability per call;
there is no cache or speed claim. The previous EQ/EQL cached-dcode witnesses
remain in the inherited corpus. Two-argument ASSOC continues to call CCL's
ASSEQL and its existing EQL implementation.

The target primitives replace native LAP entries and native code-object
inspection. Logical function bits and keyword vectors reside in a versioned,
traced literal-pool prefix; GF bits reside at CCL's accepted immediate index.
The metadata includes optional-init/supplied-p and next-method-with-arguments
bits. U1's split positional argument lists retain source evaluation order.
Function references now enter the dependency inventory. Slot-vector allocation
uses the existing rooted heap helper. No C or JS dispatch algorithm is added.

CCL source gains Wasm branches for its class table, GF allocation, method
function access, dcode publication and portable error/restart paths. Both
GF allocator definitions use the accepted seven-field function shape. A newly
constructed empty GF has its dcode before its first ADD-METHOD. The collector
and pinned-image scanner trace the native three-field population strongly,
require a zero GC link and an ordinary population type, and refuse the
four-field termination population.

## Execution

The 53 new native cases run below and above 2 GiB, before and after movement:
class/CPL specificity and a diamond, argument precedence order, EQ/EQL and
zero-argument selection, primary/before/after/around combinations, repeated
and changed-argument CALL-NEXT-METHOD, multiple values, optional/rest/keyword
arguments, errors and CONTINUE restart, nonlocal exits and cleanup, GF
construction, method insertion/replacement/removal, direct-method links,
removing the last method, and overriding a generic protocol reader. Methods
collect while executing. Every call checks restoration of the TCR and dynamic
bindings. The full inherited corpus also runs.

The image transport preserves identities, cycles, wrappers and CPLs. It
projects native class and method objects into D1; unused native cache fields
are not imported. The method entries are compiled Lisp, not host callbacks.
The fixture moves all argument graphs and closures; up to 16 KiB of eligible
literal vectors move, while the remaining literals stay pinned. The projection
is not a general image loader or a qualification of arbitrary class creation.

Custom method combinations are outside the bootstrap census and are not
qualified here. Their path remains CCL's `compute-effective-method-function`.
Completing cross-dumped class/method installation and the rest of LL15 is
separate from this dispatch implementation.

## Explicit native differences and checks

* CCL's stale dcode after removing the last method is an already recorded
  defect. The native oracle calls NO-APPLICABLE-METHOD explicitly for that case;
  the target removes the method and reaches the protocol through the GF.
* Native function source-note/noname bits are excluded from the logical
  function-bit observer (`#x1f7fffff`). Argument and method bits are compared.
* The bad-key diagnostic passes its allowable-key vector to `~s` instead of
  eagerly calling FORMAT and passing the resulting string to `~a`. Its error
  class and intended printed diagnostic are unchanged; introspection of
  SIMPLE-CONDITION-FORMAT-ARGUMENTS can observe this payload difference.
* The native FASL decoder now preserves references to an enclosing reserved
  object by enclosing depth. This permits comparing recursive native functions;
  executable bytes and all non-location constants still compare exactly.

The final source passes R6/R6a with 21,843 tests and 164 restored FASLs.
The 40 collector-owner checks and 20 inherited node-structure checks pass.
Population admission has 28 moving/pinned checks; eight focused omissions are
rejected. Function metadata has
explicit malformed-pool, extent, magic and setter refusal cases. Prior runtime
and compiler checks remain in the inherited harness.

Replay from any checkout:

```
python3 tests/wasm/stage1/bootstrap-generic-dispatch/packet.py verify \
  --packet ../ccl-evidence/2026-09-22-stage1-bootstrap-generic-dispatch-r1 \
  --output /tmp/ccl-bootstrap-generic-dispatch-replay
```

Replay recompiles and executes the target corpus and reuses native qualification
only after asserting all final proposed compiler/source hashes. The packet is
a delta over the cached-method packet; it does not duplicate its baseline.
