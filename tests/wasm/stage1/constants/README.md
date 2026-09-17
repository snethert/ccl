# LL10 constant encoder — first component

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
No shared compiler or kernel changed and no native/Wasm comparison is claimed.
Pool graphs, identity/cycle linking, relocation, IR extraction, generated pool
loads and target round-trip remain the next parts of the saved LL10 plan. Keep
this component in that eventual final packet rather than creating a separate
acceptance or archive for it.

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
compiler IR extraction and generated pool loads remain open. The public B ABI
and all shared compiler/runtime files remain unchanged.

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

This completes snapshot transport for the isolated graph representation. It is
not generated constant-pool execution or S1-LL10-a qualification. Front-end IR
extraction, function layout/pool loads, generated closure/tail composition and
native R6/R6a remain before the final LL10 packet and review.
