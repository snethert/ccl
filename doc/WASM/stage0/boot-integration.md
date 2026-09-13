# Boot execution in the census graph

The reviewed boot capture and cold-origin witness are now integrated into the census exchange graph. This completes the next assembly step after [Claude's seventeenth audit](claude-review.md) at `079c14d7`. [Claude's eighteenth audit](claude-review.md) at b90771bb re-executed the producer and materializer and found no defect; the integration does not accept LL15-b/c or change the Stage 0 gate.

| Integrated record | Count |
| --- | ---: |
| Observed event boundaries with ordered prerequisites | 52,441 |
| Cold initializer executions with source-module joins | 133 |
| Cold source modules / compiler source contexts | 31 / 131 |
| Completed loads / loader initializer calls | 121 / 8,326 |
| Function-cell installations / removal intents | 9,335 / 9,289 |
| Function cells with initial and final checkpoints | 9,094 |
| Loader filenames / distinct byte-bound paths | 122 / 120 |
| Active frames at handoff, with no invented returns | 3 |
| Corruption controls rejected | 33 |

The [runner and materializer](../../../tests/wasm/native-census/startup-closure/README.md) reuse pinned, reviewed inputs. They reconstruct the prior emission graph byte-for-byte, reproduce the reviewed boot analysis, and add a fragment containing 79,406 nodes and 193,896 edges. The full graph has 327,961 nodes and 816,362 edges. Existing nodes, edges, initializer records, seeds and external trace observations remain unchanged.

## What the joins mean

Every recorded event becomes an initializer *boundary*, including entry, return, binding change and handoff. Its prerequisite is the preceding event in this boot process. An entry assertion witnesses entry only. A removal assertion remains a pre-clear intent. Nesting is expressed by graph edges to enclosing entries; it never requires an enclosing call to return before its child can run. The three frames still active at handoff receive no completion records.

Call and reader edges point to boot-process object identities. Function-cell changes point to their actual cell, old value and new value, with separate initial and final checkpoint edges. Object descriptions are retained as provenance, not used to equate objects by name across runs. Of the cell values, 1,059 are opaque vectors in the retained description. They were left unresolved in this original fragment. The subsequent [wrapper export](boot-wrappers.md) identifies all of them as ordinary macro/special-operator representations and adds their contents and callable references. These are census analysis obligations, not 1,059 additional Stage 0 acceptance slots.

Each cold function and its entry boundary has an explicit edge to the source module identified by the reviewed xload witness. The complete origin record, including the FASL offset and optional context, is retained alongside those edges. Entries 65 and 106 keep their null source ranges. Source modules also link explicitly from the existing logical source inventory, using conservative path-membership edges. That expresses membership in the same named module surface; it does not assert identical source bytes or callable objects between captures. Each boot source version keeps its own byte identity, including the two reviewed observation-source variants.

`backend.dx64fsl` and `hash.dx64fsl` each appear under absolute and relative filenames. Each pair becomes one boot module only after its retained size and digest agree. Both load/reader histories remain present. The boot and source modules remain separate from file observations in the external clean-image trace.

The historical build-process gap is retained and points conservatively to this separate boot witness. The new run does not retroactively supply events from the earlier unobserved subprocess. Final scenario reconciliation must explicitly select the reviewed witnesses and supersede historical provisional obligations; this fragment does not silently rewrite them.

## Verification and remaining work

The independent checker derives complete node records, edge relations with multiplicity, event prerequisites, source origins and active-frame records from the retained inputs, without invoking the graph producer. It rejects omissions, surplus records, cross-process callee substitutions, invented returns, concealed opaque values, altered source ranges, checkpoint omissions and changes to the old graph or trace. Both the producer and checker reject inconsistent bytes for a loader alias.

The full exchange graph passes schema, reachability structure, initializer ordering and module-inventory checks. It remains blocked only by explicit unresolved edges and nodes. The standalone materializer rechecks the retained fragment and reproduces the producer's full graph byte-for-byte. No native execution, new instrumentation, full build-stream replay, acceptance rebind or archive-wide scan is performed.

The first development run rejected conflicting module records for the two loader aliases. Its original source, run record and log are retained. The corrected producer and alias controls pass. One compact [evidence packet](../evidence/boot-integration-summary.json) retains the fragment and checks; full graphs and unchanged prerequisite captures are referenced rather than duplicated.

Next: extend source traversal against the registered target, review the seeds and conservative dynamic-call bounds, review the completed wrapper-content update, finish lowering/import/store classifications, and reconcile the final scenario before the complete closure and omission tests. Stage 0 remains 28 accepted, 20 missing and zero unreviewed required records out of 48.
