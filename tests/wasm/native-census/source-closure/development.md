# Development record — 14 September 2026

This is a diagnostic collection deliverable, not an LL15 acceptance envelope.
Original files under the development archive retain their recorded statuses.
The archive preserves all incomplete/failed native sessions and their captures,
logs, commands and runtime source snapshots. Superseded successful bulk-survey
captures retain hashes and run records; their raw captures are unnecessary to
the final result and are listed separately. No failed capture is omitted by
that selection. Small successful probes and repetitions are retained.

The development sequence corrected these collection/checker errors:

- The first wrapper installation encountered U1's kernel-redefinition guard.
  The disposable process now dynamically binds the existing warning policy
  during installation/restoration. Main-checkout definitions are never changed.
- The first general representation/expansion recorder recursively printed large
  source trees and overflowed on the Chinese encoding file. The final IR is an
  iterative flat graph; macro records retain identities and locations rather
  than recursively serializing arbitrary expansion trees.
- Early data-description attempts contained a parenthesis error, attempted to
  store even equal values into existing constants, and treated macro parameter
  symbols as layout leaves. Their failed sessions and source snapshots remain.
- Early native sinks returned refusal guards for compiler helper functions.
  Local macro expanders must execute during compilation. Final native mode
  forwards all native compilation unchanged; only Wasm file-function results
  receive refusal guards. The largest native backend file also exceeded the
  original 90-second limit; its timeout is retained and the final bound is 600
  seconds. All 164 final native sessions completed.
- The first native smoke check referred to an image-unbound FASL constant. Its
  replacement is the pinned U1 opcode 35, not an invented runtime value.
- Initial graph checks assumed three CALL operands. NX1-%FUNCTION constructs
  two, and U1's native CALL handler makes the third optional. Both actual forms
  are now admitted. The first all-file output join also required every function
  to pass through Lisp pass 2; native LAP disproved that assumption. Its 257
  output records now remain explicitly unjoined. The rejected analysis log is
  retained; this change claims no new LAP coverage.
- The layout-probe source initially had one extra closing parenthesis. Its
  original source, failing native log and successful correction are retained.
- The first combined probe check demanded byte-identical native diagnostic
  previews. Eight second-operand print previews contain heap addresses. Both
  originals and the original refusal log are retained. Repetition now permits
  only those printed-address differences in that diagnostic field; every graph,
  observation, function identity, native code byte and other field must match.
  Target and callback raw captures are byte-identical. This is not normalization
  of source, FASLs or native code. The unwrapped native comparison independently
  reproduces 3,168 output code bytes across 26 functions.

Some early Python checker exceptions were returned only in the interactive
tool transcript: the initial native-corpus controls looked in the target-only
capture list, and the independent source-table regex missed trailing whitespace.
No original on-disk traceback or pre-edit checker snapshot exists for those
interactive invocations. This note discloses that retention limitation; it does
not manufacture a failed run record or claim the limitation satisfies the
standing original-evidence rule. Native execution failures have their original
files. The final retained verifier recomputes the result under the final checker.

No shared compiler/kernel source, input FASL, production gate, inventory,
historical envelope or previously accepted record changed. Fresh source and
bootstrap copies contained 980 files before and after observation, all identical.
The retained image and temporary compiler environments are observation inputs
only; implementation must still start from pristine U1.
