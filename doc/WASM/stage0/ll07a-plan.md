# S0-LL07-a — suggested plan of attack (Claude, advisory, 14 September 2026)

Status: advisory. Written by the reviewer for Codex, the author. Nothing here is a
contract change; the slot's assertion, evidence kind and required roles in
`inventory.json` govern. Deviate where the tree gives a better reason, and say so
in the scope report.

## 1. What the slot has to prove

- Inventory: `S0-LL07-a`, variant `full`, evidence kind HAND-BUILT WASM EXECUTION,
  no prerequisites. Assertion: "Check signed fixnum, raw address, logical-ID and
  typed-slot conversions separately. Synthetic addresses above 2 GiB retain bits
  through JS; checked exhaustion rejects invalid IDs and capacities."
- Obligation LL07 (acceptance.md): test all declared conversions and high-bit
  boundaries with synthetic address fixtures plus real allocations, negative
  header offsets and sign extension, without banning legitimate accesses;
  unchecked JavaScript signed bitwise arithmetic is never used as address
  arithmetic; bounds failures are separated from legal high-address values and
  from code-index encoding.
- D1 (layout.json v1): word 4 bytes, little-endian, object alignment 8,
  fixnum shift 2, range −2^29 … 2^29−1, fulltags even_fixnum 0, cons 1,
  nodeheader 2, imm 3, odd_fixnum 4, reserved_tra 5, misc 6, immheader 7.
  Cons: tag 1, cdr at raw +0 / tagged −1, car at raw +4 / tagged +3. A raw
  address or larger unboxed ID is never converted to a fixnum by truncation.
  wasm32 memory immediates are nonnegative, so a negative tagged displacement
  needs explicit address adjustment.
- D5: logical code IDs are checked tagged fixnums in 0 … 2^29−1 with recorded
  reservations and an explicit exhaustion failure; table capacity and slot
  index have separate checked bounds; code ID = slot is withdrawn as an ABI
  promise; a finite i32 namespace is never described as unbounded.
- Required roles: the four global roles plus source, abi, template,
  installed-binary, host-compiler, options. LL23-a is the pattern: WAT source,
  a template with substituted parameters, wat2wasm as the host compiler with
  digest and version, options recording the actual arguments, abi.json.
- Attempt-1 lessons the corpus must catch: a raw address shifted into a fixnum
  lost pointer bits above 1 GiB; typecode and cons reads used the wrong
  displacement; an entry index was shifted twice.

## 2. Four families, tested separately

Keep the families in separate case groups with separate oracles, so a defect
in one cannot be masked by another and the review can tally them independently.

### A. Signed fixnum ↔ i32

Wasm primitives: `box_checked(i32) -> (i32 result, i32 ok)` refusing any value
outside the range; `unbox(i32) -> i32` using `i32.shr_s`; `fixnump(i32)` testing
the low two bits. Cases, with expected tagged words:

| Input | Box | Note |
| --- | --- | --- |
| 0, 1, −1 | 0, 4, −4 (0xFFFFFFFC) | tags even_fixnum 0 and odd_fixnum 4 |
| 536870911 | 0x7FFFFFFC | maximum |
| −536870912 | 0x80000000 | minimum; sign bit set, still a fixnum |
| 536870912, −536870913 | refused | one past each end |
| 2147483647, −2147483648 | refused | full i32 extremes |

Unbox 0x80000000 must give −536870912. A logical shift gives 536870912, which
is the sign-extension mutant. Unbox of a non-fixnum word (tag 1, 6) must be
refused by `fixnump`, not silently shifted.

### B. Raw address ↔ tagged pointer, with real memory

Primitives: `tag(raw, tag) -> tagged`, `untag(tagged) -> raw` (mask low 3
bits), `cons_car(tagged)`, `cons_cdr(tagged)` implemented with the D1
displacements, where the cdr load adjusts the address by −1 before a
zero-offset load rather than using a negative immediate.

Synthetic values, no memory access: raw bases 0x80000000, 0xBFFFFFF8,
0xFFFFFFF0; tagged forms with tags 1 and 6; effective car/cdr addresses. These
cross the JavaScript boundary as i32 results and must be compared after
`>>> 0` normalization in the harness; the oracle expects the unsigned value.
A control that normalizes with `| 0` or compares the raw signed value must fail.

Real allocations, memory access: instantiate one memory with a small initial
size and maximum 65536 pages. Allocate and read conses at a low address, at
the last doublenode below 2 GiB, and, after growing the memory to 32769 pages,
at 0x80000000 and at the highest doublenode of the grown memory. Store unequal
car and cdr payloads and read them back through the tagged pointer with both
displacements. Growth failure fails the run; it is not a skip. If the reference
host cannot grow to 2 GiB plus one page, say so in the scope report and stop;
do not substitute a smaller memory and call the >2 GiB case covered.

