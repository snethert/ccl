# Declared-type equality paths

This isolated census extension tests the nonconstant branch of EQL optimization.
It reconstructs NX-FORM-TYPEP, NX-FORM-TYPE and the scalar NX-TARGET-TYPE helper
from pinned U1 source. A private adapter applies the scalar target translation
inside OR, AND and NOT type expressions. MEMBER payloads are left as data.
The earlier constant-range and stream/vector helper corrections are reused.

Run on the macOS x86-64 reference host with fresh paths:

```sh
python3 tests/wasm/native-census/target-types/run.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --work /private/tmp/ccl-target-types-work-review \
  --output /private/tmp/ccl-target-types-review
```

Replay the retained packet and direct bindings:

```sh
python3 tests/wasm/native-census/target-types/run.py \
  --verify /Users/buildsomething/Source/ccl-evidence/2026-09-13-target-types-r1
```

Normal and repeat captures must agree byte for byte. The prior helper, shallow
translation, host range and forced declaration trust are four native controls.
The first three expose incorrect EQ lowering; the last ignores safety policy.
Fifteen probes retain actual front-end operators, call targets and expansion
events. Seventeen checker controls reject. All six dumplisp traversals agree.

Functions compile only in memory in a disposable U1 copy. Global helper bindings,
macro hooks, pass-2 observation and target state are preserved/restored. Source
and FASLs remain unchanged. No Wasm, implementation image, graph replacement or
gate credit results. Qualification covers these declaration/query paths;
arbitrary type inference, aliases, helper dependencies and native objects remain
open. See the [scope report](../../../../doc/WASM/stage0/target-types.md).
