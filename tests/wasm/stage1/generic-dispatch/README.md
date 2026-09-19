# S1-LL11-b: empty generic dispatch

This proposal corrects the stale-method behavior identified in Stage 0. Removing
the last method selects the missing-method entry in both direct and encapsulated
paths. Every invocation also checks the live registry, so a later raw store of an
obsolete callable cannot resurrect a removed method. The missing-method entry
signals CCL's `NO-APPLICABLE-METHOD-EXISTS` through the generated condition system,
with the actual generic callable and argument list in its slots. `CONTINUE`
retries after a handler installs a new method.

The implementation is portable Lisp source compiled to Wasm, with a small
backend extension for the new condition. Method add/remove/replacement,
recomputation, EQL-versus-T selection and the envelope all execute in generated
code. The stable callable is a closure over a cons-based owner record. This is the
initial one-argument primary-method subset, **not the complete CLOS MOP**. See
`scope.json` for class, qualifier, encapsulation, concurrency and GC limits.

The independent native oracle creates a real CCL generic function, mutates it with
DEFMETHOD/REMOVE-METHOD and repeats under ADVISE. Both empty native invocations
still return the removed method's values: that defect stays explicit in the
packet. The correct expected condition is separately witnessed through CCL's
NO-APPLICABLE-METHOD protocol, as the adopted inventory requires. Native CCL also
supplies condition class layouts, specificity/replacement, cleanup, resignalling,
arity and CONTINUE results.

Thirty modules execute in Workers below and above 2 GiB: 144 generated invocations,
78 semantic comparisons, 60 installed binaries and eight class-registry refusals.
Nine faults are recompiled and rejected, including a development-found selector
bug that preferred a universal method installed after an EQL method. Eleven
publication controls and twelve artifact-role omissions are refused. The existing
107-module condition corpus supplies another 184 native-derived comparisons
against its original twelve-class registry. Native R6/R6a runs on the exact new
compiler proposal; shared source remains unchanged until review and acceptance.

```sh
python3 tests/wasm/stage1/generic-dispatch/run.py \
  --evidence ../ccl-evidence --output /tmp/generic-dispatch-fresh --qualify
python3 tests/wasm/stage1/generic-dispatch/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-19-stage1-generic-dispatch-r1 \
  --output /tmp/generic-dispatch-replay
```

The owner supplies the thirteen-row condition registry for this service. Legacy
twelve-row registries remain supported by existing code paths but cannot construct
the new condition. Declined errors still terminate at the checked code-15 boundary.
No timing or full generic-function implementation claim is made.
