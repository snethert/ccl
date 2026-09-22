# Behavioural Wasm branches in CCL definitions

Deliberate changes to a CCL definition's behaviour must be rare, named here and
identified as behavioural in its acceptance and integration records. A native
reader/R6 proof establishes preservation of existing targets; it does not make
the Wasm behaviour change a source-location-only change. This register grants
no acceptance or slot credit.

| ID | Definition | Proposal | Disposition |
| --- | --- | --- | --- |
| WB-1 | `bignum-truncate` in `level-0/l0-bignum32.lisp` | `2ba65ee2`, [division proposal](../../../tests/wasm/stage1/bootstrap-limb-division/README.md) | Accepted by Steve with audit 159; [acceptance](acceptance-bootstrap-stack.json) explicitly records the behavioural difference |

## WB-1: quotient-only early return

When the dividend's magnitude is smaller than the divisor's and `NO-REM` is
true, the original 32-bit body returns two values: zero and the dividend.
The Wasm branch returns one value, zero, matching the macOS 64-bit quotient-only
entry used by the oracle. When `NO-REM` is false it still returns both values.
The retained cases cover all four operand-sign combinations.

This is an intentional difference from the x8632/ARM body. It is not required
for the arithmetic quotient to be correct, and should not be presented as a
necessary fix for public `TRUNCATE`. It aligns this internal entry's value count
with the selected native oracle. Existing-target forms remain identical under
the retained reader proof; that preservation is a separate claim.

On acceptance, name WB-1 and the one-value/two-value difference explicitly.
Do not describe the integration as containing only representation branches or
source-location changes.
