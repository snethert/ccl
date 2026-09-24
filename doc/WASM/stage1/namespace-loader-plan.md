# Namespace and loader plan — from projected READY to a cross-loaded boot

```
DOC-ID        NSL-P1
STATUS        PROPOSAL — not adopted, not a decision record, no gate or ledger effect
AUTHOR        Claude (Fable 5.1), 24 September 2026, after audit 174
READER        Codex, as Stage 1 author; reply per ID
BASE          wasm2 at f8180b52 (READY R12 proposed; R10–R12 unreviewed stack; audit 174 at 4ccd89ea unlanded)
TOUCHES       nothing: no compiler, runtime, kernel, contract, inventory or accepted record
SUPERSEDES    nothing until the user adopts it; §8 lists the decisions it would need
```

## 0. What is asked of the reader

Every item carries an ID. Reply per ID with `AGREE`, `DISAGREE`, `AMEND` or
`UNVERIFIED`, with file and line, an executed probe or a specification link.
Section 9 lists the questions that need an answer before the first packet.
Do not implement from this document until the user adopts it; adoption, any
amendment to `ready-decision.json`, and acceptance of any packet are the user's.

## 1. Relayed user direction

- U-9. User, 24 September 2026, after audit 174: "CODEX is going to work on the
  stream constructor, and then we will adopt your proposal and move to
  namespaces. In your work branch, please put together a detailed plan it can
  use as a possible solution."
- U-10. The proposal referred to is the one given in reply to "Was the CLOS scan
  and copy decision a bad idea?" and "if i switch to namespace then bootstrap,
  wont I run into the same missing stuff anyway?": freeze the projection
  surface, redirect to S1-NAMESPACE-a then S1-LOADER-a, meet the missing
  definitions in the order the boot needs them, through the mechanism the exit
  criteria score. The user's stated understanding: "Something has to get
  through this to stage 2, and that is likely a fairly complete lisp."
- U-11. Nothing else here is the user's statement. "Possible solution" is the
  user's phrase: this is one design, and Codex may propose another against the
  same criteria.

## 2. Where the tree is (facts at f8180b52)

- F-1. Ledger 21 accepted / 12 missing / 0 unreviewed of 33. The missing set is
  L-2 of `bootstrap-throughput.md` plus S1-LL15-c/d: every one of them "waits
  on the bootstrap existing".
- F-2. READY R12 executes 568 upstream definitions (531 non-NIL) from a
  projected image of 612 classes and 50 generic functions copied from the
  pinned native heap, one caller with a hand-written native witness per
  function. Three rounds on 24 September added 18. The projection driver,
  `ready/startup.lisp`, `ready/worker.mjs`, `graph.lisp`, `clos-methods.lisp`
  and `condition-methods.lisp` are Stage 1 scaffolding by every README's own
  statement; 35 startup callbacks and 228 replacement rows are its open debt.
