# Stage 1 bootstrap strong-table substitute

User decision: **“Use the Stage 1 strong substitute.”** Bootstrap tables that
would be weak in native CCL may retain both keys and values in Stage 1. Weak
semantics remain owed in Stage 2. This changes lifetime, memory use, counts and
enumeration after collection; `hash-table-weak-p` must report NIL. It is not a
weak collector implementation, and does not authorize dropping equality tests
or introducing finalizer behavior.

This auxiliary proposal supplies a portable owner constructor and an exact
source-derived list of 21 candidate constructor sites in level-0, level-1 and
lib. These are definition sites, not a reached-startup completeness claim;
optional library constructors are outside this selection. All source bytes and
positions are retained. `selection.py` replaces only each selected `:weak`
argument with NIL and preserves the complete remaining native constructor form.
The unchanged pinned native image executes all 21 original/adapted pairs,
checks their test, rehash settings and weak status, and distinguishes EQ, EQL
and EQUAL using distinct equal strings and separately parsed bignums.

`strongPlan` requires the explicit versioned policy and preserves equality,
size and rehash settings. `createStrongEQ` materializes the 18 EQ sites using
the unchanged accepted C/Wasm hash service, with strong flags from birth. It
checks placement and owner capacity before calling the service. No collector
flag is relaxed. The two EQL sites and one EQUAL site retain their proper
plans but refuse materialization until those equality services exist. They
are not silently reduced to EQ.

The Wasm test runs all 18 EQ sites at 256 KiB and 2 GiB. The table is the sole
root for a heap key and value; three successive moves preserve both while
reclaiming an unrelated cons. Old spaces are poisoned before lookups. This
is 36 constructions, 108 collections, exact live/reclaimed byte checks, and
171 directed refusals. All 21 plans are checked; five policy faults and the
unadapted native weak-constructor control are rejected.

Scope: trusted owner and service instance, fixed-capacity normalized backing
vectors, single Worker, Node execution. The constructor retains requested
rehash settings as metadata; growth is still outside the accepted hash service.
This does not install native HASH-TABLE wrapper instances, select startup roots,
or qualify browser execution. The owner must reserve these disjoint regions and
publish/root the returned table before collection. LL15 remains open. No shared
compiler/runtime change or slot credit; review precedes integration.

```sh
python3 tests/wasm/stage1/bootstrap-tables/run.py --evidence ../ccl-evidence --output /tmp/bootstrap-tables-new
python3 tests/wasm/stage1/bootstrap-tables/packet.py verify --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-20-stage1-bootstrap-tables-r1 --output /tmp/bootstrap-tables-replay
```

Development failures are retained: the first native probe accidentally reused
constant-folded bignums (fixed by separate parsing); the next harness read the
collector's object count as a byte count; and the first extent control also
refused in the unchanged primitive, so it did not isolate owner admission.
The corrected control observes that no primitive call occurs for an invalid
owner extent. No runtime service changed during those corrections.
