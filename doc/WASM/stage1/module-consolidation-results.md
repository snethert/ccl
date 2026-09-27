# Module consolidation implementation

Implementation of MCP-P8, using and extending Claude's proposed code at
`8b2f1279`. The user accepted the four implementation commits after audit 188;
see the [acceptance record](acceptance-audit-188.json). Results below retain
their original measurement revisions. After SEP-1, the runtime archive is
68,972,499 bytes with 126,226 root cells per generation; its larger post-image
witnesses report 98 product modules / 102 instances (O-138/O-141).
The finalized evidence pack is
`ccl-evidence/2026-09-27-module-consolidation-r1` beside this checkout.

## Consolidation (P-1a and P-2)

The production build now emits one runtime archive, 82 FASL containers, and one
boot archive. The lazy installer and ordinary post-image files retain v1.
The runtime archive contains 10,891 functions, 39 shared helpers, 13 fixed
imports and 21,782 exports in 64,642,870 bytes. It reserves 125,208 root cells
per generation. Code IDs, table slots and root blocks belong to generations;
publication remains at opcode 72 in native FASL order. Partial close releases
unpublished unit reservations. Published code survives close and redefinition.

Symbol identities use package/name pairs; positional compiler wire names are
never identities. File-qualified unit names prevent collisions between each
file's `file_0` and nested function names. The owner charges all reserved cells
against the root-list/log capacity, excludes them from v1 allocation, and only
scans registered cells. Generation and unit publication have separate rollback
journals. Tables are allocated to capacity before generation creation.

| Configuration | READY | Peak RSS | Runtime LOAD returns | GC count | Product modules |
|---|---:|---:|---:|---:|---:|
| Retained P-0 | 341.087 s | 4.833 GiB | 81 | 2,029 | 11,938 |
| Runtime archive, v1 boot | 138.602 s | 2.099 GiB | 81 | 2,029 | 1,048 |
| Both archives | 131.685 s | 2.012 GiB | 81 | 2,029 | 7 |

Each is a fresh process with a 600-second timeout. Journals, exact input and
source hashes, engine identity and macOS peak RSS are retained under `p1a/`
and `p2/`. Product counts exclude the existing observation module and its
wrappers. These are single runs, not statistical performance guarantees.
Runtime-only root reservation plus registration took 0.116 seconds, versus
P-0's 115.076 seconds. Collector time remained 63.305 seconds; consolidation
does not claim to remove that cost.

Both measurements retain 64 KiB initial heap spaces and the old 16 KiB temp
and control areas. A derived layout is necessary to reserve the complete
configured generations and post-image budget. Its first argument address is
16-byte aligned, with the value-stack sentinel eight bytes before it. The
advertised stack defaults now match the allocated areas. Heap headroom and
larger stacks are the following change, not part of these timings.

Independent S-expression comparison checks each symbol dereference and tagged
code offset, reverses the archive renames, reconstructs every original module,
and assembles it with WABT. All 1,042 boot and 10,891 runtime templates are
byte-identical to the retained v1 inputs (231,794,465 bytes). Separate archive
reassembly binds the WAT witnesses to the actual template and full binaries.
The boot heap payload remains byte-identical. All 82 new compiler record sets
match the old records after removing the new identity field. Five FASLs have
changed generated symbol names after loading the additional producer function;
the container preserves its compiler's FASL bytes exactly. This is not a claim
that those five new FASLs equal the old build byte for byte.

The focused archive execution covers arithmetic, six extrema cases, six VALUES
cases, seven ASSQ cases including two type errors, four keyword observations,
nested publication, repeated installation, a second generation and old closures
across actual collection. There are 73 archive/container controls and 14 owner
block checks. The existing 40 owner checks and full v1 loader smoke pass.
The initial stack-alignment failure is retained as `empty.json` and
`empty-v1.json`; `empty-fixed.json` reaches the expected missing-file stop.
The verifier's initial line-comment serialization error was corrected before
its complete successful run; its initial full log was overwritten, not retained.

No shared native compiler file or upstream kernel source changed. Existing
native/R6 evidence remains qualified for its unchanged inputs; these runs are
not new native/R6 comparisons. New Wasm producer records and actual target
execution are verified separately. The archive D2 verifier is a separate module,
leaving the v1 materializer's policy-bound source identity unchanged.

## Reproduction

Use the verified RAM-backed work and cache volumes required by `CLAUDE.md`.
`build.py --boot0` and the default `bundles.mjs` now select archives. `--v1`
on the materialization scripts retains the old fixture path; post-image builds
select it automatically. `archive-build.mjs` and `archive-boot.mjs` can also
materialize already compiled records without recompiling Lisp. The evidence
pack retains new compiler inputs and archive artifacts once, and references
`2026-09-26-stage1-loader-completion-r1/artifacts/boot-r21.tar.gz`,
`bundles-r18.tar.gz` and `focused-r9.tar.gz` for unchanged comparison inputs.

