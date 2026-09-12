DESIGN NOTE  /  VERSION 0.17  •  11 SEPTEMBER 2026

# Clozure Common Lisp to WebAssembly

High-level porting strategy and delivery outline

#### Recommended direction

Treat Wasm as a new CCL architecture whose effective seam is the existing target abstraction above pass 2. Reuse the target-neutral compiler front end and cross-dump machinery; implement a complete Wasm pass 2/vinsn layer together with the generated-code ABI, primitive/subprimitive layer and target runtime. One Lisp process owns one shared wasm32 linear-memory heap; each Lisp thread executes in a Web Worker.

Version 0.17 replaces v0.16 and accompanies acceptance v1.7 and decisions v1.8. The bounded C/C4/B correctness protocol now has an executable corpus; its eighteen correctness records are independently reviewed and accepted at their stated bounds. R7 binds execution records to per-test contracts and the inventory version, retaining original whole-inventory hashes as provenance. The required D3 candidates are C/C4/B; H(G) is optional future work. Module granularity and startup costs join the ABI measurement plan. macOS is the sole reference host for this Wasm project. The native baseline and external census trace use macOS; no alternate operating-system qualification is required. D5 protocol v1.1 records generation-guarded host wakes, nested active-request routing and parking at idle host boundaries. D3 remains open. Runtime acceptance remains evidence-scoped. [D]

| Document | Content |
| --- | --- |
| This outline, v0.17 | Architecture, decisions, contracts, delivery stages and provenance. The authority for what is being built and why. |
| Acceptance Policy and Regression Register, v1.7 | R7 gate rules, evidence kinds and record schema, R6 normalization policy, sources and LL01–LL24. Individual obligation metadata is authoritative; stage lists and the index are derived. |
| Stage 0 Desk Decisions, v1.8 | D1–D7 selections, reversal criteria and protocol details; D3 remains the open ABI choice. The decided contracts are build targets, not claims of executed proof. |
| Evidence records E1–E5 | E1, E2 and E5 identify execution packs; E3 is a status record. E4 is conversation-recorded syscall evidence; its archived trace pack is pending. |

#### Requirements

| ID | Requirement |
| --- | --- |
| R1 | Shared-heap threading is mandatory in the full profile. |
| R2 | Compile, load, redefine, interrupt, debug and inspect inside the running Lisp process. |
| R3 | Save quiescent persistent state and restore it as a fresh independent process. |
| R4 | Preserve Common Lisp and documented CCL semantics where supported; signal unsupported operations explicitly. |
| R5 | Measure architecture and performance decisions against explicit baselines before freezing them. |
| R6 | Do not modify existing target-specific implementation code. Shared changes needed for Wasm are additive. Existing-target ABI and behavior and generated output for unchanged native-target inputs remain unchanged under regression tests. Intended shared-compiler artifact changes are reviewed separately under acceptance section 2; they are never normalized away. |
| R6a | Preserve acode operator identity mechanically. Existing *next-nx-operators* slots, including reserved and retired slots, are never inserted into, deleted, reordered, compacted or reused. New operators are appended in source-table order so evaluated operator IDs and flags remain unchanged. |
| R7 | Evidence-based acceptance. A milestone passes only when required behavior is demonstrated by identified tests against identified artifacts; diagnostic continuation, synthetic fixtures, skipped tests and unimplemented substitutes cannot satisfy the requirement they bypass. Gate rules are in the companion document, section 1. |

#### Implementation baseline and evidence scope

U1 is upstream v1.13 at `c994217adc56b3f8a564526cee4695893ac84d86`, matching this checkout. H1 is `4ca4df402e319789401cd33e680702e51ec601fc`, the source of the previous inventories and E1–E5 reports. The revisions differ across 194 files, including substantial ARM64 and shared-source changes. H1 is reference material; its build results and recipes do not qualify U1. Current macOS Gate 0 execution is tracked separately from the still-unexecuted evaluated U1 census. See [baseline](stage0/baseline.json), [evidence index](evidence/index.json) and [current status](STATUS.md).

#### R6 reproducibility baseline

Historical H1 generated code was compared at the FASL level, not by heap-image byte identity. The following E1/E2/E5 results are reported historical evidence whose packs are unavailable in this checkout; they are not a U1 baseline. Two consecutive same-host clean rebuilds of x86-64 produced 163 identical FASLs out of 164; bin/compile-ccl.lx64fsl differs and its cause is uncharacterized. Two consecutive same-host ARM64 cross-compilations produced 126 identical FASLs out of 126. Same-host repeatability, cross-host reproducibility and native behavioral validation are distinct evidence kinds; the normalization policy for a differing file is in the companion document, section 2. This revision does not rerun or reset previously accepted gates. [E1, E5]

#### Retained changes introduced in Version 0.12

Adds interrupt wake-up for FOREIGN I/O and its acceptance schedule; replaces epoch-only re-entry with the agreed admission protocol; makes ID/entry-slot mapping and lazy stubs conditional on D3; and aligns D1, D2 and D4 selection wording with the decision record. Revision dates are separate from retained evidence dates. Continuing regressions, CDR-before-CAR, all LL obligations and E4’s pending trace-pack status are preserved. [D]

#### Retained changes introduced in Version 0.10

- Acceptance policy, evidence schema, R6 normalization policy and Appendix A moved to the companion register; stages cite obligations by LL identifier.

- The cons-layout contract generalized to an object-layout schema covering every header, subtag, tag and offset, with cons as the worked example (02).

- Runtime implementation language made an explicit Stage 0 decision instead of an assumption carried in vocabulary (02).

- File-system contract added with the measured native cold-start profile (05, E4).

- Module memory-import type and profile portability made an explicit emitter decision (04, 07).

- Handler counts stated in one kind: forms and distinct names for both x86-64 and ARM64 (01).

- ARM64 cross-compilation recipe and digests cited as executed evidence (08, E5); remaining targets marked pending their interface databases.

## 01  /  SOURCE-DERIVED PORT BOUNDARY

