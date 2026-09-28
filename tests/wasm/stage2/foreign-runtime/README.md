# Single-Worker foreign owner

This Stage 2 unit connects the scalar foreign library to `CollectorOwner` and
ordinary generated Lisp. Accepted at its retained scope after user-supplied
[Claude audit 195](../../../../doc/WASM/stage0/claude-review.md).
It completes no FMT or LL slot. Product Lisp, shared compiler and upstream
kernel sources are unchanged.

Qualification: **33 owner checks per engine**, **19 killed owner mutants**,
**126 scalar checks per engine / 16 killed scalar mutants**, and **59 existing
owner regression checks**. Node's post-READY Lisp run matches **12 native rows**,
with **20 foreign entries / 13 moving collections**. The
[result binding](../../../../doc/WASM/stage2/foreign-runtime-results.json) pins
the 1,144,722-byte evidence pack and its original failures.

`CollectorOwner.foreignBoundary` supplies synchronous `enter`/`leave` hooks for
`openForeignModule`. Entry requires the admitted one-Worker profile, RUNNING,
a live unlinked TCR, no foreign or mailbox descriptor, and the published B
argument-root frame. It publishes that frame as `foreign_descriptor`, then
atomically publishes FOREIGN. All refusals precede publication. Leave checks
token identity, publication and stable checkpoints, validates the live heap,
clears the descriptor and atomically returns to RUNNING. Generated code reloads
its own roots after returning through the existing B service adapter.
Allocation bounds, a moved binding-vector address and tagged roots retain the
collector's new values. The owner never restores a saved raw Lisp heap address.

`collectForeign()` is a trusted synchronous collector capability on that same
Worker. It can be supplied as a declared import to a cooperating foreign
library. It does not execute Lisp, and state remains FOREIGN during collection.
A general Lisp callback, a second collector Worker, `gc_gen` ownership/parity,
interruptible foreign execution and callback re-admission are still owed.
Owner return failure is fatal; the embedding must not resume Lisp after it.
The scalar module retires on failed admission, as in the accepted first unit.

The portable owner suite uses the real collector with synthetic B frames to
isolate admission. It covers two stack/heap placements, view refresh after
memory growth, moving roots, initialization, exception/trap/host failures,
retirement, cross-library reentry and refusal without memory writes. Each
independent clause needs a directed case or a recorded equivalence argument.
Audit 195 identifies missing directed cases for the entry/exit live-heap
validation calls and 17 checkpoint words (O-165), carried into the next unit. The preliminary 16-byte root-head span
check is redundant for admission with the complete root extent and count >= 2;
it ensures the header read is safe. Its removal can change the refusal reason,
which is explicitly excluded from the semantic mutation count. The private
`busy` checks during collection supplement the synchronous boundary checks:
there is no public reentrant JS call inside the C collector. The collector's
existing live-heap checks retain their prior directed regression coverage.

`checks.lisp` is loaded after the existing driver first reaches READY. The
`--post-ready-load` extension calls the ordinary compiled `%FASLOAD` entry with
a rooted pathname, through its public B wrapper; both `(values t nil)` results
are checked. No runtime file is host cross-loaded. The optional
`--host-extension` hook supplies fixture opcode 100 at the existing host-process
service entry, without replacing compiled Lisp definitions or generated code.
The fixture opens the foreign module lazily from that generated call, so
instantiation and initialization have the same live roots as ordinary calls.
Only unboxed integers enter foreign code. The fixture translates the private
boundary failure tag to a status, then ordinary Lisp ERROR, HANDLER-CASE and
UNWIND-PROTECT exercise condition delivery and cleanup after admission. This
transport is a fixture, not the final Lisp foreign-call API or condition type.

Collection runs inside the foreign initializer and principal export. After
each move, instrumentation poisons the entire old live extent. Lexical aliases,
a closure, dynamic bindings and multiple values must survive; both a Wasm throw
and two distinct traps run one Lisp cleanup, with further calls to trapped
instances refused. All 64 TCR words are compared across each bracket. During GC,
the six collector-owned words (allocation bounds, binding-vector address,
next-method root and collection counter) retain their live values; other words
must match exactly. The native reference supplies Lisp semantic observations;
foreign arithmetic and retirement expectations come from the declared fixture.

O-159/O-160 are carried in the scalar suite: duplicate binary import names with
a phantom declaration, and a void import returning a Promise. Both added
remove-one-check mutants must fail their named refusal. O-162's fatal async
owner rule is documented there; call-refusal case IDs are now stable (O-164).

## Reproduction

Run from the repository root. Drivers verify both RAM mounts and lease fixed
workspaces. A qualified existing boot and runtime build can be reused by its
input hashes. If unavailable, regenerate it from the committed sources:

```sh
work=/private/tmp/ccl-work/codex/foreign-runtime
python3 -B tests/wasm/stage1/loader-target/build.py "$work/boot" --boot0
python3 -B tests/wasm/stage1/loader-target/build.py "$work/level1" --level1
python3 -B tests/wasm/stage1/loader-target/build.py "$work/checks" \
  --postimage="$work/boot" --source=tests/wasm/stage2/foreign-runtime/checks.lisp
python3 -B tests/wasm/stage2/foreign-runtime/run.py \
  --boot "$work/boot" --level1 "$work/level1" --checks "$work/checks" \
  --playwright /absolute/path/to/playwright-core/index.mjs \
  --browser-config /absolute/path/to/browser-config.json
python3 -B tests/wasm/stage2/foreign-scalar/run.py \
  --playwright /absolute/path/to/playwright-core/index.mjs \
  --browser-config /absolute/path/to/browser-config.json
```

The driver binds sources, compiled inputs, regeneration recipes and tool hashes.
Results contain binary hashes; successful generated Wasm is deleted after use.
Retain any failing run before resetting its directory. No compiler image is
retained per run. Browser owner execution uses shared Lisp memory with COOP/COEP;
full generated-Lisp/browser-provider execution remains owed. The compiler corpus
is deliberately deferred until the whole FFI layer is complete, per user direction.

The first post-READY driver probe tried `%WASM-FIND-SYMBOL` to resolve
COMMON-LISP:LOAD; its public call signalled checked 4 before the foreign fixture.
That probe remains unresolved and is retained with its diagnostic inputs. The
qualified path calls the existing compiled `%FASLOAD` directly. It proves
ordinary target FASL loading after READY, not general post-READY symbol lookup
or the COMMON-LISP:LOAD pathname frontend. Initial fixture-layout, shared-memory
profile, native-kernel permission, missing regression-output argument and
`%FASLOAD` result-count failures are retained as well.
