# Module consolidation plan — from 11,938 engine modules at READY to 7

```
DOC-ID        MCP-P6 (P1 aea879ee; P2 f22d8756 folded in Codex's seven findings; P3 56273a33
              its four corrections; P4 folds in Codex's three corrections of P3, after which
              Codex considers the plan valid for implementation; P5 records the
              user's adoption, the memory measurements F-12 and the direct-call direction A-13;
              P6 records completed P-0 and the user's heap/stack sizing amendment)
STATUS        ADOPTED by the user, 27 September 2026 (U-5: "Yes to all three"), after
              Codex judged P4 valid for implementation; packet contents, sizes and order
              remain Codex's implementation choices; A-13 is a recorded future direction
AUTHOR        Claude (Fable 5.1), 27 September 2026, after the READY commit ea82d8e7
AMENDMENT     Codex, 27 September 2026, user direction U-6; documentation only
READER        Codex, as Stage 1 author; review amended items by ID
BASE          wasm2 at ea82d8e7 (READY under decision A2); measured on the retained
              loader-startup-timing-r1 inputs boot-r21 and bundles-r18
TOUCHES       P6: this document and doc/WASM/decisions.md; no implementation change
CHANGES       §9 records revision history; §10's import qualifications still apply
```

## 0. How to read this

Every item carries an ID; IDs from P1 are kept, amended items are marked with
revision labels such as `(P6)`; new items continue the numbering. Review amended
items by ID with `AGREE`, `DISAGREE`, `AMEND` or `UNVERIFIED`. Facts (F) name
their measurements or source evidence. F-13 is the executed P-0 baseline;
F-14 gives native defaults and the current Wasm growth policy. Diagnosis (D),
target (T), archive design (A), packets (P), risks (R) and questions (Q) follow.
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
- F-14 (P6). Native CCL32 uses 1 MiB control, 1 MiB value and 512 KiB
  temporary-object stacks for ordinary listener/threads, excluding guards
  ([source](../../../level-1/l1-lisp-threads.lisp)); the initial kernel
  bootstrap temporary stack is 256 KiB. The native free-heap threshold is
  16 MiB beyond live/image data, not a fixed total heap size
  ([kernel defaults](../../../lisp-kernel/pmcl-kernel.c)). In P-0, Wasm
  started with two 64 KiB spaces, growing to two 8 MiB spaces at READY.
  The current owner grows only if collection cannot satisfy the next
  allocation; a nearly full heap can therefore collect repeatedly without
  gaining useful free space ([owner](../../../runtime/wasm32/collector-owner.mjs)).
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
- D-4 (P6). F-13 identifies root allocation as the largest measured cost;
  collection and residual execution are also substantial. A-7 removes
  repeated per-module admission work, while archive admission still has a
  cost. A-15 addresses root bookkeeping and A-14 addresses allocation
  headroom. Neither their savings nor a new READY time is established until
  P-1 measures them; a reserved root block does not by itself prove that
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
- A-11. Files stay as they are: 82 FASL streams, `bundleNamespace` and
  `%fasload` unchanged. The `.w32bundle` container loses its per-module code
  and templates and keeps the FASL bytes and the unit catalog; the archive
  is a separate file named by digest in the namespace.

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
  P6: A-15 specifies direct unit slices and registered ranges; its
  optimization must preserve every reservation and rollback condition here.
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
- A-14 (P6). Heap and stack configuration, included in P-1 under U-6.
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

  Align advertised Lisp stack defaults with the allocated areas and retain
  checked overflow boundaries. The engine's actual Wasm call stack and the
  service C stack are separate from these Lisp areas. The browser API has
  no portable call-stack-size setting; enlarging linear memory cannot raise
  that limit ([WebAssembly API](https://webassembly.github.io/spec/js-api/)).
- A-15 (P6). Root registration by published ranges. Reserve each generation's
  block once and derive a unit's slice directly from its manifest offset;
  do not repeat a scan of all occupied external cells for each publication.
  Keep capacity/ownership accounting so publication validates its slice
  without re-enumerating all prior roots. Preserve A-12's checks and journals.
  Represent registered sub-ranges explicitly, with a collector range path
  that avoids constructing one host-side address-list entry per cell.
  Only published units' ranges are roots; reserved but unpublished gaps must
  remain excluded. Retain individual-cell support for v1 code and other
  root owners, with no overlapping allocation or duplicate registration.
  Rollback removes/restores exactly the affected ranges and values.
  Ranges reduce bookkeeping; collection still examines their tagged values
  and updates moved references. Measure allocation, registration and
  collection costs separately; no complete removal of F-13's costs is assumed.
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
- P-1 (P6). Runtime archive (A-1, A-2, A-3, A-4, A-5, A-6, A-7, A-10, A-11,
  A-12, A-14, A-15); `target-bundle.mjs`/`target-load-session.mjs` gain the v2 admission
  and generations; v1 stays for post-image files. Gates: READY reproduces (81
  nested loads, two post-image loads in two fresh Workers, both refusals,
  Unicode output); A-8 (a) and (b) over all 10,891 functions; A-4 and A-12
  tests; product engine module count at READY = 1,048 (1,042 boot modules
  unchanged, one runtime archive, five services and adapter) with
  instrumentation reported separately. Repeat P-0's instrumentation on the
  changed archive path; report its complete time/memory breakdown against F-13.
  Verify published-range movement and rollback, unpublished gaps, v1/range
  coexistence and capacity refusals. Verify stack boundaries, disjoint layout,
  headroom growth before allocation failure, inhibited collection and checked
  refusal with valid state when growth cannot satisfy an allocation.

  Compare initial space sizes of 16, 32 and 64 MiB per space on the same
  archive, engine and workload, keeping the 16 MiB free-space policy constant.
  A 16 MiB initial space may grow to meet that target; record actual sizes
  rather than treating these as fixed heap caps. Use one fresh process per
  candidate, a 600 s timeout and retained partial journals, reusing the default
  run as the 32 MiB candidate. Record READY time, peak/READY RSS, live and
  allocated heap bytes, space/scratch/linear extents, GC count/time, root
  allocation/registration time and observable stack usage (label sampled
  high-water values as lower bounds). Bind the changed configuration and all
  input hashes. Select the smallest configuration with an acceptable measured
  time/memory tradeoff; report inconclusive single-run differences as such.
  Initial sizing evidence is on the P-0 engine; reuse the same defaults for
  subsequent engine qualification and record untested engines explicitly.
- P-2. Boot archive: `cross-image.mjs` admits v2; `write.mjs` emits the
  archive and the reference block; heap `codeDigest` is recomputed (the heap
  payload itself must stay byte-equal). Gates: boot identity, READY as P-1,
  product engine module count at READY = 7.
- P-3 (P2). `crypto.subtle` digest, manifest slimming, streamed WABT
  classification (A-6), and the browser import/export limit check (F-7) on
  the shipped archive. Gate: import count of the runtime archive under 100
  (fixed imports plus `$roots` and `$code_base`) and P-0 rerun.
- P-4 (P2). Record the LL21-b re-decision only after measuring retention
  (R-4): chosen packaging v2, the measurements (F-2..F-8, P-0/P-1 timings,
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
- R-8 (P6). Larger allocation spaces reduce collection frequency but enlarge
  the current collector's object-map workspace and may lengthen individual
  pauses. A-14's scratch/layout accounting and P-1's size comparison must
  establish the tradeoff. A range is not a single GC reference: every
  published pointer cell still requires tracing. No engine-specific optimum,
  elimination of the 115 s root cost, or post-consolidation RSS is promised.
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
