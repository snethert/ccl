# Bootstrap weak-object heap census — audit 133 follow-up

Auxiliary evidence, no slot credit or shared runtime/compiler changes. This
replaces the three-table measurement with a snapshot of **every weak hash
table and population object** observed by CCL's `%map-areas` over all heap
areas in a disposable copy of the pinned kernel/image.

The walk finds 19 weak tables containing 6,550 entries, and 22 population
objects containing 739 members. These are counts at capture time, not bounds
on future bootstrap definitions or session growth. No collection is forced.

## Attribution and capacity

Every table is joined by EQ identity to an owning reference and a source
constructor, not guessed from its size or contents. Named cells, the inspector
package, FTD fields, a pair's CDR, and CCL's named closure captures cover every
observed instance. Both FTD globals point to one table and are recorded as
aliases, without double counting. The reverse join checks that each declared
owning table also appears in the walk. Unknown or ambiguous attribution fails.
The two source sites with no matching instance are retained explicitly; they
do not get an invented one-entry measurement.

| Table owner | Entries | Capacity with the existing headroom rule |
| --- | ---: | ---: |
| setf function names | 1,281 | 2,048 |
| inverse setf function names | 1,281 | 2,048 |
| binding-index reverse map, captured by `binding-index-symbol` | 1,121 | 2,048 |
| lambda lists | 1,049 | 2,048 |
| documentation | 945 | 2,048 |
| slot-ID table, captured by `ensure-slot-id` | 724 | 1,024 |
| EQL specializers, captured by `intern-eql-specializer` | 97 | 128, **blocked EQL service** |

The eight-entry EQUAL combined-methods table and the 97-entry EQL specializer
table are both **BLOCKS_BOOTSTRAP**, with their captured owners and constructors
in `dependencies.json`. The empty inspector EQL table also requires its service
before materialization. No EQ substitution is allowed.

The target harness now consumes instance measurements only. It executes all
16 observed EQ tables at both placements, fills each to its captured count,
moves it three times, checks every key/value and every post-movement lookup,
and verifies exact live/reclaimed bytes. EQL/EQUAL instances refuse construction
without writes. Counts are tested using fresh synthetic keys/values, not by
copying arbitrary native objects. Fixed capacity, the 16,384 ceiling and FULL
semantics remain as previously qualified; growth is still not implemented.

## Population instances

The instance census corrects the earlier four-path inventory:

- system locks: 155 members;
- threads: 2 members;
- generic functions: 582 members;
- 18 empty lists in the nine method-combination metadata records, allocated
  by `%cons-mci` in `library/lispequ.lisp`, two populations per record;
- one empty **terminatable alist**, not an ordinary weak list, rooted by
  `*termination-population*`.

Each object is attributed by identity, with a reverse join from the globals
and both population slots of every method-combination record. The 21 ordinary
populations exercise the unchanged strong builder and collector with their
actual member counts at both placements. The termination object is recorded
as **BLOCKS_BOOTSTRAP_TERMINATION_SERVICE**, including its pending queue count.
It is not silently converted into an ordinary list, omitted because empty, or
claimed covered by strong retention. Its native finalization behavior needs a
separate replacement or exclusion decision. Accessor lowering and scanners for
real lock/thread/GF members remain required before production installation.

Capture is separate from the larger attribution form. Compiling that reporting
form itself can allocate a temporary lock; taking counts afterward produced
740 rather than 739 members in the exploratory run. The retained implementation
captures object identities, types and counts first, under GC inhibition, then
resolves reference paths. The instrumentation allocation is not subtracted by
a magic constant. All original exploratory outputs are retained.

## Validation

Fresh replay: 96 table collections, 126 population collections; 11 rejected
controls. Native producer controls omit non-EQ tables or empty populations, or
misidentify a closure capture; independent owner joins refuse them. Publication
controls shorten or misattribute the census with matching recomputed totals,
downgrade EQL or termination blockers, or reduce a count. All are checked against
the native capture. Bounds and pad-word faults in the unchanged population builder
now fail directed tests. Pair-array aliasing is inert during synchronous construction
and no new claim is made for it. Earlier constructor and policy controls are reused
from the pinned audit-133 parent packet; no compiler or C rebuild is needed.

```sh
python3 tests/wasm/stage1/bootstrap-heap-census/run.py --evidence ../ccl-evidence --output /tmp/heap-census-new
python3 tests/wasm/stage1/bootstrap-heap-census/packet.py verify --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-20-stage1-bootstrap-heap-census-r1 --output /tmp/heap-census-replay
```

This is a pinned-image measurement and dependency join, not complete LL15
startup qualification. It awaits independent review and acceptance.
