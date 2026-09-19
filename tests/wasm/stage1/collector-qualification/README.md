# S1-LL18-a: generated small-heap collector qualification

This proposal completes the pointer-free LL10 layout widths in the freestanding
collector and pinned-image scanner, then qualifies collection through the
unchanged integrated compiler. It changes no shared compiler or runtime file.
The compiler is byte-identical to the accepted constructor-retry unit, whose
reviewed native R6/R6a is reused by hash.

Run from the project root:

```sh
python3 tests/wasm/stage1/collector-qualification/run.py \
  --evidence ../ccl-evidence --output /tmp/ll18-new --controls
python3 tests/wasm/stage1/collector-qualification/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-19-stage1-collector-qualification-r1 \
  --output /tmp/ll18-review-new
```

The generated retry corpus supplies 301 native comparisons over seven heap
configurations, 539 collections and 141 growths. The same 302 observations,
including refusal after movement, reproduce with cold installation. Explicit
polls supply 120 native comparisons and 62 collections while temporaries,
bindings, conditions, restarts, closures and result descriptors are live.

Actual compiler-generated literal pools exercise all LL10 families, cycles,
sharing, NaN payloads and partial-byte bit vectors. They move below and above
2 GiB and also load from a pinned image: 453 native comparisons and 237
collections. Cold pools are collected before module installation. Returned
values and child closure pools are checked again after movement; retired spaces
are poisoned. Raw u32 words deliberately look like valid pointers and must retain
their numeric bits.

Generated conses each have exactly one declared external root family. A generated
callback closure is invoked after movement. Actual active multiple values are
moved and read back. Independent byte accounting observes unreachable allocation
reclaimed; an undeclared tag-like word neither retains nor changes its object.
A tagged interior pointer in a declared root refuses without publishing changes.
The existing 95 core checks and 40 owner checks cover bounds, legal stopping
boundaries, memory growth and maximum refusal, host-view refresh, and EGC refusal.

Seventeen single-site C/owner mutants run against these executable oracles.
Eleven publication mutations separately exercise the assessor. The bit-rounding
and raw-word scanning controls fail on literal data, rather than only on an
inventory count. Failed development inputs and first diagnostic expectations are
retained. The reviewed core oracle has six repeated test labels for distinct raw
width cases; its 95 entries are checks, not 95 distinct labels.

See [scope.json](scope.json) and [coverage.json](coverage.json). The owner remains
single-Worker, requires an honest root manifest, appends new semispaces on growth,
and may move roots before a later assurance refusal. Callback slots are declared
owner roots, not a new external callback implementation. Hash tables are LL18-b;
the complete temporary/control matrix is LL06-a. Unknown object layouts refuse.
A signalling stack guard never resumes its interrupted reservation.
