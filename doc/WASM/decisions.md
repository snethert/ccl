DECISION RECORD  /  VERSION 1.6  •  11 SEPTEMBER 2026

# Stage 0 Desk Decisions

Companion to Port Outline v0.15 and Acceptance Policy and Regression Register v1.5

Version 1.6 replaces v1.5. At the user’s direction, D3 requires only C/C4/B; H(G) is optional future work and does not gate progress. D3 measurements state granularity and startup assumptions. The macOS reference, D5 protocol v1.1 and the other decided contracts remain in force. Execution and acceptance remain separate. [17–19]

R7 in the Acceptance Policy and Regression Register v1.5 governs all delivery and verification claims; recording a decision does not claim that its artifacts have been implemented or its tests run. [17]

| ID | Decision / experiment | Decision status |
| --- | --- | --- |
| D1 | Use the x8632-derived data-layout subset, with explicit Wasm execution-state replacements. | Decided. |
| D2 | Materialize shared/unshared binaries deterministically from one validated canonical template. | Decided. |
| D3 | Qualify and compare C, C4 and B. H(G) is only a possible future enhancement. | Open selection among three generic candidates. |
| D4 | Freestanding C kernel; Lisp-emitted subprimitives and ABI adapters; named runtime imports. | Decided. |
| D5 | Owner-only GC generation updates; published-root admission, membership rescan, typed entries and stable mailbox storage. | Decided: protocol v1. |
| D6 | Adopt disposition vocabulary and explicit trap lowering; complete the census and select floating-point policy separately. | Decided: vocabulary and lowering. |
| D7 | Use the register-derived Stage 0 ID/inventory scheme and staged correctness/benchmark prerequisites. | Decided: scheme. |

Revision scope. Applies the assessment recommendations under the recorded user authorization in history/changes.md. Historical H1 results and source links remain identified separately; R6 comparison categories are clarified in acceptance section 2. No runtime acceptance is inferred from these documents or their initial probes.

## D1  /  OBJECT-LAYOUT SCHEMA AND TAG SCHEME

### Adopt the x8632-derived data representation

#### Decision

Use compiler/X86/X8632/x8632-arch.lisp at U1 (`c994217adc56b3f8a564526cee4695893ac84d86`) as the reference for 32-bit words, ntagbits = 3, nlisptagbits = 2, fixnum shift 2, dnode size 8, and the fulltags even-fixnum 0 / cons 1 / nodeheader 2 / imm 3 / odd-fixnum 4 / reserved native TRA 5 / misc 6 / immheader 7. Derive the numeric, symbol, vector and other data-object layouts and subtag relationships from that source. Canonical NIL is a distinguished cons-tagged object at a schema-defined low address, with T at a recorded offset. [1]

Do not inherit the architecture verbatim. Native function/code-vector internals, catch and exception frames, return addresses, native stack frames, TCR fields, register contexts and host-pointer objects require explicit Wasm dispositions. Preserve a source-to-target ledger for every inherited, replaced or unsupported row. Do not turn on :x8632-target globally to obtain convenient conditionals. R6 protects the source architecture. [1, 3]

| Cons contract | Raw base B | Tagged pointer P = B + 1 |
| --- | --- | --- |
| CDR, first word | B + 0 | P − 1 |
| CAR, second word | B + 4 | P + 3 |
| Size and alignment | 8 bytes; 8-byte alignment | No cons header |

Constructor order remains (cons car-value cdr-value). CAR/CDR of canonical NIL return NIL; CONSP must still distinguish NIL from an ordinary cons, and RPLACA/RPLACD must not mutate NIL as an ordinary cons. Use unequal payloads and independent byte fixtures, not paired readers and writers that could share the same reversal. [1, 2; LL04]

#### Reasoning and validation

The x8632 source and cross-loader provide a concrete derivation basis, not proof of Wasm correctness or speed. Record each field in raw-base and tagged-pointer coordinates, its storage representation, alignment and GC treatment. C-backed layouts use target-compiled sizeof/offsetof assertions; emitted layouts use target-executed probes. Both must pass the same independently specified fixtures. [1–3; LL04, LL07, LL10]

For wasm32, a memory instruction has a nonnegative immediate offset. A negative tagged-pointer displacement therefore needs explicit address adjustment or a previously computed raw base; a positive one can use the offset. The eventual instruction selection and engine cost are measured, not inferred from native addressing. Record double-float payload alignment as well as object alignment. [4]

The signed fixnum range is −2^29 through 2^29 − 1. Nonnegative code IDs fit only within that bound if stored as tagged fixnums. A raw address or a larger unboxed ID is not converted into a fixnum by truncation. Raw fields, integer objects and root-bearing tagged words have distinct schema entries. [1; LL07]

#### Alternatives and reversal

ARM32 remains a legitimate alternative. Its use in the failed attempt is not evidence against its tag scheme; the recorded failures concerned inconsistent implementations. A different misc tag cannot be chosen in isolation: assigning tag 2 to misc collides with the retained nodeheader tag. Reconsider the derived scheme only with measured benefit and a coordinated, independently validated re-derivation. Native TRA tag 5 remains reserved pending an explicit target use, not silently repurposed. [1, 3]

Initial artifact: contracts/layout.json covers fixnums, tags and ordinary cons fields only; outstanding rows are explicit. Complete schema/wasm32-layout.v1, the source-to-target disposition ledger, and assertions/wasm32-layout.v1 remain implementation deliverables. The logical-frame replacement contract is contracts/debug-frames.md; do not infer a full schema from the initial subset. Stage 0 verifies fixtures; Stage 1 repeats through generated code and fresh cross-dump loading; Stage 5 repeats through application save/restore. [LL04]

## D2  /  MODULE MEMORY TYPE

### Canonical templates, profile-specific binaries

#### Decision

Emit a canonical Lisp-code template with a wasm32 memory import, explicit minimum and maximum, and sharedness clear. For the admitted encoding, materialization leaves limits flag 0x01 unchanged for the unshared profile and changes it to 0x03 for the shared profile. This length-preserving transformation produces two instantiable binaries from one template. The maximum covers the entire linear memory, including statics, stacks, TCRs, heap and staging regions. [5, 6]

The materializer verifies template identity, schema/version, the recorded patch offset and expected original byte; it rejects unsupported encodings or features rather than guessing. It validates the resulting module and records template hash, materializer version, profile, limits, imports, feature requirements and resulting binary hash. The manifest may supply the offset, but cannot bypass structural checks establishing that the designated byte is the intended limits field. [LL21, LL22]

#### Reasoning

Memory import sharedness must match, and shared memories require a maximum. Atomic load/store/read-modify-write operations can use unshared memory; Wasm waits trap on it. Notify does not have the same shared-memory prohibition. The runtime is built per profile for its selected suspension path, with wait-based mailbox/lock slow paths excluded from the unshared path. Qualify the required features in each engine. [5, 6]

