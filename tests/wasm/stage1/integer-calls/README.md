# Generated integer calls (auxiliary LL16 prerequisite)

This proposal connects real CCL front-end calls to the accepted D1 integer
service. It is developed only in disposable U1 copies. It does not execute an
LL16 inventory slot and is not integrated into the shared compiler or loader.
The integer C service and collector binary are reused unchanged by hash.

`compile-integer-call-form` enables a private, off-by-default mode. The admitted
operations are two-argument `+`, `-`, `*`, `ash` and `truncate`, and one-argument
`integer-length`. Source pre-expansion respects lexical function shadows;
FLET definition bodies still see the enclosing function namespace. Unary and
variadic arithmetic, FLOOR, one-argument TRUNCATE and taking the arithmetic
function object are outside this slice. Six source refusals retain that limit.

Both operands are evaluated once, left to right, into a two-slot root frame.
Generated Wasm computes in-range fixnum results directly, using i64 arithmetic
for overflow and quotient checks. Negative integer length and arithmetic right
shifts follow native CCL, including large negative counts. Overflow, bignums,
large positive shifts and checked errors use one `integer.calculate` import.
TRUNCATE publishes both values; scalar, retained, discarded and dynamic
multiple-value consumers use the existing B result machinery.

The synchronous owner capability runs the unchanged arithmetic module in a
separate unshared memory with fixed input, output, scratch and result regions.
It copies D1 integer bytes into that memory and performs no JavaScript integer
arithmetic. After the service has prepared the complete result, it asks the
accepted collector owner for space. The private results contain no heap
references and survive collection and memory growth. The capability then
reloads the allocation pointer and memory view, copies the result objects and
publishes the allocation pointer and both rooted values without a call or poll
between those writes. Both input roots remain live throughout assurance. A
failed assurance may already have moved objects, as in the accepted owner
contract; it is not a heap rollback.

The capability validates the top root frame, memory identity, input extents,
integer shapes and pinned service digest. It trusts the single Worker's owner
for object starts, pinned regions and valid TCR ownership. It is not an
untrusted-memory parser or a concurrent publication protocol. Re-entry into
an active owner boundary refuses. Canonical input-budget refusals are not
retried as output shortages. All slow-path bignum operands and results are
copied through private storage; no timing claim is made. Even the inline
fixnum path currently reserves its operand root frame.

Numeric failures in this slice remain checked boundary exceptions: for
example division by zero is code 34, noninteger input is code 32, and an
input/result budget refusal is code 33. Handleable Lisp numeric conditions,
floating-point operations and the approved D6 policy path remain subsequent
work. Nonnumeric allocations still use the default compiler's existing
checked paths; this entry does not enable the separate allocation-retry mode.
Only numeric result assurance is composed with collection here.

The production binary reader refuses the function import on every generated
module. Execution uses an explicit eager owner capability; no production lazy
loader admission is claimed. The default compiler APIs remain byte-identical
on all 60 WAT/Wasm files of the reviewed generic-dispatch corpus.

## Qualification

The native oracle executes the original Lisp forms, including local shadows,
closure captures, default expressions, operand effects, cleanup, catch/throw,
pending multiple values, and two large integers from a real literal pool.
The target executes 25 modules and 305 native cases at placements below and
above 2 GiB, both normally and with forced shortage. A small-heap literal
case succeeds after real memory growth; its high-memory counterpart collects
and then refuses at the memory maximum while restoring the caller. Retired
spaces are poisoned after movement. Counts of collector copies include both
the initial collection and the second copy into a newly grown pair.

The final run contains 1,221 native-derived comparisons, 429 collector copies
and one memory growth. Six recompiled compiler faults and three owner faults
are rejected at recorded assertions. They cover the fixnum boundary, negative
integer length, large right shifts, both truncate values, operand order,
allocation-pointer reload, the second output root and allocation publication.
A native R6/R6a run of this exact proposed compiler passes 21,843 tests,
retains 162 of 164 registered FASLs unchanged, and restores all 164 after
removal. It is retained separately from the execution replay.

The original unsuccessful qualification is retained: the fixnum-bound fault
failed at `n_mul/25`, while its harness expected `n_add`. The expected
first-case label was corrected, and explicit nonzero fixnum remainders were
added before finalization. No escaped fault or implementation correction is
claimed for that attempt.

From the repository root, with the retained evidence repository:

```sh
python3 tests/wasm/stage1/integer-calls/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-19-stage1-integer-calls-r1 \
  --output /tmp/integer-calls-replay
```

The verifier checks source and toolchain pins, reconstructs the native R6
inputs, reruns qualification, recompiles the positive and mutant compilers,
re-executes the owner scenarios and compares deterministic outputs with the
packet. The output directory must not already exist. Native builds can be
repeated with `native.py`; the retained verifier requalifies their exact
captured artifacts rather than rebuilding every native target again.
