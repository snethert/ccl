# Generated B calling protocol: LL05-a and LL05-b

The combined qualification runs CCL's real pass 2 in disposable clean U1 copies.
It covers the generated argument/binding/closure/result corpus, checked lazy
installation and adapters, and bounded proper tail chains. It derives from the
accepted conditions R2 and result-scratch implementation. The proposal stays
isolated until adversarial review and acceptance.

Arity and function-designator checks now signal while the failing dynamic context
is live. The resolver's pure validation is caught locally, before unwinding;
ordinary and keyword arity checks invoke the same generated service directly.
Keyword validation precedes parameter special bindings and rest allocation, so
an error handler sees the caller’s dynamic values.
HANDLER-BIND and HANDLER-CASE use U1 expansions and the existing generated
cluster dispatcher. A declining handler continues the search; an exit or new
error follows the existing cleanup/binding/result protocol. The private service
has its own rooted result descriptor, including dynamic transfers into a producer.

Conditions are freshly allocated D1 simple vectors using the condition fixture's
private representation. Arity uses PROGRAM-ERROR; malformed keyword calls add
SIMPLE-CONDITION; bad non-symbol designators use TYPE-ERROR and undefined symbol
functions use UNDEFINED-FUNCTION. Literal expectations are checked by native CCL
before target execution. No production CLOS representation, condition slots,
restarts, debugger, moving collection or unrelated implicit errors are claimed.
With no handler, or after all handlers decline, the existing structured fatal code
remains the boundary. Resource and corrupted-state refusals remain explicit.

The owner supplies honest symbol/registry storage and the authenticated catalog.
Installation is single-Worker, not cross-Worker publication or code signing. The
corpus poisons public entries for compiled calls. Full loader controls re-execute
signature, same-type role, actual-table, digest, initialization and retry checks
against these generated modules; the public adapter is retained for host entry.

Run from the repo root, using fresh output paths:

```sh
python3 tests/wasm/stage1/b-call-errors/native.py --evidence ../ccl-evidence --work /tmp/ll05-native-work --output /tmp/ll05-native
python3 tests/wasm/stage1/registration/qualify.py --output /tmp/ll05-native --inputs ../ccl-evidence/macos-u1-inputs --kernel ../ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 --destination /tmp/ll05-qualified
python3 tests/wasm/stage1/b-call-errors/run.py --evidence ../ccl-evidence --native /tmp/ll05-native --qualification /tmp/ll05-qualified --output /tmp/ll05-run
python3 tests/wasm/stage1/b-call-errors/verify.py --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-17-stage1-ll05-r1
```

The retained verifier recompiles all compiler mutants, executes the independent
native/target oracles, replays the loader controls, and verifies R6/R6a. Constants
(LL10-a) remain separate. Neither this packet nor its condition representation
claims LL19 or collector acceptance.
