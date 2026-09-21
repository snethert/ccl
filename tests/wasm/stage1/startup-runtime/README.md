# Portable startup runtime and collector statistics

Proposal for LL15, not integrated and no slot credit. Replaces the withdrawn
native timeval/macptr buffer proposal with live collector-owned statistics and
its generated five-value GCTIME consumer. The compiler, collector C service,
and B leaf adapter are unchanged.

`classification.json` binds all 35 callbacks to the original selection hash,
including group identity (the user registry also has ordinal zero). Both host
providers have explicit dispositions. The native DB reset is withdrawn; its
absence is not a closure proof. A selected image must still demonstrate no live
native database handles or omit the subsystem. The classification does not
claim the callback snapshot exhausts the 167-unit startup worklist: definition
bodies, loader prerequisites and ordinary-condition activation remain owed.

The owner overlay creates session counters at construction and accounts every
successful copy, including the second copy during growth. Refused copies do not
increment them. Time measures the collector call, using monotonic microseconds
(default: performance.now converted to integer microseconds). It excludes owner
validation, memory growth and mutator work. Timing failure cannot turn a
committed collection into a refusal: count/bytes remain usable and GCTIME
explicitly reports timing unavailable. There is no EGC in this admitted owner,
so native's five slots are total, full, zero, zero, zero. A new owner starts at
zero; an image must not restore another session's counters.

The snapshot service captures all counters before assuring allocation space.
It boxes arbitrarily large nonnegative counts as D1 bignums, returns one vector,
and the unchanged compiler implements GCTIME using five SVREFs and VALUES.
The owner-installed adapter follows the accepted internal B protocol. The
snapshot vector and bignums survive a collecting cleanup; fixed, dynamic and
retained delivery are executed. Returning a snapshot allocates 24 bytes plus
any bignums. This is introspection work, not a numeric hot-path change.

The service is a trusted owner capability: its descriptor and publication
scratch are pinned, disjoint owner regions outside all heaps/stacks/root lists.
The fixture checks their admission, publication and refusal behavior. A zero-argument named GCTIME entry reads the snapshot through a live
function cell and an owner-supplied special descriptor. A generated caller
uses that binding; removing its table entry or binding prevents execution.
The final production symbol catalog and startup schedule join remain LL15
work, not a claim of this packet.

Native GCTIME runs against synthetic five-timeval inputs in a disposable pinned
U1 process, restoring the original static cell before freeing each buffer.
Native `timeval->milliseconds` supplies the alternate-unit oracle, including
half-even rounding and bignum boundaries. This uses native buffers only to
measure the reference; none exists in the proposed port runtime. The unchanged
compiler's accepted R6/R6a record is reused by hash. Fresh generated execution,
forty existing owner checks and focused faults cover the changed behavior.

Replay:
```
python3 tests/wasm/stage1/startup-runtime/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-20-stage1-startup-runtime-r1 \
  --output /private/tmp/ccl-startup-runtime-review
```
