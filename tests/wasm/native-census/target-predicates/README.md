# Target TYPEP paths

The private census TYPEP expander now includes source OPTIMIZE-TYPEP and translates
FIXNUM/BIGNUM before native membership and canonicalization. Boolean type operands
recurse; MEMBER literals and explicit bounds stay data. Earlier EQL and stream/vector
helper corrections remain in use. No global compiler binding or shared source changes.

Run on macOS x86-64 with fresh disposable paths:

```sh
python3 tests/wasm/native-census/target-predicates/run.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --work /private/tmp/ccl-target-predicates-work-review \
  --output /private/tmp/ccl-target-predicates-review
```

Check the retained packet without rerunning native sessions:

```sh
python3 tests/wasm/native-census/target-predicates/run.py \
  --verify /Users/buildsomething/Source/ccl-evidence/2026-09-13-target-predicates-r1
```

Twenty-two actual front-end constant probes yield fifteen true and seven false
IR bodies. Two ctype guard probes and two unchanged-call probes pass. The genuine
restore file has ten TYPEP events. The checker reconstructs all 170 helper trace
records, including canonical bounds, answers and event joins. Five native controls
and 22 checker controls reject; normal/repeat captures and all seven file
traversals are byte-identical. Source, FASLs and original global helpers remain
unchanged; temporary routing and target/pass-2 state restore.

Native membership/canonicalization still execute after translation. OPTIMIZE-CTYPEP
remains native, and its existing cross-target refusal is tested. General aliases,
arbitrary constant objects, inferred types and runtime class/builtin cells remain
open. No generated Wasm or census closure is claimed. See the
[scope report](../../../../doc/WASM/stage0/target-predicates.md).
