# Generated multiple-value calls and bindings

This auxiliary proposal adds MULTIPLE-VALUE-CALL and MULTIPLE-VALUE-BIND through
CCL's real front-end IR. These are prerequisites for U1's HANDLER-CASE :NO-ERROR
expansion, not an implementation of condition signalling or an LL05/LL19 claim.

MULTIPLE-VALUE-CALL evaluates the callable's primary value first, then each
producer once, left to right. Complete value sets append directly into a growing
continuation argument area. Earlier arguments and the callable remain rooted
while later producers run. Extent arithmetic and alignment use i64 before any
narrowing or write; newly exposed padding is NIL before the root count grows.
There is no call or poll in the extension/publication sequence. No intermediate
heap list or second argument-vector copy is introduced. Ordinary calls enter the
internal B body; legal tail calls use the existing Wasm tail-transfer machinery.
Callable validation follows argument evaluation, as witnessed against native CCL.

MULTIPLE-VALUE-BIND evaluates its value form outside the new bindings. Values
are staged in rooted slots, missing values become NIL, and excess values are
discarded. Lexical bindings participate in the existing capture-cell analysis;
SPECIAL bindings use the existing reverse-order unwind extent. Both the compiler
and the independent pre-emitter root analysis recognize the real binding IR.

The corpus retains all previous cases and adds zero/mixed/large value sets,
ordered effects and errors, live designators, nested collectors, lexical captures,
missing/excess bindings, special bindings, cleanup, nonlocal exits and defaults.
Native CCL, the separate Python evaluator and generated Wasm are compared at low
and above-2-GiB placements. Public entries are poisoned for compiled calls. Long
MVC and MVB tail chains also run 100,000 steps inside a 2 KiB stack. Separate
capacity checks require checked failures, restored ownership, unpublished results
and intact stack fences. Compiler mutations use these same semantic oracles.

Literal MVC lambdas use ordinary heap closures; the existing literal APPLY
stack-storage optimization is not generalized here. Exact allocation counts
cover that distinction. Each producer still uses the inherited result reservation; the accumulated
argument count may exceed that per-producer budget. Stack, heap, source-reader
and harness registry bounds remain finite and explicit. No collector runs in
this fixture, so relocation and safepoint obligations remain open. A special
binding extent prevents tail transfer until it has unbound. General condition
classes, signalling, handler dispatch and TAGBODY/GO remain future work.

The loader, binary reader and stub are unchanged from the reviewed lexical-exit
unit. Lazy installation composes with the new binaries. Native R6/R6a and a fresh
retained replay are required; the earlier non-B emitter is unchanged. This
proposal is developed in disposable pristine U1 copies and awaits Claude's
review before integration.

```sh
python3 tests/wasm/stage1/b-multiple-values/native.py --evidence ../ccl-evidence --work /tmp/multiple-native-work --output /tmp/multiple-native
python3 tests/wasm/stage1/registration/qualify.py --output /tmp/multiple-native --inputs ../ccl-evidence/macos-u1-inputs --kernel ../ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 --destination /tmp/multiple-qualified
python3 tests/wasm/stage1/b-multiple-values/run.py --evidence ../ccl-evidence --native /tmp/multiple-native --qualification /tmp/multiple-qualified --output /tmp/multiple-run
python3 tests/wasm/stage1/b-multiple-values/verify.py --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-17-stage1-b-multiple-values-r1
```
