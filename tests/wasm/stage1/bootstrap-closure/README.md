# Closure execution and unsigned masks

**436 original definitions execute (+13); 407 have non-NIL witnesses (+13).**
This isolated proposal follows the accepted math R2 integration. It fixes
immediate-bignum masks and supplies the source-emitted MINUS1 witness. It does
not claim completion of LL15 or the file-provider work.

The compiler's unsigned-word proof now accepts an immediate integer only when
it is in `(unsigned-byte 32)`. LOGAND, LOGIOR and LOGXOR still call the existing
checked unbox/word/box path. Values below zero and above 2^32-1 receive no new
proof. The positive matrix includes the target fixnum limit, both bignum
encodings and 2^32-1, with a literal in either operand position. MINUS1 is
emitted by CCL's own `%NEGATE`, exercised on fixnums, a bignum, both float widths
and signed zero. No additional arithmetic service or source rewriter is added.

Thirteen original double-float primitive definitions execute directly against
the compiled entries in the pinned native image, preserving their file-local
stack-float macro environment. These recipes use exact mathematical identities;
the inherited 504 approximate libm comparisons remain separately counted.
The oracle copies double-float arguments with native `%COPY-FLOAT`, retaining
identity in the copy map, so the native destination cannot rewrite the input
snapshot. Every destination starts at 17 or 19 and must change. A missing
64-bit destination store is rejected against those before/after observations.
The single-float destructive entries are not credited by pretending their
32-bit interface exists in the 64-bit native image.

Two compiler controls restore the old immediate proof and make MINUS1 return
its operand. The generated mutants are executed against the native rows.
Inherited arithmetic, two-ULP libm, exact-identity, root-movement and trap-mode
checks also run. Runtime and CCL source remain byte-identical to the accepted
integration. Native R6/R6a for the new backend passes 21,843 tests; all existing
source changes retain their accepted source-location allowance.

```sh
python3 tests/wasm/stage1/bootstrap-closure/packet.py verify \
  --packet ../ccl-evidence/2026-09-21-stage1-bootstrap-closure-r1 \
  --output /tmp/bootstrap-closure-replay
```

The verifier recompiles the cases and controls from the committed fixture,
uses the production float build helper, and checks every deterministic result.
Native qualification is reused only when its final compiler/source hashes
match. Original development failures are retained.

Remaining work includes the other closed recipes, file-namespace providers,
condition classes, heap constants, kernel-global access, lexpr spreading and
the end-to-end initializer/READY join. The existing uint32 stores still accept
only fixnum values; wide random-generator state mutation is not claimed.
