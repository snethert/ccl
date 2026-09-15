# Finite-callee replay — 15 September 2026

Claude's fifty-sixth audit found a reproducibility defect in `6be15c29`: its
first pass ran before LABELS/LAMBDA-BIND support was added to the committed
resolver. The recorded 95-plus-22 split therefore did not describe a run of
that commit. The original commit remains DEFECT_FOUND; this separate correction
provides a fresh diagnostic result for re-review, not project acceptance.

The four existing passes have now run from a clean `e0c73b10` extraction. The
resolver/integration sources are identical to `6be15c29`. No resolver was added
or relaxed. The new [replay driver](../../../tests/wasm/native-census/finite-callees/README.md)
records stage inputs and sources and refuses source drift between recorded
stages. The first two passes were invoked directly before the driver was added;
their own runners captured sources before execution. Their invocation metadata
was collected at finalization and is labeled accordingly. Later stages retain
the driver's pre-execution records and exact driver version. All share the same
committed analysis tree.

| Pass | New proofs | Preserved | Remaining | Native probes | Rejected controls |
| --- | ---: | ---: | ---: | ---: | ---: |
| Finite expressions | 98 | 0 | 1,464 | 15 | 23 |
| Local argument/capture flow | 19 | 98 | 1,445 | 41 | 39 |
| Function-name lookup | 2 | 117 | 1,443 | 47 | 43 |
| CONSTANTLY return paths | 5 | 119 | 1,438 | 6 | 14 |

Probe populations overlap across passes; do not sum them as independent cases.
The constructor also performs twelve native factory checks. The finite and
lexical retained verifiers pass. A separate driver control refuses an earlier
stage's different source set before any analysis or native execution.

The constructor's provider is re-derived from retained bytes: its original
compiler event, exact symbol history, anchored read-only function 13422, and
matching emitted body in the correlated execution. Only that one provider is
requested. No unpublished 4,373-body completion result is used as a premise.
The first preparation attempt refused a descriptor without a name; its source,
trace and inputs are retained. The correction selects the exact named descriptor
while preserving the requirement for a unique constructor history.

All 1,562 original sites remain accounted for: 124 finite expressions and 1,438
unknowns. Symbol-cell contents, target lowerings and unknown caller environments
remain unqualified. The native graph has 369,734 nodes and 1,090,048 edges and
still fails complete census acceptance. The final constructor proofs, preserved
bounds, remaining sites and delta equal the old terminal data. Its graph differs
because the old graph also contained interleaved, unpublished body-analysis
layers; this replay isolates the callee chain on the reviewed builtin base.

`CENSUS-FINITE-CHAIN-R1` retains the fresh results, commands, input identities,
executed source snapshots, original development results and failures. The
original sources that were never captured remain explicitly unknown; neither
this packet nor the old body totals are retroactively attributed to a source
version. Fresh sources and outputs are the basis for the current claim.

No shared source, census checker, inventory criterion or accepted result changed.
The approved on-demand policy remains in force: this repairs an earlier claim;
it does not restart exhaustive bounding. The new deliverable awaits independent
review. LL15-b/c qualification publication remains separate and unfinished.
