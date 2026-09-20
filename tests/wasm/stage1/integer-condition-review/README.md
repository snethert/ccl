# Integer conditions R2: audit-106 follow-up

This proposal supersedes the unintegrated integer-condition R1 proposal. It
keeps the accepted integer-call compiler as its shared-source baseline; no
shared compiler or runtime file changes here. The user said “proceed” after
the recommendation to fix the oracle/admission gaps and match native CCL's
explicit NIL divisor. Acceptance of this revised auxiliary unit remains open.
There is no LL16 slot credit or acceptance-criterion change.

Three compiler changes address the audit:

- NUMBER, REAL and TRUNCATE enter the quote allowlist only while the numeric
  mode is enabled. The default entry refuses all three; the numeric entry
  admits them. This is tested directly, in addition to the inherited byte
  comparison of sixty default-mode WAT/Wasm files.
- TRUNCATE evaluates both operands once, in order, then replaces a NIL divisor
  in its private root slot with tagged one. The caller's argument and original
  source binding are unchanged. Fixnums and bignums return their original
  value and zero remainder, including dynamic and short multiple-value calls.
- ASH checks the count before the integer after both operand expressions have
  completed. Other operations keep their previous left-first checks.

The native condition-field oracle now constructs DIVISION-BY-ZERO only when
the dividend is REAL and the divisor is zero. Otherwise it calls real native
TRUNCATE, so a nonnumeric dividend with zero divisor is a native TYPE-ERROR.
The original biased oracle is retained as a rejected control against the same
target modules. Native zero-divisor trap metadata remains separately recorded:
fixnum traps report `/`, while bignum traps report `COERCE` with no operands.
The explicit constructor still supplies the TRUNCATE/operand-list field oracle;
this is not a claim of equivalence to that native trap metadata.

The corpus retains every R1 case and adds explicit NIL divisors, nonnumeric
dividends with zero, nonnumeric divisors, two invalid operands, evaluation
effects, and wrong-class reader calls caught by ERROR. A direct native probe
records five safety/speed policies. All five agree on ASH's count-first check
and the NIL-divisor behavior. At safety 3/speed 0, native `+` and `*` inspect
the right operand first when both are bad. At the other four policies they
inspect the left. The target uses stable left-first checks for these operations
and does not promise policy-dependent error priority. The complete native
matrix is retained without converting these differences into passing target
comparisons.

Wrong-class arithmetic-error readers retain the existing target convention:
TYPE-ERROR, rather than native CCL's NO-APPLICABLE-METHOD-EXISTS. A native file
records both reader classes; compiled ERROR handlers agree. With no Lisp
handler, an ordinary nonnumeric operand reaches fatal kind 5. This is a
stage/operation-specific diagnostic, not a unique error class: registry faults
also use 5. It differs from the original integer service's status-derived 32.
Malformed/service-budget failures and recognised unsupported number families
retain their checked boundaries.

## Evidence

The 67-module corpus has 423 native/reference cases, executed below and above
2 GiB normally and under forced numeric output shortage, plus the inherited
small-heap growth/refusal scenarios. There are 1,693 comparisons, 477 collector copies, one growth and 252 inline
checks.

Thirteen recompiled compiler faults are rejected during execution, including
omitted NIL normalization and ASH's old check order. Two harness controls,
one default-mode admission control and the biased-native-oracle control are
also rejected, for seventeen controls total. The admission control fails its
explicit native source-admission assertion; it is not counted as a runtime
mutant or as an accidental syntax failure.

Native R6/R6a builds the exact proposed compiler in a disposable U1 copy and
requires 21,843 tests, 162 unchanged registered FASLs and all 164 restored after
removal. The verifier requalifies that retained build and independently
recompiles/re-executes this packet. R1 and its original development failures
remain retained by their prior hashes.

```sh
python3 tests/wasm/stage1/integer-condition-review/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-19-stage1-integer-conditions-r2 \
  --output /tmp/integer-conditions-r2-replay
```

The output directory must be new. `native.py` separately repeats native builds.
Numeric operations/arity, sealed class layout, trusted single-Worker owner,
root frames, unsupported numeric families, non-rollback assurance, default
constructor exhaustion and production-loader refusal retain R1's scope.
Floating point, allocation-retry composition and numeric-loader admission
remain open. There is no performance claim.