A template avoids duplicating stored bodies and duplicated emission work where only the admitted materialization differs. It does not avoid compilation of each resulting binary. Separately emitted binaries could also retain the same logical code identities; they do not inherently create a second identity space. [Design rationale]

#### Artifact and reversal

Artifacts: a versioned materialization procedure and manifest schema, with positive shared/unshared cases and negative offset, original-byte, hash, import-limit and feature cases. Stage 0 verifies the selected transformation; Stage 1 confirms it through the production path before the first cross-dump; Stage 5 qualifies saved and resident-compiled code across profiles. The same logical code IDs describe the profile variants; final byte hashes remain distinct. [LL21, LL22]

Use separately emitted, explicitly recorded profile variants if a required semantic or feature difference cannot be represented by the validated transformation. Growth, suspension, root restoration and late-Worker initialization tests remain mandatory; successful flag patching alone is not portability proof.

## D3  /  DYNAMIC-CALL ABI

### Open ABI selection: C, C4 and B

#### Candidate set and specification

The user directed on 11 September 2026 that H(G) be ignored except as a possible future enhancement. D3 selects among C, C4 and B. No Stage 0 or Stage 1 prerequisite, mandatory experiment or acceptance gate requires H(G). Its earlier design and thresholds remain historical; reconsideration would be a separately scoped future decision.

A funcref table may contain functions with different signatures. Each call_indirect specifies a static expected type and checks the selected element before entry. One instruction cannot derive its signature from runtime nargs. A uniform generic Lisp ABI is a design choice, not a table-wide Wasm restriction; module-local type indices are not process-wide signature identities. [12]

Retain explicit self, a complete generic call path and the two-result convention. Take all three candidates through the correctness corpus before their baseline measurements. Self, arguments and value0 are tagged Lisp values carried as i32; count encoding and VSP ownership are separate protocol definitions.

| ABI ID | Wasm entry shape | Experiment |
| --- | --- | --- |
| C | (self, nargs, a0, a1, a2) → (value0, nvalues) | Three argument parameters; remaining arguments on VSP. |
| C4 | (self, nargs, a0, a1, a2, a3) → (value0, nvalues) | Four argument parameters; remaining arguments on VSP. |
| B | (self, nargs) → (value0, nvalues) | All Lisp arguments on VSP; simplicity baseline. |

Every callable function object has a generic entry descriptor tied to its code version and environment. Resolve symbol designators under the applicable CCL semantics and preserve live redefinition. Old retained function objects continue to call their own code and environments. For APPLY, validate the list and supplied count and spread arguments under the chosen generic protocol. Bad designators and arities follow Lisp error semantics, never a Wasm type-mismatch trap. [15; LL05, LL11, LL12, LL19]

#### Complete argument and result protocols, before timing

abi/dynamic-call.v0 must define the following for each candidate before timing. Include contracts/debug-frames.md and charge its publication, storage and inspection-policy costs consistently; S0-LL23-b precedes ABI freeze:

| Contract | Required definition |
| --- | --- |
| Arguments | For supplied count N, map each argument to a parameter or precise VSP-relative address. Define stack growth, reserved extent, alignment, raw/tagged count encoding, unused-parameter contents, arity checks and maximum supported count. |
| Ownership | Define caller/callee responsibility for overflow space, temporary roots, incoming-frame lifetime and bounds on ordinary return, tail transfer, errors and reentrant callbacks. Record before/after VSP, TSP and CSP invariants. |
| Returns | Return (value0, nvalues), with value0 = NIL for zero values consumed singly. Extra values use an owned VSP region with explicit extent and lifetime; the TCR descriptor refers to it. |
| Nested calls | Preserve earlier extra values in owned, rooted storage when needed across a later call. Define release and the complete ordered sequence through multiple-value-call and cleanup. |
| GC and suspension | Publish live self, arguments, temporaries and extra values at legal stopping/allocating boundaries. Reload moved roots and rederive pointers, including stub/adapter and C-helper boundaries. |

#### Lazy installation and entry identity

Each uniform candidate can use one shared stub for its Lisp-call convention. Key entry metadata by ABI version, semantic entry kind and structural signature. The stub's role and self identify the target; a wrong structural signature traps before entry, while matching Wasm types do not establish matching semantic roles. Retain wrong-signature and same-type/wrong-role rejection controls for the generic entry and runtime adapter contracts. [12; LL05, LL21]

Every allocated uninstalled slot contains the matching stub before dispatch. The stub publishes roots, obtains the owning module, validates and instantiates the profile-specific binary, installs admitted entries, reloads moved references and redispatches under the same contract. Preserve count, overflow arguments and result-region ownership. Seed the installer's dependencies eagerly. A blocked Worker uses an accessible byte cache or stable mailbox with notification, not an incoming event-loop message it cannot handle; JSPI uses its declared suspended path. Failure is explicit and non-passing, never a silently missing entry. [LL01, LL13, LL15, LL20–LL22]

#### Tail calls and dynamic extent

Wasm tail-call validation requires compatible result types rather than equal parameter lists. The uniform result pair permits different argument counts, but emitted code must prepare the callee's arguments and release or relocate its own explicit frames and roots. Active bindings, handlers and UNWIND-PROTECT cleanup retain their required dynamic extent. Test growing and shrinking overflow, zero/many values, bounded stack/root use and preserved cleanup under long tail chains. A tail instruction does not perform Lisp-stack cleanup. [7, 12; LL05, LL19]

#### Measurement and decision rule

After all three candidates pass correctness, measure the fixed workloads with direct and indirect calls, closures, optional/rest/keyword binding, APPLY, multiple values, recursion, cross-arity tail calls and first-call installation. Keep cold and warm paths separate; record engine/version/tier, variation, root stores/reloads, code/adapter bytes, table slots, compilation/installation latency and per-Worker resources.

Each recommendation states its module granularity, eager/lazy boundary, weighted call distribution and Worker counts. Compare same-instance and cross-instance dispatch and test whether granularity changes the ABI ranking under the [product-risk plan](stage0/product-risk-plan.md). Stage 1 finalizes production packaging and repeats affected measurements if it changes the recommendation's basis.

Use stage0/benchmarks.json version 2 for the predeclared trial counts, confidence intervals and simplicity order. Freeze its digest and the representative workload/granularity matrix before selection measurements. Prefer the simplest candidate within the confidence-bound rule; record no selection if correctness, uncertainty or required product evidence is unresolved. Three arguments is a native precedent, not a privileged Wasm optimum. [18]

