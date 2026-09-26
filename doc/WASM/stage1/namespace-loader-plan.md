# Namespace and loader plan — from projected READY to a cross-loaded boot

```
DOC-ID        NSL-P2 (P1 was a7f554e3, imported at 63f15f6d; P2 folds in Codex's per-ID review)
STATUS        DIRECTION ADOPTED by the user (U-9, U-12); Q-A adopted as STAGE1-READY-DECISION-A1;
              packet contents, sizes and order below remain Codex's implementation choices
AUTHOR        Claude (Fable 5.1), 24 September 2026, after audit 175
READER        Codex, as Stage 1 author; reply per ID where P2 changed something
BASE          wasm2 at 63f15f6d (R10–R12 integrated at 4730cbae; R13 proposed at ce5e125b)
TOUCHES       doc/WASM/stage1/ready-decision.json and doc/WASM/decisions.md (the Q-A amendment,
              previous commit on this branch); no compiler, runtime, kernel, contract or inventory
CHANGES       §11 lists every item P2 changed and the review ID it answers
```

## 0. How to read this

Every item carries an ID; IDs from P1 are kept, amended items are marked
`(P2)`, new items continue the numbering. Reply per ID with `AGREE`,
`DISAGREE`, `AMEND` or `UNVERIFIED` only where P2 changed something or where
a P1 reply was `UNVERIFIED`; silence on an unchanged `AGREE` item is assent.
Adoption of the direction and of Q-A is recorded; acceptance of every packet
remains the user's.

## 1. Relayed user direction

- U-9. User, 24 September 2026, after audit 174: "CODEX is going to work on the
  stream constructor, and then we will adopt your proposal and move to
  namespaces. In your work branch, please put together a detailed plan it can
  use as a possible solution."
- U-10. The proposal referred to: freeze the projection surface, redirect to
  S1-NAMESPACE-a then S1-LOADER-a, meet the missing definitions in the order
  the boot needs them, through the mechanism the exit criteria score. The
  user's framing: "Something has to get through this to stage 2, and that is
  likely a fairly complete lisp."
- U-11. "Possible solution" is the user's phrase: Codex may propose another
  design against the same criteria; Codex's review chose to amend rather than
  replace.
- U-12 (P2). User, 24 September 2026, after audit 175: "Yes to QA. Make the
  change and write NSL-P2 on the plan branch folding in Codex's amendments."
  Q-A is entered as `STAGE1-READY-DECISION-A1` in `ready-decision.json` with
  a `decisions.md` entry; the superseded sentences are preserved there.
- U-13 (P2). Nothing else here is the user's statement.

## 2. Where the tree is (facts at 63f15f6d)

- F-1. Ledger 21 accepted / 12 missing / 0 unreviewed of 33; every missing
  criterion "waits on the bootstrap existing" (L-2 of `bootstrap-throughput.md`).
- F-2 (P2). R10–R12 are accepted and integrated at 4730cbae: the backend
  `a507228e…`, `wasm32-arch`, `w32-lap`, the lock branches in `l0-aprims` and
  `l0-misc`, the collector kinds 71/79/66/50 and the image loader's 71/79.
  Accepted executed originals: 568 / 531 non-NIL. R13 (ce5e125b) proposes
  575 / 535 with 612 classes and 54 GFs, one thread-local intrinsic, one
  `#+wasm32-target` line in `l1-streams.lisp` and the pool kind 82; it is the
  last projection round by Codex's statement. The projection driver,
  `ready/startup.lisp`, `ready/worker.mjs`, `graph.lisp`, `clos-methods.lisp`,
  `condition-methods.lisp` and `numeric-files.lisp` are scaffolding; 35 startup
  callbacks and 235 replacement rows are its open debt.
- F-3 (P2). The unchanged compiler's last recount admits 2,044 of the 2,231
  counted level-0/1 definitions (audit 160; 2,060 at audit 159 was corrected).
  Neither that count nor executed originals measures ordinary FASL
  publication: `wasm32-pass2` refuses `:native-fasl-publication` unless the
  fixture's module-result tag is bound (`wasm32-backend.lisp:29`), so today no
  `COMPILE-FILE` for wasm32 produces a loadable artifact. That, not a missing
  level-0 function, is the first boundary NSL-2 meets.
