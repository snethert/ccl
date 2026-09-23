# Default-off condition CPL integration

Steve accepted audit 162's proposal with “Accept and integrate default-off”.
The shared backend equals the reviewed compiler in `acf71bd7`'s packet byte
for byte. No runtime or CCL source file changes. `*b-cpl-conditions*` remains
NIL by default. This accepts only O-10's condition-matching component.

At the integration commit, check the final source identities with:

```sh
python3 tests/wasm/stage1/condition-cpl-acceptance/check.py --output /tmp/condition-cpl-integration.json
```

This checks the whole native-qualified proposal and unchanged compiler, Lisp
and runtime inputs against their retained hashes. It reuses the reviewed
25,868 execution comparisons and 21,843 native tests; it does not repeat or
claim new execution. The original fixture's full replay command must run
from `acf71bd7`, whose pre-integration source pins and patch anchors it binds.
Do not run that derivation over the already-integrated backend.

Audit 162's O-19–O-21 remain open: finalized classes are required; the fixture
catalog is not the image class table; constructors and readers retain the
existing schemas; SIGNAL still refuses string and symbol designators. The
six CPL callers run through an explicit fixture list, not a dependency-closed
bootstrap. No admission recount, new original execution or LL15 credit.

The next migration must use actual class-cell structures and CCL's class
table, MAKE-INSTANCE initialization and slot access. The fixture's cons-cell
catalog must not become a second permanent class registry.
