# Evidence-kind standing control — 13 September 2026

S0-LL03-a is executed; [Claude's twenty-eighth audit](claude-review.md) at 23738a1c found
no defect, and project acceptance remains the user's decision.
Packet `STANDING-EVIDENCE-KIND-CONTROL-R1` is indexed in the
[evidence index](../evidence/index.json).

The [runner](../../../tests/wasm/stage0/evidence-kind-control/README.md) invokes
the unchanged production gate CLI on a fixed synthetic inventory. Its three
evidence classes require COMPILER-GENERATED TARGET EXECUTION, HAND-BUILT WASM
EXECUTION and CONTROL EXECUTION respectively. Each has six variants: C, C4 and B
in full and reduced profiles. Eighteen distinct payload identities label the
inputs. All inner records remain under `quarantine/`, including the positive
records shaped like compiler-generated evidence. They claim no actual Lisp,
compiler, Wasm or engine execution.

| Supplied input | Cases | Required production-gate outcome |
| --- | ---: | --- |
| Complete inventory, original and reversed order | 2 | PASS |
| Hand-built record offered for generated acceptance, each candidate/profile | 6 | FAIL: wrong evidence kind |
| Synthetic control record offered for generated acceptance, each candidate/profile | 6 | FAIL: wrong evidence kind |
| Another candidate or profile replaces the required one | 2 | FAIL: duplicate and missing variant |
| Substituted required import, absent substitution disclosure, skipped execution | 3 | FAIL: substitution/skip or missing disclosure |
| Failed generated, hand-built and synthetic records | 3 | FAIL: failed execution and non-passing record |
| Mismatched payload hash | 1 | FAIL: mismatched artifact |
| Unreviewed generated-shaped record | 1 | BLOCKED: unreviewed |

Every case checks exact CLI status and diagnostic text. In the wrong-kind cases,
the complete labelled record comes from the other class; only its offered
requirement, assertion identity and contract binding change. Its evidence kind,
candidate/profile, fixture and artifact hashes stay intact. The failed-execution
cases change only status: the runner explicitly checks that the other labels
remain unchanged. The retained observation identifies the subject and its labels
even when the gate rejects it. Substitutions and skips stay visible in both the
original input and the observation.

## What this establishes

The gate refuses a declared hand-built or synthetic evidence class for a
compiler-generated requirement, refuses a missing required candidate/profile,
and retains classification independently of PASS/FAIL. Declaring a successful
test does not bypass kind, artifact, substitution or review checks.

This is a metadata control, not a compiler-origin detector. The gate cannot infer
from arbitrary payload bytes whether a declaration is truthful. Positive
synthetic records with a complete expected schema pass deliberately; their
quarantine and explicit synthetic origin prevent treating this control run as
production execution evidence. Actual generated-code acceptance still requires
the declared path to execute, its artifacts to be examined and independent review.
No compiler-generated acceptance is gained here. The actual outer envelope is
CONTROL EXECUTION for the unchanged S0-LL03-a assertion.

## Verification and ledger

The first producer run and a fresh repeat both pass: two positive inputs,
21 FAIL controls and one BLOCKED control. All 54 deterministic files reproduce
byte for byte. The only three differing files are the command log, run record
and outer results envelope, whose differences are the new output path,
timestamp and resulting command-log hash. Those original records and the exact
comparison are retained without duplicating the remaining payloads. The retained
verifier reconstructs the base, re-executes all 24 cases, checks classifications
and validates the outer envelope against the real slot. No producer or control
execution failed unexpectedly.

Registering the runner changes only S0-LL03-a's semantic contract. All 30 accepted
records retain valid bindings; their runtime-payload verification is reused.
The retained run's inventory uses literal non-ASCII characters where the final
file escapes two characters; parsed content and contract identities are identical.
The actual new envelope passes every production-slot check except review and
acceptance. The scoped ledger is **30 accepted, 17 missing, one unreviewed out of
48**. The prior gate result and accepted aggregate are retained unchanged. No
archive-wide scan, native build or runtime fixture rerun is needed for this control.

This follows [Claude's twenty-seventh audit](claude-review.md) of the target helper
slice. The next alternating deliverable resumes the census: qualify or bound the
remaining helper/type/object paths, then resolve the five source boundary stops
and extend traversal.
