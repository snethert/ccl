# S1-LL17-a: generated dynamic bindings

19 September 2026. Accepted and integrated after Claude’s ninetieth audit.
The shared backend equals the reviewed proposal; runtime and upstream kernel
are unchanged. See [acceptance](acceptance-ll17.json) and [integration](integration-ll17.json).

Generated SYMBOL-VALUE and SET use the D1 symbol's immutable binding index and
the owning thread's binding vector. A missing slot reads or writes the global
cell without allocating. Dynamic binding grows the vector when required,
including from zero capacity. NIL, T and registered constant symbols retain
native CCL's constant protection; unbound reads use the Lisp condition path.
FLET and LABELS can shadow the two standard function names without being
rewritten into the new intrinsics.

Growth checks owner bounds and unsigned extents before writing, allocates a
D1 simple vector, copies all prior slots, initializes new slots to the native
no-thread-local-binding marker, then publishes the pointer and capacity. There
is no call, poll or suspension inside that transaction. The TCR roots the old
vector until publication; each binding record roots the symbol and previous
value, and unbinding resolves the current vector. Old heap vectors become
unreachable and await the later collector; bootstrap vector storage stays
owner-managed. This is not native realloc or a process-global dynamic environment.

Forty native cases produce 29 modules and 160 target comparisons at two stack
placements, one above 2 GiB, with and without observation. They cover repeated
bindings, missing PROGV values, error and nonlocal restoration, growth during
cleanup of a pending exit, lambda parameters, closures and lexical function
shadows. Twenty-four owner/resource cases add 96 comparisons, including exact
capacity and allocation boundaries, exhausted second growth and malformed
metadata. Twelve mutated compilers and six publication controls reject.

Two real Worker suspensions preserve live binding and root chains while the
supervisor reads shared state independently. Eight forced vector evacuations
at explicit GC-service entry poison the abandoned vector before growth and
with one or two live bindings. This tests the binding-vector root protocol;
the service is not the general moving heap collector owed by LL18. The TCR's
identity remains 37 even when a symbol uses binding slot 37.

The inherited 587-module call corpus, conditions and call errors, lazy loader,
36 installation cases and fourteen loader mutants rerun against this compiler.
Three old metadata refusals now require successful growth and exact results.
Native R6/R6a checks the exact proposal in disposable U1, including 21,843 tests,
162 unchanged FASLs while registered and all 164 after removal. All five
existing architectures and seventeen target module profiles remain unchanged.

[Fixture and replay commands](../../../tests/wasm/stage1/binding-vector/README.md).
[Scope](../../../tests/wasm/stage1/binding-vector/scope.json) distinguishes owner
symbol installation, raw interior-root treatment, retired storage, resource
refusal, host suspension without re-entry, and remaining general collector work.
The package retains the original failed attempts and a fresh replay. No
acceptance was inferred from successful execution; the separate user decision
is bound to the independent review.
