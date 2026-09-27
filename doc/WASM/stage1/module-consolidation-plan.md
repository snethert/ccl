# Module consolidation plan — from 11,938 engine modules at READY to 7

```
DOC-ID        MCP-P8 (P1 aea879ee; P2 f22d8756 folded in Codex's seven findings; P3 56273a33
              its four corrections; P4 folds in Codex's three corrections of P3, after which
              Codex considers the plan valid for implementation; P5 records the
              user's adoption, the memory measurements F-12 and the direct-call direction A-13;
              P6 records completed P-0 and the user's heap/stack sizing amendment;
              P7 adds bounded input ownership and release during loading;
              P8 incorporates Claude's review 0a7cd736 and separates the work)
STATUS        ADOPTED by the user, 27 September 2026 (U-5: "Yes to all three"), after
              Codex judged P4 valid for implementation; packet contents, sizes and order
              remain Codex's implementation choices; A-13 is a recorded future direction
AUTHOR        Claude (Fable 5.1), 27 September 2026, after the READY commit ea82d8e7
AMENDMENT     Codex, 27 September 2026, U-6/U-7 and relayed review U-8; documentation only
READER        Codex, as Stage 1 author; review amended items by ID
BASE          wasm2 at ea82d8e7 (READY under decision A2); measured on the retained
              loader-startup-timing-r1 inputs boot-r21 and bundles-r18
TOUCHES       P8: this document and doc/WASM/decisions.md; imported review unchanged
CHANGES       §9 records revision history; §10's import qualifications still apply
```

Implementation status, 27 September 2026: P-1a/P-2, P-1b, P-1c, P-3 and P-4
are implemented and author-verified. See the [results and evidence](module-consolidation-results.md).
Independent review remains pending. P-5/P-6 remain future work; optional P-7
is explicitly deferred on the measured collector-preparation cost.

## 0. How to read this

Every item carries an ID; IDs from P1 are kept, amended items are marked with
revision labels such as `(P8)`; new items continue the numbering. Review amended
items by ID with `AGREE`, `DISAGREE`, `AMEND` or `UNVERIFIED`. Facts (F) name
their measurements or source evidence. F-13 is the executed P-0 baseline;
F-14 gives native defaults and the current Wasm growth policy; F-15 records
current input retention. Diagnosis (D), target (T), archive design (A),
packets (P), risks (R) and questions (Q) follow.
The prototype is a measurement
instrument: it establishes sizes, tool scale and engine cost. It is not a
proposed implementation and did not execute Lisp.

## 1. User direction

- U-1. User, 27 September 2026: "The exceedingly slow startup is due to the many
  modules. Review the first attempt. We ran into the same thing." Then, after
  Codex's read-only review: "please prepare a plan to reduce the module count
  to a small number. I think 36 might be too high."
- U-2. Codex's review (relayed by the user) established the architectural
  match with attempt 1 (8,675 table entries in 36 binaries) and stated that it
  does not establish how much startup time each part consumes. At P1 no
  end-to-end timing existed; F-13 now supplies the instrumented baseline.
- U-3. Nothing else here is the user's statement.
- U-4 (P2). Codex's review of P1 (relayed by the user, 27 September, 09:54):
  seven findings, two factual corrections, agreement with two image archives,
  shared helpers, indirect dispatch through function cells, preserved target
  FASL order and a build-side linker as the implementation boundary; the
  prototype is supporting evidence, not a production linker. Conditional
  agreement on Q-A/Q-B after the amendments; for Q-C one bounded,
  instrumented baseline before implementation.

- U-5. User, 27 September 2026, after Codex's review of P4: "Yes to all
  three." Q-A, Q-B and Q-C are adopted as written in §8. In the same message
  the user asked (a) what memory the launch will require, noting the current
  launch needs 4 GB, and asked for it to be measured (F-12); and (b) whether
  the plan can accommodate a future in which CL-package functions are called
  directly: "the compiler would output code to check for the indirect table,
  as now, but if absent, it would compile a direct call" (A-13).
- U-6 (P6). User, after the completed P-0 report and Codex's native/Wasm
  sizing comparison: "update the plan". Incorporate the proposed starting
  configuration and measurement gates in A-14/A-15 and P-1. These values
  are defaults to evaluate, not a measured optimum or a READY-time promise.
  Document revision MCP-P6 is separate from the future direct-call packet P-6.
- U-7 (P7). User: "Must everything be in memory at once? Can't things be read,
  used and derefenced in the JS so the JS collector works alongside?", then
  "update the plan". Add explicit buffer ownership, bounded staging and
  release gates to P-1 (A-16), preserving admission and repeated LOAD.
- U-8 (P8). The user relayed Claude's committed
  [review of P6/P7](module-consolidation-review-p7.md), `0a7cd736`: agreement
  with four amendments on packet scope, GC timing, host slices versus a C
  range interface, and main-thread FASL ownership. Codex imports that review
  unchanged and incorporates the amendments below; no new review was invoked.

## 2. Facts at ea82d8e7

- F-1. Module counts on the READY path (`stats.mjs` on bundles-r18; boot from
  `boot-r21/boot/artifacts/code-set.json`): 82 runtime bundle files, 8,816
  units (top-level code records), 10,891 runtime engine modules (units plus
  nested lambdas), 1,042 boot-image modules, plus 4 service modules (collector,
  integer, float, detector) and the host-call adapter (1 module, 5 instances).
  Engine modules compiled before READY: 11,938. The traced READY run observed
  5,028 distinct modules executing (`loader-target/README.md`).
- F-2. Bytes. Runtime bundles total 547,797,092 bytes: 208,260,920 bytes of
  materialized module binaries, 208,260,920 bytes of D2 templates (the same
  bytes with the shared-memory flag clear), and about 130 MB of JSON manifests
  (a full D2 record, classification and mnemonic list per module) plus the
  FASL streams. The boot code set is 23,533,545 bytes of binaries plus the same
  again in templates. Largest file: `l1-streams` with 2,103 modules and a
  102,247,001-byte bundle.
- F-3 (P2). Helper duplication (`dedupe.mjs`, `helpers.mjs`). Every generated
  module carries a private copy of the backend's runtime helpers (`$rv_alloc`,
  `$unbind_to`, `$stack_guard`, the object, control, dynamic, progv, unbound,
  result and condition runtimes). Across the 10,891 runtime modules there are
  424,749 helper function bodies, 256 distinct as binary bodies and 39 as text
  (F-8); helper bytes are 136,453,339 of 208,260,920, 65.5% of runtime code
  bytes (P1 said 69.3%, which was all non-entry bytes including headers,
  types and imports). The two exported bodies (`entry`, `tail_entry`) total
  64,006,013 bytes for the whole runtime, 30.7%; for the boot set the entry
  bodies are 9,766,196 of 23,533,545 bytes, 41.5%.
- F-4 (P2). Engine construction cost is small in V8 (`cost.mjs`, l1-streams,
  2,103 modules, Node v25.6.1 / V8 14.1.146.11): `WebAssembly.validate` on
  every module 176 ms, `new WebAssembly.Module` on every module 155 ms
  (0.07 ms each), `new WebAssembly.Instance` on every module 38 ms (0.02 ms
  each), table publication 3 ms. Extrapolated over 11,938 modules the
  construction work is about one second. These are construction
  measurements: they do not establish when machine code is generated for
  each function, and no Lisp executed; see R-3.
- F-5 (P6). Isolated admission cost (`cost.mjs`). The production path
  `bundle.compile` (validate record, sha256 every binary, `inspect`,
  `entryRanges`, `validateGenerated`, and `materializer.install`, which
  re-derives the template manifest with three sha256 digests and two binary
  parses per module) costs 7,615 ms for l1-streams, 3.6 ms per module, and
  `decodeTargetBundle` (sha256 of the 102 MB file in pure JS plus a copy of
  every module and template) another 2,670 ms. At 3.6 ms per module the
  admission of 10,891 runtime modules is about 40 s and decode about 15 s,
  before any Lisp runs. The 1,042 boot modules add about 4 s through
  `cross-image.mjs`, which uses the same `compile`.
