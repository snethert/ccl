# Generated callable objects and live bindings — 16 September 2026

The next LL05 proposal replaces opaque function handles and host-side name
resolution with generated object checks and table dispatch. Named calls,
FUNCALL and APPLY resolve a function object at dispatch; FUNCTION reads the
current symbol function cell. Retained old objects continue to call their
own code after redefinition. Table linking permits self-recursion and mutual
recursion without cyclic module imports.

The proposed function representation holds five tagged words: logical code
ID, environment, version, arity metadata and debug metadata. Symbols retain
D1's layout and function-cell offset. The fixture materializes these objects;
it does not yet emit lexical closure allocation or construct an image.
Arity/debug metadata slots are NIL placeholders; arity checks remain in code.
The [layout](../../../tests/wasm/stage1/b-callables/layout.json) distinguishes
this replacement from native code-bearing function objects.

Generated validation checks complete headers and spans, code/version encoding,
registry range and version, signature/role metadata, table bounds and null
entries. The resolved object replaces the rooted designator and becomes
SELF. Registry metadata remains owner-supplied; authenticated installation
and actual-entry identity belong to the loader work.

The corpus has 108 generated functions and 456 native/logical cases, repeated
as 1,824 Wasm comparisons at low and above-2-GiB stack placements. Native
setup changes and restores the same bindings as the target scenarios. Tests
include quoted and FUNCTION values, changed bindings, retained functions,
APPLY, recursive retention and checked stack exhaustion. Sixteen compiler
mutants are rejected; 88 callable checks supplement the inherited capacity
and allocation controls. R6/R6a passes with 21,843 native tests, 162 unchanged
registered FASLs and all 164 restored exactly.

A development corpus encoded binding tuples in Python syntax instead of Lisp
lists. The reader refusal and consequent missing-module attempt are retained;
the renderer was corrected before execution. No compiler defect was found.

The user accepted this unit after Claude’s sixty-ninth audit found no defect.
The exact payload is [integrated](integration-b-callables.json), without LL05 slot credit. Lexical closure construction
and mutation are next; full conditions, lazy adapters, tails, GC and concurrent
publication remain. Distinct fixture objects preserving environment fields
prove object identity and SELF forwarding, not capture semantics.

[Sources and replay commands](../../../tests/wasm/stage1/b-callables/README.md).
Packet: `ccl-evidence/2026-09-16-stage1-b-callables-r1`.
