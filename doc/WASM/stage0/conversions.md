# Typed conversions — 14 September 2026

Status: S0-LL07-a/full executed; reviewed by Claude's forty-fourth audit at
`1c1022a3` without defect; awaiting project acceptance. The [fixture](../../../tests/wasm/stage0/conversions/README.md) has
two hand-built Wasm variants, each executing 136 cases: 83 successful operations
and 53 expected refusals. All nineteen conversion mutants and ten omissions of
required artifact roles reject. The retained verifier reproduces 214
deterministic files byte for byte, including both ordinary binaries and all
nineteen quarantined binaries. No native rebuild or shared-source edit occurs.

| Family | Cases per variant | Concrete observation |
| --- | ---: | --- |
| Signed fixnums | 18 | Inclusive signed 30-bit payload bounds; both fixnum tags; arithmetic right shift; non-fixnum refusal; JavaScript integer/range checks before entering Wasm. |
| Raw addresses and tagged pointers | 65 | Unsigned bit preservation through JavaScript, including synthetic addresses up to 0xfffffff6; checked tag/displacement conversions; raw-to-fixnum refusal; real cons/header accesses and memory growth. |
| Logical code IDs | 25 | Distinct encoding and issued-ID validation; reserved interval skipped; double-tagged word refused as unissued; last two IDs admitted and repeated exhaustion refused; invalid ranges rejected. |
| Typed table slots | 28 | Separate capacity and reservations, installation signature/role checks, explicit handle kind, uninstalled-call refusal, finite allocation and actual indirect calls. |

## Real memory and independent observations

Both variants grow real WebAssembly memory from 65,536 to 2,147,549,184 bytes
(2 GiB plus one page). Checked placements put unequal cons words at 0x1000,
0x7ffffff8, 0x80000000 and 0x8000fff8, the last aligned eight-byte region in
the grown memory. Reads use CDR at tagged pointer minus one and CAR at plus
three. Separate header-word placements exercise a misc-tagged pointer minus
six, with real loads below and above 2 GiB. These are scalar layout witnesses,
not complete CCL misc objects. Low-memory contents survive growth, old views
are detached and subsequent observations use refreshed views.

The allocation is real linear memory with checked object placement; the fixture
has no production object allocator and does not populate a 2 GiB live heap.
Synthetic near-4-GiB pointers are converted without dereferencing them. Real
out-of-region accesses, negative-displacement underflow and effective-address
overflow are refused separately. Range calculations use widened unsigned
addresses and signed displacements, avoiding wasm32 wraparound.

The oracle checks literal expectations against separate Python integer/set
models and raw little-endian bytes, then checks the observed engine and host
values. Wrong CAR/CDR/header displacements, unsigned fixnum unboxing, signed
JavaScript address normalization, raw-address boxing and unchecked input
coercion each fail at a named case. Slot and ID controls separately cover
double tagging, exhaustion, unissued IDs, capacity, reservation, kind,
signature, role and dispatch before installation. A wrapped span calculation
and an uninstalled dispatch produce engine traps in their mutant builds;
the ordinary paths must return their declared refusal codes before a trap.

## Registry bounds and advisory-plan choices

The [reviewer's advisory plan](ll07a-plan.md) supplied the four-family structure
and high-memory cases. The binary itself supplies this fixture's two reserved
table slots: its active element segment assigns functions 0 and 1 to slots
0 and 1. The bounded decoder derives that map and checks structural signatures;
the installer receives the resulting reserved prefix. There is no C module,
C link map or claim about production C function-pointer reservations. Dynamic
entries use the separate declaratively referenced function and a checked
signature/role pair. Capacities are bounded by the actual eight-entry table.

An ID and a slot can have identical bits. Kind is explicit metadata, not a
heuristic: slot 4 successfully calls an installed entry, while a logical-ID
handle carrying the same integer 4 is refused before dispatch. The caller can
mislabel data; this fixture verifies declared-domain enforcement, not origin
detection. Encoding a raw numeric ID does not assert that it was issued;
`id_valid` checks issuance independently. The counter is initialized near the
last ID for boundary testing, with no scalability claim.

Instead of allocating a four-GiB maximum, memory has an explicit 32,769-page
maximum matching the exercised bound. Unsupported growth fails the run; there
is no smaller-memory fallback or skip. The packet retains one corpus with
nineteen implementation/bridge mutants, including the suggested cases and
additional header, role, uninstalled-call and host-input checks. No ABI timing
or unrelated runtime prerequisite is rerun.

## Evidence and remaining scope

The packet is `2026-09-14-conversions-r1` in the [evidence repository](../evidence/repository.json).
Exact source and tool identities are in `run.json`, `source/` and each build's
manifest; the execution envelope uses the unchanged per-test binding producer.
The first producer attempt passed. A second successful run finalized inventory
status and changed only the verifier's failure-retention behavior; the first
run record, original runner and log are retained in development provenance.
No conversion defect was fixed between those attempts.

The slot result has only its unreviewed reason. Registration changes only
LL07-a's runner and operational status; all 38 accepted records keep their
bindings. The composed ledger is **38 accepted, nine missing and one unreviewed
out of 48**, still BLOCKED. It reuses the accepted aggregate and verifies this
new result, without rescanning historical runtime payloads.

Bounds: macOS Node/V8, one mutator, wasm32 scalar operations, one sparse memory
and eight table entries. This does not qualify browser behavior, multiple
Workers, memory64, moving GC, a production registry or allocator, or generated
B code. Canonical NIL/T behavior, complete headers/subtags, symbols, numeric
objects, function objects, TCR layouts, header-count allocation limits and the
full cross-dump/GC schema remain outside this slot. Stage 1 repeats conversions
through generated code. The next scheduled deliverable returns to the startup
boundary replacements and broader source traversal.
