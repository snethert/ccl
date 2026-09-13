# Startup target descriptions — 13 September 2026

Status: executed, independent review pending. This follows Claude's twenty-first
audit at `ec0602d4`. Packet `NATIVE-TARGET-DESCRIPTIONS-R1` is retained in
`2026-09-13-target-descriptions-r1` and bound by the [evidence index](../evidence/index.json).

The census now captures the actual bodies of seven of the twelve definitions in
U1 `lib/dumplisp.lisp`, up from four. The additional definitions are
`CLEAR-IOBLOCK-STREAMS`, `RESTORE-LISP-POINTERS` and `RESTORE-PASCAL-FUNCTIONS`.
Five definitions still stop at native foreign/file boundaries. Nothing here
implements those functions for Wasm or replaces a widening edge in the census.

| Captured material | Count |
| --- | --- |
| Top-level forms accounted for through EOF | 16 |
| Source function definitions captured / stopped | 7 / 5 |
| Top-level initializer bodies | 2 |
| Deferred load-time initializer bodies and explicit links | 4 / 4 |
| Code prototypes, including nested functions and initializers | 22 |
| Call sites / function-reference sites | 74 / 12 |
| Calls still lacking bounded targets | 7 |

## What D1 supplies, and what it does not

D1 adopts x8632-derived data tags. It does not adopt native kernel-global
addresses or provide a complete Wasm object schema. The
[description ledger](../../../tests/wasm/native-census/target-descriptions/descriptions.json)
derives these eight type-classification values directly from pinned U1
`x8632-arch.lisp`: basic stream 50, instance 114, structure 122, istructure 130,
the minimum CL immediate-vector subtag 159, array header 234, vector header 242
and simple vector 250. The 159 row is a classification boundary, not an additional
object type. The derivation checks the source declaration, shift and fulltag,
then compares the independently written Lisp constants and evaluated target table.

This supplies front-end type metadata only. Payload fields, allocation, GC
walking and emitted accesses still require D1's independent layout checks. No
native function, catch frame, pointer or TCR layout is imported by these rows.

The batch-flag access becomes a named census dependency on
`WASM-CENSUS-SERVICES::STARTUP-BATCH-FLAG`. Its contract requires an immutable
integer supplied by the loader before restore: zero is false; nonzero is true,
preserving U1's test. It has no assigned memory offset or runtime implementation.
The fixture's function refuses execution. Only the quoted `batch-flag` key is
described; other kernel globals still require explicit contracts.

## Required boundary replacements

The machine-readable ledger records eight obligations. All remain
`REPLACEMENT_REQUIRED`, with absent implementations and condition tests not run.
These are explanations and dependency contracts, not accepted implementations or
new gate slots. They follow the existing virtual-namespace and host-service scope
in the [outline](../outline.md).

| Source surface | Required treatment |
| --- | --- |
| `RESTORE-LISP-POINTERS`: batch flag | Loader-supplied startup input, as above. |
| `KERNEL-PATH` | Replace the native pointer/C-string implementation with the bootstrap resource's name in the host-provided virtual namespace. Do not copy the native kernel-global offset or discard the containing function. |
| `SAVE-IMAGE`: `#_exit` | Declared Lisp-process termination service preserving the failure status and nonreturning behavior. No arbitrary foreign lookup. |
| `SKIP-EMBEDDED-IMAGE` | Native executable-trailer scanning is native-only machinery. Wasm uses its bundle manifest; any reachable request for native embedding needs a tested Lisp condition. |
| `%PREPEND-FILE` | Native executable-prefix copying is native-only machinery. Keep image saving separate; a native/prepend-kernel request needs an explicit, tested condition. |
| `OPEN-DUMPLISP-FILE` | Capability-gated bundle output in the virtual namespace. POSIX flags, chmod and native file descriptors need replacement. Missing write capability requires a tested condition. |
| `RESTORE-LISP-POINTERS`: `REFRESH-EXTERNAL-ENTRYPOINTS` | Restore the declared runtime/host entry registry without loading the excluded native FFI interface database. This required startup call cannot simply be deleted. |
| `RESTORE-PASCAL-FUNCTIONS` | Restore validated Wasm/JavaScript callback entries. Native macptr revival and machine-code trampolines need replacement; the foreign-thread exclusion does not remove the required Lisp callback dispatcher. |

The five remaining collection stops are `SAVE-IMAGE`, `SKIP-EMBEDDED-IMAGE`,
`%PREPEND-FILE`, `KERNEL-PATH` and `OPEN-DUMPLISP-FILE`. Their first-error messages
are preserved. The reader still refuses missing foreign names/constants; none
are supplied from the host. Classifying native-only machinery does not discharge
a required startup function or save operation. A profile `unsupported`
disposition requires the implemented and tested condition path specified by the
[census contract](../contracts/census.md).

## Retaining the containing function and its initializers

Filling in the stream type exposed a second boundary in the collection mechanism:
the compiler processes four `LOAD-TIME-VALUE` initializers before completing
`CLEAR-IOBLOCK-STREAMS`. Stopping at the first pass-2 call would capture an anonymous
initializer instead of that definition. The source-name oracle rejects this.

The census pass-2 extension retains each initializer and returns a distinct native
refusal closure while U1 constructs the deferred load-time literal. It requires
the real file compiler's deferred-evaluation token and refuses execution. The
outer function then reaches pass 2 and exits before FASL dumping or installation.
A separate walk of the actual acode literals joins each closure by EQ to its
initializer and verifies its owning function. Four initializer bodies have four
distinct literal sites: one calls `FIND-CLASS-CELL`; three call `ENSURE-SLOT-ID`.
The latter arise from the slot-boundp, slot-value and setter compiler macros in
U1 `compiler/optimizers.lisp`. Their dependencies remain in the facts.

An early development version used identical constant guard functions. CCL shared
the function object, making all four links point at the last initializer. The
retained capture shows the defect. Guards now close over distinct ordinals, and
the native alias control reproduces the defect and is rejected by the bijection
check. The original first formal failure was a checker expectation placing both
older indirect calls in one source form; the retained source and capture show
one each in SAVE-APPLICATION and %SAVE-APPLICATION-INTERNAL. The corrected check
preserves those two plus five unresolved calls in the restore routine.

## Validation and limits

Two fresh normal sessions produce identical raw capture bytes. All six native
controls and twenty-six analysis controls reject. Ordinary and nonlocal returns
restore the temporary census tables and pass-2 callback. All twelve original
source function bindings, the pristine source and the loaded FASLs are unchanged.
No shared compiler or kernel source is patched, and no target FASL or image is
written. The accepted registration and earlier traversal sources are unchanged.

Macro expanders still come from the native image. Their source notes and active
target context are observed; the full macro environment is not yet qualified for
Wasm. The batch access is a described service dependency, not an implemented
lowering. All facts therefore remain unqualified and the seven computed calls
retain unknown target sets. Further modules and general top-level effects are
outside this fixed-file driver.

Next, implement or refine the declared boundary replacements in isolated fixtures,
qualify the target macro environment, and bound the restore callback calls before
using these facts to remove any broad graph edge. Stage 0 remains 28 accepted,
20 missing and zero unreviewed required records out of 48. This packet itself
awaits independent review.
