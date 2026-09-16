# Generated local functions — 16 September 2026

The isolated LL05 proposal adds FLET, LABELS, lexical self and mutual
recursion, direct literal lambdas, inlined LAMBDA-BIND and literal APPLY.
Local functions retain lexical identity independently of global function
cells. Their shared cells are allocated before the group’s function objects,
so forward references and escaping recursive groups keep their bindings.
Defaults, arguments, rest construction and multiple values use the existing
B ownership protocol. The closure representation is unchanged.

The corpus contains 183 source functions, 241 generated modules, 687
native/model cases and 2,748 target comparisons. Thirty-two source refusals
retain the declared boundary. Additional checks include escaping local
functions after stack overwrite and inline rest-list allocation at its exact
capacity. The inherited closure, callable and result-capacity checks remain.
Sixteen compiler mutations are recompiled; two further regression controls
reproduce the development defects below. R6/R6a passes with 162 registered
FASLs unchanged, the two explained registration artifacts, all 164 restored
exactly and 21,843 native tests. The accepted pristine baseline is reused;
registered execution and restoration are fresh.

Two of Claude’s seventieth-audit observations are resolved: expected root
counts now come from pre-emitter IR and an independent lexical-ancestor
analysis, and the loader no longer materializes unused static inner-function
objects. A metadata-only mutation tests the independent count check. Literal
APPLY is now supported through a syntax-aware private rewrite rather than
refused under an incidental diagnostic.

Development exposed two defects. The first rewrite mistook a LET binding
named APPLY for a call; it now rewrites expression positions only. The fixture
also placed opaque keyword tokens inside its low allocation region, allowing
a closure to decode as a keyword. The regions are now disjoint. Original
failure logs and source snapshots are retained, with exact final reproducing
controls. Two hand-counted allocation expectations were corrected using the
retained IR’s capture identities; those failed assertions are retained too.

The [fixture and replay](../../../tests/wasm/stage1/b-local-calls/README.md)
remain an auxiliary proposal awaiting external review. No inventory slot is
claimed. The shared backend is the accepted closure unit. Local RETURN-FROM,
declarations, local macros, production conditions, authenticated loading,
lazy adapters and collection remain open. Recursive calls consume ordinary
Wasm and Lisp stack; proper Wasm tail transfer is the next substantial unit.

Packet: `ccl-evidence/2026-09-16-stage1-b-local-calls-r1`.
