# DEFTYPE expansion order in the census

This isolated extension tests the alias gap in the reviewed target TYPEP fixture.
Ten literal DEFTYPE forms are read in the target context and compiled as private
expanders using U1's own argument parser. A dynamic copy of the expander registry
makes them visible to the native type system without changing its original table.

The new wrapper expands these aliases before target translation and before both
native membership and canonicalization. Sixteen constant tests run through the
real front end. Five nonconstant optimizer expansions are checked structurally
and evaluated on five values each. That evaluation runs on the native host; it
does not qualify Wasm lowering or arbitrary DEFTYPE bodies.

```sh
python3 tests/wasm/native-census/target-aliases/run.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --work /private/tmp/ccl-target-aliases-work-new \
  --output /private/tmp/ccl-target-aliases-result-new
python3 tests/wasm/native-census/target-aliases/run.py \
  --verify /Users/buildsomething/Source/ccl-evidence/2026-09-13-target-aliases-r1
```

Use fresh directories. The runner extracts pristine U1 and uses the pinned clean
native image and accepted census registration. It writes no FASL, saves no image
and verifies source/FASL preservation and temporary-state restoration. Normal and
repeat captures must match byte for byte. Five native mutations and twenty
checker controls must reject. The genuine restore traversal retains seven
captured definitions and five boundary stops; the prior builder changes observer
IDs, which the verifier permits only through a bijective renaming.

Alias expansion is limited to the supplied source definitions, 32 expander calls
per normalization and 64 levels of nested type syntax. Cyclic and growing aliases
are tested refusals. MEMBER values and explicit numeric bounds remain data.
Resident expanders, arbitrary executable alias bodies, element-type positions,
class objects and the rest of the macro environment remain unqualified. No census
edge is replaced and no acceptance slot is claimed.
