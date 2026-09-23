# Runtime obligations carried into Stage 1

Implementation planning, 16 September 2026, incorporating the user's supplied
[ARM survey](arm-lessons.md). These obligations do not revise Stage 0 acceptance or count as
executed Stage 1 tests.

- **Runtime globals (1A design, 1D/1E implementation).** The Wasm runtime owns
  a process-wide record in linear memory, separate from NIL and from every
  Worker's TCR. The loader supplies its aligned base as an immutable instance
  import; native negative NIL-relative offsets are never accepted. Heap bounds,
  collection thresholds/counters, inhibition state and registry heads belong
  here. Tagged values must be published through explicit root descriptors;
  raw addresses and counters are not Lisp roots. Before a generated global
  access is enabled, the schema must assign its offset, width, owner, access
  protocol and collector treatment. Native return addresses, subprim addresses,
  TLS keys, signal numbers and Objective-C cells get protocol/service
  replacements or unsupported dispositions, not copied storage. The 1A
  generator excludes these native offsets and the initial leaf backend cannot
  emit a kernel-global access. This assigns the ownership/addressing model;
  it does not yet implement the complete record or its services.
- **Binding-vector growth (S1-LL17-a).** Specify the growing thread's ownership,
  the D1 no-thread-local-binding marker, initialization of every new slot,
  roots while copying, publication of pointer and byte limit, allocation
  failure, and retirement of old storage. Exercise collection at each legal
  boundary. ARM's `extend_tcr_tlb` in `lisp-kernel/arm-exceptions.c` and
  `%ensure-tlb-index` in `level-0/ARM/arm-symbol.lisp` are semantic references;
  native `realloc` and the trap are not Wasm implementations.
- **Interrupt masking (S1-LL17-a and S1-LL19-a).** Delivery consults the special
  binding for interrupt level as well as the pending request. Test nested
  `without-interrupts`, unwind restoration and pending delivery on re-enable.
  Masking Lisp interrupts must not disable collector rendezvous. See
  `check_pending_interrupt` in `lisp-kernel/arm-macros.s`; D5's explicit polls
  remain the mechanism.
- **Recoverable stack exhaustion (S1-LL19-a).** Distinguish a soft-limit Lisp
  condition from a damaged-stack fatal diagnostic. Reserve space before
  invoking the condition machinery, unwind safely and re-arm the soft limit
  after recovery. Cover control, value and temporary stacks, recursive handler
  exhaustion, and failure to restore the reserve. A bare engine trap does not
  satisfy this obligation. The accepted LL19 implementation uses one reserve-in-use
  bit for all three soft checks; hard limits remain independent. This is not
  native per-stack guard parity. [TCR v2](../contracts/tcr.v2.md) names this
  persistent state and the debugger depth; neither may be reused as scratch.
- **Trap lowering (1C).** Cross-reference the retained x86 sites with ARM's
  UUO list in `compiler/ARM/arm-asm.lisp`. Record continuable versus fatal
  checks, slot-unbound, missing throw tag, undefined function, unavailable
  foreign entry, array rank/flags/axis checks and integer division by zero.
  Preserve condition/restart semantics where supported; unsupported cases
  require explicit tested conditions. The list is a checklist, not an
  instruction encoding to carry over.
- **Callbacks (Stage 2 host services).** Specify slot allocation, signature,
  per-Worker installation, publication, replacement and retirement, plus
  host glue and stale-handle refusal. Do not copy ARM's four instruction
  words into linear memory. Wasm modules can be compiled and installed
  dynamically; linear-memory writes do not create executable trampolines.

## Architecture precedents

Use x8632 for the accepted D1 tags, distinguished-cons NIL and constant-index
limits. Read `xdump/xarmfasload.lisp` for the separation of function objects
and code, especially `xload-arm-set-entrypoint`; replace its native entry
address with D5's logical identity and typed table lookup. The per-target
registration shape is common to ARM and x8632. Neither native image writer
nor planted instruction sequences are a Wasm implementation.

ARM starts constants after two function words and adjusts `nth-immediate`;
x8632 has a different convention. The production constant-pool origin and
logical-versus-physical indexing must be explicit in S1-LL10-a. The 1A leaf
slice rejects heap constants and does not silently inherit either convention.
The Wasm CPU discriminator uses the unused value four in U1's three-bit CPU
field (32 after shifting), with OS discriminator seven and 32-bit word mode.
Existing values remain unchanged; the registration test checks collisions.

Do not use the unfinished ARM64 kernel, abandoned Darwin ARM build,
empty ARM trap handler, FP debug-trap stubs or absent ARM event-poll vinsn as
working precedents. D6's approved floating-point policy and D5's explicit
polling and allocation protocols remain in force.

## LL05 qualification follow-through

Implicit call errors now allocate private condition vectors and signal before
unwinding. LL19 must replace the private representation with production condition
construction/slots and extend the remaining checked-error paths, restarts and
debugger boundary. The collector must scan the helper’s condition and dynamic
result descriptor, including pending nonlocal transfers. Owner catalog/registry
trust, host re-entry and multi-Worker publication remain loader/runtime obligations.
General result-demand propagation remains an optimization beyond the proven-small
per-callee scratch path; LL05 makes no timing claim.

