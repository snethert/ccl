# Audit 180: SET-PACKAGE and lock integration

The user instructed “fix, accept and integrate” after Claude's no-defect audit
`5fdf9884`. The two proposals are accepted together. Seven product files equal
the reviewed proposal bytes. `check.py` binds both immutable packets, all 42
qualified compiler/CCL inputs, the runtime, and the review. Native R6/R6a
(21,843 tests, 164 restored FASLs), 51 reader comparisons and 26,048 compiler
comparisons are reused by exact identity. No criterion credit is added.

`run.py` uses the integrated product in a clean U1 extraction and reuses only
the reviewed witness drivers. The product source and runtime providers read
the product directly. All driver inputs are bound before execution, checked
again afterward and verified at retention, including the retention driver.

## Audit answers

**O-88.** The 33 controls establish checked refusals, preserved lock state and
cleanup; they do not claim 33 independently killed clauses. Only the three
named state/type deletion mutants have that author claim. The empty unlock
and promotion checks select `NOT-LOCKED`: they are reachable for the valid
empty `(0,0)` state, but are redundant for refusal because the following owner
check also rejects owner zero. Removing either check cannot admit this input.
Owner = self with depth zero is instead rejected by the earlier coherence
check. Thus these two guards are defensive for admission while preserving
the intended condition reason; this early image does not distinguish condition
classes. The vector-kind check is also defensive against the subsequent checked
SVREF. The depth-bound rows establish checked refusal and preserved state,
but independent deletion kills have **not** been demonstrated: arithmetic
overflow may supply another refusal. They receive no isolated-clause claim.
The reviewer's read-under-write deletion was killed by actual admission.

**O-89.** The historical SET-PACKAGE execution identity binds earlier versions
of `packet.py` and `provenance.json`. This is an acknowledged retention gap,
not retroactively repaired execution evidence. The packet's retained final
source snapshot equals the committed files, and audit 180's committed-driver
replay reproduced the artifacts and observations. The original packet remains
unchanged. This separate integration record binds the final execution inputs
before and after running and verifies them again at retention.

**O-90.** The two pre-existing duplicate backend definitions are excluded from
this byte-identical integration. Their cleanup belongs to a separate compiler
proposal and qualification identity.

**O-91.** Blocking lock operations remain explicit single-Worker refusals.
The native promotion/unlock timeout has no pass credit. Native-handle revival
and its startup consumers remain open.

```sh
python3 tests/wasm/stage1/loader-prefix-acceptance/check.py
python3 tests/wasm/stage1/loader-prefix-acceptance/run.py \
  /private/tmp/ccl-work/codex/loader-prefix-integration/run
```

The ordered build completes l0-aprims and stops at GENERAL-AREF2 in l0-array.
Production counts remain 0/0/0, accepted originals 575/535, ledger 21/12.
