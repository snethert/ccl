# S1-LL19-a — generated control and recovery

19 September 2026. Executed proposal, pending Claude review and project
acceptance. Shared compiler/runtime files and the upstream kernel are unchanged.

The compiler now connects checked type, bounds, arity and unbound errors to
Lisp handlers and active restarts. Improper APPLY tails carry the native datum;
condition readers expose native slot meanings. Conditions use D1 instance and
slot-vector layouts under a sealed owner bootstrap registry, replacing LL05’s
private mask vectors. Native U1 supplies the twelve classes’ slot order/defaults.
General CLOS class construction/redefinition remains LL11.

The generated debugger hook runs with itself masked and can recover through a
restart; its depth and binding restore after nested errors. Before ordinary
error service activation, an unhandled error produces a structured fatal
record. This is the runtime debugger boundary, not an interactive debugger UI.

Nested cleanup, replacement exits, bindings and complete values use the
accepted exnref/control protocol. A source-derived observer checks cleanup-entry
VSP, TSP, CSP, roots and bindings. Separate CSP entries link to the rooted VSP
control records. Soft limits for all three stacks signal STORAGE-CONDITION
using a reserved region; recovery re-arms it and nested reserve exhaustion is
checked. Explicit interrupt polls respect dynamic masking and re-enable while
leaving the collector service available.

Qualification: 107 generated modules, 46 native cases and 184 target comparisons;
32 additional target resource/protocol comparisons; thirteen recompiled compiler
mutants, five source refusals and six independent publication controls. The
inherited B, condition and call-error corpora execute 7,332, 848 and 288
comparisons. Cold installation, 36 full loader cases and fourteen loader mutants
are requalified. Native R6/R6a tests 21,843 cases, restores all 164 FASLs exactly,
and checks all existing target module profiles.

The [fixture README](../../../tests/wasm/stage1/control/README.md) gives replay
commands. Its [scope record](../../../tests/wasm/stage1/control/scope.json)
explicitly excludes general restart options/condition association, moving GC,
full symbol/class installation, cross-Worker publication and host re-entry.
`STAGE1-CONTROL-R1` retains execution, controls, exact compiler and original
failures. `coverage.json` maps the inventory assertion to concrete retained
observations; the result is NOT_REVIEWED, not an acceptance.
