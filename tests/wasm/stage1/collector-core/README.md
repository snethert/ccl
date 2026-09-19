# First moving collector service

An isolated **auxiliary proposal**, not an LL18 result. A freestanding C service
compiled to Wasm now copies live D1 conses and the admitted node/byte objects
between owner-supplied semispaces. Real CCL-generated Lisp calls it at explicit
poll service entries. This is executable collector machinery; the complete
production root/admission and allocation-retry contract still needs work.

The allocation walk fixes object starts before any root is followed. The copy
queue preserves cycles and identity. Raw payload words and scalar TCR fields are
not roots. Root updates are staged until validation completes, so a refusal
leaves source space, roots and TCR publication unchanged; scratch and inactive
space may change. The root chain is checked for cycles rather than assumed to
be address-ordered: a surviving producer descriptor can sit below its caller's
continuation. Binding vectors are raw interior roots. Indirect result buffers,
inline results, stack callables and owner-registered external slots have explicit
scanners. No Lisp code or safepoint runs inside the service.

The compiler proposal has three changes: unbinding uses a non-growing lookup;
capture access reloads its environment through the continuation's rooted SELF;
local self-calls read that same updated SELF. Actual movement exposed both stale
address paths. They remain unchanged in the shared checkout until review and
acceptance. The accepted LL17 `v_many` form now has a native-backed execution case.

The corpus has 22 generated modules, 14 native cases / 56 comparisons and 34
collections, with stack/heap placements on both sides of 2 GiB. Retired space is
poisoned. Running closures, recursive local calls, dynamic bindings, pending
exits and retained inline/arena values preserve their native results, and every
collection visibly reclaims allocation. Seventy-five independent core checks
include random cyclic graphs and failure atomicity. Eight C mutants, two compiled
stale-reference mutants and a growing-unbind control are rejected. Native
R6/R6a and the inherited generated/lazy corpora qualify the changed backend.

## Replay

```sh
python3 tests/wasm/stage1/collector-core/native.py --evidence ../ccl-evidence \
  --work /tmp/collector-native-work-new --output /tmp/collector-native-new
python3 tests/wasm/stage1/collector-core/run.py --evidence ../ccl-evidence \
  --output /tmp/collector-execution-new
python3 tests/wasm/stage1/collector-core/inherited.py --evidence ../ccl-evidence \
  --output /tmp/collector-inherited-new
python3 tests/wasm/stage1/collector-core/packet.py verify \
  --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-19-stage1-collector-core-r1 \
  --output /tmp/collector-review-new
```

## Admission and remaining work

The owner reserves the C stack, bounded scratch, extra-slot list and disjoint
semispaces. The collector is a separate host-installed Wasm kernel service, not
a Lisp module admitted by the lazy loader. Static symbols and image registries
are pinned in this unit; the owner supplies their mutable heap-reference slots.
Its layout allowlist is narrower than all CCL heap kinds. The temporary-result
arena and explicit stack do not move; their tagged contents do. EGC, weak
objects, moving code/registry installation, full image-root admission, allocation
retry and growth/view refresh are not qualified here. The tests run on a memory
already grown to the fixture maximum. General producer/consumer temporary
reloads remain LL06; this unit supplies a real mover with which to test them.
SETF of SYMBOL-VALUE remains outside the accepted LL17 source subset.

There is no timing claim. Each capture access now follows rooted SELF rather
than retaining an address across a possible collection. Later liveness analysis
can reduce reloads while retaining the same safepoint contract.