### Where the seam is

nx0, nx1, nx2 and acode-rewrite are retargeting candidates. Reuse is the default, subject to U1 census results and R6. Absence of target reader conditionals does not establish full neutrality: nx1 contains backend-name dispatch for foreign calls, nx0 partitions argument forms using backend-num-arg-regs, and acode-rewrite contains explicit architecture cases. The stub-backend plan must disposition these extension points without changing existing-target semantics.

CCL's backend is an architecture pass 2, not a thin instruction selector. Wasm needs a complete pass 2 for roughly the full acode operator surface, a Wasm vinsn layer, target metadata, low-level primitives and runtime support.

| Layer | Treatment |
| --- | --- |
| Shared front end | Reuse nx0/nx1/nx2/acode-rewrite. |
| target-arch and backend | Add Wasm through additive extension points: a target-arch, a backend record, module lists and cross-fasload registration. |
| Pass 2 | New Wasm implementation driven by the evaluated U1 acode table and per-operator mapping. Historical H1 source counts were 268 declared names, 231 x862 forms / 217 names and 221 arm642 forms / 211 names. These are reference counts, not U1 census results or a Wasm implementation count; U1 lacks arm642.lisp. |
| vinsns | New lowering for calls, allocation, stores, checks, safepoints and runtime entries. |
| Architecture level-0 and LAP | New Wasm equivalents or portable-Lisp replacements; existing target directories are not edited. |
| Subprimitives and runtime | New Wasm target code designed jointly with generated code. |

Historical scale calibration: H1's ARM64 target is roughly 50,000 lines of target-specific compiler, level-0 and kernel code before fasload and level-1 glue. Wasm reuses the shared front end but must replace what ARM64 receives from registers, native stacks, signals and OS threads.

Implementation boundary. The earlier attempt is audited as a separate historical tree, not as the clean upstream baseline. Its fixtures, diagnostics and individually reviewed components may be reused only after independent validation under the obligations they inherit. A diff against an unrelated branch or merge base is not a port-only change inventory. [P1, U1; companion section 3]

## 02  /  TARGET EXECUTION CONTRACT

### The indivisible target unit

The target-specific unit is pass 2 + generated-code ABI + vinsns + primitives/subprimitives + runtime. Allocation, runtime checks, GC entry and mutation policy are compiled into ordinary functions.

#### Dynamic-call ABI: Stage 0 decision

D3 remains open among C, C4 and B, selecting one uniform generic Lisp-call protocol. H(G) is only a possible future enhancement; it does not gate any scheduled stage. A function table may contain heterogeneous signatures: call_indirect checks the call site’s expected type, not a table-wide Lisp signature. D3 fixes argument/count placement, closure self, overflow and zero/one/many values, and entry/stub protocols. Native three-register convention is evidence, not a Wasm requirement. [D, D3; LL05]

#### Runtime implementation language: decided

D4 selects a freestanding clang/wasm32 kernel for the runtime and Lisp-emitted Wasm for the Lisp-convention subprimitive layer. The kernel imports memory/table and has no implicit libc/WASI environment or independent libc allocator; generated Lisp reaches runtime exports through named imports. The all-emitted runtime remains a reversal alternative, not an equally open initial selection. [D, D4]

| Selection / alternative | Consequences |
| --- | --- |
| Selected: freestanding C kernel + emitted subprimitives | Two toolchains; explicit allowed helpers/imports, strict linking and owned static/BSS/allocator regions. Per-Worker C stacks and current-TCR state are mandatory. Adapt reusable portable and architecture-specific GC/image logic; named imports and actual C function-pointer reservations follow the link map. [D, D4] |
| Reversal alternative: all-Lisp-emitted runtime | One emitter and no C toolchain; collector/image logic must be implemented through it. D1 layouts, D3 call/entry contracts, ownership and independent fixtures still apply. Reconsider only under D4’s recorded reversal criterion. |

Stage 0 tests the selected split and ownership/unwind boundaries; evidence may trigger D4’s reversal criterion but is not a prerequisite for recording the choice. Process-once initialization, per-Worker stack/TCR isolation, explicit root restoration and fatal link/import failures remain required. Memory ownership in 03 and entry reservations in 07 apply to either implementation. [D, D4; LL13]

#### Contract statements

- Every allocation sequence follows the target allocation protocol and slow path.

- Every potentially barrier-sensitive pointer store lowers through a replaceable Wasm vinsn/primitive.

- Every native type/tag/bounds/arg-count/unbound trap class has an explicit recoverable Wasm lowering.

- Live Lisp references in Wasm locals are published before legal GC stops or allocating transitions.

- Foreign transitions obey the TCR state contract.

- Dynamic calls use process-wide code identity and the Stage 0-selected ABI.

Stage 0 generates a machine-readable dependency graph for the percent-primitives used by portable level-0 and extends it through level-1 and lib. Source-derived aggregate counts are provisional until the native compiler census resolves reader conditionals, macroexpansion, front-end rewrites, vinsn/LAP/subprimitive lowering and bootstrap reachability. High-level bignum algorithms remain portable Lisp; digit primitives are target work.

#### Object-layout schema

One versioned schema defines every tag, header, subtag, field offset, alignment and size for the target word size W, in two coordinate systems: raw object base and tagged pointer. The compiler, runtime primitives, cross-loader, image writer and reader, GC walker and JavaScript inspectors all consume that schema. For a C runtime, target-compiled sizeof/offsetof assertions check the generated constants. For a Lisp-emitted runtime, target-executed layout probes check them; a C cross-check is optional, not a hidden C dependency. Both alternatives must pass the same independently specified byte fixtures with unequal field values. A writer/reader round-trip alone is not validation: two reversed helpers can agree and both be wrong. [LL04, LL07, LL10]

Cons is the worked example because the earlier attempt got it wrong repeatedly. The pinned C layout is struct cons { LispObj cdr; LispObj car; }: CDR is the first word and CAR the second, while the constructor remains (cons car-value cdr-value). Constructor argument order is never inferred from storage order, and storage order is never inferred from the spelling of the accessors. [U1, U1a]

