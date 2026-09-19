# Live restarts and temporaries across collection

An auxiliary proposal following the accepted collector core. It fixes three
compiler paths exposed by actual movement and adds the restart scanner that the
ninety-first audit found missing. The shared backend and runtime remain at that
accepted core until this derivative is reviewed.

* EQ stages both operands in a temporary root frame and reloads them after the
  second operand. A collection in the right operand previously made a cons
  unequal to itself.
* Captured initialization evaluates the value before loading the cell address.
  There is no call or poll between that address load and its store. The old
  ordering wrote the old space after a collecting LET* initializer/default.
* The implicit-error service retains its condition in the existing frame's
  padding, now declared as two more root words. Its four result words remain
  separate. SIGNAL and the debugger reload that root; a declining handler could
  previously collect and leave the debugger a stale condition.
* The C scanner admits six-slot istructs (D1 subtag 130, header 1666), scanning
  all six node fields and ignoring alignment padding. These are the restart
  objects emitted by the accepted constructor: type cell, name, action, report,
  interactive function and test. Other istruct counts still refuse. This is a
  layout admission, not a claim to implement all native istruct classes.
* Canonical T is a pinned identity like NIL, never a stack-temporary callable.
  Its fixed value lies within the low fixture stack's numeric range; the old
  scanner consequently refused a collection with T among the live roots.

The 30 native-derived cases produce 63 modules and 120 comparisons, with 62
collections across two observed placements, one above 2 GiB. Every collection
poisons the retired space and reclaims genuinely dead allocation. Cases cover
restart identity, expiry, nested transfer, handler/cleanup collection, captured
initializers and assignments, EQ ordering, cons operands, calls, APPLY, rest
lists, multiple values, special bindings and PROGV. The ordinary debugger-mode
case uses the inherited harness's `d_` convention. Another 56 comparisons and
34 collections replay the previous moving corpus with this service and compiler.

The independent C suite has 95 checks, including each restart field separately,
cycles/sharing, raw padding, canonical T and refused istruct counts. Four actual
compiler mutants and five actual C mutants are recompiled and rejected at named
oracles. Native R6/R6a and the inherited generated/lazy suites cover the compiler
delta. The U1 layout sources are pinned with the packet.

```sh
python3 tests/wasm/stage1/collector-live/run.py --evidence ../ccl-evidence \
  --output /tmp/collector-live-execution-new
python3 tests/wasm/stage1/collector-live/native.py --evidence ../ccl-evidence \
  --work /tmp/collector-live-native-work-new --output /tmp/collector-live-native-new
python3 tests/wasm/stage1/collector-live/inherited.py --evidence ../ccl-evidence \
  --output /tmp/collector-live-inherited-new
python3 tests/wasm/stage1/collector-live/packet.py verify --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-19-stage1-collector-live-r1 \
  --output /tmp/collector-live-replay-new
```

This is not LL06 or LL18 qualification. Collection still occurs at explicit poll
service entry, not inside allocation/store windows. Complete image-root
admission, allocator retry, memory growth and the complete LL06 control matrix
remain open. The low fixture uses canonical NIL/T as distinguished values rather
than materialized cells; production region ownership must reserve their real
objects separately from all stacks. The temporary stack and inline callables
remain nonmoving. EQ now pays a temporary root frame; a future no-safepoint proof
can remove unnecessary frames without changing this correctness rule. No timing
claim is made. Existing capture reloads remain as accepted.
