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
[foreign-runtime-results.json](foreign-runtime-results.json). **Accepted after user-supplied [Claude audit 195](../stage0/claude-review.md)**
(`a33254e6`, imported as `ec1f2532`). No FMT or LL credit.

Audit 195 reproduces the owner, scalar and Lisp results byte for byte and finds
no defect. Acceptance reruns no unchanged tests. O-165 adds directed entry/exit
heap validation and checkpoint tests to the next substantive unit. O-167
requires atomic descriptor publication and safe exit ordering before any
multi-Worker qualification; the current single-Worker scope is unchanged.
O-166/O-168/O-169 remain non-blocking observations.

The first direct public `%WASM-FIND-SYMBOL` probe after READY signalled checked 4
before the fixture; it is retained and unresolved. The qualified path uses the
existing `%FASLOAD` directly, not the COMMON-LISP:LOAD frontend.

## Third delivery: owned byte ranges

[Implementation and reproduction](../../../tests/wasm/stage2/foreign-buffers/README.md).
The scalar library now accepts optional allocator/release and pointer/length
contracts. Callers receive opaque allocation and range identities, copy through
bounded snapshots, and declare raw octets or strict UTF-8. Allocator and release
exports, including aliases, cannot bypass their managed entry points. Every
foreign entry uses FOREIGN; views and Lisp source addresses are reacquired
after growth or collection. Explicit release is idempotent, and offset reuse
cannot revive an old handle. Retirement invalidates all remaining handles;
a destructor trap prevents later releases from entering foreign code.

Qualification passes **64 buffer checks per engine / 26 killed mutants**.
The ordinary post-READY Lisp witness matches **seven native rows**, with
**38 foreign entries / 26 moving collections**. The owner passes **53 checks
per engine / 38 mutants** and its existing 12-row Lisp witness; the scalar
regression passes **126 checks per engine / 16 mutants**. Results are bound in
[foreign-buffer-results.json](foreign-buffer-results.json). **Accepted after user-supplied [Claude audit 196](../stage0/claude-review.md)**
(`fe2db2bb`, imported as `7392a92c`). No FMT or LL credit. This adds explicit release;
collector-triggered finalization, callbacks and the public Lisp API remain owed.
The fixture transport preserves a primary exception if a release later traps.

The owner dependency adds directed cases and semantic mutants for both
live-heap validation calls and all remaining checkpoint words (O-165), plus
O-168's inhibited collection. O-167 remains a prerequisite for multi-Worker D5.
The initial Lisp copy witness used the signed-byte subtag for an unsigned-byte
vector; that fixture failure is retained with its correction.

Audit 196 reproduces the buffer, owner, scalar and Lisp results and finds no
defect. Acceptance reruns no unchanged tests. O-165 is closed. O-170/O-173
carry release-refusal and output-encoding documentation into the next unit;
O-171/O-172 carry directed live-handle refusal tests. O-167 remains required
before multi-Worker admission.

## Fourth delivery: named libraries and the Lisp API

[Implementation and reproduction](../../../tests/wasm/stage2/foreign-api/README.md).
`foreign-libraries.mjs` loads digest-bound resident namespace blobs once per
Worker-local registry entry. `foreign-service.mjs` marshals i32/i64/f32/f64,
multiple values, byte vectors and allocation/range tokens through process
operation 15. The 50-line product Lisp API supplies open, call, copy, close and
explicit release, with `with-wasm-buffer` preserving primary errors and nonlocal
exits across cleanup. The source is target-loaded after READY; names currently
remain internal CCL symbols. No shared compiler or upstream kernel changes.

Qualification passes **63 API checks per engine / 21 killed mutants** and
**20 native-matched Lisp rows / 46 foreign entries / 36 moving collections**.
The buffer regression passes **66 checks per engine / 28 mutants** and its
original seven Lisp rows. O-170/O-173 are documented and O-171/O-172 now have
directed lifetime tests and killed controls. The older scalar/owner suites
reuse audit 196 by exact implementation identity. Process-service checks and
the boot driver are qualified at their changed seams. Results are bound in
[foreign-api-results.json](foreign-api-results.json). **Accepted after user-supplied
[Claude audit 197](../stage0/claude-review.md) (`d58ffe14`). No FMT or LL credit.**

Browser Workers exercise the product namespace, service and collector with
synthetic generated-B roots; ordinary generated Lisp executes under Node.
Automatic string encoding, Lisp callbacks, finalization and full D5 remain.
An independent literal-only probe reproduces checked 4 while printing `1.25d0`
without the foreign API; its minimal reproduction is retained as an unresolved
runtime frontier. The foreign scalar tests compare the value and representation
without claiming printer qualification.

