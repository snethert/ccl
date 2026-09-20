# Initialization admission follow-up

Audit 122 found no defect in LL13-a but identified actual table capacity as a
post-claim failure and fresh control storage as an implicit owner precondition.
This auxiliary proposal makes both admission checks explicit. No shared source,
compiler, inventory assertion, result envelope or acceptance changes.

`derive.py` makes anchored changes to the reviewed owner. Its constructor now
requires the actual `table` and `tail_table` that the trusted callback will use;
both must be WebAssembly tables with at least the declared capacity, including
unused reserved slots. WebAssembly tables cannot shrink, so this read-only check
suffices before any subsequent claim. It does not authenticate an untrusted
callback or prevent it from choosing different tables.

Before bootstrap claims state zero, every other control word must also be zero.
Reserved words (word 1, words 10–15, and all words after the declared Worker
states) must remain zero on both ready-process and Worker entry. Live digest and
Worker states are allowed after process publication. Dirty state refuses without
callback, claim or memory writes. These checks do not reset or repair failed
state. They assume the trusted owner alone writes the control block; they are not
protection against arbitrary concurrent corruption.

A bootstrap contender may see busy state or detect control writes by the winning
initializer during its pre-claim zero scan. Both refuse without writing; waiting
and retry policy remain the scheduler's responsibility. Four three-Worker races
(two placements, bootstrap and one late-Worker id) each admit exactly one callback
and refuse two contenders. The report normalizes scheduling-dependent refusal
reasons after asserting the allowed set.

The inherited five modules, native answers and runtime dependencies are read
from the reviewed, hash-verified R1 packet. All six generated Workers execute
again and their complete results equal R1. The ten original owner mutants and
seven publication controls rerun. There is no new compiler build; native R6/R6a
and the native oracle are reused by exact identity. The harness now hands the
owner the same actual tables it installs into.

Directed checks at 4 MiB and 2 GiB cover both absent and undersized actual tables
before and after bootstrap (including length seven when all generated slots fit),
every non-state byte in fresh control storage, every reserved byte in ready
control storage, terminal failed states and acceptance of larger actual tables.
Every refusal snapshots all declared regions and verifies byte preservation.
There are 616 directed refusals, twelve racing Workers, and four additional
behavioral faults: omitted capacity, omitted tail capacity, omitted fresh-state
and omitted reserved-state validation. Mutant syntax is checked before execution.

The fixture is a **sibling** of the reviewed one. Its own source list is explicit
in `packet.py`; inherited sources use R1's frozen list. Adding a nested directory
to this fixture will not change that list. The original fixture's recursive
source enumeration is unchanged and it still replays from the current checkout.
No nested follow-up was added under it.

Run and replay from the repository root:

```sh
python3 tests/wasm/stage1/initialization-review/run.py \
  --evidence ../ccl-evidence --output /tmp/initialization-review-new
python3 tests/wasm/stage1/initialization-review/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-20-stage1-initialization-review-r1 \
  --output /tmp/initialization-review-replay-new
```

Integration, after review and user acceptance, must take the derived `owner.mjs`
from this follow-up and supply the actual Worker-local tables to its constructor.
Neither this follow-up nor R1 has been accepted or integrated. No additional slot
credit, browser, scheduler, concurrent Lisp/GC or production image claim.
