# Stage 1A registration proposal

`run.py` builds and tests pristine U1, applies the complete proposal in that
owned archive, repeats the native suite, executes the first generated leaf
functions, removes the proposal, and rebuilds to the original 164 FASLs.
`qualify.py` independently replays the generated modules and checks the
retained build, including rejection controls. The main CCL source tree is
not patched. Claude must review before integration.

The proposal changes two shared files: three system registrations, and a
Wasm branch in each of the compiler-module and cross-loader-module selectors.
It adds the generated architecture, a functional leaf pass 2 and a
cross-loader registration that explicitly refuses image construction.
A native image writer or native instruction word is never substituted for
the Stage 1E coordinated heap/code writer.

Before each rebuild, the runner removes prior FASLs, then both sides load
U1’s existing XFASLOAD dependency from the same source state.
The registered side then loads the complete Wasm backend and cross-loader
before the native corpus compiles. This holds dependency preparation equal;
otherwise XFASLOAD’s earlier loading changes generated symbol names.
The verifier requires the loaded-backend marker, and rejects its omission.
R6 retains all 164 native FASLs. Exactly two intentionally differ. The
systems decoder accounts for the three inserted data entries and the
length/count/source-span fields, with all remaining bytes equal. The
compiler decoder compares all 144 forms, including every executable byte,
constant and nested function: only the two named selector functions change;
source-note movement is derived from the two exact source insertions.
Both changed function bodies remain in the comparison report. No whole
FASL is exempt and no executable bytes are normalized away. Existing module
selections cover five architectures and seventeen OS/architecture names.
R6a re-evaluates U1's shared operator declaration and installation macro in
private tables under each architecture's reader features, preserving all
279 IDs, flags and twelve reserved slots. This is not foreign-platform
machine-code execution; macOS x86-64 is the native execution reference.

The first pass 2 receives real CCL acode. Its declared source subset is one
required-argument lambda with fixnum/NIL/T constants, parameter references,
quotes of those constants and IF. It emits the B entry signature, reads
arguments through TCR.vsp and publishes one value through the caller's result
region. It allocates nothing and calls nothing. Every other source construct
is refused **before** macro expansion; every other IR operator is refused
again in pass 2. This boundary is necessary until the target macro/helper
work is integrated: the retained TYPEP counterexample shows that native
constant folding can otherwise hide an unsupported form from pass 2.

The smoke covers nine generated functions and 24 native-comparison calls,
plus ten refusals. It claims no general B ABI, Lisp condition, collector,
function-object, constant-pool, callback or bootstrap-image implementation.
The arity guard is presently fatal; S1-LL05 must replace ordinary user arity
failure with the Lisp condition path. The cross-loader API refuses explicitly;
its native compatibility descriptor is registration metadata, not a usable
native cross-dump backend.

Run from the repository root, supplying the retained evidence root and new
work/output directories:

```sh
python3 tests/wasm/stage1/registration/run.py \
  --inputs "$EVIDENCE/macos-u1-inputs" \
  --kernel "$EVIDENCE/2026-09-12-native-census-r7/baseline/build/dx86cl64" \
  --work "$NEW_WORK" --output "$NEW_OUTPUT"
python3 tests/wasm/stage1/registration/qualify.py \
  --inputs "$EVIDENCE/macos-u1-inputs" \
  --kernel "$EVIDENCE/2026-09-12-native-census-r7/baseline/build/dx86cl64" \
  --output "$NEW_OUTPUT" --destination "$NEW_QUALIFICATION"
```

`qualify.py` is the S1-LL08-a runner. It requires the actual three-build
result, not a synthetic PASS. Exact child commands and failure logs are
retained. CCL's zero exit alone is insufficient; success markers are required.
