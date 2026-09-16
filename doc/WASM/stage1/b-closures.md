# Generated lexical closures — 16 September 2026

The LL05 proposal now constructs escaping function objects and their capture
environments in linear memory. Sibling closures share mutable cells; separate
activations get separate cells. CCL's own inherited-variable identities join
nested captures. LET, LET*, lexical SETQ and captured required, optional,
supplied-p, keyword and rest bindings execute through the real front end.

The function layout from the accepted callable unit is unchanged. Its
environment points to a D1 simple-vector of shared D1 cons cells, whose CARs
hold captured values. Each inner function has a separate B module and logical
code ID. Captured cells are conservatively allocated on entry; this includes
unused cells for untaken LET branches. Noncaptured assigned parameters use
private rooted slots and preserve the caller's argument storage.

The corpus has 149 source functions, 177 generated modules and 574 native/model
cases, repeated as 2,296 target comparisons. It includes 129 captures in one
closure, sibling mutation, distinct activations, transitive captures, heap
escape before failure and closure identity. Seventy-two additional checks
cover reuse across JavaScript turns after overwriting the Lisp stack,
malformed environments and heap capacity. Seventeen recompiled compiler
mutants reject. R6/R6a passes: 162 unchanged registered FASLs, two explained
registration artifacts, all 164 restored exactly and 21,843 native tests.

The [fixture](../../../tests/wasm/stage1/b-closures/README.md) removes the unused
Stage 0 slot validator. The primitive and leaf entries remain unchanged.
Original development failures are retained: an inert IR probe, a source-reader
error and a corpus using the still-refused inlined LAMBDA-BIND form.

This is an auxiliary execution, pending external review and integration;
it claims no LL05 inventory slot. FLET/LABELS, inlined LAMBDA-BIND, production
conditions, authenticated loading, lazy adapters, tail transfers and GC remain
open. Function arity/debug slots are still NIL placeholders. Allocation has
no safepoint and uses the checked thread-owned region; root inspection does
not establish correctness under collection.

Packet: `ccl-evidence/2026-09-16-stage1-b-closures-r1`.