- F-4 (P2). Accepted pieces the loader stands on:
  - S1-LL09-a symbols (`symbols.c`, `symbol-adapter.wat`: D1 symbols,
    native-shaped package tables, sealed graph, bounded);
  - S1-LL10-a constant pools; S1-LL12-a closures and callable metadata; D1
    32-byte function objects with the pool pointer at raw offset 24;
  - S1-LL13-a initialization (`initialization/owner.mjs`);
  - S1-LL21-a materialization (`materializer.mjs`) and S1-LL21-b granularity
    — `bundle.mjs` is integrated (bootstrap-core/-admission/-carry records),
    one generated function per module, code-set map from logical code ID to
    module, roles, slots, ABI and layout versions;
  - `loader.mjs` / `installer.mjs` (single-Worker lazy installer, paired
    tables, catalog as integrity authority); `bootstrap-install.mjs` and
    `bootstrap-schedule.mjs` (digest-bound initializer schedule);
  - S1-LL18 collector, owner and allocation retry; `heap-image.mjs` (D1 heap
    writer and loader with relocations, roots, code digest, refusal before
    publication; admitted kinds enumerated);
  - startup inventory: `startup-seeds` snapshot and `startup-resets/selection.json`
    (35 callbacks, 13 executed), LL15-b/c worklist of 16,169 functions in 167
    units, `ready/dispositions.py` marking all 35 undischarged;
  - `xdump/xwasm32-fasload.lisp`: registered (`lib/systems.lisp:118`), every
    writer entry refusing `:coordinated-heap-code-writer`; `level-0/WASM32/
    w32-lap.lisp` and `w32-prims.lisp` in the native-qualified identity; the
    Wasm foreign-type descriptor already registered with the backend;
  - every compiler lowering and source branch from READY R5–R13, none of
    which is READY-specific.
- F-5 (P2). The native mechanism reused: `cross-xload-level-0 :wasm32`
  (`xdump/xfasload.lisp:1983`) — not `xload-level-0`, which selects the host
  backend — binds the target backend inside `with-cross-compilation-target`,
  cross-compiles `level-0`, and `xfasload` (`:1024`) loads the fasls into a
  simulated target heap and writes the boot image; the kernel runs
  `%toplevel-function%` (`level-0/nfasload.lisp:1205`), which runs the
  cold-load functions, resizes package tables, assigns binding indices and
  hands to `l1-boot`, which `%fasload`s level-1 (`l1-boot-2.lisp:31,41`) to
  `startup-ccl`. For wasm32 the dumper, the simulated heap, static-space
  setup and the code representation all need qualification (Q-9, Q-11); it
  is more than registering an opcode.

## 3. The end state the criteria describe

Quoted from `inventory.json`; unchanged from P1 (Codex: AGREE).

- C-1. S1-NAMESPACE-a: "The read-only file namespace serves named byte
  sources with stat, open, positioned read and close through the mailbox in
  the full profile and a promise in the JSPI profile, enough for the loader
  manifests and LOAD of source and precompiled bundles; realpath is a pure
  function over the virtual namespace with no symlinks; probe-file and
  truename resolve against it only; foreign-types initialization needs no
  interface database."
- C-2. S1-LL15-a: "Every initializer of the retained startup worklist that
  the bootstrap selects completes in a fresh instance, bound to prerequisite
  state and completion with loader dependencies seeded first, in the phase
  order the bootstrap design review fixes; … an omitted required module fails
  loading and a no-load path cannot pass; the accepted S0-LL15-a discipline
  is repeated through the real build path."
- C-3. S1-LL14-a: "The coordinated bootstrap heap and code set load into a
  fresh instance with builder caches absent and no binding repair; graph
  ownership, pointer ranges, shared references, constants and code metadata
  validate; no serialized pointer refers to allocator, scratch, engine or
  host state; two loaded instances diverge independently and later loading
  still works."
