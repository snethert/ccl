# Generated CATCH/THROW and control records

This auxiliary proposal consumes CCL's real CATCH and THROW IR. Tags use EQ
identity and the nearest live matching catch receives the complete ordered value
sequence. Missing catches produce the checked CONTROL refusal after evaluation
of the tag and values. This is not the Lisp condition class or handler system.

CATCH and UNWIND-PROTECT publish a linked record through the production schema's
`handler_checkpoint` (140). `unwind_state` (148) distinguishes ordinary execution,
a pending nonlocal transfer and another pending exception. The record layout is
in `layout.json`: 32 raw header bytes followed by a root record containing the
tag, padding and the capacity-sized value buffer. The whole extent is reserved
and checked before publication. Every extent is retired on return or exception.
Normal completion restores the enclosing unwind state, including a pending exit
while a cleanup runs a nested handled catch.

THROW roots its tag while evaluating values, checks the decreasing control chain,
copies values to the target's rooted buffer, then raises a distinct shared Wasm
tag carrying the raw target record address. A catch tests that address before
handling the exit. Intervening cleanups restore their own checkpoints and run
before the target is retired. A cleanup may replace the exit, handle a nested
exit without losing the original values, or propagate another checked failure.
The same exception reference is rethrown when cleanup returns normally.

The public wrapper preserves the host's incoming control head and unwind state.
Compiled ordinary calls retain the direct-continuation path: no extra wrapper,
argument copy or per-call control record. Tail transfer is inhibited inside an
active CATCH body or pending cleanup, while callees can perform real tail calls.
Record storage is `align16(48 + 4*capacity)` per simultaneous dynamic extent;
stack capacity remains an explicit resource, with no automatic growth.

The corpus compares an independent Python evaluator, native CCL and generated
Wasm at low and above-2-GiB stack placements. It covers tag identity, shadowed
catches, cross-module calls, APPLY, defaults, closures, local functions, cleanup
replacement, zero and 130 values, and recursion. Generic call-entry inspections
walk all live control and root records. Explicit Lisp effect calls witness the
unwind state. Corrupt-chain probes exercise generated validation. The inherited
cleanup-checkpoint observer remains specialised to `uw_cleanup`, whose corpus
calls are cleanup entries only. Public table entries remain poisoned.

The loader proposal adds the distinct `nonlocal_exit` capability and the profile
`wasm32-shared-B-exnref-tail-catch-v1`. Its bounded binary reader admits exnref in
internal function signatures; exact import/export policy is still enforced.
Focused controls reject missing, substituted or aliased tags and the old profile,
and real cold installation composes over the complete generated corpus. Catalog
ownership is trusted; cross-Worker publication and code signing are not claimed.

No GC or safepoint is added. Exception-reference relocation, transient Wasm
locals, stack-temporary callables and safe inspection during unwinding remain
collector obligations. This record is not a complete debugger/handler frame or
separate control-stack implementation. Dynamic special binding, local
RETURN-FROM, condition construction/signalling and full LL05/LL19 remain open.
A landing-pad root restoration and exceptional control retirement are immediately
followed by enclosing restoration with no call or poll between them. Removing
either can escape this execution oracle; the exploratory mutants are retained
and receive no rejection credit. Inspection during those transitions belongs to
the collector work. Engine traps are not Lisp exceptions and do not promise cleanup.

```sh
python3 tests/wasm/stage1/b-catch-throw/native.py --evidence ../ccl-evidence --work /tmp/catch-native-work --output /tmp/catch-native
python3 tests/wasm/stage1/registration/qualify.py --output /tmp/catch-native --inputs ../ccl-evidence/macos-u1-inputs --kernel ../ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 --destination /tmp/catch-qualified
python3 tests/wasm/stage1/b-catch-throw/run.py --evidence ../ccl-evidence --native /tmp/catch-native --qualification /tmp/catch-qualified --output /tmp/catch-run
python3 tests/wasm/stage1/b-catch-throw/verify.py --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-16-stage1-b-catch-throw-r1
```

The proposal runs only in disposable pristine U1 copies. Claude's review precedes
shared integration. This packet claims no inventory slot.