- F-6 (P5). Until F-12 no end-to-end timing existed. `ccl-evidence/2026-09-27-loader-startup-timing-r1`
  holds only `run-1.stderr` (80 `;Loading` lines); `measure.py` never wrote
  `timing.json`, and `same-process.mjs` never ran. The READY reports record
  events and collections (664 at the audit-187 checkpoint) but no durations.
  That historical run did not establish a timing breakdown. F-13 now records
  P-0's split between admission, installation, execution and collection.
- F-7. Engine limits, V8 `src/wasm/wasm-limits.h` at main (fetched today):
  defined functions 1,000,000; imports 1,000,000; exports 1,000,000; globals
  1,000,000; tags 1,000,000; module size 1 GiB; function body 7,654,321 bytes;
  table size 10,000,000. A single module holding all 10,891 runtime functions
  (21,782 exports) is far inside every V8 limit. Firefox and JavaScriptCore
  limits were not checked here; UNVERIFIED, commonly cited as 100,000 imports
  and exports, which A-3 respects.
- F-8 (P2). Prototype archive (`merge.mjs` on the retained per-function WAT in
  `*.records.json` and the boot `code-set.json`, then WABT `wat2wasm
  --enable-all`, then `engine.mjs`):

  | tier | functions | bundle bytes today | archive bytes | WAT bytes | wat2wasm | validate | new Module | new Instance |
  |---|---|---|---|---|---|---|---|---|
  | misc | 176 | 8,978,831 | 1,168,420 | 9,534,063 | 0.45 s, 86 MB RSS | 2.3 ms | 1.9 ms | 0.9 ms |
  | boot (level-0) | 1,042 | 47,067,090 | 10,248,392 | 83,383,417 | 3.6 s, 736 MB RSS | 16.9 ms | 13.6 ms | 10.2 ms |
  | l1-streams | 2,103 | 102,247,001 | 11,861,596 | 96,991,845 | 4.1 s, 852 MB RSS | 18.8 ms | 16.5 ms | 11.5 ms |
  | all 82 runtime files | 10,891 | 547,797,092 | 68,787,697 | 560,180,410 | 23.8 s, 4.96 GB RSS | 124.8 ms | 99.7 ms | 67.4 ms |

  Each merged module validates, instantiates against the fixed imports plus
  per-function renamed symbol/code globals, and publishes every `entry` into a
  table. The `validate`, `new Module` and `new Instance` columns are
  construction measurements on one process; `engine.mjs` also times
  `WebAssembly.compile` but after the synchronous construction of the same
  bytes, so that figure is not a cold compile and is not used here (P2). Distinct helpers by text after renaming: 39 in every tier, including the whole runtime (the 256 distinct binary bodies of F-3 differ only by import-index renumbering). The whole-runtime archive has 21,782 exports and 139,010 renamed imports and instantiates in 67 ms. The
  prototype keeps per-function symbol imports renamed `fN.wire` (25,277 for
  l1-streams); it does not implement A-3.
- F-9. Import inventory (`stats.mjs`): 136,935 `symbols` imports, 2,075 `codes`
  imports, 32,673 owner/integer/floating function imports, no `keywords`
  imports in bundles; 125,199 root cells over all units; at most 72 symbol
  imports in one module. Version-5 records read every symbol through a root
  cell (`wasm32-root-symbol-reads`), so a symbol read is already
  `(i32.load (global.get $symbol_X))`.
- F-10. What per-module identity binds today: `PACKAGING =
  'one-generated-function-per-module-v1'` is checked by `bundle.mjs`,
  `cross-image.mjs` and `target-bundle.mjs`; each module row carries its own
  `d2` record, `binary_sha256`, `entries[].range`, profile and slot; the code
  registry maps logical code ID to slot per function; publication is eager
  (`publish` instantiates the whole set, then writes paired tables). The lazy
  stub loader (`loader.mjs`, `installer.mjs`) is not on the READY path.
  Runtime code IDs and slots are assigned sequentially at file open
  (`targetLoadSession`, `nextCode`/`nextSlot`); boot IDs start at 16 with
  slot = ID + 8.
- F-11. LL21-b's criterion (inventory): "Bootstrap module granularity is chosen
  from measured bytes, compile, instantiate and install latency and
  retained-code growth of the generated bundles under the benchmark policy,
  with the chosen packaging recorded and every logical code ID mapped to slot,
  module, ABI and layout versions." The accepted record chose one function per
  module; F-2..F-8 are the measurement that criterion asks for, and this plan
  re-decides it.

- F-12 (P5). Memory and time of the current launch, measured today on the
  same inputs (`/usr/bin/time -l`, `boot0.mjs` to READY, no census; summary
  retained in `doc/WASM/tools/module-archive/measurements.json`):

  | measurement | result |
  |---|---|
  | fresh process to READY, wall clock | 329.9 s (81 runtime loads, 2,029 collections) |
  | maximum resident set size | 4,786,270,208 bytes (4.46 GiB); peak footprint 3,762,188,288 |
  | v1 admission alone, all 82 bundles kept alive (`admit-all.mjs`) | 55.7 s; RSS 820 MB after reading the 548 MB of bundle files, 1,994 MB after admission (950 MB of copied module and template bytes plus compiled code); maximum 2,090,655,744 |
  | archive path, one 68.8 MB module compiled, instantiated and published (`engine.mjs`) | maximum 352,387,072 bytes for the whole Node process |
  | build-time only: `wat2wasm` on the 560 MB whole-runtime WAT | 4,959,506,432 bytes, 23.7 s |

  The bundle files hold 5,754,020 bytes of FASL streams and
  125,519,920 bytes of JSON manifests beside the 416 MB of module and
  template binaries; `boot0.mjs` reads every bundle on the main thread and
  passes the bytes to the Worker through `workerData`, so the 548 MB exists
  at least twice during launch. P6 incorporates §10's correction here:
  admission-only RSS already includes bundle storage, so the former additive
  attribution and its 1.5–2 GiB launch projection are withdrawn. The archive
  prototype executes no Lisp. Whole-path memory must be measured (F-13/P-1).
- F-13 (P6). P-0 completed at `0675ba83`: one fresh process reached READY
  in 341.087 s, inside its 600 s deadline, with 4.833 GiB peak RSS and
  4.688 GiB RSS at READY. There were 81 returned nested LOADs and 2,029
  collections. Exclusive Worker times: root allocation/registration 115.076 s,
  collection 64.854 s, Lisp plus unmeasured host/observer work 62.639 s,
  runtime compile/materialization checks 41.974 s, bundle decode at admission
  13.926 s and Worker namespace decode 13.942 s. Main namespace decode
  separately took 14.135 s; thread totals must not be added indiscriminately.
  At READY, linear memory was 119.75 MiB, the current heap-space pair 16 MiB,
  scratch 32 MiB, and movable live data at the last GC 5.973 MiB. The Worker
  JS heap figure includes all JS objects, not just JSON manifests. These
  counters do not partition RSS. See the [report](module-consolidation-p0.md)
  and [bound evidence index](module-consolidation-p0.json). The user relayed
  Claude's review that the timing-only baseline is sound; this does not
  accept the unimplemented archive or sizing changes.
