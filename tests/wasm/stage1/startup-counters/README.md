# GC counter startup storage

Auxiliary proposal for the first two system startup callbacks:
`*TOTAL-GC-MICROSECONDS*` and `*TOTAL-BYTES-FREED*`. Not integrated; no slot credit.
A trusted single-Worker owner substitutes a fresh reservation in a pinned slab
for native malloc. The service zeroes its 80-byte (five macOS U1 timevals) or
8-byte buffer and returns the D1 macptr. Generated SET publishes that exact pointer
into the global symbol cell, then records completion. Repeated initialization
uses fresh storage and preserves the previous buffer. The two callbacks also run
in sequence and under cleanup through the unchanged compiler and leaf adapter.

The untouched native registered callbacks run twice in a disposable native image;
the oracle checks zero bytes, result/global identity and distinct live allocations,
restores the saved global cells, then frees the new buffers. No native GC algorithm or timing behavior is claimed. D1 macptrs
have subtag 31 and three raw words (address, domain, type); the 80-byte buffer
preserves the reference platform's byte extent, not a new portable timeval ABI.

The owner must grant a disjoint slab outside stacks and moving heaps. Storage is
pinned; production disposal, macptr scanning and GC-statistics consumers remain
open. The owner is digest-bound, reserves before callback execution, and never
collects or grows memory. This is not a full malloc implementation. The original
compiler's R6/R6a qualification is reused by exact hash.

The focused controls reject missed zeroing, a wrong published count, omitted
address/alignment/kind checks, and reused storage. Refusal cases isolate those
guards with otherwise consistent owner state. All publication words start poisoned.

Replay:
```
python3 tests/wasm/stage1/startup-counters/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-20-stage1-startup-counters-r1 \
  --output /private/tmp/ccl-startup-counters-review
```
