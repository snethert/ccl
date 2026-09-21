# Typed strong populations

Auxiliary runtime proposal toward compiling CCL's native population accessors. The accepted strong representation is an ordinary simple vector, which cannot give REQUIRE-TYPE a population identity. This proposal gives strong populations an exact two-field shape under D1's existing population subtag 90. It changes no shared source and does not yet compile REQUIRE-TYPE or claim LL15 completion.

The 16-byte object has header 602 (two fields, subtag 90), type at byte 4, contents at byte 8, and zero padding at byte 12. Type is tagged 0 or 1 (raw 0 or 4). The builder and leaf service derive from reviewed sources. The collector and image owner admit only this exact shape and trace both fields strongly. Native weak populations with three fields and termination populations with four fields remain refused. No GC-link or weak/finalization flags are installed; ordinary vector populations from v1 are not silently converted. The policy identifier is `strong-population-v2`.

The unchanged 22 generated modules reproduce all 32 native cases at both placements: 64 comparisons and 80 collections, with retired space poisoned. This reuses the reviewed selected-source scaffold only as a calling harness. The new pinned-image test leaves the population as the only root of its member list, moves the two reachable conses twice, and independently observes reclamation of an unrelated cons. Image and moving-heap tests run below and above 2 GiB. The existing forty owner checks also pass.

Eighteen shape checks and twenty image checks cover identity, both legal types, ordinary vectors, native weak/termination counts, truncated objects, invalid types and padding. Truncation occurs at memory end, so a missing extent guard traps rather than being masked by later validation. Refusals preserve source objects, TCR and roots; traps fail the test. Twelve individually derived controls cover collector and owner count/extent/type/padding, both data-root scanners, the old builder header and the old service header. Each fails at its named observation. The other service/builder admission checks are unchanged and reuse their pinned evidence.

Native R6 and the native answers are reused by the unchanged compiler and parent packet hashes. The collector binary is rebuilt and exports its C stack pointer for the production owner. This proposal has no timing claim or browser-engine claim.

Still owed: target accessor definitions (type slot 0, contents slot 1), REQUIRE-TYPE and Lisp TYPE-ERROR paths, real API installation, PUSHNEW/POP consumer admission, actual lock/thread/GF member layouts, cross-dumped image census and roots, and the READY join. The equality-key validator does not yet admit this new population shape as an opaque key. Existing v1 objects require explicit image rebuilding or migration before switching services. Do not integrate the consumer source rewriter as a substitute for these obligations.

Replay:
```
python3 tests/wasm/stage1/typed-populations/packet.py verify --packet ../ccl-evidence/2026-09-21-stage1-typed-populations-r1 --output /new/replay
```
