# Funcallable-instance storage and CCL immediate access

**470 original definitions execute and match native (+3), 439 with non-NIL
witnesses (+3). Admission rises from 1,950 to 2,043 of the same 2,231
definitions (+93).** Files read to completion remain 47/57. This is an
isolated proposal over BOOTSTRAP-HYPERBOLIC-R2, awaiting independent review;
it does not claim LL15 completion or method dispatch.

The user directed “proceed with the generic function work”. This implements
the separate-vector design described in `bootstrap-arch/function-immediates.md`.
Ordinary functions retain their 32-byte, six-field shape. A funcallable
instance uses the seven-field function header (1834) and stores a tagged
seven-element simple vector in the former padding word, offset 28. Its
logical fields are CCL's existing code descriptor, class wrapper, slots,
dispatch table, discriminating code, hash and bits, in that order. Native
machine-code vectors remain unavailable: LFUN-VECTOR and
FUNCTION-TO-FUNCTION-VECTOR still refuse.

## Implementation

Two target arch macros lower NTH-IMMEDIATE and SET-NTH-IMMEDIATE to checked
accesses to this vector. Evaluation is in source order, all operands are
rooted, and function/vector headers and the tagged index are checked before
access. Ordinary six-field functions have no such immediates.

The internal constructor takes an owner-selected callable template and seven
Lisp fields. It clones both into one 64-byte allocation, preserves the code,
capture environment, version, metadata and literal-pool prefix, and writes
the allocation pointer last. Allocation retry precedes reloading the rooted
operands. This is a storage constructor, not MAKE-INSTANCE or a method
selector. The logical code descriptor/discriminating fields do not silently
replace the callable prefix's code ID.

Generated bootstrap entry checks admit either callable shape and validate
the seventh field when present. Metadata identity checks remain in place.
The ten legacy outputs are byte-identical to the preceding packet, including
their text. The collector admits only six- or seven-field function headers,
checks the new field before copying, and traces all seven fields. Stack
callables keep their existing six-field-only contract. The owner inventories
pinned funcallables and traces their vector roots.

The binding installer requires an explicit `immediates` pointer in a
funcallable manifest row and checks its identity and exact vector shape.
It now also admits the already-defined floating-owner profile, through the
existing loader's digest and trusted-bundle checks. The independent body-range
reader receives the profile's function-import permission; its default still
refuses function imports. The installer neither creates generic functions nor
chooses their methods. Owner code still owns materialization and root registration.

The fixture snapshot reader transports both shapes, validates the side vector
as an inventoried object, and relocates it. This remains fixture transport,
not a production image loader.

## Execution and limits

`l1-clos-boot.lisp` is compiled in its file environment. The three new original
executions are `%GENERIC-FUNCTION-NAME`,
`%GENERIC-FUNCTION-METHOD-COMBINATION` and `%GENERIC-FUNCTION-METHOD-CLASS`.
Twenty-one native cases use real native generic functions with distinguishable
values installed in those three slots. The target receives a declared projection
of those slots, not a fabricated native wrapper or a complete CLOS image.
The unchanged getters run at low/high placements before and after movement:
84 comparisons, within **17,156** total comparisons. The two identity-caller
rows are separate fixture witnesses, not original-definition credit.

Additional checks cover all seven fields with only the function rooted,
constructor retry, non-aliasing of the constructor input vector, setter
collection, invocation after movement with metadata validation, and a captured
closure copied into the new shape. There are 42 generated layout checks,
10 installer checks, 12 pinned-owner checks, 10 snapshot checks, the existing
40 owner checks and 20 structure checks. Four changed-site faults are rejected.

The newly closed class-cell operations still need real class/wrapper fixtures.
An old speculative recipe passed NIL where native requires a class cell; it
is explicitly left uncredited. Admission of those functions does not mean
CLOS dependency closure. Class identity, method selection, discriminator
replacement, real image materialization and the READY join remain owed.
The trusted-owner contract still supplies valid object references; this is
not a memory sandbox or a concurrent mutation protocol.

Native R6/R6a passes on the final compiler and arch proposal: 21,843 tests,
142/164 byte-identical FASLs, identical decoded code for the previously approved
source-location changes, and all 164 restored. No CCL source change is added
beyond the preceding proposal; its existing-target reader proof is reused by
exact source hashes. The float/integer algorithms are unchanged dependencies.

## Replay

From any clean checkout containing this fixture, with the sibling evidence store:

```
python3 tests/wasm/stage1/bootstrap-funcallable/packet.py verify \
  --packet ../ccl-evidence/2026-09-22-stage1-bootstrap-funcallable-r1 \
  --output /tmp/ccl-funcallable-review
```

The verifier re-derives the compiler and runtime, recounts all 57 files,
recompiles and executes the native/generated corpus and changed-site controls,
and compares every deterministic artifact. Unchanged native qualification is
reused only after asserting the complete final proposal's source hashes.
