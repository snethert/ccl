# LL10 constants — isolated implementation

Run from the checkout root:

```sh
python3 tests/wasm/stage1/constants/verify.py
```

`Encoder.encode(descriptor)` returns either a tagged immediate word or complete,
8-byte-aligned, pointer-free object bytes. It performs no heap write or allocation
in the target. D1 supplies subtags, fixnum limits and scalar float offsets.
Integers use canonical decimal strings; floating values use exact-width lowercase
hexadecimal bit strings, avoiding host numeric conversion and NaN canonicalization.
Strings use lists of character codes. Specialized vectors use an explicit subtype
and element list; complex float elements are real/imaginary bit-string pairs.
The caller may set `max_bytes`; its default 16 MiB is an encoder resource budget,
not a Lisp array-size promise. Header counts are separately bounded to 24 bits.

Examples: `{'kind': 'integer', 'value': '536870912'}`,
`{'kind': 'string', 'value': [65, 128578]}`,
`{'kind': 'vector', 'type': 'fixnum', 'elements': ['-1', '536870911']}`.
Supported vector types are bit, s8/u8, s16/u16, s32/u32, fixnum, single-float,
double-float, complex-single-float and complex-double-float. D1 has no s64/u64
vector subtype. Single/double float scalar kinds use `value` for the bit string;
character and singleton (`nil`/`t`) kinds return immediate words.

The six test groups include literal byte oracles, integer sign-extension limbs,
float signed zeros/subnormals/infinities/NaN payloads, supplementary characters,
vector widths and padding, target range refusals, and header/resource limits.
Five semantic mutants cover host integer classification, reversed float bytes,
tagged string elements, tagged fixnum-vector elements and omitted vector padding.
The deterministic verification record pins implementation, tests and source inputs.

Source derivation: `xdump/xfasload.lisp` supplies headers, limb order, scalar floats
and allocation alignment; `x8632-misc-byte-count` supplies vector padding;
`x862-vset` explicitly unboxes fixnum-vector elements; x8632 bit-vector access uses
least-significant-bit-first indexing. The character code domain follows U1's
`lib/chars.lisp`, including its full range below #x110000.

This is an isolated supporting component, not S1-LL10-a execution or qualification.
The encoder alone claims no native/Wasm comparison; later components below add
linking, transport and generated execution. Shared source remains unchanged. All
components feed the complete LL10 qualification packet described below.

Development: the first oracle gave a two-element s16 vector sixteen bytes rather
than eight. Four header bytes plus four payload bytes already satisfy D1 alignment;
the encoder was correct. The original tests, encoder and failing output are in
`development/`. Source inspection also corrected the initial, unexecuted assumption
that fixnum-vector elements were tagged before the first test run.

## Identity graph linker

`compile_pool(graph, symbols, max_bytes)` in `pool.py` builds an immutable
relocatable plan. `plan.at(base, limit)` materializes fresh bytes and tagged roots
without writing target memory. `objects` is an ordered list of `{id, value}`
records; `roots` is an ordered value list; `version` is 1. Pointer-free heap
objects use the encoder descriptors. Node objects add `cons` with `car`/`cdr`
and `general-vector` with `elements`. A value is an immediate descriptor,
`{ref: identity}` or `{symbol: owner-key}`. Every heap object needs its own
identity; equal contents never imply shared identity. General vectors are the
pool representation, so references between parent and child pools use the same
mechanism as cyclic literals.

All objects are allocated before linking, including unused pools for cold
functions. Forward references, cycles and repeated references therefore require
no recursion or execution. D1 controls cons field order and tags. Pointer fixups
and root fixups are separate; external symbols and canonical NIL/T words never
relocate with the pool. Symbol words come from a trusted owner registry; this
component does not authenticate their target object headers or install symbols.
Malformed graphs, missing references, immediate object identities, byte-budget
exhaustion, address overflow and overlap with referenced external object bases
are refused. The owner must supply a region it owns; this is not a heap allocator.

Run `python3 tests/wasm/stage1/constants/verify_pool.py`. Six test groups use
literal word/byte expectations, not a read-back through the linker, and six
semantic mutants must fail those assertions. Cases include sharing versus equal
objects, cyclic/forward references, cold pools, exact-fit memory ends, unchanged
external words, distinct package/case keys and refusal preserving a reusable
plan. Tests use addresses above 2 GiB and up to the final aligned wasm32 region,
but only materialize small host buffers; no high-address target allocation or
Worker execution is claimed. `pool-verification.json` pins this run. The first
run and all six controls passed without a development failure.

`Pool` is an internal linker product, not an external deserialization boundary.
Target-memory serialization/restore, ownership validation at installation,
compiler IR extraction and generated loads are covered by the later checkpoint
below. The public B ABI and shared compiler/runtime files remain unchanged.

## Materialized-memory snapshot transport

Run `python3 tests/wasm/stage1/constants/verify_snapshot.py`. This adds an isolated
Node transport, `snapshot.mjs`: `capture(memory, manifest)` reads current unshared
Wasm memory; `restore(bytes, expectedDigest, memory, base, regionBytes, symbols)`
checks the complete snapshot before one destination write. The manifest supplies
the complete owned interval, object identities/offsets/tags, roots and owner
symbol identities. The snapshot binds the D1 schema and contains target bytes,
not the original constant recipe. Its expected digest comes from the trusted
owner; this is integrity checking, not code signing or a production loader.