- C-4. S1-LOADER-a: "A one-Worker image loader boots the bootstrap heap and
  code set to a ready state with canonical NIL, T and symbol hash behavior,
  the specified error-service transition, and every closure initializer
  complete; the ready artifact names the build, image and module identities."
- C-5. Outline §07: "Missing functions are resolved in the cross-compilation
  and cross-loading pipeline — never by name-based heap scans, replacement
  stubs or suppression of initialization errors."
- C-6 (P2). Outline §05: the bootstrap heap and code set come through the
  loader; "Runtime LOAD of source and precompiled bundles, and loading newly
  compiled bundles, remain requirements." Read with C-1: the delivered
  bootstrap artifact is the heap plus the code set; a fasl is the producer's
  intermediate representation; what the target loads at runtime is an
  explicitly versioned, self-contained bundle (Q-10). No executable native
  code vector and no legacy kernel cold-loader is reintroduced.

## 4. The design in one paragraph

- D-1 (P2). Replace projection of the native heap with CCL's own cold load,
  retargeted. Cross-compile `level-0` for wasm32 with the existing backend;
  each function's code is a Wasm module under a logical code ID and the fasl
  carries what the cross-loader needs to place a D1 function object and to
  emit that module into the code set. Cross-load those fasls on the host with
  `xfasload` under a real `*wasm32-xload-backend*` into a simulated D1 heap,
  and write the two artifacts of outline §07 — the bootstrap heap
  (`heap-image.mjs` format, kinds extended only as the selected build emits
  them) and the code set (`bundle.mjs` inventory). Boot that image in one
  Worker: run `%toplevel-function%`'s cold-load work, then let `l1-boot` load
  level-1 as versioned bundles through the read-only namespace, with the
  selected startup worklist's initializers running where the native trace
  places them, until `startup-ccl` reaches its ready point without an init
  file. Everything the boot finds missing is a row in an ordered log and is
  fixed where BT-4/BT-8 say — a backend lowering, a `#+wasm32-target` branch
  in the defining file, a `w32-lap.lisp` definition, a host service with a
  BT-5 justification, or an explicit `EXCLUDED` disposition with its
  authority — never by a stub, a heap scan or a caught error (C-5).
- D-2. Nothing changes about *which* definitions are missing; everything
  changes about how they are found and closed: a load-order stop the boot
  itself reports, closed by a compiler or source change that survives into
  Stage 2, instead of a census row closed by projecting native state and
  writing a witness.
- D-3 (P2). Three loaders are distinct and named as such everywhere below:
  the **host cross-loader** (`xfasload` on macOS, producing the artifact), the
  **target bundle installer** (the accepted `loader.mjs`/`installer.mjs` path
  installing modules from the code set into the Worker), and the **target
  fasloader** (`%fasload` compiled for wasm32, consuming bundles through the
  namespace after boot0).

## 5. Work packets

Discipline unchanged: one evidence packet, pins, native oracle for every
behavioural claim, R6/R6a when a shared CCL source changes, the R6
source-location allowance shown for every file gaining `#+wasm32-target`
branches, Claude review before integration, BT-13 tiers, BT-16–19 hygiene,
the admission-predicate rule. Packet counts in P1 were unverified; P2 gives
none (P2-5, P3-4, P4-5): the first real stops size the work, and related
fixes are batched — a stop is not a packet.

### NSL-1 — Read-only namespace (S1-NAMESPACE-a)

- P1-1 (P2). Host side: `runtime/wasm32/namespace.mjs`, a virtual tree built
  from a manifest the owner admits before any Lisp runs; every byte source is
  resolved and hash-checked at admission (a hash alone cannot supply bytes;
  no host-path fallback). Operations `stat`, `open`, `pread`, `close`,
  `realpath`, and `opendir`/`readdir`/`closedir` only where a selected caller
  needs them (P1-2). Semantics follow `level-1/l1-streams.lisp:5690–5698`: a
  positioned read at or beyond EOF returns zero bytes and a read crossing EOF
  is short — normal outcomes, not refusals; the directory end marker is
  likewise distinct from failure. Refusals, each with a code and a directed
  case: unknown name, a directory opened as a file, a closed handle, a
  negative or overflowing offset or count, a wrong kind. `realpath` is a pure
  function of the manifest (no symlinks, no host paths). Served through the
  D5 mailbox in the full profile; the one-Worker synchronous caller uses that
  transport and never blocks the browser main thread. The JSPI promise
  variant is deferred with the JSPI profile (decision of 16 September); the
  criterion keeps it and the packet says it ships mailbox-only.
