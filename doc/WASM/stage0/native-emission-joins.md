# Native emission dependencies in the census

The emission joiner adds the retained native compiler's actual instruction dependencies to the initializer census. It uses the full compiler capture reviewed by Claude's tenth audit and the initializer graph reviewed through the thirteenth audit at 7244b27e. It runs as analysis of existing evidence; it changes no compiler, kernel or observation hooks.

The [summary](../evidence/native-emission-summary.json) records the executed counts and packet identities. The [runner](../../../tests/wasm/native-census/startup-closure/join_lowering.py) writes an additive graph fragment and compact identity witnesses. Materializing that fragment with its pinned base produces the existing census exchange format. The retained packet does not duplicate the original graph or native build files.

| Retained observation | Joined |
| --- | ---: |
| Instruction emissions | 2,052,019 |
| Emitting front-end functions | 51,342 |
| Template identities / names | 609 / 413 |
| Live handler code identities | 207 |
| Dispatch slots represented in those frames | 141 |
| Explicit joins to evaluated image slots | 141 |
| Parameterized subprimitive calls / targets | 20,606 / 36 |
| Unknown offsets in decoded calls | 0 |
| Rejected controls / synthetic operand layouts | 32 / 6 |
| Synthetic unknown-offset refusal | 1 |

The executed decoder families are CALL-SUBPRIM and JUMP-SUBPRIM. The other four have synthetic layout coverage only. The 141-slot count denotes memberships in the recorded dispatch table, including aliases sharing a handler; it is not a count of independently exercised operators.

The 609 template identities cover 413 names because 196 names each have two identities with sequential, nonoverlapping emission ranges. This is consistent with recompiling and reloading vinsn definitions during the build; the ranges alone do not establish that cause. Both identities and their ranges remain retained.

## Joins and their scope

Every instruction emission is checked, in sequence, against the independently reviewed compiler join file. The raw stream supplies the evaluated template object's identity and attributes, the emitting front-end function, and live handler frames with their evaluated dispatch-slot memberships. The graph adds function-to-template dependencies, handler-to-template dependencies and operator-to-handler identities in the build process's namespace. Template counts and event bounds remain in the witnesses. The capture includes the observation definitions compiled in the instrumented source files; these counts are not a measurement of the future Wasm runtime or its minimal dependency set.

The base contains 279 evaluated image operator slots, including the 141 represented in the emission fragment. Each of those 141 now has an explicit edge from the image slot to its build-process representation. The edge's evidence key identifies a witness containing both evaluated records and the verified common kernel digest. ID, name, flags, encoded value and handler name must agree; the image-slot node must match the pinned image metadata. This establishes the same evaluated slot across captures. Image function IDs and build handler code IDs stay in their own namespaces; the join makes no assertion that those process-local code objects are identical or that observed paths exhaust the handler's dependencies.

A live handler frame establishes that the instruction was emitted within its dynamic extent. It does not identify a tail-elided leaf handler, nor prove that an observed path covers every branch. Multiple dispatch slots can share one handler. The existing unresolved static-template obligations remain present. Code and template identities from another process are not substituted by printed name.

The decoder covers six parameterized U1 templates: JUMP-SUBPRIM, CALL-SUBPRIM, CALL-SUBPRIM-NO-RETURN and CALL-SUBPRIM-1/2/3. Their pinned x86-64 definitions place the constant target after output slots and before label temporaries in the operand vector. The decoder requires the complete vector shape and an integer literal. An independent literal-slot reading checks the target counts. Synthetic controls exercise all six layouts; the summary separately lists which families actually executed.

Recorded offsets join the evaluated subprimitive table only after checking that the build and table inspection used the same kernel identity. The base graph's named table entries must also carry the matching offset. Unknown offsets become explicit unresolved nodes. Other templates, fixed subprimitive-call templates, foreign targets, pointer stores, traps and Wasm dispositions need their own classification; template attributes alone do not establish those meanings.

## Verification and remaining work

The checker bounds the complete set of added nodes and edges, including full node metadata, endpoints, phases, provenance and multiplicity. Corruption controls omit each dependency relation, insert surplus records, change a process namespace, narrow candidate sets, alter emission counts, substitute a valid but wrong subprimitive name and damage operand vectors. The genuine materialized graph must pass the exchange schema and graph invariants before the packet succeeds.

The follow-up also rejects missing or redirected same-slot edges, missing or changed witnesses, and mismatches in every evaluated slot field. A synthetic out-of-table operand projects onto the genuine census as a required unresolved subprimitive; the unchanged generic checker must report exactly one additional unimplemented reachable node, with all other errors unchanged.

Claude's [fourteenth audit](claude-review.md) found the original observed-emission fragment acceptable at its stated scope, but required the operator reconciliation before closure. The fifteenth audit, recorded at 83573620, independently reproduced the corrected fragment and its materialization, found no defect, and closed that finding and both low notes. Both emission packets are reviewed as diagnostic census inputs; LL15-b/c qualification remains open. The original NATIVE-EMISSION-JOINS-R1 packet remains intact. The corrected fragment uses delta format 2. Historical format-1 materialization remains reproducible with the sources at 363fc2d4; the current checker requires the explicit joins.

The first correction run stopped in the new unknown-offset control because an existing loop variable shadowed the graph-ID helper. The packet retains that failed run, log and test source. Renaming the variable fixes the test-driver error; the complete analysis was rerun in a fresh output directory. A later one-off report writer mistakenly called the file-size attribute after successfully materializing the graph; its source and traceback are also retained. Correcting the attribute access and repeating materialization produced byte-identical complete graphs. The failed commands are not counted as passing proofs.

This completes the observed-emission join, not S0-LL15-b/c. The retained base preserves earlier scenarios and their unresolved obligations. Boot-process coverage, full source traversal under the registered target, reviewed seeds and dynamic-call bounds, and the remaining lowering classifications are still needed for a passing complete census. External review and project acceptance remain separate. Following the unrelated [second-Mac retirement](second-mac-decision.md), Stage 0 has 28 accepted, 20 missing and zero unreviewed; this fragment adds no gate credit.
