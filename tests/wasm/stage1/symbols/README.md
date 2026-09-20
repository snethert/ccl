# LL09-a symbols and packages

Proposal only. No shared compiler, runtime or kernel changes. The unchanged
accepted compiler emits thirteen B modules in a disposable pristine U1 copy.
They call a C/Wasm symbol service through an internal B adapter, with no
JavaScript on the lookup/intern path. The compiler's R6/R6a is reused by exact
identity with accepted LL21-a; native semantic answers are freshly executed.

The service implements INTERN, FIND-SYMBOL, MAKE-SYMBOL, SYMBOL-NAME and
SYMBOL-PACKAGE over D1 symbols, UTF-32 strings, eight-cell package objects and
native-shaped `(vector . (count . limit))` package-table descriptors. Generated
EQ, SYMBOL-VALUE, SET and PROGV exercise the resulting real symbol objects.
NIL is stored in buckets via its separate symbol pointer but returned as the
canonical NIL. Keywords are external, constant, special and self-valued.

The owner admits a sealed package graph before lookup. Tables use versioned
FNV-1a over character code points and bounded linear probing. The JavaScript
image builder and Wasm agree on every query hash. A foreign version causes a
whole-set validated scratch rebuild before publication; claiming version 1 for
foreign buckets refuses. Admission validates reachability, not a preferred
collision insertion order. INTERN copies the name and checks space for both
objects before any write. Capacity failure preserves image, configuration and
result words; admission may overwrite expendable scratch on failure.

The native trace has 582 rows, including names colliding in different packages,
24 hashes colliding at the last bucket, case distinctions, empty strings,
embedded NUL, Unicode, NIL, T, keywords, uninterned symbols and inherited versus
private names. Real native KEYWORD membership is captured before execution;
CL test exports use a private package containing the real NIL and T identities.
An independent Python identity/package model checks every native answer.

Each primitive and generated run loads a pointer-aware image snapshot halfway
through the trace, changes its base, poisons the old region, re-admits, and
continues against the same native answers. Canonical NIL/T stay fixed. Ordinary
image bases are 4 MiB, 8 MiB and 2 GiB. Unsupported and unbacked bases refuse
before writing. A pointer-looking **fixnum** value must remain unchanged during
relocation. Dynamic bindings, same-named symbols with distinct binding indices,
EQ and canonical/keyword reads run both before and after loading. The six B
calling forms cover tail calls, APPLY, retained values, value binding, direct
producer delivery and indirect descriptors.

Twelve implementation faults and eight independent publication controls must
fail at named assertions. Source, tool, baseline image and packet hashes bind a
fresh deterministic replay. See `scope.json` for the ownership and language
limits; this is not the production xloader or a full Common Lisp package system.

```
python3 tests/wasm/stage1/symbols/run.py \
  --evidence ../ccl-evidence --output /tmp/symbols-new
python3 tests/wasm/stage1/symbols/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-20-stage1-symbols-r1 \
  --output /tmp/symbols-replay-new
```

One synchronous trusted owner supplies configuration, disjoint scratch, pinned
image storage and callable entries. Query strings are bounded and package
designators are admitted objects, not names. Raw malformed-owner refusals do not
claim validation of arbitrary forged heaps. Package allocation has a checked
fixed limit, without collection or growth. The adapter is an owner-installed
runtime leaf; it is not a production loader catalog entry. No timing or browser
qualification is claimed.