- P1-2 (P2). Lisp side: `#+wasm32-target` branches (BT-8) of the file
  primitives the kernel-imports census classifies as host services
  (`kernel-imports.v1.md:46–49`) at the sites where `l0-io.lisp`,
  `l1-files.lisp` and `l1-sysio.lisp` call them, so `probe-file`, `truename`,
  input file streams and `%fasload`'s reader see the namespace only. The
  `ccl:` root and the current directory are manifest inputs. The comparison
  against native covers byte counts, EOF, positioning, path resolution and
  handle lifecycle, not only returned data.
- P1-3 (P2). Interface database: `l1-boot-2.lisp:317–318` loads
  `FOREIGN-TYPES` and calls `(install-standard-foreign-types *host-ftd*)`.
  Reuse the Wasm foreign-type descriptor already registered with the backend
  and the existing native-FFI refusal: standard foreign-type initialization
  runs without opening a database; every read-time foreign reference (`#_`,
  `#$`) in a selected file is resolved or excluded at its defining source
  boundary as a P5-1 `FOREIGN-CALL` row, never disguised as a runtime lookup
  and never answered by inventing an excluded POSIX capability.
- P1-4. Evidence: a generated-Lisp fixture (unchanged compiler) over a manifest
  with colliding names, a missing name, a directory and an empty file,
  compared to native CCL on a real directory laid out identically; each of
  the criterion's clauses with a directed case; refusals preserve state.
  Moves no BT-1 number and says so.
- P1-5. Independent of everything below; the user's selected next step.

### NSL-2 — Cross-load writer: level-0 heap and code set (producer for S1-LL14-a)

- P2-0 (P2, first step, from Q-9). Before any file set: one ordinary
  `DEFUN` with a constant and one top-level effect, compiled by
  `COMPILE-FILE` under `with-cross-compilation-target (:wasm32)` with the
  module-result refusal lifted for real publication, loaded by the new
  cross-loader into a simulated heap, and written as heap plus code set —
  the smallest artifact that proves the dumper, the heap, the function-object
  placement and the code-set emission together. Constant-only or empty fasls
  establish nothing. Then the ordered level-0 inputs of `cross-xload-level-0`
  are enumerated with their first stops.
- P2-1 (P2). Fasl representation for wasm32: the data ops are CCL's; a
  target-specific function op in `nfcomp.lisp`'s dispatch carries the D1
  function object's immediates and pool through the ordinary ops plus the
  logical code ID, entry roles and the module (bytes inline or by digest with
  a side file — Codex's choice; the code set must be reconstructible from the
  fasl set alone). Every other target's dumper and loader are unchanged
  (R6/R6a). The fasl is producer-side representation (C-6); it is not what
  the target loads at runtime.
- P2-2 (P2). `*wasm32-xload-backend*` made real in `xdump/xwasm32-fasload.lisp`:
  `:static-space-init-function` (NIL and T at their D1 addresses,
  `*nil-relative-symbols*`, static package tables), the function-op loader
  placing the D1 function object with its pool and recording the code ID, and
  the writer. `:closure-trampoline-code`, `:udf-code` and an image base
  address stay NIL: no instruction word, native trampoline or host address is
  admissible. The writer emits the heap in `heap-image.mjs`'s record format —
  bytes, relocations, root slots (`%toplevel-function%`,
  `*xload-cold-load-functions*`, `*early-class-cells*`, the package list, the
  binding-index table), code digest — preserving the accepted D1
  representation, identities, GC roots and transactional admission, and
  extending the admitted heap-kind inventory only for kinds the selected
  build emits, each with a fixture; no promise of every D1 kind in the first
  writer. The code set is a `bundle.mjs` inventory. No allocator pointer or
  engine table index is serialized (C-3).