Claude audit 84 follow-through: LL19 must route APPLY with a non-list or dotted
final argument through Lisp TYPE-ERROR handling. The retained counterexample is
not covered by LL05’s designator/arity condition clause. Private class-mask
vectors and the checked no-handler boundary also remain production condition
and debugger obligations.


19 September execution follow-through (pending review): [LL19](control.md)
replaces the private condition payload with D1 instances/slot vectors under a
sealed owner bootstrap registry, routes improper APPLY into TYPE-ERROR with its
native datum, and executes restart/debugger-hook recovery. The same qualification
covers soft VSP/TSP/CSP exhaustion and explicit interrupt masking/re-enable with
independent collector service. These are executed claims, not accepted or
integrated changes. General class/symbol installation, moving collection and
host re-entry keep their separate obligations.


## Callable materialization (Claude audit 100)

Top-level function objects are materialized by the owner. LL14 must copy pool elements zero and one into the arity/debug words; only closure constructors initialize them in generated code.

Metadata validation is a per-call cost. It checks shape, identity and fixed counts, not all key-vector/debug contents. No timing claim.

Only keyword-symbol key names are admitted. Capture debug records follow environment-slot order, not source order; indices are explicit.


## Binding publication (Claude audit 101)

Manifest module rows match by name; their order does not affect admission.

Completeness is measured against the trusted owner's expected list. An owner omitting an alias from both lists is outside this control's authority.

Failed transactions discard their compiled instances and loader; rolled-back slots can be reused. Retained old module slots are never reused.


## Empty generic dispatch (Claude audit 102)

The empty-registry correction is in the generated dispatch service. Native CCL l1-dcode.lisp still has the retained stale-dcode defect; compiling native CLOS requires a separate source correction.

The guard covers an empty method registry. A raw stale store with a nonempty registry can select an incorrect method until recomputation; owner records remain trusted.

The private condition readers refuse non-instance arguments with checked code 4, not a handleable Lisp error.

Condition-using module bytes change with the bounded registry check. The inherited corpus was re-executed against native expectations, not claimed byte-identical.


## Integer service (Claude audits 103/104)

The exact-fit check uniquely rejects a strict capacity comparison; keep it when adapting reservations.

The thirteenth allocation fault is rejected by the follow-up and retained as escaped by the original harness. Do not count the original execution as rejection.

Canonical inputs beyond the admitted magnitude or header-width budgets may report 3 or 2. Neither permits an owner to retry the same input by merely extending output space. Status 3 also covers scratch/output exhaustion; a retry needs an independently established output shortage.

The redundant operand-base alignment check has no independent branch; tag six fixes that alignment. Owner region alignment remains checked.

The accepted service authenticates shape and extent, not object starts. Its owner must supply known objects and disjoint input, output, workspace and publication regions; no shared-memory, collector or generated numeric-dispatch admission is implied.

## Generated integer calls (Claude audit 105)

The harness derives its capability digest from its loaded bytes. The independent service identity is the packet inputs pin; require that pin at admission.

The original inline-fixnum assertion covers only addition of zero. Add per-operation fast-path counts without claiming the original packet did so.

The original decoder cannot represent NIL and omits short multiple-value fills. Retain added NIL-fill comparisons in the next unit.

Numeric failures are checked codes; fast paths still reserve operand roots. Assurance may move objects before refusing.

## Integer conditions R2 (Claude audit 107)

Numeric + and * keep left-first checks when both operands are invalid; native safety 3/speed 0 checks right-first. ASH count-first and explicit NIL divisor now match native.

Wrong-class arithmetic-error readers signal TYPE-ERROR rather than native NO-APPLICABLE-METHOD-EXISTS. ERROR handlers agree.

Arithmetic condition OPERATION and OPERANDS follow the explicit constructor, not x86-64 trap metadata; both native records remain retained.

Fatal kind 5 identifies a nonnumeric failure in this context but is not globally unique. Recognized unsupported number families and service-budget failures remain checked boundaries.

Numeric allocation-retry composition and trusted-loader admission remain separate work; no LL16 credit.

## Numeric owner composition (Claude audit 108)

The unchanged compiler retains its 252 inline-path assertions in the accepted R2 packet; this composition does not rerun that assertion layer.

Fault oracles combine a required failing execution with a function-name substring. Neither alone identifies the complete fault.

The capability factory binds a pair to one supplied owner; it does not prevent two CollectorOwner instances over one memory. Exclusive collector ownership remains the production installer’s obligation.

## Floating primitive service (Claude audit 110)

Six independent literal checks guard the Python oracle; the old-oracle target regression overlaps the positive corpus. Service faults identify a focused failing case rather than a unique failure cause.

Primitive integer coercion overflow and huge-integer/infinity comparisons differ from native CCL as retained. A Lisp adapter must preserve explicit native coercion errors and resolve infinity comparison semantics before LL16 qualification.

