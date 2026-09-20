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
