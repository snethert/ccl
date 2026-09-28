# Owned foreign byte ranges

This Stage 2 unit extends `openForeignModule` with declared copies and explicit
allocation ownership. It uses the accepted single-Worker owner. Product Lisp,
shared compiler and upstream kernel sources are unchanged. Accepted at this scope after user-supplied [Claude audit 196](../../../../doc/WASM/stage0/claude-review.md)
(`fe2db2bb`, imported as `7392a92c`); no FMT or LL slot is completed.

A declaration may add:

```js
buffers: {allocate: 'malloc', release: 'free', maximumBytes: 65536}
// On a declared export with matching binary scalar types:
ranges: [{pointer: 0, length: 1, access: 'readwrite', encoding: 'utf-8'}]
```

The allocator must have `(i32) -> i32`, release `(i32) -> ()`, and each range
uses two distinct i32 arguments. Range slots cannot overlap in the declaration.
`maximumBytes` bounds each allocation; it is not an aggregate quota. Generic
calls cannot invoke the allocator, release export or their binary aliases.
Function aliases must declare identical ranges. Declared text is strict UTF-8;
`bytes` is uninterpreted octets. Lengths are explicit, including embedded NUL.
`read`, `write` and `readwrite` select input/output encoding checks. They are ABI
promises by a trusted library, not a memory-access sandbox.

The owner API is:

```js
const h = library.allocate(16);     // May collect: discard any Lisp address.
library.write(h, 0, reloadBytes()); // Recompute rooted source, then copy.
const result = library.call('feed', [library.range(h, 0), 8]);
const copy = library.read(h, 0, 8); // Independent Uint8Array, never a live view.
library.release(h);
```

`reloadBytes` above denotes embedding code, not a new API. It obtains a view
from the current rooted Lisp object only after the allocator's admission. No
collecting call may intervene before the copy. A copy-out destination is
reloaded in the same way. The lower layer never retains the embedding's byte
view and never gives foreign code the Lisp memory or an address within it.
Both copying methods require an idle, admitted library. The foreign memory
buffer is reacquired for every access, including after memory growth.

Handles and range tokens are opaque objects private to one library instance.
Explicit release invalidates the handle before the destructor runs. Repeated
release returns false; using a released range refuses even if the allocator
reuses the same offset. If release throws a recoverable exception, its handle
still stays retired: retrying an uncertain destructor could free twice. This also applies when the owner refuses the destructor entry before it runs
(O-170): the handle stays retired and the allocation may remain unreclaimed
until instance retirement. A trap,
failed admission, invalid allocator result or explicit close invalidates all
remaining handles and drops the instance. Later releases do no foreign work.
A null, out-of-memory or overlapping allocator result retires the instance;
this profile does not expose a separate recoverable malloc-failure result.

A successful call with invalid UTF-8 output signals `UTF8` after readmission
and discards its scalar return value (O-173). Foreign side effects and the bytes
remain; the library and its handles stay live for inspection or release.

Allocator, principal export and release all use the same FOREIGN bracket.
Foreign failures retain the existing caller-tag conversion. Declaration,
range, encoding and allocator-result refusals use checked JavaScript errors;
final product Lisp condition transport is still owed. The generated-Lisp
fixture uses the existing declared host-service extension to deliver actual
foreign exceptions/traps as ordinary Lisp errors after admission. Its cleanup
preserves a primary exception if a later release traps, and never enters the
next destructor after retirement. That cleanup transport remains fixture code.

## Qualification boundary

The [bound result](../../../../doc/WASM/stage2/foreign-buffer-results.json)
records **64 checks in Node, Chromium, Firefox and WebKit**, **26 killed buffer
mutants**, and **seven native-matched Lisp rows / 38 foreign entries / 26 moving
collections**. Dependencies pass **53 owner checks / 38 mutants** in each engine,
**59 existing owner regression checks**, the original **12 Lisp rows / 13 moving
collections**, and **126 scalar checks per engine / 16 mutants**. The finalized
pack is `ccl-evidence/2026-09-28-stage2-foreign-buffers-r1` (669,764 bytes).
It retains 22,705 bytes of failure notes and source deltas; failed-run snapshots
and all successful compilation products are removed.

The portable fixture uses the real collector, synthetic generated-B root frames
and two Lisp heap/stack placements. It tests allocation and export memory
growth, moving collection inside allocator/export/release, retired-space
poisoning, copy isolation, non-ASCII and supplementary UTF-8, offset reuse,
foreign-instance affinity, explicit close, allocator/foreign/destructor
exceptions and traps, and refusals before entry or memory writes. Directed
source mutants must fail their named semantic check, not just a refusal string.

The ordinary Lisp fixture is loaded by `%FASLOAD` after READY. It supplies
explicit UTF-8 octets in a Lisp byte vector, keeps aliases, a closure, bindings
and multiple values live, reloads its source after the allocating calls, copies
back after the principal call, and survives collection during release. The
native CCL run supplies Lisp semantic observations; the WAT library supplies
the declared arithmetic and failure policy. This does not prove a Lisp string
encoder or a final public Lisp foreign API.

The scalar regression is rerun because its implementation changed. The owner
suite adds both `validateLive` call-site refusals and a separate case/mutant for
each of O-165's 17 remaining checkpoint words, plus O-168's inhibited-collection
case. O-167's publication changes remain required before multi-Worker work.

Admission coverage uses the tests' `declare-*`, `refuse-*`, `managed-*`,
`allocator-result-*`, `utf8-*`, `offset-reuse` and `reentry-*` rows. Two bounds
facts are intentionally not claimed as independent directed obligations:
`length <= size - offset` with nonnegative length also bounds the offset;
`MEMORY_RANGE` is defensive because admitted allocations fit a memory that
cannot shrink, and each requested range already fits its allocation. An
initial redundant-offset mutant survived for the first reason; its original
result is retained. Handle identity implies buffer-profile membership, and
retirement makes every live handle inactive before release can be attempted.
These derived checks are not counted as killed semantic mutants.

## Reproduction

Run from the repository root, using verified RAM mounts (the drivers check and
lease them). Existing boot/runtime products may be reused by their pinned
inputs; otherwise regenerate:

```sh
work=/private/tmp/ccl-work/codex/foreign-buffers
python3 -B tests/wasm/stage1/loader-target/build.py "$work/boot" --boot0
python3 -B tests/wasm/stage1/loader-target/build.py "$work/level1" --level1
python3 -B tests/wasm/stage1/loader-target/build.py "$work/checks" \
  --postimage="$work/boot" --source=tests/wasm/stage2/foreign-buffers/checks.lisp
python3 -B tests/wasm/stage2/foreign-buffers/run.py \
  --boot "$work/boot" --level1 "$work/level1" --checks "$work/checks" \
  --playwright /absolute/path/to/playwright-core/index.mjs \
  --browser-config /absolute/path/to/browser-config.json
```

Run the scalar and foreign-runtime dependency drivers as documented in their
READMEs, reusing this boot and level-1 build and compiling the latter's Lisp
fixture separately. Finalized evidence retains source/tool/input identities,
results and original failures. Successful generated Wasm and build products
are disposable. The compiler corpus remains deferred until the entire FFI
layer is complete. Browser Lisp/provider execution, callbacks, owner-queued
finalization, namespace loading and multi-Worker D5 remain open.