Artifacts: versioned C/C4/B ABI descriptions, generic-entry/stub metadata, the D7 correctness/rejection inventory and all 24 candidate/workload measurement records. Stage 1 repeats the chosen contract through generated code; hand-built results do not certify pass 2. Revisit the ABI when generated correctness or representative measurements overturn its recorded basis. [LL03, LL05, LL21, LL22]

## D4  /  RUNTIME IMPLEMENTATION LANGUAGE

### Retain the C kernel / emitted subprimitive split

#### Decision

Use a freestanding clang/wasm32 kernel with imported memory and table, no implicit libc/WASI environment and no independent libc allocator. Implement Lisp-callable subprimitives and G/E_k adapters through the Lisp Wasm emitter. Give C runtime entries explicit native-Wasm import/export signatures; ordinary calls to them use named imports. Reserve table slots only for entries that actually require indirect addressing, including C function pointers and Lisp-callable subprimitives. [9, 13]

This is a division of implementation responsibility, not a limitation that C cannot receive five scalar parameters. The documented Basic C ABI returns ordinary multi-field aggregates indirectly, unlike D3’s pair of Wasm results; adapters can bridge conventions. Their costs belong in the experiment. One emitted signature family per role remains under D3, not an unconditional requirement that all entries have C’s signature. [13]

| Kernel source or surface | Disposition / adaptation work |
| --- | --- |
| gc-common.c and architecture GC, including x86-gc.c | Audit reusable object-walking and weak-object logic. Replace native root/context discovery and native code-vector/return-address decoding; reconcile every walker with D1. Remove or disposition generational memoization for the initial collector. |
| image.c | Reuse applicable section/serialization logic; use loader-supplied bytes and the target ownership map. Native placement and unsaved host-state assumptions are not inherited. |
| memory.c; area management | Replace OS reservation/protection with checked target regions and memory growth. Use explicit stack/allocation bounds; no guard-page assumption. |
| thread_manager.c; TCR access | Replace native threads/signals with D5 rendezvous and lifecycle logic; define Worker-private C stack, TLS/current-TCR state and explicit roots. |
| Native exceptions and interrupted-sequence repair | Drop signal-context decoding and machine-instruction repair. Reimplement required Lisp checks, control restoration, debugger and callback semantics, not the native mechanisms. |
| spentry/subprimitive assembly | Replace with emitted Wasm implementations and typed adapters selected by D3. |
| pmcl-kernel.c, globals and imports.s | Loader parameter block, owned globals and a reviewed exact import/export inventory; complete the 65-entry census under D6. |

#### Memory ownership and implementation boundaries

One C module removes the particular two-module default-base collision only when all admitted ranges and initialization writes are controlled. It does not prevent reinitializing shared memory when that same module is instantiated in another Worker. Require process-once shared initialization, per-Worker setup, sentinels and the late-Worker mutation test. Inspect the actual linked binary’s initialization mechanism; the tool conventions describe synchronized passive-segment initialization for shared memory, but the chosen build must demonstrate it. [6, 14; LL13]

Provision a distinct linear C stack for each Worker, including required alignment, bounds and any ABI red zone. A private stack-pointer global does not imply a distinct backing region. Select the current TCR through a specified instance-private global, thread-local mechanism or explicit parameter, not an ordinary shared C global. C temporaries containing Lisp references use declared root slots and reload rules. [13; LL13, LL18]

Use fatal linker warnings and an explicit allowed-import inventory. LLD may otherwise warn about signature mismatches while generating trapping stubs. Validate exported/imported signatures and reject unintended unresolved or trapping replacements. A direct import is type-checked at instantiation, but its execution cost is measured rather than assumed lower than every indirect alternative. [9; LL01, LL21]

Specify how Lisp nonlocal transfer crosses each C helper boundary and restores C linear-stack/root state; do not assume ordinary C epilogues run during an exceptional exit. Freestanding builds still require a complete inventory of compiler-generated helpers and memory operations. Any permitted helper has an owner and implementation; missing helpers never become silent stand-ins.

#### Alternatives, artifacts and reversal

The freestanding C kernel / emitted subprimitive split is decided. It offers a source-based reuse path while keeping Lisp calling and control semantics in the emitter. An all-emitted kernel remains the alternative if adaptation and toolchain constraints prove costlier than a rewrite; an all-C subprimitive layer remains possible with suitable adapters. The proof harness tests the selected split against its ownership and boundary contracts.

Artifacts: per-file dispositions, link and initialization maps, allowed imports, exported names/types, per-Worker stack/TLS setup and unwind/root boundary contracts. Revisit the language split if the implementation cannot meet those contracts within measured budgets. No source file is declared unchanged merely from its name or original role.

## D5  /  PROTOCOL SPECIFICATIONS, VERSION 1.1

### TCR, GC admission, typed entries and mailbox ownership

#### Decision and TCR schema

D5 is decided as protocol v1.1. Use a process-wide aligned 32-bit atomic gc_gen, even when idle and odd while collection is requested or running, together with each TCR’s atomic state and pending word. The epoch-only re-entry rule is replaced by the owner-CAS and admission protocol below. [6, 18]

One TCR represents a Lisp thread in linear memory. Its field groups are thread/Worker identity and lifetime generation; atomic state and pending bits; allocation-area bounds; VSP/TSP/CSP and bounds; dynamic-binding-vector pointer; multiple-value descriptor; published root-frame/foreign-call descriptor; mailbox identity; and runtime-private stack/TLS descriptors. A TCR index and a symbol’s binding-vector index are different namespaces. Use explicit widths and alignments per field. The process-wide gc_gen is distinct from TCR/request lifetime generations. [LL07, LL17, LL18]

Classify each field as a tagged root, raw address, bounded index/count, atomic state or code/entry identifier. Define storage and update ownership. The multiple-value descriptor points to D3’s live VSP result region and its count; a separate backing buffer is not introduced implicitly. C and emitted layouts consume the same schema, with independent runtime fixtures.

| State | Meaning and admission rule |
| --- | --- |
| CREATING | The admitted RUNNING creator publishes the TCR and rooted handoff before the child can execute Lisp. Private setup does not confer heap rights; transition to PARKED with roots retained. |
| PARKED | No Lisp execution; live handoff/continuation state is rooted. Wake-up uses the admission loop before heap access. |
| RUNNING | May be a tentative admission probe or admitted heap execution. Only an even gc_gen observation authorizes the latter. A requested legal stop publishes roots and records STOPPED_GC. |
| FOREIGN | Published Lisp roots and stable request storage. Completion or an INTERRUPTED wake uses admission and root reload before result consumption or interrupt service; an outstanding request may then be waited on again. |
| STOPPED_GC | Roots remain published. Wait/recheck parity, then retry admission. A losing collection requester rechecks allocation need after admission. |
| TERMINATING | Unlink only through admitted lifecycle execution. Reclaim after a subsequent collection completes and every outstanding host request is completed or cancellation-acknowledged. |

