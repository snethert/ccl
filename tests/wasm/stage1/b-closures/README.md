# Generated lexical closures and mutable captures

This auxiliary LL05 proposal constructs real function objects in linear
memory. Each inner CCL front-end function becomes a separate B module;
the owner supplies its code ID and table entry. A function's environment is
a D1 simple-vector containing shared D1 cons cells. The CAR holds the current
captured value. CCL's `nx-root-var` supplies lexical identity across nested
functions; sibling closures share cells and separate activations do not.

The source/IR slice adds lambda values, LET, LET*, and lexical SETQ. Required,
optional, supplied-p, keyword and rest bindings may be captured. Captured cells
are conservatively allocated on entry, including cells for LET bindings in
untaken branches. Noncaptured assigned parameters get private rooted slots,
so SETQ cannot change the caller's argument storage. Defaults retain their
existing order. Parallel LET evaluates its initializers before binding;
LET* binds sequentially. Captures can themselves hold closures.

Allocation uses the thread-owned bump region and checks the whole extent
before writes. Allocation has no call, poll or GC window. Heap cells surviving
an exception are not rolled back. Closure entry validates the environment
header, extent and cell pointers before captured loads or stores. Function
objects retain the reviewed code/version/signature/role checks. The registry
is still owner-supplied; production loader authentication remains open.

The independent Python environment model and native CCL compare all values,
closure and cons identities, mutations and exceptional effects with generated
Wasm. The corpus includes 129 captures and transitive captures three levels
deep. A separate host-turn scenario returns closures to JavaScript, overwrites
the Lisp stack, then invokes and mutates them again. Literal heap-byte
expectations, malformed environment checks and exact-fit allocation checks
supplement the semantic oracle. Low and above-2-GiB placements run with plain
entries and observation wrappers checking physical root ownership and SELF.
The unused Stage 0 slot-validation module has been removed.

This is not a complete LL05 execution. FLET/LABELS and U1's inlined
LAMBDA-BIND IR are explicitly refused. Production conditions, authenticated
loading/lazy stubs, tail-call lowering and collection remain open. Arity/debug
metadata in function objects remain NIL placeholders. GC correctness is not
claimed merely because the explicit roots are inspected. The primitive and
leaf entry implementations are unchanged from the reviewed backend.

Run from the repository root, with fresh output directories:

```sh
python3 tests/wasm/stage1/b-closures/native.py --evidence ../ccl-evidence --work /tmp/b-closures-work --output /tmp/b-closures-native
python3 tests/wasm/stage1/registration/qualify.py --output /tmp/b-closures-native --inputs ../ccl-evidence/macos-u1-inputs --kernel ../ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 --destination /tmp/b-closures-qualified
python3 tests/wasm/stage1/b-closures/run.py --evidence ../ccl-evidence --native /tmp/b-closures-native --qualification /tmp/b-closures-qualified --output /tmp/b-closures-run
```

The proposed backend stays under this fixture until external review and user
acceptance. Replay the retained packet:

```sh
python3 tests/wasm/stage1/b-closures/verify.py --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-16-stage1-b-closures-r1
```
