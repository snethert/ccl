# Standard GF dispatch acceptance and integration

550 original definitions execute and match native, 515 with non-NIL witnesses.
Steve accepted audit 161's reviewed packet with “accept and integrate”. The
entire standard-dispatch unit is integrated over the accepted GCD and cached
EQ/EQL dispatch stack. Integration adds no execution or LL15 completion credit. The reviewed gain
contains 53 dispatch cases through fourteen callers (212 comparisons) and four
COMPILED-FUNCTION-P inputs (16 comparisons), 228 comparisons above the prior
corpus.

The runner copies the final reviewed compiler and CCL files, plus the reviewed
collector and pinned-owner population arms. It reconstructs the retained
corpus, rebuilds the production collector to its reviewed binary hash, and
runs 24,144 comparisons through production imports. The owner, node and
population checks run against those installed bytes. Native R6/R6a uses the
reviewed recursive FASL decoder and the final source in pristine U1. The
recount uses CCL's whole-file compiler environment and the fixed cohort.
Its report records the original COMPUTE-DCODE as TARGET-REPLACED: the Wasm
reader excludes that body, and the target Lisp replacement in w32-prims earns
no original-definition credit. The denominator remains 2,231.

Run from the integrated checkout with fresh output directories:

```sh
python3 tests/wasm/stage1/bootstrap-generic-acceptance/run.py native --output /tmp/ccl-generic-native-replay
python3 tests/wasm/stage1/bootstrap-generic-acceptance/run.py verify --output /tmp/ccl-generic-target-replay
python3 tests/wasm/stage1/bootstrap-generic-acceptance/run.py recount --output /tmp/ccl-generic-count-replay
```

The original proposal verifier retains its historical source pins; run it from
`761f1cc1`. These acceptance commands use integrated files directly and work
after integration. They do not regenerate a proposal on top of itself.

## Accepted scope and review observations

The pinned native bootstrap census has 581 initialized GFs and 1,514 methods,
all STANDARD, plus one uninitialized prototype. Standard applicability,
specificity, combinations, next-method and keyword protocols, method lifecycle
and the failure protocols execute through CCL Lisp. Dispatch recomputes
applicability per call. Custom combinations, arbitrary closure method metadata
and the cross-dumped class/global installation are not qualified here.

- O-14: CERROR with a symbol designator loses initargs; a condition object with
  extra arguments does not raise native's too-many-arguments error. The fifteen
  compiled callers do not reach those forms. Those forms have no compatibility
  claim in this unit.
- O-15: INNER-METHOD-FUNCTION is identity for the tested image methods. Closure
  and encapsulation metadata require a separate declared contract.
- O-16: COMPUTE-METHOD-LIST keeps the sub-dispatch flag true, retaining longer
  next-method chains than native. The extra methods are unreachable; tested
  values and traces agree. No equivalent cost is claimed.
- O-17: keep this EQUAL definition and backend ILOGCOUNT lowering when the LAP
  branch is merged. Drop that branch's duplicate ILOGCOUNT; do not add EQUAL
  again. This integration does not merge the LAP branch.
- O-18: one-argument MAKE-ARRAY with a list dimension refuses with checked code
  6. The lowering allocates a simple vector for an integer dimension.

Native stale-last-method behavior, the logical function-bit observer and the
bad-key diagnostic argument-vector difference remain as disclosed by the
reviewed packet. Strong populations use the native three-field shape with a
zero GC link; termination populations remain refused. The condition-CPL
successor and LL15's image/READY join remain open.
