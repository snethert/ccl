# Termination exclusion: empty-state compatibility correction

Auxiliary follow-up to audit 135 F1. No shared compiler/runtime changes,
integration, acceptance or LL15 credit. R1 stays immutable and replays from HEAD.
Use this packet's derived entries for any later integration, not R1's entries.

## Correction

Only registration is excluded. With registration refused and image admission
requiring empty termination state, cancellation finds nothing, lookup finds no
function, and draining finds no queued work. The three replacements now return
exactly one NIL value, matching native CCL. Returning NIL does not claim that a
registration was successfully removed or a callback was run.

The automatic hook remains inert when disabled. Its existing invalid-enabled
mode refusal is now explicit in that entry; it no longer depends on the draining
entry to signal. This preserves the R1 guard behavior while letting callers
invoke the empty drain normally. The image guard is byte-identical to R1 and
still refuses enabled scheduling or nonempty termination state.

The source caller at `level-1/l1-streams.lisp:5702` cancels before its dirty-stream
flush and descriptor-close operations. Other I/O paths also drain the queue.
The source excerpt and its cancellation/flush/close order are retained.
The generated `termination_fd_close_path` exercises that selected order through
separate flush and close functions, with the close recording the flush's effect.
A second caller executes it from UNWIND-PROTECT cleanup. These are executable
lifecycle models, not implementations of fd streams, buffers or host file I/O.

## Independent native oracle

The generated calling corpus's native reference now binds the three private
fixture names directly to the untouched native CCL functions. It no longer
compiles the proposed empty-state bodies as the reference for those operations.
Native state is asserted empty before running the scenarios. Registration and
the invalid-enabled automatic mode keep their explicitly chosen Stage 1 error
oracle; native CCL itself still supports registration.

A separate native probe checks 21 exact one-NIL-value answers: cancellation
with omitted, NIL and explicit callback arguments, lookup over five object
kinds, and an empty drain. It then exercises real file write/close, first with
untouched native functions and then with the corrected replacements installed
at the real CCL symbols. Both ordinary WITH-OPEN-FILE and an explicit CLOSE in
UNWIND-PROTECT during a transfer flush the content and close the stream. All
bindings are restored in cleanup. CLOSE :ABORT T is not qualified by this test.
The initial exploratory abort-close expectation failed in native CCL before any
replacement was installed; that failure is retained, not treated as a port bug.

The generated corpus has 21 modules and 19 scenarios at two placements (2 MiB
and 2 GiB), before and after collection: 76 native comparisons and 38 collections.
R1's registration, operand, handler, cleanup, unhandled-boundary and full-TCR
checks remain. The unchanged admission guard passes its 64 checks and seven
remove-one-check faults. The three original recompiled Lisp faults still fail.
Four new compiled controls restore each incorrect refusal or make cancellation
return T. The cancellation refusal is tested on the close path itself and fails
before the flush, reproducing F1. Fourteen controls total.

R6/R6a and the collector binary are reused by exact hash. Every proposed and
fault module is rebuilt through the unchanged compiler. The original 106 pins
are reasserted before and after execution. No accepted packet is edited.

## Remaining image work

The owner must install the corrected bindings at the real CCL symbols, disable
scheduling and bind admission to actual image state before READY. The guard's
trusted slot mapping is not a global root census. Nonempty state must still
refuse; it cannot be erased to justify NIL answers. Finalization remains owed
in Stage 2. General EQL/EQUAL and other LL15 dependencies are unaffected.

```sh
python3 tests/wasm/stage1/termination-exclusion-review/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-20-stage1-termination-exclusion-review-r1 \
  --output /tmp/ccl-termination-review-replay
```
