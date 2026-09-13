# Required-child command control — 13 September 2026

S0-LL01-b has executed successfully, was reviewed by Claude's thirtieth audit at
`9285ee40` without defect, and awaits project acceptance. Packet `STANDING-CHILD-COMMAND-CONTROL-R1` is in the
[evidence index](../evidence/index.json). This follows Claude's twenty-ninth
audit at `8e8cf13b` and the alternating schedule in the [plan](plan.md).

The [fixture](../../../tests/wasm/stage0/child-command-control/README.md) executes
the existing native-baseline producer's `run()` and `command()` functions.
A private invocation adapter supplies synthetic child commands and shortens
only the selected timeout. The original subprocess call, marker checks,
exception handling, partial-run accounting, report writer and aggregate exit
status are exercised without source changes.

| Command stimulus | Cases | Required aggregate outcome |
| --- | ---: | --- |
| Complete synthetic workflow: all 26 commands | 1 | Exit 0, PASS, two completed synthetic runs |
| Child exits 23 | 3 | Exit 1, FAIL, exact step and exit diagnostic |
| Child kills itself with SIGKILL | 3 | Exit 1, FAIL, exact step and return code −9 |
| Child blocks until the one-second timeout | 3 | Exit 1, FAIL, exact step in the timeout diagnostic |
| Child exits zero without its required marker | 1 | Exit 1, FAIL, exact missing-marker diagnostic |

Each of the three process failure modes runs at `run-1-kernel-build`,
`run-1-clean-rebuild` and `run-2-tests`. This covers an early build command,
a marker-bearing rebuild command and the last required command after a
successful first cycle. Each failing child first produces its normal synthetic
outputs and marker where applicable. Neither a marker nor an earlier successful
cycle conceals the subsequent command failure. No later command executes, and
the failed aggregate retains `gate0_status: NOT_ACCEPTED`.

The oracle reads the production command records and logs independently of the
adapter. It checks the literal expected step prefix, original/effective
invocation correspondence, timeout selection, log hashes, real terminal modes,
exact diagnostics, aggregate exit, report status and partial-run count. Every
original failure log and partial output is retained in `quarantine.zip`.

## Evidence boundary

Only subprocess behavior is real execution in this fixture. The source archive,
bootstrap, FASL, kernel, image and test summaries are synthetic stimuli; no CCL
or Wasm code runs. The actual outer envelope is CONTROL EXECUTION for S0-LL01-b.
The unchanged inner producer still writes its native evidence label and scope;
the surrounding quarantine, explicit synthetic input revisions, configuration
and command logs identify their actual origin. They are never promoted to
native execution or project acceptance.

The adapter changes argv, not the failure policy. Original argv and required
markers are retained alongside the actual child argv. The production timeout
is shortened to one second only for the three timeout stimuli. Each child has
no descendants; this does not qualify process-group or descendant-tree cleanup.
Initializer handling remains a separate S0-LL01-a obligation. Other runner
implementations are outside this packet's scope.

## Verification and ledger

The first producer run and the fresh verification replay both pass: one complete
aggregate and ten rejected child-command controls. All eleven semantic
observations agree exactly. Original commands, reports and logs for both runs
are retained; their timestamps, elapsed times, absolute paths and dependent
hashes are execution-specific, with no raw-byte repeatability claim. Eight
direct source pins include the production runner, gate and binding tool, all
unchanged. No producer or replay execution failed unexpectedly.

Only the S0-LL01-b runner/status fields change in the inventory. All 31 accepted
record bindings remain current; prior runtime-payload verification is reused.
The new record passes the production gate's content and artifact checks, with
review/acceptance as its only remaining reason. The scoped ledger is **31
accepted, 16 missing and one unreviewed out of 48**. The accepted aggregate is
unchanged. No native build or archive-wide payload scan was performed.

The next alternating deliverable resumes the census: qualify or bound remaining
helper/type/object paths, resolve the five boundary stops and expand source
traversal. Shared compiler and upstream kernel changes remain outside this
control's scope.
