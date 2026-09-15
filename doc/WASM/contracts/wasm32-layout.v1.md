# wasm32 layout schema v1 and source-to-target ledger

Status: generated deliverable of S0-CONTRACTS-a, executed by Claude on 15
September 2026 and awaiting Codex's review and the user's acceptance. The
machine-readable schema is [wasm32-layout.v1.json](wasm32-layout.v1.json);
the runtime-contract join is
[runtime-contracts.v1.json](runtime-contracts.v1.json). Both are regenerated
and compared byte for byte by
`python3 tests/wasm/stage0/contracts/run.py --output DIR`; edit the sources
and the disposition ledger, never these files, and regenerate with
`--generate`.

## Derivation

Every row is derived from the pinned U1 source
`compiler/X86/X8632/x8632-arch.lisp` by a small reader for the forms that
file uses: `defconstant`, `ccl::defenum`, `define-subtag` and its
immediate/node wrappers, `define-storage-layout`, `define-lisp-object`,
`define-fixedsized-object` and `define-header`, with integer arithmetic over
earlier constants and the x8632 non-Windows feature set. The producer refuses
to run unless both source files equal their U1 blobs. The C header
`lisp-kernel/x86-constants32.h` is evaluated for the same names: 44 integer
constants agree and exactly one differs, `max-non-array-node-subtag`, whose
C macro reuses the immheader form (159) while the Lisp definition is 146. The
kernel sources never use the C name; the Lisp value governs the schema and
the disagreement is recorded so any new one fails the check.

Each object cell is recorded in both coordinates: `raw_offset` from the
object base and `tagged_displacement` from the tagged pointer, with its
representation (tagged, raw, header, native) and GC treatment (root, none).
A negative displacement needs explicit address adjustment on wasm32; a
positive one can use the memory instruction offset. The initial
`contracts/layout.json` subset (fixnums, tags, cons) is compared against the
derived rows and must agree.

## Ledger

The disposition ledger `tests/wasm/stage0/contracts/dispositions.json` gives
every derived row one of five dispositions and a reference: inherited (D1
adopts the value or layout), replaced (target-specific replacement,
referenced to the decision or contract), unsupported (native-only mechanism),
deferred (later stage or decision, referenced) or reserved. Building the
schema fails on any row without an entry, so the ledger is closed.

| Group | Rows | Inherited | Replaced | Unsupported | Deferred | Reserved |
| --- | --- | --- | --- | --- | --- | --- |
| Constants | 97 | 84 | 3 | 5 | 4 | 1 |
| Subtags | 49 | 41 | 5 | 1 | 2 | 0 |
| Headers | 8 | 8 | 0 | 0 | 0 | 0 |
| Objects | 15 | 13 | 2 | 0 | 0 | 0 |
| Object and layout cells | 196 | 61 | 80 | 49 | 6 | 0 |
| Storage layouts | 9 | 0 | 8 | 1 | 0 | 0 |
| Enumerations (registers, kernel imports) | 2 | 0 | 0 | 1 | 1 | 0 |
| Subprimitive table | 1 | 0 | 1 | 0 | 0 | 0 |

Notable rows: `fulltag-tra` is reserved, never repurposed silently; the
native TCR's 61 cells are all replaced, unsupported or deferred, none
inherited; catch frames and every native stack frame layout are replaced by
the logical frame contract and the B frame records; areas become owned
regions with link-derived ownership and their generational bookkeeping is
unsupported for the initial collector; the 65 kernel imports are the D6
census worklist; the 154 subprimitives are replaced by emitted code under D4;
canonical NIL and T keep their U1 addresses as provisional schema rows.

## Runtime-contract join

The join reads the accepted aggregate named by the current ledger and cites
each fixture artifact by path and hash inside the evidence repository:

- Frames: the header table in [debug-frames.md](debug-frames.md) equals the
  executed S0-LL23-b fixture header, and the B corpus uses the same 64-byte
  header.
- Roots: the boundary, integrated-runtime and frame fixtures agree on the
  record shape (previous at 0, count at 4, tagged slots from 8).
- TCR: 56 field names across four accepted fixtures form one 256-byte fixture
  layout. The common prefix (root_head 24 through mv_owner_top 52) is shared;
  five extension offsets are reused under fixture-private names by different
  fixtures and are listed as aliases. The production D5 TCR must assign every
  field once; that assignment is Stage 1 work.
- Allocation and store: the bounded cons-only copying collector with its
  D5 states and pending bits, the independent cons-layout case, and the
  checked conversion families.
- C boundary: the boundary contract's restoration rule, result ownership,
  restarts and unsupported list, joined to the twelve retained cases whose
  C stack pointer and checkpoints are restored, and the concurrent C-call
  observations.
- Ownership: the retained ownership map is re-derived from the retained
  link metadata with the retained planner and must be identical; its 14
  regions are checked disjoint and aligned, with the two reserved table
  slots from the element segment.
