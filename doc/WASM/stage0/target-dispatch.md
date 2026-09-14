# Target architecture macro dispatch — 14 September 2026

Status: executed; reviewed by Claude's thirty-seventh audit at `4feaef69` without defect. Packet `NATIVE-TARGET-DISPATCH-R1`
is retained as `2026-09-14-target-dispatch-r1` through the
[evidence index](../evidence/index.json). This census slice follows the
[S0-LL22-a standing control](artifact-identity-control.md).

The architecture dispatcher selects the current Wasm macro binding, observes a
replacement immediately, and refuses a missing binding even when the host has
one. The experiment witnesses U1's existing behavior; no new host-versus-target
semantic defect was found in this lookup chain.

The [private driver](../../../tests/wasm/native-census/target-dispatch/driver.lisp)
reads four U1 definitions under the Wasm target context, respecting each source
package, and compiles their bodies together as private lexical functions:

| Source body | Role |
| --- | --- |
| `CCL::BACKEND-ARCH-MACROEXPAND` | Gets the architecture name from the active backend, looks up the operator and invokes the selected function or signals an error |
| `ARCH::ARCH-MACRO-FUNCTION` | Reads the architecture's macro table, preserving the lookup's value and presence flag |
| `ARCH::TARGET-ARCH-MACROS` | Requires the named architecture and returns its macro table |
| `ARCH::FIND-TARGET-ARCH` | Finds the matching name in the current architecture registry |

The builder replaces the dispatcher's single `FUNCALL` site with a private
observation bridge and wraps the lookup to record identities. Both preserve
multiple values and nonlocal exits in normal mode. The other two source bodies
are unchanged. Actual front-end observations show the four private functions,
the entry wrapper and six lexical call edges with matching function identities.
The analyzer independently reads the complete four source forms and checks
their packages, pinned spans and captured syntax.

The two architecture expansions in the real `dumplisp.lisp` traversal now have
explicit lookup records. Event 182, `%GET-KERNEL-GLOBAL-PTR` for `KERNEL-PATH`,
finds no target binding and refuses before any computed call. Event 191,
`%GET-KERNEL-GLOBAL` for `BATCH-FLAG`, selects the actual
`BATCH-FLAG-EXPANDER` from the existing description fixture and returns the named
`STARTUP-BATCH-FLAG` service dependency. Registry, lookup and invocation identities
are joined. That service remains unimplemented; it is never executed here.

## Registry changes and rejection controls

Nine probes run against a copied Wasm architecture descriptor and macro table,
with a dynamically bound architecture list. The active backend still names the
Wasm architecture, so the real lookup resolves the private copy by name. The
native tables are not changed. The probes cover:

- The original binding, a replacement, removal, a present key containing NIL,
  restoration, and the absent pointer macro.
- Removal of the architecture itself, which signals U1's unknown-architecture
  error rather than a missing-macro error.
- A target expander that exits nonlocally, restoration of its temporary binding,
  and a successful subsequent call.

Four calls return, four lookups are refused and one call exits nonlocally. The
replacement returns a distinct primary expansion plus two additional values;
all three must reach the caller. A sentinel environment object must retain its
identity through the computed-call bridge. The real file traversal separately
uses the front end's actual lexical environment.

All nine probes also run through the unchanged native dispatcher and native
lookup functions in the same session. Inputs, values, errors and nonlocal-exit
observations agree exactly; the deliberately fresh environment identity is
checked against its own registry record. These comparisons establish the
instrumented path's behavior for these transitions, not arbitrary macro bodies.

Four native mutant sessions exercise host selection, fallback to a host macro
when the target binding is missing, caching the first selected expander, and
losing additional return values. Each fails the same semantic oracle at its
expected first observation. The host bindings actually exist and have distinct
identities. Host mutant expansions are retained as data; no host kernel access
is executed. Mutations are enabled only for the probe phase, so the real file
traversal remains byte-identical in every session.

Twenty-five checker controls reject omitted or surplus records, source/package
corruption, wrong private call identities, host/target aliasing, wrong registry
or callee joins, lost lookup presence, lost values, false restoration and a
corrupted native-reference result. The expected trace populations are derived
from the literal registry transitions, including multiplicity and ordering.

## Scope and reproduction

This qualifies the observed architecture-dispatch helper path and supplies a
callee witness for its one successful computed invocation in the restore file.
It does not establish a static candidate bound for every possible architecture
macro. The computed sites in DECLAIM, SETF and APPLY remain open, as do other
helpers, general type inference and target object materialization. Standard
host list/hash-table operations and structure accessors still execute as native
compiler infrastructure. This packet does not qualify their implementations for
the target heap or certify the entire macro environment.

The source traversal remains seven captured definitions, five boundary stops,
22 prototypes, 74 calls, twelve references and seven unresolved calls. No
widening edge is removed and no LL15 acceptance is claimed. The Stage 0 ledger
is unchanged: **34 accepted, 13 missing and one unreviewed required slot**;
S0-LL22-a remains pending independent review and user acceptance.

Run from the repository root with unused work/output paths:

```sh
python3 tests/wasm/native-census/target-dispatch/run.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --work /private/tmp/ccl-target-dispatch-work \
  --output /private/tmp/ccl-target-dispatch-result
python3 tests/wasm/native-census/target-dispatch/run.py \
  --verify /private/tmp/ccl-target-dispatch-result
```

The first formal producer and retained verifier pass. Six native sessions run
from a disposable pristine U1 archive and the pinned clean image. Normal and
repeat captures are byte-identical; all four native mutants are rejected, and
each retains an identical file traversal. No source, existing FASL, global
helper binding or macro hook remains changed. No source patch, native rebuild,
new FASL or saved image is produced. Observation state is discarded; future
implementation still starts from clean U1.

The compact development archive retains the earlier successful observations,
their exact driver versions and logs. The first version lacked the independent
file-registry snapshot; the second added it, and the third added the unchanged
native-reference probes. No failed development or formal run occurred in this
slice. Quarantined mutant captures remain rejection evidence, not passing
execution results.

The alternating plan next returns to a remaining standing control, then to
census helper qualification and the five boundary contracts before broader
source traversal.
