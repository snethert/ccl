# Generated floating calls R2: native integer coercion

This follow-up answers audit 112 under the user's
[coercion decision](../../../../../doc/WASM/stage1/integer-float-coercion.md).
It supersedes R1's broad native-coercion compatibility claim. The compiler,
loader, adapter and all shared runtime files are unchanged. A derived C
primitive has a separate `float_calculate_lisp` entry, selected by a one-call
change in the proposed owner capability; its original `float_calculate` entry
retains the accepted mathematical behavior.

## What changes

The native macOS x86-64 reference constructs bignum float bits without setting
conversion flags. Below magnitude 2^128/2^1024, this includes the tie and the
rounding band that become signed infinity. Explicit coercion errors at and
above those limits remain unconditional in the unchanged Lisp adapter.
Small-integer hardware conversions still report inexact, as the native matrix
shows. The compatibility entry therefore suppresses integer-conversion flags
only beyond the reference's 60-bit positive fixnum magnitude; it does not use
the target D1 tag to infer the reference representation. Floating conversions
and subsequent arithmetic keep their flags and the D6 enable mask.

The new raw entry still computes the correct rounded bits. Only selection of
integer conversion flags changes. It adds no allocation, callback or safepoint.
The owner stages and publishes exactly as reviewed in audit 111. The compiler
regenerates byte-identically to R1, so its native R6/R6a, eight compiled-fault
rejections and default-mode witnesses are reused by packet and compiler hashes.
Every native numeric expectation is re-executed.

## Coverage

4,379 native cases run at four settings: below/above 2 GiB, ordinary/forced
collection, with eager and cold results equal. Boundary rows cover both signs,
the largest finite float, the integer below the overflow rounding tie, the tie,
the integer above it, the last integer below the explicit overflow limit, the
limit and its successor. They also cover inexact integers, the reference fixnum
boundary and the D1 boundary. Masks 0, 7, 16 and 31 and both checking modes run
for explicit coercion and all four arithmetic operations in both operand orders.
Further rows keep arithmetic invalid, division-by-zero, overflow and inexact
observable after silent conversion. In unchecked rows the native oracle runs
with all hardware traps masked, as in R1; explicit library errors still occur.

The original raw entry replays all 59,083 accepted mathematical cases at three
placements (177,249 comparisons). Nine focused faults must fail the selected
case's exact function/id assertion: old coercion entry, old right-operand
conversion, suppressed small-integer inexact, wrong magnitude cutoff, suppressed
arithmetic overflow/invalid, and the three previously rejected adapter faults.
The two arithmetic controls share the same altered source but test distinct
conditions. Assertion matching identifies the case, not an exact diagnostic.

The original failing R1 execution is retained separately. Its first failure is
an inexact condition where native returns the rounded largest finite single;
the focused old-entry control targets the reported default-mode infinity case.
The development archive also retains the undefined single-bit constructor used
by the first expanded native harness and its correction. No runtime defect was
found in the R1 primitive; the gap was the generated Lisp compatibility policy.

R1's explicit-constructor `h_collect` oracle remains unchanged and is not claimed
to be necessary on this host. Its original 116-row policy join, including the
one approved exact-tiny difference, is retained. New boundary rows compare
directly with native, without substituting rational-oracle answers. Integer-only
comparisons and the existing checked refusal for integer division are unchanged.
No LL16 credit or timing claim is made.

## Replay

```sh
python3 tests/wasm/stage1/float-calls/review-followup/run.py --evidence ../ccl-evidence --output /tmp/float-calls-r2
python3 tests/wasm/stage1/float-calls/review-followup/packet.py verify --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-20-stage1-float-calls-r2 --output /tmp/float-calls-r2-verify
```