The reader derives object extents and pointer fields from D1 headers and the
cons/general-vector layouts. Contiguous coverage includes cold objects. Exact
object-start pointers relocate; interior/unknown pointers refuse. Raw numeric
payloads, including pointer-shaped float words and NaNs, remain bits. Owner
symbol mappings may change addresses, but cannot split aliases or merge distinct
symbols. The owner still supplies an exclusively owned destination region and
valid symbol objects; moving GC and concurrent/shared memory are excluded.

The test creates 21 objects in one Worker, changes a cons CAR through a hand-built
Wasm store, captures the resulting 272 target bytes, terminates that Worker, and
restores in another Worker at 0x80000000. Actual Wasm loads check literal expected
words, sharing, cycles, distinct equal strings, a cold pool, preserved primitive
payloads and rebased external symbols. No original recipe enters the second
Worker. Twenty malformed-input cases preserve every destination byte; capture
extent and shared-memory refusals also execute. Five implementation mutants reject
missing heap/root relocation, treating a raw float as a root, premature writes and
skipped digest validation. `snapshot-verification.json` pins sources, schema,
compiled probe and toolchain. The prior encoder/linker verification stays separate.

Development failures are retained in `development/snapshot-r2` and `snapshot-r3`.
The first used payload offset 120 instead of 124 in the expected mutant diagnostic;
the mutant was already detected. The second exposed an aliased before-image in
the refusal oracle: `Buffer.from(memory.buffer)` shared the destination. A copied
Uint8Array-backed snapshot fixes the oracle, and the early-write mutant now fails
at the intended assertion. R2's unchanged runtime/test pins resolve to the retained
R3 test and current runtime files; neither failure changed the runtime behavior.

The snapshot component above uses hand-built Wasm. It is not itself generated
constant-pool execution or S1-LL10-a qualification.


## Complete S1-LL10-a qualification

`compiler.py` derives the isolated proposal from the pinned, reviewed LL05
backend. CCL's real front end supplies literal identities; the exporter preserves
those identities rather than re-reading printed source. Each function has a pool
shared by its activations. Parent pools retain child pools. The proposed 32-byte
function object appends the pool pointer at raw offset 24; logical pool slot zero
is vector offset 4. Generated loads read the current rooted SELF. Closure and
temporary-callable construction/relocation use the larger object. Constant-free
calls gain no pool lookup. Shared compiler/runtime source is unchanged.

The generated corpus has 87 B modules and one generated raw header probe. It
checks all supported scalar/vector families, signed limbs, NaN payloads, signed
zero, subnormals, infinities, supplementary characters, cycles, sharing, distinct
equal objects and owner-resolved symbols. The header probe executes the checked
raw-primitive compiler path on returned target objects. Literal byte oracles and
native CCL comparisons independently check subtags, counts and payload widths.

There are 233 native-derived comparisons across three Worker executions: the
origin at 1 MiB, then restored pools at 2 MiB and 0x80000000. The origin leaves the
cold function unexecuted and mutates a cons through generated code before capture.
Both fresh Workers receive serialized target bytes, not a builder graph, inspect
the cold pool before installation and observe the mutation. Restored expectations
compose native results with the separately tested mutation; the mutation is a
persistence probe, not a portable claim about destructively modifying CL literals.
Two closure activations have distinct environments and a shared pool. At every
placement a 100,000-step literal-APPLY tail chain uses a 2 KiB stack and 48 heap bytes.

The loader uses the new constants profile and rejects the old one. All installation
remains lazy and free of heap-writing initialization. The owner supplies the trusted
catalog and symbol registry. Snapshot transport copies an exclusively owned interval
while its sole Worker is stopped, validates/restores privately, then publishes bytes.
Six malformed restore cases preserve the entire owned region. This is not concurrent
snapshot atomicity. Moving GC, full image loading and package construction remain
later work. Pools have a 16 MiB resource bound; ratios, complex scalars and general
multidimensional arrays remain unsupported.

Four recompiled compiler mutants and seven target-image mutants fail at named
oracles. Encoder, graph and standalone snapshot controls are also rerun. The
inherited 587-module B corpus passes 7,332 comparisons, the 62-module condition
corpus 848, and the 46-module call-error corpus 288, eagerly and with lazy loading.
All 36 loader cases and 14 loader mutants pass. The source evaluator counts heap
closures independently to add eight bytes per allocated function; supplemental
literal expectations follow their source function counts. A real scope regression
found here—admitting ERROR format strings along with string constants—is explicitly
refused, preserving the condition slice's boundary.

Native R6 reuses the accepted pristine baseline, runs a fresh registered rebuild
and 21,843 tests, checks 162/164 unchanged FASLs with the two existing registration
explanations, and restores all 164 after removal. R6a and its qualifier pass.
Original failures are retained as described in `development.json`.

From the repository root, replay the retained final packet into a fresh directory:

```sh
python3 tests/wasm/stage1/constants/verify_ll10.py --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-17-stage1-ll10-r1 --output /tmp/ll10-review
```

To produce independently, run `native.py --evidence ../ccl-evidence --work DIR
--output DIR`, then `run.py --evidence ../ccl-evidence --native NATIVE_DIR --output
RUN_DIR`. All outputs must be new directories. `retain.py` creates the single final
packet, `verify_ll10.py` recompiles/replays it, and `publish.py` publishes only after
that replay. Execution is complete; review, acceptance and integration are separate.
