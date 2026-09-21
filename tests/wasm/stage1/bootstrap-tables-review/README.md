# Bootstrap table capacity and strong populations — audit 132 follow-up

Auxiliary proposal. No shared compiler or runtime changes, integration or LL15
credit. The original table fixture and statistics packets remain immutable.

## Capacity and the populated EQUAL dependency

A fresh disposable copy of the pinned native kernel/image measures the three
large EQ tables before the probe creates anything: `%setf-function-names%` and
its inverse each have 1,281 entries; `%lambda-lists%` has 1,049. The derived
owner now requires `liveCount`. Capacity is the next power of two above
`max(source size hint, liveCount + max(16, ceil(liveCount/4)))`, at least four.
All three require 2,048 slots. Caller capacity must equal that result; there
is no default of 64 or implicit truncation. The test inserts the measured
number of distinct heap keys and values, keeps only the table rooted, and
moves it three times at both placements. Contents are synthetic; this is a
cardinality and movement test, not migration of those native objects.

The fixed service ceiling remains 16,384 entries. A plan needing more refuses
before construction; headroom means a count above 13,107 already refuses.
After installation, exceeding capacity gives the existing checked FULL status
4 and preserves table and publication words. The test fills all 16,384 slots
and checks the next insertion. There is no eviction or automatic growth.
Other image tables require their own measured counts at image construction;
the remaining one-entry scenarios do not claim to measure them.

The same native probe finds **eight EQUAL entries in `*combined-methods*`**.
`dependencies.json` records this as **BLOCKS_BOOTSTRAP**, requiring an EQUAL
service and wrapper installation. EQL remains unavailable as well. Neither
is replaced with EQ, excluded without proof, or declared closed by this unit.

## Populations

The user explicitly extended the policy: **“Use strong retention for populations
too.”** The four constructor paths (system locks, threads, all generic functions,
and public `make-population`) receive that disposition. The fourth is a generic
constructor site, not evidence that exactly four live population instances exist.

`population.mjs` builds a Stage 1 strong representation from ordinary scanned
vectors and conses: a two-element vector `[kind, head]`, with kind 0 for a list
or 1 for an alist, encoded as fixnums. It copies the spine and alist pairs,
retains member identities and order, validates the complete reservation before
writing, and sets no weak header. Native `make-population` supplies the copy
and type conventions. Tests mutate the caller arrays, keep only the population
rooted, move it three times, poison old space, and check all member contents,
exact live bytes and garbage reclamation at both placements.

This does **not** implement native population layout/accessors or make native
weak objects collectable. Production must lower population construction and
access to this representation, root the returned object before a safepoint,
and admit each actual member object's scanner. Lock/thread/GF object layout
and bootstrap linkage remain explicit dependencies. Strong retention extends
lifetimes and changes post-GC membership/counts; Stage 2 owes weak behavior.
No finalizers or weak-alist disappearance are simulated. The constructor is a
trusted image-builder operation: member words must already refer to owned,
rooted objects, and the reserved destination must not overlap those objects.

## Admission and statistics publication

Redundant min/max/power-of-two capacity clauses are replaced by one exact
comparison with the validated plan. Directed cases observe **both** size-query
and initializer entry so downstream validation cannot hide a missing preflight
check. A real service bound to a smaller memory returns failure on an otherwise
admitted request; the owner must throw rather than publish a descriptor.
Weak-mode and retention-label checks are explicit.

The unchanged reviewed statistics service's unavailable-clock path is called
directly with all four result words complement-poisoned. Omitting its last two
stores, publishing a wrong count, or publishing a wrong rehash word each fails.
This closes audit 132's minor residual without changing statistics code.

## Replay

```sh
python3 tests/wasm/stage1/bootstrap-tables-review/run.py --evidence ../ccl-evidence --output /tmp/tables-review-new
python3 tests/wasm/stage1/bootstrap-tables-review/packet.py verify --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-20-stage1-bootstrap-tables-review-r1 --output /tmp/tables-review-replay
```

The run performs 108 table and 30 population collections, 15 directed owner
checks (including a full 16,384-entry table), and rejects 13 faults. It reuses
the accepted hash/collector binaries by their retained hashes; no compiler or
C code changes, so native compiler qualification is reused. Node only.

Development: the first capacity control was still masked by a mismatched
extent; the second added call observation but kept that mismatch. The final
case supplies a coherent smaller extent so only the population bound rejects
it. Both original escapes are retained. Another run correctly rejected the
missing population-value edge earlier than its expected diagnostic, at the
independent live-byte check; the control records that first failure now.
