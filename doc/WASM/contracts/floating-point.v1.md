# Floating-point detection specification v1

Status: specification under the D6 floating-point hypothesis, authored by
Claude on 15 September 2026 with an executable proof
(`tests/wasm/stage0/float-detection`), corrected after Codex's first and
second reviews and awaiting its follow-up review. It specifies detection,
as D6 requires before any cost is measured. It does not make the Stage 2
compatibility decision about which conditions the port signals; that
remains the user's policy choice.

## What U1 does

The native x86 kernel sets each thread's MXCSR to mask denormal, underflow
and precision exceptions and leave invalid, zero-divide and overflow
unmasked (`thread_manager.c`, `lisp_mxcsr`). So by default CCL signals
`floating-point-invalid-operation`, `division-by-zero` and
`floating-point-overflow` and silently returns subnormal, zero and rounded
results for underflow and inexact. `set-fpu-mode` can unmask underflow and
inexact. The SIGFPE handler in `x86-trap-support.lisp` builds the condition
from the exception code with `:operation`, `:operands` and `:status`. Double
comparisons use `comisd`, which raises invalid for any NaN operand, so
comparing with a NaN signals under the default mode; `ucomisd` would not.

## What Wasm offers

Wasm floating-point instructions are IEEE 754 with round-to-nearest-even,
no exception flags, no trap mode and no rounding-mode control. NaN payloads
are not deterministic. Float-to-integer truncation traps on NaN and
out-of-range input unless the saturating form is used. Detection therefore
has to be computed from operands and results.

## Detection

For an operation with result `r`:

- NaN operand: `r` is NaN, status exact. A NaN propagating through
  arithmetic is not a new invalid operation. Signalling NaNs are not
  distinguished.
- Invalid: `r` is NaN and no operand is NaN. This covers inf − inf,
  0 × inf, 0 ÷ 0, inf ÷ inf and the square root of a negative number.
- Division by zero: the divisor is ±0 and the dividend is finite and
  nonzero. inf ÷ 0 is exact infinity, 0 ÷ 0 is invalid.
- Overflow: `r` is infinite and every operand is finite. An infinite
  operand yields an exact infinity.
- Underflow: `r` is finite, the result is tiny and inexact, including a
  nonzero exact value that rounds to zero. Tininess is decided after
  rounding, as IEEE 754 §7.5 defines it and as x86 SSE implements it: the
  exact result rounded to 53 bits with an unbounded exponent range has a
  magnitude below 2^-1022. This is not the same as testing the final
  result. When the exact value lies in [2^-1022 − 2^-1075, 2^-1022 − 2^-1076)
  the bounded rounding reaches 2^-1022, a normal number, while the
  unbounded rounding stays at 2^-1022 − 2^-1075 or below: such a result is
  tiny, and the hardware sets the underflow flag for it. At exactly
  2^-1022 − 2^-1076 the unbounded rounding ties to even, 2^-1022, and the
  result is not tiny. Every other tiny result is subnormal or zero, so
  only a final result of magnitude exactly 2^-1022 needs the exact witness
  to decide.
- Inexact: `r` is finite, not tiny, and differs from the exact result.

The first four need only classification. The last two need an exactness
witness, computed with error-free transformations:

- Addition and subtraction: TwoSum gives the exact rounding error for every
  finite pair, including subnormals, so `r` is exact iff the error is zero.