- P2-3. Level-0 file set: `cross-xload-level-0 :wasm32` with
  `:subdirs '("ccl:level-0;WASM32;")`, i.e. the real ordered list with
  `w32-lap.lisp` and `w32-prims.lisp` in place of the x86 LAP files, compiled
  in their whole-file environments including top-level effects. x86-only or
  kernel-only forms get `#+wasm32-target` branches or `#-wasm32-target`
  exclusions in place (BT-8), each listed with its kernel-imports
  disposition; R11's `lock_source.py` pattern becomes ordinary source. An
  excluded subsystem is recorded with its authority; it is not an
  unimplemented provider.
- P2-4 (P2). Evidence: the image record and code set for the pinned level-0
  set; shared data semantics, object layout and identity compared against the
  x8632 cross-load of the same files where applicable, with the intended
  differences enumerated (wasm32 reader branches, `w32-*` primitive
  definitions, D1 function metadata, the code op) rather than normalized
  away — exact op-stream equality apart from one op is too strong; the heap
  validated by `heap-image.mjs`'s admission, the code set by `bundle.mjs`;
  hashes of every fasl and module. Headline per M-1. Boot is not claimed.
- P2-5 (P2). Size: not estimated; P2-0 first, then the first stops.

### NSL-3 — Target bundle installation and target fasloader (LOAD of precompiled bundles)

- P3-1 (P2). Bundle: self-contained and versioned — logical code ID, ABI and
  roles, module digest, inline bytes — with an inventory admitted before
  publication, installed through the existing installer path (`loader.mjs`,
  `installer.mjs`), never an ad hoc `pointer -> slot` import. `%fasload`
  compiled for wasm32 reads the bundle through NSL-1 and makes a host request
  carrying a bounded byte span and the logical code ID, with explicit status
  and result publication over the existing mailbox/call contract; the host
  copies or retains the validated bytes under the request's ownership, Lisp
  arguments and constants stay in traced roots across any suspension, and no
  raw pointer into a movable Lisp buffer is retained. Logical code identity
  stays separate from engine slots: a returned slot is not a function object;
  the D1 function object is built by Lisp from the returned entry and the
  bundle's metadata. A module whose digest, roles or signature disagree with
  the inventory is refused before publication; there is no binding repair.
- P3-2. The same path loads a bundle compiled *after* boot (C-6): the packet
  includes one bundle produced by the cross-compiler outside the image and
  loaded by `%fasload` in the booted Worker.
- P3-3. Evidence: a level-1 file as a bundle loaded into a booted level-0
  image (needs boot0); refusals for a truncated bundle, a digest mismatch, a
  wrong role, an unknown code ID, with a failed install leaving the image
  unchanged.
- P3-4 (P2). Size: not estimated; after boot0.

### NSL-4 — boot0, then boot1, then ready (S1-LL15-a, S1-LL14-a, S1-LOADER-a)

- P4-1 (P2). boot0: a fresh Worker with builder caches absent loads the
  NSL-2 image through `heap-image.mjs`'s admission, sets up the TCR from
  `tcr.v2`, the kernel globals level-0 reads, the collector owner and the code
  set through the target bundle installer, and calls `%toplevel-function%`.
  boot0 is reached when the cold-load functions, `%resize-htab` of every
  package, the binding-index pass and `set-documentation` have completed and
  control reaches the native hand-off to `l1-boot`, replaced for boot0 by a
  host-visible mark. boot0 is a diagnostic milestone, not READY and not an
  acceptance. Two instances from one artifact diverge independently (C-3).
  The level-0 code set's module count and fresh instantiation time are
  measured here (Q-14); packaging is not reopened on a proxy before then.
  The harness's fixed binding-vector region (R13 `development/binding-growth`)
  is a known limit a boot will exceed; boot0 replaces it with the TCR's
  declared budget.
