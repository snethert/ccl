# Startup seed revision — 13 September 2026

Status: executed preparation; revision 2 approved by [Claude's twentieth audit](claude-review.md) at 2ef830cb for the stated native profile, with the save/restore and widening obligations still open. This responds to
[Claude's seed review](seed-review.md) with a revised proposal and actual kernel
entry identities. It does not close LL15-b/c or change project acceptance.

The [revision-2 manifest](../../../tests/wasm/native-census/startup-closure/seeds.json)
names the complete cold-start source chain, thread startup, both kernel callbacks
and the callback dispatcher. It requires the builtin vector and applicable
toplevel methods explicitly. Read-only inspection of the retained clean r7 image
supplies the following records in one identity namespace:

| Observation | Result |
| --- | --- |
| Named entrypoints | 22: 20 function cells and two callback entries |
| Builtin vector | All 23 ordered symbol slots and their function-cell targets |
| Callback vector | All 32 slots: three live and 29 empty |
| Applicable toplevel methods | Three bodies, with qualifiers and specializers |
| Distinct root code prototypes, including vector and method targets | 49 |
| Resident code prototypes, including the changed inspector | 15,425 |

`XCMAIN` and `%XERR-DISP` are not ordinary function bindings. The inspector obtains
their callable objects from the callback vector and checks that each named
symbol's value matches its slot's trampoline. The third live slot is
`%FOREIGN-THREAD-CONTROL`. Its exclusion concerns an independent root for the
selected workload; it remains in the captured vector and root target union.
Batch mode alone does not exclude foreign-created threads. A workload admitting
such entry must explicitly include that entry surface.

The method inspection returns the development-system primary, the application
primary, and the application's before method. Three methods are applicable,
although the development-system primary does not call the less-specific primary.
All three are retained conservatively. This distinguishes applicability from the
two bodies normally invoked by this method combination; it claims no execution
of the extra primary.

The cold-start proposal uses the review's explicit-source-chain option. It does
not infer the already-executed saved closure from the later toplevel value.
Likewise, the callback table is inspected **after restore**, not at image save.
Save/restore membership equality and bounds on later callback registration remain
explicit requirements. Snapshot targets are not a qualified bound on future calls.

## Reachability diagnosis

The diagnostic uses the reviewed wrapper graph and its original 13 seeds. It does
not splice new snapshot identities into that older namespace.

| Counterfactual graph | Reachable nodes | Seeds whose individual omission changes reachability |
| --- | --- | --- |
| Retained graph | 329,036 | 0 of 13 |
| Remove only clean-image and ASDF membership edges | 311,308 | 0 of 13 |
| Remove all 208 original membership edges | 234,440 | 4 of 13 |

Removing just the two largest widening edges would not make seed omissions
discriminating. Reaching a function reaches its source module, which then reaches
every member. Even the last counterfactual leaves other conservative paths and
observed workload dependencies. These are diagnostic counts, not a smaller
qualified closure or LL15-c control results.

**No graph edges or candidates have been deleted.** Replacement requires source
traversal and justified indirect-call targets. Source provenance must remain
available without becoming an unconditional execution dependency. Until those
replacements exist, a reduced graph would hide obligations. The 1,729 dynamic
calls remain unqualified.

## Verification and retention

The revised preparation passes 27 targeted controls, covering kernel entries,
callback/function-cell confusion, trampoline matches, vector slots and targets,
methods, root unions, exclusions and revision, alongside the original checks.
Two native inspections produce identical image, candidate, summary and control
files. No shared source was patched, no FASL or saved image was produced, and no
native rebuild was repeated.

The original manifest remains byte-identical in
[seeds-v1.json](../../../tests/wasm/native-census/startup-closure/seeds-v1.json).
The historical exchange assembler pins it explicitly. Its retained candidate
record and all 14 original controls pass the updated checker. Old closure results
do not qualify revision 2. The historical projection explicitly refuses revision-2
inputs until their vector and method dependencies have been integrated; it cannot
silently drop those new obligations.

One compressed packet, `NATIVE-STARTUP-SEEDS-R2`, retains outputs, controls,
diagnostic, identities and original failures. The first invocation could not
execute the archive's non-executable kernel; the next exposed a missing parenthesis
in the isolated inspector. Their commands, logs and exact source are retained.
The successful development run was superseded by added checker refusals and
direct source pins; its outputs equal the final run. No archive-wide verification
or gate rerun was performed.

Next: implement source traversal and call-bound replacements, integrate the
revised roots in their correct namespace, witness the save/restore callback
binding, and submit the revised seeds and graph for independent review. Stage 0
remains 28 accepted, 20 missing and zero unreviewed required records.


## Approval carried into the manifest — 13 September 2026

Claude committed the twentieth audit and seed approval as `219a4129`. The current
manifest now reads `REVIEWED_APPROVED` and cites that addendum. Its revision,
entrypoints, method selection, vector requirements and exclusions are unchanged.
The retained R2 packet still records the original proposal and executed input
hash; its external review supplies the approval. No native execution or new
evidence packet is claimed for this metadata update.

Claude reproduced candidates, summary, controls and the reachability diagnostic.
His image inventory differed in eight combined-method labels containing heap
addresses, which no join reads. The earlier byte-identical local reproductions
remain true for those runs; cross-session byte identity of the entire inventory
is not required or claimed.
