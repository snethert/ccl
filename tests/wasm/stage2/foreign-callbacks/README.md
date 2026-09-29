# Typed callback boundary and rooted lifetime

The seventh Stage 2 unit supplies callback-table registration and one-Worker
owner transitions. Execution and independent review are recorded separately in
[the bound results](../../../../doc/WASM/stage2/foreign-callback-results.json).
This is the lower callback boundary: a trusted JavaScript invoker exercises real
Wasm indirect calls and the production collector with synthetic B roots.
**Generated Lisp callback invocation, the Lisp registration API, and containment
of actual Lisp nonlocal exits remain the next unit.** No FMT or LL credit.

## Contract

An optional `callbacks` declaration names signatures and scalar failure results:

```javascript
callbacks: [{name: 'integer', table: 'callbacks',
             params: ['i32'], results: ['i32'], error: [-1]}]
// The matching bounded table declaration names its export:
tables: [{export: 'callbacks', minimum: 1, maximum: 8}]
// Every export alias retains the same parameter contract:
{name: 'call', params: ['i32', 'i32'], results: ['i32'],
 callbacks: [{parameter: 0, type: 'integer'}]}
```

`library.registerCallback(type, owner, root, invoke)` returns an opaque handle.
The declared export's callback parameter accepts only an active handle of that
library and callback type; it substitutes the table index internally. Raw
indices, another library's handle, another callback type and retired handles
refuse before foreign entry. Buffer pointer/length slots and managed allocator
or release exports cannot double as callback slots. Aliases cannot erase the
contract. The embedding is trusted to declare the signature expected by the
foreign function; Wasm still checks the actual indirect call's type.

The invoker has signature `invoke(readRoot, scalarArguments)`. Its root is held
in the collector's external root cells until explicit deregistration or library
retirement. Call `readRoot()` again after any collecting operation; a tagged
word saved in a JavaScript local does not move with the heap. The accessor
refuses outside that invocation. Only the trusted invoker sees it; foreign code
receives scalar values and its own table index. This unit accepts a trusted
root word, not a public Lisp callable; the Lisp-facing layer must validate the
callable and marshal arguments/results in its own generated B frames.

The owner leaves FOREIGN through the existing validated admission path, invokes
the callback in RUNNING state, and validates its checkpoint and live heap before
publishing FOREIGN again. It restores the original foreign token, descriptor and
stable stack/control words while keeping moved roots and new allocation bounds.
The invoker must unwind its B frames on return or exception. All 18 checkpoint
words have directed callback-return refusal cases. An inhibited collection may
be serviced synchronously after callback admission; this is the existing
single-Worker pending flag, not another Worker's pending `gc_gen` request.
Nested foreign calls and draining finalizers during a callback refuse. The
finalizer queue remains available after the outer foreign call returns.

A callback exception or invalid scalar result returns its declared failure
values through foreign frames. The first failure suppresses later callbacks in
that entry and is rethrown on the port tag only after the foreign call has
returned and owner admission succeeds. A subsequent foreign trap is primary
and retires the instance. A callback-side Wasm trap, asynchronous callback or
owner, or failed owner admission is **fatal**: it becomes an `AggregateError`
after foreign frames unwind, retires the library, and must terminate use of the
Worker. It cannot be converted into a catchable Lisp condition. Tests distinguish
this fatal path from ordinary callback exceptions. Fixture exceptions contain
no Lisp heap payload. The future generated invoker must retain collector roots
for any condition or nonlocal-exit payload before deferring a host-safe failure;
a tagged value hidden inside a JavaScript/Wasm exception is not a GC root.

`library.deregisterCallback(handle)` is idempotent. It drops the collector root
and invoker, leaving a typed fallback at the old slot. Each registration grows
a new slot; slots are never reused within an instance. Foreign code retaining
an old index therefore cannot invoke a later callback. This finite-capacity
profile deliberately does not reclaim table slots. Closing or trapping retires
all callbacks after active foreign frames unwind. Registration acquires roots
before publication and releases them on table-growth failure. A host failure
after growth can consume an unused slot; it never publishes a live handle.
Foreign code is trusted with its private table; this is not a sandbox against a
library deliberately replacing its own entries.