This raw service admits private unshared memory and nearest rounding only. Collector capability, generated calls, Lisp condition delivery and TCR control remain separate work.

## Collecting floating capability (Claude audit 111)

The omitted development r2 was a passing pre-controls run. The capability bytes were unchanged across r1–r4; original failing attempts r1 and r3 remain retained.

Unchecked calls validate enabled bits but do not apply them, as in the accepted primitive.

The full 59083-row capability replay and 3000-step chain are Claude audit-111 probes; the retained author fixture samples 1585 rows.

Native explicit coercion-overflow and integer/infinity compatibility dispositions remain obligations for generated Lisp calls.

## Generated floating calls (Claude audits 112/113)

Audit 113: R1 review reference now uses the full audit-112 commit hash.

Audit 113: raw regression comparisons re-derived from the retained report at integration, rather than its summary constant; immutable reviewed evidence is unchanged.

Audit 112: native h_collect payload matches its explicit-constructor oracle on this host; that oracle remains as reviewed.

Unchecked generated rows compare with native execution with all hardware traps masked; explicit library coercion errors still apply.

Integer-only comparisons are admitted, while integer division and broader numeric families remain outside this slice.

Native reference bignum coercion is selected by magnitude rather than the narrower D1 tag; later arithmetic flags retain D6 checks. Exact-tiny native trap difference remains explicit.

Owner capability admission is trusted identity, not code signing. Assurance may move objects before refusal. No LL16 or performance credit.

The floating profile requires a primitive binary exporting `float_calculate_lisp`; the original mathematical entry remains available separately. Runtime build flags must retain both exports.

## Numeric performance integration (Claude audit 115)

The fixture reports state inherited totals, not direct-path coverage. The bench rows are entirely direct; handler rows mostly fall back because they enable underflow or inexact traps or use bignums and nonfinite values. Audit 115 measured 21,855/36,451 plain raw cases and 2,920/10,540 generated floating calls using the direct path.

Timing uses 20 trials of 125 ms after 500 ms warmup, below v3 benchmark discipline, and is descriptive. Native figures include GC; Wasm figures exclude collection.

The direct path never collects. Movement correctness rests on the slow path and post-growth refresh checks; pressure fixtures deliberately fall back before writes.

The owner must supply the shipped digest-bound scalar.wasm to floatingCapabilities as scalarBytes with scalarDigest. Omitting it keeps the existing service.

Sufficient-space owner assurance checks live state rather than enumerating unrelated image objects. Admission and collection still validate image shapes. Authority remains the trusted synchronous single-Worker owner.

Bignum operations still cross JavaScript and copy through private memory. Eligible scalar operations still pay ownership checks, boxing, temporary-frame and result-delivery costs; no native-speed or formal performance claim.

## LL16-a acceptance (Claude audit 114)

Acceptance covers native policy comparisons mapped to the two generated checking modes, not source OPTIMIZE admission. q1/q2 generated bytes coincide; reported target totals include those repetitions. Original and follow-up timings establish no formal v3 performance qualification or application-throughput claim. The [acceptance record](acceptance-ll16.json) retains the numeric-family limits, policy-dependent compatibility differences, poison scope and performance observations.

## Strong EQ tables (audit 116)

The accepted runtime uses fixed-capacity strong backing vectors and trusted internal B adapters. CL hash-form lowering, the HASH-TABLE wrapper, growth, weak semantics, pinned-image inventory and production installation remain deferred. The retained trace’s nonempty test implies a heap key only for that corpus; the scanner itself marks actual bucket-key relocation. The packet hash_seed option is unused. See [integration](integration-ll18b.json) for all audit observations.

## Portable digest integration (Claude audit 117)

Snapshots now copy ArrayBuffer storage as well as views; prior Buffer.from(ArrayBuffer) aliased it. The reviewed loader and installer controls bind ownership.

Import-name prefixes use UTF-8 byte length, identical for current ASCII names and correct for non-ASCII names.

Audit 117 resolves the same-Worker mixed-placement refusal as a Maglev-tier fault in pinned Chromium 145.0.7632.6. It passes with Maglev disabled, in Node 25.6.1 and Chrome 153.0.8010.36. Keep the affected build/placement limit in browser qualification; the runtime bounds check is unchanged.

The pinned README claim that adding diagnostic arguments made the run pass is unsupported by the retained logs and is superseded by audit 117. The immutable fixture remains unchanged for replay.

The retained browser coverage is Chromium only; no Firefox, WebKit or complete engine-matrix qualification follows.

Pure-JS SHA-256 is synchronous construction/installation work, not arithmetic-path work. Audit 117 measured about 26 seconds for a 1 GiB input; very large module binding needs a separate budget. Factory signatures and capability identities stay synchronous and unchanged.

## D2 production materialization (audit 118)