- F-14 (P8). Native CCL32 uses 1 MiB control, 1 MiB value and 512 KiB
  temporary-object stacks for ordinary listener/threads, excluding guards
  ([source](../../../level-1/l1-lisp-threads.lisp)); the initial kernel
  bootstrap temporary stack is 256 KiB: `new_tcr(initial_stack_size,
  MIN_TSTACK_SIZE)` in the kernel startup path uses `MIN_TSTACK_SIZE = 1<<18`
  ([area.h](../../../lisp-kernel/area.h)), independently of the 1 MiB
  `DEFAULT_INITIAL_STACK_SIZE`. This resolves the review's UNVERIFIED item.
  The native free-heap threshold is
  16 MiB beyond live/image data, not a fixed total heap size
  ([kernel defaults](../../../lisp-kernel/pmcl-kernel.c)). In P-0, Wasm
  started with two 64 KiB spaces, growing to two 8 MiB spaces at READY.
  Its temporary and explicit control areas are only 16 KiB each
  ([driver](../../../tests/wasm/stage1/loader-target/boot0.mjs): 196608–212992
  and 212992–229376), compared with native's 512 KiB and 1 MiB.
  The current owner grows only if collection cannot satisfy the next
  allocation; a nearly full heap can therefore collect repeatedly without
  gaining useful free space ([owner](../../../runtime/wasm32/collector-owner.mjs)).
- F-15 (P7). Source retention, checked at `9ae6bfd8`: the
  [driver](../../../tests/wasm/stage1/loader-target/boot0.mjs) reads all bundles,
  creates a main-thread namespace and sends `files` through `workerData`
  without a transfer list. The Worker builds its own namespace.
  [bundleNamespace](../../../runtime/wasm32/target-load-session.mjs) keeps a
  full bundle copy and module rows per file; closing a load removes its open
  session, not that inventory. The
  [decoder](../../../runtime/wasm32/target-bundle.mjs) also snapshots its input
  and copies decoded sections. These paths explain avoidable retention;
  they do not establish a disjoint byte attribution. In particular, F-13's
  roughly 0.75 GiB Worker JS heap is not a manifest-only measurement, and
  RSS minus the exposed counters is not a measurement of engine code memory.

## 3. Diagnosis

- D-1 (P2). The count is the visible symptom of three multiplicative costs:
  (a) a private helper runtime in every module (F-3: 65.5% of bytes), (b)
  per-module admission re-derivation in JavaScript (F-5: 3.6 ms each, about
  55 s in total with decode), and (c) per-module engine objects (F-4: about
  1 s of construction in V8; larger in browsers, and incompatible with
  per-resource code caching). Merging modules while keeping duplicate helpers
  removes (b) and (c) but not (a); sharing helpers removes all three and cuts
  the runtime archive from 548 MB to 69 MB (F-8).
- D-2. Thirty-six is the file-granularity answer and is the wrong axis. A
  bundle file is a FASL stream boundary (data, install order), not a code
  boundary. Code can be compiled and instantiated once per image tier while
  the FASL streams still publish each unit at opcode 72 in native order (A-5).
  The only reason to split an archive is delivery (browser streaming, lazy
  fetch), not correctness, and that is a later HOSTFM decision (P-5).
- D-3. Attempt 1's 36 binaries were an ad hoc grouping and its loader repaired
  bindings at launch; none of that is reused. The lesson kept is only the
  shape: many logical functions, few engine modules, table entries filled from
  exports.
- D-4 (P8). F-13 identifies root allocation as the largest measured cost;
  collection and residual execution are also substantial. A-7 removes
  repeated per-module admission work, while archive admission still has a
  cost. A-15's host-side slices address root allocation in P-1a; A-14
  addresses allocation headroom separately in P-1b. A C collector range
  interface is deferred pending those measurements (P-7). Neither their
  savings nor a new READY time is established; reservation alone cannot prove
  all 115 seconds disappear. Other residual costs remain separate work.

## 4. Target

- T-1 (P3). Product engine modules at READY: 7. The four services (collector,
  integer, float, detector), the host-call adapter, one level-0 boot archive,
  one level-1 runtime archive. Product instances: 9 fixed (four services and
  five adapter instances) plus one per archive generation (A-4), so 11 at
  READY with the first generation of each archive. Instrumentation modules
  and instances (the traced run's `observe.wasm` and its per-function
  wrapper instances, the fixture stubs) are counted and reported separately
  and are not part of the target. Table entries and logical code IDs are
  unchanged in number.
- T-2 (P2). Post-READY `LOAD` of a compiled file adds one module per file (a
  single-file archive, A-1) and, when its units are already published,
  publishes from a fresh generation (A-4) rather than a fresh module. The
  future in-image compiler keeps per-function modules (packaging v1) for
  interactive definitions; v1 and v2 coexist in one Worker because both fill
  the same paired tables and registry.
- T-3. Bytes: runtime archive 69 MB and boot archive 10 MB (F-8), from
  548 MB and 47 MB, with catalogs of one short row per function.
- T-4 (P3). Admission work at READY per tier: the D2 re-derivation of A-6
  (one digest of the template, one of the full binary), one binary parse,
  one validation, one module construction and one instantiation, then
  per-unit publication as today.
## 5. Archive design

