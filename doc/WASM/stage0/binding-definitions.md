# Unwitnessed binding definition batch — 15 September 2026

The [new integrated command](../../../tests/wasm/native-census/binding-definitions/README.md)
accounts for the complete 95-symbol worklist from the development closure,
covering 345 global call sites. It adds actual compile-phase references for 85
of those symbols and leaves the remaining ten as specific work items. It does
not establish any previously unwitnessed runtime value or exhaustive call bound.
The expected result remains **BLOCKED, exit 2**; no Stage 0 slot receives credit.

| Population | Established relationship | Still required |
| --- | --- | --- |
| 80 symbols | Exact AFUNC name references identify 79 MAKE functions and UIOP/STREAM::OUTPUT-STRING; their native materializations already have reviewed compiler bodies. | Installation/load correspondence and the runtime value bound. |
| Five reader/accessor symbols | Actual input forms of four normally completed DEFINE-CONDITION/DEFCLASS expansions reference the same original symbols. | Accessor construction, installed method identities, dispatch and target lowering. |
| Three SETF cells | Printed inverse annotations suggest the prefixed/timestamped stream accessors. | An actual original-symbol/SETF-cell registry identity link; no graph alias is inferred. |
| Seven other symbols | Pinned U1 source locations for PARSE-STANDARD-FFI-FILES, the PPC/ARM LAP definers, XLOAD-ARM-SET-ENTRYPOINT and three XREF operations. | Phase/profile analysis, any required loading and callable identity. The two generated XREF operations currently have their DEFSTRUCT as a source lead. |

MAKE is the older DEFSYSTEM implementation in `tools/defsystem.lisp`. Its 81
previously unwitnessed symbols split into 79 compiled-name joins and two
condition reader declarations. Three other accessor symbols occur in
`library/prefixed-stream.lisp` and `library/timestamped-stream.lisp`. No decision
to exclude these portable Lisp libraries is made here. Swink's existing browser
exclusion remains unchanged.

The distinction between compilation and installation is observable in U1's
`fcomp-load-%defun`: its optimized path emits a FASL definition operation. It does
not install that ordinary definition just because its body was compiled. This
packet claims the recorded compilation and materialization only; it does not
claim that a definition opcode was subsequently loaded, that the cell was
unbound, or that no installation could have escaped the observer. Likewise,
recording a class declaration does not observe its runtime accessor population.
A new ordinary rebuild by itself would not resolve that distinction; fresh
observation should cover the required loading/registration paths.

The runner reads all 4,006,405 original events, checks contiguous sequence and
completion counts, and retains 88 selected original events. It joins compiler
functions using the raw AFUNC name reference and the original symbol descriptor,
not the displayed function name. It pairs each selected declaration's normal
expansion return by nesting, process and argument identities. The form's
reader/accessor syntax establishes a declaration reference, not a proof of the
expander's target semantics or a method construction. Seven direct reader/accessor
references arise from the four events: the condition is seen once as
DEFINE-CONDITION and again in its DEFCLASS expansion.

The graph gains 80 compile-phase edges to existing compiler bodies, seven edges
to declaration occurrences, and four unresolved construction nodes. It now has
369,710 nodes and 1,090,024 edges. Every earlier record, seed, trace and initializer
remains unchanged. The existing census checker reports 31,206 unresolved edges
and 34,013 unimplemented nodes, exactly four more of the latter. All 5,693 runtime
value bounds, the 95 unwitnessed cells, 5,007 original body obligations and 1,562
computed calls remain open. **Zero original runtime obligations close.**

The 22 regressions reject changed object/code identities, missing observations,
changed source/return records, substituted accessor roles, compile references
promoted to runtime bounds, invented implementation, missing old records and
incorrect source-only classifications. They exercise the integration, not the
independent instrumentation omissions required by LL15-c. The full working graph
is reproducible from the preceding closure and the compact new delta.

The fresh verifier re-reads the complete stream and reconstructs the preceding
graph without the cached `--base` option. All six outputs and the new working
graph are byte-identical to the first run. The packet binds six retained inputs,
42 source files including 14 unchanged U1 sources, and the replay interpreter.
It contains 19 files totaling 395,510 bytes; the 16 MB graph is not duplicated.
No fixture run failed. The preliminary extraction and an interrupted ad hoc
query are disclosed in the development notes. Verification covers the new work
and direct inputs, with no native build, historical payload scan or accepted
aggregate regeneration.

The next work must join required module/registry behavior and apply candidate
bounds. Recollecting the same compilation evidence would add no information for
these 85 references. The user permits a combined native build when its additional
load/body/registry witnesses are more efficient than separate recovery steps.
Observation remains reversible in disposable U1 copies; implementation starts
clean. This packet awaits independent review, with the ledger unchanged at 40
accepted, eight missing and zero unreviewed.
