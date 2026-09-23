# Projected-image READY join — R4

Original CCL execution remains **550 / 515 non-NIL**. R4 implements the READY
public hash-table bindings and generated class-image admission. This remains
one working READY unit, with no LL15 slot claim or new original-definition
credit. Compiler, CCL and shared runtime sources are unchanged.

## Startup and public bindings

The selected image contains **612 classes and 33 generic functions**, not all
581 GFs in the native census. The adopted profile uses class conditions, strong
populations, one Worker, no scheduler or automatic termination, and uncached
standard method dispatch. The accepted image loader installs the saved heap;
a fresh consumer cannot call the graph projector.

`startup.lisp` compiles whole through CCL's file compiler. Before publishing
class globals or `%ALL-GFS%`, `ready-image-status` reads the native class and
method fields: standard-instance classes, nonempty CPL headed by the class,
matching non-obsolete own wrapper, standard method combination and callable
method function. These are checks on the selected, digest-bound image, not a
general malformed-object validator. They do not establish closure of every
class-finalization branch. The native oracle and Wasm agree on eight directed
mutations; each is restored with UNWIND-PROTECT, admission succeeds afterward,
and five startup root cells remain unchanged. The refusal caller is excluded
from the READY operator census.

`bindings.json` names four public function-cell routes: GETHASH, PUTHASH,
REMHASH and CLRHASH use the **existing reviewed Lisp EQ wrappers**. Direct
class-mode calls already used these wrappers. Calls through function cells
previously reached the native locking implementation. Binding resolves all
four installed function objects before writing any cell; the mapping and
binding code are part of the code digest. This is the strong-EQ READY profile;
the wrappers still refuse other table tests and retain their read-only checks,
growth and capacity contract. No new C/JS table service is introduced.

The cold startup now exercises those public cells on twenty cons keys, across
capacity doublings and collections, with lookup, missing/default results,
REMHASH and CLRHASH. Values and multiple-value counts match native. Four
controls restore the native binding one at a time: all stop with checked 2
and leave the process FAILED, rather than reaching READY or trapping.

Startup resolves every class cell, checks all selected GFs in the strong
population, constructs a condition with inherited default initargs and slot
readers, and catches a class-based error. Its native answer remains
`(612 33 43 41 :CAUGHT)`. The legacy condition registry is poisoned. Four cold
boots cover both memory placements, with and without movement before startup.
The process owner publishes READY only after the callback returns, publishes
FAILED on a throw, and refuses a second bootstrap. Missing image, missing entry
and premature READY also fail. The published-last memory assertion remains a
harness check, distinct from that owner contract.

## Reproduce

From this source revision beside the evidence store and retained P4 cache:

```sh
python3 tests/wasm/stage1/ready/run.py /private/tmp/ccl-work/claude/ready/replay
python3 tests/wasm/stage1/ready/packet.py verify ../ccl-evidence/2026-09-23-stage1-ready-join-r4 /private/tmp/ccl-work/claude/ready/verify
```

The warm compiler session is hash-verified. Only six new functions are
compiled; the unchanged corpus is not rebuilt. The native process's GF and
scheduler globals are restored after all six oracle entries. The saved native
compiler image is tooling, never the target bootstrap heap. The written worker
checks values, mutations and thread/binding restoration. The accepted loader's
31 controls run with imported module hashes recorded. The heap-key image check
still exercises MOVED, first-lookup rehash, cache invalidation and tombstones at
both placements. Historical packets replay from their own source revisions.

## Remaining READY work

The public bindings remove 136 modules of native hash machinery from the
conservative graph. The new census reaches **546 modules, 109 operator kinds,
24,127 occurrences**, with **83 missing edges naming 59 callees** and **35
indirect-call modules**. Roots are the startup entries, projected callables and
four public bindings. No path is pruned merely because the image admission or
a cold boot passed. Class finalization, reporting, some slot protocols and
indirect calls still need closure or an explicit, justified profile exclusion.

`replacements.json` retains 61 target definitions: 26 direct LAP antecedents,
10 Lisp antecedents, seven renamed routes and 18 entries awaiting complete
attribution. Source branches and backend substitutions still need their final
join; the 25-name cap is not claimed yet. `callbacks.json` retains all 35 native
registrations and their outstanding dispositions. The inherited 550/515
execution baseline is distinguished from this cold image's execution.

Development evidence includes the rejected MAPCAR dependency in the initial
admission caller; it was replaced by an ordinary LOOP in this new fixture code.
No native definitions were rewritten. R6/R6a is reused by unchanged shared-source
identity. The next work remains in this READY unit.
