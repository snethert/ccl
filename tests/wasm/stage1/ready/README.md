# Projected-image process READY join

This is the working READY packet, still in progress; it is not yet submitted
for LL15 acceptance. Membership and replacement-census work stay in this unit.

Original-definition execution stays **550 / 515 non-NIL**, reused from the
unchanged compiler qualification. Three new startup entries earn no original
CCL definition credit. This work implements the process transition over the
selected class/condition image; it does not claim the full LL15 slot.

Steve's [six adopted decisions](../../../../doc/WASM/stage1/ready-decision.json)
select a projected native image, class conditions, one Worker without a
scheduler, uncached dispatch and executed-original coverage with a named
replacement cap. The class-image loader was accepted by Steve after audit 168 and is now
imported from the shared runtime. Its bytes equal the reviewed prepared module.
No compiler or CCL source changes are needed for this join.

`startup.lisp` is compiled whole through CCL's file compiler. It publishes the
class globals using the reviewed initializer, builds `%ALL-GFS%` in the native
three-field strong population layout, and disables automatic termination and
periodic scheduling. The population includes the protocol GFs, the EQL
specializer reader and the three additional GFs in the initialization
invalidation alist: all **33 GFs** reachable in this selected graph. This is not
a projection of every one of the 581 native GFs. The latter remains a census,
not an installed-function claim.

The compiled checker resolves all **612 class cells**, checks every selected GF
by identity, collects, constructs a condition using inherited initargs and slot
readers, and handles a class-based error. CCL's native result is
`(612 33 43 41 :CAUGHT)`. The three new entries run as one startup call in a
fresh consumer; the consumer cannot call the graph projector.

The integrated `InitializationOwner` claims the process before image loading.
After the loader checks and installs bytes and roots, the generated startup
runs with its legacy mask registry poisoned. Native values, graph mutations,
root publication, all relevant TCR words and bindings are checked before the
owner publishes process READY. A second bootstrap attempt does not execute.
There is one fresh Worker per placement/movement variant; scheduler startup is
absent. No new C/JS runtime service or readiness state machine is introduced.

Four cold boots cover both placements and collection before startup; startup
itself also collects. Missing image, omitted entry and premature READY fail,
leaving the process owner FAILED. The image admission controls remain in the
accepted class-image packet; they are not relabelled as newly run here.

## Reproduce

Beside the existing evidence store and retained P4 compiler environment:

```sh
python3 tests/wasm/stage1/ready/run.py /private/tmp/ccl-work/claude/ready/replay
```

The driver uses the warm whole-file environment and compiles only these three
forms, appending module, symbol and pool identities. It retains a real native
oracle for them. `worker.mjs` is written source, derived once from the prior
harness; replay does not text-patch it. The unused parent class-image worker is
not executed. Code and service hashes are checked before Worker entry. The
saved native compiler image is tooling, not the target image.

## Coverage and boundary

`coverage.json` separates the inherited 550 original executions from this
packet's startup, and reports the retained emitted-acode census. A count of
emitted operators is not a claim that every branch executed. The pending
qualification still needs a complete named replacement census against the
25-name cap, and a justified join from the selected image dependencies to the
35 native startup callbacks. Closure metadata outside this selected graph also
remains open. Those are recorded as incomplete, not silently waived by the
policy change. No LL15-a/c/d slot credit or broad CCL READY claim is made.

Development failures were a direct GF reference absent from the ordinary
function-only dependency list (use its real symbol cell), an incorrect lexical
placement of the harness globals helper, and an unqualified `MEMQ` symbol in
the compiler package. The graph census also caught the three additional GFs
before the final run. Original failure logs are retained. R6/R6a is reused by
unchanged shared-source identity; no native rebuild is necessary for these
fixture-only entries.


Audit 168 O-41 is exercised by `heap-keys.mjs` in this same READY unit. It
writes a table containing cons keys, shared key/value identity, a self-reference,
a tombstone and a live cache entry; poisons the source heap; loads at both
placements; and calls the accepted hash leaf. The first lookup must rehash,
later lookups must not, and updates and deletion must work. Clearing MOVED and
invalidating the cache makes both live keys miss at both placements. This is
new runtime-boundary evidence, not new original-definition execution credit.
O-42 remains the trusted-owner identity boundary; O-43 keeps the admitted kind
inventory explicit. The test does not claim EQL/EQUAL wrapper installation.