Run `archive-equivalence.mjs` for each tier, then `archive-binding-check.mjs`
to bind its textual witness to the admitted binary. `archive-check.mjs` accepts
the retained focused fixture directory, the smoke archive directory and the
collector binary; `archive-controls.mjs` uses its first two arguments.
`root-block-check.mjs` takes the collector binary. Timed runs use
`startup-baseline.py OUTPUT BOOT BUNDLES --timeout=600`.

## Sizing and headroom (P-1b)

The selected default is **32 MiB per space**, with 16 MiB free headroom,
a 1 MiB value stack, 1 MiB control area and 512 KiB temporary area. Explicit
collection and allocation retry both apply the headroom policy. If headroom
cannot be provided, an allocation that fits still succeeds; a necessary smaller
growth is attempted before refusing the allocation. Inhibited allocation grows
without moving objects and the outer unlock performs the deferred collection.

| Initial space | READY | Peak RSS | Final space | Linear memory | Collections | Host preparation | C collector |
|---|---:|---:|---:|---:|---:|---:|---:|
| 16 MiB | 54.515 s | 2.209 GiB | 32 MiB | 306.312 MiB | 8 | 116.1 ms | 400.0 ms |
| 32 MiB | 54.512 s | 2.196 GiB | 32 MiB | 158.812 MiB | 6 | 96.4 ms | 370.8 ms |
| 64 MiB | 54.236 s | 2.272 GiB | 64 MiB | 302.812 MiB | 2 | 33.3 ms | 254.8 ms |

The three times are effectively indistinguishable as single runs. Starting at
16 MiB grew to 32 MiB and relocated scratch/heap storage, consuming more linear
memory than starting at 32 MiB. Starting at 64 MiB added memory without a
meaningful measured time advantage. The archive and input ownership paths were
held fixed. The measurements use Node v25.6.1 on macOS; they do not qualify
these defaults on other engines.

`collector.copy` remains the enclosing span. `collector.prepare` covers root
listing, workspace preparation and list writes; `collector.c` covers the C
call, including object inventory, maps, roots and copying. Every collection
records roots, used bytes and live bytes. The raw journals and `stage2.json`
retain these observations and stack samples, explicitly lower bounds. The
32 MiB run's observed bounds are 14,864 value-stack bytes, 240 control bytes,
and zero temporary bytes; zero is not a claim of no temporary-stack use.

Twenty-two new layout/growth checks and the existing 40 owner checks pass.
They cover aligned, disjoint layouts, invalid extents, explicit collection,
allocation headroom, fallback without optional headroom, exhausted growth with
valid live roots, inhibited growth, and stack bounds. The C collector bytes are
unchanged. P-7's optional C root-range interface is deferred: host preparation
is below 0.1 seconds total at the selected default, so this workload does not
justify changing and requalifying that ABI.

## Input ownership and release (P-1c)

The main thread now owns the FASL namespace and reads one archive tier on
request. It verifies both file digests on every read and transfers standalone
buffers; both sender buffers detach. The Worker keeps a compact file directory,
consumes archive buffers, and releases raw bytes and full validation manifests
after each admission. Publication remains synchronous. Closing a LOAD releases
its unpublished reservations; terminal exits release outstanding sessions.

With the same archives and 32 MiB configuration, READY took **55.828 seconds**,
with **1.649 GiB peak RSS** and 1.649 GiB RSS at READY. The preceding ownership
configuration took 54.512 seconds and 2.196 GiB peak RSS. This single run shows
lower memory use, not a speed improvement. The baseline remains 341.087 seconds
and 4.833 GiB. Full thread timings and every ownership milestone are retained in
`ownership/` and summarized in `stage3.json` in the evidence pack.

At READY the main thread owns 5,754,020 FASL bytes in 82 buffers; the Worker
owns zero v2 input bytes and zero full validation manifests. Main peak owned
input bytes were 104,447,228; Worker peak was 98,693,208. These describe backing
buffers owned by the application, not engine code storage or an RSS partition.
Each admission-end and file-close observation records ownership separately.

The focused load-session diagnostic exercises real transferred buffers,
digest failures on reread, failed admission, thrown/refused host opens,
overlapping LOAD, partial close, terminal close, and main-thread FASL rereads
after archive cleanup. Three generations intentionally retain one compiled
module, three instances, 657 reserved root cells and distinct logical code IDs
16, 34 and 52; closed-session count is zero. No marked temporary input survives
forced GC: all 37 WeakRefs clear, and the heap snapshot contains only the
deliberately retained positive-control marker. The loader, its tables and its
generations remain alive during that diagnostic. The snapshot is retained;
forced GC is separate from the timed launch and is not a correctness dependency.
All 73 admission controls also assert zero remaining tracked validation inputs
after refusal. The fixture's initial invalid dummy special-symbol failure is
retained, followed by the corrected successful fixture.

Both fresh post-image Workers pass the existing READY contract: 83 returned
loads each, independent 111/222 state and 112/223 functions, Unicode stdout and
stderr, and observed Lisp service adapters. Required-bundle omission and the
empty namespace both stop without the post-image marker. These results complete
the deferred end-to-end archive gates; audit 188 subsequently reviewed them.
The final report also counts v1 post-image modules and instances when present,
in addition to the ordinary seven-module, eleven-instance READY path.

