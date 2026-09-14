# Source SETF lookup and expander protocol — 14 September 2026

Status: executed; reviewed by Claude's forty-first audit at `413b938c` without defect. Packet `NATIVE-TARGET-SETF-R1`
is retained as `2026-09-14-target-setf-r1` in the
[evidence index](../evidence/index.json). This resumes census work after the
user accepted S0-LL23-a and S0-LL24-a.

None of the five SETF expansions in the image-restore file calls a registered
expander function. Four resolve to named setter symbols. The fifth is the
BASIC-STREAM.STATE accessor: its source macro expands to `%SVREF`, whose SETF
lookup resolves to `%SVSET`. The observed registry and the resulting source
expansions now carry explicit joins:

| Event | Place operator | Registry result |
| --- | --- | --- |
| 9 | `*%SAVED-METHOD-VAR%*` | `SET-*%SAVED-METHOD-VAR%*` |
| 45 | `BASIC-STREAM.STATE` | Absent; source accessor macro expands the place |
| 47 | `%SVREF` | `%SVSET` |
| 88 | `SLOT-VALUE` | `SET-SLOT-VALUE` |
| 255 | `INTERRUPT-LEVEL` | `SET-INTERRUPT-LEVEL` |

The four symbol bindings match explicit DEFSETF declarations in pinned U1
`level-1/l1-utils.lisp`, `lib/macros.lisp` and `level-1/l1-clos-boot.lisp`.
This establishes the observed lookup results and branch choices. It does not
establish that a later source file or a changed registry cannot use a callable
expander, or qualify the target implementations of those setter functions.

The [private driver](../../../tests/wasm/native-census/target-setf/driver.lisp)
rebuilds SETF from its U1 source form and lexically supplies the source body of
`%SETF-METHOD`. It records that helper's GETHASH value and presence flag. The
SETF body's single computed FUNCALL goes through an observation bridge, and
its function-information query goes through a forwarding wrapper. The normal
mode preserves their behavior; only explicit probe mutants alter it. No global
SETF macro or helper function is replaced.

Seventeen source reads include the eleven prerequisite helper forms, four
inverse declarations, SETF and `%SETF-METHOD`. Actual compiler observations
identify the private SETF entry, private lookup function and lexical dependency.
The checker validates source spans against U1, inverse and lookup syntax,
registry identities, exact event/lookup/expansion joins and record populations.
The SETF body is read by CCL's actual reader; its full macro syntax is not
independently reparsed by the Python checker.

## Callable-expander probes

Nine probes execute in the Wasm census target context against a copied native
SETF table. They also run through the unchanged native SETF macro in the same
session. The original table, every original binding, global functions, macro
hook and pass-2 hook are checked after restoration.

- A callable method returns the five SETF expansion values. Its emitted form
  evaluates the place once, evaluates two value forms in order, stores both
  values and returns both. The effects are checked as `place, 11, 22, store`.
- Replacing that method immediately changes the store/result pair to `22, 11`.
- A symbol method produces its named setter call. Absent and present-NIL entries
  both use the ordinary fallback, retaining their distinct lookup presence flags.
- A local function binding bypasses the global SETF registry.
- An expander's nonlocal exit restores the copied table entry; the next call
  succeeds with the original method.
- A direct bridge probe checks all five returned values, including the getter
  form that SETF itself does not consume.

The expanded callable forms are compiled and executed natively as fixture code,
not emitted Wasm. Probe expanders use fixed private temporary names; this is
not a general hygiene or capture-avoidance proof. Native-reference comparison
allows a bijective renaming of generated observer identities, preserving their
symbol names, sharing and all other fields.

Five native mutants fail: caching the first callable method, dropping extra
values, losing the lexical environment, ignoring local function bindings, and
dropping only the fifth/getter value. The last mutant preserves ordinary SETF
results and fails the direct five-value oracle. Twenty-five checker controls
reject source, binding, routing, expansion, effect-order, presence, environment,
restoration and reference-result corruption, including inserted records.

## Scope, reproduction and remaining work

All 293 expansions in the genuine file traversal remain source-routed. Normal
and repeat captures are byte-identical. Every native mutant retains the same
file traversal; mutations apply only to probes. The traversal still contains
seven captured and five stopped definitions, 22 code prototypes, 74 call sites,
twelve function references and seven unresolved calls. No widening edge is
removed, and LL15-b/c remain incomplete. The observed SETF callable-branch
population is zero; the five computed invocations belong only to the probes.

The registry is still observed from the native image. General SETF expanders,
structure accessors, function-information and default-setf helper bodies remain
native dependencies outside this slice. DECLAIM/APPLY's computed helper sites,
other inference and object paths, the five boundary replacements and broader
source traversal remain open. No new target semantic defect was found here.

```sh
python3 tests/wasm/native-census/target-setf/run.py \
  --evidence-root /Users/buildsomething/Source/ccl-evidence \
  --work /private/tmp/ccl-target-setf-work \
  --output /private/tmp/ccl-target-setf-result
python3 tests/wasm/native-census/target-setf/run.py \
  --verify /private/tmp/ccl-target-setf-result
```

Seven formal native sessions run from a disposable pristine U1 archive and the
retained clean image. No source patch, FASL write, native rebuild or saved image
is produced. Observation state is discarded; implementation still starts from
clean U1.

The compact development archive retains the original missing-parenthesis load
failure, successful explorations, all exploratory mutant captures, and the
first analyzer rejection: an out-of-macro event used Lisp NIL, which the JSON
writer represents as an empty array rather than null. The emitter now uses the
explicit null token. The first formal run and verifier passed; the second moves
the probe phase into explicit target state and records/checks that context.
Both are retained, with exact sources and commands and without duplicate byte
storage. The final packet carries the second run.

Stage 0 remains **37 accepted, eleven missing and zero unreviewed required
slots out of 48**. This diagnostic is review-pending and earns no gate credit.
The alternating plan next takes a remaining Stage 0 deliverable, then returns
to the census helpers and source-boundary replacements.
