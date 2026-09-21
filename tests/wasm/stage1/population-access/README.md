# Strong population access

Auxiliary LL15 prerequisite, executed but not integrated. This supplies the
checked data reader, data setter and raw type-code reader for the accepted
ordinary-vector population representation. It does not reinterpret native weak
population offsets or re-enable finalization.

The freestanding C/Wasm leaf validates the exact two-element vector and type
code, then reads or sets its contents and publishes exactly one value. SET
shares the supplied list spine as native CCL does; NIL, proper, dotted and cyclic
lists are allowed. There is no allocation, poll or callback between validation
and publication. Invalid inputs refuse with checked codes; translating those
into public Lisp conditions is still a binding-layer obligation. The raw type
code is 0/1, not the keyword returned by public POPULATION-TYPE.

The native oracle calls untouched MAKE-POPULATION, POPULATION-CONTENTS and its
SETF function, POPULATION-TYPE and the native raw slot reader. It verifies copied
constructor spines, preserved member identity, shared setter spines and failed
setter preservation. The target uses the integrated builder and collector,
including members whose only root is the population. It does not qualify the
layout of arbitrary lock, thread or GF objects; the members here are conses.
Actual native macro/accessor lowering and installation in the selected image
remain open.

Four Workers below/above 2 GiB exercise primitive and six accepted generated
calling forms: 792 observations, 296 collections and six rejected compiled
faults. Old space is poisoned after collection. All four publication words are
poisoned before direct success, independently of what the adapter consumes.
The adapter differs from the accepted hash adapter only by its one-value count;
its fixed, direct and indirect dynamic delivery paths all execute. The nine
compiler-produced caller modules are reused byte-for-byte.

```
python3 tests/wasm/stage1/population-access/packet.py verify \
  --packet ../ccl-evidence/2026-09-20-stage1-population-access-r1 \
  --output /tmp/ccl-population-review
```
