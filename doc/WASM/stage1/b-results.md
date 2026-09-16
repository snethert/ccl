# Generated runtime result capacity — 16 September 2026

The next LL05 proposal removes the fixed 64-value ceiling. The caller's
reserved result region supplies a runtime resource budget for scratch
storage and nested call outputs. Bound variables follow that scratch region,
and MULTIPLE-VALUE-PROG1 retains exactly its actual result count. Extents use
i64 before narrowing; insufficient stack or output capacity is a checked
refusal with ownership restored and no result publication.

This preserves the accepted B signature and ownership rules. It does not
supply automatic growth: reservation size and call depth determine storage
cost, and an intermediate result can exhaust its budget even when a later
expression would discard it. Production adapters still need a reservation
policy. The minimum four scratch words permit scalar evaluation when the
final reservation is empty.

Ninety-five generated functions run 401 native/logical cases and 1,604 target
comparisons. Tests return up to 1,024 values and exercise direct calls, APPLY,
nested retention, defaults, aliased heap objects, effects and exceptions.
Sixteen recompiled compiler mutants, 19 source refusals, the inherited 60
resource refusals/eight allocation checks, and 36 result-capacity checks cover
failure boundaries. Both low and above-2-GiB placements execute. R6/R6a passes
with 21,843 native tests and all 164 FASLs restored.

One development control initially escaped: a one-word scratch displacement
was harmless to the existing cases. The first additional case still left
spare result words. An exact-capacity case now observes the overwritten
optional binding and rejects it. Both escaping runs are retained; the
proposed compiler needed no correction.

The unit awaits Claude's review. The shared backend stays at the accepted
rest/APPLY payload, and no LL05 slot is claimed. Callable objects and symbol
function cells are next, followed by conditions, lazy adapters and tails.
There is no collection or safepoint claim; APPLY still requires no
intervening execution or concurrent mutation between its two traversals.

[Sources and replay commands](../../../tests/wasm/stage1/b-results/README.md).
Packet: `ccl-evidence/2026-09-16-stage1-b-results-r1`.
