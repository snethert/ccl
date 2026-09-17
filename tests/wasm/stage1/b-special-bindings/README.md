# Generated dynamic special bindings

This auxiliary proposal implements LET/LET* bindings declared SPECIAL, LOCALLY
special declarations, special references and SETQ through CCL's real front end.
It does not install global proclamations. A local SPECIAL declaration applies
to its binding or references; it does not make later inner bindings globally
special. Both lexical-shadowing directions are tested explicitly.

This slice admits declared special symbols from its private WASM32-COMPILER
namespace only. Other packages and non-round-tripping spellings are refused
before publication; a general package-aware symbol installer remains open.
The package-collision defect found in development is retained and replayed.

The symbol's D1 binding-index cell holds a positive fixnum index into the current
TCR's binding vector. It is unrelated to the raw TCR registry index. Generated
code checks the symbol header, index representation, reserved zero, capacity,
vector alignment and full extent before access. `no-thread-local-binding` (243)
selects the symbol's global value cell; the distinct unbound marker (51) raises
a checked UNBOUND refusal. SETQ updates the live local slot when bound and the
global value otherwise. Constants and offsets are checked against D1 and the
production TCR schema, not inherited from the 64-bit host.

Each actual dynamic binding adds one aligned 32-byte record on the explicit
value stack. It holds the previous binding head, the tagged binding index, a
root header, the symbol and saved TLS value, plus a version marker. The symbol
and old value are roots; the current vector's slots remain TCR roots. A saved
no-local-binding marker is restored literally, so subsequent reads use the
current global cell. The chain is published only after reservation and record
initialization, with no call or poll between publication and the value store.

Parallel LET evaluates every initializer before any binding takes effect.
Sequential LET* publishes each binding before the next initializer. Both restore
bindings in reverse order on normal and exceptional exits. Cleanup inside the
binding sees its value; cleanup outside it sees the restored value. Catches and
cleanup keep the reviewed exception protocol. An active binding extent inhibits
tail transfer, while a called function can still run a proper tail chain.
Ordinary compiled calls retain the direct-continuation path.

The corpus compares a Python evaluator, native CCL and generated Wasm, including
unbound values, nested/repeated bindings, assignments, failures during partial
initialization, CATCH/THROW, cleanup replacement, defaults, closures, local calls,
APPLY, large multiple values and recursion. Native reference state is isolated
by a private per-case PROGV; this does not claim generated PROGV support. The
owner assigns three symbol indices and a four-entry vector. The TCR index is 37
to expose namespace confusion. Both low and above-2-GiB stacks are exercised.
Generic call-entry inspections join live binding records to their actual roots;
44 metadata/capacity probes check refusal without symbol/TLS changes, including
unwinding a first binding when the second cannot fit the vector.

The loader, binary reader and stub are unchanged reviewed bytes. Lazy composition
uses the same owner symbol/vector setup and result oracle. The inherited loader
controls remain regressions; no new loader mechanism or concurrency is claimed.

Nineteen compiler mutants exercise binding storage, namespace separation,
restoration, validation and the direct call path. Three additional development
regressions include the package-identity guard.

The binding vector has owner-assigned capacity; automatic growth under admission
is still open. Special lambda parameters, PROGV, local RETURN-FROM and other
declarations are refused. There is no GC or safepoint, no special condition class
construction/handler dispatch, no general symbol installer and no multi-Worker
binding-vector qualification. Generated records are owned metadata, not an
untrusted input format. Corruption during unbinding fails closed; recovery from
an invalid saved record is not promised. Host re-entry during a pending exit
retains the previous unit's open obligation.

```sh
python3 tests/wasm/stage1/b-special-bindings/native.py --evidence ../ccl-evidence --work /tmp/special-native-work --output /tmp/special-native
python3 tests/wasm/stage1/registration/qualify.py --output /tmp/special-native --inputs ../ccl-evidence/macos-u1-inputs --kernel ../ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 --destination /tmp/special-qualified
python3 tests/wasm/stage1/b-special-bindings/run.py --evidence ../ccl-evidence --native /tmp/special-native --qualification /tmp/special-qualified --output /tmp/special-run
python3 tests/wasm/stage1/b-special-bindings/verify.py --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-16-stage1-b-special-bindings-r1
```

The proposal runs in disposable pristine U1 copies and awaits Claude review
before shared integration. It claims no inventory slot.
