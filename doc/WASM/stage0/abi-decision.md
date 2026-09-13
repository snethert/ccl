# S0-ABI-selection — formal record of the B decision

Decision date: **12 September 2026**. Record prepared: **13 September 2026**.
Status: **complete desk record; independent review and acceptance pending**.
Packet `ABI-DESK-DECISION-R1` is retained in `2026-09-13-abi-decision-r1`, identified
by the [evidence index](../evidence/index.json).

The project chose **B for simplicity and clarity**. Every Lisp argument follows
one placement rule, avoiding a split between Wasm parameters and overflow slots.
This formalizes the existing [engineering choice](abi-choice.md). The user
explicitly required a dated project rationale rather than an outcome of the
benchmark rule. Policy v2's minima were never met, the rule was not applied,
and this decision makes no claim that B is demonstrably faster.

## Selected contract and correctness basis

B's entry is `(self:i32, nargs:i32) -> (value0:i32, nvalues:i32)`. Self, arguments
and value0 are tagged values; counts are raw unsigned i32. Argument i is at
`incoming_VSP + 4*i`; the caller reserves `align16(4*nargs)` bytes. The callee
publishes its frame before any stopping boundary and restores incoming VSP on
return; the caller then releases the argument area.

Zero values return `(NIL, 0)`. The full ordered result sequence uses the caller's
owned, rooted VSP region, referenced by the TCR descriptor. That region lives
until the owner reuses or releases it. A caller retaining results across another
call first copies them into owned rooted storage. Each physical result slot has
exactly one collector scanner; ownership changes occur without polling. The
[reviewed protocol v0](../abi/dynamic-call.v0.md) supplies the complete ordinary,
tail, callback and exceptional transitions. Its original multi-candidate status
text is historical; the B engineering decision determines implementation use.

The producer requires **all 24 direct and transitive prerequisite variants** to
be accepted under their current contracts, including the C and C4 alternatives.
The ten directly required IDs are grouped below. LL04-a, LL13-a, LL13-c and
LL19-b also enter through their prerequisite edges.

| Required evidence | What supports this decision |
| --- | --- |
| LL05-a/b/c/d and LL21-b, C/C4/B | Ordered arguments, full multiple values, tails and dynamic extent, rooted lazy stubs, frame/debug policy, entry and installation identity |
| LL20-a/b/c | Moving roots, GC admission, concurrent requests and interruptible I/O at the reviewed bounds |
| LL23-b | Logical frame identity, relocated tagged slots, inspection and exceptional restoration |
| LL21-a | Prebuilt code/version identity publication to existing and late Workers |

The [fourth audit and acceptance](project-acceptance.md) establish the dynamic-call
basis: 53 positive cases and 27 rejected controls per candidate. Its bounds remain
32 arguments, six values, 512-byte activations, 16 KiB explicit stacks, up to eight
logical frames, three live Workers, four ownership slots, a 1 MiB memory and two
4 KiB semispaces. Three 100,000-transfer chains per candidate establish bounded
tail behavior within that fixture. They establish no arbitrary-capacity claim.

LL21-a's accepted scope is identity publication: each Worker already holds the
module bytes, and host actors acquire a generation plus digest. It proves neither
delivery of module bytes nor a Wasm-side acquire. Function objects, symbols and
closures in the corpus remain hand-built surrogates. Both debug policies still
materialize roots, so no reduced-storage benefit is inferred.

## Packaging, retained alternatives and continuing work

The correctness fixture uses one callable definition per module plus support
and runtime modules, making cross-instance indirect calls explicit. For the
first generated bootstrap, the [existing proposal](bootstrap-design-review.md)
is a small number of coherent, eagerly installed bundles. This is provisional:
production partitioning remains a Stage 1 decision and no packaging advantage
has been measured by this desk record.

C and C4 remain documented and qualified alternatives at their original bounds.
The original exploratory summaries, runs, policy v2 and policy-change record
remain intact. The three packaging summaries each retain `NO_SELECTION` and
three paired trials, below the thirty-trial minimum. Comparative timing and its
proposed sensitivity and instrumentation work are deferred. H(G) remains an
optional future enhancement with no blocking role.

Generated B code must preserve roots, frames, result ownership, stack checkpoints,
cleanup, bindings, handlers, code identity and entry roles, with ordinary Lisp
conditions at invalid-call boundaries. Engine qualification, census closure and
the contracts join remain mandatory independent work. Startup, scale and memory
must be assessed on useful generated code. This document changes no compiler
author authorization or clean-start rule.

Reopen B only for a demonstrated generated-code correctness problem or a
representative performance problem attributable to it. If comparison is reopened,
first establish sensitivity, representative weights, the engine and granularity
assumptions, and the necessary trials and metrics. No new comparison is requested
by this record.

## Verification and disposition

The [producer](../../../tests/wasm/stage0/abi-decision/README.md) binds the four
desk assertions to the protocol, direction, retained basis and continuing work.
It checks the original accepted-envelope identity and all 29 existing contract
bindings, then selects the 24 prerequisite variants without altering any earlier
result. Runtime-payload verification is reused. Ten negative controls reject
missing or corrupted prerequisites, false measurement claims, a changed argument
protocol and overstated implementation scope. The first producer run succeeded;
the retained verifier and a fresh reproduction pass.

A separate preparation check initially assumed S0-CONTRACTS-a declared this
record as a prerequisite. Its contract does not contain that edge; only the desk
record's identity changes. The original failed expectation and corrected check
are retained. Final contracts review still belongs last in the execution plan.

The new envelope is `DESK DECISION`, `PASS`, `NOT_REVIEWED`. PASS means the desk
record's assertions hold; it claims no fresh runtime execution. The unchanged
gate validates this record and its artifacts. A labeled scoped ledger combines
that result with the unchanged accepted set: **29 accepted, 18 missing and one
unreviewed of 48**. The formal slot still requires independent review and project
acceptance. The implementation choice of B is already in force.

Under the alternating plan, the next census work returns to the 68 native helper
names and four computed helper calls exposed by the reviewed source-expander
packet, followed by the boundary replacements and wider source traversal.