| Field | Raw object base B | Tagged cons pointer P |
| --- | --- | --- |
| CDR | B + 0 | P + (0 − T) |
| CAR | B + W | P + (W − T) |
| Object size | 2 × W bytes | P = B + T; T is the cons tag |

For the D1 x8632-derived data scheme, W = 4 and the cons tag T = 1: CDR is at B + 0 or P − 1; CAR is at B + 4 or P + 3. Native execution-state layouts are replaced explicitly, not inherited wholesale. CAR/CDR of canonical NIL return NIL through its defined representation, while CONSP distinguishes NIL and RPLACA/RPLACD reject mutation of NIL as an ordinary cons. Cons slots are direct fields, never list indexing. The schema contract extends to every object and immediate representation. [D, D1; LL04]

#### Representations and compiler invariants

Distinguish tagged Lisp values, raw memory addresses, byte offsets, element indices, logical code IDs and callable table slots. Specify boxing, unboxing, sign extension, range checks, header addressing, NIL/T and unbound markers, string element widths, specialized-vector subtags and numeric payloads. A raw address is not a fixnum merely because both travel in an i32. Host numeric widths, package nicknames and cached macros are never target definitions. [LL07, LL08, LL10]

Argument order and arity are verified at every direct, dynamic, primitive, closure, overflow-argument and foreign boundary. Temporary-local ownership, lexical lifetime, left-to-right evaluation and preservation across nested calls, allocation and nonlocal transfer are tested before bootstrap breadth. The earliest violated compiler invariant is fixed; portable algorithms are not rewritten around wrong code generation. [LL05, LL06]

## 03  /  MEMORY, GC, SAFEPOINTS AND STORES

### Heap, collector and safepoint contract

Baseline heap: shared wasm32 WebAssembly.Memory with explicit CCL object layouts. Image persistence is the decisive reason to prefer linear memory over WasmGC: a known linear-memory graph serializes and restores directly, while engine-managed WasmGC objects need graph reconstruction. WasmGC is revisited if engines provide snapshotable heap semantics compatible with CCL images. Memory64 is later.

GC is compiled into the program. A no-collection bootstrap mode may reserve a large heap or inhibit collection, but only defers reclamation; it is a debugging aid, never an exit criterion. [LL18]

Safepoints are new Wasm compiler semantics. Native CCL uses asynchronous suspension and instruction repair; Wasm pass 2 emits cooperative polls. Polls are never placed inside allocation or designated store sequences, so there is no interrupted-sequence repair rule.

- Poll at selected function entries, loop backedges and measured additional points.

- Publish all live Lisp references before a stopping poll.

- Treat allocation and designated store sequences as no-safepoint regions.

- Force GC at every legal allocation/safepoint boundary in test builds.

- Measure and bound time-to-safepoint.

Stage 1's non-generational stop-the-world collector needs no generational write barrier. Stage 0 proves only that potentially relevant stores pass through a replaceable lowering; initially it may emit a plain store. CCL's refbits algorithm is not inherited; the Wasm barrier is designed together with a later generational collector. lisp_egc_control preserves CCL's existing behavior for a target on which EGC is unavailable; Stage 1 does not invent a new generational-control policy.

Memory ownership. Emit a checked map of every module's static data and BSS, any C stacks and allocator arenas, per-thread Lisp stacks, TCRs, heap regions and image staging buffers, and map callable entry slots separately from logical code IDs, deriving C function-pointer reservations from the link map and allocating other slots through the process-wide registry. Validate ranges, alignment and initialization writes before publication; read authoritative linker exports or emitter metadata for the selected layout. A fixed gap or a guessed stack pointer is not proof of heap safety. [LL13]

Initialization ownership. Active data segments are applied on every instantiation, including in a newly created Worker. Disjoint module ranges alone do not protect already-live shared state. The installation protocol separates process-once shared initialization from per-Worker setup and prevents later instantiations or start functions from repeating shared data/BSS writes. A late Worker must preserve mutated heap/runtime sentinels and published code; intentional per-Worker writes stay in that Worker’s owned region. Stage 0 proves this in the hand-built harness, Stage 1 checks generated installation, and Stage 2 repeats it with production Worker creation. [17; LL13]

A larger heap is not a collector proof. Stage 1 forces real collection with a small heap, verifies reclamation as well as survival, and checks roots in Wasm locals, explicit stacks, runtime temporaries, closures, multiple-value state, module constants and runtime registries. Invalid tag-like words must not become roots accidentally. Legal high-address and memory-growth boundaries are tested and host views refreshed according to the selected memory protocol. Test safepoints are never inserted inside no-safepoint regions. [LL18, LL07]

## 04  /  THREADS, HOST SUSPENSION AND DEPLOYMENT

### Workers, suspension and profiles

Shared-heap threading is a hard requirement (R1), not a Stage 0 tradeoff. If a mechanism fails, the mechanism is replaced; shared Lisp identity is not abandoned.

Full-profile host suspension uses an Atomics.wait mailbox. A Worker publishes roots, enters FOREIGN, posts a request to the microkernel and waits on its stable request status. Completion or interrupt wakes it; every resumption uses D5’s admission loop and reloads roots before Lisp/heap access. The single-thread non-isolated profile uses JSPI over asynchronous JavaScript with the same logical request outcomes. Asyncify and explicit continuations are not baseline. The main thread never runs Lisp. [D, D5; LL20]

Admission contract. Only successful even-to-odd CAS acquires gc_gen; the owner alone clears GC-pending bits, stores the next even generation and notifies. A returning thread probes RUNNING with roots retained, reads parity and either enters with root reload or records STOPPED_GC, waits on the observed odd value and retries. The collector closes membership with the final rescan. Lifecycle reclamation also requires a completed collection and host completion or acknowledged cancellation. [D, D5; LL18, LL20]

