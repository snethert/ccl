COMPANION DOCUMENT  /  VERSION 1.4  •  11 SEPTEMBER 2026

# Acceptance Policy and Regression Register

Companion to Port Outline v0.14 and Stage 0 Desk Decisions v1.5

This document governs milestone acceptance: R7 rules and evidence (section 1), R6 normalization (section 2), sources (section 3), and LL01–LL24 (section 4). It replaces v1.3 and accompanies outline v0.14 and decisions v1.5. Individual obligation metadata remains authoritative; the index and outline stage lists are derived. This register specifies required regressions; execution and acceptance are tracked in [current status](STATUS.md). Documenting a test does not close its implementation.

Changes in v1.4. Selects macOS x86-64 for native regression qualification and second-host reproduction. Historical platform-specific baselines remain in the history ledger; they do not impose current host requirements. R6 source preservation, independent review and all LL obligations remain in force.

## 1  /  R7 EVIDENCE-BASED ACCEPTANCE

### Gate rules and evidence

A milestone passes only when required behavior is demonstrated by identified tests against identified artifacts. Required build, initialization, installation and test failures propagate to acceptance. Diagnostic continuation, synthetic fixtures, skipped tests and unimplemented substitutes cannot satisfy the requirement they bypass.

#### Gate rules

- Required tests are an explicit inventory bound to expected test IDs and required modules, not whichever files were discovered. A missing mandatory case blocks acceptance; skip reasons are recorded.

- Before acceptance, verify that paired document versions, outline stage lists and the section 5 index match the individual obligation metadata in section 4. Reject stale or contradictory projections; none may override an obligation or remove its continuing regressions.

- PASS requires all mandatory results, matching provenance and successful gate-negative controls. FAIL, BLOCKED, NOT RUN and NOT APPLICABLE remain distinct; unavailable evidence is BLOCKED or NOT RUN, never PASS.

- A diagnostic continuation cannot supply a passing production bootstrap result. A killed process or a timeout is not a successful computation.

- A negative-control meta-test passes only by observing the production gate reject the injected defect; its mutated artifacts remain quarantined. Deliberate mutations verify that altered constants, bypassed cleanup, discarded return values, missing closure state, stale artifacts and ignored child failures are detected.

- Original failing tests are stored unchanged when reduced reproducers are added; claims are never transferred to the reduced case.

- Acceptance criteria change only through a recorded scope decision that identifies withdrawn claims and tests. Agents may reduce an approved milestone's scope; they may not redefine passing, remove R6, or replace shared-heap threading with isolated runners.

#### Evidence kinds

Evidence kinds are distinct and are labeled on every record: NATIVE BASELINE EXECUTION, SOURCE INSPECTION, HOST COMPILATION, HAND-BUILT WASM EXECUTION, COMPILER-GENERATED TARGET EXECUTION, IMAGE ROUND-TRIP, SELF-HOSTED REBUILD, CONTROL EXECUTION and BENCHMARK EXECUTION. CONTROL EXECUTION identifies the gate/checker path being tested and whether its inputs are synthetic; it never certifies the corresponding Lisp semantics. BENCHMARK EXECUTION identifies fresh raw measurements and their correctness prerequisites; saved summary JSON alone is insufficient. SYNTHETIC fixtures and historical reports are recorded as such. Source-token counts, installed-module counts, saved performance JSON and schema checks cannot stand in for fresh semantic execution. A test must demonstrate that its named behavior ran and that its assertions would detect its absence.

#### Evidence record

Each gate record identifies: requirement and test ID; evidence kind; source revision with dirty-tree and untracked-input digest; bootstrap, compiler and toolchain versions; target, profile and engine; command, configuration and seed; input and output hashes; assertions and results; logs; substitutions and skips; timestamp; and review disposition. Test revisions are pinned as well as implementation revisions. Stable semantic metadata is separated from timestamps and diagnostic provenance. For materialized modules, record both template/source and final binary hashes, materializer/emitter version, profile, memory limits and validated imports; a template digest cannot identify different installed binaries. The obligation-metadata revision and derived stage inventory are pinned together.

#### Reporting and agent operating rules

One dated current-status summary and a separate history. Proposed, implemented, compiled, installed, executed and accepted are distinguished. Percentage completion is never reported from function counts. Every fixed-defect claim links to a change and a regression result; earlier narrative is not proof the patch exists. Agents preserve failing tests, expose bypasses, obey R6 and R6a, and record criterion changes rather than weakening them silently. A new defect in a dependency is investigated to the first violated invariant, not worked around.

## 2  /  R6 REPRODUCIBILITY AND NORMALIZATION

### R6 comparison boundaries

R6 prohibits edits to existing target-specific implementation source. Shared additions required for Wasm are reviewed in four distinct artifact categories:

| Category | Required comparison | Acceptance disposition |
| --- | --- | --- |
| Existing target-specific source | Exact source diff against U1 | Any edit fails R6 unless R6 is explicitly revised. |
| Unchanged native-target inputs | Identical pinned source corpus, options, target and environment compiled before/after shared changes; compare raw and approved narrowly normalized FASLs | Unexpected executable or ABI differences fail; native behavior is checked separately. Include full unchanged-source native build inputs where applicable, not just favorable microfixtures. |
| Intentionally changed shared compiler artifacts | Enumerate source changes and affected FASLs/decoded executable components; retain before/after hashes, rationale and review | Additive registration/dispatch/compiler-data changes may intentionally alter these artifacts. Require explained diffs and unchanged-input target output/behavior checks. A whole changed file is never exempt from review. |
| Existing-target behavior and ABI | Pinned compiler/runtime tests, exported ABI and evaluated operator identity/flag snapshots | Unexpected differences fail regardless of byte repeatability. Missing target evidence stays BLOCKED/NOT RUN. |

