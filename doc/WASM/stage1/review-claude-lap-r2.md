# Codex second review of Claude's LAP branch

Reviewed `27f5bc02` over `964eb005` and `7f6a4208`, rebased onto
`71026330`. **No new defect found. Recommend acceptance and integration,**
with the documentation corrections below and final R6/R6a qualification.
This review changes no admission, execution or ledger credit.

The unchanged fixture passes from the detached review checkout: 25,772
comparisons, 146 checked refusals, 20 structure-scanner checks, 28 population
checks and 40 collector-owner checks. No native R6 rebuild was repeated for
this review; final integration still needs its normal R6/R6a qualification.

## Earlier findings

All three are closed:

- `%SYMPTR->SYMBOL` recognizes `(%symbol->symptr nil)` before the ordinary
  symbol test. The compiled round trip includes NIL, T, a keyword and CAR.
- Float-to-fixnum conversion admits only magnitudes below 2^30 before
  rounding or truncation. Rounding can therefore reach at most 2^30,
  within the signed conversion's domain. The following fixnum-range check
  handles both limits. The former trapping inputs now refuse with checked
  code 5 and restore thread state. The asymmetric negative boundary,
  including the even tie at -536870912.5d0, is tested correctly.
- The proposed `CLASS-OF`, `FALSE` and `%ILOGCOUNT` definitions are removed;
  the integrated implementations remain authoritative.

## Implementation concerns

Generic logical calls preserve the proven unsigned-word path and the runtime
fixnum path. Other integer operands are folded through CCL's existing
`LOGAND-2`, `LOGIOR-2` and `LOGXOR-2`. The operand frame stays rooted, and
ordinary internal-call frames protect intermediate results. There is no
second bignum algorithm and no recursive call back into CL:LOGIOR.

`float.c` includes the single switch in `transcend.c`, and `build-float.py`
copies that include. I rebuilt the predecessor's embedded-switch source and
the reviewed source with the same build helper and musl inputs. Both binaries
hash to `dc0db90ec8bf24abc6991ad6e40b6d3b66ff96669cf2c58ddadff39a398db404`.
Historical packets retain their source-commit replay contract.

## Additional execution probes

The review driver adds four source forms, compiled by the unchanged reviewed
compiler and compared with the fixture's native CCL oracle. Forty operand
triples include fixnum boundaries and seeded signed integers up to 1,100 bits.
They exercise three-operand AND/IOR/XOR, unary and zero-argument cases,
collection during every operand, evaluation order, and allocation retry with
a full semispace. Six further rows put a non-integer in different operand
positions. The harness retains its original thread-state restoration checks.

Without allocation retry, the 86 ordinary/effect/error rows pass 344
comparisons with 1,440 collections during calls. My initial full-heap probe
then refused with checked code 6: the fixture compiles ordinary library
functions with `*b-allocation-retry*` NIL. That is the profile's expected
allocation refusal, not a defect. The additional pressure run enables the
existing retry mode while compiling those library functions. It passes all
26,276 comparisons: the inherited 25,772 plus 504 new comparisons (126
native rows at both placements, before and after movement). That run records
250 allocation-retry collections in total, and all 88 collector/owner checks
still pass. The ordinary-call fallback, including intermediate results,
therefore survives allocation retry as well as explicit operand collections.

## Small documentation corrections for integration

- The fixture introduction still says 59 entries; three withdrawals leave 56.
- The runtime README still calls `transcend.c` a provenance-only duplicate.
  It is now a build input.
- The fixture's boundary prose conflates nearest and truncating conversion.
  For example, 536870911.5d0 refuses for nearest but truncates to 536870911.
  The actual test lists correctly distinguish them.

Unexecuted entries remain explicitly uncredited, including the slot-id
closures and the hashes without an oracle. This review does not claim those
entries or the startup integration are complete.

## Reproduction

Use a checkout of `27f5bc02` beside the existing evidence store:

```
python3 tests/wasm/stage1/lap-primitives/run.py /tmp/lap-r2-review
```

From the checkout containing this review, run the additional probes:

```
python3 tests/wasm/stage1/lap-review/logical-probe.py REVIEW_CHECKOUT /tmp/lap-r2-review /tmp/lap-r2-logical --retry
```

The probe changes only a copied driver. It preserves the reviewed compiler,
runtime and original fixture files. Review hashes and counts are retained in
`tests/wasm/stage1/lap-review/record-r2.json`.