#### Protocol v1.1 amendment — 11 September 2026

The integrated fixture exposed two lifetime defects (original failures r3 and r6). Claude’s external audit then exposed an exceptional return that left an idle Worker RUNNING (original failure r9). These findings amend protocol v1; the [evidence index](evidence/index.json) retains the originals and the [audit disposition](stage0/claude-review.md) distinguishes reviewed r8 from subsequent fixes.

- **Generation-guarded wake publication.** Represent the request wake and generation as one aligned atomic 64-bit pair: low 32 bits wake, high 32 bits lifetime generation. Host payload and result writes precede the durable terminal outcome; the outcome precedes the final wake and notification. A terminal outcome ends all ordinary host writes. A delayed final wake uses compare-and-exchange on the pair with the captured generation; it must reject a reused descriptor without writing it. Rearming clears only the low wake half atomically. Preparing or reclaiming storage advances the generation before reuse. Request/TCR lifetime exhaustion is rejected; it does not use the wrapping GC parity rule. Generation validation before an unguarded write is insufficient.
- **Active request versus outstanding ownership.** Each TCR has an explicit atomic active-request address (or zero). A nested wait saves the previous active address, publishes its own descriptor before entering FOREIGN, then restores the previous address on return or nonlocal cleanup. Interrupt delivery targets the currently active descriptor and generation; it must not select an older outstanding parent request. A zero address leaves an interrupt pending for the next admitted service point. All outstanding descriptors remain owned until terminal host acknowledgement, even when they are no longer active.
- **Idle host boundaries and lifecycle admission.** Every return from the outer emitted entry to idle JavaScript, including a caught nonlocal exit, restores checkpoints and publishes PARKED with roots retained before returning. Read the scalar result while admitted; JavaScript must not dereference returned Lisp references while idle. Retirement and other host-invoked lifecycle entries acquire admission before registry or heap access. A collector must complete between exceptional return and retirement without assistance from the idle Worker.

These mechanisms preserve the owner-CAS, root-publication and reclamation rules below. The v1.1 regression set includes stale final publication, wrong nested-descriptor routing, a host outcome published after its final wake, and collection while the exceptional-return Worker is idle. Missing notification and late-outcome controls use explicit waiter-count witnesses; they are not timeout-based semantic proofs.

#### GC ownership, admission and release

Marker ownership. Initialize gc_gen to zero once. All synchronization operations here are sequentially consistent. Acquisition is compare-and-exchange from an observed even generation g to g + 1; a failed CAS writes nothing. Only the successful owner may subsequently write the marker, releasing it by an atomic store of (g + 2) mod 2^32 after clearing GC-pending bits, then notifying waiters. Unconditional fetch-add is prohibited: a losing requester would turn the marker even while another collector still owns the world. [6, 18]

Admission from FOREIGN, PARKED or STOPPED_GC. Keep roots published throughout the tentative RUNNING probe. Between that store and observing an even gc_gen, the thread has no heap-access rights. On an odd observation it records STOPPED_GC, waits/rechecks until it observes even parity, and retries from the first store:

```text
admit(tcr):
  repeat:
    atomic_store(tcr.state, RUNNING)  // probe; roots retained
    g = atomic_load(gc_gen)
    if (g & 1) == 0:
      reload_roots_and_rederive_pointers(tcr)
      return                        // admitted
    atomic_store(tcr.state, STOPPED_GC)
    wait_until_even(gc_gen)          // recheck, then retry
```

Waiting and restoration. wait_until_even reloads the marker after every wake and uses the currently observed odd value as the atomic-wait expectation, avoiding a lost notification. Test parity, never “even and greater”; generation arithmetic wraps. An even observation ends the wait, not admission. After admission, reload tagged references in Wasm locals and C temporaries from the collector-updated root slots and re-derive raw/interior pointers. Roots remain published until that restoration is complete. [18; LL20]

Collection request. At its own safepoint, the requesting thread publishes its roots, loads gc_gen and attempts CAS only if the value is even. If it finds odd parity or loses CAS, it records STOPPED_GC, waits for even parity, retries admission and re-evaluates allocation/collection need; the completed collection may already satisfy it. A successful owner retains its own published roots and excludes itself from the wait for other RUNNING TCRs. For each other registered TCR, it atomically sets the GC-pending bit and then loads state, waiting for RUNNING threads to publish roots and stop. Pending-bit updates preserve unrelated interrupt bits. [18]

Membership closure. Only an admitted RUNNING creator may publish a new TCR, including its handoff roots; a child cannot execute Lisp before publication and admission. After all RUNNING participants found in the first pass have stopped, the collector enumerates the registry again. It includes children published during that pass, sets their pending bits and waits on any newly discovered RUNNING child, repeating the final scan as needed. Once all publication-capable threads are stopped, the final enumeration is complete and includes every handoff root. TCR removal follows the same admission rule. [18]

Collection and release. With membership closed and roots published, the owner collects. It then clears the GC-pending bits for the complete participant set, atomically stores the next even generation and notifies waiters. The owner also uses admission/root restoration before resuming mutator work, so a new collector arriving immediately after release is respected. Reclamation uses an explicit collection-completion safety condition, not ordinary ordering of the wrapping marker. [18]

Exclusion argument. In the sequentially consistent order, the thread’s RUNNING store precedes its generation load, and the collector’s successful even-to-odd CAS precedes its state load. For a collection that still owns the marker, either admission sees odd parity and stops or the collector sees RUNNING and waits; both observations are harmless. Owner-only writes preserve this parity invariant. Retrying admission covers a new request arriving after an even wake-up observation. S0-LL20-b exercises the selected protocol and its rejection cases. [6, 18]

#### Safepoints and explicit stacks

The initial safepoint policy polls at function entries, loop backedges and allocation slow paths; selected additional sites depend on measured time-to-safepoint. The shared pending word is accessed atomically. No poll occurs inside a declared no-safepoint allocation or store sequence. Record root publication/reload, stack bounds, and preservation of binding, handler and multiple-value state at each legal stopping boundary. Stage 1 forces collection only at legal boundaries, never by inserting a poll into an indivisible sequence. [LL06, LL18–LL20]

D3’s ordinary, tail and adapter transitions must state their VSP/TSP/CSP and root ownership. C stack provisioning is per Worker under D4. Runtime slow paths that can allocate, block or invoke Lisp are included in the stopping-boundary inventory, not treated as safe merely because their call is a direct import.

#### Logical code identity and typed entry slots

Retain process-wide monotonic logical code IDs through Stage 5 and defer reuse to Stage 6. Withdraw the unconditional equation code ID = table slot. For H, one code version may expose G plus several E_k entrypoints, each needing a different slot. Even a uniform baseline records an explicit mapping; equal numbers may be an implementation convenience, not an image ABI promise. [LL07, LL11, LL21]

