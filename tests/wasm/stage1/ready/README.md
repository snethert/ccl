# Projected-image READY join — R9

Original-definition credit remains **550 / 515 non-NIL**, with no LL15 slot
claim. This continuation adds packed-bit allocation, reads and stores to the
isolated compiler. It exercises unchanged whole-file `MAKE-CPL-BITS` and
`SIMPLE-VECTOR-DELETE` from the restored READY image. No shared compiler,
runtime or CCL source changes; no new C or JavaScript service.

## Packed bits

The layout is CCL's x8632 low-bit-first bit vector, subtag 255. Allocation
initializes the complete object and keeps unused tail bits and padding zero.
Typed AREF, SBIT, `%SBITSET` and UVREF/UVSET use one byte-access helper.
Simple one-dimensional `MAKE-ARRAY` with a constant BIT element type uses
the existing rooted allocation path. Other MAKE-ARRAY shapes retain their
ordinary call and dependency obligations.

The native witness covers lengths 0, 1, 7, 8, 9, 31, 32, 33, 63, 64, 65 and
257, initialized to both zero and one, with collection between stores and
reads. A collecting operand-order case preserves the vector across all
three operands. Invalid vectors, indices, bit values and initial elements
are compared through native error handlers. An initial development run
returned checked 5 for invalid bits; the final lowering uses the existing
TYPE-ERROR constructor with datum and expected type BIT. That failure is
retained.

`MAKE-CPL-BITS` runs on the actual projected class precedence list and checks
each class's native ordinal. DELETE runs forwards and backwards with a
collecting comparison callback and observes both result and visit order.
The count-limited early-exit branch still calls generic ABS and is not
qualified here. This does not claim FINALIZE-INHERITANCE or class mutation
is complete.

Admission checks are accounted for as follows:

| Check | Directed witness |
| --- | --- |
| Object tag / bit-vector header | NIL, a simple vector, and a string |
| Fixnum index / index below length | A double, -1, and exactly the length |
| Header / complete payload span | Raw pointers at memory end and a backed header with an unbacked tail; checked refusal, unchanged object bytes and restored TCR apart from the allocation pointer and value count |
| Store / initial value is zero or one | Wrong integers and non-integers; native error handlers; vector unchanged |
| Allocation count is a fixnum in 0..16,777,215 | NIL, -1 and 16,777,216; checked refusal and unchanged existing heap |

Allocation alignment, available extent and retry collection remain the
shared `bootstrap-heap-block` contract. Object alignment follows from the
low three tag bits. Positive maximum-size allocation remains subject to the
owner's heap capacity; no growth policy is added. In this one-MiB-semispaces
profile, the count ceiling is also implied by allocation capacity: a count
above 16,777,215 needs more than two MiB before alignment. Removing only that
ceiling still refuses at the shared allocator. A larger-space profile must
isolate the header-width ceiling independently.

Audit 172 O-57 is addressed by screening every emitted module, including
whole-file modules, against the upstream macro-name index. The two controls
inject a macro-name closure edge and a whole-file macro call. O-58's NIL
frame on the still-unreached `%error` fallback remains disclosed.

## Native functions and method bodies

The remaining two standalone macro-name candidates now bind to whole-file
compilations: `%INTEGER-ABS` uses l0-int's NUMBER-CASE environment, and
`%GET-HASHED-HTAB-SYMBOL` uses nfasload's HTVEC environment. All 33 candidate
edges found by the earlier standalone screen are superseded by qualified bindings;
the R9 screen includes whole-file modules too.
Restoring either old module is a directed refusal control. This remains a
conservative name screen, not a general lexical macro proof.

GCD comes from lib/numbers, MAPCAR/MAPLIST/MAPL/MAPCAN/MAPCON from lib/lists,
and CTYPE-P from l1-typesys. The callers cover thirteen signed integer
magnitudes and zero-, one-, two- and three-argument GCD, all six maps with
collecting callbacks, nine symbol lookups through the native package-table
shape, and seven CType predicates. Lookup inputs specify hash residues to
isolate collision, tombstone, wraparound and name comparison from host word
width. Generic ABS is still blocked by specialized complex-float accessors;
this unit does not claim it works.

The projected population grows from 33 to 50 generic functions. Fifteen native
DEFMETHOD bodies use the existing PARSE-DEFMETHOD path; eight slot readers join
the real native methods and slot definitions. UPDATE-DEPENDENT is projected
with no methods, exercising NO-APPLICABLE-METHOD. Qualification callers invoke
the actual GF function cells and compare class/GF dependents, class and slot
readers, CPL computation and inherited default initargs. SLOT-MISSING and
SLOT-UNBOUND compare condition payloads and object identity, with collection
and a subsequent successful slot write/read. Funcallable slot read, write and
boundness use the native methods too; a temporary GF name is observed across
collection and restored. Native dependent lists and the
static class table are restored and checked after every oracle entry.

