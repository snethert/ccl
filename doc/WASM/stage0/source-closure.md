# Source-wide collection and call bounds — 14 September 2026

Status: executed diagnostic; reviewed by Claude's forty-seventh audit at `363a964f` without defect. **LL15-b/c remain
incomplete.** This work finishes the general file driver and the source-wide
observation pass; it does not finish the joined bootstrap census. No slot,
criterion, accepted record or historical graph changes disposition.

The user asked to finish the census after supplying Claude's forty-sixth audit.
This replaces the narrow, manually interpreted top-level driver with U1's actual
file compiler. It handles nested PROGN/EVAL-WHEN, source macro definitions,
MACROLET, structures, classes, methods, includes and reader conditionals. All
164 compilation units recorded by r7 are attempted in fresh independent native
and Wasm-target sessions, using pristine U1 source. Four includes bring the
actual read-source count to 168. The inventory is the recorded build's source
universe, not every optional file in the repository.

| Observation | Native reference context | Wasm census context |
| --- | ---: | ---: |
| Attempted compilation units | 164 | 164 |
| Successful file reads/compilations | 164 | 103 |
| Files reaching EOF | 164 | 135 |
| Function observations, including compiler helpers | 51,708 | 20,005 |
| Call sites | 104,081 | 56,337 |
| Flat graph objects | 5,773,904 | 2,972,929 |
| Proven immutable lexical callback bounds | 206 | 113 |

The target pass records 259 top-level compiler-form failures. It marks 4,363
subsequent captures as affected by an earlier failure. Twenty-nine files stop
before EOF; continuing through other failed forms never removes their gaps.
These counts include native-only files and operations. They are diagnostic
worklists, not new gate slots or a claim that every native operation belongs in
the Wasm profile. Successful target reads still use an unqualified wider macro
environment and produce no executable Wasm.

## What is now established

The [driver](../../../tests/wasm/native-census/source-closure/driver.lisp) calls
the real file compiler and captures flat acode before pass 2. Native mode always
forwards the original native pass 2. It records actual emitted function IDs and
code prefixes and joins them to the compiler's in-memory output records. Wasm
mode supplies distinct refusal functions to the census-only backend; they
cannot execute and the guarded FASL writer cannot publish them. Host compile-time
effects and local macro expanders retain their native execution path.

The complete node graph preserves variable roots, assignments, local functions,
binding initializers and calls. An independent check joins it to the earlier
observer's exact function population, call order and operator histograms. The
bound analyzer requires a unique immutable local binding, the correct lexical
owner, and a use dominated by the binding body. It scans parent and child writes
independently of the compiler's assignment bit. It makes no whole-program
parameter, registry or heap-value inference.

The D1 description extension derives 161 integer values, 37 data subtype rows,
sixteen architecture fields and eight data macros from pinned x8632 source. The
independent checker recomputes integers and table entries from U1. Eight literal
expansion probes cover allocation sizes/tags, ratio slots, identity predicates
and symbol views. No native code-vector layout, foreign pointer definition,
kernel-global offset or native stack state is borrowed as a target description.

The native output join identifies **257 functions that did not pass through
Lisp pass 2**, including directly assembled native LAP definitions. Their actual
output identities remain in the packet as unjoined records. Reading their file
does not qualify their target lowering.

## Verification and retained evidence

Packet `NATIVE-SOURCE-CLOSURE-R1` retains both surveys, exact commands, raw
captures, original failures, the per-call worklists and 34 probe/checker controls
in a small number of archive/catalog entries. It references existing source,
bootstrap, image and registration inputs rather than copying baseline packs.

The retained author's target and callback probe pairs reproduced byte-identically;
that is an observation about those pairs, not a target-mode guarantee. Claude's
fresh target run differed in the same eight address-bearing previews seen in the
native pair. Diagnostic second-operand print previews are nondeterministic in
both modes. Both raw values are retained and no semantic identity is read from
those previews. Cross-directory comparisons also need an explicitly identified
disposable-work prefix mapping. With those differences disclosed, Claude's ten
fresh survey sessions matched every graph, observation, native code prefix,
gap, effect and read record. The retained verifier continues to compare retained
bytes directly; no historical capture is rewritten. A separate unwrapped native session reproduces 3,168
output code bytes across 26 corpus functions. This is a code-prefix comparison,
not a comparison of arbitrary constant objects or a new full native build.

All 980 files in the disposable source/bootstrap copy remain byte-identical.
Main-checkout compiler and kernel source are untouched. The [development
record](../../../tests/wasm/native-census/source-closure/development.md) retains
the failed native experiments and discloses the missing on-disk snapshots for
two early interactive Python checker mistakes. No original failure is rewritten
as a success. The verifier recomputes both complete survey worklists and the
probe results without scanning historical evidence.

## Work still needed for LL15-b/c

The new native capture has 1,723 computed calls. Of these, 206 have proven local
bounds and **1,517 remain unresolved**: 878 variable calls and 639 computed
callee expressions. The variable-call reasons are 595 parameter/absent-binding
cases, 251 unsupported initializer shapes, sixteen cross-owner uses, twelve
assigned variables and four uses outside the binding body. Struct-field reads
and vector-slot reads are prominent among computed callees. Each worklist row
names its file, actual source location, function and call-site identity.

These are fresh independent file sessions. They do not recreate the sequential
r7 rebuild's binding environment, and their numbers must not be substituted for
r7's **1,729** unresolved sites. Joining old and new function generations requires
an explicit witness; printed names and similar counts are insufficient.

The subsequent [retained-build IR integration](build-flow.md) avoids that
cross-session inference for the rich build by consuming the full IR already in
its own stream. It joins actual compiler/code identities and establishes 200
local bounds in that separate namespace. This source-wide packet and its counts
remain unchanged.

The target worklist exposes the remaining representation and boundary decisions:
135 failures request NTH-IMMEDIATE, eighteen request FUNCTION-TO-FUNCTION-VECTOR,
and others reach function mutation, kernel globals and foreign interfaces.
Those source operations need explicit logical-function/registry replacements
or justified profile exclusions. D1's data layout cannot supply native code
storage that the Wasm design intentionally removes. The mandatory startup
entry-registry and callback replacements also remain unimplemented.

The next completion work is therefore to join source/body generations to the
retained build and boot observations; qualify the reached target macro/helper
paths and boundary replacements; derive parameter/registry/heap-call bounds;
and integrate the reviewed seeds, initializer schedule, lowering/import/store
dispositions and trace reconciliation. Only then can justified static edges
replace membership widening and the genuine closure pass the independent
node/edge/unknown-call/seed/initializer omission controls. The historical graph
and its unresolved edges are preserved meanwhile. The ledger remains **39
accepted, eight missing and one unreviewed of 48**; LL13-b still awaits the
user's acceptance.
