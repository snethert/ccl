# Condition handlers through real classes

The original-definition headline remains 550 executed / 515 with a non-NIL
witness. This unit adds six protocol callers, 24 native cases and 96 target
comparisons. It does not recount admission or claim LL15 completion.

Under the new, default-off `*b-cpl-conditions*`, HANDLER-BIND, HANDLER-CASE and
constant condition TYPEP/REQUIRE-TYPE tests call CCL's unchanged `CLASS-TYPEP`
from `l1-typesys.lisp`. That function uses `CLASS-OF`, `%INITED-CLASS-CPL` and
MEMQ. The file is compiled in its whole-file environment; only this definition
joins the execution unit, so internal macro expander names cannot replace
the existing numeric oracle functions.

The owner supplies a pinned vector of native-shaped class cells (name . class)
through `symbols.condition_class_cells`. The vector and cons cells stay pinned;
their CDRs are collector roots. Class objects, wrappers, instances and CPLs
move. Lookup compares the complete symbol identity, including its package,
and resolves the current class cell for each test. The owner must provide
unique, correctly bound cells and finalized classes with initialized CPLs.
This is trusted image linking, like the existing class/method graph fixture.

There is no new ancestry mask. Four newly defined conditions, including a
diamond inheriting ERROR and WARNING, have no constructor-registry row or
assigned bit. Their handler selection, multiple inheritance, TYPEP answers,
declining handlers, re-signalling, restart transfers and cleanups are compared
with native. Handlers collect; each row also runs after relocation at both
placements. An existing TYPE-ERROR is constructed, collected, signalled and
read through its accepted slot interface.

This is the matching component of O-10, not the entire condition-system
migration. The old mode remains byte-identical. Existing constructors and
readers retain their admitted schemas; custom conditions in these tests are
projected from native instances. General MAKE-CONDITION for new classes,
generic slot readers, owner installation on the cross-dumped heap and
uninitialized-class handling remain work. Do not enable this mode on an image
without its class cells and class table.

The catalog tests use the four helper functions extracted from an emitted
module, including the existing span/object checks. They cover pointer and
header tags, header/body/cell/class spans, missing and unresolved cells,
empty catalogs, first/last entries and exact memory-end fits. A trap is never
accepted as a refusal. Four focused omissions must fail. The full inherited
corpus and its structure, population and 40 collector-owner checks also run.
Native R6/R6a is bound to the final proposal manifest and compiler hash.

Development failures are retained: a whole-file macro-expander/oracle name
collision, an owner fixture confusing CL:ERROR with :ERROR, and class roots
left over when the fixture reset an image between cases. The final harness
isolates the selected definition, binds package-qualified class symbols and
resets catalog roots with the image.

From the packet's source checkout beside `ccl-evidence`:

```
python3 tests/wasm/stage1/bootstrap-condition-cpl/packet.py verify \
  --packet ../ccl-evidence/2026-09-22-stage1-condition-cpl-r1 \
  --output /tmp/ccl-condition-cpl-replay
```

Replay compiles and executes in pristine U1, runs the catalog controls and
reuses native qualification only after comparing the final source manifest.
For a fresh native build:

```
python3 tests/wasm/stage1/bootstrap-condition-cpl/native.py /tmp/ccl-condition-cpl-native
```

The compiler change remains a proposal. No shared compiler, runtime or CCL
source file is changed by this fixture.
