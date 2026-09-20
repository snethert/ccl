# LL13-a generated initialization and late Workers

Five functions compile through the unchanged integrated compiler in pristine U1.
Native CCL supplies process initialization, mutation, read and Worker-initializer
answers. The same generated modules run with shared objects at 4 MiB and 2 GiB.
The first Worker mutates the shared cons and runtime/staging sentinels, then two
late Workers initialize only their own regions and lazily install their code.
The first Worker stays alive and calls its original published function again.

`owner.mjs` is an isolated portable runtime proposal. It validates the complete
layout, write authority, actual TCR pointer fields, table reservations and every
module's bytes before claiming initialization. The accepted binary reader rejects
active data, start/BSS initialization and element segments before instantiation.
A shared digest binds late joins to the initialized layout. Sequentially consistent
atomic claims distinguish new, busy, ready and failed process/Worker states.
Shared initialization is process-once; private setup is once per Worker identity.
A failed initializer is terminal, not a rollback or an automatically retried action.

All ranges derive from explicit metadata: TCR v2, D1 object widths, generated
module counts and declared bootstrap stack budgets. Empty literal-pool storage is
omitted. No C service is linked, so there is no hidden C stack or static data gap.
The layout is trusted: validation is not confinement of arbitrary initializer code.
Foreign-region hashes and canaries check the actual generated write behavior.
Wasm tables are local to each Worker; logical code identities and registry rows
are shared and unchanged by late installation. This does not qualify a scheduler,
concurrent Lisp/GC, browser execution, production image loading or Stage 2.

Ten owner faults and seven publication controls accompany the positive runs.
The compiler and production runtime are unchanged; accepted R6/R6a is reused by
exact compiler hash, while the native corpus is freshly compiled and executed.
The inherited compiler helper assembles an unused symbol adapter as scaffolding;
it is never installed and has no LL13 execution claim.

```
python3 tests/wasm/stage1/initialization/run.py --evidence ../ccl-evidence --output /tmp/initialization-new
python3 tests/wasm/stage1/initialization/packet.py verify --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-20-stage1-initialization-r1 --output /tmp/initialization-replay-new
```