## Final admission and LL21-b decision (P-3/P-4)

The final implementation reaches ordinary READY in **51.041 seconds**, with
**1.688 GiB peak RSS**, 1.687 GiB RSS at READY, six collections, seven product
modules and eleven product instances. The LOAD observer is counted separately:
one instrumentation module and 1,042 wrapper instances. Post-image witnesses
add 50 v1 modules/instances in each fresh Worker, giving 57 product modules and
61 instances for those tests. They are not part of the ordinary seven-module
startup workload. The traced witness again executes exactly the baseline's
5,028 distinct logical file/function pairs.

| Measured step | READY | Peak RSS |
|---|---:|---:|
| P-0, retained baseline | 341.087 s | 4.833 GiB |
| P-1a, runtime archive | 138.602 s | 2.099 GiB |
| P-2, boot archive | 131.685 s | 2.012 GiB |
| P-1b, selected 32 MiB spaces | 54.512 s | 2.196 GiB |
| P-1c, transferred/released inputs | 55.828 s | 1.649 GiB |
| P-3, native hashes and compact manifest | 51.041 s | 1.688 GiB |

P-3 uses Web Crypto for the archive's full/template digests and native Node
hashing for the host file source. The same admission implementation serves sync
and async callers. Caller bytes, manifest and policy are isolated before any
suspension; publication does not suspend. Eleven async checks cover digest and
policy refusals, hash failure cleanup, and caller mutation during suspension.
The final archive suite has 81 refusal/publication controls. Streamed WABT
classification was already required by the original consolidation build.

Per-function helper lists now reference one shared helper set. The manifest
also binds helper body hashes and indices and records callable arity/captures.
Runtime JSON shrinks from 34,050,338 to 22,145,868 bytes; boot archive JSON from
3,383,492 to 2,251,127 bytes. Independent metadata comparison expands the helper
sets and reproduces every original manifest field, then matches all callable
metadata to compiler records. WAT, templates, full Wasm binaries, all 82 FASL
containers and the heap payload are unchanged, so the original complete
rewrite/byte-equivalence evidence remains qualified. Boot metadata/codeDigest
changes are rebound by freshly compiled post-image witnesses.

Against P-1c, host archive reads fall from 2.508 to 0.246 seconds and the runtime
archive compile/materialization span from 2.987 to 0.532 seconds. Exclusive
unmeasured Lisp/host/observer work remains 41.343 seconds; these measurements do
not identify pure Lisp CPU time. Final owned-input peaks are 92,542,758 bytes
on the main thread and 86,788,738 in the Worker. READY still retains only the
main thread's 5,754,020 FASL bytes, with zero Worker v2 buffers or full validation
manifests. The final expanded heap diagnostic marks 3,922 objects, including
nested D2 inventories and function/entry arrays; none remains reachable. The
positive control is identified explicitly in the retained snapshot. Compact
runtime metadata consists of 10,891 dispatch rows, 8,816 unit records and an
82-file directory; these intentional records are distinct from raw inputs.

The first P-3 measurement was 50.491 seconds/1.721 GiB. A final policy snapshot
guard and explicit instrumentation counts were then added and verified; the
final measurement above binds that source. Both journals remain in the pack.
The small timing/RSS differences between individual runs are not a statistical
ranking. Relative to P-1c, P-3 shows lower admission time and slightly higher
peak RSS, rather than an additional proven memory reduction.

Both shipped archives compile and instantiate in Chromium 145.0.7632.6,
Firefox 146.0 and Playwright WebKit 26.0. Each has 13 imports; boot has 2,084
exports and runtime 21,782. These are construction/limit checks, not browser
Lisp startup qualification or a claim about installed Safari. The initial
automation-version mismatch and Chromium's main-thread synchronous 8 MiB
restriction are retained as failures. The corrected harness pins matching
Playwright 1.58.1 and uses asynchronous instantiation; no engine limit is raised.

LL21-b now selects **one archive per bootstrap tier**, with generation-relative
code IDs and paired slots. A live generation keeps the entire compiled module,
its reserved code window and root block; unloading generations remains outside
this implementation. Repeated LOAD growth is intentional and measured, while
raw inputs and closed sessions do not accumulate. V1 post-image files and the
lazy stub loader/installer retain their existing packaging. P-5 delivery and
P-6 guarded direct calls remain the plan's explicitly deferred future work;
P-7's optional C collector range ABI is deferred on the measured evidence.

Implementation commits are `484643be`, `ac813bce`, `5e807214` and `cd0947f1`.
The [evidence index](module-consolidation-results.json) binds the retained
results, artifacts and reproduction commands. Audit 188 reproduced both archives
and all linked function templates at the final SEP-1 revision, plus the host
controls and retention diagnostic. O-134 remains open: the default two-generation
budget must refuse through the file service when exhausted, with the budget
documented alongside that fix. This acceptance grants no new criterion credit.