Use checked tagged logical code IDs in 0…2^29 − 1, with recorded reservations and exhaustion failure. Table capacities and slot indices have separate checked bounds. A later unboxed u32 code-ID representation requires an explicit non-root field encoding and schema revision; a finite i32 namespace is never described as unbounded.

The manifest maps each (logical code ID, entry kind) to its structural signature key, table slot, module/template hash, profile binary identity, module-local function/export, ABI/layout versions, dependencies and debug record. Numeric Wasm type indices are module-local and are resolved from the structural signature key at emission/validation. Function objects reference code descriptors but retain separate environments and metadata; sharing code does not merge closures. [12; LL11, LL12, LL21, LL22]

Derive reserved C function-pointer slots from the actual link map. Named runtime imports consume no table reservation unless they are separately address-taken. Allocate subprimitive and Lisp entry slots from one checked process-wide entry registry; do not hard-code an unsupported 256/4096 partition. Table-growth chunk size is a measured policy. Each Worker has the same registry-to-slot mapping but its own installed function references.

For an allocated callable entry, install its signature- and role-correct stub or real function before first dispatch in that Worker. Unallocated capacity stays null/non-callable. The process-wide registry serializes ID/slot allocation and manifest publication; per-Worker first-use setup handles reentrant installation and failed publication explicitly. The producing Worker completes required installation before exposing the new definition; another Worker installs missing entries before dispatch. Old entries retain their signatures while old function objects remain live. [LL11, LL13, LL21]

#### Mailbox and lazy-install requests

A TCR-owned request block records opcode, payload schema, scalar arguments, stable byte-region identity/extent, request generation, an aligned atomic wake/generation pair, a durable atomic completion/cancellation outcome and result. One request may be outstanding per descriptor; callbacks or debugger nesting use another owned descriptor or explicit rejection. While admitted, the Worker prepares the request, publishes roots and atomically records FOREIGN, notifies the host and waits/rechecks. The full profile blocks on the status word; JSPI uses a promise for the same logical outcomes. Every resumption uses admission. [6, 18, 19; LL20]

Interrupt wake-up (R2). An interrupt request for a FOREIGN thread atomically sets its interrupt-pending bit, preserving the GC bit, stores the distinct INTERRUPTED wake status on that thread’s active request descriptor and notifies its status word. Setting the pending bit alone is insufficient. The waiter retains published roots, re-enters through admission, reloads moved references and services the interrupt before consuming a result or returning to the I/O wait. If the host request is still outstanding, it republishes roots, returns to FOREIGN and waits on the same descriptor; otherwise it observes completion or host-acknowledged cancellation. The descriptor and generation are not reused meanwhile. [19; LL20]

Wake/completion races. INTERRUPTED is a wake reason, not cancellation or a terminal host result. Keep the completion/cancellation outcome durable and separate so an interrupt-status store cannot erase a concurrent completion or acknowledgement. Claim the pending interrupt atomically before servicing it, preserving later interrupts and unrelated bits. Before blocking again, arm the wake word, re-read pending interrupts and the durable outcome, and wait with the observed pending status as expectation only when neither needs service. A concurrent interrupt or terminal host event must prevent blocking or wake it; a completion must not suppress an unserviced interrupt. [19; LL20]

Host ownership and reclamation. The host writes only the request block, including any owned stable byte payload, and notifies; it never accesses the Lisp heap. Request storage remains stable through collection and is not reused while an ordinary host write remains possible. A delayed final wake is permitted only through the generation-guarded pair, which cannot modify a reused descriptor. Completion validation checks TCR/request generations and lifetime. Cancellation means host acknowledgement that no further write will occur, not requester intent. Termination unlinks the TCR under admission; reclamation requires both a subsequent completed collection and completion or acknowledged cancellation of every outstanding request. An interrupt or a nonlocal exit from its handler does not authorize early reuse; retain any abandoned request until the host can no longer write it. [18, 19; LL20]

For code installation, D3’s stub preserves typed call state in rooted storage and obtains module bytes through the admitted mailbox/cache path. On completion, it re-enters via GC admission, reloads roots, validates and installs code without clobbering live shared state, and redispatches through its own signature and semantic role. Ordinary event-loop message delivery to the blocked Worker is not the correctness path. [LL13, LL20, LL21]

#### Artifacts and reversal

Artifacts: versioned TCR/root schema; owner-CAS/admission state transitions; code-ID and typed-entry manifest; mailbox ownership, interrupt-wake and cancellation contract; per-profile suspension specification; and deterministic interleaving tests. Revisit D5 if a protocol counterexample, required lifecycle case or measured progress/resource bound defeats its safety or liveness contract. Proof and implementation tests validate the decision; they are not prerequisites for recording it as decided. Production acceptance remains staged under the register. [18, 19]

## D6  /  SOURCE-ONLY CENSUS CLASSIFICATIONS

### Decided vocabulary and lowering; census and FP choice outstanding

#### Kernel import classification

Decision. Use the disposition vocabulary Wasm runtime, JavaScript host service, atomics/memory implementation, or explicitly unsupported, and the explicit trap-lowering rule below. The groups are a census worklist. Each of the 65 actual defimport spellings receives its own record, caller evidence, target/profile disposition, closure phase, implementation or replacement and regression ID. Keep direct foreign calls in a separate inventory. The complete census and floating-point compatibility choice remain outstanding. U1 is the inventory basis; historical H1 aggregate counts are not evaluated U1 results. contracts/census.md and contracts/census.schema.json define the graph and completion rule. [10, 18]

| Source entries / work group | Provisional treatment or unresolved point |
| --- | --- |
| xNewThread, xDisposeThread; suspend/resume and interrupt surfaces | D5 lifecycle/safepoint implementation. Audit callers and semantic replacements; safepoints do not prove that suspend/resume callers disappear. |
| Semaphores, recursive locks, rwlocks; lisp_futex | Shared-memory synchronization. Any single-thread simplification must preserve that profile’s actual locking, reentrancy and blocking semantics. |
| lisp_open/read/write/lseek/close, stat/fstat/lstat/realpath, directory APIs, ftruncate/fchmod, lisp_pipe | Host namespace and capability contract; pipe is provisionally unsupported. Record each exact entry and required caller separately. |
| lisp_malloc; lisp_free | Owned runtime/foreign-buffer allocation contract. Do not substitute a malloc/free/calloc/realloc quartet for the source inventory. |
| lisp_egc_control | Preserve the existing EGC-unavailable policy for the initial non-generational collector. |
| Native executable/shared-library/JVM entries; FP-context and vector-register helpers | Disposition individually. Include restore_fp_context as well as save_fp_context and put/get_vector_registers; preserve any required higher-level semantics or signal unsupported. |
| lisp_gettimeofday; lisp_sigexit; remaining entries | Host clock/process-lifecycle policy. Explicitly include register_xmacptr_dispose_function, restore_soft_stack_limit and other entries not resolved by this grouping. |