Audit 197 reproduces the API, buffer and Lisp results and finds no defect.
Acceptance reruns no unchanged tests. O-174 carries directed service admission
tests into the next substantive unit; O-175 requires a persistent Playwright
version recipe. O-176 remains the separate literal-double printer frontier.

## Fifth delivery: collector-queued buffer finalization

[Implementation and reproduction](../../../tests/wasm/stage2/foreign-finalizers/README.md).
A buffer can now register a weak moving-heap lifetime anchor. The owner reads the
collector's completed forwarding map after each successful copy and queues dead
anchors without running foreign code. An explicit Lisp drain executes one batch
on the owning Worker outside collection. Explicit release cancels pending work;
close and traps cancel the library's remaining registrations. Recoverable
finalizer failures never retry the uncertain release and preserve later work.
This prepares lifetime machinery for callbacks; it does not implement callbacks,
general Lisp finalizers, automatic queue pumping or multi-Worker ownership.

Qualification passes **106 checks per engine / 55 killed mutants**, with
**30 native-matched post-READY Lisp rows / 81 foreign entries / 60 moving
collections**. Collector regression passes **128 checks / 11 controls**; owner,
buffer and scalar regressions pass at their recorded scopes. Product Lisp adds
10 lines. O-174 now has directed service refusals and float-header checks;
O-175 has a committed Playwright 1.58.0 lockfile and browser-revision recipe.
O-176 remains open. Results are bound in
[foreign-finalizer-results.json](foreign-finalizer-results.json). **Accepted after user-supplied [Claude audit 198](../stage0/claude-review.md)
(`94b410d0`, imported as `0244319d`). No FMT or LL credit.**

## Sixth delivery: explicit UTF-8 string copies

[Implementation and reproduction](../../../tests/wasm/stage2/foreign-strings/README.md).
The product Lisp API now copies simple strings to and from owned foreign buffers
with explicit `:utf-8`. Byte counts and offsets are explicit; BOMs and embedded
NULs survive without added terminators. Invalid Unicode, malformed UTF-8, bad
ranges and retired handles refuse before publication. Result allocation reloads
the rooted request after moving collection.

The combined API suite passes **148 checks in each of Node, Chromium, Firefox
and WebKit / 69 killed mutants**, adding **42 string checks / 14 controls**.
Ordinary post-READY Lisp matches **45 native rows**, including 15 new string
observations, with **88 foreign entries / 67 moving collections**. Native CCL's
own UTF-8 codec supplies the string oracle. Product Lisp adds 14 lines (74 total).
Unchanged lower-layer dependencies reuse the preceding unit by exact source
identity; the compiler corpus stays deferred. Results are bound in
[foreign-string-results.json](foreign-string-results.json). **Accepted after user-supplied [Claude audit 198](../stage0/claude-review.md)
(`94b410d0`, imported as `0244319d`). No FMT or LL credit.**

Non-simple strings, other encodings, callbacks, browser generated Lisp/provider
integration and full D5 remain. Audit 198 accepts the finalizer and string units at their executed scopes.
O-167 and O-176 remain open.

## Seventh delivery: typed callback boundary and rooted lifetime

[Implementation and reproduction](../../../tests/wasm/stage2/foreign-callbacks/README.md).
The lower layer now registers typed table trampolines with collector-visible,
reloadable roots. The one-Worker owner admits callbacks from FOREIGN and checks
return state before resuming foreign execution. Deregistration drops roots and
leaves typed fallback slots; slots never alias later registrations. Callback
errors are deferred until foreign frames return, and traps or failed admission
retire the appropriate boundary. Finalizer draining inside callbacks refuses
without consuming queued work.

The fixture uses real Wasm indirect calls and the production collector with a
trusted JavaScript invoker and synthetic B roots. Generated Lisp callback
invocation and the Lisp registration API remain next. The retained WebKit
failure and four-way probe establish the required grow-then-set table sequence.
Qualification passes **80 checks per engine / 63 killed mutants** in Node,
Chromium, Firefox and WebKit. Existing API/string/finalizer execution retains
**45 native-matched Lisp rows / 88 foreign entries / 67 moving collections**;
its four-engine suite passes 148 checks / 69 mutants. Owner, scalar and buffer
regressions also pass. Detailed counts are bound in
[foreign-callback-results.json](foreign-callback-results.json). **Accepted after user-supplied [Claude audit 198](../stage0/claude-review.md)
(`94b410d0`, imported as `0244319d`). No FMT or LL credit.** Product Lisp and whole-file
count movement are zero. Audit 198 accepts all three units as one reviewed stack.

