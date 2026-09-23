# Codex review of Claude's LAP branch

Reviewed `c0b5baa1` and `60901f31` against integration head `96ce04e6`.
The original fixture passes all 24,132 comparisons and 20 structure-scanning
checks. Two additional executed probes find defects; a third issue is a
source-level merge regression. Hold integration until these are corrected.
This review changes no admission, execution or ledger credit.

1. **NIL symbol pointers do not round-trip.**
   `w32-lap.lisp:212` returns any symbol pointer unchanged. D1 distinguishes
   canonical NIL, 77825, from NIL's symbol pointer, 77870. The existing
   `%SYMBOL->SYMPTR` lowering returns the latter. Calling the proposed
   `%SYMPTR->SYMBOL` module with 77870 returns 77870 at both placements;
   it must return 77825. A caller testing the result for NIL would therefore
   get the wrong answer. Native's corresponding round trip returns NIL
   (confirmed on the pinned kernel/image), and x8632-symbol.lisp explicitly
   handles NILSYM before its ordinary symbol check. Recognize that pointer
   first, preferably by comparing with `(%symbol->symptr nil)` rather than
   embedding its address. Retain a compiled round-trip case including NIL.

2. **Nearest conversion can trap before its range check.**
   `wasm32-backend.lisp:4154–4164` admits exponents below 31, then executes
   `f64.nearest` followed by `i32.trunc_f64_s`. Inputs 2147483647.5d0 and
   2147483647.75d0 pass the exponent guard but round to 2147483648, which
   traps. At both placements the underlying exception is
   `RuntimeError: float unrepresentable in integer range`; VSP at TCR+64
   remains 132560 instead of 132096. The installer's restoration assertion
   hides that underlying exception, which the probe records separately.
   Adjacent values 2147483647.49d0 and 2147483648d0 correctly refuse with
   checked code 5. These inputs exceed the native leaf's caller-guaranteed
   fixnum result domain, but contradict the proposal's explicit trap-free
   refusal contract. Check the rounded value before conversion, or use a
   sufficiently restrictive exponent guard, and retain both edge refusals.

3. **Do not overwrite the integrated `CLASS-OF`.**
   The unexecuted definition at `w32-lap.lisp:228` indexes non-misc objects
   by FULLTAG alone. A character therefore selects slot 3 instead of the
   character subtag's slot 75. Under the current Wasm class table, odd
   fixnums also select slot 4 rather than fixnum slot 0. This is a source
   finding, not claimed as an executed LAP case. The integrated definition
   at `w32-prims.lisp:432` already uses TYPECODE with the character case
   and was exercised by generic dispatch. Keep it. Also omit the redundant
   FALSE definition and the proposed `%ILOGCOUNT` already lowered by the
   integrated backend. EQUAL is already integrated; no second definition
   belongs in the merge.

The fixture honestly lists its unexecuted entries. This review does not grant
execution credit to those entries, including slot-id closures or hashes.

## The two implementation concerns

- The generic logical-operation limitation is real. The integrated backend's
  word path requires both operands to be proven unsigned 32-bit; its fallback
  refuses bignums with code 32. Keep that optimization and close the generic
  fallback through CCL's own LOGAND-2, LOGIOR-2 and LOGXOR-2, including their
  fixnum/bignum and arbitrary-width bignum callers. Widening a type proof alone
  would not solve the generic case. Do not duplicate those algorithms in C or
  another WAT loop.
- `build-float.py` compiles the switch embedded in `float.c`, not
  `transcend.c`. The runtime README explicitly describes the latter as a
  provenance copy. Keep one authoritative implementation, preserving old
  text in immutable evidence. Update derivation/build tooling which currently
  reads the duplicate, especially the hyperbolic fixture; do not break its
  documented historical replay by simply deleting a pinned dependency.

The bignum status in the supplied report is stale: the limb implementation
is integrated at `5fd7aaa6`, GCD/cached-dispatch at `a61947f8`, and standard
GF dispatch at `96ce04e6`. The restart support is bounded wrong-type recovery,
not a complete kernel-restart implementation. Exclude the unused GMP-only
functions individually under `#-wasm32-target` after checking their callers;
no replacement GMP implementation is needed. Runtime/thread LAP entries
remain a separate runtime-design obligation.

## Reproduction

Use a checkout of `60901f31` beside the existing `ccl-evidence` store:

```
python3 tests/wasm/stage1/lap-primitives/run.py /tmp/lap-review-run
```

Then run this review's probe from the main checkout:

```
python3 tests/wasm/stage1/lap-review/probe.py /tmp/lap-review-run --output /tmp/lap-review-observations.json
```

The probe reuses the emitted modules and fixture initialization. It writes
separate probe scripts into the execution directory, leaves the original
harness/install scripts unchanged, and records the original exception before
the original restoration assertion. Its success means the reported defects
were reproduced, not that the proposal passed. The observations and hashes
are retained under `tests/wasm/stage1/lap-review/`.

An initial checkout under `/tmp` lacked the sibling evidence store; rerunning
from a sibling checkout resolved that environmental failure. No fixture patch
was needed for the full replay. No native rebuild was repeated for this
review-only change; final source integration still needs its normal R6/R6a
qualification on the reconciled files.
