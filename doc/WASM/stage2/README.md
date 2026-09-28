# Stage 2 — runtime correctness

Stage 2 began on 28 September 2026 at the user's direction. Stage 1 remains
[closed at its retained scopes](../stage1/exit-criteria-review.md). The first
work is the foreign-function lower layer and weak hash tables; the continuing
stage contract is [outline §08](../outline.md#stage-2-runtime-correctness).

## First delivery: scalar foreign-module boundary

[Implementation and reproduction](../../../tests/wasm/stage2/foreign-scalar/README.md).
`runtime/wasm32/foreign-module.mjs` admits a digest-bound module, verifies the
binary's scalar signatures and declared resources, instantiates its private
memory, and calls declared exports through an embedding-owned FOREIGN bracket.
Start functions and explicit initializers use that bracket too. A foreign trap
retires the instance; a recoverable exception keeps it available. Both leave
through admission before becoming an exception on the caller's `(i32)` tag.
Initializer aliases cannot bypass one-time initialization.

The [bound result](foreign-scalar-results.json) records **124 checks in each of
Node, Chromium, Firefox and WebKit**, plus **14 killed source mutants**. The
compact evidence pack is `ccl-evidence/2026-09-28-stage2-foreign-scalar-r1`.

This lower-layer unit is **accepted after user-supplied [Claude audit 194](../stage0/claude-review.md)** (`949ae5d8`, imported as `8d2aee38`).
It grants no FMT or LL acceptance. The owner hooks are checked by the fixture,
not yet connected to the production TCR/collector or generated Lisp. The Wasm
cleanup witness is hand-written. Node and browser Workers execute the same
implementation; namespace-provider loading is still owed. No shared compiler,
product Lisp or upstream kernel source changes are part of this unit.

The compiler corpus is deferred by user direction until the whole foreign-function
layer is complete, then replayed once. Focused verification continues for each
changed unit.

## Second delivery: single-Worker roots across FOREIGN

[Implementation and reproduction](../../../tests/wasm/stage2/foreign-runtime/README.md).
`CollectorOwner.foreignBoundary` retains the generated B argument-root chain,
publishes the TCR's FOREIGN state and descriptor, checks stable checkpoints on
return, and preserves collector-updated roots and allocation bounds. Its
`collectForeign()` capability permits synchronous collection on the owning
Worker while foreign code is active. This extends the admitted one-Worker
collector; it is not multi-Worker D5 admission or a Lisp callback.

The owner suite passes **33 checks in Node and Chromium/Firefox/WebKit**, with
**19 semantic source mutants killed**. After READY, the ordinary compiled
`%FASLOAD` loads the Lisp fixture. Its **12 native-matched observations** include
**20 foreign entries and 13 moving collections**, with retired-space poisoning,
lexical/closure roots, bindings, multiple values, one-time Lisp cleanup and
trap retirement. A fixture host-service transport converts the private failure
tag to ordinary Lisp ERROR; the final Lisp foreign API remains owed.

The scalar regression now passes **126 checks per engine and 16 killed
mutants**, including O-159/O-160. O-162's fatal asynchronous-owner rule is
explicit, and O-164's refusal row names are stable. The result binding is
[foreign-runtime-results.json](foreign-runtime-results.json). **Executed;
independent review pending. No FMT or LL credit.**

The first direct public `%WASM-FIND-SYMBOL` probe after READY signalled checked 4
before the fixture; it is retained and unresolved. The qualified path uses the
existing `%FASLOAD` directly, not the COMMON-LISP:LOAD frontend.

## Next foreign work

[HOSTFM P2](../host-and-foreign-modules.md#6-foreign-wasm-modules-cap-ffi-wasm)
remains the architecture; FMT-1–FMT-9 remain its proof obligations.

| Obligation | Current position / next implementation |
| --- | --- |
| FMT-1, scalar calls | Four scalar types, multiple results, signed zero and numeric boundaries execute in the owner unit. A generated fixnum call now executes through the owner; full generated scalar coverage and both Lisp-memory placements remain. |
| FMT-2, bytes and encoding | Add explicit copy ranges and declared encodings, with views reacquired after memory growth. No Lisp memory or addresses may enter the foreign module. |
| FMT-3, moving collection | One-Worker owner roots and reloads execute with collection in an active foreign import and retired-space poisoning. Copied Lisp source ranges, Lisp callbacks and other-Worker collection remain. |
| FMT-4, failures and releases | Generated Lisp conditions/cleanups execute through the fixture transport; 64 TCR words are checked, with six collector-owned words retaining updated values. Product condition transport, allocation releases, callback retirement and destructor-trap ordering remain. |
| FMT-5/6, callbacks | Add typed table trampolines, collector-visible callback roots, callback admission during pending GC, and containment of Lisp nonlocal exits. The first unit refuses re-entry. |
| FMT-7, admission | Binary/declaration/digest controls execute, including start/initializer failure and source mutation. Add named-namespace loading and the larger pointer/ownership declaration contract. |
| FMT-8, Workers | The scalar profile chooses per-Worker instances. Production thread ownership, two-Worker schedules and interruptible funnelled calls remain. |
| FMT-9, lifetime | Whole-instance retirement executes. Add allocation generations, explicit free, finalizer suppression, callback deregistration and owner-queued finalization. |

The Node integration now uses ordinary post-READY `%FASLOAD` with the accepted
level-0 image and target-loaded runtime. Next work is a reusable Lisp-facing
scalar/copy service with declared byte ranges, encoding and ownership, followed
by namespace-provider loading and callback/finalization obligations. Browser
provider integration and full D5 must be qualified at their actual scope.
Native R6/R6a applies if a later step changes shared compiler source.

## Weak-table starting point

The [reviewed runtime weak-table implementation](../../../tests/wasm/stage1/loader-level1/weak-hash.md)
already supplies native-shaped weak-key/value vectors, an ephemeron fixed point,
moving-key tracking, reaping and atomic refusal. Its retained collector and
native-matched witnesses are reused at their recorded scope. It is not a new
Stage 2 implementation or acceptance.

Continue with image-builder metadata tables (still owner-created strong tables),
weak populations and finalization, then multi-Worker roots/lifecycle races.
Retain the audit-133 size census and the existing weak-table regression cases.
Finalization must compose with foreign allocation/callback retirement; explicit
release followed by collection must never invoke a destructor twice.

The other Stage 2 obligations remain open: production lifecycle and late-Worker
initialization, LL20 interrupt-wake I/O, conditions/restarts and binding/value
preservation under GC, floating-point qualification, and the relevant named
Stage 1 deferrals. Opening the stage or passing this first unit closes none of
those obligations.
