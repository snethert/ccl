# Startup publication and ordering review follow-up

Audit 128 found that the generated hash adapter consumes only the primary
publication word for CLR. The added direct successful call independently checks
all four words: `[table, NIL, 1, 0]`. Three compiled faults change the secondary
value, count or rehashed word only for operation 5. Each reproduces its complete
escape under R1, then fails the corrected assertion. The nine previous faults
still reject. The corrected positive execution record is byte-identical to R1.
The compiler, C service, adapter, generated modules and native answers are
unchanged and reused by pinned hashes. No native build is needed for this
harness-only correction.

The joined R1 schedule groups all thirteen resets before the five configuration
callbacks. That is fixture order, not native registry order. This follow-up
selects the same eighteen callbacks in retained snapshot order (system pointers,
then user pointers), reruns the generated schedule in Node and pinned Chromium
at both placements, and compares every reset answer, configuration answer and
final readback with the grouped run. Installed digests are unchanged; actual
entry order is checked against the selection. This establishes equivalence for
these eighteen callbacks only. Future joins must preserve registry order and
account for additional dependencies explicitly.

Original fixture directories remain unchanged and replayable. Future CLR
validation must use this corrected harness; future joined scheduling should use
the retained registry-order overlay. These overlays are proposals awaiting
review and acceptance, with no LL15 credit or shared-runtime integration.
Clearing still accepts a shape-valid table with inconsistent bucket counts and
reinitializes it; capacity is fixed, and production cache materialization is
open. Winners remains Node-only; the ordering check has R2's Chromium scope.

```
python3 tests/wasm/stage1/startup-winners-review/run.py --evidence ../ccl-evidence --output /new/review
python3 tests/wasm/stage1/startup-winners-review/packet.py verify --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-20-stage1-startup-winners-review-r1 --output /new/replay
```
