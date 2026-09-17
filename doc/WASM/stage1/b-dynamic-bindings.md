# Special lambda parameters and PROGV — 17 September 2026

The [isolated proposal](../../../tests/wasm/stage1/b-dynamic-bindings/README.md)
extends the accepted special-binding unit to required, optional, rest, keyword
and supplied-p parameters, including inline lambdas and local functions, and to
PROGV. The user accepted this unit after Claude’s seventy-seventh audit; its exact
reviewed bytes are integrated. It claims no LL05/LL19 slot.

Defaults see the bindings established before them. Keyword lookup stages values
and supplied flags, then binds in lambda-list order; it never publishes later
keyword parameters early. Every parameter extent restores the previous dynamic
state on normal return or failure, including failure during initialization.

PROGV follows U1's front-end ordering: validate symbols, evaluate values, then
establish bindings. The target revalidates after values because that expression
can mutate the symbol list. It checks proper finite structure, constant/global
flags, preassigned indices and explicit stack capacity. Missing values bind the
unbound marker; excess values are ignored. Repeated symbols unwind in reverse
order. The same rooted records support cleanup and nonlocal exits.

The corpus contains 362 source functions, 443 generated modules and 1,506
native/model cases, producing 6,024 comparisons at low and above-2-GiB stack
placements. It reaches 128 simultaneous bindings, with 24,388 binding inspections.
Twenty-four target-only refusal checks cover invalid flags, post-values cycles,
record-capacity exhaustion before values effects, and malformed values after a
partial binding. The earlier 44 metadata checks remain. Twenty-one compiler
mutants and three inherited development regressions use the ordinary oracle.
Native R6/R6a passes: 162 unchanged FASLs, two explained registration
artifacts, all 164 restored FASLs, 21,843 native tests, five architecture tables
and 17 existing-target profiles. The unchanged loader's lazy composition passes;
compiled calls use zero public wrapper dispatches. The retained verifier
recompiles the complete corpus and all mutants byte-identically, reproduces
each first failure, and replays native qualification and lazy composition.

Development found a missing extent around an inlined lambda's special parameter;
its binding leaked after return. The fixed path evaluates operands first, then
wraps bindings and body together. The original failure and a mutant that removes
that extent are retained. Other failed drafts and incorrect fixture expectations
are listed separately in the packet's development record.

The owner still assigns three private symbols and fixed vector capacity. General
symbol installation, index allocation, vector growth, global proclamations,
condition objects and handlers, host re-entry and collector integration remain
open. U1's native PROGV limit derives from its native stack; this target uses
explicit checked capacity instead. Native comparisons exercise up to 128
bindings. The target-only malformed-input and resource probes are not claims
about native behavior on undefined input. Active binding extents prevent tail
transfer, while their callees retain proper tail calls.

Packet: `ccl-evidence/2026-09-17-stage1-b-dynamic-bindings-r1`.
