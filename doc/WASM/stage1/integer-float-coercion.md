# Integer-to-float coercion decision — 20 September 2026

After Claude audit 112 (`97f589ad`) identified the untested rounding band in
STAGE1-FLOAT-CALLS-R1, Codex asked whether to match native silent coercion or
retain D6 flag-based signalling as a disclosed difference. The user selected:

> Match native CCL below the limits (Recommended)

The question explicitly preserved native's unconditional overflow error at or
above magnitude 2^128 for single and 2^1024 for double. This decision applies
to the generated Lisp numeric path. The mathematical primitive's independent
IEEE conversion flags and the adopted D6 policy for floating arithmetic remain
unchanged.

U1's `%bignum-sfloat` and `%bignum-dfloat` construct the rounded bits without an
FPU conversion. Values just below the limits can round to signed infinity
without signalling; ordinary bignum rounding does not signal inexact either.
Their explicit exponent guard runs before rounding. The reference is the
pinned macOS x86-64 U1, whose fixnum conversion instead uses hardware and can
signal inexact. The follow-up native matrix reproduces that distinction at
2^60, as well as at the target D1 fixnum boundary 2^29. Thus the proposed
compatibility entry selects the reference's conversion behavior by numeric
magnitude, not by the narrower target's fixnum/bignum tag. The exact negative
value -2^60 is representable in either float precision, so its asymmetric
native fixnum membership introduces no flag difference.

Only integer-coercion flags are suppressed for the reference bignum range.
Floating narrowing and the arithmetic performed after coercion retain their
D6 checks, including invalid, division by zero, overflow, underflow and inexact.
The existing adapter continues to select unconditional explicit coercion
failure at or above the limits. The previously recorded exact-tiny difference
from x86's unmasked trap behavior remains separate.

This changes no inventory criterion or acceptance count. The implementation
and its native boundary matrix remain proposals until adversarial review and
user acceptance.
