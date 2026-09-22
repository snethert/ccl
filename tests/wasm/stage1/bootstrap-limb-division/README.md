# Original CCL bignum division

This proposal executes CCL's original `BIGNUM-TRUNCATE`,
`BIGNUM-TRUNCATE-NO-REM` and `BIGNUM-REM`. Original execution rises **534 → 537**, with **502 non-NIL witnesses** and
**22,480 comparisons**. Admission remains **2,060 of 2,231**. These are whole-file definitions, with no source rewriting.

Target Lisp supplies the digit division, quotient-estimate correction and
carry-addition LAP entries. Unsigned 16-bit halves keep every intermediate in
a target fixnum. The dividend and divisor sign handling, working buffers,
normalization and long-division algorithm are the original CCL code. No new
C or runtime JS service is added, and no speed claim is made.

The signed corpus covers quotient zero, multiple quotient digits, exact powers,
full digit carries and dividends through 1,024 bits. The four sign combinations
are compared with native CCL for all three original division entries. A retained development probe of the Lisp digit loop on native CCL has 10,000
seeded comparisons against native integer division; these are not target
execution credit. Its internal
contract is a nonzero 32-bit divisor and an upper dividend digit smaller than
the divisor; it returns quotient and remainder as four unsigned 16-bit halves.
Existing digit access checks govern the object reads and stores. Direct target
calls refuse a zero divisor and a quotient that cannot fit in one digit. For
unsigned inputs the explicit zero test is redundant with the upper-digit bound;
removing the upper-digit bound is distinguished by the second case.

The first run exposed a CCL 32-bit source bug: the early return for a smaller
dividend ignored NO-REM and leaked a second value. A Wasm-only reader branch
honours NO-REM. Quotient-only cases cover this branch for every sign pair.

Final-source R6/R6a is run for this proposal. The bignum32 reader
proof is rerun across all eight assignments, including the quotient-only fix.
This remains an unreviewed, unintegrated proposal. GCD, generic numeric restart
semantics, full GF dispatch, the remaining metadata/owner work and LL15's
image/READY join are not claimed complete.

```sh
python3 tests/wasm/stage1/bootstrap-limb-division/packet.py verify --packet ../ccl-evidence/2026-09-22-stage1-bootstrap-limb-division-r1 --output /tmp/ccl-limb-division-replay
```