The owner supplies engine provenance, ABI and instruction classification. Install verifies these bindings but does not discover the current engine. JSON field ordering is part of the present record comparison. Generated imported globals use the two-byte shape; typed references outside it refuse. Atomics have no per-profile filter; wait/notify stay banned and no qualified module uses atomics. Complete unshared runtime services, browser qualification, JSPI and packaging remain separate. See [integration](integration-ll21a.json).

## Per-function packaging (audit 119)

The accepted bootstrap packaging is one generated Lisp function per module, with both B roles and heap-resident closure environments. Preserve old modules/slots while old function objects remain live; code reclamation and merging are unimplemented. The trusted expected inventory defines completeness. The 19-module corpus has 18 distinct binaries, equal-size constant-only revisions, and is not the completed bootstrap workload. Cold ~1.93 ms is lazy-tier decode/validation; full validated installation is ~37.1 ms for this set, not a per-call cost. Eager retention is 458,786→549,124 bytes in the retained run. See [integration](integration-ll21b.json) for the review observations and scope.

## Symbols and packages (audits 120/121)

Original R1 replay uses 3ebb85d6 because its recursive source enumeration predates the nested follow-up; the follow-up replays from HEAD.

Integrate the corrected C service from the follow-up, not the original surrogate-admitting service.

The pre-existing keyword is owner-materialized from native membership, not copied from the native package; find-before-intern identity and relocation are executed.

Fixed-capacity sealed package topology and pinned objects; no package mutation API, production symbol registration, moving package scanner or complete bootstrap membership claim.

Names reject surrogate words, matching native CODE-CHAR; noncharacters remain admitted. Owner image and tables are pinned with sealed topology, 4–256 table capacity and 4,096-code-point names. No global registration of the runtime functions or package collector scanner is supplied. See [integration](integration-ll09a.json).

## Shared initialization (audits 122/123)

Use the reviewed follow-up owner, with the actual Worker-local table and tail_table supplied before any claim. Both must meet the declared capacity.

The owner accepts one table object for both roles. Callers must supply distinct tables; the accepted lazy loader rejects aliasing at installation, after the claim. Moving distinctness admission earlier requires a separately reviewed change.

On fresh storage the reserved scan runs first, so a dirty reserved word reports CONTROL_RESERVED rather than CONTROL_NOT_FRESH. Both refuse without writes.

Fresh bootstrap requires zero control storage; reserved words remain zero. Only trusted protocol owners may write it. Callback failures are terminal, not rollback.

Busy bootstrap contenders refuse instead of waiting; a winning initializer may cause PROCESS_STATE or CONTROL_NOT_FRESH. Join and retry policy belongs to the scheduler.

The follow-up uses a frozen source list in a sibling directory. Adding the integrated runtime module changes R1 recursive runtime enumeration, so replay the original R1 verifier from d6bf93fb; the follow-up frozen pins remain valid at HEAD.

See [integration](integration-ll13a.json). The accepted bounded shared profile initializes only owned regions; it supplies neither a scheduler nor a production cross-dump.

## Generated initializer schedule (audit 124)

The scheduler validates private byte copies, but the trusted installation callback installs from its own loader catalog and returns only an invoke function. A behaviour-identical substituted binary can reach ready. Before relying on production startup identity, bind the loader installed digest to the plan digest. This integration preserves reviewed bytes and does not add that binding.

Effects are checked only at declared state words, completion words and ready words. Undeclared writes elsewhere remain outside the scheduler view; foreign-region checks belong to the LL13 owner qualification.

The nine initializer bodies are protocol markers, not the selected native startup worklist. Membership, required effects and any needed census witnesses remain open for S1-LL15-a; no slot credit.

Trusted synchronous single-Worker callbacks require exclusive access to state and ready regions. Failure is terminal without rollback. No cross-Worker publication, callback confinement or movement of raw state addresses during a run is qualified.

See [integration](integration-bootstrap-schedule.json).

## Native startup resets and installed-byte binding (audit 125)

The digest-bound adapter closes the audit-124 catalog-substitution gap for this adapter only; BootstrapSchedule still trusts any installer callback. Invocation and imported capabilities remain trusted.

The PRIVATE_CATALOG diagnostic wraps any failure of the private-catalog run, so the fault control proves refusal, not a specific reason (the underlying loader reason is BINARY_DIGEST).

Effects are checked only within the 8,600-byte image window and at declared words; writes to the binding vector, allocation area or stacks are outside the view. Foreign-region checks belong to the LL13 owner.

The thirteen resets are the literal subset of one post-restore snapshot; membership and the 22 computed callbacks remain open for LL15. No production package materialization, ordinary-condition activation, coordinated image or complete startup is claimed.

See [integration](integration-startup-resets.json).

## Startup configuration R2 (audit 127)

Use the retained R2 callback and both corrected harnesses. Original startup-config and startup-resets sources remain historical pinned evidence; never use the superseded R1 spin body for integration.

Browser concurrency may differ from native. Millisecond units and Lisp stack extents are explicit runtime/owner policy, not measured native clock frequency or browser stack size.

Full TCR preservation is a check for these nonallocating startup bodies only; mv_count is separately verified. Seventeen snapshot callbacks, wider startup membership, definition effects and ordinary-condition activation remain open. No LL15 credit.


