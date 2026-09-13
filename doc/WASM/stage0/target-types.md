# Declared-type equality paths — 13 September 2026

Status: executed; independent review pending. Packet `NATIVE-TARGET-TYPES-R1`
is retained in `2026-09-13-target-types-r1` and bound by the
[evidence index](../evidence/index.json).

The [preceding helper slice](target-helpers.md) fixed equality decisions for
numeric constants and explicitly left nonconstant type inference open. This
extension reproduces an unsafe decision in that remaining path. A variable
declared `(signed-byte 31)`, or declared to equal 536870912 or -536870913, still
caused EQL to become EQ. Each type permits a value that Wasm32/D1 must box.
An OR type combining a symbol with a boxed integer exposed the same mistake.
The original diagnostic capture and final prior-helper control retain it.

## Cause and isolated correction

U1's `NX-TARGET-TYPE` translates a standalone FIXNUM to `(signed-byte 30)` for a
32-bit target. It leaves compound expressions unchanged. The target-read EQL
helper asks whether a nonconstant form is a subtype of a compound OR containing
FIXNUM. That nested FIXNUM retained the host's signed 61-bit meaning, allowing
the native subtype predicate to approve an unsafe pointer comparison.

The [driver](../../../tests/wasm/native-census/target-types/driver.lisp) rebuilds
NX-FORM-TYPEP and NX-FORM-TYPE from source and includes them lexically in the
private EQL compiler macro. It preserves their real lexical-environment and
declaration-policy inputs. The scalar NX-TARGET-TYPE source body remains the leaf
translator; a private recursive adapter applies it to OR, AND and NOT operands.
It does not descend into MEMBER values, integer bounds or other type payloads.
The EQL helper remains target-read and retains the prior target FIXNUMP binding.
Stream/vector lookup remains supplied by the reviewed private helpers.

This changes only the isolated census's private functions. Global helpers,
shared compiler source and earlier fixtures are unchanged. Nine U1 source forms
are read; the host compiler builds private functions. Actual AFUNC records join
the five EQL alternatives to their returned functions. The existing owner-only
observer forwards native pass-2 behavior and is restored. No Wasm is executed.

## Probes and genuine traversal

Each probe compiles a two-argument lambda through the real front end, declares
the first argument's type, then compares the arguments with EQL. The second
argument remains unknown. Fifteen cases distinguish these outcomes:

| Declared type / policy | Required lowering |
| --- | --- |
| SYMBOL, CHARACTER, FIXNUM, `(signed-byte 30)` | EQ |
| `(or symbol (integer 0 5))`, symbol MEMBER sets, `(member fixnum)` | EQ |
| `(signed-byte 31)`, the two exact boxed integers | EQL |
| SINGLE-FLOAT, DOUBLE-FLOAT, mixed symbol/boxed-integer OR, unknown T | EQL |
| SYMBOL with safety 3, where declarations are not trusted for this optimization | EQL |

Seven cases use EQ and have no call. Eight retain EQL: seven use builtin index 10
from U1's pinned vector; the safety-3 case retains the ordinary global EQL call.
The oracle checks the source lambda, expansion, input-return identity, actual IR
operator and exact callee. The MEMBER/FIXNUM case checks that FIXNUM as literal
data is not mistaken for a type position.

The dumplisp traversal still has 293 expansion events and seventeen EQL
invocations. Within those invocations the trace records sixty type queries,
sixty inferred form types and 244 target-translation steps. Each row carries its
parent macro event and target context. The checker validates declared probe
facts, translated queries, primary subtype answers and secondary certainty
values. Unknown relationships remain uncertain. There are 770 trace records
including the probes.

All six sessions produce byte-identical file traversals: seven definitions,
five boundary stops, 22 prototypes, 74 calls, twelve references and seven
unresolved calls remain. Normal/repeat type captures also match. The prior helper
and shallow/host-range mutants fail the boxed-type oracle. Forced declaration
trust fails the safety-policy oracle. Seventeen checker controls reject altered
source, declaration, callee, translation, literal data, certainty, event joins,
restoration and scope promotion.

## Bounds and retention

Qualification covers these declared-type forms and observed EQL queries. Native
declaration lookup, TYPE-EXPAND, SUBTYPEP, type canonicalization, policy helpers
and compilation of the private helpers still have transitive dependencies.
User-defined aliases, general result-type inference, OPTIMIZE-TYPEP, native class
objects and other macro helpers remain outside this proof. Rebuilding three
source bodies and testing their composition does not qualify the entire type
system or macro environment. The scope flag remains false; no widening edge is
removed and no census slot passes.

The first formal run and retained verifier pass with forty direct source pins.
Source and on-disk FASLs remain unchanged, global helper identities are checked,
and temporary state is restored. The development archive retains the original
unsafe nonconstant capture, the corrected capture and native mutants. A
preliminary checker printout reversed the aggregate EQ/EQL counts; its original
log is retained. The counts were changed to derive from the correct per-case
expectations before the first formal run, which records seven/eight.

The separate S0-LL03-a acceptance is committed as cd3188c2. Stage 0 remains
**31 accepted, 17 missing, zero unreviewed required slots**. This helper packet
awaits independent review. The alternating plan next takes a standing control,
then resumes remaining helper/type/object qualification and source traversal.