Interruptible I/O (R2). An interrupt on a FOREIGN thread sets its interrupt-pending bit, stores INTERRUPTED in the active request’s wake/status word and notifies it. The waiter uses admission, services the interrupt and either waits on the same still-outstanding descriptor or observes completion/host-acknowledged cancellation. Wake status is separate from the durable terminal outcome; rearming rechecks both the pending bit and outcome to prevent lost wakes. The descriptor is not reused while the host can still write it. S0-LL20-b includes this schedule. [D, D5/D7; LL20]

| Profile | Requires | Provides |
| --- | --- | --- |
| Full / reference | SharedArrayBuffer with COOP/COEP; Wasm exception handling. JSPI optional. | Several shared-heap Lisp threads, Atomics mailbox I/O, break loops, interactive compiler and debugger. |
| Single-thread JSPI | Wasm exception handling; JSPI. No COOP/COEP. | One Lisp thread with the same object/image ABI; thread creation signals unsupported. |
| Precompiled callback | Wasm exception handling only. | Compiler-light, callback-driven applications; not full interactive Lisp. |

Module materialization is decided by D2: one canonical explicit-maximum Lisp-code template deterministically produces the shared/unshared profile-specific binaries, with the runtime built for its selected suspension profile. A template is not universally instantiable, and a shared-flag change alone is not portability proof. Stage 0 verifies the transform; Stage 1 confirms it before the first cross-dump; Stage 5 qualifies saved and resident-compiled paths. Separately emitted variants remain D2’s reversal alternative. [D, D2; 17; LL21]

Materialization contract. Record the template or source-module hash, materializer/emitter version, target profile, feature requirements, memory minimum/maximum and the resulting binary hash. Validate the resulting binary, import types and limits before instantiation; qualify the suspension path in profile tests. Never patch a compiled WebAssembly.Module or use the template hash as the installed-binary identity. Missing variants and unsupported transformations fail explicitly. The Stage 1 experiment validates the selected materialization and its variants; Stage 5 qualifies the complete profiles without implying that both runtimes already exist in Stage 1.

Shared memory requires an explicit maximum. Atomic loads, stores and read-modify-write operations may use unshared memory, but Wasm wait instructions trap there. Profile tests therefore check limits, growth and the selected mailbox or JSPI suspension path, not just instantiation. The unshared profiles must not reach a shared-memory wait path. [17; LL20, LL21]

Engine qualification records engine and version, exception-handling encoding and JSPI API shape independently. The Node 22 / V8 12.4 probe results are historical environment evidence only; the target matrix is rerun on current engines using the standardized WebAssembly.Suspending / WebAssembly.promising API and the final exception-handling encoding. The full profile's COOP/COEP requirement constrains hosting and cross-origin embedding; live compilation also requires a CSP permitting WebAssembly compilation.

Dynamic state is not optional in a one-thread bring-up. Compiled special-variable access, SYMBOL-VALUE, setters, binding lookup and unbinding agree on the active dynamic binding; one thread does not justify replacing binding-stack/TLB semantics with global-cell access. Full-profile atomics and lock semantics remain explicit; any single-thread simplification is confined to a proved single-thread stage or profile. [LL17]

A stepping API or a successful request enqueue does not prove suspension and resumption. Tests suspend inside nested bindings, handlers and cleanup contexts, permit GC and code installation, then resume at the correct continuation with the right values; suspension alone never executes unwind cleanup. Worker creation, FOREIGN re-entry, interruption and termination participate in the same lifecycle/GC protocol. [LL20]

## 05  /  KERNEL AND HOST SURFACES, IDENTITY, FILE SYSTEM, FLOATING POINT

### What the host must provide

The host contract is derived from the source census: the kernel import table, UUO/trap classes, subprimitives and direct foreign calls. Source inspection finds 65 defimport forms in both U1 and H1; the reported 266 level-1 and 141 lib/library direct foreign-call counts belong to H1 and must be re-enumerated for U1.

| Surface | Treatment |
| --- | --- |
| Kernel imports | Classify each as Wasm runtime, JavaScript host service, atomics/memory implementation, or unsupported. |
| UUO/traps | Replace with Wasm control flow, exception handling, runtime call or host transition; preserve GC and image-save semantics. |
| Subprimitives | Implement as Wasm functions, vinsns or runtime entries under the target ABI. |
| Direct foreign calls | Classify libc/libm/file/socket/thread calls as Wasm operations, host imports, Lisp rewrites or unsupported. |

The Lisp process is the object-identity, shared-state and trust boundary. Workers share ordinary Lisp objects; modules do not isolate code. Untrusted code requires separate processes and memories.

#### File-system contract

The native cold start is file-driven. The earlier attempt reported an open() shim defeated by a data-segment collision and failures inside FASL loading. This design delivers the bootstrap heap and code set through the loader, removing the legacy FASL-driven cold-boot path and its particular load-order dependency. It does not eliminate segment collisions, incomplete loader dependencies or invalid loaded objects. Runtime LOAD of source and precompiled bundles, and loading newly compiled bundles, remain requirements. [P2, P8; LL13–LL15]

The earlier E4 cold-start profile is preserved in [historical evidence](history/pre-macos-evidence.md). It is unverified historical context and does not specify host paths or services for the Wasm runtime. Reconcile a fresh macOS cold-start trace under the [census contract](contracts/census.md). [E4]

| Capability | Contract |
| --- | --- |
| Read-only namespace (Stage 1) | Named byte sources with stat (size and kind), open, positioned read and close, served through the mailbox in the full profile. Enough for the loader's manifests and for LOAD of source and precompiled bundles. |
| Path semantics (Stage 1) | realpath as a pure function over the virtual namespace with no symlinks; a host-supplied current directory and ccl: root. probe-file and truename resolve against that namespace only. |
| Interface database (Stage 1) | Not loaded in the Wasm profile: native #_ resolution is out of scope, so foreign-types initialization must not require the .cdb files. If a later profile needs them, they are named blobs. |
| Writable store (Stage 3) | compile-file and save-application need a writable location — OPFS in browsers, memory or disk under Node — that shares the namespace with the read-only sources so the loader can read back what the compiler wrote. |
| Mutation and enumeration (Stage 3, gated) | Directory listing, delete, rename and output streams are capability-gated; absent capability signals an explicit unsupported condition rather than a silent no-op. |

