# Projected-image READY join — R11

Executed originals rise from **554 / 519 non-NIL to 562 / 525**. The eight
new originals are MAKE-LOCK, %MAKE-LOCK, LOCK-NAME, GRAB-LOCK, TRY-LOCK,
RELEASE-LOCK and the two object-level acquire/release wrappers. The target
primitive replacements receive no original-definition credit.

This proposal closes the recursive-lock primitive dependencies reached by
`WRITE-STRING` in the READY graph. It implements the approved exclusive,
scheduler-disabled Worker profile. It does not claim a complete stream layer,
shared-memory mutual exclusion between Workers, persistent lock images or
LL15 slot credit. The CLOS projection remains 612 classes and 50 GFs.

## Implementation

CCL's six-field lock object and public lock functions stay in place. Target
branches in `l0-aprims.lisp` and `l0-misc.lisp` replace the foreign lock pointer
with a traced two-element vector: owner token and recursion depth. The token
comes from the executing module's owner-bound TCR, through one compiler
primitive; it is not a rebindable Lisp global. This representation needs no
foreign-resource finalizer or registration in the native system-lock list.

`MAKE-LOCK`, `LOCK-NAME`, `GRAB-LOCK`, `TRY-LOCK`, `RELEASE-LOCK`, the object
wrappers and acquisition-status functions compile in their original file
contexts. The ordinary `WITH-LOCK-GRABBED` expansion handles cleanup.
Acquisition returns T, release returns NIL, and acquisition flags follow the
native protocol. A different owner makes TRY-LOCK return NIL; blocking acquire
signals because this profile cannot wait. Invalid state and recursion overflow
refuse before changing ownership or depth. Release by a non-owner signals
`NOT-LOCK-OWNER`.

The collector admits exactly six lock fields and traces each one. A held lock
and its owner/depth vector may move during collection. The heap-image loader
continues to refuse locks: restoring synchronization state requires a separate
image reset policy. Locks in this unit are constructed after image loading.
The READY classifier follows the native lock-kind dispatch and resolves the
classes already in the image; no native lock pointer or classifier closure is
projected.

## Execution and controls

The READY caller compares with native: public acquisition and release, recursive
try-lock, status flags, two independent locks, collections while held, nested
THROW cleanup, error cleanup, unowned release and invalid flags. Target-directed
cases additionally inspect owner/depth transitions and refuse foreign ownership,
malformed state and overflow with state preserved. The collector checks all six
fields through movement, wrong counts and truncated storage at both placements.
A separate compiled omission demonstrates the field-count check is required.

The larger closure exposed the probe registry's 4,096-entry bound. Validation
now allows 4,352 entries, with matching pre-installation and installer checks.
The registry still begins at 4,096 and ends below NIL at 77,824; an explicit
bound prevents overlap. The binding table's independent capacity is unchanged.
The original overflow refusal is retained.

R10's scalar-complex lowering and checks remain in this stacked proposal, as do
the low-bit-first raw bit-vector observation, image admission controls, generated
admission-guard omission and native-state restoration. Shared compiler, runtime
and CCL sources remain unchanged pending review. Native R6/R6a qualifies the
complete proposed files; the validation capacity change also runs through the
full regression corpus.

The first lock witness correctly refused at `LOCK-NAME`: its `REQUIRE-TYPE`
reached the missing lock classifier. The retained failure and diagnostic calls
identify that boundary. The corrected initializer installs the classifier into
its private class-table copy. The scheduler file still stops at `sched_yield`
after the selected public lock definitions; it is recorded, not counted as a
complete file or silently ignored.

## Results and retention

The full proposed compiler/runtime passes 26,048 fresh regression comparisons,
including the collector-owner checks. Four cold boots at both placements,
with and without movement, pass 50 support comparisons and 1,306 collections.
Twenty boot refusals, 31 image admission checks, eight lock layout rows and the
lock-count omission pass. The registry capacity/overlap controls refuse without
memory writes. R10's sixteen scalar-complex rows and four omissions still pass.
Fresh R6/R6a passes 21,843 native tests and restores all 164 FASLs, bound to all
35 final compiler/CCL proposal files.

The READY census is 797 modules, with missing edges reduced from 57 to 55 and
50 indirect modules remaining. Neither a stream-layer completion nor an LL15
acceptance follows from that conservative dependency census.

The complete author run is retained separately from development continuations.
Native qualification is reused only against identical final proposal sources.
The session key now explicitly includes all three source files read by the
lock derivation, in addition to the derivation and compiler/driver identities.
Original failed compiler inputs, the registry refusal and the lock classifier
failure are retained. No execution is claimed during retention.

## Reproduce

```sh
python3 tests/wasm/stage1/ready/packet.py verify ../ccl-evidence/2026-09-24-stage1-ready-join-r11 /private/tmp/ccl-work/claude/ready/verify
```

Native qualification can be rebuilt independently with `native.py` under a
managed `ccl-work` output root. The saved native compiler image is review
tooling, never the port's heap. Historical packets replay at their recorded
source revisions. Replacement attribution, startup callback dispositions and
the remaining unresolved/indirect READY edges are still owed.
