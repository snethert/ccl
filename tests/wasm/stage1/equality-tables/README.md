# Bootstrap EQL and EQUAL table services

Auxiliary proposal, not integrated and no LL15 credit. This closes the missing
comparison service prerequisite for the three non-EQ bootstrap tables; image
wrapper and binding installation remain separate work.

Two freestanding Wasm binaries derive from the integrated strong EQ service.
They keep the fourteen-word backing-vector prefix and GET/SET/REMOVE/COUNT
publication ABI. The owner checks the binary's comparison role and applies the
accepted measured-capacity policy. No weak bits, collector changes, compiler
changes, allocation, poll or JavaScript comparison callback are introduced.

EQL compares canonical D1 bignum digits, raw single/double bits, and recursive
ratio/complex components. EQUAL additionally compares finite cons trees, simple
UTF-32 strings and simple bit vectors. Other admitted heap objects compare by
identity. Double padding and unused bit-vector bits do not participate. Opaque
hash contributions are address-independent, including inside pinned structural
keys; exact comparisons resolve collisions. This deliberately gives symbol-only
keys many collisions. This unit makes no performance claim.

Each operation validates the argument, resident and cached keys before changing
the table. Structural walks are bounded at 1,024 pending objects and 65,536
visits; cyclic structural keys refuse. The owner supplies canonical objects and
object starts, disjoint from the C stack; this is not a hostile-heap validator.
Macptrs, scalar boxed complex floats, displaced arrays and pathnames are not
admitted. Mutation of a key while installed is outside the contract. Capacity
remains fixed, with the accepted 16,384 ceiling and preserving FULL refusal.

The pinned native image supplies 47 logical objects and both predicate matrices.
Its real EQL/EQUAL hash operations independently agree with those matrices with
FP traps masked. At the default mask, native EQUAL hashing a NaN signals
FLOATING-POINT-INVALID-OPERATION; that boundary is asserted and retained. This
service does no FP arithmetic and does not reproduce native hash FP traps.
The captured bootstrap keys do not contain floats.

A snapshot taken before reporting finds EQL tables of 0 and 97 keys and the
seven-key EQUAL combined-methods table. Their key graphs are serialized by
identity. Method instances become identity-only D1 instance placeholders, so
this proves list-key comparison and relocation, not materialization of native
method bodies or the port's eventual heap census. Copies of EQUAL list spines
resolve to the same entries. Re-census the actual port image at image build.

Eight Workers cover both comparisons below/above 2 GiB through primitive and
six accepted generated calling forms. 70,688 matrix-derived observations,
1,248 captured-key lookups and 23,596 collections pass, with retired space
poisoned. The nine accepted generated modules and adapter are reused exactly;
the unchanged integrated collector is rebuilt. Ten compiled faults are rejected,
including identity-only comparison, incorrect padding, pointer-based full-table
replacement and duplicate rehash, address hashing and omitted publication.
No new native compiler build is claimed or needed for this runtime-only change.

Replay:

```
python3 tests/wasm/stage1/equality-tables/packet.py verify \
  --packet ../ccl-evidence/2026-09-20-stage1-equality-tables-r1 \
  --output /tmp/ccl-equality-review
```
