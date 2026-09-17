# Generated explicit conditions and handlers

The [isolated proposal](../../../tests/wasm/stage1/b-conditions/README.md) adds
`SIGNAL`, `ERROR`, `HANDLER-BIND` and `HANDLER-CASE` with `:NO-ERROR` through U1's
real macro expansions and compiler IR. It is auxiliary work awaiting external
review, with no LL05 or LL19 gate credit. The accepted R2 MVC storage backend is
the shared implementation until this proposal is reviewed and accepted.

The dispatcher searches clusters in order and masks the current cluster before
invoking a handler. Returning from a handler declines the condition. A signal
inside that handler sees outer clusters. Single and indexed HANDLER-CASE clauses
use the existing published catch/throw records, so intervening cleanup and special
bindings restore before the selected clause runs. A handler's discarded result
count is independent of the final caller reservation: four values stay inline,
and larger returns use the reviewed temporary-result mechanism and release it
on both paths. Compiled handler calls use internal entries, without public wrappers.

The new corpus has 62 modules and 212 native cases, executed at two memory
placements with and without entry inspection: 848 comparisons. It covers six
condition identities against nine simple class queries, handler order, declining
and recursive signalling, handler expressions with effects, closures, cleanup
replacement, special bindings, `:NO-ERROR`, zero and 130 values, and signalling
after a 3,000-step tail chain. The unchanged loader cold-installs the same modules
with identical results. Seven malformed proxy inputs refuse at each placement
and observation mode (28 checks). Ten compiler mutations are rejected: nine by
semantic/resource assertions and one by a ten-second progress deadline with the
active case recorded. Native execution uses CCL's debugger hook to observe ERROR
fallback; an outer condition handler would incorrectly consume declining SIGNALs.

All 587 inherited MVC modules are byte-identical to the reviewed R2 modules.
The inherited corpus, nineteen mutants, copy/handoff observations, long tail
chains and regressions also run. Condition runtime helpers are emitted only in
modules that signal; there is no new ordinary-call path. Native R6/R6a passes
21,843 tests in each build, 162 of 164 original FASLs unchanged while registered
and all 164 identical after removal.

This unit deliberately supplies condition **proxies**, not a CLOS implementation.
The owner provides six immutable D1 simple-vectors containing a tagged membership
mask and an identity. The native oracle uses actual condition instances. The
proxy layout is private fixture state; no production condition layout or class
registry is adopted. The reserved handler-symbol import is owner installed.
Production symbol installation must keep that runtime identity distinct from
user symbols. User-defined classes, compound types, condition construction and
slots, implicit checked-error conversion, restarts, debugger entry and moving
collection remain open. An unhandled explicit ERROR is checked refusal 15 at the
debugger boundary. Resource and collector limits inherited from R2 still apply.

Packet: `ccl-evidence/2026-09-17-stage1-b-conditions-r2`. Original failed attempts
are retained, including the incorrect initial native oracle and dropped dispatch
body. The verifier rebuilds both corpora and all mutants, replays native
qualification, and compares cold installation. Byte-identical prerequisite
payloads are referenced rather than copied again. No timing claim is made.

R2 fixes the source-scope defect from Claude's eighty-second audit. The pre-expander
processes user expressions without macro privileges before expanding a handler.
This includes handler functions, protected forms, clauses, nested handlers and
`:NO-ERROR` defaults. Only generated scaffolding may use the private CASE/LIST/POP
rewrites. Fourteen added refusal cases pass; controls reproduce the reviewed
NIL-key counterexample and reject both missing guards and inherited privileges.
R1 remains retained with its defect; R2 awaits external review.

The result-mode investigation executes six focused scenarios against native CCL
and unchanged target code, then counts operations in a labelled observation
variant. Two nested scalar calls under a producer allocate no arena blocks but
create two callee descriptors and execute three releases. Returning 130 values
into a scalar operand, discarded form or cleanup still allocates one block and
performs two release visits. A callee forced to bounded mode refuses the valid
scalar case. This is avoidable storage work, but removing it requires separating
a call's result demand from any internal operation that consumes all values.
The investigation changes no production mode propagation and makes no timing
claim. Result-demand handling is the next proposal before further condition work.