- P4-2 (P2). boot1: `l1-boot-2.lisp`'s load sequence over the namespace, in
  native order, each level-1 file cross-compiled to a bundle and loaded by
  the target fasloader. The selected startup worklist's initializers run
  where the retained native cold-start trace places them — joined per
  callback to its boot phase, registration ordinal, compiled body and
  observed effects (Q-13), not assumed to occur at each file load — bound to
  their prerequisite state; an omitted required bundle fails the load (C-2).
  CLOS is built by loading `l1-clos-boot` and `l1-clos` (A1 of
  `ready-decision.json`); class-mode conditions, one Worker, scheduler
  disabled and uncached dispatch are the profile.
- P4-3. ready: `startup-ccl` without an init file, up to the point before the
  listener/toplevel loop (no terminal stream in this profile), with the
  error-service transition of C-4 observed. The ready artifact names the
  build, image and module identities — the image record's digests and the
  code-set inventory's hashes.
- P4-4 (P2). Evidence per boot packet: the ordered boot log (P5-1) as the
  primary record; the native cold-start trace of the same files (outline §07)
  as the load-order oracle; per-file execution comparisons against native for
  the definitions that ran, with the 26,048-comparison corpus as regression;
  heap and code identities; the collector's kinds versus the kinds the heap
  contains. The 35 callbacks come from `startup-resets/selection.json` and the
  retained native trace, each joined as in P4-2.
- P4-5 (P2). Size: not estimated; a packet ends at the next real stop or
  batch of stops, per BT-7.

### NSL-5 — The refusal loop

- P5-1 (P2). The boot log: one row per stop, in order,
  `{index, phase, file, form-or-definition, kind, name, disposition}` with
  `phase` ∈ {`READ`, `COMPILE`, `CROSS-LOAD`, `INITIALIZE`, `RUNTIME`} kept
  distinguishable, and `kind` ∈ {`NOT-COMPILED` (an acode operator or source
  construct the backend refuses), `NOT-LOWERED` (a primitive without a wasm32
  lowering), `NOT-DEFINED` (a callee absent from the image and the loaded
  bundles), `KERNEL-IMPORT` (a census row unsupported in the profile or a host
  service not yet supplied), `FOREIGN-CALL`, `SCHEDULER` / `THREAD`,
  `INITIALIZER-FAILED`}. `disposition` is one of D-1's fix categories or
  `EXCLUDED` with the decision that excludes it.
- P5-2. A target branch replacing a level-0/1 definition body counts against
  the 25-replacement cap (A1 keeps it) and is listed.
- P5-3. Forbidden, restated from C-5: name-based heap scans, replacement
  stubs returning plausible values, a `handler-case` that turns a load stop
  into a warning. The `READY-SCHEDULER-FILE-STOP` handler in
  `numeric-files.lisp` is the pattern to retire: `l1-processes.lisp:614`'s
  `#_sched_yield` becomes a `#+wasm32-target` branch or an `EXCLUDED` row.

### NSL-6 — What carries over, what retires, what waits

- P6-1. Carries over: every compiler lowering and source branch (R5–R13),
  the collector and its kinds, `heap-image.mjs`, installer/loader/materializer,
  `bundle.mjs`, the schedule, the native oracle and R6/R6a, the evidence
  discipline, `w32-lap.lisp`/`w32-prims.lisp`. R13's thread-local intrinsic
  and pool collection are runtime differences native stream code needs, not
  projection machinery, and stay.
- P6-2 (P2). Retires, each only after its replacement actually runs in a
  boot packet and the executed-original regression floor is shown intact:
  READY admission, graph setup, method aliases, class-table rebinding and
  native-state observers (`ready/startup.lisp`, `ready/worker.mjs`,
  `graph.lisp`, `clos-methods.lisp`, `condition-methods.lisp`,
  `numeric-files.lisp`, the class-image projection); the radix initializer
  copy (the top-level form in `level-0/l0-int.lisp` executes instead); the
  stream and lock classifier copies (`l1-clos-boot.lisp:2428, 2488` load
  instead). `symbols.c` and `hash.c` retire only when their Lisp twins
  (`l0-symbol`, `l1-symhash`, `l0-hash`) run from the image with their own
  witnesses; boot0 alone does not establish that. The numeric C kernels stay
  as target primitives beneath their Lisp callers. Remaining replacements are
  listed at each retirement.
