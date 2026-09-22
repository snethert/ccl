# Whole-file hyperbolic entries and numeric execution

**467 original definitions execute and match native (+4), 436 with non-NIL
witnesses (+4).** Comparable admission stays **1,950/2,231**. Files read to
completion rise from **46 to 47 of 57**. This is an isolated proposal over
STAGE1-BOOTSTRAP-ARCH-R1, not an integration or LL15 acceptance.

`l1-numbers.lisp` now compiles whole: **67/68** definitions are admitted. Its
remaining refusal is `%CURRENT-TCR`; no foreign lookup has been fabricated.
The three native non-Windows groups for ASINH, ACOSH and ATANH are excluded
on Wasm, and six ordinary target DEFUNs call the existing float service.
Existing targets read the original groups unchanged. The historical cohort
stays fixed; newly reached definitions after the old stop are reported
separately rather than inflating its numerator.

## Implementation and execution

The existing float module gains operations 38–43 for double and single
ASINH, ACOSH and ATANH. Eight unmodified source files from the same pinned
musl distribution supply these functions and LOG1P; the existing licence
and build remain applicable. `libm/provenance.json` binds each added file.
No host Math function is imported by the runtime. The owner admits the six
new operation numbers and retains its staging, collection and publication
protocol. ATANH at either signed unit endpoint signals division by zero;
ACOSH below one and ATANH outside the unit interval signal invalid operation.
Finite correctly typed inputs and nearest rounding remain the scope.
Enabled inexact/underflow trap modes still refuse, and unchecked operation
keeps the existing convention.

The four original macro-generated `%DOUBLE-FLOAT{+,-,*,/}-2!` definitions
now execute from their whole-file outputs. Twenty rows observe both the
returned result and mutated destination, including signed zero and wide
finite operands. These are the four new original-definition credits.
The 32-bit-only destructive single-float definitions remain uncredited;
the 64-bit native image has no matching mutable-single-object API.

The generated corpus passes **17,064** comparisons at low/high placements,
before and after moving collection. The new hyperbolic callers contribute
**176** native comparisons (maximum observed difference **one ULP**) and
**80** exact condition comparisons. They are caller witnesses over target
branches, not additional unchanged native definitions. The adopted limit
is two ULP; signed zero, exact identities and domain conditions stay exact.
This is a tested envelope, not a global error-bound proof.

The raw module passes **15,360** sampled comparisons across three placements
against independent host Math (maximum observed difference two ULP), plus
**837** directed checks. The original raw entry also reruns all **59,083**
accepted rows at three placements (**177,249** comparisons). Three changed-site
faults are rejected: wrong ASINH dispatch, missing ATANH pole classification,
and the old owner operation ceiling. Native R6/R6a passes **21,843** tests;
all **164** FASLs restore. The final native source comparison permits only
the previously adopted source-location changes. The inverse source proof
and reader checks cover all **17** existing target profiles.

## Replay

From a clean checkout of this commit:

```sh
python3 tests/wasm/stage1/bootstrap-hyperbolic/packet.py verify \
  --packet ../ccl-evidence/2026-09-22-stage1-bootstrap-hyperbolic-r1 \
  --output /tmp/ccl-hyperbolic-replay
```

The verifier re-derives the proposals, runs the whole-file recount, compiles
and executes the numeric corpus, rebuilds libm, reruns raw checks and controls,
and compares deterministic artifacts. Native build evidence is reused only
when all final compiler, arch and CCL source hashes agree.

Eight foreign-name file stops remain, plus the boot kernel-global and TIMEVAL
stops. They need real owner interfaces; this packet does not hide them with
reader stubs. The generic-function immediate layout is still a separate
pending decision. LL15 remains open.