Acceptance reruns no unchanged tests. O-174/O-175 are closed. Carry O-177
post-fatal owner-state assertions and O-179 drain/live-heap and registration-retry
cases into the next substantive unit. O-178 is a reason-only admission
equivalence; O-180/O-181 preserve the documented execution limits.

## Next foreign work

[HOSTFM P2](../host-and-foreign-modules.md#6-foreign-wasm-modules-cap-ffi-wasm)
remains the architecture; FMT-1–FMT-9 remain its proof obligations.

| Obligation | Current position / next implementation |
| --- | --- |
| FMT-1, scalar calls | Four scalar types, multiple results, signed zero and numeric boundaries execute in the owner unit. All four scalar types now execute through the product service in both portable placements and through generated Lisp under Node; browser generated Lisp remains. |
| FMT-2, bytes and encoding | Declared ranges, explicit copies and UTF-8 octets execute with fresh views after growth. Explicit UTF-8 simple-string copies now execute through the product API; other string representations/encodings and full browser/provider integration remain. No Lisp memory or addresses enter the foreign module. |
| FMT-3, moving collection | One-Worker owner roots and reloads execute with collection in an active foreign import and retired-space poisoning. Copied Lisp source ranges now execute across allocator/call/release collection. Lisp callbacks and other-Worker collection remain. |
| FMT-4, failures and releases | Generated Lisp conditions/cleanups execute through the fixture transport; 64 TCR words are checked, with six collector-owned words retaining updated values. Explicit allocation releases and destructor-trap ordering execute in the owned-buffer unit. The product service now signals ordinary Lisp errors after admission and preserves primary cleanup failures; callback retirement remains. |
| FMT-5/6, callbacks | Typed table trampolines, rooted lifetime, one-Worker callback admission, inhibited pending collection and deferred callback failures execute. Generated Lisp invocation/API and actual Lisp nonlocal exits remain; nested foreign calls and full D5 are not admitted. |
| FMT-7, admission | Binary/declaration/digest controls execute, including start/initializer failure and source mutation. Resident named-namespace loading now executes; mounted providers and the larger pointer/ownership declaration contract remain. |
| FMT-8, Workers | The scalar profile chooses per-Worker instances. Production thread ownership, two-Worker schedules and interruptible funnelled calls remain. |
| FMT-9, lifetime | Whole-instance retirement executes. Opaque allocation identities and explicit free detect offset reuse and instance retirement. Weak-anchor collection now queues releases on the owner, and explicit release/retirement cancel them. Explicit callback deregistration and retirement now drop roots without slot reuse. Automatic queue pumping, token/slot reclamation and multi-Worker qualification remain. |

The Node integration now uses ordinary post-READY `%FASLOAD` with the accepted
level-0 image and target-loaded runtime. The owned scalar/copy service now has declared byte ranges, encoding and
explicit allocation lifetime. A product Lisp API and resident namespace loading now
execute. Weak-anchor buffer finalization now queues on the owner with an explicit drain.
Explicit UTF-8 simple-string copies now execute as well.
Typed callback ownership now executes through the trusted fixture invoker.
Next work is generated Lisp callback invocation/API and broader providers. Browser
provider integration and full D5 must be qualified at their actual scope.
Native R6/R6a applies if a later step changes shared compiler source.

## Weak-table starting point

The [reviewed runtime weak-table implementation](../../../tests/wasm/stage1/loader-level1/weak-hash.md)
already supplies native-shaped weak-key/value vectors, an ephemeron fixed point,
moving-key tracking, reaping and atomic refusal. Its retained collector and
native-matched witnesses are reused at their recorded scope. It is not a new
Stage 2 implementation or acceptance.

Continue with image-builder metadata tables (still owner-created strong tables),
weak populations and general Lisp finalization, then multi-Worker roots/lifecycle races.
Retain the audit-133 size census and the existing weak-table regression cases.
Finalization must compose with foreign allocation/callback retirement; explicit
release followed by collection must never invoke a destructor twice.

The other Stage 2 obligations remain open: production lifecycle and late-Worker
initialization, LL20 interrupt-wake I/O, conditions/restarts and binding/value
preservation under GC, floating-point qualification, and the relevant named
Stage 1 deferrals. Opening the stage or passing this first unit closes none of
those obligations.
