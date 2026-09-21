# Bootstrap core: whole files and runnable primitives

**Throughput: 1,539 of 2,492 inventoried DEFUNs admitted; 129 original CCL
definitions executed against native, up from eight.** Admission is not execution
or bootstrap closure. The historical 639/82 figures included audit-143 F1/F2;
this packet rejects those shapes. Auxiliary proposal, not integrated, no LL15
slot credit. User authorization: accept the values lowering and adopt P3, then
implement the two whole files, their operators and at least 100 original
functions. The user's style direction is to follow CCL's Lisp source.

## Implementation

`backend.py` derives the proposal from the integrated compiler and pristine U1.
`operators.lisp` adds tag/typecode readers, predicates, node reads and writes,
rooted `%GVECTOR`, fixnum arithmetic and comparisons, and calls to the accepted
numeric services. Generic fixnum comparisons execute directly in Wasm. `EQL`
uses the existing reviewed EQL service and comparator, with a two-argument
adapter; there is no second EQL implementation.

Proposed `#+wasm32-target` branches live in **CCL's own** `l0-pred.lisp`,
`l0-utils.lisp` and `l0-def.lisp`. They implement SYMBOLP, LISTP, VECTORP, ARRAYP,
LFUNP and representation helpers. In particular, the FUNCTIONP/LFUNP cycle is
implemented, not merely hidden from the count. `level-0/WASM32/w32-prims.lisp`
provides four callable primitive definitions. The proposed architecture gains
the D1 function subtag. No consumer source rewriter is used.

`whole-file.lisp` invokes CCL's real `compile-file`, retaining its file macro
environments. A temporary function-emission hook sends definitions and their
actual environments to Wasm; a file-output hook retains records before native
FASL dumping. Both hooks are restored with UNWIND-PROTECT. Diagnostic sink tokens
are never installed or executed. Native references use the untouched native
function compiler over the same source files, avoiding later host redefinitions.

Both requested files compile whole: 62 named definitions from `l0-pred.lisp`
and 16 from `l0-utils.lisp`; the new primitive file adds four. There are 89 file
records including seven top-level forms, and 188 assembled modules overall.
All 44 callee-closed definitions in the two requested files have input-table
execution against native. Whole-file compilation does not execute their global
initializers or close their remaining error, debugger and TYPEP dependencies.
Those are real named CCL calls, never success stubs.

The collector and owner proposals add generic structure subtag 122 to their
node scanners. A generated structure whose only reference survives in a root
frame can now move. This was required by actual collecting execution, and the
old scanner is retained as a rejected control.

## Measurement and execution

The census reads with the Wasm target binding and retains 268 read/name skips.
Host failures carry their class and message. Native reader diagnostics retain
the raw text; a separate deterministic copy masks only the printed string-stream
address, retaining every source position, error class and message. `measure.lisp` joins native and
Wasm bodies, refuses a body erased by reader conditionals, and refuses a
self-call-only definition unless its operator actually lowered. Controls compile
the defective shapes first and retain their rejected Wasm text. Meaningful NIL
functions remain legal. The target-node-size witness observes 4 versus native 8.

Callee closure is a fixed point over emitted dependencies, excluding unresolved
indirect calls. It yields 193 definitions, including the four new primitives;
it does not establish initialized globals, all-input behavior or termination.
Only 129 original definitions have native input-table comparisons. The input
table, all unexecuted closure rows and all dependencies are retained. Whole-file
IR instrumentation counts 1,826 distinct emitted IR-object visits under 57
operator names, not textual matches in the backend and not the entire startup
operator surface.

There are 1,734 native rows, executed before and after movement at 256 KiB and
2 GiB: 6,936 comparisons, 3,468 between-call collections and 52 collections
inside generated calls. Arguments are compared after mutation too. Seven
supplemental probes exercise vector/structure/slot operands, setters, pending
values, cleanup and nonlocal transfer across a test-only collecting leaf. They
do not count toward the 129 original definitions. The retired semispace is
poisoned. Error paths check TCR and binding restoration before returning the
checked failure. Twenty directed malformed-access checks must refuse, not trap.
Eighty fixnum-comparison checks assert no numeric-service call.

Four focused executable faults fail at their named observations: unrooted
GVECTOR operands, wrong SYMBOLP typecode, fixnum comparisons forced through JS,
and the old structure scanner. This is a proportional development check, not
Claude's integration-candidate mutant sweep. Ten legacy modules remain
byte-identical to the accepted values packet.

Native x86-64 and Wasm32 differ in immediate single-float and symbol layouts.
Raw representation predicates use their common native input domain; this is
not a claim that host and target tags are equal. Mixed real arithmetic and
comparison rows exercise the accepted slow services as well. Their limits
remain in force. Checked THE, arbitrary collector object kinds and a complete
Lisp unbound-slot error path are not added here. Allocation retry is not enabled
for these modules; moving tests run at explicit safepoints, not new shortage
paths. Function cells, pools and arguments are fixture-owner materializations,
not a completed cross-dumped image or bootstrap installer.

## Native safety and replay

R6/R6a ran in a disposable pristine U1 build: 21,843 tests pass, five existing
architectures and 17 module profiles agree, all 164 restored FASLs are identical.
159 registered-build FASLs are raw-identical. The two existing registration
artifacts retain their accepted explanation. The three source files gaining
reader branches have different source notes and PC/source maps. `native_source.py`
compares all 136 decoded function occurrences: executable bytes, function flags
and all non-location data must agree. Only source-note spans and PC/source maps
in the native flags-selected function-info slot are recorded separately, with
bounds checked. The original strict FASL failure is retained. This is an explicit
shared-source artifact explanation for review, not raw byte identity for those
three files. No upstream kernel is modified.

Run from any checkout with the pinned sibling evidence store:

```
python3 tests/wasm/stage1/bootstrap-core/packet.py verify \
  --packet ../ccl-evidence/2026-09-21-stage1-bootstrap-core-r1 \
  --output /tmp/bootstrap-core-replay
```

This re-derives the proposal, compiles the census and whole files, re-executes
native references, target cases and focused faults, and compares deterministic
artifacts. R6/R6a is reused by exact compiler/source hashes; add `--native` to
rebuild it. Source pins are checkout-relative; dependencies are evidence-root
relative. Registered images are omitted as reproducible build outputs; their
hashes and build logs remain. Baseline image/FASLs are reused from their pinned
existing packet. The proposal remains for Claude's review before integration.
