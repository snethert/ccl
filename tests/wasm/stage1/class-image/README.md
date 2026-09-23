# Cold class images and persistent class roots

550 original definitions execute, 515 with non-NIL witnesses: unchanged.
This unit adds a runtime image path, not original-definition credit.

Completed author run: 26,048 unchanged baseline comparisons, 90 producer
comparisons, 180 cold-load comparisons and four persistent-root comparisons.
The consumers perform 616 collections. All 31 admission/lifecycle checks pass.
The initialized image is 216,888 bytes containing 8,606 target objects;
all 612 class cells resolve after restoration. The 46 retained images contain
10,321,480 heap bytes and 1,117,915 explicit relocations in total.

The writer emits D1 heap bytes, relocations and root bindings. The loader
admits a private copy, checks the installed code and service identity, copies
the heap, and publishes its relocated roots. Fresh Workers consume that
artifact at 8 MiB and near 2 GiB. They are explicitly forbidden to call the
graph projector. The source heap is absent; the destination starts poisoned.

The 45 retained class cases run from these images: lookup, cell creation,
condition construction and readers, slots and initargs, handlers and restarts,
implicit failures, table growth, deletion and clearing. Results and mutations
match the native rows, with collection before execution and inside callers.

The stronger startup case runs generated `CORE-CONDITION-OWN-TABLE`: it builds
a new class table and all 612 cells in the target heap. Generated
`CORE-CONDITION-PREPARE` publishes that table into `%FIND-CLASSES%`. The writer
then saves this initialized heap. A second fresh Worker loads that image and
calls generated FIND-CLASS for all 612 names, MAKE-CONDITION and SLOT-VALUE,
with repeated collection. It does not call either startup function or rebuild
the graph. The inherited defaults are 43 and 41, as in the native witness.
The two consumer Workers have independent memories, objects and mutations.

The READY state belongs to this class-image owner. It follows successful
generated checks; admission or copying alone cannot reach it. A failed or
asynchronous initializer is terminal. This is **not the process-wide LL15
READY transition**. The full native cold-initializer worklist, DEFCLASS/class
finalization, and the xfasloader's coordinated writer remain open. The class
metadata is still the accepted native projection, now written ahead of time
into target bytes rather than reconstructed by the consumer. No source
rewriter, native saved image or native address becomes the target heap.

## Image contract

`heap-image.mjs` is a portable runtime proposal, not yet integrated. It uses
the integrated synchronous SHA-256. Its writer scans the complete allocated
range using the collector's admitted D1 layouts. Every node reference must
name an actual object boundary or a declared imported object; padding and raw
numeric/vector payloads are not scanned as pointers. Cycles and sharing retain
their identities. Node pointers in the payload are replaced with relocations.
EQ vectors with pointer keys are marked for rehash after relocation.

Imports name the fixed symbol, string, constant and function-object arenas.
Their bytes, excluding the declared root destinations, are digest-bound.
Root slots come from the trusted owner's allowlist, and every declared slot
must occur exactly once. Root-frame count/head words are raw owner metadata,
not Lisp roots. Import/root/heap ranges are checked before writing. The image
does not serialize stacks, service scratch, native pointers or WebAssembly
instances. Code remains the accepted per-function modules; the manifest binds
their actual installed binaries, including the collector hook, service
binaries, runtime modules and installer. This is trusted-owner identity
checking, not authentication of untrusted Lisp.

The source and destination heap bases may differ. The pinned import arenas
retain their accepted layout; relocation of those arenas is not claimed.
Admission and installation require a quiescent single-Worker owner. They do
not synchronize active mutators or replace InitializationOwner's process
claim. The loader's private copy isolates caller mutation; installation checks
the imported bytes again before any publication. Allocation pointers and
collector root registration remain the owner's responsibility, exercised by
the harness before generated code runs.

## Reproduce

From this source revision, beside the existing evidence store:

```
python3 tests/wasm/stage1/class-image/run.py \
  /private/tmp/ccl-work/codex/class-image-replay/run
```

This uses the bounded P4 cache; a missing session is rebuilt from its pinned
inputs. It runs the existing full corpus once, writes the images, cold-loads
them in separate Workers, tests the initialized class image, and runs the
direct admission/lifecycle controls. It emits `summary.json` and phase times.
The compiler, CCL sources and existing runtime are unchanged; their native
qualification is reused by exact source identity. There is no copied compiler
session archive in this packet.

The author baseline run preceded the final relocation-marker change. Its
worker never imports the new image helper; the exact unused helper bytes are
retained by the hash in that run's manifest. The final writer/consumer/control
runs exercise the final helper. No earlier execution is relabelled as a run
of changed code. On a fresh replay the baseline runs before that helper is
installed, and only its comparison count enters the deterministic summary.

`prepare.py` adds one explicit image boundary to the written P4 harness. It
keeps the native value/mutation/global checks and the existing generated-call
thread-state checks. `class-boot.mjs` drives generated CCL entries; it does not
implement class lookup or condition construction in JavaScript.
