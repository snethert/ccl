# S1-LL10-a: generated constant pools

Implementation plan saved 17 September 2026 at the user's request. The user
selected a shared constant-pool vector. This plan does not execute or accept
LL10, and does not change its inventory criterion.

## Summary

Deliver one complete LL10 qualification unit: constants pass through CCL's real
front end and Wasm emitter, preserve their target representation and identity,
and survive serialization into a fresh Worker—including constants of functions
never executed.

Use the selected shared-pool layout. Develop in disposable U1 copies from the
reviewed LL05 implementation; keep this proposal isolated until its own review
and acceptance.

## Representation and compiler changes

- Add a versioned Wasm function-layout schema alongside the existing D1 schema.
  Preserve the five existing fields and append a tagged pool pointer at raw
  offset 24. The function object becomes 32 aligned bytes, with six payload
  words and padding. Use NIL for an empty pool.
- Define logical constant index zero as element zero of a D1 simple-vector:
  raw vector offset `4 + 4*i`. Do not inherit ARM's or x8632's native
  function-index adjustments.
- Collect constants from actual front-end IR across the complete function tree,
  including uncalled inner functions. Preserve object identity with an
  identity-based graph; support shared references and cycles without merging
  distinct equal objects.
- Give each compiled function a pool shared by its closure activations. Parent
  pools retain references to inner-function pools, so closure construction
  copies one pool pointer rather than pool contents.
- Emit constant loads through the function's rooted SELF and pool pointer.
  Embed no heap addresses in Wasm code or immutable JavaScript globals.
  Constant-free execution gains no pool lookup.
- Add a form-based compiler core for literal objects that cannot safely
  round-trip through printed source, particularly NaN payloads. Preserve the
  existing text entry point as a wrapper and keep its `*read-eval*` refusal.
- Update all function constructors, validators, stack-temporary callables and
  tail relocation from the layout schema. Public and internal B signatures
  remain unchanged; use a new loader profile to reject incompatible layouts.

## Encoding, installation and round-trip

- Implement a reusable target constant encoder driven by
  `wasm32-layout.v1.json` and pinned U1 representation rules. Classify integers
  by the target fixnum range and construct signed 32-bit bignum limbs
  independently of host word size.
- Cover fixnums, bignums, characters, single/double floats, conses, general
  vectors, strings, and D1 simple specialized vectors: bits, signed/unsigned
  integer widths, fixnum vectors, and real/complex float vectors.
- Preserve floating-point payloads as raw bits. Store string elements as D1
  character codes, including supplementary characters—not tagged characters
  or UTF-8 bytes.
- Produce a versioned object graph, target byte payload and relocation/root
  metadata. Use exact integer or hexadecimal encodings for payloads; never
  round wide integers or floats through JSON numbers.
- Allocate objects before resolving references to preserve cycles and sharing.
  Canonical symbol references resolve through the existing owner registry;
  unsupported objects and unresolved references fail explicitly.
- Validate schema, hashes, counts, references, alignment and complete memory
  extents before publishing pools or callable entries. Keep executable module
  installation free of heap-writing initialization.
- Serialize the materialized target constant graph, then restore it at a
  different address in a fresh Worker without builder caches. Preserve pools
  for cold functions before installing or invoking their code.

## Qualification

- Use independently specified golden bytes and identity relationships, native
  CCL comparisons, and generated target probes. Writer/reader agreement alone
  is insufficient.
- Exercise integer boundaries and sign limbs; floating signed zeros,
  subnormals, infinities and NaN payloads; empty and odd-length vectors;
  element widths and alignment; supplementary characters; shared,
  distinct-equal and cyclic objects.
- Test pools shared across closure activations with distinct captured
  environments, constants returned through B calls and multiple values, lazy
  installation, and stack-temporary callable relocation through long tail
  chains.
- Round-trip unexecuted-function pools and inspect them before first
  invocation. Test valid placements below and above 2 GiB, plus overflowing
  extents and invalid pool indices.
- Reject targeted mutants for host-width classification, wrong
  subtag/width/index base, lost sharing, accidental merging, tagged string
  elements, altered float bits, omitted cold-function pools and stale absolute
  pointers.
- Re-run the existing generated B corpus, loader controls and required native
  R6/R6a. Update allocation expectations independently for the larger
  function object.

## Delivery and boundaries

Publish one final LL10 packet, its retained failures, replay command and
requirement-to-evidence mapping. Register only S1-LL10-a; preserve prior result
objects and acceptance criteria.

This implements constant representation and persistence, not general array
operations, numeric arithmetic, package construction, moving GC or the complete
image loader. The encoder and relocation interface are reusable by the later
cross-loader. Shared-source integration follows Claude's review and the user's
acceptance.

## Implementation progress — 17 September 2026

The [pointer-free constant encoder](../../../tests/wasm/stage1/constants/README.md)
is implemented in isolation with independent literal byte checks and five rejected
semantic mutants. It covers target-width integers, scalar float bits, characters,
strings and D1 specialized vectors. Shared-pool graphs, compiler integration and
target round-trip are next; LL10 remains NOT_RUN. This bounded first commit follows
the user’s request to conserve the remaining weekly token allowance.

The identity graph linker now allocates every declared pool/object before linking,
preserving sharing, distinct equal objects, cycles and cold pools. Immutable plans
materialize at different wasm32 bases with separate pointer/root fixups and fixed
external owner symbols. Six test groups and six semantic mutants pass. No Worker
execution or materialized-target serialization is claimed yet; those and the
compiler integration remain open. Shared source and the LL10 criterion are unchanged.

Materialized-memory snapshot transport now restores the isolated graph in a fresh
Node Worker at 0x80000000. A hand-built Wasm mutation before capture survives the
round-trip; twenty malformed-input controls preserve destination memory and five
implementation mutants are rejected. This is supporting transport evidence, not
compiler-generated constants. The remaining implementation is front-end IR
extraction, function layout and pool loads, then generated composition and R6/R6a
qualification. Shared source, accepted records and LL10 NOT_RUN remain unchanged.
