# Direct argument placement and internal calls — 16 September 2026

The user directed this optimization now: eliminate avoidable argument copying
and wrapper overhead on compiled-to-compiled calls. The
[isolated compiler proposal](../../../tests/wasm/stage1/b-direct-context/README.md)
does both. It preserves B and the public entry while using the existing internal
body for ordinary compiled calls. The shared backend remains the accepted tail
unit until external review and acceptance.

The caller reserves results below a continuation, then evaluates arguments
directly into that continuation's final root slots. The callee uses those slots
in place. The surviving caller's Wasm locals retain its restoration state;
there is no intervening public wrapper activation. Tail transfers continue to
reuse the context. APPLY still stages its prefix while discovering the list
length, then copies the prefix once and spreads the list into the final slots.
Its previous second whole-vector copy is gone.

For an ordinary call, this removes `16 + align16(4*N)` bytes of explicit-stack
storage, one argument root frame and one Wasm wrapper activation. Public host
calls retain their wrapper and argument copy. Scratch/results, assigned bindings,
capture cells and genuine APPLY staging remain. These are layout and execution
properties, with no timing or speed-ratio claim.

The corpus now has 206 source functions, 276 generated modules, 761 native/model
cases and 3,044 target comparisons. Every public table entry is guarded to fail
if a compiled call enters it; all comparisons pass with zero such entries.
Thirty-six 100,000-step tail chains still fit 2 KiB. Peak observed root depth is
50, compared with 66 in the preceding packet. Added ordinary APPLY cases cover
prefix effects, long prefixes/list spreads, heap closures, temporary literal
callables and errors. The same generated binaries also pass through the unchanged
pending lazy-loader proposal, with the semantic observations and long chains
matching the eager run.

Twenty compiler mutants and the two inherited development regression controls
reject. Fresh registered execution and R6/R6a pass: 162 unchanged FASLs, two
explained registration artifacts, all 164 restored, and 21,843 native tests.
The accepted pristine baseline is reused. The final packet is replayed before
commit.

Two development controls initially escaped. The missing APPLY prefix revealed
that the old non-tail cases had no prefix; the new cases catch that same mutant.
A wrong MV-owner restoration between calls was not observable before subsequent
entry repaired it; its complete build and passing output remain as an unqualified
control, outside the twenty rejections. Actual post-call safepoint inspection
remains an explicit collector/poll obligation. The correct restoration stores
remain in the proposal, and no collection is claimed here.

This is auxiliary LL05 work awaiting review, with no inventory slot claimed.
Production Lisp conditions, dynamic binding/cleanup extent and collection remain
open. The next implementation work returns to the condition path.

Packet: `ccl-evidence/2026-09-16-stage1-b-direct-context-r1`.