Source inspection supplies initial dispositions and caller locations; the compiler-mediated census resolves target conditionals, macros, front-end rewrites and reachable bootstrap effects. Keep unresolved entries in the worklist until classified. A shadow in level-1/WASM remains subject to R6, R4 and its semantic regression.

#### Trap lowering and recoverability

Lowering rule. Type, bounds, arity and unbound checks lower to explicit checks and the appropriate Lisp condition path; GC and interrupt events use their own runtime transitions. Retain native UUO/check sites, including the previously recorded 143 x86-64 vinsn occurrences, as an inventory to reconcile with evaluated lowering records, not 143 independent semantic classes. [11]

For each recoverable check, specify supplied condition data, available restart behavior, the resumed result/control contract and stack/root restoration. An ordinary call preserving activations is necessary infrastructure, not proof of recoverability. Required early bootstrap failures remain fatal until their supported condition path exists. Unexpected engine traps and resource failures receive structured fatal diagnostics; do not relabel all engine failures as Lisp conditions or assume every one proves a runtime coding defect. [LL01, LL19, LL23]

#### Floating-point hypothesis

The hypothesis remains to preserve required CCL floating-point conditions with explicit checks/helpers under the default policy, subject to the Stage 2 compatibility decision. Specify correct detection before benchmarking its cost. A result infinity alone does not distinguish finite overflow, division by zero and an existing infinite operand; a NaN can be propagated or newly produced by an invalid operation. Required operand/operation checks, rounding, literal encodings and the exposed condition policy must be stated. “One comparison per operation” is not an established cost. [16; LL10, LL16]

An unchecked path under safety 0 is a proposed compatibility choice requiring approval, not an automatic entitlement to change semantics. Benchmark the actual correct algorithms against a documented non-trapping alternative and record the policy decision, unsupported aspects and declarations explicitly. Performance data alone cannot silently withdraw R4.

#### Stub-backend edit plan, not an attached patch

Retain the proposed additive edit sites: backend registration; a new target architecture; lib/compile-ccl.lisp module lists and target clauses; lib/systems.lisp registrations; a target cross-fasloader derived from the x8632 precedent; and Wasm-specific level-0/level-1 files. Exact clauses, masks and module ordering must be checked against the pinned tree before applying a patch. Existing target clauses and acode identities are preserved under R6/R6a. [3, 8]

This record supplies an edit-site plan, not a prepared executable patch. The actual patch must identify its path, revision and digest, attach the baseline comparison recipe, and produce native FASL/behavior and evaluated acode-ID/flag comparisons after application. Preserve Gate 0 and ARM64 same-host results at their original evidence scope; second-host reproducibility is a separate test. [17; LL08, LL22]

#### Reversal criterion

Revise the vocabulary or lowering rule only if the census or a demonstrated semantic requirement shows that the selected categories or runtime condition/restart path cannot represent a required operation. Record the affected policy change explicitly under R4/R6. Census completion, implementation and floating-point measurements do not themselves reopen the decided vocabulary or lowering rule. [18]

## D7  /  BINDING LL OBLIGATIONS TO STAGE 0 TESTS

### Authoritative obligations, typed-call tests and negative controls

Decision. Use the register-derived ID and inventory scheme below. Acceptance Policy and Regression Register v1.5 is authoritative for first acceptance, extensions and continuing regressions; this section maps its Stage 0 slices and standing controls without creating a second stage schedule. All LL01–LL24 obligations remain in force. Stage 0 includes LL01, LL02, LL04, LL05, LL07, LL08, LL13, LL15, LL19–LL21 plus standing LL03 and LL22–LL24. [17, 18]

Use S<stage>-LL<nn>-<letter> with an evidence kind and pinned test revision. The JSON inventory lists mandatory IDs, profile/candidate variants, assertions and prerequisites for each experiment phase. Missing mandatory evidence is BLOCKED or NOT RUN, never PASS. H(G) is absent from the required candidate and measurement inventories.

#### Acceptance, representation and ABI

| Obligation / test ID | Required Stage 0 observation |
| --- | --- |
| LL01 S0-LL01-a/b | Fail early/middle/late initializers separately; reject partial bootstrap. Kill or time out a child process and require a non-passing aggregate with the failing step identified. |
| LL02 S0-LL02-a/b | Omit one required test ID and require BLOCKED. Mutate a returned value, capture or cleanup effect and observe the production gate reject the defect; quarantine mutant artifacts. |
| LL03 S0-LL03-a | Reject a hand-built or synthetic evidence record offered for compiler-generated acceptance. Label candidate, profile, substitution and exact artifacts independently of pass/fail. |
| LL04 S0-LL04-a/b | Compare schema with target-compiled C assertions and emitted probes. Independent unequal two-word CAR/CDR fixtures include mutation and NIL; inject a one-sided swap. Exercise dotted, nested, shared and cyclic fixtures where supported by the hand-built slice. |
| LL05 S0-LL05-a | For C, C4 and B: verify ordered arguments 0–6 and long overflow, nested side effects, direct/indirect/closure calls, APPLY and optional/rest/keyword binding, and every zero/one/many result. Check explicit stack/count ownership. |
| LL05 S0-LL05-b | Place different signatures in one table and call matching entries. Reject wrong-signature mutants; an isolated probe confirms trapping before stub entry. Also substitute G for E_4/E_5/E_1 where types coincide: role validation or semantic assertions must detect what the engine type check cannot. |
| LL05 S0-LL05-c | Force G and every supported E_k through their own lazy stub. Check eligibility/fallback for exact versus variable arity, preserve closure self and overflow space, and reload roots after allowed collection/suspension. |
| LL05 S0-LL05-d | Run generic cross-arity tail chains, shrinking/growing overflow and adapters. Observe bounded explicit-stack/root use, complete multiple values and preserved cleanup/binding extent. |
| LL07 S0-LL07-a | Check signed fixnum, raw address, logical-ID and typed-slot conversions separately. Synthetic addresses above 2 GiB retain bits through JS; checked exhaustion rejects invalid IDs and capacities. |
| LL08 S0-LL08-a/b/c | a: validate the actual registration patch in clean host sessions with target state set before reading. b: compare evaluated acode IDs/flags and reserved slots under R6a. c: repeat the pinned U1 macOS x86-64 baseline on a second host and compare retained digests under R6 normalization, separately from target-state proof and native behavior. This supersedes the unexecuted H1/E5 ARM64 reproduction slice because U1 lacks that backend; history/changes.md records the scope change. H1 evidence remains historical. |

