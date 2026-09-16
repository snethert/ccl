# Generated rest lists and APPLY — 16 September 2026

The next LL05 proposal implements rest-list construction and APPLY over
CCL's real front-end IR. The accepted optional/keyword unit stays integrated;
this extension is developed and qualified in disposable pristine U1 copies.
No complete LL05 slot is claimed.

Rest arguments become D1 conses in the TCR's owned allocation area. Capacity
and alignment checks precede writes; every cell is initialized before the
allocation pointer and bound root are published. A later exception does not
rewind allocation or invalidate escaped cells. Empty rest lists allocate
nothing. This is a checked bump allocator with no collector or slow path.

APPLY evaluates operands once in order, validates tags, memory bounds and
proper-list structure with cycle detection, then constructs a runtime-sized
argument frame and dispatches through the checked B table entry. Root and
result ownership are restored on ordinary and exceptional returns.

The fixed 64-argument ceiling is removed, without adopting a new language
limit. Counts and byte extents use i64 before narrowing; capacity follows the
supplied stack and heap. Tests reach 1,024 arguments and 129 required
parameters. The source reader's budget and the separate 64-value result
limit remain explicit implementation bounds.

Seventy-one generated functions run 339 native/logical cases, repeated as
1,356 target comparisons with low and above-2-GiB stacks and allocation
areas. The oracle checks every value and reachable cell identity, allocation
counts, untouched heap tails and physical root ownership. Eighteen compiled
mutants, twenty source refusals, sixty resource refusals and eight allocation
boundary checks exercise the failure paths. Circular-list controls execute
only in Wasm. R6/R6a passes with 21,843 native tests and all 164 FASLs restored.

The user accepted this unit after Claude’s sixty-seventh audit found no defect.
The exact reviewed backend is [integrated](integration-b-rest-apply.json).
The direct-link APPLY branch remains unexercised; validation followed by
unchecked copying depends on no intervening execution. Revisit that invariant
before introducing safepoints or concurrent list mutation. Function and keyword identities are
still fixture-owned; collection, dynamic result capacity, production callable
objects, full conditions, lazy adapters and tail transfers remain LL05/Stage 1
work. The next unit addresses result capacity and callable objects.

[Source and replay commands](../../../tests/wasm/stage1/b-rest-apply/README.md).
Packet: `ccl-evidence/2026-09-16-stage1-b-rest-apply-r1`.
