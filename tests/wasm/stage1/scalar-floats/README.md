# Direct Wasm scalar arithmetic (complete runtime proposal)

This finishes the numeric-cost correction begun by `26d99600`. The reviewed
compiler and its 76 LL16 modules are unchanged. The existing three-i32 numeric
import binds directly to a Wasm function, so eligible scalar operations make no
JavaScript call and copy no operands or results through private service memory.
Both commits are proposals for Claude's review; no shared runtime is integrated
and LL16 remains unaccepted.

The fast path supports finite single/double values and fixnums in arithmetic,
exact comparisons and FLOAT conversion. It preserves single-precision operand
rounding, signed zeros, same-format FLOAT identity and the complete returned
status word. With checked underflow or inexact enabled, nonfinite values,
bignums, integer-only division, invalid state or insufficient space, it delegates
before any write to the existing Lisp service. That service retains all current
condition, coercion, native-compatibility and collector behavior. Those cases
are deliberately outside the performance claim.

Ownership checks are still present. A read-only owner admission snapshot supplies
stack/binding bounds and one mutable boundary flag. The Wasm helper checks live
TCR geometry, distinguished objects, the argument frame and object extents.
Pinned-region membership is another Wasm function, generated as a binary search
from copied immutable spans. Overlapping declarations use the old first-span
semantics via fallback. After a slow call, cached semispace bounds refresh from
the real owner, including on failure. A shortage may collect or grow before
refusing, just as before. Fast publication has no call or safepoint between its
first write and final root publication. There are no new collector root shapes.

The owner capability is still trusted-owner identity, not code signing or an
untrusted-host boundary. The binary is digest-bound and has an exact import and
export set. Supplying `scalarBytes` and `scalarDigest` selects the new binding;
omitting them preserves the existing capability. The production owner must
supply the scalar binary when adopting this fix. The loader and module ABI need
no change, and the normal path returns the actual Wasm export, not a JS wrapper.

Qualification replays every LL16 generated comparison in eager and cold modes,
below and above 2 GiB. A test-only pressure wrapper exhausts free space before
entering the real Wasm function; normal and timed imports are direct. The full
floating-only portion of the accepted rational corpus checks returned status
bits as well as values, plain and under movement. A throwing replacement for the
slow import proves the fast cases do not call JS, and proves excluded cases
fallback without writes. Directed faults cover arithmetic, identity, precision,
ownership, capacity, FP mode, boundary state and post-growth cache refresh.

Timing uses the same 64-operation loops as LL16, without its allocation observer,
and freshly compiled native CCL. Both old-owner and new-scalar runs use identical
inputs and checking modes. The separate service-only loop holds one root frame
for the batch: its difference from the generated loop includes temporary-frame
work, Lisp loop bookkeeping and multiple-value delivery, not stack work alone.
Wasm timings exclude collection; native timings include GC. These are descriptive
single-host measurements, not cross-engine or application performance claims.

```
python3 tests/wasm/stage1/scalar-floats/run.py --evidence ../ccl-evidence --output /tmp/scalar-floats-new
python3 tests/wasm/stage1/scalar-floats/retention/packet.py verify --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-20-stage1-scalar-floats-r1 --output /tmp/scalar-floats-replay-new
```

Retained qualification: 72,200 comparisons and 31,836 collections per eager/cold
run; 145,804 independent raw comparisons, 56,200 raw collections and one real
growth; 109 direct-path checks, ten rejected faults and 10,138 region checks.
The inherited comparison count includes the reviewed q1/q2 duplicate generated
variant; it is not a claim of 72,200 independent target programs.

Retained medians on macOS 15.7.9, Xeon W-2140B, Node 25.6.1 (ns/operation):

| Workload | Owner fix only | Direct Wasm | Native CCL | Target/native |
| --- | ---: | ---: | ---: | ---: |
| add | 4759.3 | 152.1 | 17.41 | 8.7× |
| sub | 4744.1 | 153.5 | 17.19 | 8.9× |
| mul | 4779.3 | 153.7 | 16.11 | 9.5× |
| div | 4746.0 | 146.7 | 16.32 | 9.0× |
| single | 3098.8 | 139.2 | 3.75 | 37.1× |
| mixed | 3188.0 | 129.8 | 22.86 | 5.7× |

Double arithmetic improves another 31–32× over the owner-only proposal, roughly
500× over the earlier observer-free ~76 µs measurement. Native still wins by
about 9×. Single coercion has a wider ratio: native single floats are immediate
on this x86-64 host while this wasm32 layout boxes them. No claim applies to
the fallback cases or to application throughput.

The separate persistent-frame addition loop measures 93.2 ns/op versus 152.1
for the generated form. The ~59 ns difference includes temporary frames, Lisp
loop bookkeeping and value delivery, with separate host reset harnesses; it
does not isolate stack-management cost. The service still validates live
ownership and boxes the result. Development runs r2/r3 used an inappropriate
raw-test reset for this one timer (image clearing and owner-layout cloning);
those measurements are retained and excluded from attribution. The final
reset removes those unrelated operations. Fresh replay timings are retained
separately and are not required to be byte-identical.