#### Floating point and encodings

Floating point remains an explicit compatibility decision. CCL normally traps overflow, division by zero and invalid operations; Wasm has no equivalent status flags. Benchmark checks and helpers, then either preserve CCL conditions or document non-trapping IEEE behavior; the decision closes in Stage 2. [LL16]

The foreign/host boundary uses declared encodings and payload schemas. Character objects, string storage units and wire bytes are different representations; decoders never guess among 8-, 16- and 32-bit storage. Cross-language fixtures include non-ASCII and supplementary characters, typed arrays and error payloads. [LL09, LL10]

## 06  /  CONTROL TRANSFER AND DEBUGGER STAGING

### Nonlocal exits and the break loop

WebAssembly exception handling carries low-level nonlocal transfer while generated and runtime code restore Lisp stack and dynamic state. Exact catch placement is a Stage 0 experiment. Native runtime-error traps become recoverable Wasm paths.

The Stage 0 debugger proof is limited: interrupt a hand-built Wasm computation at a cooperative safepoint; enter nested execution; install and invoke a prebuilt module; perform host suspension and GC; then resume or transfer through the interrupted computation. It does not require the CCL compiler. Stage 3 performs the real test: enter a CCL break loop, read and evaluate forms, compile and install code from inside the break loop, perform repeated GC and host I/O, and invoke a restart or nonlocal transfer into or through the interrupted computation. The R2 case includes breaking into a thread blocked on unfinished host I/O, then resuming that wait or taking the supported completion/cancellation path without losing the original descriptor. [D, D5/D7; LL20]

Control restoration is observable: zero, one and many returned values; nested UNWIND-PROTECT, THROW, RETURN-FROM and GO, including cleanup that itself transfers; cleanup order, restored bindings and stacks, and the absence of side effects after a nonlocal exit. Early errors may use a structured fatal bootstrap diagnostic before the condition system exists; they are never cleared and relabeled as success. [LL01, LL19]

## 07  /  BOOTSTRAP, IMAGES AND LIVE CODE

### Two artifacts, one identity space

Cross-dump produces two coordinated artifacts because executable code no longer lives in heap code vectors: a bootstrap heap (packages, symbols, constants, closures/functions, data, logical code IDs and roots) and a bootstrap code set (modules, bodies, dependencies and debug/link metadata). The manifest maps (logical code ID, entry kind) to structural signature, callable slot, module/function, ABI/layout versions, profile/materialization records and binary hash. Stage 0 measures provisional granularity alongside D3; Stage 1 finalizes production granularity and confirms D2’s materialization contract. Boot consumes both artifacts. [D, D2/D5; LL11, LL21]

Bootstrap image loading is Stage 1; application image save and restore is Stage 5. Saved images persist heap and code metadata at a quiescent boundary and do not serialize Wasm engine stacks. Cold-start load order is observed on the native reference with a macOS external file-activity tracer rather than by hooking %fasload; static load-site projection and runtime load order are compared because REQUIRE introduces additional loads. CCL's cheap-eval permits limited evaluation without the compiler; general interactive evaluation still compiles.

Each Worker has a private WebAssembly.Table with the process-wide entry-to-slot mapping and its own installed references; tables are not structured-clone transferable. The producer installs required entries before publication; other Workers install before first dispatch. Logical code IDs are not table-slot identities: the uniform ABI still records an explicit entry mapping. IDs remain monotonic and superseded code retained under a budget through Stage 5. [D, D5; LL11, LL21]

Lazy-stub choice remains conditional until D3 closes. A selected C, C4 or B uses one shared stub for its uniform Lisp-call convention. Equal Wasm types can carry different protocols, so role validation is separate from the engine type check. Install the correct stub or function in every allocated callable slot before dispatch; unused capacity remains null/non-callable. The C runtime’s named imports need not share the Lisp signature. [D, D3/D5; LL05, LL21]

Manifest and installation validation reject missing or conflicting ID/entry/slot records, reserved-slot reuse and signature or semantic-role substitution. Stable logical IDs are distinct from module-local type indices and slot capacities. Lazy installation preserves rooted call state across admission, obtains code from accessible cache/request storage rather than a blocked Worker’s event loop, validates the final profile binary, reloads moved references and redispatches under the same entry contract. [D, D3/D5; LL07, LL13, LL20–LL22]

Complete bootstrap artifacts, not binding repair. The selected bootstrap closure includes initialization effects, macroexpansion, load order, primitive lowerings, callbacks and the reader/compiler/error dependencies it actually needs, and every required dependency has an implementation, phase and test disposition. Missing functions are resolved in the cross-compilation and cross-loading pipeline — never by name-based heap scans, replacement stubs or suppression of initialization errors. Approved loader fixups consume explicit, versioned metadata and preserve identity. [LL12, LL15]

Code identity is tracked separately from function-object identity, package-qualified symbol identity and callable slots. Deduplication may share an identical body but retains every binding alias, closure environment, keyword vector, debug record and constant pool; an existing function object is never replaced by a smaller entry-only object. A missing boot bundle, alias, pool or callable dependency is a build or installation failure. Only persistent Lisp state and declared reconstruction records may be relied on after restore; allocator pointers, engine tables, module instances, JavaScript caches and scratch buffers cannot masquerade as saved Lisp state. [LL11, LL12, LL14]

Packing and merging are optimizations of an already-correct installation path: final emitted, merged and profile-materialized binaries, signatures, dependencies, table reservations and hashes are validated, and silently dropping invalid modules cannot satisfy completeness. Compilation, instantiation, installation and byte footprint are measured separately. [LL21]

## 08  /  DELIVERY PLAN

### Stages and exit criteria

