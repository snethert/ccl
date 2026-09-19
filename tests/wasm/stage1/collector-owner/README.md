# Collector owner admission and growth

An auxiliary single-Worker owner for the accepted collector. The shared backend,
C collector, loader and kernel do not change. This proposal claims no LL06 or
LL18 slot. Its collector digest is integrity against the owner's trusted catalog,
not code signing.

`owner.mjs` admits disjoint, backed memory regions and a copying-only, non-EGC
profile. NIL and T's actual objects must live in pinned image regions outside
all stacks. The two movable semispaces, three Lisp stacks, C stack, TCR, scratch,
root list, bootstrap bindings and external slots each have declared ownership.
Admission checks every pinned-image object extent before walking its tagged
fields. Raw headers, padding and scalar metadata are not roots. Four explicit
external slot lists cover module constants, callbacks, registry and host roots;
they name storage, not a complete callback or loader protocol. TCR v2's sole
direct tagged root, next_method_context, is added separately and checked against
the schema by the runner. The accepted collector still scans explicit frames,
results and the binding vector.

Collection requires a synchronous owner boundary with roots already published.
This API does not prove that generated code has published every live temporary.
`ensure` first collects, then grows and evacuates into a new semispace pair if
needed. It does not advance the allocation pointer. Host DataViews are refreshed
immediately after real memory growth. Engine and policy limits refuse explicitly.
Old spaces remain backed but retired after pair growth: this simple policy has
a monotonic memory high-water mark. A failed ensure may already have collected
or grown memory; preservation means live objects and current roots remain valid,
not transaction rollback of the entire call. Scratch capacity is independently
bounded and may refuse a larger graph.

The executable checks cover sole-path survival through each external root group,
the TCR root and pinned image function/symbol fields; omission controls; raw
metadata exclusion; canonical ownership; immutable admission metadata; reclaim
before growth; live graph evacuation; actual growth to 2 GiB plus one page;
unsigned heap addresses above 2 GiB; stale versus refreshed host views; and
owner, engine and resource refusals. The oracle poisons retired space. Eight
single-site owner mutants must fail at eight named diagnostics.

Two functions compiled by the accepted backend also run here: CONS construction
and a two-value CAR/CDR reader. Native CCL supplies their expectations. Eight
inherited-harness comparisons qualify the generated functions; the owner then
executes twelve constructions and thirteen reads across movement and growth.
The owner ensures space at the public boundary after publishing arguments.
Unused condition-service imports have inert fixture bindings, so this composition
claims only the successful constructor/reader paths. No internal generated
allocation slow path has changed. Adding rooted retry/reload at those sites,
complete LL06 safepoint coverage, registry installation and multi-Worker stopping
remain future work. The existing moving collector and native R6/R6a evidence
are reused by exact compiler, C source and module identity.

```sh
python3 tests/wasm/stage1/collector-owner/run.py \
  --evidence ../ccl-evidence --output /tmp/collector-owner-new
python3 tests/wasm/stage1/collector-owner/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-19-stage1-collector-owner-r1 \
  --output /tmp/collector-owner-replay-new
```
