# Audit 189 error-path follow-up

**Accepted:** the user accepted `19ff6839` after [audit 190](../../../../doc/WASM/stage0/claude-review.md)
(`890fde8f`), which found no defect and closed O-134/O-142/O-143/O-145.
The reviewer independently reran the 26,204-case corpus, native baseline and
registered suites (164 FASLs restored), and 782 reader comparisons. Both READY
instances, the dedicated refusal/error run, both startup refusals and nine
additional error-path probes pass. The provenance and BREAK notes need no action.

Audit 189 (`34b130cd`) is imported on `wasm2`. It independently confirms the
host generation refusal, closes O-124 and O-137, and withdraws audit 188's
O-124 finding. Its compiler replay made 26,204 fresh comparisons with zero
failures, zero inherited comparisons and zero sampling. That evidence remains
qualified: none of its five compiler/runtime Lisp inputs changes here.

This follow-up addresses the remaining audit-189 issues together:

- **O-142 / O-134:** wasm32 LOAD routes low-level failure through
  `signal-file-error`, retaining the pathname. Generation exhaustion therefore
  signals `SIMPLE-FILE-ERROR`, which a Lisp `file-error` handler can catch.
  The host still returns errno 12 before any host open or reservation change.
- **O-143:** `%get-frame-ptr` returns NIL on wasm32: this profile has no native
  frame, and `%error` already ignores that context. Existing error dispatch and
  restart code can therefore signal their intended conditions. Native stack
  function lookup returns NIL instead of trying to walk unavailable frames.
  `invoke-debugger` already had a wasm32 branch; its hook is exercised here.
  Native stack walking and an interactive debugger remain outside the profile.
- **O-145:** the budget-consuming witness moves from `postimage.lisp` to the
  separately loaded `refusals.lisp`. Ordinary READY leaves the second runtime
  generation available. Exhaustion tests explicitly opt into consuming it.

The earlier README claim that LOAD's `checked 4` was an uncatchable designed
refusal was incorrect. It was an unhandled `UNDEFINED-FUNCTION` referring to
`%GET-FRAME-PTR`. The final witness reproduces that original error against the
pre-fix runtime, then requires two caught `SIMPLE-FILE-ERROR` conditions with
the right pathname and message. It also checks a missing file and runs a later
ordinary LOAD after recovery. Host opens, generations and session cleanup are
checked in the report. Two fresh ordinary Workers pass 83 returned loads
each with one generation; the dedicated refusal/error run passes 85 returned
loads with two generations. Both required startup refusals pass.

`errors.lisp` exercises the two FASL-header error dispatch codes, errno file
errors, CHECK-TYPE and ENSURE-VALUE-OF-TYPE with STORE-VALUE, package-name and
nickname conflict restarts, export conflicts, a muffled warning, the debugger
hook, and unavailable native stack context. Its portable assertions also run
on native CCL during fixture compilation. The old runtime fails this witness.
The FASL-header checks call the same dispatcher directly; they do not claim a
new malformed-container admission test.

In the author run, only the three changed runtime files and post-image witnesses are compiled
for target execution. The other 79 runtime files and the boot image reuse
pinned compiler products. The runtime archive is relinked once. Native R6/R6a
passes 21,843 tests and restores all 164 FASLs. The two frame edits, added after
that run began, are rebound by identical decoded native code and non-location
data (139 and 628 functions); all other native inputs are hash-equal. The final
reader matrix passes 782 comparisons over 46 files and 17 existing target
profiles. The compiler corpus and unchanged host controls reuse audit 189's
independent execution; they are not rerun for these Lisp error-path changes.

The [result record](../../../../doc/WASM/stage1/load-error-followup.json) pins
one evidence pack, `ccl-evidence/2026-09-27-audit189-errors-r1`, with exact
commands, source identities, original failures and final artifacts. Its
`REPRODUCE.md` is the final review handoff. No Claude process was invoked.

Product Lisp delta: **8 added / 3 removed**. Ordinary READY remains 81 runtime
loads / 82 compiled files, seven product modules / eleven instances. Originals
575/535 and ledger 21/12 are unchanged; no criterion credit. O-134/O-142/O-143/O-145
are closed by audit 190 and user acceptance. Unrelated earlier findings such
as O-136/O-139 remain carried.
