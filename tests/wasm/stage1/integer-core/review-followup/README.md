# Integer-service review follow-up

Audit 103 found no defect in the integer service, but its first-value-only
allocation mutant escaped the retained controls. This follow-up strengthens
the checks and clarifies the diagnostics. It changes **no service source or
binary**, compiler, loader or runtime. It neither accepts the auxiliary unit
nor claims LL16 slot credit.

The runner verifies the original packet's eleven source pins before deriving
an overlay from its harness. Every case in that packet remains, including the
636 chained operations. The freshly rebuilt service must equal the reviewed
binary (`a56d7f7ff3d5472d9a72f28ea93bc00f521d52a45b15f9b47b5cda4a29c58f59`).

- **Combined allocation.** A truncate result has a 16-byte quotient and a
  16-byte remainder. Reservations of 16 and 24 bytes refuse without changing
  inputs, the allocation region or publication. A 32-byte reservation succeeds
  exactly, publishes both values and preserves the following guard bytes.
  Replacing the combined check with a quotient-only check reproduces Claude's
  escaped result against the entire original harness, then fails the new
  16-byte case. Both executions are retained. The quotient and remainder also
  appear in the native/Python corpus, independently checking their values.
- **Large multiplication and division.** Another 128 signed and seeded-random
  cases exercise multi-hundred-digit operations. Multiplication reaches two
  512-digit inputs and a 1,024-digit result; division takes inputs up to 1,024
  digits. All expected values come from the unchanged exact Python oracle and
  agree with native CCL at the same three compiler policies. These are retained
  fixture cases, separate from Claude's additional probe.
- **Alignment.** A tag of six necessarily gives an eight-byte-aligned base.
  The old `misaligned-pointer` control is renamed `aligned-nonobject-header` in
  the overlay. Removing the redundant source test produces the identical
  binary; it is an identity check, not another rejected fault. The independent
  owner-region alignment check and its refusal still apply.
- **Input-width diagnostics.** A canonical 1,025-digit input whose magnitude
  exceeds 1,024 digits refuses with capacity status 3. A canonical 1,026-digit
  input refuses at the admitted-header-width check with status 2. Thus status
  2 includes an unadmitted width, not only malformed/noncanonical values. Two
  explicit controls pin this existing distinction; no status changes here.

Totals: 4,553 cases, 13,659 native comparisons, 9,106 target comparisons at
1 MiB and 2 GiB, 636 additional chain comparisons, 56 refusal/preservation
checks, two exact-fit checks and thirteen rejected compiled faults.

```sh
python3 tests/wasm/stage1/integer-core/review-followup/run.py \
  --evidence ../ccl-evidence --output /tmp/integer-followup-new
python3 tests/wasm/stage1/integer-core/review-followup/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-19-stage1-integer-review-r1 \
  --output /tmp/integer-followup-replay-new
```

The original service packet and its verifier remain unchanged and replayable.
The follow-up stores its source snapshots and commands, pins the original
packet and native inputs, and rebuilds every positive and mutant binary. No
new native R6 run is needed because no shared source changed.
