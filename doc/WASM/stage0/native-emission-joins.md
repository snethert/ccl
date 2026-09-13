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
| Parameterized subprimitive calls / targets | 20,606 / 36 |
| Unknown offsets in decoded calls | 0 |
| Rejected controls / synthetic operand layouts | 17 / 6 |

The executed decoder families are CALL-SUBPRIM and JUMP-SUBPRIM. The other four have synthetic layout coverage only. The 141-slot count denotes memberships in the recorded dispatch table, including aliases sharing a handler; it is not a count of independently exercised operators.

## Joins and their scope

Every instruction emission is checked, in sequence, against the independently reviewed compiler join file. The raw stream supplies the evaluated template object's identity and attributes, the emitting front-end function, and live handler frames with their evaluated dispatch-slot memberships. The graph adds function-to-template dependencies, handler-to-template dependencies and operator-to-handler identities in the build process's namespace. Template counts and event bounds remain in the witnesses. The capture includes the observation definitions compiled in the instrumented source files; these counts are not a measurement of the future Wasm runtime or its minimal dependency set.

A live handler frame establishes that the instruction was emitted within its dynamic extent. It does not identify a tail-elided leaf handler, nor prove that an observed path covers every branch. Multiple dispatch slots can share one handler. The existing unresolved static-template obligations remain present. Code and template identities from another process are not substituted by printed name.

The decoder covers six parameterized U1 templates: JUMP-SUBPRIM, CALL-SUBPRIM, CALL-SUBPRIM-NO-RETURN and CALL-SUBPRIM-1/2/3. Their pinned x86-64 definitions place the constant target after output slots and before label temporaries in the operand vector. The decoder requires the complete vector shape and an integer literal. An independent literal-slot reading checks the target counts. Synthetic controls exercise all six layouts; the summary separately lists which families actually executed.

Recorded offsets join the evaluated subprimitive table only after checking that the build and table inspection used the same kernel identity. The base graph's named table entries must also carry the matching offset. Unknown offsets become explicit unresolved nodes. Other templates, fixed subprimitive-call templates, foreign targets, pointer stores, traps and Wasm dispositions need their own classification; template attributes alone do not establish those meanings.

## Verification and remaining work

The checker bounds the complete set of added nodes and edges, including full node metadata, endpoints, phases, provenance and multiplicity. Corruption controls omit each dependency relation, insert surplus records, change a process namespace, narrow candidate sets, alter emission counts, substitute a valid but wrong subprimitive name and damage operand vectors. The genuine materialized graph must pass the exchange schema and graph invariants before the packet succeeds.

This completes the observed-emission join, not S0-LL15-b/c. The retained base preserves earlier scenarios and their unresolved obligations. Boot-process coverage, full source traversal under the registered target, reviewed seeds and dynamic-call bounds, and the remaining lowering classifications are still needed for a passing complete census. External review and project acceptance remain separate. The recorded Stage 0 gate stays at 28 accepted, 21 missing and zero unreviewed.
