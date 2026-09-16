# Generated proper tail calls and temporary literal APPLY

This isolated LL05 proposal extends the reviewed local-function backend.
Eligible calls use actual Wasm `return_call_indirect`; observation wrappers use
`return_call` too. Direct, FUNCALL, APPLY, lexical, self and mutual calls share
the path. The public B signature remains `(self, nargs) -> (primary, count)`.
Calls that must retain values or perform a later effect remain ordinary calls.
No cleanup/binding extent is silently discarded: those source forms are still
outside this slice.

An ordinary B entry creates one private continuation above the caller-owned
output reservation. It saves the incoming arguments and ownership, copies the
arguments into its own root record and calls its internal tail entry. The
internal signature adds a raw continuation pointer. A paired per-Worker table
holds those entries at the same slots as the B entries; range and null checks
precede dispatch. Both tables and registry metadata are owner-supplied, with
production authentication still assigned to the loader. No production TCR
field or public B function-object field changes.

A tail site evaluates its designator and arguments into temporary roots,
validates APPLY's list and extent where applicable, and resolves the live
callee before changing the continuation. An overlap-safe copy reuses the
argument area, clears padding and publishes the new SELF and root count.
The temporary roots are retired and the original output reservation restored
before `return_call_indirect`. There is no call or poll during relocation.
The public wrapper restores its original caller on both return and exception,
including the old result count on failure. Context geometry is in
[layout.json](layout.json). A complete initial-frame check precedes all context
writes; the original implementation's too-late check is a retained mutant.

Literal APPLY is marked privately before pass 1, avoiding U1's native
literal-APPLY destructuring rewrite. Its anonymous callable cannot be observed
as a Lisp value, so it uses checked stack storage. A tail transfer copies that
object with the arguments and rebases its environment pointer before the old
frame is reused. Captured cells retain conservative heap allocation, and an
escaping inner closure owns its own heap object and environment. Thus the
uncaptured literal needs no heap; the existing captured example uses eight
bytes for its cell instead of forty for cell plus callable. This is not an
escape-analysis optimization for arbitrary closures. GC support for temporary
stack objects remains an explicit later obligation.

The corpus keeps the native CCL and independent logical model comparison,
physical ownership checks and pre-emitter root-count witness. Long-chain
checks execute 100,000 transfers at both memory placements, plain and observed,
with a 2 KiB Lisp-stack budget. They include changing arities up to 130,
zero/130 values, local mutual recursion and a final error with three old values
restored. Tail boundaries have two root frames; input arguments, heap usage,
output tails and stack fences are checked. A pending-effect recursion must
instead fail at the checked stack limit. Missing tail entries, heap-free
literal APPLY and a closure escaping literal APPLY across stack overwrite have
separate checks. Compiled mutants distinguish real tail instructions, frame
retirement, copying, ownership, arity and temporary-object relocation.

This is an auxiliary proposal, not a complete LL05 execution or permission to
integrate unreviewed code. Dynamic bindings/cleanup, production conditions,
lazy authenticated installation and collection remain open. Ordinary nested
calls still consume stack; tail calls do not remove genuine per-step heap
allocation such as rest lists. The shared backend remains the accepted
local-function unit until external review and user acceptance.

Run from the repository root with fresh directories:

```sh
python3 tests/wasm/stage1/b-tail-calls/native.py --evidence ../ccl-evidence --work /tmp/b-tail-work --output /tmp/b-tail-native
python3 tests/wasm/stage1/registration/qualify.py --output /tmp/b-tail-native --inputs ../ccl-evidence/macos-u1-inputs --kernel ../ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 --destination /tmp/b-tail-qualified
python3 tests/wasm/stage1/b-tail-calls/run.py --evidence ../ccl-evidence --native /tmp/b-tail-native --qualification /tmp/b-tail-qualified --output /tmp/b-tail-run
python3 tests/wasm/stage1/b-tail-calls/verify.py --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-16-stage1-b-tail-calls-r1
```
