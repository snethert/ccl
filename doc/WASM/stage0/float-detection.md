# Floating-point detection — 16 September 2026

Status: diagnostic EXECUTED and PASSING at its stated scope in its second
corrected form `FLOAT-DETECTION-R3`, awaiting Codex's follow-up review. The
earlier executions are retained unchanged: `FLOAT-DETECTION-R1` classified
the largest finite double times one as inexact, and `FLOAT-DETECTION-R2`
classified a product that is tiny after rounding as merely inexact; [Codex's
reviews](codex-review.md) found both. No inventory slot changes and no gate
credit; Stage 0 stays at 40 accepted, two missing and six unreviewed of 48.

## Second correction after review

The R2 finding: for 2^-1022 × (1 − 2^-53) the module answered inexact and
the rational oracle answered underflow. The exact product is
2^-1022 − 2^-1075; rounded to 53 bits with an unbounded exponent range it
stays below 2^-1022, so it is tiny under IEEE 754's after-rounding
definition, but the bounded rounding reaches 2^-1022 exactly, and the
module judged tininess on that final result. The oracle was right: on this
x86-64 Mac, U1's reference platform, `mulsd` sets the underflow flag for
the case and does not for its neighbour 2^-1022 × (1 − 2^-104).

The correction resolves the definition explicitly in favour of IEEE 754 and
the hardware. The [specification](../contracts/floating-point.v1.md) now
states it, and the module decides the one distinguishing situation, a final
result whose magnitude is exactly the smallest normal, from its exact
witness: a product is tiny when its exact value lies more than 2^-1076
below the result in magnitude (the scaled error is exact, a multiple of
2^-53), and a quotient when |a| < (2^52 − ¼)|b| on the scaled operands
(an exact difference by Sterbenz and an exactly signed sum). The corpus
gains twenty-one named cases at the boundary, including the review's case
under both operand orders and all sign combinations, the tie that rounds to
even and is not tiny, its neighbours on both sides, and quotients through
both scalings of the small-quotient witness, plus 150 deterministic random
cases straddling the boundary. Three more mutants are rejected: tininess
judged on the final result (the R2 defect) at the review's case, the tie
counted as tiny, and the quotient boundary ignored.

Every f64 corpus case now also executes natively. A small C program,
compiled with the system compiler at `-O0` so that each operation is one
`addsd`, `subsd`, `mulsd`, `divsd` or `sqrtsd`, resets MXCSR to its default
before every operation and reports the six exception flags and the result
bits. For all 1,646 f64 cases the status taken from the flags in x86
priority and the result bits equal the oracle's expectations, so the oracle
agrees with the reference hardware on every corpus case, not only at the
boundary. Codex's R2 boundary probe, run unchanged against this checkout,
reports the six max-exponent cases exact and the boundary case underflow
(`CODEX-R2-PROBES-ON-R3`).

## First correction after review

The R1 defect: the Dekker split scaled a large operand down by 2^28 for the
splitter multiplication and scaled the high part back up, and near the
largest exponent the rounded high part reaches 2^996 exactly, which
becomes 2^1024 and overflows; the error term then held infinities and the
witness reported a nonzero residual. The correction scales the whole
TwoProduct instead: a factor above 2^996 is scaled down by 2^28 together
with the product, which commutes with the rounding of a normal product, the
plain split runs on operands at most 2^996, and the error is scaled back
up. The corpus gained sixteen named cases near both signs of the maximum
exponent and a random population with exponents from 990 upward.

Authorship: Claude Fable 5.1 wrote the module, the oracle and the
[specification](../contracts/floating-point.v1.md) on branch
`wasm2-claude`; Codex reviews them. No shared compiler or upstream kernel
source changed; the native facts are read from the pinned U1 sources.

## What executes

A hand-built wasm32 module implements checked f64 add, sub, mul, div and
sqrt returning a status word without any engine flag: overflow, division by
zero and invalid from operand and result classification; underflow and
inexact from error-free witnesses, with exact power-of-two scaling whenever
a partial product could underflow or a split could overflow, and tininess
decided after rounding. A checked conversion truncates without ever
trapping and reports invalid or the bignum path. An f32 slice covers the
three default-mode conditions.

A Python oracle rounds exact rationals to the nearest double or single with
ties to even, tininess after rounding and correctly rounded irrational
square roots, and computes the IEEE flags. Over 2,069 corpus cases every
status and every result bit pattern agrees with the module, and over the
1,646 f64 cases with the native x86 flags and results as well.

| Status | Cases | Of which native f64 |
| --- | --- | --- |
| exact | 419 | 324 |
| overflow | 113 | 83 |
| division by zero | 14 | 10 |
| invalid | 125 | 112 |
| underflow | 145 | 145 |
| inexact | 972 | 972 |
| bignum path (conversion) | 34 | |
| finite, single-float slice | 247 | |

## Controls

Eleven mutants are rejected by the unchanged oracle, each at the first
corpus case that exposes it: the divisor-zero check omitted, NaN propagation
reported as invalid, overflow reported for any infinite result, the
large-operand scaling removed, the witness ignored, underflow reported as
inexact, the conversion left unchecked, the small-product scaling removed,
tininess judged on the final result, the boundary tie counted as tiny, and
the quotient boundary ignored.

## Evidence and reproduction

The packet holds the corpus with expectations, the complete bundle with
source, binary, disassembly, options and host-compiler record, eleven mutant
bundles with their observations, the native witness output with its
compiler record and instruction mnemonics, environment identity including
the C compiler, and source snapshots; the verifier recompiles and
re-executes everything, native program included, and compares 89
deterministic files byte for byte in a few seconds. The native binary
itself is not retained because Mach-O output is not byte-deterministic;
its source, compile command and disassembled mnemonics are.

Limits. This fixes detection, not policy: which statuses become conditions
is the D6 compatibility decision. The single-float slice witnesses nothing
beyond the default mode. Signalling NaNs and NaN payloads are outside the
Wasm guarantee. Cost is not measured here; the specification exists so that
it can be.