The trampoline is a defined Wasm function of the declared type forwarding to a
single trusted import. It has no memory or start function. WebKit 26.0 in the
pinned matrix reports a `call_indirect` signature mismatch when either an
import re-export or a defined forwarding function is supplied as
`table.grow(1, function)`'s fill value. The retained four-way probe isolates that
failure: `grow(1)` followed by `set(index, function)` works in every engine.
The product uses that sequence. Original failures and the probe are retained.

## Validation and scope

The callback suite passes **80 checks in Node, Chromium, Firefox and WebKit**,
with **63 killed semantic mutants**. It covers two memory placements, roots held only by the
registration, moving collection with retired-space poisoning, all scalar types
and multiple results, void results, stale indices, alias/type/library affinity,
capacity and growth rollback, recoverable and fatal errors, suppressed repeated
callbacks, owner-hook capture, inhibited collection and finalizer deferral.
Semantic source mutants must fail their directed case through a changed outcome
or state, rather than just a different refusal message.

Declaration and operation refusals cover each new independent predicate.
The remaining equivalences are explicit:

- A start/export initializer has no parameters under the existing admission
  contract, so the callback-slot i32 requirement already excludes it. The
  additional initializer guard is defense in depth.
- A table export's name is either an admitted string or absent. The hidden-table
  variant independently tests the missing-string callback-table clause and
  the declared-but-absent table export; duplicate export names and invalid
  table indices remain engine validation obligations.
- Callback signature argument/result arrays each have shape and member-type
  refusals. Scalar range/arity checks reuse `argumentsFor` and its scalar-suite
  coverage; callback error arity/type and callback output type are directed.
- Slot indices use the existing unsigned 31-bit integer predicate, additionally
  requiring an actual i32 parameter. Negative, absent and non-i32 parameter
  cases cover the range/type exclusions; the independent overlap sites include
  duplicate slots and both buffer pointer and length positions.
- Callback entry uses `foreignBoundary.leave` itself, including its already
  directed token, publication, live-heap and checkpoint checks. The callback
  return site has separate publication/live-heap cases and all 18 checkpoint
  cases. Private busy/safepoint flags cannot escape their synchronous `finally`
  blocks; the existing owner suite exercises nested safepoints. Nested callbacks
  also have no active foreign frame, independently preventing re-admission.
- Root shape/capacity and table engine resource/type failures retain their
  existing owner/engine validation. The new registration tests cover invalid
  owner/root/invoker, capacity-before-publication and growth rollback.

The existing scalar (**126 checks / 16 mutants**), buffer (**66 / 28**),
combined API/string/finalizer (**148 / 69**), and FOREIGN owner (**53 / 38**)
suites pass in all four engines against the changed sources. The general owner
regression adds **59 checks**. The existing post-READY API witness matches **45 native rows**, with **88
foreign entries / 67 moving collections**, using rebuilt archives from unchanged
sources and the identical native oracle; it does not
claim Lisp callback execution. The ordinary collector/owner regression also
runs. No shared compiler, product Lisp or upstream kernel source changes;
whole-file compilation and cross-load count movement are both zero. The compiler
corpus stays deferred until the complete foreign layer is ready. The finalizer
and string deliveries remain independently pending review.

## Reproduction

Verify the RAM mounts per `CLAUDE.md` and restore the
[pinned browser tools](../browser-tools/README.md). From the repository root:

```sh
python3 -B tests/wasm/stage2/foreign-callbacks/run.py \
  --playwright /private/tmp/ccl-work/codex/stage2-browser-tools/node_modules/playwright-core/index.mjs \
  --browser-config /absolute/path/to/browser-config.json
python3 -B tests/wasm/stage2/foreign-callbacks/owner-regression.py \
  --playwright /private/tmp/ccl-work/codex/stage2-browser-tools/node_modules/playwright-core/index.mjs \
  --browser-config /absolute/path/to/browser-config.json
```

The callback driver compiles only its small foreign fixture and the unchanged
collector. The owner runner stages the existing owner suite and controls;
it does not add another Lisp integration harness. Use the existing
[API/string recipe](../foreign-strings/README.md#reproduction) for the generated
Lisp regression and existing scalar/buffer drivers for their direct regressions.
Exact commands, input hashes, tool versions, results, and minimal original
failures are in `ccl-evidence/2026-09-28-stage2-foreign-callbacks-r1`. Successful
WAT/Wasm are discarded; no compiler image or compiled archive is retained.