#### Ownership, control, publication and standing controls

| Obligation / test ID | Required Stage 0 observation |
| --- | --- |
| LL13 S0-LL13-a/b/c | a: reject overlap/undersized ranges before publication. b: mutate shared state, then instantiate a late Worker and preserve it while initializing only owned private regions. c: concurrent C-helper activity uses distinct C stacks/current-TCR state; wrong initialization/stack-base mutants fail. |
| LL15 S0-LL15-a | Bind every harness initializer to prerequisite state and completion, including the loader’s own dependencies. An omitted required module fails loading; a no-load path cannot satisfy a load test. |
| LL15 S0-LL15-b | Validate the actual qualified-compiler joined census and conservative closure under contracts/census.md; include all phases, reviewed seeds, unknown edges, required initializers and external trace reconciliation. |
| LL15 S0-LL15-c | Independently specified missing-node/edge/seed, concealed unknown-call and cyclic initializer mutants must be rejected by the instrumentation and gate path. |
| LL23 S0-LL23-b | Prove frame order, lexical identities, source-site maps, unavailable-value policy, moved roots and frame restoration across suspension/nested debugging/EH under contracts/debug-frames.md. Reject stale-slot, generation and metadata mutants. |
| LL19 S0-LL19-a/b | a: EH through nested frames and cleanup that throws restores bindings, roots and VSP/TSP/CSP, preserves all values and suppresses post-exit effects. b: test the chosen emitted/C boundary and restart/result contracts explicitly. |
| LL20 S0-LL20-a | Suspend inside nested Lisp state, collect/install code and resume without suspension-triggered cleanup. Verify the same continuation, bindings and complete values. |
| LL20 S0-LL20-b | Deterministically schedule competing collectors, CAS loss, owner-only release, host completion, PARKED/STOPPED_GC admission, a new request during admission, parity wrap, final membership rescan, child handoff roots and allocation recheck. Fetch-add acquisition and omitted-rescan mutants must fail. Also park a FOREIGN Worker on an unfinished I/O request, interrupt it without completing the host operation, and require INTERRUPTED plus notification to reach interrupt service through GC admission/root reload. Resume waiting on the same descriptor or observe raced completion/cancellation acknowledgement. Include GC during wake, completion on either side of the interrupt store, and an interrupt during rearming. Pending-bit-only, omitted-notify, lost-terminal-outcome and premature-reuse mutants must fail. |
| LL20 S0-LL20-c | Stable request payloads survive GC. Interrupt handling, nested debugger requests and nonlocal exit do not reuse an outstanding descriptor. Cancellation without host acknowledgement cannot permit TCR/request reclamation; a late completion is checked against the original lifetime generation. |
| LL21 S0-LL21-a/b/c | a: publish prebuilt code and first-call from another/late Worker. b: map one code ID to G/E_k slots, fill new callable slots with matching stubs, reject conflicting signatures, preserve old function objects across a prebuilt redefinition. c: validate shared/unshared materialized binaries, import limits and profile suspension; reject wrong patch bytes/hashes/features. |
| LL22 S0-LL22-a/b | Bind implementation, test, ABI, template and materialized bytes to hashes; reject mixed builds and stale evidence. Run R6/R6a comparison for any applied shared-source edit; do not exclude an unexplained differing FASL wholesale. |
| LL23 S0-LL23-a | Structured diagnostics name the exact build, logical code ID, entry kind, signature, slot and faulting operation. Preserve the first error and bound output; a last-observed event is not labeled as the failing frame. |
| LL24 S0-LL24-a | One current ledger and separate history; explicit authorization for criterion changes; preserve earlier accepted evidence scope and link delivery claims to identified artifacts. |

#### Benchmark inventory and later repeats

The LL rows are supplemented by three explicit outline-exit records in stage0/inventory.json. S0-ENGINE-a qualifies the pinned engine/profile matrix including multivalue, tail calls, selected EH encoding, atomics, bulk memory and the profile's suspension path. S0-CONTRACTS-a reviews the complete versioned layout, frame, allocation/root/TCR, C-boundary and ownership contracts against their executed fixtures; the initial layout subset is insufficient. S0-ABI-selection records the complete ordered experiment, all measurement IDs from stage0/measurement-inventory.json, confidence intervals, resource budgets and the selected/rejected candidate rationale. None is replaced by passing a limited PROBE ID.

D3 benchmarks use 24 S0-ABI-<candidate>-<workload> identifiers linked to LL05/LL20/LL21 correctness prerequisites. Inventory phases are C/C4/B correctness followed by their baseline measurements. Record the candidate, adapter/stub counts, VSP/MV protocol, granularity, call distribution, engine/tier and budgets. Keep cold and warm paths separate. Correctness failure makes a candidate ineligible for selection. H(G) has no required inventory entry. [18]

Stage 1 repeats the chosen ABI, representation and initialization checks through compiler-generated code. The register’s Stage 2 lifecycle/GC and Stage 3 live-compilation/redefinition extensions remain distinct from the prebuilt harness cases. Stage 5 verifies retained entry descriptors and code variants after fresh restoration. D3 selection, the source census, floating-point choice and test work remain on the outstanding-work ledger; the decided architecture and D5 protocol supply their build target.

#### Reversal criterion

Revise D7’s scheme only for a demonstrated conflict with the register’s authoritative obligations or an identifier/provenance ambiguity it cannot represent. Preserve test history with explicit supersession mappings and regenerate dependent inventories; implementation delay or an unrun test does not reopen the scheme. [18]

## REFERENCES

### Source basis and provenance

U1 is c994217adc56b3f8a564526cee4695893ac84d86. Historical upstream source links below retain H1 4ca4df402e319789401cd33e680702e51ec601fc where they record earlier inspection; they do not override U1. D1 layout references [1–3] are repinned to U1, whose referenced files were inspected. Requalify other edit sites and census claims before implementation. Outline v0.15, register v1.5 and this decision record form the coordinated document set. Specification/toolchain references retain their prior recorded basis; no new engine qualification is claimed. Reference [18] dates the agreement’s confirmation, and [19] dates this exchange’s corrections; neither is a file-creation timestamp.

