# Generated dynamic bindings — 16 September 2026

The [isolated proposal](../../../tests/wasm/stage1/b-special-bindings/README.md)
adds SPECIAL declarations on LET/LET*, dynamic reads and SETQ through CCL’s real
front end. The accepted CATCH/THROW implementation is integrated separately.
The user accepted this unit after Claude’s seventy-sixth audit; its exact reviewed
bytes are integrated. It claims no LL05/LL19 slot.

Each symbol carries its D1 tagged binding index, distinct from the raw TCR index.
The generated lookup validates the symbol, index and owned vector before access.
A no-local-binding marker selects the global value cell. An unbound value raises
a checked refusal; constructing a Lisp condition remains separate work. SETQ
updates the active thread slot or global cell according to that same rule.

Each binding reserves a 32-byte aligned record on the explicit stack, publishing
its symbol and old thread value as roots. LET stages all initializers first;
LET* binds one at a time. Normal return, THROW and checked exceptions restore
the previous values in reverse order. Nested cleanup observes the bindings
appropriate to its extent. Active bindings inhibit tail transfer, while callees
retain the direct-continuation and proper-tail-call paths.

The final corpus has 313 source functions, 390 modules and
1,323 native/model cases, producing 5,292 target comparisons
at low and above-2-GiB stack placements. Call-entry checks perform
8,252 binding inspections, reaching 40 simultaneous bindings.
Another 44 checks inject invalid symbol/vector metadata or insufficient
capacity. All 19 compiler mutants reject, together with 3 development
regressions and the inherited loader controls. Compiled calls use zero public
wrapper dispatches; the proper-tail-call corpus and lazy installation pass.

Native R6/R6a passes with 162 unchanged FASLs, the two explained registration
artifacts, all 164 restored FASLs and 21,843 native tests. Five architecture tables
and 17 existing-target module profiles agree. The retained verifier recompiles
the corpus and mutants byte-identically and reproduces each first failure.

The fixture uses three owner-assigned symbols and a four-entry vector. Invalid
metadata and capacity exhaustion are checked, including failure after the first
binding was established. There is no automatic vector growth, special lambda
parameter binding, PROGV, collection or multi-Worker execution. Current vector
slots are TCR roots; the collector must also scan saved values and symbols in
binding records. Recovery from corrupt owned records is not promised.

Declarations are local, not global proclamations. The corpus tests lexical
shadowing in both directions, nested/repeated bindings, partial initialization,
assignment, unbound variables, cleanup and throw replacement, closures, local
functions, defaults, APPLY, large multiple values and recursion. Native reference
state is isolated by per-case PROGV; that is not generated PROGV support.

The private symbol namespace uses the fixture’s restricted ASCII import names
(letters, digits, underscore and hyphen, at most 64 characters). Development exposed a collision when
two packages supplied the same printed name; foreign-package specials now refuse
before publication. The original two-function capture and a guard-removal
regression are retained. A general package-aware symbol installer remains open.
The first retained replay also caught an unintended older leaf-admission edit;
the reviewed non-B prefix is restored byte-for-byte and the refusal is retained.

The loader, binary reader and stub remain byte-identical to the reviewed
CATCH/THROW unit. Lazy composition reuses the same symbol/vector setup. The
previous host-re-entry and exception-root obligations remain in force.

Packet: `ccl-evidence/2026-09-16-stage1-b-special-bindings-r1`.