- **Bootstrap weak tables (user decision, 2026-09-20).** The user authorized
  “Use the Stage 1 strong substitute.” Both keys and values may remain live in
  Stage 1; expose NIL weakness rather than claiming weak behavior. Preserve EQ,
  EQL and EQUAL separately. Counts, enumeration and lifetime after collection
  can differ; do not introduce finalizer callbacks. Stage 2 owes weak semantics.
  [The executable proposal](../../../tests/wasm/stage1/bootstrap-tables/README.md)
  covers the EQ backing vectors only. Production still needs full wrapper and
  equality services, placement/root publication, capacity/growth policy, and
  linkage of the selected constructors to the actual startup worklist.


- **Bootstrap population extension (user decision, 2026-09-20).** “Use strong
  retention for populations too” extends the earlier table decision to system
  locks, threads, generic functions and public population construction. Retain
  members strongly in Stage 1, disclose longer lifetimes and changed post-GC
  membership, and implement weak behavior in Stage 2. The reviewed native weak
  headers remain refused by the collector; the new proposal uses ordinary
  vectors/conses and requires explicit constructor/accessor lowering before
  installation. A generic constructor site is not a count of live populations.
- **Bootstrap capacities (audit 132).** Require actual image-entry counts plus
  headroom; source `:size` is only a hint. The current service is capped at
  16,384 slots. Oversized plans refuse before construction and installed FULL
  refuses without eviction, mutation or growth. The populated EQUAL combined-
  methods table remains a hard dependency until its equality service exists.


- **Complete weak-object measurement (audit 133).** Measure instances by heap
  walk, not only globally named tables. Attribute closure-held tables and FTD
  fields by identity. The pinned image contains 19 weak tables and seven exceed
  60 entries; populated EQL and EQUAL tables both block bootstrap. Future image
  contents require a new count, not reuse of these counts as bounds. Include the
  18 populations owned by method-combination metadata in constructor/accessor
  lowering. The separate terminatable alist has native finalization obligations;
  ordinary strong-list storage does not discharge them, even with an empty queue.


- **Port image census (audit 134).** The accepted-scope candidate measures the
  pinned native macOS image only. Re-take instance counts and owner/source joins
  on the actual cross-dumped heap before table capacity/root installation and
  LL14/LL15 image claims. The retained EQUAL combined-methods count is seven;
  eight belongs to the earlier observer-affected probe.


- **Termination policy (user decision, 2026-09-20).** The user selected “Exclude
  it in Stage 1 (recommended)”. [Decision and enforcement requirements](termination-decision.md):
  explicitly refuse `terminate-when-unreachable`; do not silently retain or
  discard registrations. Reject images carrying registered objects, pending
  callbacks or live termination-function registrations. Disable/exclude native
  automatic scheduling and disposition remaining consumers before bootstrap
  closure. Finalization remains owed in Stage 2. This policy is approved; the
  [isolated enforcement proposal](../../../tests/wasm/stage1/termination-exclusion/README.md)
  now executes, awaiting review. Bind its generated entry digests to the real
  CCL symbols and map the admission guard to actual image data/pending/count/
  enable slots before READY. Its trusted-owner slots are not proof of global
  root discovery. Recheck the actual cross-dumped image; production integration
  remains open.

- **EQL bootstrap key domain (termination-exclusion survey).** The populated
  specializer table in the pinned image contains 94 symbols and integers
  1, 2 and 30. Those keys have identity-compatible EQL behavior, but new
  specializers can carry boxed integers, floats and other EQL numeric values.
  Do not substitute unrestricted EQ for the pending EQL service. The empty
  inspector EQL table and the populated EQUAL table remain separate joins.

- **Termination empty-state consumers (audit 135).** R1's refusal for
  cancellation, lookup and queue draining breaks `fd-stream-close`, which
  cancels unconditionally before its flush/close path. Use the
  [corrected follow-up](../../../tests/wasm/stage1/termination-exclusion-review/README.md):
  exactly one NIL for those three operations under the admitted empty-state
  invariant. Registration still signals SIMPLE-ERROR; enabled scheduling and
  nonempty image state still refuse. Do not install R1's three error bodies.
  The native reference now calls the untouched native functions, and real
  file close plus a generated close/cleanup model execute. Actual image
  installation and global empty-state admission remain owed.

## Bootstrap values integration — audit 143

The quoted-constant, special-variable and OR lowering is accepted. Admission and static dependency closure do not establish execution: target reader conditionals can erase a native body, and native self-call stubs need open coding. Correct both measurement defects in the predicate/whole-file unit under adopted P3. Existing eight native-matched functions remain the executed author count. The previous frontend acceptance was explicitly the user’s instruction, confirmed by “it was from me”; see `acceptance-bootstrap-frontend-provenance.json`.

## Bootstrap core — audit 145

C-1: add executed witnesses for %ILOGNOT and signed less-than %I<>; neither has one in the accepted corpus. Distinguish implemented operators from emitted/executed operators.

