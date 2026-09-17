# Per-callee result scratch

The [isolated proposal](../../../tests/wasm/stage1/b-result-scratch/README.md)
separates the caller's delivery protocol from the callee's local result storage.
A conservative scan of each function's own compiler IR proves when all scratch
requirements fit four words. It includes initializers and lambda-list defaults;
unknown operators and calls, transfers and larger VALUES forms keep the existing
dynamic path. No named function is assumed to retain its current binding.

Proven-small callees use ordinary rooted scratch, omit their dynamic descriptor
and do not release an arena scope. Their return still follows the continuation's
delivery mode, including direct producer delivery. Public B signatures, loader
roles, continuation layout and root shapes do not change. An independent
pre-emitter operation witness checks the proof and the emitted entry choice.

The focused operation-count witness changes two nested scalar callees from two
descriptors to zero and reduces releases from three to the producer's one. Both
versions allocate zero arena blocks. Seven controls reject incorrect proofs,
omitted default/initializer traversal, universal inheritance and lost dynamic
delivery. Eighteen additional native scenarios exercise retention, branches,
closures, special parameters and rebinding to a many-valued function. The
inherited MVC and corrected conditions suites remain required, along with native
R6/R6a and cold installation. No timing or speed claim is made.

This does not implement general first-value/discard propagation. A function with
unknown calls or large intermediate values still uses dynamic storage beneath a
producer, even when its caller needs only one value. That further change needs a
result-demand protocol covering internal multiple-value consumers and nonlocal
transfers. Disabling dynamic mode without that distinction is a tested refusal
of otherwise valid native code.

The proposal derives from [conditions R2](b-conditions.md). Both await external
review and acceptance; the shared implementation remains accepted MVC storage
R2. No Stage 1 inventory slot is claimed. The new packet is
`ccl-evidence/2026-09-17-stage1-b-result-scratch-r1`.
