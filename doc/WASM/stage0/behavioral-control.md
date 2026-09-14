# Behavioral assertion control — 13 September 2026

S0-LL02-b has executed successfully, was reviewed by Claude's thirty-second audit at
`f35d2bfe` without defect, and awaits project acceptance. Packet `STANDING-BEHAVIORAL-CONTROL-R1` is in the
[evidence index](../evidence/index.json). It follows Claude's thirty-first audit
at `08a6d5d2` and the alternating plan.

The [fixture](../../../tests/wasm/stage0/behavioral-control/README.md) supplies the
escaping mutable closure, complete multiple-value inspection and observable
cleanup that LL02 requires. Its Wasm factory returns a table-entry/environment
descriptor. Two factory calls return independent environments; subsequent calls
happen after both factory frames have returned. Wasm instructions read and update
the stored capture. JavaScript holds only the returned handles and observations.

Five actual indirect calls test the first escape, a second mutation through that
handle, an independent closure, a real Wasm exception through two cleanup scopes,
and a further call after the exception. All successful calls return six values:
updated state, previous state, delta, initial state, call count and a final sentinel.
The oracle reads every value, the primary result/count and the published count.
It independently inspects capture contents. Cleanup appends the ordered markers
1/2/3 and separately computes the effect 23; both are asserted. Exceptional exits
preserve the exception payload, publish no values and retain the capture mutation.

| Mutant | Required first refusal |
| --- | --- |
| Omit the fifth returned value | First call, all six values; primary result/count remain correct |
| Read initial state instead of captured mutable state | Second call, primary result/count; first call passes |
| Skip inner cleanup | First call, observable cleanup order |
| Skip inner cleanup only on exception | Fourth call, exceptional cleanup; preceding three calls pass |
| Reverse inner/outer cleanup effects | First call, observable cleanup order |

Every variant uses the same `assertions.mjs` and execution adapter. The mutation
option enters only the WAT generator. All six binaries are valid and execute;
the producer requires an actual AssertionError with its expected first assertion
and case. A build failure, engine trap, unrelated exception or timeout cannot
satisfy a rejection case. Original failing binaries, observations and stacks remain
quarantined. They are never accepted as successful runtime results.

## Scope and verification

This is a new Stage 0 behavioral assertion corpus, with actual hand-built Wasm
execution. It is not a rerun of the larger accepted dynamic-call corpus. Calls
follow B's self/count, explicit arguments and two-result shape, using fixed caller
areas and tagged integers. The descriptor is a minimal code/environment pair;
full CCL function objects, GC, threading, arbitrary growth, generated code and
full bootstrap behavior remain outside this control. Those obligations stay open.

The first producer and fresh retained verification pass: five positive calls and
five rejected mutants. All six WAT files, binaries and observation records are
byte-identical on replay. Six direct source bindings, the document checks and
the new slot's production-gate content/artifact checks pass. The preliminary
normal-case execution and final original refusals are retained. No producer,
verifier or native development execution failed unexpectedly.

Only S0-LL02-b's runner/status fields change in the inventory. Existing accepted
bindings and the pending S0-LL01-b binding remain compatible; prior runtime-payload
verification is reused. The scoped ledger is **31 accepted, 15 missing and two
unreviewed out of 48**. S0-LL01-b has Claude's review and awaits user acceptance;
this new record awaits review and acceptance. No earlier acceptance is changed.

Next census work addresses the user-DEFTYPE alias path highlighted by Claude:
expanding an alias after target translation could expose host FIXNUM/BIGNUM meaning
again. The preceding TYPEP packet explicitly left aliases unqualified; no approved
result is broadened by this control.
