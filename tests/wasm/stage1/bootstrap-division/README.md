# Exact integer division through the accepted arithmetic service

186 original definitions remain executed; admission is unchanged. This packet extends the division witness to integers on the user's instruction, without claiming another original definition or LL15 completion. It builds on execution R2, whose retained verifier passed before commit 7ef90b2a.

For bootstrap compilation, DIV2 and a two-argument `/` call dispatch integer operands to the accepted `$integer` quotient/remainder helper. Exact quotients return one value. Fixnum results use that helper's Wasm fast path; bignum results use the existing collecting owner capability. No arithmetic implementation, C service or JavaScript service is duplicated. A nonzero remainder refuses with checked code 45: ratio-result arithmetic remains unimplemented, so `/ 1 2` must not silently return zero.

The ordinary real-number checks and operand evaluation order are unchanged. Both operands are already rooted before classification. A zero integer divisor signals DIVISION-BY-ZERO with `/` as the operation and the original operands. The owner requires a two-slot root frame at the chain head, so the operands are staged there while the enclosing frame retains the original values. The integer helper may move objects; publication reloads the quotient from its updated root and discards the remainder. Mixed integer/float and floating division retain the accepted path. The change is gated by the bootstrap entry; legacy numeric compilation retains its previous behavior.

Witnesses cover `/ 6 3`, zero numerators, all sign combinations, the minimum fixnum divided by -1, bignum/fixnum and bignum/bignum exact quotients, mixed floats, and CCL's unchanged `%QUO-1` on integer 1 and -1. Another generated form checks left-to-right effects, collection in the divisor, and both live input operands after division. A handler/cleanup form compares integer division by zero and invalid operands with native. Direct refusal checks cover nonintegral integer quotients and restoration. Fast-path counters check that eligible fixnum division calls neither JavaScript numeric service.

The error witnesses also exposed a pre-existing bootstrap dispatch defect: native HANDLER-BIND expansions store quoted class symbols, while the older signal loop shifted those pointers as if they were fixnum masks. Bootstrap dispatch now resolves each admitted class symbol by identity to the existing class mask; legacy mask entries still work. Restart/type/operation imports also use the bootstrap symbol owner, preserving their identity with literal symbols. Unknown handler types refuse rather than being treated as pointer bits. The scope remains the existing sealed condition classes, not general TYPEP.

R2's 186-definition execution corpus, moving collection, six focused controls and legacy byte checks are inherited. New directed faults cover exact integer dispatch, the remainder refusal and treating a handler symbol as a numeric mask. Compiler changes receive a fresh native R6/R6a build; native tests and source-reader evidence are reused only under the existing exact-equality checks. This proposal remains unintegrated and subject to Claude's review.

```sh
python3 tests/wasm/stage1/bootstrap-division/packet.py verify \
  --packet ../ccl-evidence/2026-09-21-stage1-bootstrap-division-r1 \
  --output /tmp/bootstrap-division-review
```
