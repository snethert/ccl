# Native condition construction and class-cell lookup

This proposal adds ten condition-protocol callers; it does not add their
helper functions to the standing original-definition headline. The complete
existing execution corpus and the new callers run against the native oracle.
The final counts are retained in `summary.json`. No LL15 credit is claimed.

The default-off class mode now resolves names through CCL's real FIND-CLASS
and CLASS-TYPEP. The fixture projects the pinned native image's finalized
`%find-classes%` entries as native-shaped class cells in an ordinary EQ table.
The accepted hash service supplies GET, including relocation rehashing.
The table census is not construction coverage for every class.
There is no eleven-name vector or `condition_class_cells` import. A test
replaces a class cell, collects, constructs through its name, and restores the
cell; lookup must observe the replacement.

MAKE-CONDITION, CONDITION-ARG, MAKE-INSTANCE, allocation, initialization,
default initargs, initarg checking and slot access execute CCL's Lisp bodies.
The file compiler supplies their file-local environments. Constructor method
bodies are extracted with CCL's PARSE-DEFMETHOD; the fixture gives those method
functions callable entries in the projected generic functions. Reader methods
use SLOT-VALUE over the native slot definitions. Slot initforms and type
predicates are compiled as Lisp thunks. Their callable metadata is compared
with native compilations of those thunks, rather than the metadata of native
LAP or optimized predicate closures they replace. This projection does not
transport arbitrary captured native closure environments.

The owner image includes the real initialization invalidation table, wrapper
and class globals, and error-format strings. These are dependencies of CCL's
initialization code, not substitutes for its operations. Generic functions
receive their dcode through the accepted COMPUTE-DCODE implementation.

SIGNAL and ERROR accept object, symbol and string designators, with arguments
and APPLY. Indirect SIGNAL uses the same target Lisp entry. CERROR retains
symbol initargs; its existing target restart implementation is reused. Typed
readers dispatch through real generic functions. The scenarios cover inherited
slots, default initargs, duplicate keys, invalid and odd initargs, mutation,
restarts and cleanup, and a condition outside the old 28-class registry.
Every case runs before and after relocation at both memory placements, and
calls also collect internally. Values, projected object identity and mutation,
roots, bindings and the complete TCR preservation contract are checked.
After that complete comparison, the execution record stores canonical graph
digests and node counts. Full expected graphs remain in the native record;
this avoids repeating them in every target result and exceeding Node's maximum
JSON string size.

Default-mode library modules and class-mode modules remain distinct in this
fixture. The owner selects the corresponding bindings before constructing an
input graph. This prevents the new class-table dependency from silently
removing legacy definitions from the execution measure. Shared runtime,
compiler and CCL files are unchanged by this proposal.

## Scope still open

* The class table is projected from the pinned native image. The port's own
  cross-dumped table and READY installation remain owed.
* Classes must be finalized with initialized CPLs. Class redefinition and the
  UPDATE-CLASS/COMPUTE-CPL closure are not qualified here.
* Explicit construction, readers and signalling use the class path. Compiler
  generated implicit failures still use the old condition allocation registry;
  its removal is still required before the mode becomes the only path.
* The class-table GET adapter admits strong EQ tables. General hash-table
  creation, growth and arbitrary comparison functions are not added here.
* This does not implement the native debugger or BREAK-ON-SIGNALS protocol.

## Reproduction

Run from a checkout beside the evidence store:

```
python3 tests/wasm/stage1/bootstrap-condition-system/run.py /tmp/condition-system
python3 tests/wasm/stage1/bootstrap-condition-system/native.py /tmp/condition-native
```

The native command performs the required final-source R6/R6a qualification.
Packet replay reuses that evidence only after comparing every proposal hash.
The packet verifier and retained evidence location are recorded with the final
summary. Debugging runs are not acceptance evidence.

Retained-packet replay:

```
python3 tests/wasm/stage1/bootstrap-condition-system/packet.py verify \
  --packet ../ccl-evidence/2026-09-23-stage1-condition-system-r1 \
  --output /tmp/condition-system-replay
```

The packet retains the earlier failing constructor runs. They exposed missing
bootstrap globals, missing native list helpers, and metadata differences
between projected thunks and native optimized closures. The combined runner
also caught insufficient fixture workspace when both compiler modes were
installed; its memory regions were enlarged without changing the collector.
The final run and replay use written source files without debugger hooks.
