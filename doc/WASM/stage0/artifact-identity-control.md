# Artifact identity control — 14 September 2026

Status: executed; independent review and project acceptance pending.
`STANDING-ARTIFACT-IDENTITY-CONTROL-R1` is retained in
`2026-09-14-artifact-identity-control-r1` through the
[evidence index](../evidence/index.json). This is S0-LL22-a/control, the standing
control following Claude's thirty-fifth audit of the census object witness.

The [runner](../../../tests/wasm/stage0/artifact-identity-control/run.py) feeds the
unchanged production gate two complete synthetic records and 36 defective ones.
Each complete record identifies ten separate files: source, implementation,
test, ABI, template, installed binary, image, host compiler, options and log.
The synthetic inventory explicitly requires these ten roles. The gate's role
policy is inventory-driven; this fixture does not change other inventories'
required roles or the production gate implementation.

| Cases | Required observation |
| --- | --- |
| Two complete synthetic builds | PASS with no diagnostic |
| One mixed/stale file per role, ten cases | Hash mismatch fails the aggregate |
| One absent file per role, ten cases | Missing-file check fails the aggregate |
| One omitted role per build record, ten cases | Required-role check fails the aggregate |
| A duplicate test artifact masks the omitted ABI artifact | Equal artifact count still fails for the missing role |
| Template hash offered for installed module bytes | Installed-binary identity fails |
| Wrong source revision | Source-identity check fails |
| Changed current test contract | Original evidence remains bound to its executed contract and fails current qualification |
| Stale retained-inventory digest | Snapshot-identity check fails |
| Unreviewed build record | BLOCKED, never PASS |

Both builds use exactly the same template bytes but different hand-encoded module
bytes. Complete records with each binary's own hash pass; substituting the other
binary while retaining the first one's digest fails. The test therefore would
catch a checker that relied only on the shared template identity. Neither module
is compiled from the template or instantiated; no materializer correctness or
runtime behavior is asserted.

Every case has a literal expected status, exit code and diagnostic. Defective
inner records keep their synthetic PASS execution labels, so a refusal must come
from the production identity, role, binding or review check. The observations
retain the exact artifact role/path/hash declarations for each case. Shared
payload files remain in the quarantine; missing-file cases point to actual
absent paths, without a mocked file reader or injected gate result.

The verifier rebuilds all synthetic bytes, bounds the retained file set,
reconstructs each input mutation, and re-executes the production CLI. A second
fresh producer reproduces every deterministic input, observation, summary and
slot assessment. Original command paths and timestamps remain retained as such.
The first producer, fresh repeat and verifier pass; there is no unexpected
development failure. Expected defective inputs and their refusals are retained.

## Scope and remaining obligations

This establishes content-hash and required-role enforcement against declared
references. It does not authenticate the source of those declarations, prove
semantic consistency of a newly rehashed build, or validate source-to-binary
derivation. The gate's `test_revision` label is not independently authenticated
by this test; the separate retained test file is checked by content hash. Review
and producer provenance remain necessary. No shared source, production gate or
earlier fixture changes. Native behavior, repeatability, real materialization
and S0-LL22-b's four R6 artifact categories remain separate work.

Only LL22-a's runner registration changes its contract digest. All 34 accepted
records remain current and their prior payload verification is reused. The new
record's production slot gate blocks only for review/acceptance. The scoped
ledger is **34 accepted, 13 missing and one unreviewed of 48**. This packet is
ready for independent review; it is not project-accepted evidence.

The next scheduled deliverable returns to census helper qualification and the
five boundary contracts. When target registry materialization is scheduled,
the plan requires an explicit census node for RESTART wrapper contents supplied
by the target class system; serialization of the key cannot satisfy that node.
