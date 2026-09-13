# Initializer identities in the census exchange

The [integration runner](../../../tests/wasm/native-census/startup-closure/README.md) adds the reviewed compiler/loader execution identities to the existing census exchange graph. It links 18,907 compile-time initializer calls, 4,660 loader initializer calls and 35 cold-start callbacks to their recorded code identities. Compile and loader calls also retain their returned-value witnesses. These records are now graph edges and initializer prerequisites, rather than only a separate collector report.

The two captures reviewed in [Claude's tenth audit](claude-review.md) have different preparation and execution histories. Their code IDs remain in separate namespaces. Every original projection node, edge, initializer, seed and trace observation is preserved. This integration does not promote a provisional initializer in the older run merely because a similar initializer executed in the newer run. The final scenario still needs to reconcile or supersede those provisional obligations with corresponding source and execution witnesses.

## What the added graph establishes

Each recorded effect has entry and return boundaries. A boundary depends on the preceding recorded effect boundary in its own process. This preserves nested evaluation without introducing the false cycle that results from requiring an enclosing initializer to finish before a nested initializer starts. It is a conservative execution order; it does not claim a minimal analysis of every state read and write.

The build contributes 64,900 boundaries and cold startup contributes 70. Compile-time callees link directly to materialized front-end functions. Loader callees link through the actual FASL read and its matching write position to the materialized function. Completion assertions identify the corresponding returned-value event and its retained object-graph digest. Numeric code identities from the build and cold processes cannot substitute for one another.

Of 13,543 reader effects, 12,347 use the native loader and 1,196 use the image builder. Both have recorded reader identities and normal completions. An image-builder return explicitly leaves queued Lisp execution unobserved. The boot-image subprocess's L1 installation remains a separate required witness. The external trace continues to describe its original clean-image scenario.

## Verification and scope

The original integration passed input-coverage checks and the existing exchange schema and graph invariants. Its thirteen controls rejected wrong-process callees, incorrect serialization/materialization links, reader and callback substitutions, invalid nested-effect ordering, changed result witnesses, false image-execution claims, hidden boot/static-dependency obligations, removed loader seeds, trace conflation and omitted boundaries. Each mutation failed its own check. Claude's subsequent review identified surplus-record insertions that those controls did not exercise.

This is an integration deliverable, **not LL15-b/c qualification**. The complete census remains blocked. The added explicit scope nodes describe existing missing work, not additional project tasks: the boot-process witness, complete static dependencies and target dispositions. The next closure work is full source traversal under the registered target, conservative bounds for the retained 1,729 dynamic call sites, review of the thirteen seeds, and lowering/import/store classification. LL15-c still requires the complete passing census and its omission mutants.

See the [execution summary](../evidence/initializer-joins-summary.json) for the packet identity and exact counts. Finalization checks only the new packet; no native source was edited, native build repeated, acceptance aggregate regenerated or historical archive rehashed.

## Checker correction — 13 September 2026

The checker now derives the complete added node-ID/kind set and edge multiset from the captures, independently of the graph producer. The edge comparison includes endpoints, phase, origin, resolution and evidence identity as well as multiplicity. Initializer records must be unique and match the expected inventory; the added module inventory must also match exactly. This closes the insertion gap alongside the existing substitution and omission checks.

Five added controls cover an extra cross-process edge, a reachable invented function, a duplicate initializer, a duplicate workload edge, and a changed source-module edge endpoint. The focused verifier reproduces their escapes with the former checker at f3b4b07e and requires all eighteen cases to reject with the corrected checker. The original graph and witnesses are reused unchanged; the producer is checked for unchanged code and dependencies. This correction awaits independent review and does not mark the original packet reviewed.

The development output named `/tmp/ccl-identity-join-r1` completed successfully and was superseded by the instrumentation-pin edit. The subsequent successful command used an r2 directory and became the retained `NATIVE-INITIALIZER-JOINS-R1` packet. The first successful temporary outputs are no longer available; the new packet records this explanation without reconstructing their run record or claiming their artifact identities. The new development note records the first run as a superseded success.

The checker follow-up is a five-file packet of approximately 10 KB. It contains the verification and development explanation; the original 12.4 MB graph packet is referenced in place. The [summary](../evidence/initializer-joins-summary.json) retains the original thirteen-control result and separately identifies the eighteen-control follow-up.
