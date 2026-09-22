# CCL limb multiplication

Original CCL executions rise from **531 to 534**, with **499 non-NIL witnesses**
and **21,760 comparisons**. Admission rises from 2,059 to **2,060 of 2,231**.
The additions are bignum multiplication and the two float `MINUSP` helpers;
no earlier original execution is lost.

`multiply.lisp` supplies native LAP equivalents using eight-bit partial products,
so every arithmetic intermediate fits a target fixnum. CCL's existing
`MULTIPLY-BIGNUMS` supplies sign handling, allocation and the schoolbook loop.
The Wasm branch selects that loop, as x8632 and ARM already do, and removes the
unreachable foreign-pointer branch from the Wasm reader. CCL's front end still
processes an unreachable branch before this backend emits it; appending Wasm
to the constant-false condition alone did not remove the foreign dependency.
The refused GMP arm has an explicit unreachable error body on the target.
Inputs cover both signs, full carry chains, the 16-limb algorithm threshold and
32,800-bit operands, beyond the bounded integer service's capacity. No new C or
runtime JS service is added.

Two machine lowerings read float sign bits through the existing checked real
operand decoder, preserving the sign of zero. Direct caller rows observe both
zero signs in both widths; wrong-type calls refuse without allocation. CCL's
unchanged `%DOUBLE-FLOAT-MINUSP` and `%SHORT-FLOAT-MINUSP` bodies then execute.

Generic `MINUSP` and the original `MULTIPLY-BIGNUM-AND-FIXNUM` are still blocked
by `%KERNEL-RESTART`; supplying their input recipes does not earn execution
credit. A target-only caller exercises the new fixnum loop against native `*`,
including the boxed positive magnitude of the target's most-negative fixnum.
The loop splits that magnitude with the existing bignum digit reader. That
caller earns no original-definition credit. The half-digit entries are internal
LAP equivalents over unsigned sixteen-bit halves, not public arbitrary-integer
APIs. General kernel restarts, division/GCD primitives, remaining metadata and
the image/READY join are still unfinished.

Native R6/R6a runs on the final proposed files. The extra `l0-bignum32` change
does not participate in the native 64-bit build. Its reader proof therefore
reads the entire old and proposed files under all eight assignments of the
changed architecture tests and 32/64-bit file guard, with Wasm absent. The
32-bit cases must actually include the file body. `DIGIT-SIZE` is bound to the
file's declared 32 for its read-time constant. The script asserts that removing
only the three declared reader edits restores the original source exactly.
Every existing native target is covered by one of those feature assignments.

From the repository root:

```sh
python3 tests/wasm/stage1/bootstrap-limb-multiply/packet.py verify --packet ../ccl-evidence/2026-09-22-stage1-bootstrap-limb-multiply-r1 --output /tmp/ccl-limb-multiply-replay
```

The verifier reuses the preceding retention format, reruns the reader proof,
whole-file compile, native oracle and target execution, and reuses native
qualification only after exact final-source comparison. The proposal is
unreviewed and unintegrated and awards no LL15 credit.
