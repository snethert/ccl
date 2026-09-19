# Closed GO and ordinary loop branches

This isolated proposal admits closed GO using U1's existing captured catch-tag
lowering, including handlers and restart clauses. Each function still starts
with an empty backend tag map. Closure capture, moving roots, cleanup, binding
restoration and live target identity use the accepted runtime paths.

An IR proof selects ordinary Wasm branches when every GO is in statement
position beneath its own TAGBODY. IF arms and PROGN preserve that position;
operands, nested loops and pending extents do not. Those cases retain the
addressed-exit path. Eligible loops allocate no per-iteration control record
and throw no exit exception. Nine instruction-shape checks include four such
modules, and a 4,000-iteration case exercises the backedge. No timing claim.

Thirty native-first cases run at two placements with and without collection:
120 comparisons and 130 collections. The unchanged LL06 corpus adds 120
comparisons and 300 collections; 40 WAT/Wasm files without TAGBODY are identical
to accepted LL06. Seven recompiled mutants, six admission refusals and eight
publication controls run. Native R6/R6a qualifies the exact proposal.

This does **not** complete LL12-a: callable arity/keyword/debug metadata through
installation remains open. Expired-target checks are a target safety guarantee,
not a general native semantic oracle outside dynamic extent; the development
archive retains a native stack-reuse case. See [scope](scope.json).

```sh
python3 tests/wasm/stage1/closure-transfers/run.py \
  --evidence ../ccl-evidence --output /tmp/closure-transfers-new --qualify
python3 tests/wasm/stage1/closure-transfers/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-19-stage1-closure-transfers-r1 \
  --output /tmp/closure-transfers-review-new
```

The proposal is not integrated. Runtime sources and the collector are unchanged.
