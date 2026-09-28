# Scalar foreign-module boundary

First Stage 2 implementation unit for HOSTFM FM-1–FM-5, FM-7, FM-9 and FM-11.
Accepted at its retained scope after user-supplied Claude audit 194, imported
as `8d2aee38`. This does not complete any FMT or LL slot.

Final qualification: **124 checks per engine** (Node, Chromium, Firefox and
WebKit), **14 killed source mutants**, no skips. The
[result binding](../../../../doc/WASM/stage2/foreign-scalar-results.json) identifies
sources, tools and retained evidence. The pack keeps the initial browser
executable-discovery failure, mismatched automation driver and WebKit's different
multi-memory compile refusal. Interface admission now precedes engine compilation,
so all engines issue the same checked extra-memory refusal before any entry.

## Interface and admitted profile

`openForeignModule({bytes, declaration, imports, boundary, errorTag})` returns
an opaque library with `call(name, args)`, `close()`, a read-only `state`, and
its immutable declaration. It never exposes the foreign memory or raw exports.
The caller passes scalar values only; this unit has no Lisp-memory parameter.

The version-1 declaration names the library, SHA-256 of its bytes,
`policy: "per-worker"`, all function imports/exports and their `params`/`results`,
one `memory: {export, minimum, maximum}`, the defined tables' `{minimum, maximum}`
limits, and `initialization: {kind}`. Initialization is explicitly `none`,
`start`, or `export` with a `name`. Every exported alias of the selected
initializer is unavailable to later calls. Internal library code remains
trusted; it can invoke its own functions.

Only i32/i64/f32/f64 function types are admitted. i32 and i64 values must be in
their signed ranges; i64 is a BigInt. Floats are Numbers, preserving infinities,
NaNs and signed zero; f32 rounds at the engine boundary. Sparse, coerced or
out-of-range arguments refuse before entry. Checked arguments and multi-result
host returns are copied before the engine consumes them. Foreign globals,
elements and data may initialize only that instance's resources. The engine
validates the full module. The independent reader restricts its surface:

- Exactly one defined, bounded, unshared wasm32 memory, exported by the declared
  name. No imported memory, table, global or tag; no reference-valued function
  types, memory64, shared memory, or unbounded resources.
- Defined tables are bounded funcref tables with exactly declared limits.
  Exported resources other than the one memory are refused in this profile.
- Every actual function import has exactly one declaration and a supplied
  synchronous function. Only those functions are passed to instantiation.
  Promise returns refuse; this API is not a suspension transport.
- Every exported function has exactly one matching declaration. Start presence
  must match the convention. An explicit initializer must exist and be `()→()`.

The embedding owns `boundary.enter(operation)` and `boundary.leave(token)`.
Enter publishes roots/FOREIGN and returns a token; if it throws, it must do so
without leaving partial publication. Leave performs admission and root reload
before returning. Neither hook may suspend by returning a Promise. This unit
tests hook sequencing; it does not implement the production D5 protocol.
Re-entry and closing an active instance refuse. Instantiation itself is always
bracketed, even without a start section. An explicit initializer uses a second
bracket, and no public library is returned until initialization succeeds.

`errorTag` must have signature `(i32)`; a resource-only link checks that signature
before foreign execution. After successful admission, foreign failures become
catchable exceptions on this tag: 1 trap, 2 Wasm exception, 3 host failure.
`foreignFailure(error)` retrieves the original cause and library/operation
metadata. A trap retires the instance before admission; subsequent calls refuse
without entering foreign code. Initialization failure never publishes a ready
library. Owner admission failure retires the instance and throws a fatal
AggregateError retaining the foreign cause first; it cannot safely resume Lisp.
Close performs host-only retirement and is idempotent. Allocations, destructors,
callbacks and finalizers are not supplied by this unit.

## Qualification and limits

The portable suite executes in Node and a Worker in each installed Chromium,
Firefox and WebKit engine. It checks scalar extremes, multiple results, private
state/memory, growth, start/explicit/no initialization, initializer aliases,
snapshots, malformed declarations, strict arguments, host failure/async refusal,
re-entry, retirement and owner-hook failures. Separate foreign Wasm `throw`,
`unreachable` and out-of-bounds cases distinguish exceptions from traps. A
hand-written Wasm caller catches the port tag and increments its cleanup
counter exactly once. This is not a generated Lisp UNWIND-PROTECT witness.

Each independent admission rule has a directed refusal. Binary framing,
section ordering, function indices, instruction validation and start-function
type validity also receive the engine's validation before any instantiation;
removing a redundant parser framing check cannot admit a malformed module
through `WebAssembly.Module`. This unit does not claim exhaustive malformed
binary fuzzing. Remove-one-check controls target semantic admission and call
guarantees, and require the named witness to fail in a fresh process.

Equivalent/unreachable clauses are explicit: with resource imports prohibited,
one defined memory and one exported memory, the engine also enforces memory
index zero and rejects a zero-memory module that names a memory export. It
independently rejects non-`()→()` start functions. One non-function resource
import exercises the same kind-zero predicate for memory/table/global/tag.
`IMPORT_OUTSIDE_FOREIGN` is a defensive check: the opaque instance never exposes
an import wrapper, so all reachable wrapper calls are inside `invoke`. The
internal retired-state check likewise supplements the public call-state gate.
These checks remain present; no artificial private access is used to claim
independent public-path witnesses for them.

No production TCR restoration, moving collection, memory-placement comparison,
callback, pointer ownership, namespace provider or finalization claim follows
from these tests. The broader [Stage 2 work](../../../../doc/WASM/stage2/README.md)
keeps those obligations open. R6/R6a is unchanged because shared compiler and
upstream kernel sources are untouched. Product Lisp lines changed: zero.

## Reproduction and retention

Run from the repository root. The driver verifies both RAM-backed volumes and
leases a fixed workspace. WABT and Node use the existing validation toolchain.
Browser testing needs Playwright matched to the installed browsers. An optional
JSON configuration maps `chromium`, `firefox`, and `webkit` to executable paths.

```sh
python3 -B tests/wasm/stage2/foreign-scalar/run.py \
  --playwright /absolute/path/to/playwright-core/index.mjs \
  --browser-config /absolute/path/to/browser-config.json
```

Without `--playwright`, the driver runs Node and explicitly records the browser
skip. Results bind source files, generated binary hashes, tools, check names and
each mutation. Successful generated WAT is removed after assembly and Wasm
after execution. An unfinished run cannot be overwritten before its failure
evidence is retained. No compiler image, native oracle or large build is needed.
