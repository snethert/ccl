# Sequential-build binding versions — 14 September 2026

Status: executed diagnostic; reviewed by Claude's forty-ninth audit at `91c27067` without defect. This joins the
global-call symbols from the reviewed [build IR packet](build-flow.md) to
their actual recorded function-cell values. It grants no census gate credit.
No native session or shared-source change was needed.

The original rich stream already contains both binding inventories and the
store hooks. Earlier joiners consumed installation events but did not use the
complete inventory/removal history. The new
[derivative](../../../tests/wasm/native-census/binding-versions/README.md)
reads those retained bytes in the same `identity:build` namespace.

| Retained build fact | Count |
| --- | ---: |
| Binding inventory entries before / after the build | 10,124 / 11,386 |
| Installations observed after the store | 6,620 |
| Removal intents, with the old value observed before the store | 8,197 |
| Binding identities, including literal NIL | 11,483 |
| Global call sites joined to exact symbol identities | 98,213 |
| Distinct symbols used by those calls | 5,693 |
| Called symbols with observed values | 5,598 |
| Called symbols with no value witness | 95 |
| Called symbols with multiple ordinary prototype identities | 2,060 |

Symbol IDs select histories; names and source annotations are descriptive.
SETF symbols retain their own identities. NIL has no numeric symbol ID in the
observer's encoding; its 27 removal events remain a distinct literal history.
All values are classified: 28,754 ordinary-function observations, 4,669 macro
wrappers, 62 special-operator wrappers and 2,842 already-unbound observations.
Only ordinary-function values enter the runtime-call prototype lists.

Earlier versions are retained even when a later installation replaces them.
Multiple prototype IDs can also arise from reloading the same source; this is
an identity count, not a claim that every such replacement changed behavior.
The source-body joins use materialization events or exact native FASL reader
and writer identities, including the latest preceding write generation.
Cross-dump image words cannot become native callable IDs. These joins identify
2,676 observed prototypes with already attached compiler bodies; 5,007 observed
prototypes still need body witnesses. The latter include resident-before code,
not merely newly missing definitions.

## What remains unresolved

The 95 called symbols without a value witness account for 345 call sites:
81 are in MAKE, ten in CCL, one in UIOP/STREAM and three are uninterned SETF
names. Examples include other-architecture LAP helpers and stream accessors.
This is a concrete source/disposition worklist, not evidence that those calls
executed or an authorization to drop their dependencies. The history records
contain every exact descriptor and call count needed to work through it.

A removal hook records intent before the store. It does not prove completion.
An absent inventory entry is also not proof of an unbound cell, because the
enumeration depends on package and SETF-registry membership. The comparator
finds no mismatches between the confirmed values it can compare; that does
not establish coverage during unobserved intervals or future execution.
Every binding's exhaustive candidate bound and target/profile disposition
therefore remain open. Prototype identity also does not bound a closure's
environment or a generic function's internal dispatch state.

## Graph effect and verification

Each global call still has its own edge, now to the exact symbol cell rather
than a name placeholder. That reference edge is complete because its symbol
is known. Each symbol cell then has **one unresolved callable-value edge**,
holding its observed ordinary prototypes. Thus the graph cannot interpret
the known designator as a complete runtime target bound.

The patch retires 5,692 name placeholders whose last incoming edge was replaced.
Builtin calls retain their existing placeholders: their snapshots have indices
and names, not the exact symbol descriptors used by this join. All computed
calls, widening families, seed records, initializers, module dispositions and
trace mappings remain unchanged. The 259 previously unattached assembly bodies
are not traversed or silently attached.

The graph has 369,580 nodes and 1,089,337 edges. Structural checks pass; the
census still refuses closure. Unresolved reachable-edge reports fall from
118,604 to 31,091 by consolidating repeated global-binding obligations. There
are still 34,004 unimplemented reachable nodes. These graph diagnostics are
**not Stage 0 slots**, and this reduction earns no gate credit.

Twenty-two controls reject omitted versions and calls, duplicate/surplus
records, wrong symbol/process identities, macro expanders offered as runtime
targets, a changed FASL write generation, fabricated completeness, erased
obligations and unrelated node removal. Three positive probes check unknown
wrapper refusal, distinct identities with equal names, and detection of an
unobserved change. The standalone verifier replays the original stream and
requires byte identity for all five analysis outputs. The packet retains the
three original development failures and their executed sources.

Next, resolve the 95 binding worklist entries and obtain the missing native
body witnesses, then use the call graph for parameter-flow and registry bounds.
The rich build's 1,562 computed calls remain open; the independent file survey
and r7 retain their separate populations. Target environment qualification,
startup replacements, the reviewed seed integration, lowering/import/store
dispositions and genuine omission controls remain required for LL15-b/c.
The ledger stays **39 accepted, eight missing and one unreviewed of 48**.
