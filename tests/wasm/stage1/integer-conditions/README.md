# Generated integer conditions (auxiliary LL16 prerequisite)

This disposable compiler proposal extends the accepted integer-call mode with
Lisp TYPE-ERROR and DIVISION-BY-ZERO delivery. It is auxiliary, unintegrated and
claims no LL16 slot. The C arithmetic service, JavaScript owner capability,
collector and production loader are unchanged.

Both operands are evaluated into the existing two-slot root frame before type
checking. Fixnums and D1 bignums enter the accepted arithmetic helper. Admitted
nonnumeric values signal through the existing implicit-error service, retaining
the offending datum and expected NUMBER, REAL or INTEGER symbol. Recognised
ratios, complex numbers and floats still refuse at the unsupported numeric
boundary (code 32); they must not be reported as failing NUMBER. Malformed
bignum shapes and service budgets retain their checked refusals.

A zero divisor constructs a rooted two-element operand list and calls the
implicit-error service with kind 34. Its condition is a real D1 instance and
slot vector, using the native class layout exported by CCL. The sealed owner
registry may contain the old twelve/thirteen rows or fifteen rows including
ARITHMETIC-ERROR and DIVISION-BY-ZERO. Their native slots are OPERATION,
OPERANDS and STATUS. The new condition carries TRUNCATE and the operand list;
STATUS keeps the native NIL default. The two arithmetic-error readers compile
to checked accesses, and ordinary ERROR and ARITHMETIC-ERROR handlers match the
new class through its ancestry. Handler masking, cleanup, restart transfers,
resignalling and condition rooting use the accepted runtime machinery.

## Native oracle boundary

The unmodified x86-64 native trap does not always carry the Lisp operation and
operands. `native-zero-traps.txt` retains its actual observations: fixnum cases
report `/` and their operands; the two bignum cases report `COERCE` and NIL.
An initial nested probe consequently tried to divide NIL. This is retained as
a native-oracle failure, not erased or counted as target agreement.

For the added `e_` reference functions only, a lexical native TRUNCATE wrapper
uses CCL's explicit `(make-condition 'division-by-zero :operation 'truncate
:operands (list a b))` when the divisor is zero. Nonzero arithmetic still calls
native TRUNCATE. The wrapper supplies a protocol oracle for the condition
fields; it does not reproduce the native hardware-trap fields. This follows
U1's explicit Lisp zero-divisor construction in `level-0/l0-numbers.lisp` and
its 32-bit bignum path in `level-0/l0-bignum32.lisp`, both pinned. All other
arithmetic, type errors, handlers, restarts and field readers execute native
CCL. The 305 inherited arithmetic cases use their original native functions.
No timing or exact x86-64 trap-metadata equivalence is claimed.

## Qualification and review follow-up

The 54 generated modules run 372 reference cases at both memory placements,
with and without forced numeric output shortage: 1,489 comparisons, 465
collector copies and one real growth. A final high-memory case collects and
then refuses growth, leaving live roots valid and the caller restored. The
added cases include handlers that perform collecting arithmetic and then
resignal their condition, two-result retention across a handled failure,
cleanup effects, restart values, type-error datum/expected type, NIL short
multiple-value fills, local shadows and mutated bignum bindings.

Audit 105's three coverage observations are addressed explicitly:

- The harness pins the arithmetic binary to the retained SHA-256 before
  creating the capability. A wrong-pin control refuses before execution.
- All six eligible fixnum operations have zero-slow-call assertions, 252
  checks overall. Six separately compiled faults force one operation at a
  time through the slow service, and each fails its inline assertion.
- The decoder represents NIL and T. Short multiple-value fills have native
  expectations; a NIL-as-zero oracle control is rejected.

Five further compiled faults cover skipped type signalling, the wrong
condition class, missing operands, wrong expected type and an omitted
condition root. There are eleven compiled faults and two harness controls,
all rejected during execution. The default APIs reproduce the reviewed
30-module dispatch corpus's 60 WAT/Wasm files byte for byte. Native R6/R6a of
the exact proposed compiler passes 21,843 tests, preserves 162 of 164
registered FASLs, and restores all 164 after removal.

The development archive retains the native trap-field failure, the harness's
initial two-slot assumption (native CCL also has STATUS), an invalid mutant
that removed a formatting argument (not counted as rejection), and a guessed
first-failure label corrected from `e_zero` to the earlier `e_collect` case.

## Limits

The admitted integer operations and arities are unchanged. General arithmetic
and floating-point execution remain open. This mode still uses a two-slot root
frame and classification helper calls before arithmetic; no speed claim is
made. Nonnumeric allocation retry is not enabled by this entry, so condition
and operand-list constructors can still refuse for heap exhaustion. Collection
inside handlers is exercised through numeric service calls. The service
remains synchronous and trusted-owner only. Failed space assurance is not a
rollback. With no Lisp handler, failures reach the existing fatal boundary.
The production loader refuses the numeric import; authenticated admission and
its composition with the allocation-retry capability remain subsequent work.

Replay from the repository root:

```sh
python3 tests/wasm/stage1/integer-conditions/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-19-stage1-integer-conditions-r1 \
  --output /tmp/integer-conditions-replay
```

The output directory must be new. Replay checks source/input/toolchain hashes,
requalifies the retained native build, recompiles the corpus and eleven faulty
compilers, executes both harness controls and compares deterministic files.
The native build can separately be repeated with `native.py`.