A native-host compiler FASL modified to support Wasm is not an unchanged-input output-equivalence sample. Mark it as an intentional shared-artifact change, not a normalization. Every differing artifact must belong to a reviewed category; unattributed differences fail. New executable branches must never be erased by normalization. This clarifies how additive shared changes satisfy R6; it does not authorize existing-target source edits or behavior changes.

### Baselines and variance

The native regression reference is **macOS x86-64 at U1 v1.13**. Its bootstrap, tests, toolchain and execution disposition are recorded in [baseline.json](stage0/baseline.json), [current status](STATUS.md) and the [evidence index](evidence/index.json). Repeat the same macOS target on a second Mac for S0-LL08-c. Same-host repeatability, second-host reproducibility and native behavior are separate claims.

Generated code is compared primarily at the FASL level; heap-image byte identity is not required, but image behavior and object-graph validity are. The [historical H1 baseline table](history/pre-macos-evidence.md) and its missing archives retain their original provenance. Other upstream targets are preserved as source; their host provisioning and execution are outside this Wasm project's qualification matrix. This scope change does not permit source or behavior changes to those targets.

Variance policy. A differing file is not automatically a harmless exception, and a whole file is never excluded. An approved normalization identifies the affected fields, byte ranges or decoded semantic components, explains their origin, is independently checked not to erase executable differences, and retains raw digests alongside normalized results. Until characterized, a variance remains unexplained and cannot support an all-artifacts-unchanged claim. Every stage binds code, image, modules, ABI schema, host compiler, test revision, options and logs to content hashes and rejects mixed builds.

Cross-host reproducibility is established by repeating the same build on a second host and diffing against the retained digests. Previously accepted Gate 0 results are preserved with their original evidence scope and are not promoted to full Stage 0 completion.

E4 retention status. The historical syscall counts are conversation-recorded execution results, not an archived trace pack. Commands, environment, raw traces and digests remain to be retained on recapture. This evidence gap does not reset Gate 0 or the established 126/126 ARM64 same-host repeatability result.

## 3  /  PREVIOUS-ATTEMPT SOURCES

### The historical tree

P1 is the historical port; U1 in the outline is the selected v1.13 implementation baseline, while H1 is the later upstream revision used by E1–E5 and earlier design inspection. P-series sources below are pinned to snethert/ccl at 2d71436555563cd0ba06fa4b5afdc110aec56117. "Observed" in section 4 means directly inspected source; "reported" means the old ledger or plan records the event and may describe a repaired defect; "safeguard" is a resulting requirement. No fresh build or execution of this tree is claimed. W1 is external specification evidence for the added safeguards, not evidence that a defect was reproduced in the historical port. U1, E1, E2, E4 and E5 are defined in outline section 11.

