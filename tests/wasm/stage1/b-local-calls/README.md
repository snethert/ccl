# Generated local functions and inline lambda calls

This auxiliary LL05 proposal adds FLET, LABELS, lexical self and mutual
recursion, direct literal lambdas, U1's LAMBDA-BIND IR, and literal APPLY.
It extends the reviewed closure backend; the leaf and typed primitive entries
are unchanged. The shared checkout keeps the accepted closure backend until
this proposal has external review and user acceptance.

Local functions use the existing B signature and checked callable resolver.
CCL can omit function-cell captures when its native backend directly calls a
local entry. This emitter supplies those lexical cell identities, propagates
them through enclosing closures, and constructs each function group after
allocating its shared cells. Forward and cyclic references therefore retain
the same function objects across calls. FLET definitions see the enclosing
function namespace; LABELS definitions see their whole group. Quoted symbols
still name global function cells. Escaping local functions retain their cells
after the stack is overwritten between host calls.

LAMBDA-BIND stages all arguments in rooted slots before assigning parameters,
then evaluates defaults in order and builds any rest list in the checked
thread-owned allocation region. Literal APPLY is rewritten to a private LET
before pass 1 to avoid U1's native destructuring helpers. Only expression
positions are rewritten: binding names, lambda-list syntax and quoted data
are preserved. The first rewrite mishandled a variable named APPLY; its failed
compile and a reproducing regression control are retained.

The Python environment model, native CCL and generated Wasm compare every
returned value, object identity, mutation and exceptional effect. Separate
literal byte counts check allocation. Root-count expectations now come from
a forwarding pass-2 observer's pre-emitter IR, with lexical ancestor analysis
in Python, independently of the emitter's environment fixed point and module
metadata. A metadata-only mutant proves those expectations are independent.
The loader creates static objects for top-level functions only; inner modules
receive code registry rows and dynamically created function objects.

The fixture also retains the keyword-handle overlap found during development:
a newly allocated closure had the same token as an opaque keyword. Keywords
now occupy a separate region. A harness mutant restores the overlap and the
ordinary identity oracle rejects it. Neither this correction nor the IR
observer changes the production ABI.

This is a bounded compiler slice, not a complete LL05 execution. Local
RETURN-FROM, declarations and local macros remain refused. Registry rows are
owner-supplied; authenticated installation, lazy adapters, production Lisp
conditions, collection and allocator slow paths remain open. Recursive calls
currently use ordinary Wasm calls and consume stack; proper tail transfer is
the next unit. Result reservations still propagate per call depth. Allocation
has no call or poll window and does not claim concurrent mutation safety.

Run from the repository root with fresh output directories:

```sh
python3 tests/wasm/stage1/b-local-calls/native.py --evidence ../ccl-evidence --work /tmp/b-local-work --output /tmp/b-local-native
python3 tests/wasm/stage1/registration/qualify.py --output /tmp/b-local-native --inputs ../ccl-evidence/macos-u1-inputs --kernel ../ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 --destination /tmp/b-local-qualified
python3 tests/wasm/stage1/b-local-calls/run.py --evidence ../ccl-evidence --native /tmp/b-local-native --qualification /tmp/b-local-qualified --output /tmp/b-local-run
python3 tests/wasm/stage1/b-local-calls/verify.py --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-16-stage1-b-local-calls-r1
```
