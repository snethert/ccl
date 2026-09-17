# Generated UNWIND-PROTECT

This auxiliary proposal adds CCL's real `unwind-protect` IR to the B backend.
It is a prerequisite for Lisp condition handling; it does not implement the
condition class system or HANDLER-CASE.

Before entering the protected extent, the emitter checks and reserves a rooted
retention area of `align16(8 + 4*capacity)` bytes. Protected calls and cleanup calls
are ordinary calls, so a tail transfer cannot discard pending cleanup or values.
Calls inside their callees retain the established tail-call behavior.

A final-encoding `try_table` surrounds only the protected form. On a checked
exception, the landing pad restores its own VSP, root chain, result descriptor,
count and allocation cursor for the explicit stack before cleanup runs. The
original exception remains in a Wasm exception-reference local and is rethrown
if cleanup returns. An exception from cleanup replaces it and reaches the next
enclosing cleanup; it is never caught by the same extent. The heap allocation
pointer is not rolled back: effects and escaped objects survive unwinding.

Normal results are copied into the reserved tagged root slots while cleanup
runs, and restored with their exact count afterward. Cleanup's values are
ignored. Nested extents each own their checkpoint and retention area.

The corpus compares native CCL, an independent Python evaluator and generated
Wasm, at low and above-2-GiB stack placements. It exercises ordered effects,
normal zero/one/many values, failures inside nested calls and argument evaluation,
exception replacement, cleanup that itself has cleanup, closures, local functions,
rest/APPLY, defaults, and recursion with pending cleanup. Public table entries
remain poisoned against compiled-wrapper dispatch. The accepted lazy loader
composes unchanged over the new modules. Compiler mutants use the same oracle.

The explicit-stack cost is proportional to result reservation and simultaneous
cleanup extents. A 1,024-word reservation in the original large-values case
exhausted the fixture's 32-KiB stack; that original run is retained. Positive
large-value cases use reservations through 512 words. This is checked resource
exhaustion, not a new fixed language maximum.

No GC or safepoint is added. Catch tags, THROW, local RETURN-FROM, dynamic special
binding, condition construction/signalling and debugger transfer remain open.
These extents currently live in Wasm handlers plus explicit value-stack roots;
TCR control-stack/handler-chain publication is not yet supplied. Exception
payload relocation, stack-temporary callables and post-call descriptor scanning
remain collector obligations. Engine traps are not Lisp exceptions and cannot
be used to exercise a cleanup guarantee. The checked failures here use Wasm tags.

```sh
python3 tests/wasm/stage1/b-unwind-protect/native.py --evidence ../ccl-evidence --work /tmp/unwind-native-work --output /tmp/unwind-native
python3 tests/wasm/stage1/registration/qualify.py --output /tmp/unwind-native --inputs ../ccl-evidence/macos-u1-inputs --kernel ../ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 --destination /tmp/unwind-qualified
python3 tests/wasm/stage1/b-unwind-protect/run.py --evidence ../ccl-evidence --native /tmp/unwind-native --qualification /tmp/unwind-qualified --output /tmp/unwind-run
python3 tests/wasm/stage1/b-unwind-protect/verify.py --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-16-stage1-b-unwind-protect-r1
```

The proposal is applied only in disposable pristine U1 copies. Shared integration
requires Claude's review and user acceptance. No complete LL05 or LL19 slot is claimed.
