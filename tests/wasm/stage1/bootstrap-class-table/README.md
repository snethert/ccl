# Target allocation and publication of class cells

This proposal adds protocol execution, not credit for additional original CCL
functions. The original-definition headline remains 550 executed / 515 non-NIL.
Admission is not recounted and no LL15 slot credit is claimed.

In default-off class mode, CCL's PUTHASH call (including SETF GETHASH expansion)
uses an ordinary Lisp wrapper and the accepted strong EQ store leaf. The
wrapper preserves PUTHASH's optional-default/value calling convention and
refuses read-only tables. No new hash algorithm or runtime service is added.
The leaf remains fixed-capacity and synchronous. Full tables still refuse;
this work adds neither growth nor arbitrary hash-table tests.

CCL's unchanged FIND-CLASS-CELL creates an absent class cell through its own
MAKE-CLASS-CELL macro, allocates it in the moving target heap, and publishes it
with SETF GETHASH. The scenarios also replace every existing class-table cell
with a newly allocated cell, collect, resolve all names, and construct a
condition with inherited slots and default initargs. The native oracle performs
the same operations. The fixture compares values, heap graph identity and
fields, root/binding state and TCR restoration.

The classes themselves remain the finalized native-projected class graph.
Reallocating its cells is not a claim that the port can cross-dump or bootstrap
that graph. The image roots/READY join, class finalization, and implicit-error
registry retirement remain open.

SIGNAL now resides in a `#+wasm32-target` definition in l1-readloop.lisp; its
whole definition is removed from w32-prims.lisp. The fixture reads this exact
source definition because an earlier foreign lookup still stops whole-file
reading. It does not substitute a hand-written caller body. BREAK-ON-SIGNALS
and the debugger remain outside the completed protocol.

Run the proposal and native qualification from this checkout:

```
python3 tests/wasm/stage1/bootstrap-class-table/run.py /tmp/class-table
python3 tests/wasm/stage1/bootstrap-class-table/native.py /tmp/class-table-native
```

A newly named raw cell is looked up and passed as a class object to
MAKE-CONDITION. Native CCL's separate subtype cache does not learn an alias
from a raw cell store. This unit does not replace SET-FIND-CLASS, DEFCLASS or
class finalization. Rebuilding cells for existing names preserves their classes.

The development record retains the first graph-encoder failure (a fixture
input used the method-metadata slot) and the native subtype-cache refusal for
a new raw alias. Both corrections are in the caller/fixture; neither prompted
a compiler or service change.

Two later fixture failures are also retained: the old GET-only projection
hard-coded the wrapper as read-only, and the selected SIGNAL definition was
initially read in the fixture package. The final projection reads the native
read-only flag and the source reader binds CCL. The final clean run, not the
scratch diagnosis, is the qualification record.

Unchanged service binaries are reused from the accepted condition-system packet
only after verifying its packet and binary digests and every pinned runtime
source. Compiler, Lisp caller and native oracle execution are rebuilt. The
integration of the preceding packet is an identity check, recorded separately.

Retained-packet replay (rebuilds compiler, callers and oracle; reuses pinned
native qualification and unchanged runtime binaries):

```
python3 tests/wasm/stage1/bootstrap-class-table/packet.py verify \
  --packet ../ccl-evidence/2026-09-23-stage1-class-table-r1 \
  --output /tmp/class-table-replay
```