## Image boundary

The function-class table now distinguishes ordinary compiled functions,
lexical closures, method functions and funcallable GFs using D1's retained
LFUN bits. The old classifier treated every function as a GF and refused an
ordinary function's six-field object. Four native class-name observations
and an invoked capturing closure exercise the replacement.

GF and metaclass slot metadata are retained for the new MOP readers, with
initfunctions and predicates produced by the existing source-derived driver.
The first expanded caller exposed missing NAME metadata on a GF; its failure
and the passing earlier corpus are retained. A second failure identified the
missing funcallable slot methods and the legacy-mode NO-APPLICABLE-METHOD
body. The class image now selects the native method compiled in class mode.
The setter then exposed TYPEP T falling through to dynamic TYPEP and recursing
through CTYPE. The type-call literal recognizer now handles NX1's dedicated
T/NIL operators. A collecting, side-effecting TYPEP T/NIL witness checks both
results and operand evaluation; the prior failure and stack trace are retained.
This does not qualify arbitrary dynamic TYPEP or the uninitialized CTYPE
environment reached by that fallback.

Class-mode %SLOT-REF now calls CCL's unchanged %SLOT-UNBOUND-TRAP on the
unbound marker. That function finds the native slot definition and invokes
SLOT-UNBOUND; its location reader is the fiftieth projected GF. Default mode
keeps its existing refusal. The witness compares the condition's slot name
and instance identity, takes USE-VALUE after collection without binding the
slot, then stores and reads the slot successfully.
The driver is a written file.

READY's post-state is compared before the support callers run. Each support
caller then compares its own return values and complete represented object
graph against its corresponding native snapshot. In particular, the lazy
class-initarg metadata produced by the condition callers is observed at the
right point in both executions.

Condition classes now carry their native direct-subclass and local-default
fields. The initial broader projection pulled in unrelated native captured
closures; the failed corpus and exact inputs are retained. Those unrelated
fields remain outside this image profile. A native function may become a named
function reference only if it is the actual FDEFINITION of that name; mapped
method/initfunction entries keep their explicit bindings. An unsupported
captured closure is refused during projection, with a retained directed
control. First-class function values now enter the closure census too.

This is not a claim that all class bookkeeping or closure metadata can be
saved. The complete static closure, upstream attribution for the replacement
cap, printer stream-lock paths and all 35 callback obligations remain open.
Successful indirect-call witnesses do not prove every indirect path closed.

## Carried READY contract

The native integer printer, target radix tables, type-method dispatch,
ISTRUCT classification, generated image admission, owner-installed public
table bindings, moving heap keys and class-based conditions remain covered.
Four cold boots use both placements and movement variants. Seven startup roots
must survive admission refusal. The copied, reader-checked radix initializer
and ISTRUCT classifier, per-name file selections and READY callers remain
Stage 1 scaffolding. Heap-image and owner contracts are durable.

## Results

The final proposal passes 26,048 fresh corpus comparisons, four cold boots with 714 collections, 20 boot refusals and 31 image-admission controls. Eight support callers compare both results and represented post-state at each boot (40 comparisons including the producer). Five direct bit-vector refusals and four layout observations run per boot. The admission-guard omission control is rejected. Fresh native R6/R6a passes 21,843 tests and restores all 164 FASLs. No post-retention replay is claimed.

The expanded census is 742 modules, 113 operators and 36,025 occurrences. Missing edges fall from 66 to 62; 50 indirect modules remain. These are obligations, not executed coverage. The all-module macro screen covers 6,362 modules and retains the same 33 superseded candidates.

## Reproduce

```sh
python3 tests/wasm/stage1/ready/packet.py verify ../ccl-evidence/2026-09-24-stage1-ready-join-r9 /private/tmp/ccl-work/claude/ready/verify
```

The native qualification can be rebuilt independently:

```sh
python3 tests/wasm/stage1/ready/native.py /private/tmp/ccl-work/claude/ready-native/run
```

Verification executes the corpus and READY once. Probe-only refinements may
reuse the exact bound corpus; such reuse is recorded separately from fresh
execution. Retention does not claim another replay. R6/R6a is bound to all 33
final proposed source files; verifier replay checks that exact identity before
reusing the native qualification. The saved native compiler image is review
tooling, never the port's heap. Scratch and caches are disposable.
