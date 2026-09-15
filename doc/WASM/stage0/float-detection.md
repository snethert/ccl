# Floating-point detection — 15 September 2026

Status: diagnostic EXECUTED and PASSING at its stated scope; awaiting Codex's
review under the 15 September role switch. Packet `FLOAT-DETECTION-R1` in
the evidence repository. No inventory slot changes and no gate credit;
Stage 0 stays at 40 accepted, two missing and six unreviewed of 48.

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
square roots, and computes the IEEE flags. Over 1,882 corpus cases every
status and every result bit pattern agrees with the module.

| Status | Cases |
| --- | --- |
| exact | 359 |
| overflow | 97 |
| division by zero | 12 |
| invalid | 125 |
| underflow | 81 |
| inexact | 916 |
| bignum path (conversion) | 37 |
| finite, single-float slice | 255 |

## Controls

Eight mutants are rejected by the unchanged oracle, each at the first
corpus case that exposes it: the divisor-zero check omitted, NaN propagation
reported as invalid, overflow reported for any infinite result, the Dekker
split left unscaled, the witness ignored, underflow reported as inexact, the
conversion left unchecked, and the small-product scaling removed.

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
