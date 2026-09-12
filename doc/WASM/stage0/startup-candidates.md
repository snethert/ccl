# Startup candidate preparation — 12 September 2026

The [new packet](../evidence/startup-candidates-summary.json) adds clean-image code identities to the reviewed r7 dependency inputs and proposes the startup seeds for independent review. It is preparation for LL15-b/c, with no gate credit. The complete contract exchange graph is still open.

A separate process starts the retained **clean** r7 native image and enumerates its resident code prototypes, function and macro bindings, existing SETF bindings, startup callback objects and evaluated backend tables. It loads the inspector without enabling the observation hook. It neither patches shared source nor saves an image. Implementation still starts from pristine U1 and its bootstrap.

| Observation | Result |
| --- | --- |
| Resident native code prototypes, including inspector code | 15,424 |
| Retained r7 compiler-object identities | 51,342 |
| Current native function / macro bindings | 9,031 / 1,019 |
| Proposed entrypoint seeds | 13 |
| Startup callbacks identified by their actual code | 35 |
| Evaluated operator slots / slots with handler code identities | 279 / 247 |
| Evaluated vinsn templates / subprimitives | 599 / 154 |
| Previously unmatched global names with a native binding candidate | 768 of 951 |
| Names still lacking a named candidate in either input | 183 |

These are inventory counts, not missing implementation tasks. The native and compiler identities are separate namespaces; overlapping functions and repeated compilations must not be counted as distinct production functions. The inspector is included explicitly rather than silently subtracted.

The packet retains all resident code and all r7 compiler bodies in one shared candidate set for the 1,729 unresolved dynamic calls. No address-taken pruning occurs, and old source versions remain. This finite set is **not yet a proved bound**: the captures do not establish completeness for static stub-backend paths, arbitrary future EVAL, FASL loading, rebinding or plugins. The producer consequently leaves every affected call `UNQUALIFIED`. Adding candidates does not discharge the closure obligation.

Native binding identities describe this clean-image snapshot. A matching printed name proposes a candidate; it does not establish the active binding at an earlier call. SETF records retain the package-qualified original symbol alongside the uninterned cell name, and the join preserves collisions. Function and macro namespaces remain separate. Startup variable labels are not treated as function names: callbacks are joined through the actual callable objects. Evaluated operator metadata agrees with r7, and handler records identify the native code objects. Full vinsn bodies, attributes, opcode metadata and subprimitive offsets are retained for the subsequent lowering joins; their presence alone does not prove which lowerings a handler may emit.

The [proposed seed manifest](../../../tests/wasm/native-census/startup-closure/seeds.json) names image restoration, its four explicit pre-callback operations, startup/top-level dispatch, reader, source and binary loaders, compiler/rebuild and error entrypoints. It also requires every startup group, paired compile-time effect and emitted load effect. A return event witnesses execution; it is not a semantic prerequisite proof. Emitted load effects are not claimed executed. Neither the seed set nor the candidate bound has independent approval.

Two positive analysis cases and fourteen controls pass. The controls detect omitted resident/compiled code, hidden dynamic calls, unjustified bound or acceptance promotion, missing loader seeds, changed callback/handler identities, dropped source/native binding candidates, missing slots and collapsed SETF package identities. They check retained input witnesses separately from summary counts. The SETF collision case is an analysis mutation, not a native rebinding execution. This suite does not substitute for LL15-c's complete graph omission controls.

Remaining work is S0-LL08-a static reachability, qualification or widening of the candidate set, operator/lowering/import/trap/store joins, semantic initializer prerequisites, the complete exchange graph and its omission witnesses. The [dyld classification](../evidence/native-loader-contexts.json) separately resolves the four retained trace contexts and also awaits review. Existing project acceptances remain unchanged.

The finalized packet contains six files, approximately 6.8 MB. It references existing native and r7 artifacts instead of copying them. Verification covers the direct inputs and new output; no native rebuild or full evidence archive scan was run. [Reproduction instructions](../../../tests/wasm/native-census/startup-closure/README.md) identify the command and scope.
