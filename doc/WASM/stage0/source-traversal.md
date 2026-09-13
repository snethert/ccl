# First source traversal — 13 September 2026

Status: executed; reviewed without defect by [Claude's twenty-first audit](claude-review.md) at 4c7f2162. Evidence packet
`NATIVE-SOURCE-TRAVERSAL-R1` is retained in `2026-09-13-source-traversal-r1` and
bound by the [evidence index](../evidence/index.json). The first driver accounts for every
top-level form in pristine U1 `lib/dumplisp.lisp`, using the accepted census
backend. It replaces none of the broad dependency edges and confers no gate credit.

| Result | Count |
| --- | --- |
| Source forms accounted for, through EOF | 16 |
| Top-level function definitions | 12 |
| Definitions with captured front-end bodies | 4 |
| Definitions stopped by an explicit target gap | 8 |
| Captured initializer bodies | 2 |
| Code prototypes, including nested functions | 12 |
| Call sites / function-reference sites | 40 / 9 |
| Calls without a resolved target expression | 2 |

The four captured definitions are `KILL-LISP-POINTERS`, `SAVE-APPLICATION`,
`%SAVE-APPLICATION-INTERNAL` and `%SAVE-APPLICATION`. The initializer captures are
the load-time package operation and the special proclamation. DEFVAR forms are
handled by the real file compiler and retain their deferred output opcodes;
their initializers are not claimed executed. Capturing a DEFUN exits before its
load plan is completed. No captured function is installed or run.

## Concrete target gaps

| Source definition | First operation that stops traversal |
| --- | --- |
| `CLEAR-IOBLOCK-STREAMS` | The small descriptor lacks `:BASIC-STREAM` support |
| `SAVE-IMAGE` | No target foreign entry for `exit` |
| `SKIP-EMBEDDED-IMAGE` | No target foreign constant `SEEK_END` |
| `%PREPEND-FILE` | No target foreign constant `SEEK_SET` |
| `KERNEL-PATH` | No `%GET-KERNEL-GLOBAL-PTR` macro for the census architecture |
| `OPEN-DUMPLISP-FILE` | No target foreign constant `O_RDONLY` |
| `RESTORE-LISP-POINTERS` | No `%GET-KERNEL-GLOBAL` macro for the census architecture |
| `RESTORE-PASCAL-FUNCTIONS` | The descriptor lacks `:VECTOR-HEADER` support |

These are limitations of the existing observation descriptor and target interface
data, not newly found defects in native CCL. The descriptor was accepted for its
fourteen-form fixture, not for arbitrary upstream source. Each stopped definition
reports the first error, so this table is not an exhaustive list of everything
needed to compile those bodies. In particular, no host foreign constants or
kernel offsets are substituted to make target reading succeed.

The `UNSUPPORTED` capture status records a collection gap. It grants no
`unsupported` profile disposition under the census contract.

The driver resumes at the next source boundary. Later rows retain their preceding
unresolved forms: compilation after a failure does not establish a complete file
environment. Macro expansion records identify the expander's source and the
active backend, but the expanders come from the clean native image. Their full
target suitability is not yet qualified. Every emitted dependency fact therefore
remains unqualified, including named calls; the two computed calls retain their
empty target sets rather than being widened to the whole image.

## Mechanism and checks

The runner loads the accepted LL08-a registration binaries in a fresh process
over pristine U1 source, the retained clean r7 image, and bootstrap interface
data. This reuses the reviewed registration behavior without another shared-source
patch or rebuild. The actual registered module lookup loads the architecture and
capture backend. Native compiler/kernel source in the main checkout is untouched.

A native read and a read-suppressed read agree on all sixteen boundaries. They
provide an independent coverage inventory; target forms are separately read from
the original text after target state is established. Each form then enters the
real `fcomp-form`. The pass-2 escape is caught per form, preserving all later
definitions. The pinned module has only the four top-level kinds described in
the [driver instructions](../../../tests/wasm/native-census/source-traversal/README.md);
this is not yet a general module loader or top-level macro traversal.

Two normal sessions produce identical captures. The native controls actually
stop after the first capture or use the host reader context; both are rejected.
Twenty-one analysis controls reject omitted forms, bad ranges/EOF, hidden failures,
missing functions/calls/references, surplus functions/edges, and false macro or
closure qualification. Exact derived records are compared, including their
provenance and multiplicity. Focused replay reproduces these checks.

Target state and all twelve original function bindings are restored/unchanged.
The source files and loaded FASLs are unchanged; no target FASL or saved image is
produced. One compact packet retains the capture, derived facts, native mutants,
controls, commands and development records. The main source graph and existing
accepted results are unchanged. Stage 0 remains 28 accepted, 20 missing and zero
unreviewed required records.

Next, qualify the target macro environment and resolve the descriptor/interface
gaps needed by these twelve definitions before expanding to more modules. These
require explicit target layout and replacement choices, not guessed host values.
Only a complete dependency replacement can remove the corresponding broad graph
edges; a successful sixteen-form accounting run does not supply that replacement.
