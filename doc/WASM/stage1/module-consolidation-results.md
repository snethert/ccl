# Module consolidation implementation

Implementation of MCP-P8, using and extending Claude's proposed code at
`8b2f1279`. Results below are author verification, not independent acceptance.
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
