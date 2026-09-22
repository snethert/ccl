# Bootstrap lexpr spreading

Original CCL execution stays **486 definitions, 451 with a non-NIL witness**. Admission rises **2,051 → 2,059 of 2,231**. All eight `B-SPREAD-KIND` refusals disappear. The new execution witnesses are callers, not original-library execution credit.

This unintegrated compiler proposal stacks on the condition-frontier and introspection proposals. There are no new runtime, C or JS services, no CCL source changes, and no LL15 or method-dispatch credit.

## Implementation

CCL's front end already represents `%APPLY-LEXPR` as spread kind 0. The bootstrap entry now lowers it through the existing APPLY emitter. Ordinary list APPLY and legacy entries keep their old behavior. The ten retained legacy outputs remain byte-identical.

The accepted lexpr binding emitter stores a tagged argument count followed by reversed arguments in a retained root frame. The new path locates that frame on the active root chain, checks its extent and exact count, and copies the arguments in source order into the existing APPLY destination. It builds no intermediate list. Both tail and internal calls reuse existing callee resolution, stack reservation, root publication, multiple-value handling and unwind restoration.

The callee, prefix operands and lexpr expression are evaluated once, in that order. The evaluation frame keeps their values rooted. The source lexpr remains rooted until the destination roots hold every argument. No allocating call occurs during copying. As with existing frame reservations, a soft stack-limit signal does not resume the interrupted reservation.

Admission is the existing trusted stack/root contract, not an unforgeable lexpr type. A pointer must name the first payload word of an active, correctly bounded frame whose first word agrees with its root count. A different valid root frame with that same shape is indistinguishable. Lisp code cannot infer that an arbitrary fixnum is a valid lexpr.

## Execution and controls

Seven generated callers cover zero, one, five and seven arguments, prefix arguments, collecting operand evaluation, a computed callee, local functions, multiple values, repeated spread calls and a THROW crossing an UNWIND-PROTECT cleanup. All seven must appear in the native comparison record. The 25 native rows pass 100 target comparisons; the full corpus passes 17,760. The normal harness runs at low and above-2-GiB heap placements before and after collection, with full caller TCR restoration checks.

`lexpr-check.py` extracts the validator from an emitted module rather than rewriting it in a test. Thirty checks exercise real frames and malformed pointers at both placements. Every refusal must be the checked code 5, never a Wasm trap, and must preserve memory. Three executable faults reverse argument order in the tail or internal path, or omit a prefix copy. Each must fail its selected native comparison.

The independent validation clauses and observations are:

| Clause | Directed case or equivalence |
| --- | --- |
| Nonzero frame | Null chain; additionally implied by the admitted positive stack base |
| Word alignment | A complete, otherwise valid frame at an unaligned address |
| Stack lower bound | A valid requested frame below the declared stack base |
| Header below the preceding frame/top | Header beyond top; cyclic link also fails this monotone bound |
| Full payload below the preceding frame/top | Payload beyond next frame; maximum unsigned count uses widened arithmetic |
| Requested pointer equals payload start | Unknown pointer and unbacked pointer exhaust the chain without dereference |
| Tagged count | Non-fixnum count whose shifted value would otherwise match |
| Nonnegative count | Negative count; under the admitted stack extent, a matching negative tagged count also cannot fit the frame |
| Count equals frame payload count minus one | Count mismatch; empty, three and seven argument exact matches |

The eight newly admitted original modules are assembled and named in `spread-admission.json`. Their remaining dependencies are retained in the frontier report. In particular, `%APPLY-LEXPR`'s generic entry also calls list utilities; this packet does not claim to execute that entry or the generic-function dcode bodies.

## Replay

```
python3 tests/wasm/stage1/bootstrap-lexpr-spread/packet.py verify \
  --packet ../ccl-evidence/2026-09-22-stage1-bootstrap-lexpr-spread-r1 \
  --output /tmp/lexpr-spread-review
```

Native R6/R6a passes 21,843 tests, with 140/164 byte-identical FASLs and all 164 restored. The packet binds that run to the final backend. Unchanged source-branch reader proofs and runtime sources retain their existing contracts. The inherited condition fault record is reused by its retained hash. Only changed fault modules and focused logs are retained; the temporary corpus symlinks are excluded from deterministic artifacts.

Still open: method-context calls and dispatch, the remaining numeric/CLOS dependency closure, condition classes outside the bounded registry, owner-backed kernel globals and heap constants.
