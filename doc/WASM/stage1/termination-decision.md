# Stage 1 termination exclusion — 20 September 2026

Status: **user-approved policy; corrected components accepted and integrated**.
This records no result acceptance, integration or LL15 credit.

The user answered “Exclude it in Stage 1 (recommended)” to this question:

> For Stage 1, should terminate-when-unreachable be explicitly excluded, or
> should I implement a finalization replacement before bootstrap can proceed?
> Exclusion would refuse registration rather than silently retain objects;
> finalization would remain owed in Stage 2.

Stage 1 excludes `CCL:TERMINATE-WHEN-UNREACHABLE`. Attempted registration must
be refused explicitly; it must not return success, install a callback, or turn
registration into strong retention. The refusal must preserve the established
Lisp error/unwind behavior at a Lisp entry point, not leak a host exception.
Finalization replacement remains owed in Stage 2.

Image admission must establish that no registered objects, pending termination
callbacks or live termination-function registrations need preservation. Nonempty
state refuses the image; it is not cleared to make admission pass. The empty
termination population observed in the native census is evidence about that
image only. Recheck the port's cross-dumped heap and its actual root graph.

Bootstrap must disable or exclude automatic termination scheduling and bind any
reachable registration entry to the explicit refusal. Cancellation, lookup and
queue draining return exactly one NIL value when the admitted state is empty
and registration is refused. This is the native
not-registered answer, not a claim of successful removal or callback execution.
Other native termination consumers still require an explicit disposition.
Keep these implementation joins open until they execute in the selected image.

Ordinary strong populations remain a separate approved compatibility policy.
The terminatable alist has a pending queue and registered callbacks, so it is
not materialized as an ordinary strong list merely because the observed queue
was empty. Explicit resource disposal is unaffected by this policy; this is
not permission to omit required releases or cleanup during normal control flow.

The user accepted both this corrected exclusion and the strong-table/population
proposal after audit 136: “accept integrate and finish ::15”. The acceptance and
component integration are bound in acceptance-bootstrap-policies.json and
integration-bootstrap-policies.json.

Corrected implementation candidate: [empty-state follow-up](../../../tests/wasm/stage1/termination-exclusion-review/README.md),
STAGE1-TERMINATION-EXCLUSION-REVIEW-R1. Audit 135 found that R1 incorrectly
refused cancellation, lookup and draining, which breaks ordinary stream close.
Five generated entries and a read-only state admission guard execute with native Lisp error/unwind comparisons and real
collection. Cancellation, lookup and explicit draining now return the native
empty-state NIL; registration still signals the exclusion. The disabled automatic hook is
inert. The follow-up compares against untouched native consumers and exercises
real file close with the corrected bindings. Native registration/cancellation is
observed separately and restored, without finalizing an object. Actual image
slot discovery, digest-bound installation at the CCL symbols and the bootstrap
READY join remain required. The reviewed components are integrated; production image joins remain open.

Audit 136, imported as e153515d, finds no defect and closes audit-135 F1.
The retained replay and three additional compiled faults support the declared
scope. Both this corrected exclusion and the strong-table/ordinary-population
substitute are now accepted, with reviewed components integrated. Production image
installation and the READY join remain open; review is not bootstrap closure.
