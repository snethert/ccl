# Layout schema and runtime-contract join — 15 September 2026

Status: S0-CONTRACTS-a [complete-report] EXECUTED and PASSING at its stated
scope; awaiting Codex's adversarial review under the 15 September role
switch, then the user's acceptance decision. Packet `CONTRACTS-R1` in the
evidence repository. Stage 0 is **40 accepted, two missing and six
unreviewed of 48** after the later LL15-a execution; the two missing slots are
the census's LL15-b and LL15-c.

Authorship: Claude Fable 5.1 wrote this fixture and the two generated
contracts on branch `wasm2-claude`; Codex reviews them. No shared compiler or
upstream kernel source changed: the derivation reads the pinned U1 files.

## What executes

This is a CONTROL EXECUTION: it runs no Wasm. The producer pins both U1
sources to their blobs at `c994217a`, derives the 377-row layout schema,
checks it (closed ledger, D1 fulltags and cons rows, unique subtag values,
the single known Lisp/C disagreement, the initial subset), and requires the
committed [wasm32-layout.v1.json](../contracts/wasm32-layout.v1.json) to
equal the regeneration byte for byte. It then builds the runtime-contract
join from the accepted aggregate named by the current ledger, verifying
every cited artifact's hash inside the evidence repository, re-deriving the
boundary fixture's ownership map from its retained link metadata with the
retained planner, and requiring the committed
[runtime-contracts.v1.json](../contracts/runtime-contracts.v1.json) to
equal the regeneration. The schema document
[wasm32-layout.v1.md](../contracts/wasm32-layout.v1.md) explains both.

| Assertion | What the run establishes |
| --- | --- |
| Complete versioned schema and ledger | 97 constants, 49 subtags, 8 headers, 15 objects with 196 cells in raw and tagged coordinates, 9 storage layouts, the register and kernel-import enumerations and the 154-entry subprimitive table, each with a disposition and reference; 44 constants agree with the C header and the one disagreement is named. |
| Frames, roots, TCR, allocation/store and C-boundary restoration | The written frame header equals the executed fixture header; three fixtures agree on the root record; 56 TCR field names form one consistent fixture layout with five fixture-private aliases recorded; the collector, cons-layout and conversion evidence is cited; the twelve C-boundary cases restore SP and checkpoints. |
| Link-derived memory/table ownership with executed fixtures | The retained ownership map is reproduced from the retained link metadata; 14 regions are disjoint and aligned; reserved table slots come from the element segment. |

## Findings for the reviewer

Two facts surfaced by the derivation and the join are recorded rather than
hidden. First, U1's C header spells `max_non_array_node_subtag` with the
immheader form, so it is 159 in C and 146 in Lisp; the kernel never uses the
C name, and the schema keeps the Lisp value. Second, the accepted fixtures do
not share one TCR schema: they share a prefix and reuse five extension
offsets under different names. The join tolerates aliases only across
different fixtures and refuses one inside a fixture; the production D5 TCR
schema is Stage 1 work and must assign each field once.

## Controls

Nine synthetic mutations of copies are refused with their named reasons: a
ledger entry removed, a Lisp constant changed, a C header constant changed,
the initial subset changed, a schema disposition outside the vocabulary, the
frame contract table changed, a stale artifact hash inside a copy of the
accepted aggregate (retained as a patch record, not as a second copy of the
aggregate), an ownership overlap, and a TCR alias inside one fixture. Four
production artifact-role omissions are refused; the slot gate otherwise
reports only the unreviewed contracts record and its missing prerequisite
entries in the restricted inventory.

## Evidence and reproduction

The packet holds the regenerated schema and join, the derived observations,
environment with U1 pins, the nine control records, source snapshots, the
bound envelope, slot-gate and role-omission records. The verifier regenerates
both files and compares the deterministic files byte for byte in a few
seconds. A change to either U1 source, the ledger, the frame contract, the
accepted aggregate or the committed contracts makes the producer refuse.

Limits. The schema is a source-derived contract with dispositions; it does
not execute layout probes itself, which is what S0-LL04-a and S0-LL07-a did
and what Stage 1 repeats through generated code. The join proves agreement
among the fixtures and between the fixtures and the written contracts; it
does not qualify the production TCR, D3 descriptor, collector or image
formats.


Project acceptance recorded 16 September 2026 after Codex review `81345b28`
and the user's conditional approval. See [acceptance scope](project-acceptance.md).
Original execution envelopes remain unchanged.