- P6-3. Waits: the JSPI promise variant of the namespace; the writable store
  (Stage 3); multi-Worker scheduling; application image save (Stage 5).

## 6. Sequencing

- S-1. NSL-1 first (selected by the user; prerequisite accepted; independent).
- S-2 (P2). NSL-2 next, starting at P2-0 (one definition through a real
  dumper and cross-loader), then the ordered level-0 inputs and their first
  stops, widening until `cross-xload-level-0` runs whole.
- S-3. boot0 with the target bundle installer inside it; the target fasloader
  is needed when boot1 begins.
- S-4. boot1 file by file with NSL-5 dispositions accumulating; NSL-6
  retirements as replacements execute.
- S-5. Inventory edges: LL14-a lists LL15-a as a prerequisite and LOADER-a
  lists LL14-a; the initializers run inside the boot that proves the fresh
  load, so the two may be recorded at the same commit. No inventory wording
  changes.

## 7. Gates and review

- G-1. Packet, pins and replay as today. Tier 2 replay of a boot packet:
  rebuild the image from the pinned sources through the pinned compiler
  session, boot it in a fresh Worker, compare the boot log, heap digests and
  code-set inventory to the packet's. Source-identity reuse and the bounded
  cache apply; a compiler or runtime change needs full relevant execution; no
  second identical native rebuild merely to publish a record.
- G-2. Native R6/R6a per shared-source change; the R6 source-location
  allowance (reader matrix and decoded-code comparison, as
  `ready-runtime-acceptance/readers.py` does it) for every file NSL-2/NSL-5
  give a branch.
- G-3. Admission-predicate rule for every refusal in NSL-1, NSL-2's writer
  and NSL-3's installer: a directed case or a recorded equivalence.
- G-4. Review cadence per R-1..R-5; each audit opens with §10's headline.

## 8. Decisions

- Q-A. **Adopted** (U-12) as `STAGE1-READY-DECISION-A1`: `decisions.image`
  now says READY is reached by cross-loaded level-0 and target-loaded
  level-1 through the namespace, with CLOS built on the target;
  `decisions.sequencing` points at NSL-1 and the NSL packets; the superseded
  sentences are preserved in `amendments[0]`; coverage, conditions,
  concurrency, dispatch, the floor and the cap are unchanged.
- Q-B (P2). Headline metric per §10, with executed originals and the
  accepted floor kept visible; the first NSL packets move neither BT-1
  number and say so. Recorded as part of U-12's adoption of this plan; Codex
  may still amend the wording of M-1.
- Q-C (P2). Settled exclusions carry their existing authority: POSIX layer
  (earlier ruling), threads and scheduler (READY decision), JSPI deferred as
  a profile (16 September), interface database (C-1). No new permission is
  needed to cite them in `EXCLUDED` rows.
- Q-D (P2). Resolved: R10–R12 are integrated at 4730cbae. Whether R13 is
  integrated before NSL-1 is the user's call; NSL-1 does not depend on it.

## 9. Questions still open for Codex

- Q-9 (P2). Answered as UNVERIFIED with a method; P2-0 adopts the method. The
  first NSL-2 packet reports which level-0 files cross-compile and which stop,
  and where, once P2-0 exists.
- Q-10 (P2). Codex's proposed design is adopted into P3-1. Open: the concrete
  bundle format version, the host request signature, and where the D1
  function object is built.
- Q-11 (P2). `lib/nfcomp.lisp:2221–2241` binds the TARGET/OS nicknames with
  unwind restoration and `cross-xload-level-0` uses it (verified). The writer
  needs a directed 4-byte-cell / 8-byte-cons case and a host-width-leak
  control over its output heap; both belong to P2-0.
- Q-12 (P2). Answered; folded into P6-2.
- Q-13 (P2). Open: the per-callback join (phase, ordinal, compiled body,
  observed effect) from `startup-resets/selection.json` and the retained
  native trace; the current symbol/effect join is not that proof.
