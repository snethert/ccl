# Population consumer scaffold admission

Auxiliary follow-up to audit 140 F1. The retained selected-source rewriter now validates source before normalization. It refuses population API shadows in FLET/LABELS, local macros, API-named variables, standalone setter function references, unsupported setter arities and population PUSHNEW/POP. Multi-place SETF is refused when a population place occurs in either position, including the shape in `library/macptr-termination.lisp:173`.

The pinned native compiler checks thirteen directed refusals and eight omission controls. All sixteen admitted corpus forms still produce alpha-equivalent rewritten forms; generated code, native observations and movement evidence are reused from the bound population-consumers packet. No compiler, runtime or earlier fixture changes.

**Do not integrate this rewriter.** It remains selected-fixture scaffolding. The durable implementation must provide target population accessor indices and REQUIRE-TYPE support so CCL's ordinary accessor functions compile without consumer rewriting. PUSHNEW at `lib/method-combination.lisp:155`, POP, general SETF/function references, catchable TYPE-ERROR and real-symbol installation remain owed. The neighboring typed-populations proposal establishes a distinguishable strong layout for that path; it does not implement REQUIRE-TYPE.

Replay:
```
python3 tests/wasm/stage1/population-consumer-review/packet.py verify --packet ../ccl-evidence/2026-09-21-stage1-population-consumer-review-r1 --output /new/replay
```
No slot credit, acceptance or integration is claimed.
