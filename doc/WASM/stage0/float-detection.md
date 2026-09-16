# Floating-point detection — 15 September 2026

Status: diagnostic EXECUTED and PASSING at its stated scope in its corrected
form `FLOAT-DETECTION-R2`, awaiting Codex's follow-up review. The first
execution `FLOAT-DETECTION-R1` is retained unchanged: [Codex's
review](codex-review.md) showed that the largest finite double multiplied
by one, by one half, and divided by one were classified inexact although
exact. No inventory slot changes and no gate credit; Stage 0 stays at 40
accepted, two missing and six unreviewed of 48.

## Correction after review

The defect: the Dekker split scaled a large operand down by 2^28 for the
splitter multiplication and scaled the high part back up, and near the
largest exponent the rounded high part reaches 2^996 exactly, which
becomes 2^1024 and overflows; the error term then held infinities and the
witness reported a nonzero residual. The correction scales the whole
TwoProduct instead: a factor above 2^996 is scaled down by 2^28 together
with the product, which commutes with the rounding of a normal product, the
plain split runs on operands at most 2^996, and the error is scaled back
up. The corpus gains sixteen named cases near both signs of the maximum
exponent, exact and inexact, and a random population with exponents from
990 upward paired with small exact multipliers. The mutant that removes the
large-operand scaling is rejected at the first exact large product; the old
high-part rescaling is no longer a distinct mutant because the operands it
would rescale are now already bounded. Codex's boundary probe on the
corrected module reports status 0 for all three counterexamples.

Authorship: Claude Fable 5.1 wrote the module, the oracle and the
[specification](../contracts/floating-point.v1.md) on branch
`wasm2-claude`; Codex reviews them. No shared compiler or upstream kernel
source changed; the native facts are read from the pinned U1 sources.

## What executes

A hand-built wasm32 module implements checked f64 add, sub, mul, div and
sqrt returning a status word without any engine flag: overflow, division by
zero and invalid from operand and result classification; underflow and
inexact from error-free witnesses, with exact power-of-two scaling whenever
a partial product could underflow or a split could overflow. A checked
conversion truncates without ever trapping and reports invalid or the
bignum path. An f32 slice covers the three default-mode conditions.

A Python oracle rounds exact rationals to the nearest double or single with
ties to even, tininess after rounding and correctly rounded irrational
square roots, and computes the IEEE flags. Over 1,898 corpus cases every
status and every result bit pattern agrees with the module.

| Status | Cases |
| --- | --- |
| exact | 390 |
| overflow | 104 |
| division by zero | 12 |
| invalid | 123 |
| underflow | 77 |
| inexact | 900 |
| bignum path (conversion) | 37 |
| finite, single-float slice | 255 |

## Controls

Eight mutants are rejected by the unchanged oracle, each at the first
corpus case that exposes it: the divisor-zero check omitted, NaN propagation
reported as invalid, overflow reported for any infinite result, the
large-operand scaling removed, the witness ignored, underflow reported as
inexact, the conversion left unchecked, and the small-product scaling
removed.

## Evidence and reproduction

The packet holds the corpus with expectations, the complete bundle with
source, binary, disassembly, options and host-compiler record, eight mutant
bundles with their observations, environment identity and source snapshots;
the verifier re-executes everything and compares the deterministic files
byte for byte in a few seconds.

Limits. This fixes detection, not policy: which statuses become conditions
is the D6 compatibility decision. The single-float slice witnesses nothing
beyond the default mode. Signalling NaNs and NaN payloads are outside the
Wasm guarantee. Cost is not measured here; the specification exists so that
it can be.