Stages retain their scope. Facilities needed by an earlier bootstrap closure must work there; Stage 4 means broader compatibility, not deferral of essential semantics. Hand-built Stage 0 proofs do not substitute for Stage 1 compiler-generated execution. The companion section 4 metadata is the sole authority for LL stage bindings. The scheduled LL lists below are derived from its First acceptance and Extensions fields; they do not replace the outline’s exit criteria or continuing regressions. All earlier accepted slices remain mandatory at later gates within the declared capability scope. Standing controls LL03, LL22–LL24 apply at every delivery stage; Gate 0 retains LL22’s baseline-identity facet. Test inventories and paired-document versions are checked before acceptance.

#### Gate 0: current U1 qualification pending; historical H1 acceptance retained

Pin source, bootstrap artifact and digest, and ccl-tests; build the native kernel; perform one clean (rebuild-ccl :clean t); start the rebuilt Lisp; run the pinned tests; preserve commands, versions, logs and FASL digests. Use the macOS x86-64 U1 reference host and pinned Darwin bootstrap. A second clean rebuild measures same-host repeatability separately. The earlier H1 results remain [historical](history/pre-macos-evidence.md). [E1, E2]

The native execution matrix is macOS x86-64. Preserve all upstream target-specific source under R6, and use macOS before/after output and behavior comparisons for this project. Historical cross-target recipes remain in [history](history/pre-macos-evidence.md); they are not current host setup or acceptance prerequisites. [E5]

#### Stage 0: census and architecture proof, in parallel

Census track, inside the qualified native compiler: enumerate evaluated acode IDs and flags, front-end elimination and rewrites, native handlers, vinsns, LAP and subprimitives, imports, traps, foreign calls and barrier-sensitive stores; instrument cross-compilation against a census stub backend for static module/function reachability; observe cold-start file opens externally with a macOS file-activity tracer and compare with static load-site projection. Join operator keys (IDs, flags, lowering chains) to module/function keys (dependency reachability, observed load order) through the instrumented compilation record. Registering the stub backend is the first shared edit governed by R6 and is followed by the first R6 comparison.

Architecture track, independent of CCL data: qualify engines, EH encoding and JSPI API shape; test the decided D1/D2/D4/D5 contracts and run D3’s ABI experiments. Qualify and measure C/C4/B, with module-granularity assumptions and sensitivity recorded alongside the ABI recommendation. Prove hand-built allocation, stores, roots, GC admission, lifecycle, interruptible FOREIGN I/O, EH, mailbox, lazy installation and nested debugging. D7 supplies phased inventories; census distributions refine but do not block the track. [D]

Rejection tests: omit a required module, alter its ABI or layout version, collide reserved memory or table ranges, and fail an initializer in the proof harness; acceptance must reject each mutant, and a killed process or timeout is not a successful computation.

Scheduled LL tests: LL01, LL02, LL04, LL05, LL07, LL08, LL13, LL15, LL19, LL20, LL21.

#### Stage 0 subgates and closure/frame contracts

[Stage 0 plan](stage0/plan.md) separates 0A baseline controls, 0B census, 0C representation/engine proofs, 0D integrated control/concurrency, 0E ABI experiments and 0F acceptance. The [workflow](workflow.md) permits architecture work independently of native census work; both tracks join before acceptance. Subgates do not waive any Stage 0 requirement.

[Logical debugger frames](contracts/debug-frames.md) define observable frame identity, source/lexical maps, debug-policy availability and restoration across moving GC, suspension and EH. D3 must account for this contract before freezing an ABI. [Census completeness](contracts/census.md) defines conservative indirect edges, reviewed seeds, a fixed-point closure, initializer prerequisites and external trace reconciliation. S0-LL15-b/c and S0-LL23-b make these explicit acceptance slices under existing obligations.

[Benchmark policy](stage0/benchmarks.json) supplies initial quantitative selection, variance, resource and dedicated-host progress thresholds. Record the policy hash before selection measurements. The initial probes exercise limited mechanisms only; their results cannot satisfy complete S0 IDs.

#### Stage 1: target contract and generated bootstrap

Execute coordinated cross-loaded heap and code artifacts using the real Wasm pass 2, vinsns, primitives and runtime. Finalize the object, allocation, root and TCR contracts, the selected call ABI, a one-Worker image loader, the read-only file namespace and a precise single-thread collector; measure and choose bootstrap module granularity and confirm D2’s selected module materialization. Exit requires independent layout fixtures and generated access and mutation tests, argument and temporary preservation, target-width arithmetic boundaries, canonical NIL/symbol/hash behavior, specialized constants, escaping mutable closures, keyword metadata where required, small-heap forced collection with visible reclamation, completion of every initializer in the selected closure, fresh-instance loading without builder caches or binding repair, and the Stage 0 rejection tests repeated through the real build path.

Scheduled LL tests: LL01, LL02, LL04, LL05, LL06, LL07, LL08, LL09, LL10, LL11, LL12, LL13, LL14, LL15, LL16, LL17, LL18, LL19, LL21.

#### Stage 2: runtime correctness

Complete level-1-required coverage; multi-Worker GC, weak references and finalization, conditions and restarts, the census-derived host services and Wasm trap, thread and callback glue; close the floating-point decision. Exit requires binding restoration, every multiple value, cleanup effects and nonlocal side-effect suppression under forced GC, and FOREIGN entry and re-entry and Worker lifecycle under randomized safepoint timing with bounded rendezvous. A late-created Worker must not replay initialization over already-mutated shared state; verify both state survival and legitimate per-Worker setup. Re-run the FOREIGN interrupt-wake schedule against production I/O, including wake during GC and completion/cancellation races on the retained descriptor. [D, D5/D7; LL20]

Scheduled LL tests: LL02, LL13, LL16, LL17, LL18, LL19, LL20.

#### Stage 3: interactive Lisp and self-hosting

