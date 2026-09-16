# Production TCR schema — 15 September 2026

Status: diagnostic EXECUTED and PASSING at its stated scope in `TCR-SCHEMA-R3`,
which adds the `fp_control` word under the D6 floating-point policy the
user decided on 16 September (the ARM model keeps the logical enable mask in
the TCR); `TCR-SCHEMA-R2`, reviewed without defect, and `TCR-SCHEMA-R1` are
retained. Awaiting Codex's review. No inventory slot and no gate credit.

Authorship: Claude Fable 5.1 wrote the schema source, the checker and the
generated [contract](../contracts/tcr.v1.md) on branch `wasm2-claude`;
Codex reviews them. No shared compiler or upstream kernel source changed.
The schema consumes the committed layout schema and runtime-contract join
and the decided D5 text; it depends on nothing in the census.

## What executes

A control execution over the committed contracts. The schema source names 48
fields in D5's nine groups with offsets, widths, alignments, classification,
owner, update rule and native origin, a mapping from every replaced or
deferred native TCR cell to production fields, and a mapping from every
fixture TCR field to a production field or a fixture-private reason. The
builder joins the three, the checker requires the record to be well formed
(no overlaps, alignment satisfied, atomic fields aligned, the reserved tail
intact, every group present and every field in exactly one group, tagged
roots limited to the declared slot, every fixture witness carrying its
tests), and the committed contract must equal the regeneration.

| Fact | Value |
| --- | --- |
| Fields | 48 in 9 groups: 26 raw addresses, 16 bounded, 3 atomic, 2 raw scalars, 1 tagged root |
| Native cells | 41 mapped, 2 deferred, 18 unsupported and unmapped |
| Fixture fields | 56: 25 mapped, 31 fixture-private |
| Fields with an executed witness | 22 |
| Fields without a native origin | 14, each explained |

## Controls

Eight refusals of mutated copies: overlapping fields, a misaligned atomic
field, a classification outside the vocabulary, a replaced native cell left
unmapped, a native mapping to a nonexistent field, a fixture field left
unmapped, a D5 group dropped, and a second tagged root introduced outside
the declared slot.

## Evidence and reproduction

The packet holds the regenerated schema, observations, the eight control
records and source snapshots; the verifier regenerates the schema and
compares the deterministic files byte for byte in under a second. A change
to the schema source, the layout schema, the join or the committed contract
makes the producer refuse.

Limits. This is the build target D5 owes, not executed proof; Stage 1 runs
it through generated code. Request descriptors keep their own contract. The
allocation statistics stay deferred, and `next_method_context` waits for
Stage 1 CLOS dispatch.
