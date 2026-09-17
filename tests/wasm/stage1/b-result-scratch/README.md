# Per-callee result scratch

An isolated proposal derived from corrected conditions R2. It separates a
caller's delivery protocol from the storage a callee needs while computing.
The shared backend remains at the accepted MVC storage R2 unit; neither this
proposal nor conditions R2 is integrated.

The compiler scans each function's own CCL IR, including initializers and
lambda-list defaults. An explicit operator allowlist and a four-value bound on
every VALUES form prove the scratch requirement. Unknown calls, transfers,
multiple-value consumers and counts above four keep the dynamic path. No proof
about a named callee is inferred from its current function cell, so rebinding
still selects that installed function's own implementation.

A proven-small function uses ordinary rooted scratch and creates no dynamic
result descriptor, makes no arena allocation and releases no arena scope of its
own. It still reads the continuation's delivery mode when handing values back.
The ordinary B signature, continuation layout, loader and collector root shapes
are unchanged. Non-dynamic entries retain the existing caller reservation.

An independent pre-emitter witness lists the IR operators and VALUES arities.
Python checks the storage bound and the actual emitted entry choice. Seven
controls damage the proof, defaults/initializer traversal, mode choice or result
delivery. Eighteen additional native scenarios cover zero/four values, retention,
branches, lexical and special bindings, closures, unknown defaults and live
rebinding. The corrected conditions corpus and all inherited tests also run.

The operation-count probe runs unchanged and observed binaries against native
CCL. Its two nested scalar callees now create zero descriptors, down from two;
only the producer's one release remains, down from three. Both versions allocate
zero arena blocks. This is an operation count, not a timing claim.

This is deliberately **not general first-value/discard propagation**. A callee
with unknown calls or large intermediate values still uses dynamic storage when
entered under a producer, even if its caller will discard most of its results.
Removing that cost needs a result-demand protocol that preserves internal
multiple-value consumers and nonlocal transfers; a blanket bounded-mode change
is retained as a rejected counterexample. Moving collection remains unqualified.

From the repository root, with fresh output paths:

```sh
python3 tests/wasm/stage1/b-result-scratch/native.py --evidence ../ccl-evidence --work /tmp/scratch-native-work --output /tmp/scratch-native
python3 tests/wasm/stage1/registration/qualify.py --output /tmp/scratch-native --inputs ../ccl-evidence/macos-u1-inputs --kernel ../ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 --destination /tmp/scratch-qualified
python3 tests/wasm/stage1/b-result-scratch/run.py --evidence ../ccl-evidence --native /tmp/scratch-native --qualification /tmp/scratch-qualified --output /tmp/scratch-run
python3 tests/wasm/stage1/b-result-scratch/verify.py --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-17-stage1-b-result-scratch-r1
```

No inventory slot or acceptance is claimed. Both proposals require Claude's
review and the user's acceptance before integration.
