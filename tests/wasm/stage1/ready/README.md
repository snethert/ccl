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
packet's startup. Audit 169 O-44 is repaired by `closure.json`: the roots are
the three startup entries, every function in the selected image and the
funcallable trampoline. It follows named calls, class-mode binding precedence,
projected GF bindings, nested code and the three installed hash leaves. The
operator counts come from these modules' compiler records, not the corpus.

The conservative walk reaches **682 modules / 116 operator kinds / 33,308
occurrences**, with **111 missing edges naming 72 distinct callees**, and
**40 modules with indirect calls**. This is an incomplete closure census, not
an assertion that all those branches execute at startup. Missing paths include
class finalization, error reporting and native locking; a retained standalone
fallback even names `WITH-ONE-NEGATED-BIGNUM-BUFFER` as a callee. Successful
cold boots do not discharge those paths. The report retains every edge and
installed-module digest, and refuses missing compiler records. Controls remove
a required binding and unused corpus code to check those distinctions.

`replacements.json` names all 100 target-file definitions reached by this walk:
55 have direct native LAP antecedents, 16 have a native DEFUN antecedent,
six are explicitly named replacement routes, and 23 still need attribution
as helpers or macro-generated/native primitive entries. The search is a
source-site census across U1, not an active-reader proof. The 25-name cap has
**no PASS claim** until that attribution and the source branches are complete.
Renaming an entry does not exempt it.

`callbacks.json` joins all 35 immutable native registrations, including their
source identity, named effects and prior obligations, to imported symbols in
the selected code graph. None has a direct consumer in the current walk.
Because missing and indirect calls remain, none is silently discharged on that
absence alone. Historical callback selections are unchanged. This keeps the
next implementation work explicit without recreating excluded native services.
No LL15-a/c/d slot credit or broad CCL READY claim is made.

The metadata is read from the retained compiler session's actual module
objects. The three new forms are lowered a second time in that same process
solely to recover their records after the probe driver's destructive list
consumption; their WAT must equal the installed WAT. The corpus is not rebuilt.
Paths for these submitted forms are normalized to the repository source name.

O-47 is repaired by binding the native GF-population and scheduling globals
around each oracle entry. Fixture state carries from initialization to checking,
but the real process globals are restored by PROGV; all three restorations are
asserted and logged. O-46 is repaired by a fresh 31-check admission run recording
both imported module hashes and its driver hash. Historical controls are not
rewritten. O-45 remains the distinction between a harness check and the owner's
actual contract: the owner publishes READY on return, FAILED on throw and
refuses a second bootstrap.

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