C-2: isolate the inline fixnum operand check with a refusal. This check is stricter than native safety-0 code.

C-3: isolate the node-access object-tag check; existing malformed objects also fail later checks.

C-4: reconcile the even-length %GVECTOR padding convention (NIL) with strong-population padding (zero), and test it. Integration preserves reviewed bytes pending that next-packet decision.

Callee closure is not all-input execution: %QUO-1 refuses ratio-producing division under the accepted numeric service scope.

Next packet: ERROR/SIGNAL with arguments, character/string primitives, l0-symbol and l0-misc whole, and a denominator from the real Wasm module list.

Original proposal verifier replays from 6947f83b after integration; no additional LL15 credit.

## Audit 148 — accepted library and dependency integration

252 original definitions execute and match native; 193 have a non-NIL witness, while 59 return NIL for every retained input. Add member inputs before treating structure predicates as positively exercised.

After member witnesses, supply recipes for the remaining 136 closed definitions without inputs, then resolve the 22 target-list files stopped at reader/environment errors. Historical admission 1864/2492 and incomplete target admission 1522/1919 are not bootstrap completion.

Replace the handwritten ASSQ WAT loop with a CCL-style target Lisp definition through the normal compiler in the next implementation packet; this integration preserves the reviewed lowering.

Move refusal of literal handler classes outside the twenty admitted classes to compile time. The integrated runtime retains the reviewed checked refusal.

Add source-emitted witnesses for %I<> and %IZEROP, condition-lowering refusal cases, and the bit-vector array-kind refusal case.

Literal-zero subtraction of negative double zero differs from the native compiler: target preserves -0.0d0, native returns +0.0d0. With variable zero both preserve the sign; retained as an explicit native compiler quirk.

Exact integer division is supported; nonintegral quotients refuse rather than truncate. Ratios, bignum logical operations, the full dynamic type system, proper native improper-list conditions and initialized object layouts remain outside the current executable scope.

The three original packet verifiers replay at their proposal commits after integration. No LL15 or BT-0 completion credit is claimed.

## Audit 149 — accepted witnesses integration

Audit-149 C-11 closed here: all forty collector-owner checks pass against the new collector and owner. The optional generated-boundary check is outside that count; generated execution is retained separately.

The fixnum selection is folded into the existing operator CASE, with no helper hook. All generated modules and checked outputs remain byte-identical to the reviewed packet.

ASSQ as a Lisp definition in level-0/WASM32 remains next-packet work.

Literal handler classes outside the admitted set still need compile-time refusal; do not confuse this with the now-tested explicit condition-constructor refusal.

The SIGNAL-spread refusal case remains owed; the other six condition/bit-vector refusal cases are retained.

Literal-zero subtraction of negative double zero retains the native-compiler signed-zero observation from audit 148; no behavior change here.

The next fixture extension should use a written harness instead of the current string-replacement chain.

Correct the Wasm module list, including removing or replacing linux-files, and implement Wasm branches at the nineteen POSIX lookup sites. Do not substitute native OS values. The next denominator must use that corrected list.

Eighty original closed definitions still have no input recipe (87 when the six fixture helpers and EQL primitive are included). Eleven executed definitions remain NIL-only as disclosed.

%PATH-MEMBER is uncredited because native source reads beyond a string bound before testing termination. Raw array subtype/flag return values require representation-aware expectations.

Original proposal replay stays at 9f5bd0cc after integration. No LL15 or BT-0 completion credit is claimed.

## Audit 149 carry proposal — awaiting review

[Bootstrap carry packet](../../../tests/wasm/stage1/bootstrap-carry/README.md)
implements Lisp ASSQ, macro-time refusal of unsupported handler classes, and
SIGNAL/ERROR spread refusal cases. These obligations close at acceptance and
integration, not merely at proposal publication. The written execution harness
also replaces the accumulated harness replacement chain.

The signed-zero observation now has a direct bit-pattern witness: native literal
zero changes -0.0d0 to +0.0d0; target subtraction retains the sign. Variable zero
agrees. No numeric behavior was changed and the four observed differences are
excluded from the native-match count. Collector-owner checks already closed in
b9de543d are reused only on exact source and rebuilt binary identity.

## Audit 150 — carry acceptance

Steve accepted the carry packet explicitly. Lisp ASSQ, compile-time handler admission, spread refusals and the written harness are integrated byte-exact; those carry items are closed. Literal signed zero remains a tested, declared difference. The witnesses replay source override now crosses the subprocess boundary; its documented command must be run from the committed clean checkout and retained with the next execution packet. Remaining execution recipes and POSIX source/module work continue.


Math R2 (audit155, accepted by Steve): pinned musl implements the 26 finite single/double transcendental entries. The adopted two-ULP native comparison limit leaves signed zeros, exact identities and domain conditions exact; it is not a global error bound. Checked underflow/inexact trap modes still refuse. The runtime build must include every pinned libm header and retain COPYRIGHT. Production primitive results use the boxed destination; native optimized unboxed locals may not expose destructive mutation. The immediate-bignum uint32 proof limit and MINUS1 witness continue as compiler work.