- Multiplication: Dekker's TwoProduct with the 2^27 + 1 split, applied only
  to operands of magnitude at most 2^996 so the splitter product cannot
  overflow. A larger factor is scaled down by 2^28 together with the
  product, which commutes with the rounding of a normal product, and the
  error is scaled back up; scaling only the split's high part back up is
  wrong, because near the largest exponent the rounded high part reaches
  2^996 and its rescaling overflows (the review's MAX × 1 counterexample).
  Partial products must not underflow, so
  when |r| < 2^-970 both factors are scaled by 2^537 (exact) and the
  witness compares the scaled product, whose partials are at least 2^-53,
  with `r` scaled by 2^1074 in two exact steps; a factor below 2^-970 with
  a normal product is scaled up by 2^537 alone, which commutes with
  rounding. A zero product from nonzero factors is underflow without a
  witness. When |r| is exactly 2^-1022 the scaled error
  e = (a·b − r)·2^1074 is exact (the scaled product and r·2^1074 lie within
  a factor of two, and e is a multiple of 2^-53 of magnitude at most one),
  and the product is tiny iff e has the sign opposite to r with |e| > ¼.
- Division: the residual a − r·b, with r·b expanded by TwoProduct, is zero
  iff the quotient is exact. A quotient below 2^-970 is witnessed on a
  dividend scaled up by 2^1074 or a divisor scaled down by 2^1074,
  whichever is exact, and requires in addition that `r` scaled by 2^1074
  equals the scaled quotient, which catches the second rounding into the
  subnormal range. A dividend below 2^-970 with a normal quotient scales
  both operands by 2^537, leaving the quotient unchanged. When |r| is
  exactly 2^-1022 the quotient is tiny iff |a'| < (2^52 − ¼)|b'| on the
  scaled operands: |a'| − 2^52|b'| is exact by Sterbenz and adding |b'|/4
  gives an exactly signed sum. Only a dividend whose significand is all
  ones over a power-of-two divisor can reach that region.
- Square root: the residual a − r·r with r·r expanded by TwoProduct. A
  subnormal or small operand below 2^-970 is scaled by 2^1074, whose root
  scales by 2^537 and commutes with rounding. A square root never
  underflows and never overflows.

Float-to-integer conversion truncates with `f64.trunc`, refuses NaN and
infinity as invalid, takes the bignum path when the truncated value is
outside the fixnum range, and otherwise uses the saturating instruction,
which can no longer trap. Single floats use the same classification for the
three default-mode conditions; their exactness witnesses are the same
algorithms with the 2^12 + 1 split and are not part of this slice.

## Proof

2,069 corpus cases, 119 named boundary cases and 1,950 deterministic random
cases over normals, subnormals, powers of two, small integers, values near
both signs of the maximum exponent, products and quotients straddling the
normal/subnormal boundary, small exact multipliers and specials, have
expectations computed by exact rational rounding with correct
tininess-after-rounding and ties-to-even, including correctly rounded
irrational square roots. Every status and every result bit pattern agrees;
NaN results are compared for NaN-ness only. The 1,646 f64 cases also
execute natively on the macOS x86-64 reference machine through scalar SSE
instructions with MXCSR reset before each operation, and the status taken
from the hardware flags in x86 priority and the result bits equal the
oracle's expectations for every case, so the oracle's definitions,
tininess after rounding included, are the hardware's. Eleven mutants of the
module are rejected by the unchanged oracle: the divisor-zero check
omitted, NaN propagation reported as invalid, overflow reported for any
infinity, the large-operand scaling removed, the witness ignored, underflow
reported as inexact, the conversion left unchecked, the small-product
scaling removed, tininess judged on the final result, the boundary tie
counted as tiny, and the quotient boundary ignored. The first execution
classified exact results near the largest finite double as inexact and the
second judged tininess on the final result; Codex's reviews found both, and
the corrected execution supersedes them.

## Policy inputs this leaves open

Which of the six statuses signal a condition, and whether `set-fpu-mode`
keeps its native keywords, is the D6 compatibility decision; the default
mode needs only the three classification-based statuses and no witness.
One nuance belongs to that decision: with underflow unmasked, x86 traps on
every tiny result, exact subnormal results included, while the masked flag
and this specification's underflow status require inexactness as well; a
port that unmasks underflow natively-faithfully would need a further
"tiny and exact" status, which the witnesses can supply.
The cost of a witness is measurable now that its correctness is fixed.
Comparison with NaN, rounding modes other than nearest and literal
encodings are stated as follows: comparisons signal invalid for any NaN
operand under the default mode to match `comisd`; only round-to-nearest
exists; float literals cross-dump as their bit patterns.