Attempt-1 control: `box_checked(untag(tagged))` for a raw base ≥ 2^30 must be
refused, never truncated to a fixnum.

### C. Logical code IDs

A registry in Wasm memory: `id_alloc() -> (tagged id, ok)`, `id_reserve(lo, hi)`,
`id_valid(tagged) -> ok`. Cases: allocate 0, 1, 2 and check the tagged forms
0, 4, 8; reserve a range and check allocation skips it; set the counter to
2^29−2 and allocate twice, then observe the explicit exhaustion failure on the
third call (the counter is set directly; the corpus does not iterate 2^29
times); reject −1, 2^29 and 2^31−1 offered as IDs; the maximum tagged ID is
0x7FFFFFFC.

Attempt-1 control: tagging an already tagged ID (double shift) must be caught.
ID 5 tagged is 20; tagging 20 again gives 80, which `id_valid` on a registry
with next-ID 6 must reject as never allocated.

### D. Typed table slots

A slot registry separate from the ID registry: capacity, reserved low range
taken from the actual link map of the fixture module (the address-taken
function slots), typed entries recorded as (signature key, role). Cases:
capacity 8 admits 0 … 7 and rejects 8 and −1; capacity 0 rejects everything;
reserved slots cannot be allocated; a tagged ID offered where a slot index is
expected is rejected before any `call_indirect`; an unallocated slot is
reported as non-callable before dispatch rather than by an engine null trap;
a signature-key mismatch is refused at installation. Keep this family to
conversions and bounds. Dispatch semantics are already accepted under the
dynamic-call corpus and LL23-a; do not re-prove them here.

## 3. Fixture shape

`tests/wasm/stage0/conversions/`, following LL23-a:

- `program.wat` (source) with `@PARAM@` substitutions producing `template.wat`
  and `module.wasm`, compiled by wat2wasm with the recorded digest, version and
  arguments. Two builds with different parameters give distinct binaries
  sharing a template, as before.
- `abi.json` naming every exported primitive with its signature and the
  conversion family it belongs to.
- `execute.mjs`: instantiates, runs `cases.json`, writes `observed.json`. All
  address values leaving Wasm pass through one `u32()` helper that applies
  `>>> 0`; grep the harness for `|0`, `<<`, `>>` on address values and make sure
  none remain. Use BigInt only where an intermediate exceeds 32 bits.
- `oracle.py`: literal expectations computed in Python with explicit masks
  (`& 0xFFFFFFFF`) and explicit sign extension, independent of the harness.
  It should also decode the module's exports against `abi.json` and read the
  link map for the reserved slot range, as the diagnostics decoder did.
- `cases.json`: every case names its family, inputs, expected outputs or
  expected refusal code, and whether memory growth is required.
- `run.py --output` / `--verify`, quarantine of mutants, development archive
  with any original failures, slot gate expecting only `unreviewed`, results
  bound to the inventory, the ten role omissions refused by the production gate
  on the genuine result, publication of the packet and catalog rows, STATUS row,
  scope report `doc/WASM/stage0/conversions.md`, changes entry, plan item.
  Run `doc/WASM/tools/check-project-ledger.py` before committing.

## 4. Mutants

One-line changes, each failing the same oracle at a named first case:

1. `i32.shr_u` for unbox (sign extension).
2. Box without the range check.
3. Box by truncating a raw address.
4. Wrong cons displacement (car at +4 from the tagged pointer).
5. Negative immediate replaced by an unadjusted zero-offset load (reads the
   wrong word).
6. Harness normalizes addresses with `| 0`.
7. Harness compares a signed i32 against the unsigned expectation.
8. ID counter allowed to reach 2^29 (no exhaustion).
9. Tagging an already tagged ID accepted (double shift).
10. Slot bound uses `<=` capacity.
11. Reserved slot range ignored.
12. Tagged ID accepted as a slot index.
13. Signature key not checked at installation.

Mutations enter only the WAT generator or the one harness helper they target;
the oracle and case list are untouched. Retain each mutant's binary and
observation under quarantine.

## 5. Bounds to state in the scope report

Fixed memory of at most 2 GiB plus one page on the reference host; one Worker;
Node/V8 only; hand-built conses, not CCL objects; no allocator, collector or
production registry; D1 fixnum, cons and tag rows only, with the outstanding
layout rows (NIL/T, other subtags, symbols, numeric payloads, function objects,
TCR) explicitly not covered; no memory64. Stage 1 repeats every family through
generated code.

## 6. What the review will check

Byte-identical re-execution of both builds and every case; independent
recomputation of every expected value from the case inputs; the `>>> 0`
discipline in the harness by inspection; the four families in separate case
groups with separate mutants; every mutant a single-site change; the reserved
slot range read from the real link map, not hand-typed; growth to 2 GiB
actually performed, not simulated; the ten role omissions refused; the gate
composite and ledger checker at 38 accepted, 9 missing, 1 unreviewed.