[1] x8632 architecture data and execution layouts Tag constants, widths, canonical NIL/T, cons ordering and native execution-layout exceptions. [x8632-arch.lisp](https://github.com/Clozure/ccl/blob/c994217adc56b3f8a564526cee4695893ac84d86/compiler/X86/X8632/x8632-arch.lisp)

[2] C cons layout and accessors CDR then CAR in struct cons; untagged field access. Constructor order is a separate Lisp contract. [constants.h](https://github.com/Clozure/ccl/blob/c994217adc56b3f8a564526cee4695893ac84d86/lisp-kernel/constants.h) · [macros.h](https://github.com/Clozure/ccl/blob/c994217adc56b3f8a564526cee4695893ac84d86/lisp-kernel/macros.h)

[3] 32-bit cross-loader and ARM comparison Cross-loading precedent and alternative fulltags; no adoption of native architecture conditionals by implication. [xx8632-fasload.lisp](https://github.com/Clozure/ccl/blob/c994217adc56b3f8a564526cee4695893ac84d86/xdump/xx8632-fasload.lisp) · [arm-arch.lisp](https://github.com/Clozure/ccl/blob/c994217adc56b3f8a564526cee4695893ac84d86/compiler/ARM/arm-arch.lisp)

[4] WebAssembly core: memory instructions Address arithmetic and nonnegative memarg offsets. Engine optimization costs are not specified. [Core specification](https://webassembly.github.io/spec/core/bikeshed/)

[5] WebAssembly memory limits encoding The admitted wasm32 explicit-maximum unshared/shared encodings; exact transforms require validation. [Threads: limits and memory types](https://github.com/WebAssembly/threads/blob/main/proposals/threads/Overview.md#spec-changes)

[6] WebAssembly threads Atomic access, wait/notify distinctions, shared-memory initialization and the host-facing synchronization basis. [Threads overview](https://github.com/WebAssembly/threads/blob/main/proposals/threads/Overview.md)

[7] WebAssembly tail calls and multiple results Tail transfers use the callee signature and compatible result types; linear-memory Lisp-stack ownership remains an implementation contract. [Tail-call overview](https://github.com/WebAssembly/tail-call/blob/main/proposals/tail-call/Overview.md) · [Core validation](https://webassembly.github.io/spec/core/bikeshed/)

[8] CCL backend and native pass 2 Native argument-register conventions are comparison evidence, not a Wasm parameter limit. [backend.lisp](https://github.com/Clozure/ccl/blob/4ca4df402e319789401cd33e680702e51ec601fc/compiler/backend.lisp) · [x862.lisp](https://github.com/Clozure/ccl/blob/4ca4df402e319789401cd33e680702e51ec601fc/compiler/X86/x862.lisp)

[9] LLVM WebAssembly linker Import/export and memory/table options; signature-mismatch warnings and trapping stubs; strict link policy. [LLD WebAssembly documentation](https://lld.llvm.org/WebAssembly.html)

## REFERENCES  /  CONTINUED

### Kernel, ABI and project-document sources

[10] Kernel adaptation and exact imports Portable and architecture-specific collector work must be audited together; imports.s is the exact census source. [gc-common.c](https://github.com/Clozure/ccl/blob/4ca4df402e319789401cd33e680702e51ec601fc/lisp-kernel/gc-common.c) · [x86-gc.c](https://github.com/Clozure/ccl/blob/4ca4df402e319789401cd33e680702e51ec601fc/lisp-kernel/x86-gc.c) · [image.c](https://github.com/Clozure/ccl/blob/4ca4df402e319789401cd33e680702e51ec601fc/lisp-kernel/image.c) · [memory.c](https://github.com/Clozure/ccl/blob/4ca4df402e319789401cd33e680702e51ec601fc/lisp-kernel/memory.c) · [thread_manager.c](https://github.com/Clozure/ccl/blob/4ca4df402e319789401cd33e680702e51ec601fc/lisp-kernel/thread_manager.c) · [imports.s](https://github.com/Clozure/ccl/blob/4ca4df402e319789401cd33e680702e51ec601fc/lisp-kernel/imports.s)

[11] Native trap/check lowering inventory Previously recorded x86-64 UUO/check occurrences remain a worklist to reconcile with evaluated census records. [x8664-vinsns.lisp](https://github.com/Clozure/ccl/blob/4ca4df402e319789401cd33e680702e51ec601fc/compiler/X86/X8664/x8664-vinsns.lisp)

[12] WebAssembly heterogeneous function tables and call-site types Core control instructions and call_indirect / return_call_indirect validation. A static expected type belongs to the call site; incompatible table entries trap before entry. [Core: control instructions](https://webassembly.github.io/spec/core/syntax/instructions.html) · [Core: validation and execution](https://webassembly.github.io/spec/core/bikeshed/)

[13] WebAssembly Basic C ABI Scalar versus aggregate parameter/result passing; address-taken locals and the linear C stack. [BasicCABI.md](https://github.com/WebAssembly/tool-conventions/blob/main/BasicCABI.md)

[14] WebAssembly linking conventions Process-once initialization with passive segments and per-thread storage conventions; verify the actual linked output. [Linking.md](https://github.com/WebAssembly/tool-conventions/blob/main/Linking.md)

[15] Common Lisp ordinary lambda lists and calls Required, optional, rest and keyword arguments; FUNCALL/APPLY semantics. A supplied count does not determine callee convention. [Lambda lists](https://www.lispworks.com/documentation/HyperSpec/Body/03_da.htm) · [FUNCALL](https://www.lispworks.com/documentation/HyperSpec/Body/f_funcal.htm) · [APPLY](https://www.lispworks.com/documentation/HyperSpec/Body/f_apply.htm)

[16] WebAssembly numeric semantics Floating-point operation and operand cases; result classification alone is not a CCL condition policy. [Core numerics](https://webassembly.github.io/spec/core/exec/numerics.html)

[17] Coordinated project-document authority Port Outline v0.15; Acceptance Policy and Regression Register v1.5; Stage 0 Desk Decisions v1.6. The outline owns architecture scope, the register owns acceptance and obligation metadata, and this record owns D1–D7 choices and protocols. Source inputs are identified below.

[18] Agreed decision amendments, reaffirmed 11 September 2026 Project exchange confirming the v1.2 agreement: decided statuses and reversal criteria; owner-only CAS acquisition and atomic-store release; parity admission/root reload; final membership rescan; host-acknowledged cancellation; and the then-current baseline-first incremental H(G) accounting, superseded by the user’s later instruction to make H(G) optional future work. The date identifies the confirmation exchange, not this file’s revision or an inferred earlier message timestamp.

[19] Interrupt-wake and companion consistency corrections, 11 September 2026 Project exchange requiring wake-up of a FOREIGN I/O waiter through INTERRUPTED status and notification, admission before interrupt service, retention of its outstanding descriptor, a S0-LL20-b schedule, conditional G/E_k stub wording, separate logical IDs and slots, and corrected revision/exchange dates.

#### Input identity

The complete original v0.12/v1.2/v1.3 input files and their SHA-256 digests are retained in history/2026-09-11-inputs and history/inputs.json. That preserved v1.3 decision record contains the earlier v0.11/v1.1/v1.2 input hashes. New DOCX reading copies are generated from the current Markdown; tools/manage.py checks both source and generated identities.
