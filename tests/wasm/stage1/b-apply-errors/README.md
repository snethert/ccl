# APPLY list errors through Lisp handlers

First LL19 prerequisite after subgate 1B. The proposal changes one anchored
emitter expression in the accepted repeated-keyword backend. APPLY's non-cons
list-tail check calls the existing private implicit-condition service with
fatal code 5 and a TYPE-ERROR class mask. The current frame and its roots remain
live while handlers run; the existing unwind machinery restores them on transfer.
No-handler and declined-handler exits keep fatal code 5. Invalid memory spans,
cycles and resource exhaustion keep their existing checked refusals.

The 19 source forms generate 24 modules and 56 cases, run at four placements
(224 comparisons). Native CCL must agree with literal expected values, heap
effects and final special values before target execution. Cases cover non-list
and dotted tails; ordinary and tail APPLY; operand effects; cleanup and cleanup
replacement; dynamic binding visible to the handler and restored outside it;
declining handlers; closures; retained and produced multiple values; 130 values;
a 3,000-step tail chain; proper and empty lists. Two recompiled controls restore
the old refusal or substitute PROGRAM-ERROR for TYPE-ERROR. Both must fail the
first native/logical result check. Native condition classification at the test
boundary was extended to recognize non-function TYPE-ERROR; its first failed
attempt is retained. No target expected value was changed to fit execution.

The complete inherited B, condition, call-error and lazy-loader corpus runs with
the proposal. R6/R6a uses a fresh registered build and reversal in a pristine U1
copy, referencing the accepted unchanged baseline. Shared source stays unchanged.

Run from the repository root:

```sh
python3 tests/wasm/stage1/b-apply-errors/run.py --output /tmp/apply-errors-new
python3 tests/wasm/stage1/b-apply-errors/packet.py verify \
  --packet ../ccl-evidence/2026-09-19-stage1-b-apply-errors-r1 \
  --output /tmp/apply-errors-review
```

The packet's verifier checks source/artifact pins, replays native qualification,
regenerates and executes the positive and mutant compilers, and reruns inherited
execution. Native build reproduction is `native.py --evidence ../ccl-evidence
--work NEW_DISPOSABLE_DIRECTORY --output NEW_DIRECTORY`.

This is an auxiliary proposal, not LL19 qualification. Production condition
objects and slots, restarts, debugger entry, other checked errors, recoverable
stack exhaustion, interrupt masking and collector obligations remain open.
It adds no recovery restart that could resume a malformed APPLY traversal.
