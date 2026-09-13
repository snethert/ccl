# Compiler and loader identity observations — 12 September 2026

The missing information can be gathered. The [new observation unit](../../../tests/wasm/native-census/rich-observation/README.md) extends collection in disposable pristine U1 archives. It records macro-expansion hook calls and their supplied expanders, native function materialization, function-cell changes, executed initializers and instruction emissions. It also inspects the exact clean image retained by the external file trace. No new administrator trace is required.

The unit patches nine shared sources as one reversible operation. It changes no existing target-specific source or kernel source. The implementation checkout remains clean U1; observed sources, binaries and the saved image are evidence only.

## Identity joins

Function installation is observed after the primitive store. Removal intent is observed before the primitive clear. No callback runs in the unbound interval: two original full-build failures showed that CCL redefines helpers the logger itself uses, first `%LFUN-INFO-INDEX` and then `STRING-DOWNCASE`. The corrected placement has native positive cases for both helpers and mutants that reproduce the unsafe interval. Both original failures remain retained.

A third complete build exposed an output difference: the added macro-observation helper DEFUN consumed three compiler gensyms, changing later generated names. Recording-disabled reproduction rebuilt all 164 FASLs byte-identically to that run. Inlining the three observation sites removed the cause; the subsequent fast full-build check leaves only the eight intended shared-source FASLs different. The correction neither normalizes output nor adjusts compiler counters; both sides use the same retained baseline preparation. The original failed comparison remains retained.

FASL write and read records join actual function objects through the same file's exact opcode position. Compiler materialization supplies the front-end function identity. Compile-time and loader initializer records identify the callable actually executed and preserve its completion and values. The conservative per-process effect schedule retains entry and completion boundaries so nested effects do not create artificial cycles. It does not claim a minimal analysis of state reads and writes.

Each reader invocation also carries the actual callable and dispatch-table mode. The full stream exposed a case absent from the small host corpus: the cross-dumper returns a tagged image word, not a host function. The reader now preserves these in a separate namespace and rejects mode/type contradictions. Completing an image-builder reader operation does not mark its queued Lisp initializer executed.

Expansion records retain the invoked hook designator and supplied expander object. The native corpus uses the default FUNCALL hook; a custom hook's own internal calls would require separate analysis. CCL sometimes creates separate expanders for the compilation environment, global macro binding and serialized FASL. Identical printed names do not merge these objects. The three-layer corpus checks actual called expander identities, six function installations, six macro installations, retained older definitions, SETF identities and a real computed call.

Emission records retain evaluated templates, operands, current function identities and actual live dispatch-handler stack frames. The observer does not wrap or modify native handlers. Tail-elided frames remain unavailable; a live ancestor is not asserted to be the exact leaf operator. Native imports and stores still require their own target classification.

The [execution summary](../evidence/rich-census-summary.json) records the completed collection:

| Observation | Collected and joined |
| --- | ---: |
| Native compilation sources | 164 of 164 |
| Materialized front-end functions | 51,601 |
| Compile-time initializer callables | 18,907 |
| Executed loader initializer callables | 4,660 |
| Deserialized host functions joined by exact FASL position | 11,493 |
| Image function words joined separately | 1,240 |
| Function-cell installation events | 6,620 |
| Macro-expansion hook invocations | 745,930 |
| Native instruction emissions | 2,052,019 |
| Live handler code identities joined | 207 of 207 |
| Cold-start callbacks completed | 35 |

## Exact traced image

The existing inspector ran against the exact kernel and image named by the retained Terminal trace. It found 15,424 resident functions and 10,050 bindings. Existing foreign tables supply 65 kernel-import offsets, 118 external entry points, zero foreign variables and 43 library records. Evaluated import offsets join U1's explicit assembly table; three damaged-table controls reject. The inspector does not resolve new entry points or invoke imports.

The inventory comparison with the previously inspected r7 image preserves both image identities. Bindings, callback groups, operator slots, vinsns and subprimitives agree. Eight function rows differ only in printed combined-method names containing heap addresses; the differing fields are retained without normalization. This compares inventories, not heap bytes.

## Verification and remaining closure work

The independent three-layer checks reject three actual collector omissions while the unchanged native program still passes and its three FASLs remain byte-identical. Sixteen further semantic mutations reject damaged joins, reader mode and effect ordering. Eight reader controls reject dispatch/type contradictions; the original image-word failure is retained as a regression. The apply/remove unit has two positive recovery cases and five rejection controls. Two helper-redefinition mutants reject. Twelve JSON cases compare exact bytes against the original writer and round-trip through a separate parser.

Both native suites passed all 21,843 eligible tests, with the same 75 upstream-disabled cases disclosed. Of 164 native FASLs, 156 are byte-identical and eight are the intentional shared-source artifacts. The three unchanged corpus FASLs match. Actual initializer omission and reordering both fail the native prerequisite-state assertion. After removal, a clean rebuild reproduces all 164 baseline FASLs. The clean baseline is retained once and reused across the failed observation attempts.

The first cold-start attempt failed after these successful stages: the initial thread opened a private stream, then the listener tried to finish it. The correction adds `:sharing :external` only to the cold-start OPEN; the existing event lock serializes writes. A separately pinned continuation restores the retained observed image, successfully captures cold startup and completes the clean rebuild. The original failed run stays unchanged. The successful full compilation and regression tests used the retained pre-correction observer; the continuation uses the corrected observer. No additional full compilation capture was needed for this cold-only correction.

The build stream observes the parent compiler and its actual loads. It does not observe the boot-image subprocess's L1 installation. Cold-start callbacks and the exact traced-image snapshot are separate witnesses. The corpus's L0/L1/L2 names denote its test layers, not complete observation of every bootstrap installation.

These are collected inputs to LL15-b/c. Next, assemble their identities and conservative effect order into the exchange graph, complete static source traversal under the registered target, classify native lowering/import/store operands, and review seeds and call bounds. Future generated or externally loaded code must remain explicit in those bounds. Run the complete passing census and its omission mutants before claiming LL15 qualification. External review and project acceptance remain separate; existing accepted records are unchanged.

The raw graph includes observation code compiled in the eight changed FASLs. Use the retained patch and clean baseline to distinguish those calls during assembly. Its raw dynamic-call count is not a count of independent missing project tasks.

The finalized packet contains 148 files, approximately 1.33 GB, including the original large failure streams and one successful full capture. It retains one baseline archive and eight changed FASLs; redundant successful development captures were removed. Finalization verified only this new packet and preserved every prior catalog entry unchanged.