## Audit 158 — accepted arch, hyperbolic and funcallable integration

Steve's “address the obligations and accept/integrate” accepts the cumulative
reviewed compiler and runtime, including the seven-field D1 funcallable storage
layout. [The storage record](function-storage.md) is authoritative for these
integration obligations; ordinary six-field functions are unchanged.

- O-6's storage decision is settled: ordinary keyword vectors live at element 6
  of the existing arity record, reached through function byte offset 16. Target
  `lfun-keyvect` implementation remains owed. Ordinary `nth-immediate`, coverage
  notes and trampoline reflection still refuse; admission is not execution.
- O-7 is retained as an explicit observer: `1.5s0` gives native `(T T)` and
  target `(NIL NIL)` before/after movement at both placements. Boxed singles
  follow x8632. No native-match or new-definition credit.
- O-8 is an explicit admission widening: the installer accepts legacy and the
  existing floating-owner profile. The loader still enforces its digest and
  trusted bundle identity checks. The default range reader still refuses
  function imports.

The production float and collector builds equal the reviewed binaries; the
17,156-comparison record and forty owner checks reproduce through installed
imports. R6/R6a is reused only after every final compiler, arch and CCL source
file matches the qualified proposal by hash. Prior proposal verifiers replay at
their recorded commits; the acceptance runner works after integration.

Method dispatch still invokes template code rather than vector index 4. Real
class/wrapper fixtures, production image materialization and CLOS READY remain
owed. Execution-first follow-on work is the 175 admitted numeric definitions
without execution, roughly 90 CLOS accessors, FFI definition exclusions, then
condition classes, kernel globals, heap constants and spread kinds. No LL15 or
BT-0 completion is claimed.

## Review observations O-9 to O-11 — pending proposals

- **O-9:** The division proposal's `NO-REM` branch is behavioural. Its acceptance
  and integration records must name [WB-1](behavioural-branches.md), including
  the intentional difference from x8632/ARM. Reader preservation remains true;
  the branch is not necessary for the quotient's arithmetic correctness.
- **O-10:** The 28-row condition registry has exhausted its positive-fixnum
  handler-mask representation through bit 28. Do not allocate another mask or
  treat bit 29 as a usable positive-fixnum extension. The successor is Lisp
  `TYPEP` against real condition classes and their class precedence lists, built
  on the CLOS class/wrapper work. The eight remaining class refusals remain
  refusals until that path is implemented and qualified.
- **O-11:** The old condition packet remains immutable. Its 12,492 control
  paths comprise 12,480 base-corpus aliases and 12 distinct mutation artifacts.
  [The canonical verifier](../tools/verify-condition-frontier.py) compares 3,799
  artifact contents, retains all twelve mutation artifacts, and checks alias
  edges without hashing their contents again. Existing qualified replay may be
  reused explicitly; fresh mode still compiles and runs all four controls.

These observations do not constitute user acceptance of the pending packets.

## Audit 159 acceptance

Steve accepted all seven reviewed packets, including WB-1 explicitly, and the
final reviewed files are integrated. The preceding O-9 pending disposition is
superseded by [the stack acceptance](acceptance-bootstrap-stack.json).
O-10 remains an implementation obligation; no extra mask is authorized.
Claude's 490 random bignum cases are independent review evidence, not extra
retained author execution credit. Future bignum recipes should include dense
seeded operands alongside the existing boundary cases. Method selection and
image/READY materialization remain separate from the accepted combined-method
dcode and funcallable storage work.

## Audit 160 acceptance and retained limitations

Steve accepted the reviewed GCD and cached EQ/EQL method-dispatch packets with
“I accept the reviewed packages”. The full standard-GF proposal `761f1cc1`
remains separate and unreviewed. Integration grants no LL15 completion credit.

- **O-12, bignum stores:** generic UVSET admits only nonnegative target fixnum
  digits (0 through 2^29−1). Native's unsigned-32 contract also admits bignum
  digit values through 2^32−1. Those wider values refuse with checked code 5;
  the existing half-digit routines remain the supported wide-digit path.
- **O-13, host restart branch:** `%KERNEL-RESTART` calls target Lisp because no
  native frame pointer exists. Registered hooks run first and receive NIL for
  that argument. Only `$XWRONGTYPE` with two arguments has the built-in numeric
  USE-VALUE fallback, including revalidation. Other kernel codes signal
  SIMPLE-ERROR. This host adaptation is not the WB-1 NO-REM behavioural change.
- **F1, historical replay:** the canonical condition verifier uses its pinned
  Git source revision for pin validation, derivation and execution. Neither
  mode modifies current files. The historical packet and its execution credit
  remain unchanged.
- Verification records from numeric dispatch onward are retained and cataloged
  beside their packets, with their hashes in the evidence catalog. They are not
  separate auxiliary acceptance units. Their replay grants no new slot credit.

Generic GCD/ABS, real-CPL condition matching and image/READY construction remain
open. Full standard method selection is implemented in the separate proposal
awaiting review, not claimed by this cached-dispatch integration.