- Q-14 (P2). Open until boot0 exists.
- Q-15 (P2). Answered: extend and compose the existing runtime pieces; the
  missing work is connecting CCL's file compiler, cross-loader and target
  loader to those contracts.
- Q-16 (new). Which level-0 files contain read-time foreign references or
  `#+x8632-target`-only forms that need a wasm32 branch before
  `cross-xload-level-0` can read them at all (the `READ` phase of P5-1)?
- Q-17 (new). The one-Worker profile's TCR budget for the binding vector and
  value stack at boot0, so that boot0 does not inherit the harness's fixed
  region (P4-1).

## 10. Measurement

- M-1 (P2). Headline for every NSL packet, in the README's first line and in
  `STATUS.md`, three counts kept distinct: `files cross-compiled: a of N`,
  `files cross-loaded: b of N`, `files target-loaded: c of N` (N from the
  native cold-start trace, with the manifest identity of the denominator
  recorded), plus `first stop: <index, phase, kind, name>` and `open rows by
  kind`. Before boot0, `c` is zero, not a producer count. The two BT-1 numbers
  (admitted as written; executed and matching native) and the accepted floor
  (568 / 531) remain as the next lines; LL15-c/d are not silently replaced by
  a file count.
  Adopted [BT-20](bootstrap-throughput.md) counts successful whole-file
  compilation and source-removed cross-loading as they happen, including
  packet drivers. Acceptance and integration are separate state; the accepted
  original-execution floor is now 575/535.
- M-2. A packet that moves none of M-1 says so in its first line.
- M-3. Cost lines stay: author wall time by phase, reviewer tier and time,
  evidence bytes retained, and product Lisp lines changed (BT-23).

## 11. Change log from P1 (each with the review ID it answers)

| Item | Change | Answers |
|---|---|---|
| Header, §0 | P2 status; reply only on changed items | — |
| U-12, U-13 | Q-A adoption recorded | Q-A |
| F-2 | R10–R12 integrated; R13 facts; scaffolding list corrected | F-2, F-4, Q-D |
| F-3 | 2,044 (audit 160); no FASL publication exists (`wasm32-backend.lisp:29`) | F-3, Q-9 |
| F-4 | `bundle.mjs` integrated; foreign-type descriptor exists; `dispositions.py` | F-4, Q-15, P1-3 |
| F-5, D-1 | `cross-xload-level-0`; dumper/heap/static/code representation need qualification | F-5, D-1 |
| C-6, D-3 | heap + code set delivered; fasl is producer IR; three loaders named | C-6, P2-1, P3-1, P4-x |
| P1-1 | EOF and short reads are successes; directory end marker; resolved and hash-checked bytes; refusal list | P1-1 |
| P1-2 | comparison covers counts, EOF, positioning, handles; directory ops only where needed; mailbox transport | P1-2 |
| P1-3 | reuse the registered descriptor and native-FFI refusal; resolve/exclude at source boundary | P1-3 |
| P2-0 | first step: one definition through dumper and cross-loader | Q-9 |
| P2-2 | preserve D1/roots/transactional admission; kinds only as emitted | P2-2 |
| P2-4 | enumerate intended fasl differences; compare against x8632 where applicable | P2-4 |
| P2-5, P3-4, P4-5 | no packet-count estimates; batch fixes | P2-5, P3-4, P4-5 |
| P3-1 | versioned bundle; existing installer; request ownership and rooting; slot ≠ function object | Q-10, P3-2 |
| P4-1 | boot0 diagnostic, not READY; measure modules/instantiation there; binding-vector limit | P4-1, Q-14, audit 175 |
| P4-2, P4-4 | callbacks joined to real phase via native trace | P4-x, Q-13 |
| P5-1 | phase column; distinguishable failures | P2-3, P5-1 |
| P6-2 | retire only after replacement runs; floor shown; symbols/hash conditions | P6-2, Q-12 |
| Q-A–Q-D | statuses updated | Q-A, Q-B, Q-C, Q-D |
| Q-16, Q-17 | new questions | — |
| M-1 | three distinct counts; first stop; denominator identity; BT-1 lines kept | M-1, Q-B |
