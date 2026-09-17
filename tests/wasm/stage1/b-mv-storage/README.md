# Multiple-value producer storage correction (proposal)

This replaces the withdrawn `b-multiple-values` proposal. It is not integrated
and claims no Stage 1 inventory slot. The public candidate B signature and the
ordinary compiled-call structure stay the same. Internal continuations now initialize the two previously unused metadata words described below. The internal profile is
`wasm32-shared-B-exnref-tail-mv-storage-v1`; mixing its continuation metadata with
the previous profile is not supported.

The changes address all three observations in audit 79:

* A MULTIPLE-VALUE-CALL producer has demand-sized temporary result storage,
  independent of the enclosing function's final output reservation. The corpus
  includes 130 and 1,024 values consumed by calls reserving four output words.
  Final public returns still obey their caller-owned output extent; finite stack,
  temporary storage, heap and source-reader limits remain checked resources.
* A literal MVC callable and its environment use nonescaping stack storage, with
  relocation during tail transfer. Captured variable cells and genuinely escaping
  inner closures retain heap storage. Native comparisons include an escaping
  closure created by a temporary callable.
* A called producer transfers ownership of its completed temporary buffer instead
  of copying it into a caller return buffer. Immediate call and VALUES producers
  can target the continuation directly. The MVC then publishes the complete
  argument range. Necessary operand staging and tail-argument relocation remain.
  `copy_cost.py` counts actual `memory.copy` executions in an explicitly labelled
  observation derivative, including a semantically correct extra-copy mutant.

## Temporary storage and roots

Only producer evaluation and its descendants enter the dynamic-result mode.
Continuation words 20 and 28 carry that mode and its recipient descriptor; public
adapters clear both. Ordinary callers continue using their existing result
reservation. A producer's recipient remains live through tail transfers.

The Worker owns a temporary-result arena through TCR `tsp_base`, `tsp`, and
`tsp_limit` (80, 76, 84). Allocation uses checked i64 extent arithmetic, initializes
new words to NIL, reuses free blocks, coalesces adjacent free blocks, and releases
buffers by their live scope owner. Trailing free storage is reclaimed. This is a
proposal for temporary result storage, not a Lisp heap allocator or a general
implementation of the native temp stack.

A 32-byte indirect root descriptor has previous-root at 0, marker `0xffffffff`
at 4, data pointer at 8, word capacity at 12, and raw scope owner at 16. Its buffer
is the sole scanner of those physical value slots. Descriptor word 20 is zero.
A direct recipient is unlinked metadata with word 20 set, and names the argument
destination; the continuation root takes ownership at publication. No poll or
Lisp call occurs between writing that destination and publishing its root range.

Buffers have a 16-byte allocator header (block bytes, scope owner, usable words,
marker). An owner of zero means free. A completed result can be reowned by its
recipient without copying. Catch, block and cleanup records in dynamic mode use
an indirect descriptor at offset 48, with its address in control word 28. Their
ordinary tag root retains two slots. Transferring values into or out of these
records moves ownership, including across exceptions. In particular, retaining
a successfully completed protected form performs no allocation which could
bypass its cleanup.

The fixture checks unique physical scanners, live buffer ownership, normal and
exceptional reclamation, finite storage exhaustion, and guard bytes. Collection,
relocation of these new indirect roots, and stack-object handling by a production
collector remain unqualified; the existing collector-time obligations are not
claimed closed.

## Run and replay

From the repository root, with retained inputs in `../ccl-evidence`:

```sh
python3 tests/wasm/stage1/b-mv-storage/native.py \
  --evidence ../ccl-evidence --work /tmp/mv-storage-native-work \
  --output /tmp/mv-storage-native
python3 tests/wasm/stage1/registration/qualify.py \
  --output /tmp/mv-storage-native \
  --inputs ../ccl-evidence/macos-u1-inputs \
  --kernel ../ccl-evidence/2026-09-12-native-census-r7/baseline/build/dx86cl64 \
  --destination /tmp/mv-storage-qualified
python3 tests/wasm/stage1/b-mv-storage/run.py \
  --evidence ../ccl-evidence --native /tmp/mv-storage-native \
  --qualification /tmp/mv-storage-qualified --output /tmp/mv-storage-run
```

Use fresh output paths. `verify.py --evidence ../ccl-evidence --packet PACK`
requalifies R6/R6a, recompiles the corpus and every compiler mutant, executes the
oracles, and replays the loader composition. The copy observer changes only its
own derivative; those binaries are never offered to the production loader.
