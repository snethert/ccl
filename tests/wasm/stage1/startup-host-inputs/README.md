# Startup image name and arguments

The owner supplies an image namespace name and application arguments. These are
not inferred from Node's process arguments or a browser URL. The earlier browser
configuration acquisition is still re-executed in the Chromium Workers.

Two additional callbacks publish `*heap-image-name*` and
`*command-line-argument-list*`. Three new modules (the callbacks and a two-value
readback) compile with the unchanged integrated compiler in disposable U1. The
joined schedule runs twenty registered callbacks in native registry order,
with preflight and two readbacks, before its ready word. All prior eighteen
callback bodies and native answers are reused by digest. This is a proposal;
no compiler, runtime or kernel file changes and no LL15 credit is claimed.

The native oracle reads U1's actual image-name DEFUN and argv initializer. It
substitutes only their kernel pointer acquisitions with pointers to owner UTF-8
strings, then runs the native decoder, list construction, Darwin composition
and global writes. Return count, return identity and untouched other globals
are checked. The target owner materializes the decoded strings and list;
generated Lisp performs the global writes and returns their values. The two
new globals are fixture symbols, not bindings discovered in a cross-dumped
image. That binding remains part of the image/READY join.

Native Darwin's `precompose-simple-string` is **not Unicode NFC**: it composes
adjacent pairs without canonical reordering, and its combinability gate
excludes characters at or above U+1000. The runner exports the complete pair
domain from the pinned native image and retains all native answers. A portable
sequential map preserves those rules, including unchanged Hangul and the
A/ring/dot ordering case. The source and native image are pinned; this data is
not taken from the host JavaScript Unicode version. Arguments are never
normalized. Ten input cases cover empty arguments, order, duplicate strings,
whitespace, astral characters, combining sequences and 256 arguments.

The materializer copies and freezes owner inputs and checks the entire extent
before writing. Its domain is scalar strings without NUL, at most 4,096 code
points each, 256 arguments, and 65,536 total code points. NUL is refused rather
than silently truncated by the native C-string representation. Names carry no
filesystem authority. The trusted owner provides a dedicated destination range;
this helper does not establish that range's disjointness from other live regions.
It writes ordinary D1 UTF-32 strings and conses, with no weak or native pointers.

The retained run covers 288 joined scenarios in four Workers (Node and pinned
Chromium at 4 MiB and 2 GiB). Each checks full-TCR restoration, declared effects,
completion and installed digests. Every run then roots only the two published
global cells, moves their graph with the integrated collector, poisons the old
bytes and invokes generated readback again. The builder's host references are
not collector roots. The inherited module-omission and no-load controls remain.
Owner checks include every exported native pair, private snapshots, malformed
inputs, exact memory fits and refusal preservation. Eight focused faults cover
NFC substitution, argv order and empty arguments, both roots, an assembled
module omitting the global write, a wrong completion token, and an assembled
module returning with a displaced TSP. Faults are run in Node; positive joined
execution and owner checks are identical in both hosts.

```
python3 tests/wasm/stage1/startup-host-inputs/run.py --output /new/host-inputs
python3 tests/wasm/stage1/startup-host-inputs/packet.py verify --packet ../ccl-evidence/2026-09-20-stage1-startup-host-inputs-r1 --output /new/replay
```

This closes two effects within the 35-entry callback snapshot, not the complete
167-unit retained startup worklist. Home pathnames and logical translations,
scheduler/thread and static-cons effects, the remaining runtime joins, definition
initializers, final image membership and the census/build-path proof remain
open. No whole native bootstrap, complete browser image or engine matrix is
claimed. The browser run retains the accepted separate-Worker-per-placement
policy and rechecks its browser-derived configuration inputs.