[P1] [snethert/ccl, wasm-port at 2d71436](https://github.com/snethert/ccl/tree/2d71436555563cd0ba06fa4b5afdc110aec56117) Previous-attempt baseline only.

[P2] [TODO.md](https://github.com/snethert/ccl/blob/2d71436555563cd0ba06fa4b5afdc110aec56117/TODO.md) Historical bug reports, claimed fixes, bridge-test status, working rules and inconsistent completion entries.

[P3] [lisp-kernel/wasm-kernel-stubs.c](https://github.com/snethert/ccl/blob/2d71436555563cd0ba06fa4b5afdc110aec56117/lisp-kernel/wasm-kernel-stubs.c) wasm_run_cold_boot_init, wasm_drain_cold_load_list, start_lisp and tagged-memory helpers.

[P4] [scripts/wasm/rebuild-everything.sh](https://github.com/snethert/ccl/blob/2d71436555563cd0ba06fa4b5afdc110aec56117/scripts/wasm/rebuild-everything.sh) Root-image failure policy (ROOT_IMAGE_ALLOW_FAIL=1 by default), optional test compilation, artifact cleaning and freshness.

[P5] [doc/wasm/calling-convention-abi.md](https://github.com/snethert/ccl/blob/2d71436555563cd0ba06fa4b5afdc110aec56117/doc/wasm/calling-convention-abi.md) Earlier ARM32-shaped ABI and explicit cons slot ordering.

[P6] [scripts/wasm/generate_abi_contract.py](https://github.com/snethert/ccl/blob/2d71436555563cd0ba06fa4b5afdc110aec56117/scripts/wasm/generate_abi_contract.py) Regex extraction, declared layouts and generated cross-language assertions.

[P7] [scripts/wasm/tests/all-smoke.mjs](https://github.com/snethert/ccl/blob/2d71436555563cd0ba06fa4b5afdc110aec56117/scripts/wasm/tests/all-smoke.mjs) Executed test inventory and synthetic-artifact calls.

[P7a] [scripts/wasm/tests/compiler-smoke.mjs](https://github.com/snethert/ccl/blob/2d71436555563cd0ba06fa4b5afdc110aec56117/scripts/wasm/tests/compiler-smoke.mjs) Source-count and historical JSON checks alongside execution.

[P7b] [scripts/wasm/tests/start-lisp-smoke.mjs](https://github.com/snethert/ccl/blob/2d71436555563cd0ba06fa4b5afdc110aec56117/scripts/wasm/tests/start-lisp-smoke.mjs) Minimal-image startup-return assertion.

[P7c] [scripts/wasm/compile-smoke-modules.lisp](https://github.com/snethert/ccl/blob/2d71436555563cd0ba06fa4b5afdc110aec56117/scripts/wasm/compile-smoke-modules.lisp) wasm-smoke-closure-unwind-mv fixture: no inner closure, only the first returned value used.

[P7d] [scripts/wasm/tests/closure-unwind-mv-smoke.mjs](https://github.com/snethert/ccl/blob/2d71436555563cd0ba06fa4b5afdc110aec56117/scripts/wasm/tests/closure-unwind-mv-smoke.mjs) Claims closure/MV coverage but asserts only result === 12 (line 157).

[P7e] [scripts/wasm/tests/phase0a-bridge-smoke.mjs](https://github.com/snethert/ccl/blob/2d71436555563cd0ba06fa4b5afdc110aec56117/scripts/wasm/tests/phase0a-bridge-smoke.mjs) Missing-export substitutes and staleness warning.

[P8] [doc/wasm/deterministic-startup-plan.md](https://github.com/snethert/ccl/blob/2d71436555563cd0ba06fa4b5afdc110aec56117/doc/wasm/deterministic-startup-plan.md) Reported malloc-only saved objects, key-vector destruction and the image-versus-host-state distinction.

[P9] [scripts/wasm/lib/make-real-image.mjs](https://github.com/snethert/ccl/blob/2d71436555563cd0ba06fa4b5afdc110aec56117/scripts/wasm/lib/make-real-image.mjs) Runtime module installation policy, name-based image fixup, constant pools and cold-boot invocation.

[P10] [level-0/WASM/wasm-symbol.lisp](https://github.com/snethert/ccl/blob/2d71436555563cd0ba06fa4b5afdc110aec56117/level-0/WASM/wasm-symbol.lisp) Hash implementation, global-cell value fallback and closure-free binding-index overrides.

[P11] [level-0/WASM/wasm-utils.lisp](https://github.com/snethert/ccl/blob/2d71436555563cd0ba06fa4b5afdc110aec56117/level-0/WASM/wasm-utils.lisp) Lisp GC/control stubs, address limitation and heap-walking code; does not establish absence of C-level GC.

[P12] [lisp-kernel/wasm-subprims-provider.c](https://github.com/snethert/ccl/blob/2d71436555563cd0ba06fa4b5afdc110aec56117/lisp-kernel/wasm-subprims-provider.c) Error absorption, pending-throw dispatch, runtime NIL and code-vector trampoline.

[P13] [compiler/WASM/wasm2.lisp](https://github.com/snethert/ccl/blob/2d71436555563cd0ba06fa4b5afdc110aec56117/compiler/WASM/wasm2.lisp) Earlier compiler, temporary allocation, operator extension and compiled-module/name-alias machinery.

[P14] [lisp-kernel/wasm32/Makefile](https://github.com/snethert/ccl/blob/2d71436555563cd0ba06fa4b5afdc110aec56117/lisp-kernel/wasm32/Makefile) Imported memory/table and reservation of table indices for C function pointers.

[P15] [lisp-kernel/wasm-ccl-step.c](https://github.com/snethert/ccl/blob/2d71436555563cd0ba06fa4b5afdc110aec56117/lisp-kernel/wasm-ccl-step.c) Step-state wrapper; deadline_ms is reserved and discarded (line 74).

[P16] [CODEX-ANALYSIS-REQUEST-9.md](https://github.com/snethert/ccl/blob/2d71436555563cd0ba06fa4b5afdc110aec56117/CODEX-ANALYSIS-REQUEST-9.md) Historical logs, corrected entry-name attribution and unresolved numeric-dispatch hypotheses.

[E3] CCL_Stage0_Current_Status.md, 10 September 2026 Supplied project record; historical status carried forward, not freshly executed.

#### Additional specification basis

[W1] [WebAssembly threads: memory, atomic access and instantiation](https://github.com/WebAssembly/threads/blob/main/proposals/threads/Overview.md) Shared memory, Resizing, Initializing Memory Only Once, Atomic Memory Accesses, and Wait and Notify. Checked 10 September 2026. Supplies specification facts for LL13 and LL21; the tests are project safeguards, not claimed historical execution.

[D] Stage 0 Desk Decisions v1.5, 11 September 2026 Project authority for D1–D7. D3 remains open; D5 specifies owner-only CAS GC admission, typed entry identity and interruptible FOREIGN I/O. D7 maps authoritative LL stage slices into phased executable inventories, including S0-LL20-b. This is a decision/protocol source, not test-execution evidence. CCL_WebAssembly_Stage0_Desk_Decisions_v1_5.docx

## 4  /  REGRESSION OBLIGATIONS LL01–LL24

### What the previous attempt obliges the new port to test

Each obligation records the historical evidence, required regression, authoritative stage metadata and protected outline sections. First acceptance is the initial test slice; extensions add or re-prove the behavior in the stated context. Passing a hand-built slice does not close a later compiler-generated or image-save slice. The Required regression text defines the scope of each scheduled slice.

#### Binding authority and continuing regressions

The metadata under each LL entry is the sole stage-binding authority. Generate the section 5 index and outline section 08 lists from its First acceptance and Extensions fields; do not edit those views independently. Standing controls are LL03, LL22, LL23 and LL24 at every delivery stage. Gate 0 is the separate native baseline; LL22’s baseline-identity facet applies there without claiming all LL22 regressions have already run.

Continuing regressions apply at every later gate to all previously required slices within the gate’s declared capability scope, even when an obligation has no new scheduled extension there. Earlier bootstrap dependencies cannot become optional because a later stage has a narrower list. Each gate inventory includes its scheduled slices, standing controls, continuing regressions and the outline’s own exit criteria; omissions or NOT APPLICABLE dispositions need the section 1 scope decision.

For example, LL12 remains a Stage 3 regression after its Stage 1 acceptance; LL11, LL13 and LL18 remain applicable at Stage 5; and LL21 continues under Stage 6 code reclamation and slot reuse. LL15 likewise continues at Stage 2. These carry-forward uses are not new metadata extensions. The late-Worker safeguard adds an explicit LL13 Stage 2 extension.

### A.1  Acceptance must measure the intended system

#### LL01  /  Fail closed at initialization, installation and build boundaries

Observed: cold-boot initialization accepts a pending error after startup step 40; the C drain clears individual failures. The rebuild script allows root-image failure by default and ignores other required-looking failures. Runtime module installation is non-strict. [P3, P4, P9]

Required regression. Stage 0 harness and Stage 1 production gates fail required early, middle and late initializers, omit one required module, fail a child command and trigger a timeout, and require a non-passing aggregate, precise diagnostics and no accepted partial image. Diagnostic continuation records errors but remains ineligible for acceptance. An approved language-level restart is not equivalent to silently clearing an error.

First acceptance: Stage 0. Extensions: Stage 1. Regression: all later stages in scope. Outline sections: 06, 07, 08. Status: contract specified; execution and acceptance tracked in STATUS.md.

#### LL02  /  Tests retain their behavioral assertions and required inventory

Observed: the closure/unwind/MV smoke fixture has no inner closure, ignores five of six values and has no observable cleanup mutation; its JavaScript assertion checks only 12. The aggregate smoke inventory omits the bridge runner. [P7, P7c, P7d]

Required regression. Stages 0–3 gate the expected test IDs and counts; require an escaping mutable closure, inspect every multiple value and observe cleanup order and effects. Mutants that drop an extra value, skip cleanup or remove capture must fail. The original failing test is kept when a smaller reproducer is created.

First acceptance: Stage 0. Extensions: Stages 1–3. Regression: all later stages in scope. Outline sections: 06, 08. Status: contract specified; execution and acceptance tracked in STATUS.md.

#### LL03  /  Separate fixtures, minimal-entry tests and measurements from runtime proof

Observed: smoke code emits synthetic artifacts; compiler checks consume historical performance JSON and source-token counts; startup smoke uses a minimal image; bridge tests can supply missing-export substitutes. None certifies the corresponding production subsystem. [P7, P7a, P7b, P7e]

Required regression. All gates label evidence kind, fixture identity and substitutions. Acceptance executes the declared production path and current artifacts. Deliberately supplied old evidence or a missing import is rejected rather than silently substituted. Stage 3 requires fresh target compilation and execution, not a zero startup return code.

First acceptance: Stage 0. Extensions: Stages 1–6. Standing control. Regression: all later stages in scope. Outline sections: 08, 09. Status: contract specified; execution and acceptance tracked in STATUS.md.

### A.2  Representation and compiler foundations

#### LL04  /  CDR-before-CAR is one row of a cross-language layout schema

Observed: U1 defines CDR first and CAR second (constants.h 41–44). Reported: earlier CAR/CDR fixes included incorrect list traversal in a word-access helper and swapped JavaScript variable meanings; the ledger admits previously described fixes were not in the code. [U1, P2, P5]

Required regression. Stages 0 and 1 validate the selected runtime using target-compiled sizeof/offsetof assertions for C or target-executed layout probes for Lisp-emitted code. Both use the same independent raw two-word fixture: CDR in word 0, CAR in word 1, with unequal payloads, while construction remains (cons car-value cdr-value). Cover dotted pairs, nested, shared and cyclic graphs, CAR/CDR of NIL and RPLACA/RPLACD changing only the intended field across runtime, generated Wasm, cross-loader, JS inspector and GC, as those paths enter the stage. Repeat fresh loading at Stage 1 and save/restore at Stage 5. A one-sided slot swap must fail. Symmetric data or mutually reversed readers/writers cannot be the oracle. Apply the same fixture discipline to every schema row; an emitted runtime has no mandatory C dependency.

First acceptance: Stage 0. Extensions: Stages 1, 5. Regression: all later stages in scope. Outline sections: 02, 07. Status: contract specified; execution and acceptance tracked in STATUS.md.

#### LL05  /  Argument order, arity and return protocol are per-boundary contracts

Reported: prologue, value-stack push/sync and three-argument allocation paths disagreed about first/last argument placement. The earlier ABI retained per-subprimitive conventions. [P2, P5]

Required regression. Stages 0 and 1 exercise zero, one, two, three and overflow arguments with distinct values, subtraction and ordered side effects across direct and dynamic calls, closures, APPLY, optional/rest/keyword binding, primitive entries and host callbacks when in the closure, verifying count encoding and zero/one/many returns against the Stage 0-specified Wasm ABI. Qualify C, C4 and B before their baseline measurements; only afterward qualify any H(G) against its corresponding G. For H, additionally verify entry eligibility/fallback, adapters and signature/semantic-role checks; baseline qualification does not require H variants early. [D, D3/D7]

First acceptance: Stage 0. Extensions: Stage 1. Regression: all later stages in scope. Outline sections: 02. Status: contract specified; execution and acceptance tracked in STATUS.md.

#### LL06  /  Temporary lifetime and evaluation order precede bootstrap breadth

Reported: PROG1 saved a value into a reusable local that a nested SETQ overwrote, corrupting the cold-load function list and surfacing later as an unbound-function error. [P2, P13]

Required regression. Stage 1: generated nested PROG1/PROG2, LET, SETQ, conditionals, calls and loops preserve every live temporary and the defined evaluation order under forced allocation and legal GC between producers and consumers; spill/root reload and stack balance are checked on normal and exceptional paths, with an independent expected result that detects a changed local allocation.

First acceptance: Stage 1. Extensions: none. Regression: all later stages in scope. Outline sections: 02, 03. Status: contract specified; execution and acceptance tracked in STATUS.md.

#### LL07  /  Raw addresses, tagged values and integer payloads are not interchangeable

Reported: shifting an untagged high address into a fixnum lost pointer bits; similar mistakes affected cons access and typecode reads. Observed: smoke metadata identifies a separate double-shift of an entry index. [P2, P7c]

Required regression. Stages 0 and 1 test all declared conversions and high-bit boundaries with synthetic address fixtures plus real allocations, negative header offsets and sign extension, without banning legitimate accesses; unchecked JavaScript signed bitwise arithmetic is never used as address arithmetic; bounds failures are separated from legal high-address values and code-index encoding.

First acceptance: Stage 0. Extensions: Stage 1. Regression: all later stages in scope. Outline sections: 02, 03. Status: contract specified; execution and acceptance tracked in STATUS.md.

#### LL08  /  The cross-compiler must not inherit host target state

Reported: TARGET package references resolved to x86-64 during reading; cached host macro FASLs masked source changes; ad hoc target loading also failed in the project status record before E5 fixed the recipe. [P2, P4, E3, E5]

Required regression. Stages 0 and 1 pin the supported backend-loading recipe and establish target state before reading or expanding target-dependent forms; macros, tags, widths and reader conditionals are verified under multiple clean host sessions; dirty and cached inputs are recorded. R6a snapshots evaluated IDs and flags including reserved slots.

First acceptance: Stage 0. Extensions: Stage 1. Regression: all later stages in scope. Outline sections: 01, 08. Status: contract specified; execution and acceptance tracked in STATUS.md.

#### LL09  /  Canonical symbols, package hashes and runtime NIL must agree

Reported: target hash width disagreed with cross-generated package tables. Observed: subprimitives cache a runtime NIL because their compile-time NIL differs; name-based image repair and synthesized-symbol diagnostics expose identity risks. [P2, P9, P10, P12]

Required regression. Stages 1 and 5 test INTERN, FIND-SYMBOL, EQ and bindings before and after image loading with colliding names in distinct packages, NIL, T, keywords and uninterned symbols. A host/target hash contract matches before lookup or triggers a defined pre-lookup rebuild. Supported image bases are varied and unsupported ones rejected explicitly; nothing is bound by unqualified name alone.

First acceptance: Stage 1. Extensions: Stage 5. Regression: all later stages in scope. Outline sections: 05, 07. Status: contract specified; execution and acceptance tracked in STATUS.md.

#### LL10  /  Constant pools preserve representation as well as values

Reported: unboxed fixnums were stored as Lisp objects; specialized arrays were flattened until a subtype-aware pool encoding was added; tagged characters were used where numeric codes were required. [P2, P6]

Required regression. Stages 1 and 5 use golden fixtures for signed fixnums, bignum limbs, selected float bit patterns, specialized vectors, general vectors, strings and supplementary characters, preserving sharing, identity, element widths and subtags, and round-tripping unexecuted-function constants. The generated schema is checked against the selected target implementation using the LL04 C assertions or emitted-runtime probes; a regex extractor is not the ABI authority.

First acceptance: Stage 1. Extensions: Stage 5. Regression: all later stages in scope. Outline sections: 02, 05, 07. Status: contract specified; execution and acceptance tracked in STATUS.md.

### A.3  Code, bootstrap and persistent state

#### LL11  /  Deduplicating code must not erase aliases or collide entries

Reported: deduplication by shared bootstrap entry dropped function-name aliases, including a FASL initialization function. Observed: separate boot/runtime index handoff and an entry-index double-shift required explicit treatment. [P2, P4, P7c]

Required regression. Stages 1 and 3 compile differently named functions sharing identical code, preserve all package-qualified bindings and keep closure environments distinct; validate complete entry ranges, arity and boot/runtime manifests; fail installation on missing aliases, reused reserved slots or conflicting records; and test dynamic redefinition while old function objects remain callable.

First acceptance: Stage 1. Extensions: Stage 3. Regression: all later stages in scope. Outline sections: 07. Status: contract specified; execution and acceptance tracked in STATUS.md.

#### LL12  /  A callable entry is not a complete function object

Reported: force-rebinding replaced FASL-created functions with stubs that lost keyword vectors; binding-index closures were bypassed because environments were unpopulated. The closure-free override is visible in the old source. [P8, P10]

Required regression. Stages 1 and 5 load escaping mutable closures with shared and distinct captured cells, keyword functions and callable metadata; preserve environments, key vectors and debug records through install and restore; inject a truncated function object and require validation failure. The first affected function is never repaired with global state.

First acceptance: Stage 1. Extensions: Stage 5. Regression: all later stages in scope. Outline sections: 07. Status: contract specified; execution and acceptance tracked in STATUS.md.

#### LL13  /  Modules share memory and table namespaces that must have owners

Reported: kernel and subprimitive static-data initialization collided. Observed: the kernel linker reserves table space so C function pointers are not overwritten by subprimitive installation. [P2, P14] Specification fact: active data segments initialize again on each instantiation, including in another agent. The late-Worker test below is an added safeguard, not a claimed reproduction in P1. [W1]

Required regression. Stages 0 and 1 compare linker- or emitter-derived static/BSS/stack/heap/staging and table ranges, protect reservations and test sentinel survival across module initialization. Reject overlaps, misalignment, undersized ranges and unauthorized initialization writes before publication; use metadata rather than a guessed gap. Stage 0’s multi-Worker harness mutates shared sentinels before instantiating the same module in a late Worker; Stage 1 validates generated process-once versus per-Worker setup. Stage 2 repeats with production Worker creation after heap/runtime mutation and code publication. Existing shared state must survive, and legitimate per-Worker initialization must succeed only in its owned region. Inject a repeated active-data or start-function/BSS write to live shared state and require rejection. Recheck through lazy installation and subsequent Worker creation.

First acceptance: Stage 0. Extensions: Stages 1–2. Regression: all later stages in scope. Outline sections: 02, 03, 04, 07. Status: contract specified; execution and acceptance tracked in STATUS.md.

#### LL14  /  An image contains only serialized state plus declared reconstruction data

Reported: function objects allocated via C malloc were not part of the saved Lisp heap. The startup plan correctly separates heap objects from engine modules, instances, tables and JavaScript caches. [P8]

Required regression. Stage 1 cross-dump loading and Stage 5 application save restore into a fresh process with builder caches absent; validate graph ownership, pointer ranges, shared references, constants and code metadata; no serialized pointer refers to unsaved allocator, scratch or host state; two restored processes diverge independently and subsequent compilation and loading still work.

First acceptance: Stage 1. Extensions: Stage 5. Regression: all later stages in scope. Outline sections: 07. Status: contract specified; execution and acceptance tracked in STATUS.md.

#### LL15  /  Bootstrap completeness includes dependency cycles and initialization order

Reported: missing LAP bridges, omitted boot modules, load-order overwrites and load-time PROCLAIM dependencies repeatedly blocked startup; later draining of initializers attempted to continue past errors. [P2, P3, P4]

Required regression. Stages 0 and 1 derive and review the selected transitive closure including compile/load-time effects and primitive-to-Lisp cycles; bind every required initializer to its prerequisite state and completion result; seed the loader's own dependencies before loading later bundles. Stage 0 additionally requires the reviewed seed set, conservative indirect-edge fixed point, unresolved-edge blocking, initializer ordering and external-trace reconciliation in contracts/census.md. S0-LL15-b/c exercise the actual instrumentation and independently specified omission mutants. A no-load build path does not prove loading; required libraries are not deferred because their breadth stage is later.

First acceptance: Stage 0. Extensions: Stage 1. Regression: all later stages in scope. Outline sections: 07, 08. Status: contract specified; execution and acceptance tracked in STATUS.md.

#### LL16  /  Numeric primitives must terminate and compute correctly before reuse

Reported: MOD/REM/division/hash code was rewritten around compiler defects; LENGTH and SEQUENCE-TYPE fallbacks recursed until primitive paths were supplied; the float-multiplication report contains hypotheses, not a completed diagnosis. [P2, P16]

Required regression. Stage 1 for the required numeric subset, then Stages 2 and 4 for breadth: fixnum bounds, large and negative shifts, integer length, quotient/remainder and bignum carry/borrow compared with an independent oracle; mixed fixnum/float operations and compiler-policy variations; dispatch inspected for fallback recursion. A depth or fuel guard is not a semantic fix; the separately approved FP condition policy is preserved.

First acceptance: Stage 1. Extensions: Stages 2, 4. Regression: all later stages in scope. Outline sections: 02, 05. Status: contract specified; execution and acceptance tracked in STATUS.md.

### A.4  Dynamic state and execution

#### LL17  /  Single-thread execution still requires dynamic bindings

Observed: symbol-value fallbacks read and write the global cell on a single-thread rationale while the kernel checks TLB state for a special variable — a contract inconsistency requiring tests. [P3, P10]

Required regression. Stage 1 binding subset and Stage 2 full runtime compare compiled special access, SYMBOL-VALUE, SET and nested LET bindings; verify restoration after errors, nonlocal exit and host suspension; keep two Workers' bindings independent at Stage 2; test unbound markers and binding-index growth without replacing lexical closure state with process globals.

First acceptance: Stage 1. Extensions: Stage 2. Regression: all later stages in scope. Outline sections: 04. Status: contract specified; execution and acceptance tracked in STATUS.md.

#### LL18  /  GC proof requires visible reclamation and complete root coverage

Observed: the Lisp utility file stubs GC and control operations; this does not prove there is no C collector. Reported: a much larger heap reduced allocation failures but exposed representation bugs. [P11, P2]

Required regression. Stage 1 proves the accepted GC path collects, reclaims unreachable allocation and retains every live object on a small heap, including temporaries, bindings, closures, constants, callbacks and multiple values. Stage 2 adds multi-Worker roots, weak/finalization behavior and lifecycle/FOREIGN races. The existing EGC-unavailable policy is preserved.

First acceptance: Stage 1. Extensions: Stage 2. Regression: all later stages in scope. Outline sections: 03. Status: contract specified; execution and acceptance tracked in STATUS.md.

#### LL19  /  Error flags alone do not establish nonlocal control correctness

Observed: dispatch short-circuits pending throws and error handling absorbs failures; startup can clear them and continue; the source describes continued generated calls after errors. [P3, P12]

Required regression. Stages 0–3 test EH transfer across nested frames, observable cleanup, binding/root/stack restoration and absence of post-exit side effects, including cleanup that throws again, missing handlers, recoverable runtime checks and errors inside the debugger. Bootstrap fatal errors remain failures. All multiple values are tested across cleanup, not a scalar checksum.

First acceptance: Stage 0. Extensions: Stages 1–3. Regression: all later stages in scope. Outline sections: 06. Status: contract specified; execution and acceptance tracked in STATUS.md.

#### LL20  /  A host API must prove continuation and GC/lifecycle semantics

Observed: the old step wrapper reserves but ignores its deadline argument; step/status functions are not proof of arbitrary suspension. The new design specifies mailbox blocking and a separate JSPI profile. [P15]

Required regression. Stages 0, 2, 3 and the Stage 5 profiles suspend within nested Lisp state, permit GC and lazy installation, and resume the same continuation with complete values and dynamic state. Test D5’s owner-only CAS acquisition/even-store release, probe-then-load admission with roots retained, parity-only waits, final membership rescan, handoff roots and root reload. Exercise Worker creation/termination and host completion/cancellation under deterministic and randomized schedules, with bounded safepoints. Host completions touch only stable request storage; reclamation requires a completed collection and completion or host-acknowledged cancellation. [D, D5; LL18]

Interrupt-wake slice (S0-LL20-b; R2). Block a FOREIGN Worker in Atomics.wait on unfinished I/O. An interrupt sets its pending bit, stores INTERRUPTED on that request’s wake/status word and notifies. Require admission and root reload before interrupt/debugger service, then return to the same outstanding descriptor or observe completion/acknowledged cancellation. Verify GC during wake, completion before/after the interrupt store, and an interrupt during wait rearming. Pending-bit-only, omitted-notify, overwritten-terminal-outcome and early-descriptor-reuse mutants must fail. Wake status cannot erase the durable terminal outcome. [D, D5/D7]

Retain callback/debugger nesting without treating suspension as unwind or discarding live activations; a handler’s genuine nonlocal exit follows the specified cleanup/cancellation path. The request remains owned until the host can no longer write it. Stage 0 uses the hand-built schedule; Stages 2–3 exercise production I/O and break loops; Stage 5 checks equivalent logical outcomes in supported profiles. Record engine features and versions. [D, D5/D7]

First acceptance: Stage 0. Extensions: Stages 2–3, 5. Regression: all later stages in scope. Outline sections: 04, 06. Status: contract specified; execution and acceptance tracked in STATUS.md.

#### LL21  /  Packaging success cannot replace semantic completeness

Observed and reported: required-module installation could continue after failures; merging had validation failures and fallback paths; very large module and heap counts were reported as progress. [P2, P9] Specification basis: shared imports require matching memory and an explicit maximum; atomic accesses can use unshared memory, whereas Wasm waits trap there. [W1]

Required regression. Stages 0, 1 and 3 validate emitted and packed modules, ABI/imports, required inventory, tables and constants. A rejected pack may use only a separately validated, reported unmerged path, never omitted code. Measure bytes, compile/instantiate/install latency and retained-code growth. Exercise publication and first-call installation in another Worker, including one created after redefinition. Preserve distinct closures and old function objects while sharing code. [D, D3/D5]

Entry identity and stubs. Validate the mapping (logical code ID, entry kind) → structural signature, callable slot, module/function and ABI version; numerical ID/slot equality is never required by the image ABI. Under a selected C, C4 or B, one stub is universal for that uniform Lisp-call convention. Under H, one code version may have G and several E_k slots, with stubs keyed by signature and semantic role. Reject wrong-signature and same-type/wrong-role substitutions, missing mappings and reserved-slot collisions. Every allocated callable slot has a matching stub or implementation before dispatch; unused capacity remains non-callable. H-specific tests enter only at the D3/D7 phase that evaluates H. [D, D3/D5/D7]

Profile materialization. D2 selects canonical-template materialization; Stage 0 verifies it and Stage 1 confirms the production path before cross-dump. Stage 5 qualifies complete saved/resident-compiled paths across profiles. Retain template/source hash, materializer/emitter version, profile, limits, imports and resulting binary hash; validate final bytes. Reject missing variants, unsupported transforms and stale hashes. Test limit matching, growth and the selected suspension path; unshared atomic load/store/RMW support does not imply wait support. Separately emitted variants require D2’s explicit reversal decision. [D, D2; W1]

First acceptance: Stage 0. Extensions: Stages 1, 3, 5. Regression: all later stages in scope. Outline sections: 04, 07. Status: contract specified; execution and acceptance tracked in STATUS.md.

### A.5  Provenance, diagnosis and project control

#### LL22  /  Artifact identity and R6 require narrow, explainable comparisons

Observed: build and test paths permit stale artifacts or substitute missing exports; evidence files can be read independently of the measured binary. The follow-up packs demonstrate one x86-64 variance and a repeatable ARM64 cross-build. [P4, P7a, P7e, E2, E5]

Required regression. Every stage binds code, image, modules, ABI schema, host compiler, test revision, options and logs to content hashes and rejects mixed builds; preserves native target files and acode identities mechanically; normalizes only characterized nonsemantic differences, never whole unexplained files; repeats cross-host and native-behavior checks separately and marks unavailable evidence BLOCKED or NOT RUN.

First acceptance: Gate 0. Extensions: Stages 0–6. Standing control. Regression: all later stages in scope. Outline sections: 08; section 2 of this document. Status: contract specified; execution and acceptance tracked in STATUS.md.

#### LL23  /  Diagnostics must identify the exact build and first violated invariant

Reported: an entry number was attributed to the wrong function; last-constant-pool-reference data was discussed as though it located the failure; the ledger admits some described fixes were absent. [P16, P2]

Required regression. All stages emit build-bound module/function/code-ID maps and structured errors with phase, operation, expected/actual representation and relevant state; distinguish last observed activity from the faulting frame; bound diagnostic volume and retain first-error data; debug with minimal reproducers and disassembly; never mark a hypothesized diagnosis or prose-only fix complete. Stage 0 S0-LL23-b additionally proves the initial logical frame/source/lexical map and debug availability contract in contracts/debug-frames.md, including moving roots, suspension and nonlocal restoration. Stage 1 repeats with compiler-generated frames; Stage 3 exercises the real debugger. D3 charges the fixed-policy frame cost before ABI freeze.

First acceptance: Stage 0. Extensions: Stages 1–6. Standing control. Regression: all later stages in scope. Outline sections: 06, 09. Status: contract specified; execution and acceptance tracked in STATUS.md.

#### LL24  /  Scope, status and acceptance changes are explicit project decisions

Observed: the old README, TODO and plan describe different states, and the TODO lists later work as both completed and pending; the old one-blocker-deep rule encouraged workarounds. [P2, P8]

Required regression. Every stage maintains one current ledger, a separate dated history, explicit evidence scope and links to tests and changes; preserves accepted Gate 0 and repeatability results without promoting them to Stage 0 completion; tracks unresolved dependencies instead of percent complete by function count. Agents may reduce an approved milestone's scope but cannot redefine passing, remove R6 or replace shared-heap threading with isolated runners.

First acceptance: Stage 0. Extensions: Stages 1–6. Standing control. Regression: all later stages in scope. Outline sections: 08, 09. Status: contract specified; execution and acceptance tracked in STATUS.md.

Carry-forward rule. Reuse proven fixtures, target-validated ABI checks, the distinction between saved heap and host code state, and small verified components from the historical tree. Do not import permissive bootstrap acceptance, name-based identity repair, semantic no-ops or historical green labels as a working foundation. Every retained component inherits the LL obligations that apply to it.

## 5  /  OBLIGATION INDEX

### First acceptance and scheduled extensions

Derived from the metadata in section 4. This table schedules new or repeated acceptance slices; it is not the complete regression inventory. Every later gate also carries forward all earlier in-scope slices and the standing controls. No new extension at Stage 6 means continuing obligations, not no tests.

| Stage | First acceptance | Scheduled extensions |
| --- | --- | --- |
| Gate 0 | LL22: current U1 native baseline identity | Historical H1 acceptance retained separately. |
| Stage 0 | LL01, LL02, LL04, LL05, LL07, LL08, LL13, LL15, LL19, LL20, LL21 | None |
| Stage 1 | LL06, LL09, LL10, LL11, LL12, LL14, LL16, LL17, LL18 | LL01, LL02, LL04, LL05, LL07, LL08, LL13, LL15, LL19, LL21 |
| Stage 2 | None | LL02, LL13, LL16, LL17, LL18, LL19, LL20 |
| Stage 3 | None | LL02, LL11, LL19, LL20, LL21 |
| Stage 4 | None | LL16 |
| Stage 5 | None | LL04, LL09, LL10, LL12, LL14, LL20, LL21 |
| Stage 6 | None | None |
| Every stage | LL03, LL22, LL23, LL24 | Standing controls at Stages 0–6; LL22 also covers Gate 0. |