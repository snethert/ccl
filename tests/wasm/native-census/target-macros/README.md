# Source-derived target macros

This isolated extension rebuilds fourteen metadata/accessor macros from eight
pinned U1 source forms. Seven reconstructed macros are used in the real dumplisp
front-end traversal. Native expanders execute on the cross-compiler host; their
source is read in the census target context. No source definition is installed.
The full target macro environment remains unqualified.

Run from the repository root on the macOS x86-64 reference host, choosing unused
work and output directories:

```sh
python3 tests/wasm/native-census/target-macros/run.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --work /private/tmp/ccl-target-macros-work-review \
  --output /private/tmp/ccl-target-macros-review
```

Replay this packet and its direct source bindings without native execution:

```sh
python3 tests/wasm/native-census/target-macros/verify.py \
  --packet /Users/buildsomething/Source/ccl-evidence/2026-09-13-target-macros-r1
```

The unchanged accepted registration, clean r7 image and reviewed descriptions
are reused. Two fresh sessions must emit identical raw captures. Four native
mutants and twenty checker controls must reject. Each native invocation and its
outputs are retained; the duplicate repeat captures are elided after comparison.
The runner verifies that source and FASLs remain unchanged.

See the [report](../../../../doc/WASM/stage0/target-macros.md) for the scope and
remaining compiler-macro/helper work. This input does not close LL15-b/c.
