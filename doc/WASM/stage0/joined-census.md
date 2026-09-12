# Joined census projection — 12 September 2026

The retained inputs now have an executable projection into `contracts/census.schema.json`. It passes the schema and independent retained-input coverage checks. **It is not a qualified LL15-b/c census.** The unchanged census checker rejects its explicitly unresolved joins. Stage 0 remains at **28 accepted, 21 missing, zero unreviewed**; no new acceptance envelope or combined gate was produced.

The distinction matters: acceptance of LL08-a established registration and target state for fourteen front-end forms. It did not establish full source coverage. The existing logs also lack complete initializer state dependencies and execution of the emitted load effects. Assembly cannot supply observations that were never captured.

See the [summary and retained packet](../evidence/joined-census-summary.json) and [runner](../../../tests/wasm/native-census/startup-closure/README.md). The packet is compressed JSON in the existing exchange schema, with a separate witness file. It references the committed r7 graph/events, clean-image snapshot, proposed seeds, trace and accepted stub session. The assembly runner changes no Lisp source and starts no native build. No instrumentation is carried into an implementation image.

| Join | What the packet establishes | What remains unproved |
| --- | --- | --- |
| Functions and calls | Distinct native, r7 compiler and stub identity namespaces; every retained call/reference, old source candidate, function-to-module edge and operator use preserved. | A closed bound on generated, loaded or rebound callees. All 1,729 dynamic calls remain unresolved; an enumerated candidate set is not a complete installation history. |
| Operator and lowering metadata | All 279 evaluated slots; 247 dispatch entries joined by actual native code identity; 599 evaluated templates decoded into 222 opcode identities and 17 UUO names. | Handler-specific emission, concrete subprimitive cycles, imports/direct foreign targets, pointer-store classes and Wasm dispositions. The whole template table remains an explicitly unqualified candidate set for each handler. |
| Compile effects | All 18,907 entry/return pairs, source locations and the function identities compiled within their dynamic extent. | Semantic state prerequisites and the complete dependencies of the executed effect. Compilation within the interval is not an exact callee identity. |
| Load effects | All 9,362 emitted effects, their source modules and conservative body candidates. | Loader execution, installed body identity, prerequisite state and completion. No emitted effect is marked completed. |
| Startup | All 35 callback code identities and paired normal returns; source-required ordering after the four explicit pre-callback calls. Reaching the first callback implies those preceding calls returned normally; their completion records label that source-based inference. | The complete prerequisite-state contract. The callback schedule preserves U1 control flow; it does not claim a minimal data-dependency order. |
| Trace | The reviewed parser reproduces successful image/control opens and the four dyld classifications. Only the actual r5 traced image is marked observed. | The r7 inspected image remains a separate node. Its heap identity is not inferred from the r5 trace or their common source revision. |

`implemented` on a native observation node identifies its existing native code or evaluated metadata. It does **not** mean a Wasm implementation exists. The graph's profile states this limitation and includes unresolved Wasm-disposition nodes. No native slot is silently dropped, and no required dependency is made optional. A native vinsn `:SET` attribute describes register dataflow; this producer does not misclassify it as proof of a pointer store.

The 183 names without a named body candidate remain an explicit worklist. Their recorded definition locations give leads into generated ASDF bindings, accessor definitions and cross-dumper helpers. A source declaration is not proof that a function was installed. In particular, an unresolved conditional or generic binding is not converted into an unsupported operation merely to close the graph.

Thirty-seven compile-effect previews differ between entry and return; the retained examples include relocated lexical-environment addresses. Pairing therefore follows the observer's nested calls and source locations, with both previews preserved. No printed form is read back as executable Lisp. The small decoder accepts only the grammar of the fully printed evaluated opcode alists, including shared tails; it rejects reader evaluation, unreadable objects, truncation and malformed labels.

## Verification and its limit

The producer and coverage checker read different witnesses: the checker obtains required effect entries/returns directly from the original event streams and required calls, code identities, dispatch entries and candidates from their pinned inputs. It checks the startup predecessor chain against U1's explicit call and callback traversal order. The generic census checker then checks graph invariants and rejects unresolved dependencies.

All 23 omission controls reject. They remove a required node or edge, conceal an unknown call, narrow the candidate surface, remove a loader seed (including from the proposal), create a startup initializer cycle, omit a load effect, substitute a callback/handler/opcode, collapse a source version, hide an effect-body witness, substitute a return, omit a stub call or module join, promote unproved coverage and conflate the traced and inspected images. Each must cause its **own specific coverage failure**. The baseline projection passes coverage before and after the mutations. The opcode decoder also passes two positive cases and rejects five malformed/unsafe inputs.

These controls prepare the omission oracle. They do not satisfy LL15-c: that requires the complete instrumentation and gate path to accept the genuine census and reject its mutants. Here the genuine census is intentionally blocked. The summary groups those failures by mechanism rather than presenting thousands of repeated diagnostics as independent project tasks.

## Next observation work

Extend the reversible observation to capture identities through read/macroexpand, initializer execution and function installation, including generated generic/accessor bindings. Record semantic prerequisite state and completion at the loader boundary, not only compiler emission. Use the registered target to cover the selected source closure, and join lowering/import/store operands to their evaluated targets. Review the seed set and conservative bounds against those observations before producing LL15-b/c execution records.

This is observation work under the existing exception. Any shared hook change must still be a removable unit in a disposable U1 copy and carry its required native R6 comparison. Functional B emission remains a separate authorization; the implementation baseline remains pristine U1.
