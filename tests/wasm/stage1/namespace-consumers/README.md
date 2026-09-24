# Read-only namespace consumers

This proposal runs CCL's `PROBE-FILE`, `TRUENAME`, `OPEN :INPUT`, file-stream
construction, binary and character input, positioning, EOF and unwind cleanup
against the admitted byte namespace. It completes the NSL-1 consumer work after
its host and primitive packets. Shared source changes are applied in disposable
U1; integration and S1-NAMESPACE-a acceptance await Claude's review.

The public consumers retain their original Lisp policy. Target branches replace
native file calls, foreign pointer buffers and excluded OS operations at their
source boundaries. IO-BUFFER owns a collector-managed ivector; its native pointer
slot is NIL. The mailbox client roots the buffer and reloads it after collection,
then validates the actual byte extent before copying. Reads larger than the
8,128-byte request payload complete through repeated requests. Stream disposal
closes the descriptor and leaves memory reclamation to the collector.

`proposal.py` emits the shared-source and runtime changes. New target code
provides integer-vector allocation/access and byte copying, the small strong-table
and package boundaries required by initialization, manifest-root initialization,
and foreign-type initialization without a CDB. Native foreign calls and output
files remain excluded. Strong type and function-name registries are explicitly
owned for the image lifetime; this does not implement weak tables or the full
package system.

The compiler is CCL's real file compiler. Function references emitted before
load time keep their linker identities. The linker discards unreachable code and
constant pools while preserving object identity and sharing. The native projection
remains the exact READY graph source: 612 classes and 53 generic functions;
new stream prototypes, methods, class-name metadata and foreign types initialize
on the target. No new native objects are projected.

The original namespace cases cover colliding names, Unicode names, logical CCL
paths, alternate roots, missing files, directories, empty files, independent
handles, signed/unsigned 8/16/32-bit streams, Latin-1 and UTF-8, line input,
9,000-byte reads, buffer-boundary seeks, EOF conditions, closed-stream errors,
and `THROW` cleanup. Invalid roots preserve all three published root variables.
Standard foreign types use the registered 32-bit ABI and make zero CDB opens.

Each of four fresh Workers uses an 8 MiB or near-2 GiB heap placement, with
allocation-triggered collection and with an additional collection at every host
request. Observations include buffer contents, positions, error classes and
pathnames; the host records every request and verifies that no handle remains
open. Direct controls cover 14 byte-copy layouts, 17 byte-copy refusals,
16 integer-vector allocation refusals, 11 linked-symbol admission refusals, and
12 unsupported or invalid table options. The primitive R2 and provider controls
remain prerequisites.

One native substitution is explicit: `OPEN :OUTPUT :IF-EXISTS :SUPERSEDE` fails
natively while creating a random `/ccl/[digits].tem`; the target reports the
requested `a.bin`, refusing before creating or renaming anything. Both exact
observations are retained and checked. The provider's declared `a.bin/..` and
`a.bin/` path differences and primitive short-read cap remain declared too.

Qualification includes a cold compiler rebuild, all 26,048 full-corpus original
comparisons, the accepted READY/string-stream consumers in five boots and 20
fault refusals, all 21,843 enabled native tests, decoded native FASL comparisons,
and 153 reader comparisons (nine changed shared files across 17 profiles).
Fifteen byte-identical complete foreign-reader forms are proved compositionally:
macOS has no Windows interface database; every changed form is read normally.
The reader proof retains each omitted form and its exact hash. Native executable
code and every existing architecture/module profile remain unchanged.

```sh
# Complete cold qualification, with no retained compiler session required.
python3 tests/wasm/stage1/namespace-consumers/run.py \
  /private/tmp/ccl-work/codex/namespace-replay

# Rerun the four Workers in an existing prepared consumer directory.
python3 tests/wasm/stage1/namespace-consumers/run.py \
  /private/tmp/ccl-work/codex/namespace-replay/consumers --matrix-only

# Replay the finalized Wasm in fresh Workers, reusing hash-bound native rows.
python3 tests/wasm/stage1/namespace-consumers/packet.py verify \
  ../ccl-evidence/2026-09-24-namespace-consumers-r1 \
  /private/tmp/ccl-work/codex/namespace-packet-replay
```

`develop.py --compiler-cache KEY` is an optional, hash-checked development path.
`trace.py` instruments only disposable Wasm for debugging; traced binaries are
excluded from the finalized execution evidence. The original consumer compiler
stops and subsequent relevant failures are retained in the final evidence pack.

This ships the full-profile mailbox path. NSL-P2 defers JSPI. This packet does not
publish or load source/precompiled bundles: the cross-loader and `%fasload` bundle
reader are NSL-2/NSL-3 work. Files cross-compiled / cross-loaded / target-loaded
remain **0 / 0 / 0**. Accepted originals remain **575 / 535 non-NIL**, and the
ledger remains **21 accepted / 12 missing** until independent review and acceptance.
