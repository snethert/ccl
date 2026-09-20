# S1-LL18-b: strong EQ tables under movement

This proposal implements strong EQ backing vectors and qualifies their moved-key
protocol through the unchanged, accepted compiler. It changes no shared source.
It awaits Claude review and user acceptance.

`hash.c` uses D1 hash-vector subtag 74 and U1's fourteen-word payload prefix.
Keys and values occupy alternating words after that prefix. Address-based
mixing and bounded linear probing replace U1's bucket arithmetic. The track-key
and key-moved bits retain their native meaning. The copying collector derives
from the integrated collector: forwarding a bucket key sets key-moved on the
**destination** object, and the next table operation rebuilds the bucket array
in disjoint owner scratch, clears the cache and clears the flag. A failed
collection preserves source objects, roots and the TCR as before. Cache slots
are traced even while rehash is pending. Value-only movement does not set the
key flag.

Nine real compiler-generated modules call the operations through B function
values: tail calls, APPLY, multiple-value binding/retention, and both direct and
indirect producer delivery. The hand-built `adapter.wat` implements the small
runtime leaf boundary, calling C/Wasm directly without a JavaScript round trip.
The adapter's public entry deliberately refuses; callers enter a generated B
wrapper and dispatch internally. Its collector operation is a fixture capability,
not a new production poll service. Two native-compiled forms retain values and
keys across collection inside generated code and across a collecting cleanup.
The retired space is poisoned before generated execution resumes.

The retained run has 1,292 native trace answers, 2,584 primitive comparisons,
2,588 generated/native comparisons, 88 collections, 95 inherited collector
checks and 52 checked-refusal observations across the two execution paths.
Twelve runtime faults and eight independent publication controls are rejected.
The production gate additionally refuses every required-role omission. Actual
installed module bytes, delivery counters, root relocation addresses, native
answers and the independent Python identity-map comparison are retained.

The hash table has a fixed owner-chosen capacity (power of two, 4–16,384).
Full insertion refuses; automatic growth is deferred. This is the strong EQ
backing store and runtime interface, not CCL's HASH-TABLE wrapper, a
MAKE-HASH-TABLE/GETHASH source rewrite, weak tables, user tests, cross-Worker
mutation or production loader installation. Pinned hash vectors remain outside
the production owner's image inventory. `scope.json` lists these boundaries.
Ordinary cache/probe paths do bounded work in Wasm; no timing claim is made.

Run and replay from the repository root:

```sh
python3 tests/wasm/stage1/hash-tables/run.py \
  --evidence ../ccl-evidence --output /tmp/ccl-hash-fresh
python3 tests/wasm/stage1/hash-tables/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-20-stage1-hash-tables-r1 \
  --output /tmp/ccl-hash-replay
```

Compilation runs only in a fresh disposable U1 archive. The integrated compiler
is asserted byte-identical to the reviewed floating-call compiler; its R6/R6a
qualification is reused by exact hash. Native hash operations and both moving
forms are re-executed, every module and runtime binary is rebuilt, and every
negative control reruns during verification. Native kernel/image, U1 archives,
toolchain and executed sources are pinned. `development.json` accounts for all
iterations, including two escaped adapter controls and the first real dynamic
producer case that exposed an overly strict adapter descriptor check.