Run general EVAL, COMPILE, COMPILE-FILE and LOAD with the compiler resident in the target process and the writable store in place. Compile and execute fresh source; load a newly generated bundle; verify compile- and load-time effects and live redefinition while old function objects remain callable; run the break-loop compile/install/GC/host-I/O/restart test; rebuild the target on target under identified inputs and compare reproducible artifacts with explicit normalization. A browser REPL, a kernel return code or a preinstalled arithmetic function does not pass.

Scheduled LL tests: LL02, LL11, LL19, LL20, LL21.

#### Stage 4: compatibility breadth

Validate the published Common Lisp and CCL-extension profile across CLOS, numeric completeness, streams and pathnames, thread APIs and representative ASDF systems. Unsupported operations signal the declared behavior; exclusions and NOT APPLICABLE results are explicit and reviewed. No new label silently replaces R1–R7.

Scheduled LL tests: LL16.

#### Stage 5: application images and deployment profiles

Save quiescent application state, terminate the original instance, restore in a fresh independent process and verify identity, closures, keyword metadata, packages, unexecuted constants and continued compilation and loading; two restored processes mutate independently. Qualify the compiler-light and single-thread JSPI profiles against the same object/image ABI, their declared capability sets and the materialization contract, validated final binary hashes and profile-specific suspension paths. Retain superseded code under measured budgets.

Scheduled LL tests: LL04, LL09, LL10, LL12, LL14, LL20, LL21.

#### Stage 6: hardening

Prove safe code reclamation and slot reuse, resource budgets, long-running stability and the regression matrix; add optional generational GC and optional non-JavaScript hosting. Hardening cannot retroactively excuse missing bootstrap semantics or swallowed failures.

Scheduled LL tests: no new stage-specific slice. All applicable continuing regressions remain mandatory.

Gates at every stage. R6: run the macOS reference build and compiler regression suites and compare generated artifacts and behavior where reproducible; a Wasm change that requires editing X86, ARM, ARM64 or PPC target-specific code is rejected unless R6 itself is revised. R7: the required-test inventory, result states, negative controls and criterion-change rules in the companion document, section 1.

## 09  /  MEASUREMENT AND RESOURCING

### What gets measured

Benchmark direct Wasm calls, dynamic table dispatch, complete Lisp dispatch, allocation, forced-GC overhead, host crossings, and Atomics mailbox and JSPI round trips separately. Measure time-to-safepoint, GC pause, allocation rate, per-Worker memory, module compile, instantiate and install latency, retained code growth, image size and restore time. Compare native-Wasm execution against a bytecode or interpreter-on-Wasm baseline, including a reproducible CLISP/Emscripten-class baseline where available. Run the same semantic corpus against native CCL where behavior is defined and track existing-target regressions under R6.

Planning assumption: three to six engineer-years through interactive self-hosting (Stages 0–3), to be replaced by measured Stage 0 and Stage 1 velocity. The roughly 50 KLOC ARM64 target is scale calibration, not a person-year conversion. Stages 4–6 add compatibility and hardening work. Evidence records, evidence kinds and reporting rules are in the companion document, section 1.

## 10  /  OPEN SOURCE AUDITS

### Still to close

- Enumerate pass-2 acode handlers and the bootstrap subset versus complete coverage; join operator-level records (operator → handler → vinsn/LAP/subprimitive/trap/store) with module/function-level records (static closure and runtime load order) through the instrumented compilation record.

- Generate percent-primitive to vinsn/LAP/subprimitive graphs through level-0, level-1, lib and library.

- Classify all kernel imports, trap classes and direct foreign calls; derive the file-system and host-service contract from that census.

- Audit generation, tenure, refbits, areas, purification and barrier interfaces visible above the collector.

- Audit FASL/image assumptions about code vectors, relocations, function objects and code addresses.

- Audit debugger and backtrace assumptions about native signal contexts and frame layout.

- Audit architecture-specific level-1 conditionals and callback/FFI dependencies, including foreign-types initialization without an interface database.

- Verify every shared-source Wasm modification is additive and preserves existing-target outputs and semantics under R6.

- Audit the object-layout schema across the selected C or emitted runtime, Lisp, JavaScript, GC and image tools using the same independent golden fixtures, plus target-compiled sizeof/offsetof assertions for C or target-executed layout probes for an emitted runtime.

- Audit test inventory, synthetic or stale evidence, error propagation, build provenance, loader identity repair and host-only saved state; map every LL obligation to executable positive and rejection tests before accepting the affected stage.

## 11  /  REFERENCE BASIS AND PROVENANCE

### Sources and evidence

[H1] Historical design/evidence revision: `4ca4df402e319789401cd33e680702e51ec601fc`. Source links [3]–[13] retain H1 as their historical inspection basis; implementation edit sites and inventories are requalified at U1. References [1]–[25] retain the recorded design basis; specification review dates are historical, not this revision’s execution evidence. [D] identifies the coordinated decisions. U1 is the clean implementation baseline; P1 is the historical attempt, with P2–P16 in companion section 3. E1, E2 and E5 identify execution packs, E3 is a status record, and E4 remains conversation-recorded evidence with its archived trace pack pending.

