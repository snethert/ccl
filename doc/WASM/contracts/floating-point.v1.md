# Floating-point detection specification v1

Status: specification under D6, authored by Claude on 15 September 2026
with an executable proof (`tests/wasm/stage0/float-detection`), corrected
after Codex's first and second reviews and reviewed without defect in its
third execution. On 16 September 2026 the user decided the condition policy
("do what CCL did on ARM, plus whatever else is needed for WASM"); the
policy section below records it and the fourth execution adds it to the
proof. Detection and policy are specified; the cost of the checks in
generated code is not yet measured.

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

2,135 corpus cases, 129 named cases, 1,950 deterministic random cases and
56 policy cases, over normals, subnormals, powers of two, small integers,
values near both signs of the maximum exponent, products and quotients
straddling the normal/subnormal boundary, small exact multipliers,
specials, comparisons with and without NaN operands, and every status under
seven enable masks, have expectations computed by exact rational rounding
with correct tininess-after-rounding and ties-to-even, including correctly
rounded irrational square roots, and by the policy rule below. Every status,
every result bit pattern, every comparison result and every condition
agrees; NaN results are compared for NaN-ness only. The 1,656 f64 arithmetic
and comparison cases also execute natively on the macOS x86-64 reference
machine through scalar SSE instructions (`addsd`, `subsd`, `mulsd`, `divsd`,
`sqrtsd`, `comisd`) with MXCSR reset before each operation, and the status
taken from the hardware flags in x86 priority and the result bits equal the
oracle's expectations for every case, so the oracle's definitions, tininess
after rounding and signalling comparison included, are the hardware's.
Fourteen mutants of the module are rejected by the unchanged oracle: the
divisor-zero check omitted, NaN propagation reported as invalid, overflow
reported for any infinity, the large-operand scaling removed, the witness
ignored, underflow reported as inexact, the conversion left unchecked, the
small-product scaling removed, tininess judged on the final result, the
boundary tie counted as tiny, overflow without its inexact flag, inexact
given priority over the other flags, a quiet comparison, and the quotient
boundary ignored. The first execution classified exact results near the
largest finite double as inexact and the second judged tininess on the
final result; Codex's reviews found both, and the corrected executions
supersede them.

## Policy — decided 16 September 2026, the ARM model

Native CCL on ARM cannot trap on floating-point exceptions (the runtime
notes that NEON does not support them and that some macOS versions rebooted
when a process enabled one). It therefore keeps the logical enable mask in
the TCR, stores only the rounding mode in the hardware FPSCR, and under
float safety emits after each operation a check that reads the cumulative
flags, ANDs them with the enabled mask and traps into the condition when
any survive. The user chose that model for the port. Wasm removes the
hardware flags as well, so the status computed by the detection rules
above stands in for them. Everything else follows ARM:

- **Enable mask.** A per-thread logical control word, `fp_control` in the
  production TCR schema, with bits invalid 1, division-by-zero 2, overflow 4,
  underflow 8 and inexact 16. The default enables invalid, division by zero
  and overflow, as on ARM and x86. A new thread receives the default.
  `get-fpu-mode` and `set-fpu-mode` keep their native keywords, including
  `:underflow` and `:inexact`, and read and write the owning thread's word.
- **Flags per status.** A hardware FPU sets the inexact flag together with
  overflow and underflow, so the status maps to flags as overflow → overflow
  and inexact, underflow → underflow and inexact, and the others to their
  own flag. When only inexact is enabled, an overflowing or underflowing
  operation therefore signals `floating-point-inexact`, as it does on ARM.
- **Priority.** Among the enabled flags the condition is chosen in ARM's
  order: `floating-point-invalid-operation`, `division-by-zero`,
  `floating-point-overflow`, `floating-point-underflow`,
  `floating-point-inexact`, each carrying `:operation` and `:operands` as
  ARM's `%df-check-exception-2` does.
- **Emission.** The check is emitted after a floating-point operation
  exactly where ARM emits `trap-if-fpu-exception`: when the compiler's float
  safety is on, that is at safety 3 or under the
  `:detect-floating-point-exception` policy hook (`nx-float-safety`). Code
  compiled without float safety carries no check, as on ARM. The default
  mask needs only the classification-based statuses; the exactness witness
  for underflow and inexact is computed only when one of those two bits is
  enabled, which changes cost, not results.
- **Comparisons.** ARM compares with `fcmped`/`fcmpes` and x86 with
  `comisd`/`comiss`, both of which raise invalid for any NaN operand. Wasm
  comparisons are quiet, so the emitted comparison checks for a NaN operand
  and reports invalid through the same mask; the ordering result is the
  Wasm result (false for NaN). The native `comisd` witness in the proof
  confirms the flag.
- **Conversions.** Float-to-integer truncation reports invalid for NaN and
  infinity and takes the bignum path outside the fixnum range, never
  trapping, as specified above.
- **Tiny exact results.** ARM's hardware underflow flag, like x86's masked
  flag and this specification, requires inexactness; a tiny exact result
  raises nothing on ARM even with underflow enabled. The port follows ARM,
  so this is not a deviation.

Deviations from native CCL, recorded as the decision requires:

1. **Rounding modes.** ARM and x86 support `:nearest`, `:positive`,
   `:negative` and `:zero`; Wasm has round-to-nearest-even only.
   `set-fpu-mode :rounding-mode` accepts `:nearest` and signals an error
   naming the target for any other mode; `get-fpu-mode` reports `:nearest`.
2. **Host mathematics.** ARM reads the FPSCR after a libm call such as `pow`
   and raises from it. The port's transcendental functions come from the
   host, which exposes no flags, so after a host call only classification
   is available: a NaN result from non-NaN arguments is invalid, an infinite
   result from finite arguments is overflow (division by zero where the
   function defines it, such as `log` of zero), and underflow and inexact
   are not detected for host functions even when enabled.

Not decided here: the cost of the emitted checks in generated code, which
D6 requires measured before any cheaper alternative is proposed; and
whether Stage 1 implements any transcendental function in Lisp to remove
deviation 2. Float literals cross-dump as their bit patterns; NaN payloads
are outside the Wasm guarantee.
