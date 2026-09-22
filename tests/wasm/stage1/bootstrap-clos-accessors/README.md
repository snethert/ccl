# Original CLOS accessor execution

Original definitions executing against native rise **486 → 507**, with **451 →
472** non-NIL witnesses. Admission remains **2,059/2,231**. No compiler, runtime
or CCL source changes; no slot credit or integration is claimed.

The 21 additions in `expected-definitions.json` are unchanged whole-file
`l1-clos-boot.lisp` definitions. Seventy native cases produce 280 new comparisons
at both placements before and after movement: **18,040 total**. Native method,
class and effective-slot objects supply the input fields. `clos-source-proof.json`
binds each definition to its installed whole-file module.

The cases cover method metadata, class alists and relationships, effective-slot
location and first-match lookup, instance self backpointers, method removal,
slot-cache invalidation, generic-function keyword metadata, method-specializer
index selection and the non-dispatch-table hook chain. Observer callers use
NOTINLINE calls to the originals. Mutation callers create real cycles, collect,
mutate through the original functions, collect again and compare identities.
The hook callbacks also collect and record their order and early termination.

Only explicitly selected native slots are transported. Other fields are NIL;
this is accessor execution, not complete class construction, wrapper admission,
method-context invocation or generic method dispatch. The slot-vector backpointer
is real and survives movement; it is represented separately in the JSON snapshot.
A fresh method function is mapped by identity to its same-body target template.

Inputs are serialized before native execution, including mutable native instances.
Two focused controls reject omission of the backpointer and use of post-call
state as input. The full corpus and the 40 collector checks pass. Compiler, arch
and CCL source bytes equal the lexpr proposal, whose R6/R6a result is reused by
hash; there is no repeated native build or whole-worklist recount.

Run from the repository root (output directory must not already exist):

```sh
python3 tests/wasm/stage1/bootstrap-clos-accessors/run.py /tmp/ccl-clos-run
python3 tests/wasm/stage1/bootstrap-clos-accessors/controls.py /tmp/ccl-clos-run
python3 tests/wasm/stage1/bootstrap-clos-accessors/packet.py verify --packet ../ccl-evidence/2026-09-22-stage1-bootstrap-clos-accessors-r1 --output /tmp/ccl-clos-replay
```

The retained packet stores changed artifacts only and references unchanged lexpr
artifacts by hash. `development.json` records the native factory/caller mistakes
and the stale-input mismatch corrected before the passing run.
