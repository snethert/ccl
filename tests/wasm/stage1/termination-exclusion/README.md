# Stage 1 termination exclusion

Auxiliary proposal implementing the user's 20 September decision to exclude
`terminate-when-unreachable` in Stage 1. No integration or LL15 slot credit.
The compiler and shared runtime are unchanged. Finalization is owed in Stage 2.

The five replacement entries in `entries.lisp` are compiled by the integrated
compiler in disposable U1. Registration, cancellation, lookup and explicit
queue draining signal an owner-installed SIMPLE-ERROR, with the text
“Finalization is not supported in Stage 1.” The automatic hook returns NIL when
its enable special is NIL; an enabled hook reaches the same explicit refusal.
It does not install callbacks, invoke them or report successful registration.
The unused optional registration callback has NIL as its replacement default:
selecting native's default TERMINATE function is unnecessary before refusal.

`bindings.json` identifies the five native CCL function bindings and the two
owner-provided special values. The runner checks native symbol visibility and
emits `bound-bindings.json` with each compiled module digest. The generated
calling corpus uses private fixture symbols bound to these entries. Installing
these replacements at the real CCL symbols in the selected image is still owed;
this fixture does not claim the entire startup image has been replaced.

`admission.mjs` is a synchronous, read-only image-owner guard. It requires the
explicit exclusion policy, distinct backed state words, NIL population data,
NIL pending callbacks, zero function-registration count, and NIL automatic
scheduling. It rejects instead of erasing nonempty state. The owner must supply
the actual image's data, pending-list, function-table-count and enable slots,
with exclusive access while admission runs. The guard does not authenticate
that mapping, discover every alias or prevent a later writer from changing it.
The image builder must join it to its real roots before READY. Ordinary strong
populations do not stand in for the terminatable alist.

## Evidence

Seventeen modules exercise named, default-argument, FUNCALL, APPLY and
MULTIPLE-VALUE-CALL refusals; operand effects; nested cleanup; a declining
handler; each replacement entry; disabled and enabled automatic hooks; and an
unhandled registration. Thirteen native oracle scenarios run at two placements
(2 MiB and 2 GiB), before and after real collection: 52 comparisons and 26
collections. All TCR words other than the allocation cursor/bounds and returned
value count must restore, including on the unhandled path. The callback never
runs and the user's object stays unchanged. No claim of collection *inside* the
refusal is made; collector/condition composition is reused from prior evidence.

Native CCL compiles the deliberately substituted refusal bodies to supply the
condition and unwind oracle; this is a chosen exclusion, not a claim that native
CCL refuses registration. A separate probe runs native registration, lookup and
cancellation with a strongly reachable object, cleans up with UNWIND-PROTECT,
and verifies no callback ran and the original state was restored. The pinned
image has zero population entries, zero pending callbacks and zero callback
registrations, but automatic termination is enabled there. The port must disable
it explicitly rather than inheriting that flag.

Sixty-four admission checks include each nonempty state independently, exact
empty encodings, malformed extents, aliasing and frozen private admission
records. Seven remove-one-check controls and three recompiled Lisp faults
(successful registration, silent enabled hook, and callback execution) must
fail the named assertions. Mutant Wasm is compared against the unchanged native
oracle, not a native version of the mutation. Prior compiler R6/R6a is reused by
exact hash; no compiler or collector change is proposed.

The same pinned native probe surveys all 97 keys in the populated EQL
specializer table: 94 symbols and integers 1, 2 and 30. This informs the next
service; it does not justify substituting EQ for general EQL. Newly registered
specializers may use boxed numeric keys. EQL/EQUAL services, ordinary population
accessors/scanners, table growth and installation as actual image roots remain
open, along with the full LL15 startup join.

## Replay

```sh
python3 tests/wasm/stage1/termination-exclusion/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-20-stage1-termination-exclusion-r1 \
  --output /tmp/ccl-termination-replay
```

Sources are an explicit sibling inventory; adding a later fixture does not
alter this packet's pin list. Development failures are retained in the packet.
