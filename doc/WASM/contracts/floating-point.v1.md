# Floating-point detection specification v1

Status: specification under the D6 floating-point hypothesis, authored by
Claude on 15 September 2026 with an executable proof
(`tests/wasm/stage0/float-detection`) and awaiting Codex's review. It
specifies detection, as D6 requires before any cost is measured. It does not
make the Stage 2 compatibility decision about which conditions the port
signals; that remains the user's policy choice.

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
- Underflow: `r` is finite, |r| is below the smallest normal number
  (tininess after rounding, as x86 does) and the result is inexact,
  including a nonzero exact value that rounds to zero.
- Inexact: `r` is finite, not tiny, and differs from the exact result.

The first four need only classification. The last two need an exactness
witness, computed with error-free transformations:

- Addition and subtraction: TwoSum gives the exact rounding error for every
  finite pair, including subnormals, so `r` is exact iff the error is zero.
- Multiplication: Dekker's TwoProduct with the 2^27 + 1 split. The split is
  applied to operands scaled down by 2^28 when |x| > 2^996 so it cannot
  overflow, and scaled back up. Partial products must not underflow, so
  when |r| < 2^-970 both factors are scaled by 2^537 (exact) and the
  witness compares the scaled product, whose partials are at least 2^-53,
  with `r` scaled by 2^1074 in two exact steps; a factor below 2^-970 with
  a normal product is scaled up by 2^537 alone, which commutes with
  rounding. A zero product from nonzero factors is underflow without a
  witness.
- Division: the residual a − r·b, with r·b expanded by TwoProduct, is zero
  iff the quotient is exact. A quotient below 2^-970 is witnessed on a
  dividend scaled up by 2^1074 or a divisor scaled down by 2^1074,
  whichever is exact, and requires in addition that `r` scaled by 2^1074
  equals the scaled quotient, which catches the second rounding into the
  subnormal range. A dividend below 2^-970 with a normal quotient scales
  both operands by 2^537, leaving the quotient unchanged.
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

1,882 corpus cases, 82 named boundary cases and 1,800 deterministic random
cases over normals, subnormals, powers of two, small integers and specials,
have expectations computed by exact rational rounding with correct
tininess-after-rounding and ties-to-even, including correctly rounded
irrational square roots. Every status and every result bit pattern agrees;
NaN results are compared for NaN-ness only. Eight mutants of the module are
rejected by the unchanged oracle: the divisor-zero check omitted, NaN
propagation reported as invalid, overflow reported for any infinity, the
split left unscaled, the witness ignored, underflow reported as inexact,
the conversion left unchecked, and the small-product scaling removed.

## Policy inputs this leaves open

Which of the six statuses signal a condition, and whether `set-fpu-mode`
keeps its native keywords, is the D6 compatibility decision; the default
mode needs only the three classification-based statuses and no witness.
The cost of a witness is measurable now that its correctness is fixed.
Comparison with NaN, rounding modes other than nearest and literal
encodings are stated as follows: comparisons signal invalid for any NaN
operand under the default mode to match `comisd`; only round-to-nearest
exists; float literals cross-dump as their bit patterns.