- A-1 (P2). Archive = one Wasm module + one manifest (+ the unchanged FASL
  byte streams for the runtime tier). `PACKAGING = 'code-archive-v2'`. The
  manifest is the single authority the file digest binds, as today's
  `.w32bundle` manifest binds `codeSet`, `units` and `fasl_sha256`: the
  module's `binary_sha256` and `template_sha256`, the one D2 record, the
  helper inventory (39 names with their content hashes and function
  indices), the export map (function index for every `k.entry` and
  `k.tail_entry`), per-function rows `name, code_offset, unit, entry_index,
  tail_index, arity, captures, symbols [wire,index], codes [name,
  code_offset], body_sha256` (the two bodies' bytes from `entryRanges`, so an
  audit can still bind each function's code), and per unit `name,
  symbol_count, root_base, record_version, record_sha256, modules`. Each
  FASL keeps its `install_record` whose `record_sha256` the manifest lists;
  opcode 72 still supplies the record and the loader still refuses a
  mismatch (`CODE_RECORD`). Nothing outside the manifest is trusted.
- A-2. Module structure: one type set; fixed imports once (`env.*`, and the
  owner, integer and floating functions always present, so the archive's
  profile is the floating-owner superset and the per-module profile field is
  dropped); each distinct helper once, named `helper__<content-hash>` after a
  fixed point over callee variants (prototype `merge.mjs`); per function
  `$body__k` (tail entry) and `$entry__k`; exports `k.entry` and
  `k.tail_entry`. No start function, no segments, no defined globals, no data,
  exactly as the v1 validator requires.
- A-3 (P2). Symbol access through one root block per generation. Replace
  per-function `symbols.*` global imports by one imported immutable global
  `$roots` (the generation's root block base) and the read
  `(i32.load offset=4*(root_base+index) (global.get $roots))`, where
  `root_base` is a build-time constant per unit recorded in the manifest.
  The runtime block has 125,199 cells (489 KiB) per generation; the boot
  block is filled from the manifest's heap references at image load, so no
  host address enters the artifact. Reservation, filling, ownership and
  rollback are specified in A-12; a block is never shared between
  generations, so a retained old function keeps reading the cells it was
  published with. This is a text rewrite of the same site
  `wasm32-root-symbol-reads` already rewrites. A-3 is required for non-V8
  engines (F-7) and removes 136,935 import bindings; the prototype shows V8
  does not need it for construction speed.
- A-4 (P4). Code identity by generation, not by fixed ID. A generation is one
  instantiation of the compiled archive with two imported immutable globals:
  `$roots`, the base address of its root block, and `$code_base`, the tagged
  word `4 * code_base`; the manifest's per-function `code_offset` gives
  `code_id = code_base + code_offset`, and `codes.*` imports become
  `(i32.add (global.get $code_base) (i32.const 4*code_offset))`, which
  equals today's import value `4 * code_id`. Creating a generation consumes
  its whole ID window at once: `nextCode` advances by the archive's `count`
  and that range is charged against capacity immediately, whether or not
  every unit is ever published; the root block is likewise reserved whole,
  and reserved unpublished cells are unavailable to every other allocation.
  Only registry population, root-cell filling and root registration happen
  per unit (A-12). The first generation is created at Worker start (A-5).
  Reservation of units happens at LOAD open, not at opcode 72: when a load
  session opens file F it reserves F's units in the oldest generation in
  which they are unreserved (unit states: `unreserved`, `reserved` by that
  session, `published`); a nested LOAD of another file reserves its own
  units, and a recursive or overlapping LOAD of F while F's session is open
  reserves the next generation, creating it if needed (a new instance of
  the same `WebAssembly.Module`, about 67 ms, F-8). On session close, units
  still `reserved` return to `unreserved`; units already `published` stay
  published, as a failed v1 LOAD leaves its installed units today, and the
  loader reports the partial load. Two independently built archives never
  collide because every generation's window comes from the shared
  `nextCode`. Retained function objects keep their generation's instance,
  registry rows and root cells alive; generations are never released in
  this plan (R-4). Capacity policy: the registry row count is configured
  from the manifests at Worker start as
  `first_code + boot count + G * runtime count + post-image budget` with
  `G` an explicit configuration: `G = 2` gives 16 + 1,042 + 2 * 10,891 +
  8,192 = 31,032 rows, inside the present 32,768; `G = 4` gives 52,814.
  The paired tables are sized separately as that row count plus the
  reserved-slot offset (slot = code_id + reserved) and are allocated at
  that full size during Worker setup, before any generation is admitted,
  because a `WebAssembly.Table` can grow but never shrink (A-12). A LOAD
  that would need a generation beyond the configured window refuses with a
  checked error before any state changes, never a trap. Tests: the same
  file LOADed twice in one Worker (second load publishes a fresh
  generation, first-generation closures still return their old constants),
  a recursive LOAD of an open file, a partial load released on close,
  redefinition through a later LOAD, old closures surviving a forced
  collection between the two loads, and the capacity refusal.
- A-5 (P2). Install semantics preserved. The archive is validated, compiled
  and its first generation instantiated at Worker start (before
  `%toplevel-function%`; in a browser through `WebAssembly.compileStreaming`,
  off the Lisp path). Admitted modules have no start function, segments or
  defined globals, so instantiation has no side effect on Lisp state.
  Publication stays per unit at opcode 72 in target order and is the
  transaction of A-12: root-cell fill, registry rows, `table.set` of the
  unit's slots from the generation's exports; `SLOT_OCCUPIED`,
  `REGISTRY_CHANGED`, `TABLE_CHANGED`, `IMPORT_IDENTITY`, `CODE_RECORD` and
  `UNASSIGNED_SPECIAL` checks are unchanged. A unit whose FASL never installs
  is never published, so required-bundle omission and the empty namespace
  still stop before the post-image marker.
- A-6 (P2). D2 once per archive: template (unshared memory flag) and full
  binary differ by the one byte the materializer patches; the archive's D2
  record is derived once at build and re-derived once at admission with
  exactly one sha256 of the template, one patch, one sha256 of the full
  binary, one `inspect` and one `WebAssembly.validate` (today's
  `materializer.install` performs those steps several times per module; the
  v2 path is specified as one of each, and P-1 reports the count).
  Instruction classification stays with WABT: `wasm-objdump -d` is streamed
  through the feature scan and hashed, and only `-x` sections and the
  digests are retained, because `runtime/wasm32/binary.mjs` parses section
  headers, imports, exports and types and does not decode instruction
  bodies; replacing WABT here is not proposed.
- A-7 (P2). Admission cost: sha256 of 69 MB through `crypto.subtle.digest`
  (the pure-JS `sha256.mjs` digests about 50 MB/s here, 802 ms for the 38.8 MB
  of l1-streams module bytes, and is the largest single item in F-5), the
  one-of-each D2 re-derivation of A-6, `WebAssembly.validate` (125 ms
  measured for the whole runtime), module construction (100 ms) and one
  instantiation (67 ms). Manifest checks are per row without hashing.
  Measured construction total under half a second per tier (F-8), against
  about 55 s of admission and decode today (F-5). Whether machine-code
  generation is included in those figures is not established (R-3); P-0
  and P-1 measure it with Lisp executing.
- A-8 (P3). Two gates, because one inversion cannot cover both
  transformations. (a) Structural merge equivalence: with symbol and code
  imports still per function (the prototype's shape), rebuilding each
  function's standalone v1 module from the archive's pieces (its bodies plus
  the helpers it references in the original order, renames inverted) must be
  byte-equal to the retained v1 binary; distinct-helper counts (39) are
  recorded. (b) Rewrite verification, separately, over both input forms:
  runtime (version-5) sites are `(i32.load (global.get $symbol_w))` and
  boot (version-4) sites are the direct tagged reference
  `(global.get $symbol_w)`; both must become exactly one dereference
  `(i32.load offset=4*(root_base+index) (global.get $roots))`, never two
  loads for a runtime site and never zero for a boot site, and every
  `(global.get $code_n)` site must become
  `(i32.add (global.get $code_base) (i32.const 4*code_offset))`. The check
  is a bijection between the sites of the v1 text and the archive text,
  computed from the manifest (unit `root_base`, symbol index,
  `code_offset`) by an independent scan of both texts, never by the
  linker's own bookkeeping; plus execution: READY itself, the focused
  loader checks in `tests/wasm/stage1/loader-target/check.mjs` (constants,
  nested functions, keywords, VALUES, ASSQ, checked exceptions) and the
  collector cases, all against the archive, with a forced collection
  between root fill and first call. Neither gate proves the other.
- A-9. Not in this plan: turning named calls inside an archive into direct
  `return_call`s. Function cells must stay rebindable and every call keeps
  its table dispatch and checks.
- A-10. Where the merge runs. Recommended: a build-side WAT linker in
  JavaScript (the prototype is 70 lines) over the retained per-function WAT,
  followed by one `wat2wasm` per tier. It needs no shared-compiler change and
  no R6 obligation, and the compiler's per-function WAT remains the reviewed
  artifact. Alternative (i): a compiler-side archive writer that splits
  `b-one-module` into header, helpers and bodies and assembles one WAT per
  tier in Lisp; same output, but a backend change with R6/R6a. Alternative
  (ii): Binaryen `wasm-merge` plus duplicate-function elimination; a new
  pinned toolchain and binary rewriting, not recommended.
- A-11 (P7). Preserve the exact 82 FASL streams, namespace behavior and
  `%fasload` semantics. The `.w32bundle` container loses its per-module code
  and templates and keeps the FASL bytes and the unit catalog; the archive
  is a separate file named by digest in the namespace. `bundleNamespace`
  ownership/storage changes under A-16; retaining all input containers in
  both threads is not part of the namespace contract.

- A-12 (P4). Rooting and publication transactions, both journaled with
  prior values, never assuming a prior value was zero or NIL. The paired
  tables and the registry are allocated at their configured capacity (A-4)
  during Worker setup, before any generation exists; no transaction grows
  a table, because growth cannot be undone. Generation creation, inside
  one owner boundary: check capacity for the whole root block before any
  write (external-region cells, root-list bytes, `logCapacity`, the
  collector's scratch requirement for that many roots, and the A-4
  registry and table window), journal and reserve the root block, journal
  and advance `nextCode`, then instantiate; if instantiation or any
  earlier step fails, replay the journal (root cells restored, `nextCode`
  restored) and refuse, leaving the tables untouched. Cells are registered
  in the `module-constants` group per unit at publication, not for the
  whole block, so unpublished sub-ranges are never roots, while the whole
  reserved block stays unavailable to other allocations. Unit publication,
  inside one owner boundary with no await, callback or Lisp reentry: (1)
  `IMPORT_IDENTITY`/`CODE_RECORD`/`UNASSIGNED_SPECIAL` checks and the
  reservation check (the unit is `reserved` by this session), (2) journal
  and write the unit's symbol values into its sub-range and register those
  cells, (3) journal and write the registry rows, (4) `table.set` every
  pair; any failure replays the journal (cells and registration, rows and
  tables back to their journaled prior values) exactly as `installer.mjs`
  does today, and the unit returns to `reserved`. Ownership: block and
  window belong to their generation; release is out of scope (R-4). Tests:
  forced collection between (2) and (4) with a moving symbol, a failed
  install at each step leaving cells, rows and tables unchanged, a failed
  instantiation leaving the owner, `nextCode` and the tables unchanged, and
  a capacity refusal at generation creation.
  P8: A-15 specifies host-side direct unit slices now, and a possible C range
  interface later; both preserve every reservation and rollback condition here.
- A-13 (P5). Guarded direct calls, a recorded future direction (U-5 b), not
  part of P-0..P-5. Today a named call loads the symbol's function cell, takes
  the function object's code word, resolves it through the code registry to a
  slot and dispatches with `call_indirect`/`return_call_indirect` on the tail
  table (A-9 keeps that). A Wasm direct `call` is only possible to a function
  in the same module, which is exactly what the archive creates: every
  runtime function is `$body__k` in one module. The user's scheme fits as a
  guard: at a call site whose callee is a known archive function, emit
  (1) load the function cell, (2) compare the callee object's code word with
  this generation's expected word `(i32.add (global.get $code_base)
  (i32.const 4*code_offset))`, (3) if equal, `call $body__k` (or
  `return_call $body__k` in tail position) passing that object as `$self`
  so its pool and roots are the ones it was published with, else the
  existing table dispatch. The guard keeps every semantic the plan
  preserves: redefinition through a later LOAD or the in-image compiler
  changes the code word, so the guard fails and the indirect path runs; a
  second generation of the same code has a different `$code_base`, so
  cross-generation direct calls cannot happen; unbound or non-function
  cells fall to the existing checks. What A-13 needs from this plan and gets:
  stable per-function names `$body__k` and a manifest map from symbol to
  `code_offset` (A-1, A-2), generation-relative code words (A-4), and no
  premature direct calls (A-9). What it needs beyond it: a shared-compiler
  change to the call emitter (Codex, under R6/R6a), a decision whether the
  boot and runtime tiers become one module so level-0 CL functions are
  reachable directly too (that would make the target 6 product modules),
  and measurement of the guard's cost against the saved `call_indirect`
  signature and null checks.
- A-14 (P8). Heap and stack configuration, isolated in P-1b under U-6.
  Use the same initial defaults across supported engines, with explicit
  configuration and measured adjustment:

  | area / policy | starting value |
  |---|---|
  | active allocation space | 32 MiB |
  | spare copying space | 32 MiB |
  | free-space target after collection | 16 MiB |
  | Lisp value stack | 1 MiB |
  | temporary-object stack | 512 KiB |
  | explicit Lisp control-stack area | 1 MiB |
  | initial linear-memory layout budget | approximately 192 MiB |

  Preserve free allocation headroom after GC, growing when live bytes plus
  the pending allocation and target require a larger space; do not wait
  until even the next allocation fails. The 16 MiB target is a growth-policy
  target, not an extra reason to reject an allocation that still fits when
  growth is unavailable. An unsatisfied actual allocation gets a checked
  refusal. Preserve collection-inhibition behavior and valid roots/owner
  state on refusal; memory growth itself cannot be rolled back by shrinking.

  Derive a disjoint, aligned layout before creating the Worker memory. Larger
  spaces cannot simply replace the fixture's size constants at their old
  addresses. Size scratch, root lists, update logs, external roots, registry
  and tables from the configured spaces, manifests and generation count.
  The current scratch bound is `96 + usedHeapBytes / 8 * 20 + logCapacity * 12`:
  a full 32 MiB space and today's 262,144-entry log require about 83 MiB.
  Thus 64 MiB of heap spaces is not the complete memory budget. Recompute
  this bound when root capacity or collector representation changes.
  Approximately 192 MiB is an initial default-layout budget to verify,
  not an RSS prediction, a fixed maximum, or a budget for every sweep size.
  Retain configurable growth within the admitted ABI/engine bounds and
  account for superseded heap/scratch extents retained in linear memory.

  Distinguish the costs inside today's `collector.copy` timer. Before every
  C call, the owner enumerates registered roots and writes their addresses
  to the root list (`#validate`/`#copyInto`); C then traces those entries.
  For the same root set this cost recurs independently of heap capacity.
  Inventory and object-map work depend on used from-space; copying depends
  on reachable data. Larger spaces are expected to reduce repeated root
  work by reducing collection frequency. Total inventory work may stay
  roughly similar for a fixed allocation volume, but survivor recopying,
  growth and root-set changes mean this is a hypothesis, not a constant.
  Split observation into host preparation and the C collector call, retaining
  the enclosing total and reporting residual owner checks separately. Record
  each collection's root count, used source bytes, live/copied bytes and
  whether it is a growth relocation. The C timer includes root tracing and
  inventory as well as copying; do not label all of it copying time or infer
  a copying speedup from fewer collections. Instrumentation stays off by
  default and does not change the C collector for this measurement.

  Align advertised Lisp stack defaults with the allocated areas and retain
  checked overflow boundaries. The engine's actual Wasm call stack and the
  service C stack are separate from these Lisp areas. The browser API has
  no portable call-stack-size setting; enlarging linear memory cannot raise
  that limit ([WebAssembly API](https://webassembly.github.io/spec/js-api/)).
- A-15 (P8). Separate host root allocation from collector representation.
  P-1a reserves each generation's block once and derives each unit's slice
  directly from its manifest offset. Incremental capacity/ownership accounting
  replaces `rootCells`' repeated validation enumeration and occupied-cell
  search; that host-side work is F-13's 115 s category. Preserve A-12's checks
  and journals. Keep the C collector and its existing individual-address
  root-list ABI unchanged; host slices can still supply that list at GC.
  Only published units' ranges are roots; reserved but unpublished gaps must
  remain excluded. Retain individual-cell support for v1 code and other
  root owners, with no overlapping allocation or duplicate registration.
  Rollback removes/restores exactly the affected ranges and values.

  Listing every root again at each collection is a separate cost, measured
  by A-14's split timers. Removing that list in favor of ranges accepted by
  `runtime/wasm32/collector.c` is optional P-7, justified by measured residual
  cost. It requires collector requalification and independent review before
  acceptance; prior accepted evidence does not cover a new root interface.
  Every published tagged cell still needs tracing and moving-reference
  updates. No complete removal of F-13's root or GC costs is assumed.
- A-16 (P8). Input ownership and release, isolated in P-1c under U-7.
  Stage one archive's admission inputs at a time, release its temporary
  state, then stage the next; retain the compiled modules needed by A-5.
  Declare the bound on in-flight reads and working buffers. Whole-archive
  authentication/validation may still require a full source buffer; P-1c
  does not require a streaming hash or browser delivery redesign.

  | data | owner and lifetime |
  |---|---|
  | raw archive/container bytes, template/patch buffers, decode scratch | admission owner only; release after their last check and compilation completes, or on failure |
  | parsed validation manifest and classification temporaries | admission owner; validate fully, extract compact runtime metadata, then release |
  | compact file/unit/function metadata and digests | retain for namespace lookup, install checks, generation creation and repeated LOAD |
  | FASL bytes | the approximately 5.8 MB set remains resident in the main-thread read-only namespace, which serves file requests |
  | per-open decode/read buffers and session metadata | release on close or failure, including partial loads; preserve published units under A-4 |
  | compiled modules, live instances, registry/table entries and roots | retain under the generation contract; releasing source bytes does not unload executable code |

  Make the Worker the archive admission/cache owner. The main thread remains
  the file host: `serviceRequest` answers Lisp's reads from its namespace, so
  it retains the FASL bytes and compact directory. Moving the file host or
  evicting its FASLs is outside P-1c. Archive binaries and validation manifests
  belong only to the Worker after delivery. Read into that owner directly or
  transfer an exclusively owned `ArrayBuffer` across the thread boundary.
  Do not clone
  full archives through `workerData`. Transfer detaches the sender's buffer;
  use standalone buffers, not a pooled Node Buffer's backing store
  ([Node transfer rules](https://nodejs.org/api/worker_threads.html#portpostmessagevalue-transferlist)).
  Preserve private authenticated snapshots: a mutable shared buffer or
  caller-held alias cannot replace them. Document any necessary copy and
  release the source at the earliest valid boundary. Await all consumers,
  including asynchronous digest/compile operations, before detaching or
  reusing their input.

  Drop every reference, including caches, `workerData`, closures, error/debug
  records and typed-array views. A small view must not pin a large archive;
  copy compact retained data into its own storage where necessary. Keep
  evidence as paths, digests and scalar results rather than retained payloads.
  Project metadata only after A-1/A-6 admission succeeds, retaining everything
  needed for per-unit checks, imports and future generations. The complete
  manifest and verification evidence remain durable, digest-bound artifacts
  for audit; trimming runtime objects must not remove an admission predicate.

  If bytes are evicted, reread only from the configured read-only backing
  store and authenticate against the pinned directory/manifest digests before
  use or publication. Do not add an arbitrary filesystem/network fallback.
  The resident FASL set preserves seek/read behavior and
  repeated/recursive/overlapping LOAD, partial-close reservations and old
  closures. New generations reuse the admitted module and compact metadata
  without retaining another raw archive.

  Cleanup covers success, decode/digest/compile/instantiate refusal and
  teardown, preserving A-12 rollback and other live sessions. Release makes
  objects eligible for JS collection; it cannot schedule collection or
  promise immediate RSS reduction. V8 can mark concurrently, but not all GC
  work is concurrent ([V8 GC](https://v8.dev/blog/concurrent-marking)). Normal
  startup must not depend on forced GC, finalizers or sleeps. Engine-owned
  compiled/debug data is reported separately where observable and is not
  presumed released with the JS source buffer.

## 6. Packets

- P-0 (P3). Measure (small, first). One bounded, instrumented fresh-process
  run to READY on the retained boot-r21 and bundles-r18 with durations in
  `boot0.mjs` and the load session: bytes into the Worker,
  `decodeTargetBundle`, `admitTargetBundle` (compile path), `publish`,
  root-cell allocation, Lisp time between installs, collections, and
  memory (maximum resident set, `WebAssembly.Memory` size at READY,
  `process.memoryUsage` after admission); per file and totals; an explicit
  timeout, with the per-file partial breakdown
  retained if READY is not reached. Gate: `timing.json` with the breakdown,
  in a new evidence directory, not a rerun of the cancelled three-run
  experiment. This is the baseline P-1 is judged against and tells whether
  a Lisp-side plan is needed (D-4). P6 status: completed at `0675ba83`, F-13;
  retain that baseline rather than launching another unchanged v1 run.
- P-1 (P8). Three separately committed and measured steps, P-1a/P-1b/P-1c.
  Execute P-1a, then P-2 to finish both archive tiers, then P-1b, then P-1c.
  P-2 depends on P-1a, not on sizing or input-lifetime changes; neither later
  step blocks landing the adopted consolidation. These are change boundaries
  in the working checkout, not a return to isolated proposal worktrees.
  Each step reports P-0's complete time/memory breakdown against F-13 and
  against the immediately preceding measured configuration. The latter
  comparison attributes its incremental effect; comparison only with F-13
  cannot do so. Bind exact code, inputs, configuration and instrumentation;
  record any necessary coupling rather than crediting all savings to one
  change. Keep workload/engine constant, use a 600 s deadline per run, retain
  partial journals, and reuse unchanged results. New split GC timers start
  in P-1a; F-13 has only the aggregate, which remains the baseline comparison.
- P-1a (P8). Runtime archive (A-1..A-12 and A-15's host-side slices).
  `target-bundle.mjs`/`target-load-session.mjs` gain v2 admission and
  generations; v1 stays for post-image files. Preserve current heap/stack
  sizes and growth policy, changing only the layout/capacities needed for
  the archive's root blocks, tables and registry. Do not change `collector.c`
  or add the A-16 lifetime refactor. Record memory reductions caused by the
  packaging itself and any unavoidable ownership changes separately.
  Gates: READY reproduces (81 nested loads, two post-image loads in two fresh
  Workers, both refusals, Unicode output); A-8 (a) and (b) over all 10,891
  functions; A-4 and A-12
  tests; product engine module count at READY = 1,048 (1,042 boot modules
  unchanged, one runtime archive, five services and adapter) with
  instrumentation reported separately. Verify published-slice movement and
  rollback, unpublished gaps, v1/slice coexistence and capacity refusals
  through the unchanged collector root-list ABI. Add A-14's host-preparation
  and C-call timers with per-collection counts/bytes and an enclosing total;
  keep them observational and off by default. Report root allocation and
  registration separately from per-collection preparation and C execution.
- P-1b (P8). Heap/stack sizing and growth policy (A-14), on the measured
  consolidated path. Hold archive and input-ownership code fixed. Verify
  stack boundaries, disjoint layout, headroom growth before allocation
  failure, inhibited collection and checked refusal with valid state when
  growth cannot satisfy an allocation. This includes layout and growth-policy
  code, not only replacing size constants.

  Compare initial space sizes of 16, 32 and 64 MiB per space on the same
  archive, engine and workload, keeping the 16 MiB free-space policy constant.
  A 16 MiB initial space may grow to meet that target; record actual sizes
  rather than treating these as fixed heap caps. Use one fresh process per
  candidate, a 600 s timeout and retained partial journals, reusing the default
  run as the 32 MiB candidate. Record READY time, peak/READY RSS, live and
  allocated heap bytes, space/scratch/linear extents, GC count, host-preparation
  and C-call times, per-collection roots/used/live bytes, root allocation and
  registration time and observable stack usage (label sampled
  high-water values as lower bounds). Bind the changed configuration and all
  input hashes. Select the smallest configuration with an acceptable measured
  time/memory tradeoff; report inconclusive single-run differences as such.
  Initial sizing evidence is on the P-0 engine; reuse the same defaults for
  subsequent engine qualification and record untested engines explicitly.
  Do not add a speculative v1 sizing sweep: a configuration-only pilot on v1
  is possible, but would not establish the new growth policy or replace these
  archive measurements. The chosen order avoids extra baseline runs.
- P-1c (P8). Input ownership and release (A-16), holding the measured archive
  and chosen P-1b sizing fixed. Verify sender detachment on transfer, no
  retained raw-buffer aliases in the compact cache, release on close and each
  failure exit, digest mismatch on any reread, and repeated/overlapping LOAD
  with old closures intact. Verify main-thread FASL reads still work after
  archive delivery/cleanup. Record unique owned backing-buffer bytes and
  counts by thread/category, including their peak and values at admission
  start/end, file close and READY, alongside P-0's memory counters. At READY
  both tiers' v2 admission buffers and full validation manifests have no
  application-owned retainers; compact metadata and main-thread FASLs are
  itemized. Inspect actual retaining paths as well as counters in a focused
  fixture. Repeated LOAD must not accumulate raw inputs or closed-session
  data; report intended generation/root/registry growth separately. A
  separate forced-GC diagnostic may distinguish retention from delayed
  collection, but is not the timed READY run or a correctness dependency.
- P-2 (P8). Boot archive, after P-1a and before P-1b/P-1c:
  `cross-image.mjs` admits v2; `write.mjs` emits the archive and the reference
  block; heap `codeDigest` is recomputed (the heap
  payload itself must stay byte-equal). Gates: boot identity, READY and
  generation/root-slice checks as P-1a, product engine module count at READY
  = 7. Hold heap/stack/growth policy fixed; measure against P-1a and F-13.
  A-16 release gates for both tiers follow in P-1c, independently of this gate.
- P-3 (P8). `crypto.subtle` digest, further serialized-manifest slimming,
  streamed WABT classification (A-6), and the browser import/export limit check (F-7) on
  the shipped archive. Gate: import count of the runtime archive under 100
  (fixed imports plus `$roots` and `$code_base`) and P-0 instrumentation rerun
  on the changed path. Compact runtime metadata and temporary-input release
  belong to P-1c, not to this later packet.
- P-4 (P7). Record the LL21-b re-decision only after measuring retention
  (R-4), distinguishing live generations from temporary-input retention
  (A-16): chosen packaging v2, the measurements (F-2..F-8, P-0/P-1 timings,
  the retention figures) in the inventory record, `runtime/wasm32/README.md`,
  and the sentences in `namespace-loader-plan.md` and `bundle.mjs` that name
  one function per module; state that the lazy stub loader and
  `installer.mjs` stay v1-only (R-6).
- P-5. Delivery (HOSTFM, later): one archive per tier fetched with
  `compileStreaming` so the browser's implicit code cache applies; split only
  if measured fetch latency requires it.

- P-6 (P5). Guarded direct calls per A-13, after P-4, as its own proposal
  with the compiler change, the one-module-or-two decision and the
  measurement; not scheduled by this plan.
- P-7 (P8). Optional collector root-range interface, distinct from document
  revision MCP-P7. Decide from A-14's measured preparation/C-call costs after
  P-1b; it is not a consolidation or sizing prerequisite. If justified, change
  the owner and `runtime/wasm32/collector.c` together in a separate commit,
  preserving v1 roots, published-only scanning, capacity refusal, moving
  updates and transactional failure behavior. Requalify affected collector
  and owner suites, existing refusal/mutation checks, range/list coexistence
  and forced-collection loader cases against the changed bytes; independent
  review is required before acceptance. Reuse evidence only for unchanged
  inputs and report incremental timing/memory against its measured parent.
  Record deferral explicitly if the measured benefit does not justify it;
  neither P-4 nor the seven-module target requires this optimization.

## 7. Risks

- R-1. WABT scale: the whole-runtime WAT is 560 MB and `wat2wasm` needs 24 s
  and 4.96 GB RSS for it (F-8); the text also exceeds V8's maximum string
  length, so the linker must stream its output. Acceptable on this machine;
  fallback if the build host cannot afford it: assemble two to four archives
  by file order, still under ten modules at READY.
- R-2. Non-V8 import and export limits (F-7): A-3 keeps imports fixed and
  exports at 21,782.
- R-3 (P2). Compilation timing is not established. F-4 and F-8 measure
  construction of `WebAssembly.Module` and `Instance` objects without
  executing Lisp; whether V8 generated machine code for every function at
  construction or defers it to first call is not shown by them, and the
  prototype's asynchronous compile sample is not a cold measurement. P-0 and
  P-1 measure with Lisp executing. The plan promises no READY time.
- R-4 (P2). Retained-code growth (LL21-b) changes shape: keeping one function
  object alive retains its whole generation (the archive instance, 69 MB of
  code, and a 489 KiB root block) instead of one module and its cells. v1
  also never releases an instance today, but the unit of retention grows
  from one function to one archive, so "unchanged" is too strong. P-1
  keeps the existing redefinition and old-function checks and P-4 records
  measured retention across repeated LOAD and redefinition (instances,
  root cells, registry rows kept) before the LL21-b decision. Interactive
  post-READY code uses v1 and is not affected.
- R-5. Evidence identity: per-module `binary_sha256` disappears; `body_sha256`
  per function and A-8 replace it. Audit replay of an archive is one WABT run
  per tier instead of 10,891.
- R-6. The lazy stub loader and `installer.mjs` remain v1-only and off the
  READY path; say so in P-4 rather than porting them.
- R-7 (P3). Capacity: a generation's 125,199-cell block must be checked at
  generation creation against the external region (1 MiB at boot0), the
  root-list bytes, `logCapacity` 262,144 and the collector's scratch
  requirement, and its code window against the configured registry and
  table capacity (A-4), all sized from the manifests at Worker start, not
  fixed in the driver as today's `capacity = 32768`.
- R-8 (P8). Larger allocation spaces reduce collection frequency but enlarge
  the current collector's object-map workspace and may lengthen individual
  pauses. A-14's split GC timers, scratch/layout accounting and P-1b's size
  comparison must establish the tradeoff without attributing root-list work
  to copying. A range is not a single GC reference: every
  published pointer cell still requires tracing. No engine-specific optimum,
  elimination of the 115 s root cost, or post-consolidation RSS is promised.
- R-9 (P8). Dropping one reference is insufficient if a namespace cache,
  captured manifest, view or diagnostic record still owns the data. Logical
  release counters alone do not prove reachability or physical reclamation;
  A-16/P-1c require retaining-path checks and comparable memory milestones.
  Collection timing and engine-internal binary/code retention remain outside
  the loader's control. Keep peak memory, retained inputs and READY RSS as
  separate measurements, without an additive engine-memory estimate.

## 8. Questions for the user

- Q-A. Adopt the target of 7 engine modules at READY, one archive per image
  tier (T-1), with delivery splitting deferred to HOSTFM (P-5)?
- Q-B. Accept that the runtime archive is compiled and instantiated at Worker
  start, before the first FASL asks for code, while publication of every unit
  still happens at opcode 72 in native order (A-5)? This keeps NSL-P2's
  install-on-request rule for table and registry state and moves only engine
  compilation ahead of it.
- Q-C (P3). Order: P-0 as one bounded, instrumented baseline run before P-1,
  with an explicit timeout and partial results retained if READY is not
  reached, as Codex recommends, then P-1 with the same timers rerun as its
  gate?
## 9. Changes in P2

Each entry names the Codex finding it answers.

- Finding 1 (A-4, T-2, fixed code IDs): A-4 rewritten to generation
  allocation with `$code_base` and `$roots` per instantiation; T-2 and T-1
  amended; tests for repeated LOAD, redefinition and old closures across a
  collection added.
- Finding 2 (A-8, equivalence gate): split into structural merge equivalence
  (a) and independent rewrite verification plus execution checks (b).
- Finding 3 (A-1, A-6, A-7, admission contract): the manifest now binds the
  module digests, D2 record, helper inventory, export map, per-function rows
  and per-unit records; classification stays with streamed WABT because
  `binary.mjs` does not decode instruction bodies; the v2 D2 re-derivation
  is specified as one of each step.
- Finding 4 (A-3, A-5, R-7, transactional rooting): new A-12 with capacity
  checks at generation creation, a journaled four-step publication, tests
  for forced collection, failed install and capacity refusal; A-3, A-5 and
  R-7 point to it.
- Finding 5 (F-4/F-8, R-3, compilation cost): eager-compilation claim
  removed; timings labelled construction measurements; the prototype's
  asynchronous compile sample marked not cold and unused.
- Finding 6 (P-1, T-1, intermediate count): P-1's gate is 1,048 product
  modules, P-2's is 7; instrumentation modules and wrapper instances are
  reported separately.
- Finding 7 (R-4, P-4, retention): R-4 restated (one function retains one
  generation); P-4 waits for measured retention.
- Factual corrections: helper bytes are 65.5% of runtime code bytes (F-3,
  D-1); the 69.3% figure was all non-entry bytes. The unit/module
  distinction (8,816 / 10,891) stands.
- Q-C: one bounded baseline run, not three (P-0).

Changes in P3, each naming the Codex correction it answers:

- Code-base units: `$code_base` is the tagged word `4 * code_base`, so the
  sum equals today's `4 * code_id` import (A-4).
- LOAD reservations and capacity: units are reserved at load-session open
  with states unreserved/reserved/published, recursive and overlapping
  LOADs take the next generation, partial loads release reservations on
  close; IDs, rows and roots are consumed per unit; registry and table
  capacity are configured from the manifests with an explicit generation
  count G and a checked refusal (A-4, R-7).
- Boot symbol rewrite: A-8 (b) covers both input forms and requires exactly
  one dereference.
- Generation rollback: A-12 journals generation creation (root block,
  registration, `nextCode`, table growth) and replays prior values on a
  failed instantiation; registration is per unit.
- Cleanup: T-4 names the two digests of A-6; T-1's instance count is 9 fixed
  plus one per generation, 11 at READY.
- Q-C and P-0: explicit timeout with partial results retained.

Changes in P4, each naming the Codex correction it answers:

- Table growth cannot be rolled back: both tables and the registry are
  allocated at the configured capacity during Worker setup, and growth is
  removed from the generation transaction (A-12, A-4).
- Arithmetic: `G = 2` gives 31,032 rows and `G = 4` gives 52,814, not
  32,033 and 61,795; tables are sized separately with the reserved-slot
  offset (A-4).
- Consumption: a generation's ID window and root block are consumed at
  creation and charged against capacity immediately; only registry
  population, cell filling and root registration are per unit, and
  reserved unpublished cells are unavailable to other allocations (A-4).

Changes in P5: STATUS records the user's adoption (U-5); F-12 adds the
measured launch time and memory with attribution and a projection; P-0 adds
memory to its breakdown; A-13 and P-6 record the guarded direct-call
direction; `decisions.md` gains the adoption entry.

Changes in P6, on user direction U-6: F-13 records completed P-0 and F-14
records native defaults and the tiny initial Wasm spaces. F-12's overlapping
attribution/projection is withdrawn in place, as §10 required. D-4 now uses
the measured root and GC costs. A-14 adds initial sizes, headroom policy and
complete layout/scratch accounting; A-15 adds published root ranges while
preserving A-12. P-1 gains correctness gates and the bounded 16/32/64 MiB
comparison; R-8 records the workspace/latency tradeoff. P-0 is complete and
its unchanged baseline is reused. Direct calls remain future packet P-6.

Changes in P7, on user direction U-7: F-15 records the current retention
paths and the limits of memory attribution. A-11 preserves namespace/FASL
semantics while allowing storage changes. A-16 defines bounded staging,
exclusive buffer ownership, transfer, release, compact runtime metadata and
authenticated rereads. P-1 gains lifetime/failure/repeated-LOAD checks and
memory milestones; P-2 extends them to boot; P-3's later serialized-manifest
work does not defer P-1 release. P-4 separates temporary inputs from generation
retention, and R-9 records GC/retainer limits. No implementation, benchmark or
acceptance is recorded by this documentation amendment.

Changes in P8, incorporating review `0a7cd736`: P-1 becomes P-1a (runtime
archive and host slices), P-1b (sizing/growth) and P-1c (input lifetime), with
P-2 immediately after P-1a to finish consolidation. Each change has a measured
parent as well as F-13 for comparison. A-14 splits GC observation and states
the fixed-per-root versus used/live-data costs; A-15 defers a new C collector
range interface to optional P-7 and requalification. A-16 keeps FASL bytes in
the main-thread file host. F-14 adds the current 16 KiB areas and resolves
the bootstrap temporary-stack question from source. §11 records the response;
the imported review is unchanged. No runtime implementation or new benchmark
was performed for this revision.

## 10. Codex import review — 27 September 2026

Imported from Claude's `7932c3d4` after the user's adoption of Q-A/Q-B/Q-C.
P4 resolves the generation-creation rollback and capacity corrections.
The following qualifications govern F-12 and A-13; the imported measurements
above remain as reported by their author, not independently rerun results.

- Memory attribution: `admit-all.mjs` retains the input bundle buffers as
  well as decoded bundles, compiled modules and instances. Its process RSS
  therefore overlaps the bundle-storage estimate; those measurements cannot
  be added as disjoint components or subtracted from the full-launch peak
  to infer a 1.3 GiB Lisp remainder. The separate runs also peak at different
  stages. The 1.5–2 GiB projection is unsubstantiated by this breakdown.
- The archive-only process executes no Lisp, uses dummy service imports and
  a small unshared memory, and does not exercise production archive admission.
  Its 352,387,072-byte peak is approximately 0.328 GiB (0.352 GB), not a
  full-launch memory requirement. P-0/P-1 must measure the complete path.
- Memory evidence must report peak process RSS, RSS at READY, main-thread
  and Worker heap/external/ArrayBuffer counters, linear-memory byte length,
  and live Lisp heap/collector-space sizes at comparable milestones. Worker
  RSS is process-wide: do not add it to main-thread RSS; ArrayBuffer memory
  is included in external memory, so those counters are not additive either.
  Preserve timestamps and the raw run report; distinguish allocated address
  space from resident memory and actual live Lisp data. Keep build-time
  assembler memory separate from launch memory.
- Direct-call compatibility: the user's absent-override fallback and A-13's
  code-identity guard are two possible future designs, not identical rules.
  A missing entry in today's dispatch tables is not permission to call an
  old implementation. An override design must distinguish no override from
  an explicitly unbound function or invalid/unpublished code. A guard design
  must validate the callee before reading its code word and preserve existing
  call checks, argument conventions, closure context and redefinition behavior.
- Wasm direct calls can target imported functions as well as locally defined
  functions (the function index space includes imports). Combining boot and
  runtime is therefore optional, not a correctness requirement for direct
  calls to boot functions. Imports bind at instantiation; their performance
  and optimization opportunities must be measured. See the
  [WebAssembly module specification](https://webassembly.github.io/spec/core/syntax/modules.html#indices).
  A-13/P-6 remains future work; consolidation keeps existing dispatch.

## 11. Codex response to the P6/P7 review — 27 September 2026

The [review](module-consolidation-review-p7.md) is imported byte for byte by
fast-forwarding `0a7cd736520c7006e9c474b47bc74acc65da9a8f`. These are Codex's
plan amendments in response, not a new independent review of P8 or acceptance
of implementation.

- A-14: AGREE. Host preparation and the C call have separate timers, per-GC
  root/used/live counts and the original enclosing total. Roughly constant
  total inventory work is an expectation to test; the C call also traces
  roots and recopies surviving objects.
- A-15: AGREE. Direct host slices land in P-1a through the existing root-list
  ABI; a C range interface waits for measurements and its own qualification
  in optional P-7.
- A-16: AGREE. Main-thread file service retains the FASL set; archive admission
  and its large temporaries belong to the Worker in P-1c.
- P-1: AGREE. The three steps have separate commits and measurements; P-2
  follows P-1a without depending on sizing or release. Compare adjacent
  measured configurations as well as F-13 to avoid cumulative attribution.
- F-14 clarification: the 256 KiB bootstrap temporary stack is verified by
  `MIN_TSTACK_SIZE` and its `new_tcr` call, separate from the initial-stack
  constant. Current Wasm temp/control areas are 16 KiB each, now stated.
- Evidence-count clarification: [audit 185](../stage0/claude-review.md)
  records 123 collector checks and 17 killed mutants, rather than the review's
  59 checks. P-7 requires the applicable retained qualification suites, not a
  reduced count. Those historical checks are not rerun for this plan edit.
