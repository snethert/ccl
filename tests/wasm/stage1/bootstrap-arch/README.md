# Bootstrap arch macros and numeric execution

Admission rises from **1,895 to 1,950 of the same 2,231 definitions**.
Original definitions executed against native rise from **460 to 463**,
with **432 non-NIL witnesses**, up from 429. This is an unintegrated
proposal for review; it carries no LL15 or other slot credit.

## Implementation

Six missing arch macros follow CCL's x8632 definitions: `%MAKE-DFLOAT`,
`%MAKE-SFLOAT`, `%NUMERATOR`, `%DENOMINATOR`, `IMMEDIATE-P-MACRO`, and
`HASHED-BY-IDENTITY`. The two float constructors allocate initialized D1
objects through the existing checked allocation helper. Native destructive
float stores, copies, and fixnum conversions use the existing rooted float
store and numeric service. Operand evaluation order is preserved, including
collection while evaluating a destination. No new C or JS service is added.

Four other missing macros now give named admission refusals.
`LFUN-VECTOR` and `FUNCTION-TO-FUNCTION-VECTOR` cannot expose the D1 object
as a native code/immediate vector: native callers would interpret its
metadata words as LFUN fields. `%GET-KERNEL-GLOBAL` and
`%GET-KERNEL-GLOBAL-PTR` have no native-kernel addresses on this target.
Their owner replacements remain owed. Each refusal has an explicit case.

The target also gains the native 32-bit `WITH-STACK-SHORT-FLOATS` macro.
Its objects currently use the moving heap; its name does not establish a
stack-allocation claim. The initialized macro caller remains unexecuted:
its call to the full `%SHORT-FLOAT` definition is not dependency-closed.

Actual whole-file numeric admission rises from **147 to 199 of 224**:
94 in `l0-numbers`, 45 in `l0-float`, and 60 in `l0-bignum32`.
All 207 emitted numeric modules assemble. The new original executions are
`%FIXNUM-DFLOAT`, `%FIXNUM-SFLOAT`, and `%MAYBE-MAKE-RATIO`, including
rounding, destination mutation, heap allocation and bignum ratio fields.
Unchanged definitions whose other dependencies are missing receive no
execution credit.

Generated probes cover ratio fields across collection, allocated single
and double floats including signed zero, copying with operand effects and
collection, and both immediate/identity tests. The symbol-identity observer
asserts different architectural answers: x8632/D1 says true for non-NIL
symbols, while the pinned x8664 macro says false. This is a representation
observation, not native-equal raw macro output. Other probe inputs are in
the common domain. The historical signed-zero differences remain explicit.

## Foreign reads and function layout

Two source branches exclude native FFI pointer functions with their
definitions: `%SET-COMPOSITE-POINTER-REF` and `%NEW-GCABLE-PTR`.
They are native pointer/malloc/finalizer operations, not portable memory
services. `l1-utils` and `l1-aprims` now read to completion, making **46 of
57 files**, up from 44. Eighteen additional definitions are reported
separately; the comparable denominator stays 2,231.

[foreign-stops.json](foreign-stops.json) dispositions all eleven foreign
reader stops from audit 157. Nine remain open. In particular, virtual cwd,
sleep, yield and exit require actual owner protocols; suppressing their
definitions or inventing libc entries would not implement those APIs.
Inverse hyperbolic functions need additional qualified libm entries.

[function-immediates.md](function-immediates.md) makes O-5 concrete: use
the final padding word of a distinct funcallable-instance header to root
a vector of CCL immediates, preserving ordinary function objects and their
capture vectors. This is pending the user's decision and is not implemented.

## Verification

R6/R6a passes on the final proposed files: 21,843 native tests, identical
native state, and all 164 FASLs restored. Of the registered build's FASLs,
142 are byte-identical; changed source files have identical decoded code
under the accepted source-location allowance. The two new branches are
definition prefixes `#-wasm32-target`; they select the identical original
forms for every existing target. No whole-file foreign-profile reader
claim is added.

The execution suite compares at low and high placements, with and without
moving collection. It retains every prior executed definition. The new
guards are tested directly; this packet does not claim a full independent
mutant audit. Native build evidence is reused during replay only after
asserting exact compiler, arch and source hashes.

From a clean checkout:

```sh
python3 tests/wasm/stage1/bootstrap-arch/packet.py verify \
  --packet ../ccl-evidence/2026-09-22-stage1-bootstrap-arch-r1 \
  --output /tmp/ccl-bootstrap-arch-replay
```

Development failures and their causes are listed in `development.json`.
The compiler inherits the reviewed, not yet accepted closure proof change.
Neither that inheritance nor this packet changes an acceptance disposition.
