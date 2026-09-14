# Target TYPEP paths — 13 September 2026

Status: executed; reviewed by Claude's thirty-first audit at `949333c4` without defect. Packet `NATIVE-TARGET-PREDICATES-R1`
is retained in `2026-09-13-target-predicates-r1` and bound by the
[evidence index](../evidence/index.json). This resumes the census after Claude's
thirtieth audit at `48270967`.

The next helper path exposed another inherited host/target mismatch. The native
TYPEP expander returns true for 536,870,912 and -536,870,913 as FIXNUMs, and false
for 536,870,912 as a BIGNUM. All three answers are wrong under D1's signed 30-bit
fixnum range. A compound OR containing FIXNUM has the same problem. The original
native diagnostic is retained. Native CCL's 64-bit answers are appropriate for
its own representation; the defect is in inheriting them for Wasm32.

## Private correction and source optimizer

The [driver](../../../tests/wasm/native-census/target-predicates/driver.lisp)
reconstructs the TYPEP compiler macro and OPTIMIZE-TYPEP helper from U1 source.
Private wrappers translate types before native constant membership and type
canonicalization. FIXNUM uses U1's source NX-TARGET-TYPE translator; BIGNUM becomes
`(and integer (not (signed-byte 30)))`, the complement within integers required by
D1. OR, AND and NOT recurse through type positions. MEMBER values and explicit
numeric bounds remain data.

Earlier EQL, declared-type and stream/vector helpers remain in use. Eleven source
forms are read for this composition. The new macro's actual compiler observation
is joined to the selected callable. No global function or compiler-macro binding
is installed or replaced. Temporary observation and routing restore; shared
compiler and upstream kernel source are unchanged.

OPTIMIZE-CTYPEP remains a native dependency. Its existing first guard compares
target and host backend identities and returns NIL for cross-compilation. The
fixture preserves and observes that refusal. A native control forces host
identity, produces a non-NIL expansion and is rejected. The native body itself
is not reconstructed or qualified for cross-target lowering here.

## Executed checks

| Surface | Cases / result |
| --- | --- |
| Constant TYPEP through the real front end | 22 probes: 15 true, seven false |
| D1 representation | Both fixnum boundaries and adjacent boxed integers, large bignum, single/double floats |
| Compound types and literals | OR, AND, NOT, MEMBER symbols named FIXNUM/BIGNUM, literal integer and explicit bounds |
| Native cross-target guard | Numeric and byte-array ctypes both refuse optimization |
| Unchanged expansion | Dynamic type and explicit environment preserve original call identity |
| Genuine restore-file TYPEP expansions | Ten: two BASIC-STREAM, six IOBLOCK, two BUFFERED-STREAM-MIXIN |

The constant oracle independently computes membership and checks the source
lambda, macro input/output, selected callable, actual IR body and absence of
residual calls. It reconstructs all 170 helper trace records, including canonical
integer bounds, literal preservation, answers and parent events. File expansions
retain their exact predicate/class-cell forms and join the traversal's macro events.

Two normal sessions produce byte-identical captures. Five native controls reject:
inherited membership, translating FIXNUM alone, scalar-only translation, rewriting
MEMBER data and bypassing the ctype guard. Twenty-two checker controls reject
omitted/inserted records, incorrect values and IR, wrong routing, erased class
dependencies, changed bounds/answers, false qualification and lost restoration.
All seven file traversals are byte-identical.

## Remaining scope and retention

Native SPECIFIER-TYPE-IF-KNOWN, TYPEP and transitive type-system helpers still
execute after translation. User aliases, arbitrary constant objects, general
inferred types and nonconstant numeric TYPEP lowering are outside these probes.
The IOBLOCK class cell, RESTART wrapper and compiler environment remain explicitly
unqualified native objects; two float literals are also labeled native diagnostic
values. Observing their identity does not materialize target objects. The named
load-time class-cell dependency remains in the capture.

The restore traversal still has seven captured definitions, five boundary stops,
22 code prototypes, 74 calls, twelve references and seven unbounded calls. This
slice replaces no widening edge and gives no LL15 gate credit. Full macro
environment qualification and the wider source traversal remain open.

The first formal producer and retained verifier pass with 42 direct source pins.
Source and on-disk FASLs remain unchanged in the disposable U1 copy; no image is
saved. The compact development archive retains the inherited defect, corrected
capture and five native mutations with original drivers, commands and logs. No
native or checker execution failed unexpectedly. A documentation patch failed its
context match without changing files and was reapplied; execution was unaffected.

Stage 0 stays **31 accepted, 16 missing and one unreviewed required slot**. That
slot, S0-LL01-b, has Claude's review and awaits the user's acceptance; this
diagnostic adds no acceptance record. The alternating plan next takes a standing
control, then continues helper/object qualification, the five boundary
replacements and wider traversal.
