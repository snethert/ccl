# Lexical callback bounds — 14 September 2026

Status: executed; reviewed by Claude's forty-third audit at `41457604` without defect. Packet
`NATIVE-LEXICAL-CALLBACKS-R1` identifies two previously unbounded computed call
sites inside source-rebuilt macro expanders. No Stage 0 slot changes disposition.

| Expander | Compiler IR proves | Bound |
| --- | --- | --- |
| DECLAIM | MAPCAR's function variable is initialized with its local anonymous proclamation builder. | One exact local function prototype, through one LET* binding. |
| APPLY | MAPCAR's function variable reads the lexical QUOTIFY binding established by FLET. | One exact local function prototype, through LET* and FLET. |

These are calls made by the compiler's expansion machinery. They are separate
from the 1,729 computed calls in the earlier whole-build observation. The result
does not claim to bound that population, qualify the helpers these callbacks
use, or implement APPLY in Wasm. The APPLY callback is in the quoted proper-list
transformation branch; deriving a static bound does not assert that branch ran
during the image-restore traversal.

## Observation and identity

The runner reuses the reviewed SETF driver, including its existing private
source expanders and target descriptions, in disposable pristine U1. A temporary
owner-thread pass-2 observer records the two expanders' actual acode before the
native compiler consumes it. The observer forwards every return value and
restores the entry on normal and nonlocal exits. It never changes compiler IR,
global compiler definitions, source files or on-disk FASLs. The eight additional
probes use the actual Wasm census front end and stop before code generation.

Each capture joins the pinned source span, the source-read context, the actual
native expander function selected at its macro event, and the local AFUNC
identities. The complete expression structure is retained, including variable
root identities, the compiler's assignment flag, binding initializers, calls
and child functions. Literal object graphs remain data. The unchanged earlier
observer independently supplies the call-site sequence and per-function operator
histograms; both must match the new structural capture exactly.

The relevant U1 layouts are stated by the LET/LET*/FLET decompilers in
`compiler/nx-basic.lisp`, their constructors in `compiler/nx1.lisp`, and the
variable-assignment bit in `compiler/nxenv.lisp`. The source spans and these
direct dependencies are pinned with the runner.

## Conservative resolution

The [analyzer](../../../tests/wasm/native-census/lexical-callbacks/analysis.py)
follows only a uniquely identified lexical binding whose body contains the use.
It accepts local function values and chains of immutable lexical references,
requiring the resulting function to belong to the same lexical owner. It checks
every occurrence of the variable throughout the function and its children.
Either the compiler's assignment flag or an observed assignment prevents a
bound. Unclassified variable uses also prevent one.

Unknown parameters, reassigned variables, unsupported initializer shapes,
nonunique bindings and uses outside a binding's body remain unresolved. The
analysis deliberately does not infer a safe order around assignments. It also
does not extend a LET* binding into later initializer positions, propagate
arbitrary data flow, resolve registries, or bound runtime closure instances.
Its singleton sets identify code prototypes; captured environments remain
separate dependencies. Existing broad graph edges are preserved.

## Checks and limits

Two fresh native sessions reproduce all three raw captures byte for byte.
Eight additional source probes exercise literal callbacks, FLET, unknown
parameters, ordinary reassignment, reassignment by a nested closure, shadowed
names, captured data and sequential scope. Four receive singleton prototype
bounds; four remain unresolved. The inherited SETF and traversal checker also
passes on the new capture.

Twenty-one checker mutations reject missing/surplus observations, incorrect
source and expander identities, bad function ownership, missing calls, mismatched
histograms, nonunique or out-of-scope bindings, unknown aliases and false
restoration claims. Two controls insert assignments while leaving the compiler's
assignment flag clear, including an assignment inside the callback's child
function. They confirm the structural write scan independently prevents a bound.
The inserted-node controls update the auxiliary histogram to reach the semantic
check rather than failing only on observation counts.

Development retained two early analyzer refusals caused by incorrect package
labels for FIXNUM/T, and a control-construction failure that looked for CONS
where the native compiler emitted LIST. Their original sources and outputs are
kept with the successful exploratory captures in the compact development archive.
No new host-versus-target semantic defect was found in this slice.

The output joins are an input to the eventual census integration. They do not
remove widening edges, discharge the five startup boundary replacements, qualify
the full macro environment or close LL15. The ledger remains **38 accepted,
ten missing and zero unreviewed of 48**. Under the alternating plan, the next
independent deliverable is the full-scope typed-conversion fixture (S0-LL07-a),
then a return to startup boundary replacements and broader source traversal.
