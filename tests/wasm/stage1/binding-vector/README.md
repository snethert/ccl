# LL17 binding vectors and dynamic symbol access

Compiler proposal for S1-LL17-a. Shared implementation stays unchanged.

SYMBOL-VALUE and SET consume actual front-end IR, root evaluated operands and
use the symbol's D1 binding index. Lexical function shadows keep their own calls.
Reads and writes fall back to the global value for an absent thread-local slot;
only creating a binding grows the vector. Unbound values signal the accepted
Lisp condition path. NIL, T and owner-registered constant symbols cannot be set.

Growth allocates a D1 simple vector, copies the entire old population, fills
new slots with 243 and publishes only after all checks and writes complete.
All address arithmetic is unsigned/i64, including the placement above 2 GiB.
The thread owns this non-polling transaction. Existing binding records keep
symbol/index and old value, so restoration resolves the new vector rather than
using a retired address. [scope.json](scope.json) spells out root scanning,
retirement, resource refusal and the remaining symbol-installer/collector work.

The native-first corpus has 40 cases, including nested LET/LET*, specials in
lambda lists, PROGV duplicates and missing values, ordinary and nonlocal exits,
cleanup growth, unbound conditions, constant errors, lexical closures and local
function shadows. Four target runs per case give 160 comparisons. A real Worker
suspends twice with a live binding while its parent independently reads the
shared state. Eight forced vector evacuations at explicit collector-service
entry poison the old words; the observer moves only this root region, not the
whole Lisp heap. The owner-resource corpus adds 24 cases/96 comparisons.

Twelve compiler mutants must reach target execution and fail assertions, six
independent publication controls reject changed observations, and the production
gate rejects every required-role omission. The inherited B/conditions/call-error
corpora and lazy installation re-execute against this compiler. Three old
metadata refusal cases now require successful growth; their original failures
remain in development evidence.

```sh
python3 tests/wasm/stage1/binding-vector/native.py --evidence ../ccl-evidence \
  --work /tmp/ll17-native-work-new --output /tmp/ll17-native-new
python3 tests/wasm/stage1/binding-vector/qualify.py --evidence ../ccl-evidence \
  --native /tmp/ll17-native-new --work /tmp/ll17-work-new \
  --output /tmp/ll17-packet-new
python3 tests/wasm/stage1/binding-vector/packet.py verify \
  --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-19-stage1-binding-vector-r1 \
  --output /tmp/ll17-review-new
```

Native authority: `level-0/l0-symbol.lisp` for SYMBOL-VALUE, SET and constants;
`level-0/ARM/arm-symbol.lisp` for slot fallback and ensuring a binding index;
`lisp-kernel/arm-exceptions.c` for old-value preservation and initialization of
new slots. D1 offsets come from `x8632-arch.lisp`; symbol flag bits from
`library/lispequ.lisp`. All are source-pinned, not copied native addresses.
