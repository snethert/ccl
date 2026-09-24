# Projected-image READY join — R10

Executed originals increase from **550 / 515 non-NIL to 554 / 519**:
whole-file CCL `ABS`, `COMPLEX`, `REALPART` and `IMAGPART` now run from the
cold image. The previous corpus contains none of those four entries; the
coverage record binds their native source modules and the new oracle row.
This does not recount admission or claim an LL15 slot. The projected surface
stays at 612 classes and 50 generic functions.

## Numerical closure

Native `ABS` could not compile its complete NUMBER-CASE expansion because
scalar-complex-float constructors and readers were missing. Six primitive
lowerings now implement those operations at the backend boundary. CCL's
public definitions compile unchanged in their whole-file environment.
`%%short-float-abs!` is an ordinary target Lisp counterpart of the native
single-float LAP entry, using the existing float-word accessors. There is no
new C or JavaScript arithmetic service.

Constructors evaluate both operands in order and retain roots across allocation
retry. Readers also allocate through the shared heap-block helper and reload
the rooted source after a collection. The raw shapes follow native 32-bit CCL:

| Object | Subtag | Header count | Bytes | Components |
| --- | --- | --- | --- | --- |
| Complex single float | 71 | 3 | 16 | 32-bit words at 8 and 12 |
| Complex double float | 79 | 5 | 24 | 64-bit words at 8 and 16 |

The word at offset 4 is zero padding. The isolated collector and heap-image
loader recognize exactly these counts and treat component bits as raw data.
Pointer-shaped payloads must neither retain objects nor acquire relocations.
These additions are proposals under this fixture; shared compiler, runtime
and CCL files are unchanged.

`READY-NUMERIC-SEQUENCES` exercises eleven real inputs, including fixnum
limits, signed bignums and signed floating zero, plus six single/double complex
pairs. It compares magnitude, components and operand-effect order with native.
Native `SIMPLE-VECTOR-DELETE` now reaches its ABS-dependent COUNT path:
30 combinations cover both directions, five counts and three bound pairs,
with collection in comparison callbacks and observed visitation order.
No general complex-arithmetic completeness claim is made.

## Representation and failure checks

Each writer/reader run forces allocation retry through the actual whole-file
`COMPLEX`, `REALPART` and `IMAGPART` entries. Independent raw header, padding
and component-word observations prevent matching reads and writes from hiding
a wrong representation. The primitive guard entry has an explicit native
execution row; wrong operand shapes refuse without allocating.

`complex-shapes.mjs` runs at both placements. Its sixteen rows check relocation,
non-tracing of pointer-shaped component bits, exact count admission and
truncated extents. Invalid collector objects refuse before changing source,
roots or TCR; invalid image payloads refuse before destination writes.
`complex_controls.py` removes each new count check separately from the
collector and loader. All four omissions fail their named observation.
The existing shared object-span and allocation guards are reused, not relaxed.

The earlier low-bit-first raw bit-vector check remains load-bearing (audit173
O-61). Its value-only observers would not distinguish paired bit-order bugs.
All-module macro screening, explicit execution lists, direct-entry image
refusals, owner-installed table bindings and the admission-guard omission
control remain in the run. O-58's NIL frame on the unreached `%error` fallback
is still disclosed.

## Scope and provenance

The compiler is derived from the accepted R9 backend, not from its retired
patch stack. Cache identity includes the generated backend, target LAP source,
collector source, clang and driver dependencies. Execution binds the proposed
collector binary. Native R6/R6a is fresh and binds all 33 final compiler/CCL
source files: 21,843 tests pass and all 164 FASLs restore.

The author run reused its completed build while fixing probe-only failures,
then recompiled the final explicit probe batch and freshly ran the writer,
full regression corpus, four cold boots and guard control. The failed inputs
and continuation record are retained. Retention itself executes nothing.
The verifier runs those phases from scratch or their exact build cache.

The first retry probe used a wrapper compiled with retries disabled; the
corrected probe forces retry through the native entries. A second assertion
incorrectly counted the main witness's capture-cell allocation as a primitive
write; a simple primitive entry now isolates that refusal. Missing explicit
execution and a missing mutant-driver import were refused and corrected. The
guard probe also copied the proposed collector from the executed base while
the reused preparer expected its original service. A digest-checked handoff
now restores that input before applying the proposal; the already compiled
guard module then executes unchanged. The continuation record distinguishes
these phases; writer/reader wall times were not recovered after interruption.

READY and each support caller compare their own values and represented
post-state against the corresponding native snapshot. The native oracle's
class table and dynamic startup state are restored after all eighteen image
entries. A nineteenth explicit entry executes the primitive guard's default
case; its additional operations run in the target layout checks.

Complete static closure, printer locks, upstream attribution under the
25-replacement cap and all 35 startup callback dispositions remain open.
The radix initializer, per-name selection lists, image projection and READY
callers remain Stage 1 scaffolding. No additional projected GF or class field
is added in R10, and this is not complete LL15 acceptance.

## Results

The proposed compiler/collector passes 26,048 fresh corpus comparisons, including
40 collector-owner checks. Four cold boots pass at both placements with 1,286
collections, 45 support comparisons, 20 boot refusals and 31 image-admission
checks. All sixteen scalar-complex layout rows and four count-check omission
controls pass. The generated admission-guard omission is rejected.

The closure is 781 modules / 122 operators / 39,306 occurrences, with missing
edges reduced from 62 to 57; 50 indirect modules remain. This larger numeric
closure is a dependency census, not an assertion that every branch executes.

## Reproduce

```sh
python3 tests/wasm/stage1/ready/packet.py verify ../ccl-evidence/2026-09-24-stage1-ready-join-r10 /private/tmp/ccl-work/claude/ready/verify
```

The native qualification can be rebuilt independently:

```sh
python3 tests/wasm/stage1/ready/native.py /private/tmp/ccl-work/claude/ready-native/run
```

The saved native compiler image is review tooling, never the port's heap.
Historical READY packets replay from their recorded source commits. Scratch
outputs and caches are disposable; final retention deletes its source output.
