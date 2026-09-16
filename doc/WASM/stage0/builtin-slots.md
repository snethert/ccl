# Builtin slot obligations — 15 September 2026

Claude's fifty-fifth audit identified 1,500 builtin calls missing from the named
worklists. The [integrated command](../../../tests/wasm/native-census/builtin-slots/README.md)
now accounts for all of them. They are separate from the 1,562 open computed
calls: together they explain all 3,062 previously unresolved `build-flow/call`
edges. No additional unknown-call family is hidden in that population.

| Slot | Operation | Recorded calls | Native source route |
| --- | --- | ---: | --- |
| 4 | =-2 | 1 | .SPbuiltin-eq |
| 6 | >-2 | 1 | .SPbuiltin-gt |
| 8 | <-2 | 1 | .SPbuiltin-lt |
| 10 | EQL | 487 | .SPbuiltin-eql |
| 11 | LENGTH | 971 | .SPbuiltin-length |
| 12 | SEQUENCE-TYPE | 37 | .SPbuiltin-seqtype |
| 21 | %AREF1 | 1 | .SPbuiltin-aref1 |
| 22 | %ASET1 | 1 | .SPbuiltin-aset1 |

The operand numbers and displayed names come from the reviewed original-build
IR join. Its retained analysis samples carry the same execution's evaluated
23-slot table; the original collector checked that table across its snapshots.
The new reader checks agreement among those retained tables and the order in
U1's `xdump/xfasload.lisp`. It retains each original call, compiler event,
function identity, source context and graph evidence key. The name is descriptive;
it is never used to alias a function or symbol from another execution.

U1's x8664 architecture maps the range 0–22 to consecutive builtin subprimitive
entries. The source reader associates each slot with its declared entry and
the corresponding kernel source span. `x862-builtin-index-subprim` supplies
this route to `x862-builtin-call`. These are source interpretation witnesses,
not observed per-call emissions, binary addresses, exhaustive dependency sets
or Wasm implementations. Source spans end at the next `_spentry` label; they
do not describe assembled code sizes. The retained `jump_builtin` flag reports
the presence of that syntax only, not the absence of other dependencies.

The graph now separates the known operation from its unfinished implementation.
Exactly 1,500 site edges point to eight new required, unresolved operator nodes.
Those nodes each have an unresolved edge retaining the previous name-level
placeholder. A complete site-to-slot edge establishes the operand's identity
only; the reachable slot and its lowering edge remain unqualified. All old
nodes, every other edge, seeds, widening, initializers and trace records remain
unchanged. No function-cell value or method population is inferred from this
table, and no name-only edge is promoted to a callable bound.

The resulting graph has 369,718 nodes and 1,090,032 edges. The unchanged census
checker reports 29,714 unresolved edges and 34,021 unimplemented nodes, with no
structural error. The decrease of 1,492 unresolved edges is **consolidation of
repeated obligations**, not newly qualified execution or lowering. All 1,500
sites still require the eight implementations. The distinct 1,562 computed
calls, 5,693 unbounded symbol cells, 95 unwitnessed runtime values and 5,007
original body obligations remain open. The command returns **BLOCKED, exit 2**
and claims no LL15-b/c credit.

Each slot has explicit target work. LENGTH needs D1 list/vector layouts,
traversal safepoints and condition paths. EQL needs target-aware boxed-number
behavior and root handling, including the host-layout pitfalls already exposed
by the helper probes. Numeric comparisons retain boxed and fallback paths.
Sequence and array operations need representation and bounds work; %ASET1 also
needs store/GC classification before any write barrier is removed. These are
unimplemented obligations, not accepted replacement contracts.

The integration controls corrupt genuine call operands, event identities,
slot tables, target declarations and graph records. The checker independently
derives the permitted old-edge edits from the retained call operands and checks
full node and edge records, multiplicity and metadata. Inserting a node or
widening edge, hiding a binding gap, removing a site or initializer, and claiming
native source as target implementation must all fail. These checks do not
replace LL15-c's independent instrumentation omissions.

The original closure and definition packets are unchanged. The new worklists
preserve their existing populations and add the builtin family. Verification
uses direct retained inputs and a fresh reconstruction; no native execution,
historical payload scan or acceptance-envelope regeneration is needed. The
first development run's source-span reader assumed every native entry had an
`_endsubp` marker. U1's unused builtin division entry lacks one. That failed run,
log and exact new sources are retained; the reader now uses the next entry label.

Claude's fifty-sixth audit independently reproduced the builtin outputs and
graph from `6be15c29`, with all 32 controls rejecting. This separate publication
retains the original packet unchanged, restores the executed sources from that
commit at their recorded hashes, and supplies its README, status and index.
It claims no new execution. The original commit's other packaging and finite-chain
reproducibility findings are separate and are not cleared by this publication.

The acceptance ledger remains forty accepted, eight missing and zero unreviewed.
Under the approved on-demand policy, these eight lowerings remain named work
for concrete implementation questions; do not resume exhaustive native bounds
as a Stage 0 prerequisite. The dated original report's next-work text retains
its historical plan and is superseded by that policy.