## Audit 161 — accepted standard GF dispatch

Steve accepted the entire reviewed `761f1cc1` proposal with “accept and
integrate”. These limits are carried into its acceptance and integration
records. The pinned fixture remains unchanged.

- **O-14, CERROR:** the symbol-designator branch drops initargs, and a condition
  object with extra arguments does not raise native's too-many-arguments error.
  The fifteen compiled callers use a condition object or string without reaching
  these narrowed cases. Those argument forms have no compatibility claim.
- **O-15, method metadata:** `%INNER-METHOD-FUNCTION` is identity. The image
  methods exercised here have the required metadata. Closure method functions
  need a declared metadata/encapsulation contract before being qualified.
- **O-16, method-list pruning:** the target leaves `COMPUTE-METHOD-LIST`'s
  sub-dispatch argument true; native combined-method construction passes NIL.
  The resulting longer chains contain unreachable methods after a method that
  cannot call next. Tested values and traces agree; no equivalent cost is claimed.
- **O-17, LAP merge:** keep the proposal's correct Lisp EQUAL and backend
  `%ILOGCOUNT` lowering. When merging `wasm2-claude-lap`, drop its duplicate
  `%ILOGCOUNT` and do not add a second EQUAL. This records merge ownership;
  it does not authorize or perform that separate merge.
- **O-18, MAKE-ARRAY:** the one-argument lowering builds a simple vector for an
  integer dimension. A list dimension refuses with checked code 6; general
  multidimensional array construction is not implemented by this arm.

The integration qualifies the final shared files and recounts admission.
Cross-dumped classes and `%ALL-GFS%`, wrapper invalidation and caching, real-CPL
condition matching, and closure metadata remain separate obligations. The
accepted GCD/cached-dispatch stack is already integrated at `a61947f8`.

- **Accepted LAP integration (27f5bc02; Codex review c47b0a47).** Keep the
  integrated CLASS-OF, FALSE, EQUAL and ILOGCOUNT implementations; the LAP
  duplicates are withdrawn. Generic logical operations use CCL's LOGAND-2,
  LOGIOR-2 and LOGXOR-2 with rooted operands. Whole-file allocation retry is
  still opt-in and was explicitly enabled for the full-heap review probes.
  `transcend.c` is the single switch included by `float.c`, with sqrt ops 44/45.
  Slot-id closures, displaced-array access, the three hashes without an oracle,
  FAST-MOD-3, SET-%SHORT-FLOAT-EXP and %FUNCTION-REGISTER-USAGE remain unexecuted
  and uncredited. Runtime/thread LAP and installation in the real image/READY
  path remain required. See [the integration record](integration-lap.json).

## Audit 162 — accepted default-off condition CPL matching

Steve said “Accept and integrate default-off”. Only the reviewed backend
changes; no runtime or CCL source change. `*b-cpl-conditions*` defaults to NIL.

- **O-19, class initialization:** the six callers execute through an explicit
  fixture list. They are not dependency-closed: CLASS-TYPEP reaches
  %INITED-CLASS-CPL, with UPDATE-CLASS and COMPUTE-CPL still open. Require
  initialized CPLs; a NIL CPL can reach checked code 2.
- **O-20, class identity:** compile-time admission knows host classes, while
  the fixture catalog holds eleven names. Missing runtime names refuse with
  checked code 12, rather than falling through to another handler. Replace
  this cons-cell catalog with actual class-cell structures from the real
  cross-dumped class table. It is not the final image class registry.
- **O-21, condition-system scope:** construction and readers retain their
  prior schemas and the 28-row mask registry. SIGNAL still refuses string
  and symbol designators. The accepted change covers O-10's matching component
  only; do not claim that the condition-system migration is complete.

The successor should compile CCL's class lookup, MAKE-CONDITION/MAKE-INSTANCE
and slot initialization machinery, using the same class identities throughout.
Actual image roots and the READY join remain required. See
[the integration record](integration-condition-cpl.json).

## Audit 163 — accepted default-off native condition system

- O-19: Finalized initialized CPLs remain required; UPDATE-CLASS/COMPUTE-CPL is not qualified.
- O-20: The eleven-name catalog is retired in favor of FIND-CLASS over 612 projected native class cells. Actual cross-dumped class roots and READY installation remain owed.
- O-21: Explicit construction, readers and signal designators use class identities. Implicit allocation still uses the old registry; *BREAK-ON-SIGNALS* and %ERROR re-entry remain open.
- O-22: Author retention used --reuse-output (execution_rebuilt: false). Claude audit 163 performed the independent from-scratch replay (execution_rebuilt: true). Integration reuses both and claims no new execution.
- O-23: SIGNAL currently resides in w32-prims.lisp. Move it to a #+wasm32-target branch in l1-readloop.lisp in the next proposal; this integration preserves reviewed bytes.
- O-24: Only strong-EQ GETHASH is admitted. SETF GETHASH and class-table writes remain the next implementation work.