[1] [Clozure CL source repository](https://github.com/Clozure/ccl) Source layout and build requirements.

[2] [Clozure CL Internals](https://ccl.clozure.com/docs/build/internals.html) TCRs, threads, foreign state, exceptions, GC, tagging and compiler conventions.

[3] [compiler/backend.lisp](https://github.com/Clozure/ccl/blob/4ca4df402e319789401cd33e680702e51ec601fc/compiler/backend.lisp) Backend and target structures; register-oriented pass-2 interfaces.

[4] [compiler nx0/nx1/nx2/acode-rewrite](https://github.com/Clozure/ccl/blob/4ca4df402e319789401cd33e680702e51ec601fc/compiler/nx1.lisp) Shared front end and target abstraction.

[5] [lib/compile-ccl.lisp and CCL manual](https://github.com/Clozure/ccl/blob/4ca4df402e319789401cd33e680702e51ec601fc/lib/compile-ccl.lisp) Target compilation, cross-dumping and bootstrap.

[6] [Architecture pass-2 files (x862.lisp, arm642.lisp)](https://github.com/Clozure/ccl/blob/4ca4df402e319789401cd33e680702e51ec601fc/compiler/X86/x862.lisp) acode coverage and target lowering.

[7] [Architecture vinsn files](https://github.com/Clozure/ccl/blob/4ca4df402e319789401cd33e680702e51ec601fc/compiler/X86/X8664/x8664-vinsns.lisp) Allocation, checks, barriers and runtime entry patterns.

[8] [lisp-kernel gc-common.c and architecture gc.c](https://github.com/Clozure/ccl/blob/4ca4df402e319789401cd33e680702e51ec601fc/lisp-kernel/gc-common.c) Collector implementation.

[9] [thread_manager.c and architecture exception sources](https://github.com/Clozure/ccl/blob/4ca4df402e319789401cd33e680702e51ec601fc/lisp-kernel/thread_manager.c) Suspension, TCR states and interrupted-sequence repair.

[10] [imports.s and spentry/subprimitive sources](https://github.com/Clozure/ccl/blob/4ca4df402e319789401cd33e680702e51ec601fc/lisp-kernel/imports.s) Kernel import and subprimitive surfaces.

[11] [level-0 architecture sources](https://github.com/Clozure/ccl/blob/4ca4df402e319789401cd33e680702e51ec601fc/level-0/X86/x86-misc.lisp) LAP and low-level primitive implementations.

[12] [level-1 architecture trap/error/thread/callback support](https://github.com/Clozure/ccl/blob/4ca4df402e319789401cd33e680702e51ec601fc/level-1/x86-trap-support.lisp) Signal-context-dependent Lisp glue.

[13] [xdump/xfasload.lisp, heap-image and architecture cross-fasload files](https://github.com/Clozure/ccl/blob/4ca4df402e319789401cd33e680702e51ec601fc/xdump/xfasload.lisp) Cross-dump and image construction.

[14] [Common Lisp HyperSpec: COMPILE](https://www.lispworks.com/documentation/HyperSpec/Body/f_cmp.htm) Definition replacement and literal-object identity.

[15] [Common Lisp HyperSpec: HANDLER-BIND and UNWIND-PROTECT](https://www.lispworks.com/documentation/HyperSpec/Body/s_unwind.htm) Handlers, cleanup and nonlocal transfer.

[16] [WebAssembly core specification](https://webassembly.github.io/spec/core/intro/overview.html) Calls, tables, memories, traps and numeric semantics.

[17] [WebAssembly threads proposal](https://github.com/WebAssembly/threads/blob/main/proposals/threads/Overview.md) Shared/unshared memory matching, maximum limits, atomic access and wait behavior, and repeated data-segment initialization. Specification basis checked 10 September 2026; not engine-execution evidence.

[18] [WebAssembly exception handling proposal](https://github.com/WebAssembly/exception-handling) Tags, throw/catch and unwinding.

[19] [WebAssembly JS Promise Integration](https://github.com/WebAssembly/js-promise-integration) Engine-level Wasm stack suspension.

[20] [MDN: Using Web Workers](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API/Using_web_workers) Worker execution and messaging.

[21] [MDN: Atomics.wait()](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Atomics/wait) Blocking waits on shared memory; not permitted on the main thread.

[22] [MDN: SharedArrayBuffer](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer) Cross-origin-isolation requirements.

[23] [MDN: WebAssembly.Module / Table / Memory](https://developer.mozilla.org/en-US/docs/WebAssembly/Reference/JavaScript_interface/Module) Module transfer, table installation and memory growth.

[24] [MDN: CSP script-src](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/script-src) WebAssembly compilation policy.

[25] [Emscripten: Asynchronous Code](https://emscripten.org/docs/porting/asyncify.html) Suspension alternatives and the interpreter-on-Wasm baseline.

[D] Stage 0 Desk Decisions v1.8, 11 September 2026 D1 derived data layout; D2 profile materialization; D3 open ABI candidate sequence; D4 selected runtime split; D5 GC admission, logical IDs/entry slots and interruptible mailbox; D6 vocabulary/lowering; D7 phased tests. Decision choices are distinct from implementation/test acceptance. CCL_WebAssembly_Stage0_Desk_Decisions_v1_8.docx

#### Implementation baselines

[U1] [Clean implementation baseline: Clozure/ccl v1.13](https://github.com/Clozure/ccl/blob/c994217adc56b3f8a564526cee4695893ac84d86/lisp-kernel/constants.h) lisp-kernel/constants.h lines 41–44: struct cons { LispObj cdr; LispObj car; }.

[U1a] [Companion C accessors: lisp-kernel/macros.h](https://github.com/Clozure/ccl/blob/c994217adc56b3f8a564526cee4695893ac84d86/lisp-kernel/macros.h) untag, car and cdr at lines 30, 44 and 45 of the same baseline.

[P1] [Previous-attempt baseline: snethert/ccl, wasm-port at 2d71436](https://github.com/snethert/ccl/tree/2d71436555563cd0ba06fa4b5afdc110aec56117) Historical tree only; never substituted for U1. Detailed sources P2–P16 are in the companion document.

#### Evidence records and retention status

[E1] Historical native Gate 0 run, reported at H1; original platform and bootstrap provenance are retained in history/pre-macos-evidence.md.

[E2] Historical repeatability and cold-start load-order report at H1; retained in history/pre-macos-evidence.md.

[E3] CCL_Stage0_Current_Status.md, 10 September 2026 Project status record: native reference result, provisional inventories, census/load-order distinction, and the failed ad hoc ARM64 backend-loading experiment that E5 supersedes.

[E4] Historical cold-start syscall profile; raw trace archive unavailable. Original counts and platform-specific paths are retained in history/pre-macos-evidence.md.

[E5] Historical ARM64 cross-compilation report at H1; original recipe and prerequisites are retained in history/pre-macos-evidence.md. This is not a qualification requirement for the current macOS reference.
