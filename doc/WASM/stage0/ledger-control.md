# Project ledger and decision control — 14 September 2026

Status: executed; reviewed by Claude's fortieth audit at `fdb6f0b5` without
defect; awaiting user acceptance as S0-LL24-a/control. The production checker is
[`check-project-ledger.py`](../tools/check-project-ledger.py); the
[policy file](ledger-policy.json) names the canonical ledger, current status
projection, separate dated history, accepted baseline and criterion decisions.

The checker reads the real project metadata and retained evidence envelopes. It
requires one current accepted-aggregate index entry, unique active result keys,
correct evidence classes and contract bindings, and a status row derived from
the ledger's actual required variants. Missing and unreviewed work must remain
in the result, including unresolved census obligations and prerequisites. A
passing checker result does not mean Stage 0 passed: the output names the
project gate separately as BLOCKED.

The 35 previously accepted result objects are compared in full with the pinned
accepted baseline. Removing a record or changing its scope, configuration,
execution fields, assertions or artifact references fails. Their runtime
payloads are not rescanned. New submissions have their retained artifact bytes,
required roles and assertion coverage checked. A current aggregate must contain
exactly the accepted active records, so a pending execution cannot become the
accepted index merely by moving a pointer.

The recorded production-role decision is checked against its actual old/new
inventory snapshots. Its complete change list and both contract identities must
match, and its authorization, dated rationale and snapshot hashes are required.
The current criteria must equal the authorized result. Status/review bookkeeping
and runner registration are excluded from that criterion comparison; runner
identity remains covered by ordinary contract bindings. A control changes an
accepted runner and confirms that its old evidence becomes incompatible.

These checks enforce recorded authorization and scope. They do not authenticate
that a human truly spoke a quotation, prove the truth of arbitrary prose or
replace adversarial review. The user supplied the authorization recorded in this
unit. The current status row is checked mechanically; historical narrative is
separate, with an exact dated-entry link.

## Controls and repeatable inputs

Thirty-one controls damage the input bytes while executing the same production
assessor. They cover competing authorities, duplicate or stale status/index
records, false completion, omitted census gaps, changed accepted scope, missing
accepted records, class substitution, failures/skips, missing execution metadata and assertions,
unapproved criteria, removal of R6 or a required test, missing authorization,
corrupt decision snapshots/change lists, broken history, evidence digests and
required artifact roles. Altered current envelopes receive corresponding current
reference hashes, so scope-preservation cases reach the actual comparison with
the unchanged accepted baseline rather than stopping at an unrelated hash error.

The fixture uses a hash-pinned snapshot of the actual project just before its own
result was published. It includes LL24 runner registration but no LL24 execution
record; the observed project gate is 35 accepted, twelve missing and one
unreviewed. Freezing this input prevents the newly published LL24 result from
changing its own test. Fresh runs reproduce the observed ledger and all control
results from those retained bytes. The production CLI separately checks the
final live ledger after publication.

Mutants use explicit in-memory changes to input bytes and memoized reads of
unchanged retained files. They do not replace the assessor or inject its return
value. Changed-input paths and literal expected refusals are retained. This is a
metadata control, with no compiler or runtime execution claim.

Run from the repository root:

```sh
python3 tests/wasm/stage0/ledger-control/run.py \
  --output /private/tmp/ccl-ledger-control
python3 tests/wasm/stage0/ledger-control/run.py \
  --verify /private/tmp/ccl-ledger-control
python3 doc/WASM/tools/check-project-ledger.py
```

The first development run rejected a scope mutation at the earlier hash check:
the test had changed the pinned baseline as well as the offered current input.
That original failure and its source are retained. The corrected test keeps the
baseline fixed and offers a distinct changed current envelope, which fails the
intended scope check. Later successful runs add authority/runner/census controls
and freeze the pre-publication input snapshot; the final run adds required
execution metadata validation and its omission control. These are disclosed test setup
changes, not reconstructed successes.

After publication, Stage 0 is **35 accepted, eleven missing and two unreviewed
required slots out of 48**. LL23-a and LL24-a await independent review; the
production-role enhancement also awaits its own review. Existing acceptances,
S0-LL23-b's frame evidence and remaining census work are unchanged.
