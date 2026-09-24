# READY R10–R12 acceptance and integration

Steve accepted the stack with “I accept them” after audit 174. This integrates
exactly the reviewed compiler, architecture, target LAP definitions, two
level-0 files, collector and image loader. It adds no execution credit beyond
the reviewed 568 originals / 531 non-NIL witnesses and awards no LL15 slot.
Class conditions remain default-off outside the selected READY profile.

The integrated source check reuses audit 174's target execution explicitly:

```sh
python3 tests/wasm/stage1/ready-runtime-acceptance/check.py --output /private/tmp/ccl-work/codex/ready-runtime-check/identity.json
```

It binds all 35 qualified compiler/CCL files and both runtime sources to R12,
plus the audit record. The reviewed full corpus's 26,048 comparisons and four
cold boots are not reported as a new integration execution. Locks and streams
remain transient; the image loader admits complex single/double objects but
still refuses locks and streams. The final integrated files receive a fresh
native build and regression run:

```sh
python3 tests/wasm/stage1/ready-runtime-acceptance/native.py --output /private/tmp/ccl-work/codex/ready-runtime-native/run
python3 tests/wasm/stage1/ready-runtime-acceptance/readers.py /private/tmp/ccl-work/codex/ready-runtime-readers/run
```

The reader proof uses the seven actual edited native definitions and the new
target definitions. Inverting the edits restores every surrounding byte. CCL's
reader compares both files under all 17 existing target profiles, with FUTEX
both enabled and disabled. Decoded native code equality is checked separately
by R6. This is a compositional source-location proof; it does not load foreign
interface databases for whole-file cross-platform compilation.

## Audit 174 controls

O-64: the historical R9 check now binds product sources at its integration
commit and checks the exact independent raw-bit observation in the current
worker. Unrelated stream/lock witnesses may change. Bit-order and padding
mutants are rejected. This stack's checker binds the current product sources.

O-65: the added Lisp expression allocates native lock-layout witnesses with
recursive, read/write and other kind cells. It compares CLASS-OF with the
appropriate FIND-CLASS result before and after collection. The read/write and
fallback objects are classification witnesses only; no unsupported OS lock is
acquired. A wrong recursive-lock classifier must fail the native comparison.

O-66: the exact emitted lock-token expression is assembled separately so that
zero, misaligned and high-bit TCR values can reach its three guards without
first entering a Lisp frame through an invalid TCR. Each clause is omitted
independently; each omission admits only its corresponding invalid input.
Ordinary calls still require the owner's valid immutable TCR (1024 in READY).
This local expression test is not a claim that arbitrary invalid TCRs can safely
enter generated Lisp functions.

The focused command requires the retained R12 cache session. On a cold machine,
first run the R12 verifier at `f8180b52` to populate that session. A missing
session refuses rather than silently building with a different compiler.

```sh
python3 tests/wasm/stage1/ready-runtime-acceptance/focused.py /private/tmp/ccl-work/codex/ready-runtime-focused/run
```

It checks the pinned driver inputs, compiles only the augmented READY probe
file, runs the writer and four cold readers, and rejects the classifier mutant.
No full-corpus re-execution or new original-definition credit is claimed.
All outputs belong under the managed workspace; retain results before deletion.

The historical R10–R12 proposal verifiers replay at their respective commits.
Their patch generators intentionally precede integration. Public stream
construction, the unresolved READY closure, replacement attribution and the
35 startup callback dispositions remain open.
