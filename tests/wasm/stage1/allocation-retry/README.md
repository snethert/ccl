# Internal allocation retry

Auxiliary proposal, not an LL06 or LL18 result. The accepted compiler, collector,
owner and lazy loader in shared source remain unchanged. This derives the compiler
from the accepted collector-live proposal and calls the accepted owner through a
small, synchronous `owner.ensure(i32 bytes)` capability.

`compile-retrying-call-module` and `compile-retrying-call-form` opt into retry.
The existing entry points keep their old profile and emit identical Wasm for the
comparison corpus. The existing lazy loader deliberately refuses the new function
import. The test owner instantiates these trusted, generated modules eagerly;
there is no claim that a new lazy-loader profile is installed or authenticated.
The capability cannot run Lisp callbacks. Its failure becomes checked code 6.

The emitted fixed-size allocator and variable rest-list allocator test space in
64-bit arithmetic. Only a shortage calls the service. The allocation pointer is
loaded after the service and the existing bounds checks still run, so a service
that returns without making room cannot bypass the guard. Operands, captured
cells, SELF and incoming arguments remain in their existing root records;
construction reloads them after collection. No call, poll or collection occurs
from the first object write through publication. Construction remains all-or-none.
Ordinary allocations that fit do not call the service or the helper function.

This covers CONS, captured cells, heap closures, local-function environments,
inline rest and general rest/APPLY lists. Binding-vector growth, restart and
condition constructors still have their old checked exhaustion paths. Complete
root/safepoint qualification, those other allocation sites and lazy-loader
admission remain required before LL18/LL06 credit.

The corpus compares native values, object identity, mutations and complete
multiple values with generated execution. Small semispaces force movement during
construction prerequisites; another placement has real heap addresses above
2 GiB. Retired spaces are poisoned. Cases include calls and escaped closures,
local recursion, captures, optional/keyword defaults, EQ, rest/APPLY, literal
APPLY's stack callable, dynamic producers, active bindings, cleanup, CATCH and
BLOCK exits. Independent literal expectations must match native CCL before any
Wasm comparison. A separate resource case refuses growth *after* moving a live
object: its cleanup must reload and mutate that object before the checked
exception returns. Failed assurance is explicitly not rollback.

Six compiler mutants exercise omitted retries, reuse of the old allocation
pointer, unrooted EQ, early captured-cell address calculation and cached closure
environments. Every mutant is compiled through the real front end and must reach
its named execution failure. Native R6/R6a rebuilds the final proposal in a
pristine disposable U1 copy. The C collector and owner reuse their reviewed bytes.

```sh
python3 tests/wasm/stage1/allocation-retry/run.py --qualify \
  --evidence ../ccl-evidence --output /tmp/allocation-retry-new
python3 tests/wasm/stage1/allocation-retry/native.py \
  --evidence ../ccl-evidence --work /tmp/allocation-native-work-new \
  --output /tmp/allocation-native-new
python3 tests/wasm/stage1/allocation-retry/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-19-stage1-allocation-retry-r1 \
  --output /tmp/allocation-replay-new
```