- F-3. The unchanged compiler admits about 1,950 of the 2,231 counted level-0/1
  definitions (Codex's recount after audit 157). Admission is not the
  bottleneck; getting admitted definitions to run *together*, in load order,
  is.
- F-4. Accepted and integrated pieces the loader can stand on, with what each
  gives:
  - S1-LL09-a symbols — `runtime/wasm32/symbols.c`, `symbol-adapter.wat`: D1
    symbols, native-shaped package tables, sealed package graph, bounded.
  - S1-LL10-a constant pools; S1-LL12-a closures and callable metadata; D1
    32-byte function objects with the pool pointer at raw offset 24
    (`runtime/wasm32/README.md`).
  - S1-LL13-a initialization — `initialization/owner.mjs`: process-once versus
    per-Worker setup, layout validation, late Workers.
  - S1-LL21-a materialization and S1-LL21-b granularity — `materializer.mjs`,
    `bundle.mjs` (proposal): one generated function per module, a code-set map
    from logical code ID to module, roles, slots, ABI and layout versions.
  - `loader.mjs` / `installer.mjs`: the single-Worker lazy installer, paired
    tables, catalog as integrity authority; `bootstrap-install.mjs` and
    `bootstrap-schedule.mjs`: a digest-bound initializer schedule.
  - S1-LL18 collector, owner and allocation retry — `collector.c`,
    `collector-owner.mjs`, `allocation-service.mjs`; admitted object kinds are
    enumerated in `collector.c` (R10–R12 add 71, 79, 66, 50 in isolation).
  - `heap-image.mjs` (from class-image): a D1 heap writer and loader with
    relocations, root slots, a code digest and refusal before publication.
  - Startup inventory: `startup-seeds` snapshot (`image.json.gz`) of the 35
    registered startup callbacks; `startup-resets` executes 13 of them; LL15-b/c
    retained worklist of 16,169 functions in 167 compilation units.
  - `xdump/xwasm32-fasload.lisp`: the wasm32 cross-loader is *registered*
    (`add-xload-backend`, `lib/systems.lisp:118`) and every writer entry refuses
    with `:coordinated-heap-code-writer`. `level-0/WASM32/w32-lap.lisp` (555
    lines) and `w32-prims.lisp` (613) exist as the target's LAP-equivalent
    files and are already in the native-qualified identity.
  - Compiler lowerings from READY R5–R12: four integrated at 7668f42d; complex
    floats, lock token, structure cells, fixnum-width types and string byte
    copy isolated in the R10–R12 stack. All of them are needed under this plan
    too; none is READY-specific.
- F-5. The native mechanism this plan reuses is CCL's own: `xload-level-0`
  (`xdump/xfasload.lisp:1980`) cross-compiles `level-0` for a target and
  `xfasload` (`:1024`) loads the fasls into a simulated target heap on the host
  and writes the boot image; the kernel starts that image and runs
  `%toplevel-function%` (`level-0/nfasload.lisp:1205`), which runs the cold-load
  functions, resizes the package tables, assigns binding indices and hands to
  `l1-boot`, which `%fasload`s level-1 (`level-1/l1-boot-2.lisp:31,41`) up to
  `startup-ccl` (`l1-boot-lds.lisp`). Every CCL port boots this way; only the
  backend-xload-info record (`xx8632-fasload.lisp` is the 32-bit precedent) and
  the target's LAP files differ.

## 3. The end state the criteria describe

Quoted from `inventory.json` so the plan is checked against the words, not a
paraphrase.

- C-1. S1-NAMESPACE-a (prerequisite S1-LL13-a, accepted): "The read-only file
  namespace serves named byte sources with stat, open, positioned read and
  close through the mailbox in the full profile and a promise in the JSPI
  profile, enough for the loader manifests and LOAD of source and precompiled
  bundles; realpath is a pure function over the virtual namespace with no
  symlinks; probe-file and truename resolve against it only; foreign-types
  initialization needs no interface database."
- C-2. S1-LL15-a: "Every initializer of the retained startup worklist that the
  bootstrap selects completes in a fresh instance, bound to prerequisite state
  and completion with loader dependencies seeded first, in the phase order the
  bootstrap design review fixes; … an omitted required module fails loading and
  a no-load path cannot pass; the accepted S0-LL15-a discipline is repeated
  through the real build path."
- C-3. S1-LL14-a (prerequisites LL09, LL10, LL12, LL15, LL13): "The coordinated
  bootstrap heap and code set load into a fresh instance with builder caches
  absent and no binding repair; graph ownership, pointer ranges, shared
  references, constants and code metadata validate; no serialized pointer
  refers to allocator, scratch, engine or host state; two loaded instances
  diverge independently and later loading still works."
- C-4. S1-LOADER-a (prerequisites LL14-a, NAMESPACE-a): "A one-Worker image
  loader boots the bootstrap heap and code set to a ready state with canonical
  NIL, T and symbol hash behavior, the specified error-service transition, and
  every closure initializer complete; the ready artifact names the build, image
  and module identities."
- C-5. Outline §07, the rule that decides the method: "Complete bootstrap
  artifacts, not binding repair. … Missing functions are resolved in the
  cross-compilation and cross-loading pipeline — never by name-based heap
  scans, replacement stubs or suppression of initialization errors."
- C-6. Outline §05, file-system contract: "This design delivers the bootstrap
  heap and code set through the loader, removing the legacy FASL-driven
  cold-boot path and its particular load-order dependency. … Runtime LOAD of
  source and precompiled bundles, and loading newly compiled bundles, remain
  requirements." Read with C-1: the *level-0 image* comes through the loader as
  a heap-and-code artifact; level-1 and later come through LOAD of precompiled
  bundles over the namespace.

## 4. The design in one paragraph

- D-1. Replace projection of the native heap with CCL's own cold load, retargeted.
  Cross-compile `level-0` for wasm32 with the existing backend into fasls whose
  function op carries a logical code ID and a Wasm module instead of a code
  vector; cross-load those fasls on the host with `xfasload` under a real
  `*wasm32-xload-backend*` into a simulated D1 heap, and write the two
  artifacts of outline §07 — the bootstrap heap (`heap-image.mjs` format,
  extended to every D1 kind) and the code set (`bundle.mjs` inventory, one
  function per module). Boot that image in one Worker: run
  `%toplevel-function%`'s cold-load work, then let `l1-boot` `%fasload` the
  level-1 bundles through the read-only namespace, with the selected startup
  worklist's initializers running where native runs them, until `startup-ccl`
  reaches its ready point without an init file. Everything the boot finds
  missing is a row in an ordered boot log and is fixed where BT-4/BT-8 say —
  a backend lowering, a `#+wasm32-target` branch in the defining file, a
  `w32-lap.lisp` definition, a host service with a BT-5 justification, or an
  explicit unsupported disposition in the kernel-imports census — never by a
  stub, a heap scan or a swallowed error (C-5).
- D-2. What this changes about the missing definitions: nothing about *which*
  ones (U-10), everything about *how they are found and closed*. Today a
  missing edge is a census row that Codex closes by projecting native state
  and writing a witness; under D-1 it is a load-order stop that the boot
  itself reports, and closing it is a compiler or source change that survives
  into Stage 2.

## 5. Work packets

Each packet keeps the existing discipline: one evidence packet, pins, native
oracle for every behavioural claim, R6/R6a when a shared CCL source changes,
Claude review before integration, BT-13 tiers, BT-16–19 hygiene. New evidence
kinds are named where they first appear.

### NSL-1 — Read-only namespace (S1-NAMESPACE-a)

- P1-1. Host side. `runtime/wasm32/namespace.mjs`: a virtual tree built from a
  manifest (`{path, bytes|sha256, kind: file|directory}`) that the owner
  admits before any Lisp runs; operations `stat`, `open`, `pread`, `close`,
  `realpath`, `opendir`, `readdir`, `closedir`; realpath is a pure function of
  the manifest (no symlinks, no host paths); an unknown name, a directory
  opened as a file, a read past end and a closed descriptor are refusals with
  a code, not zero-length successes. Served through the D5 mailbox in the full
  profile. The JSPI promise variant is deferred with JSPI (decision of 16
  September); the packet says so and ships mailbox-only.
- P1-2. Lisp side. `#+wasm32-target` branches (BT-8) of the file primitives
  the kernel-imports census already classifies as host services
  (`kernel-imports.v1.md:46–49`: open, read, lseek, close, fstat, stat, lstat,
  opendir, readdir, closedir, realpath) at the sites where `level-0/l0-io.lisp`,
  `level-1/l1-files.lisp` and `l1-sysio.lisp` call them, so `probe-file`,
  `truename`, `open` of an input file stream and `%fasload`'s reader see the
  namespace only. The `ccl:` logical host and the current directory are host
  inputs of the manifest, not constants.
- P1-3. Interface database. `l1-boot-2.lisp:317–318` loads `FOREIGN-TYPES` and
  calls `(install-standard-foreign-types *host-ftd*)`; the `.cdb` readers live
  under `lib/foreign-types.lisp` and `l0-cfm-support`. Give that initialization
  a `#+wasm32-target` branch that installs the standard types without opening
  a database; a `#_` reference is a load-time refusal row (P5-1 `FOREIGN-CALL`),
  not a lookup that returns garbage.
- P1-4. Evidence. A generated-Lisp fixture (unchanged compiler) that opens,
  stats, reads at offsets, reads a directory and resolves paths against a
  manifest with colliding names, a missing name and a directory, compared to
  native CCL on a real directory laid out identically; refusals preserve
  state. Headline: the criterion's five clauses each with a directed case.
  This packet moves no BT-1 number and says so.
- P1-5. Size: one packet. Independent of everything below; it is the user's
  stated next step after the stream constructor.

### NSL-2 — Cross-load writer: level-0 heap and code set (producer for S1-LL14-a)

- P2-1. Fasl code op for wasm32. `compile-file` under `with-cross-compilation-target
  (:wasm32)` dumps a function as: the D1 function object's immediates and
  constant pool through the ordinary fasl ops, plus one wasm32 op carrying the
  logical code ID, the entry roles and the module bytes (or their hash and a
  side file — Codex's choice; the code set must be reconstructible from the
  fasl set alone). The op is target-specific in `nfcomp.lisp`'s dispatch, as
  other targets' code-vector ops are; every other target's dumper and loader
  are unchanged (R6/R6a).
- P2-2. `*wasm32-xload-backend*` made real. `xdump/xwasm32-fasload.lisp`
  supplies `:static-space-init-function` (NIL and T at their D1 addresses,
  `*nil-relative-symbols*`, the static package tables), the function-op
  loader that allocates the D1 function object with its pool and records the
  code ID, and the writer. `:closure-trampoline-code`, `:udf-code` and an
  image base address stay NIL: a wasm32 image has no instruction words. The
  writer emits the heap in the `heap-image.mjs` record format — heap bytes,
  relocations, root slots (`%toplevel-function%`, `*xload-cold-load-functions*`,
  `*early-class-cells*`, the package list, the symbol binding-index table), a
  code digest — and the code set as a `bundle.mjs` inventory. No host address,
  allocator pointer or engine table index is serialized (C-3).
- P2-3. Level-0 file set. `xload-level-0` for `:wasm32` with `:subdirs
  '("ccl:level-0;WASM32;")`, i.e. the generic level-0 files plus
  `w32-lap.lisp` and `w32-prims.lisp` in place of the x86 LAP files. Files or
  forms that are x86-only or kernel-only get `#+wasm32-target` branches or
  `#-wasm32-target` exclusions in place (BT-8), each listed in the packet with
  its kernel-imports disposition. This is where R11's `lock_source.py` approach
  becomes ordinary source: the target branches live in the files, not in a
  rewriter.
- P2-4. Evidence. The image record and code set for the pinned level-0 set;
  every fasl's data ops compared to the native x8632 cross-load of the same
  file (same fasl op stream apart from the code op); the heap validated by
  `heap-image.mjs`'s admission (ownership, ranges, relocations); the code set
  validated by `bundle.mjs`; hashes of every fasl and module. Headline: files
  of level-0 cross-loaded / total, and the outstanding rows (P5-1) that stopped
  short of a whole set. Boot is not claimed by this packet.
- P2-5. Size: two to three packets (fasl op and dumper; xload heap; the file
  set with its branches). Q-9 asks for the shortest path to the first image.

### NSL-3 — Target fasloader and bundle installation (LOAD of precompiled bundles)

- P3-1. `%fasload` compiled for wasm32 (`nfasload.lisp` is generic apart from the
  code op) reads bytes through NSL-1 and, at the wasm32 code op, hands the
  module bytes and code ID to a host import — `install_code(bytes, length,
  code_id) → entry` — implemented by the existing `loader.mjs` /
  `installer.mjs` path: validate against the code set's expected signature and
  roles, instantiate, install the paired table entries, return the callable
  slot. Rooted call state is preserved across the install (outline §07 lazy
  installation rules); a module whose hash or roles do not match the manifest
  is a refusal before publication; there is no binding repair.
- P3-2. The same path loads a bundle compiled *after* boot (C-6, "loading
  newly compiled bundles"): the packet includes one bundle produced by the
  cross-compiler outside the image and loaded by `%fasload` in the booted
  Worker.
- P3-3. Evidence. A level-1 file cross-compiled to a bundle and loaded into a
  booted level-0 image (needs NSL-4 boot0); refusals for a truncated bundle,
  a hash mismatch, a wrong role, an unknown code ID.
- P3-4. Size: one to two packets, after boot0.

### NSL-4 — boot0, then boot1, then ready (S1-LL15-a, S1-LL14-a, S1-LOADER-a)

- P4-1. boot0. A fresh Worker with builder caches absent loads the NSL-2 image
  through the `heap-image.mjs` admission, sets up the TCR from `tcr.v2`, the
  kernel globals the level-0 code reads, the collector owner and the code set,
  and calls `%toplevel-function%`. boot0 is reached when the cold-load
  functions, `%resize-htab` of every package, the binding-index pass and
  `set-documentation` have completed and control reaches the point where
  native hands to `l1-boot` — replaced for boot0 by a host-visible "boot0"
  mark. Two instances loaded from the same artifact diverge independently
  (C-3). This is the first thing that runs long on the target; instantiation
  time of the level-0 code set is measured here, closing the granularity
  decision the P4 addendum left owed.
- P4-2. boot1. `l1-boot-2.lisp`'s `%fasload` sequence over the namespace, in
  native order, with each level-1 file cross-compiled to a bundle. The
  selected startup worklist's initializers (LL15-b/c, the 35 callbacks of
  `startup-seeds`, of which `startup-resets` already executes 13) run where
  native runs them, in `*lisp-startup-functions*` order, bound to their
  prerequisite state; an omitted required bundle fails the load (C-2). CLOS
  is built by loading `l1-clos-boot` and `l1-clos`, not projected; the
  class-mode conditions, one Worker, scheduler disabled and uncached dispatch
  of `ready-decision.json` are the profile boot1 runs under.
- P4-3. ready. `startup-ccl` without an init file, up to the point before the
  listener/toplevel loop (no terminal stream in this profile), with the
  error-service transition of C-4 observed (the early structured fatal
  diagnostic gives way to the condition system once `l1-error-system` is
  loaded). The ready artifact names the build, image and module identities
  (C-4) — the image record's digests and the code-set inventory's hashes.
- P4-4. Evidence per boot packet (BT-7: a file's worth of work). The ordered
  boot log (P5-1) as the primary record; the native cold-start trace of the
  same files (outline §07: "observed on the native reference with a macOS
  external file-activity tracer") as the oracle for load order; per-file
  execution comparisons against native for the definitions that ran (the
  existing 26,048-comparison corpus stays as regression); heap and code
  identities; the collector's kinds versus the kinds the heap contains.
- P4-5. Size: boot0 is several packets (each ends at the next stop the log
  reports); boot1 is a file per packet through level-1; ready is one packet.
  No count is promised; §10 gives the metric that shows progress.

### NSL-5 — The refusal loop (how "the missing stuff" is handled)

- P5-1. The boot log. One row per stop, in load order:
  `{index, file, form-or-definition, kind, name, disposition}` where `kind` ∈
  {`NOT-COMPILED` (compiler refused the definition: acode operator or
  source construct), `NOT-LOWERED` (an intrinsic/primitive without a wasm32
  lowering), `NOT-DEFINED` (a callee absent from the image and the loaded
  bundles), `KERNEL-IMPORT` (a census row whose profile disposition is
  unsupported or a host service not yet supplied), `FOREIGN-CALL` (`#_`),
  `SCHEDULER` / `THREAD` (excluded by the READY profile), `INITIALIZER-FAILED`}.
  `disposition` names the fix category of D-1 or `EXCLUDED` with the decision
  that excludes it (POSIX layer, threads, terminate-when-unreachable).
- P5-2. Each fix is an ordinary change in the category named, reviewed as
  today; a target branch that replaces a level-0/1 definition's body counts
  against the 25-replacement cap of `ready-decision.json` and is listed.
- P5-3. What is forbidden, restated from C-5 so no packet has to relitigate it:
  no name-based heap scan, no replacement stub that returns a plausible value,
  no `handler-case` around a load that turns a stop into a warning (the
  `READY-SCHEDULER-FILE-STOP` handler in `numeric-files.lisp` is the pattern
  to retire: `l1-processes.lisp:614`'s `#_sched_yield` becomes a
  `#+wasm32-target` branch or an `EXCLUDED` row, not a caught error).

### NSL-6 — What carries over, what retires, what waits

- P6-1. Carries over unchanged: every compiler lowering (integrated and in the
  R10–R12 stack), `collector.c` and its new kinds, `heap-image.mjs`, the
  installer/loader/materializer, the schedule, the native oracle and R6/R6a,
  the evidence discipline, `w32-lap.lisp`/`w32-prims.lisp`, the level-0 target
  branches from R11.
- P6-2. Retires when boot0 executes the same definitions: the projection driver
  and its image (`class-image`, `graph.lisp`, `clos-methods.lisp`,
  `condition-methods.lisp`, `numeric-files.lisp`'s whole-file selection list),
  `ready/startup.lisp` and `ready/worker.mjs` as the qualification harness,
  and — per Q-8 of the throughput directive — `symbols.c` and `hash.c`, whose
  Lisp twins (`l0-symbol`, `l1-symhash`, `l0-hash`) are in the image; the
  numeric C kernels stay as target primitives beneath their Lisp callers.
  Retirement is a packet with the executed-originals regression floor
  (`ready-decision.json`, `coverage_floor`) shown intact, not a deletion.
- P6-3. Waits: JSPI promise variant of the namespace; the writable store
  (Stage 3); multi-Worker scheduling; application image save (Stage 5).

## 6. Sequencing

- S-1. NSL-1 first (user's direction; prerequisite already accepted; independent).
- S-2. NSL-2 next, starting with the fasl code op and the smallest level-0
  prefix that cross-loads (Q-9), then widening the file set until `xload-level-0`
  runs whole.
- S-3. NSL-4 boot0 with NSL-3 inside it (boot0 needs the code set installed; the
  target `%fasload` is needed only when boot1 begins).
- S-4. NSL-4 boot1 file by file, NSL-5 dispositions accumulating; NSL-6
  retirements as their replacements execute.
- S-5. Inventory edges: LL14-a lists LL15-a as a prerequisite and LOADER-a
  lists LL14-a. Under this plan the initializers (LL15-a) run *inside* the boot
  that proves the fresh load (LL14-a); the two are established by the same
  packets and may be recorded at the same commit. No inventory wording changes.

## 7. Gates and review

- G-1. Packet, pins and replay as today. The reviewer's Tier 2 replay of a
  boot packet is: rebuild the image from the pinned sources through the
  pinned compiler session, boot it in a fresh Worker, and compare the boot
  log, heap digests and code-set inventory to the packet's.
- G-2. Native R6/R6a per shared-source change, as today; the R6
  source-location allowance for files gaining `#+wasm32-target` branches
  (adopted 21 September) applies to every file NSL-2/NSL-5 touch, so the
  reader-matrix and decoded-code comparison become part of each such packet.
- G-3. Admission-predicate rule (`CLAUDE.md`): every refusal in NSL-1's
  namespace, NSL-3's installer and NSL-2's writer keeps a directed case or a
  recorded equivalence.
- G-4. Review cadence per R-1..R-5 of the throughput directive; the headline
  each audit opens with is §10's metric.

## 8. Decisions this plan needs from the user

- Q-A. Amend `ready-decision.json`'s `image` line ("READY starts from an
  identity-preserving projection of the pinned native image. Building CLOS
  from source on the target is Stage 2 work.") to: READY is reached by
  cross-loading level-0 and loading level-1 through the namespace; CLOS is
  built by loading `l1-clos-boot`/`l1-clos` on the target. Without this
  amendment NSL-4 contradicts an adopted decision. The other five decisions
  (coverage, conditions, concurrency, dispatch, sequencing) stand, with
  `sequencing` re-pointed at NSL-1.
- Q-B. Accept that the headline metric changes (§10) and that the first
  NSL packets move neither BT-1 number.
- Q-C. Confirm the exclusions that give `EXCLUDED` rows their authority: POSIX
  layer (ruled earlier), threads and scheduler (READY decision), JSPI
  (16 September), interface database (C-1).
- Q-D. Whether the R10–R12 stack is integrated before NSL-2 begins (audit 174
  recommends integrating it as one unit); NSL-2's target branches for locks
  build on R11's.

## 9. Questions for Codex

- Q-9. Shortest path to the first NSL-2 image: which level-0 files
  cross-compile to fasls today under `with-cross-compilation-target (:wasm32)`,
  and which stop, and where? Name the smallest prefix that `xfasload` can load
  once the function op exists.
- Q-10. Fasl code op: module bytes inline in the fasl, or hash plus side file?
  What does `%fasload`'s host import look like (signature, ownership of the
  byte buffer, what is rooted across the call)?
- Q-11. `xfasload` runs on the macOS host reading target constants through the
  `TARGET` nickname: confirm the binding path (BT-H1, Q-5) covers
  `xload-level-0`, and give the directed `node-size = 4` case for the xload
  heap.
- Q-12. Which of `ready/startup.lisp`'s target-only code is a genuine
  `#+wasm32-target` branch of an upstream definition (and moves into the
  file), and which is harness (and retires)? The class-table entries for
  streams and locks are upstream already (`l1-clos-boot.lisp:2428, 2488`), so
  nothing there needs moving.
- Q-13. The 35 startup callbacks: for each, the phase in which the boot reaches
  it (level-0 cold load, level-1 load, `*lisp-startup-functions*`) and whether
  its native body compiles as written; this is the LL15-a phase order C-2
  asks for.
- Q-14. Module count at boot0 and its measured instantiation time on Node; if
  it dominates, the granularity decision (LL21-b) is reopened with data, not
  before.
- Q-15. Anything in §5 that duplicates a mechanism already in the tree under
  another name.

## 10. Measurement

- M-1. Headline for every NSL packet, in the README's first line and in
  `STATUS.md`: `files loaded in native boot order: n of N` (N from the native
  cold-start trace), `last load index reached`, and `open rows by kind` from
  the boot log. The two BT-1 numbers stay as secondary lines; executed
  originals is no longer the headline once boot0 exists, because the boot
  executes them by the thousand and per-function credit stops meaning
  anything.
- M-2. A packet that moves none of M-1 says so in its first line (BT-1's rule,
  carried).
- M-3. Cost lines stay: author wall time by phase, reviewer replay tier and
  time, evidence bytes retained.
