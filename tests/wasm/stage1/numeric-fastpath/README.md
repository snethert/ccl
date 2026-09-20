# Numeric allocation fast path (proposal)

The LL16 benchmark exposed about 80 microseconds per floating operation. Full
pinned-image enumeration ran on every allocation assurance; its test observer
also cloned the semispace manifest on every operation. A checked/unchecked ratio
near one concealed this absolute cost. This packet measures absolute cost against
both the reviewed implementation and native CCL.

The runtime-only proposal caches lookups into the owner's immutable copied region
manifest and separates live-state checks from root enumeration. Sufficient-space
assurance still checks allocation ownership, all stack bounds/cursors previously
checked, binding-vector ownership, result extent, memory limit and NIL/T. Image
headers and root-list capacities are checked on admission and before collection's
first write. A fast assurance is no longer an audit of unrelated pinned-image
headers. Every collection inventories the current image; no mutable shape or root
value is cached. Collection no longer enumerates the image twice.

The floating service and Lisp adapter reuse DataViews, refreshing them whenever
memory.buffer changes, and the adapter precomputes the two immutable integer
limits. No compiler, arithmetic, condition, loader or allocation-policy change.
The three proposed files are derived from the integrated runtime; shared files
remain untouched pending Claude review and acceptance. No new gate credit.

Validation reuses pinned LL16 native answers and binaries, executes the complete
eager/cold corpus with forced movement, extends owner refusal tests, and replays
the raw floating owner's boundary corpus. Focused faults remove the live check,
restore per-allocation scanning, cache mutable image shapes, omit canonical
checks and omit view refresh. A result is reused as an operand after real growth
to distinguish refreshing a cached view from merely publishing through a new one.

Timing uses the same six 64-operation compiled loops on each side. Both Wasm
variants omit the harness's allocation observer, retain production checks, reset
the heap between entries and do not collect inside the measured interval. Native
CCL compiles the same forms at safety 1/speed 1 and includes allocation and GC.
Twenty 125-ms paired checking trials follow warmup per Wasm variant. The two
implementations run sequentially, so the numbers are descriptive, not an
interleaved statistical superiority test or application benchmark. The residual
cost still includes generated frames, Wasm/JS calls, checked operand staging into
private memory, arithmetic/flag calculation, result validation and boxed copying.
It must not be called native-speed arithmetic.

```
python3 tests/wasm/stage1/numeric-fastpath/run.py --evidence ../ccl-evidence --output /tmp/numeric-fastpath-new
python3 tests/wasm/stage1/numeric-fastpath/packet.py verify --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-20-stage1-numeric-fastpath-r1 --output /tmp/numeric-fastpath-replay-new
```

Measured on the recorded Xeon W-2140B / Node v25.6.1 host:

| Workload | Reviewed runtime µs/op | Proposal µs/op | Native CCL ns/op |
| --- | ---: | ---: | ---: |
| add | 76.39 | 4.76 | 17.12 |
| sub | 76.28 | 4.78 | 16.94 |
| mul | 76.20 | 4.77 | 16.01 |
| div | 76.17 | 4.77 | 16.23 |
| single | 74.14 | 3.10 | 3.75 |
| mixed | 74.38 | 3.17 | 22.88 |

The four double-arithmetic workloads improve about 16×, but remain roughly
278–298× slower than native CCL. This fixes the repeated scan; it does not close
the numeric performance gap. Scalar generated arithmetic needs a further fast
path that avoids the general service boundary. LL16 remains unaccepted.
