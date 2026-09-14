# Sequential-build IR and call/code joins — 14 September 2026

Status: executed and checked; reviewed by Claude's forty-eighth audit at `5c1ca7b0` without defect. This advances the
census graph and grants no gate credit. LL15-b/c remain incomplete.

The original rich build stream already retained complete flat compiler IR in
each `frontend` and `before-pass2` event. The earlier identity joiner used the
function summaries but did not consume that IR. The new
[derivative](../../../tests/wasm/native-census/build-flow/README.md) reads those
existing bytes, checks the IR against the summaries, bounds immutable local
callbacks and connects compiler functions to the emitted identities recorded
by that same build. No native rebuild or source instrumentation was needed.

| Sequential rich build observation | Count |
| --- | ---: |
| Retained events processed | 4,006,405 |
| Pre-pass-2 family captures | 46,117 |
| Functions, including nested functions and assembly bypasses | 51,601 |
| Functions joined to actual materialized code identities | 51,601 |
| Call sites | 103,393 |
| Computed call sites | 1,762 |
| Newly bounded immutable lexical calls | 200 |
| Computed calls still open | 1,562 |
| Global calls with exact retained symbol descriptors | 98,213 |
| Functions that bypass Lisp pass 2 | 259 |

These are the rich build's identities and counts. The earlier r7 capture still
has its own 1,729 computed sites; the independent source-wide sessions still
have 1,723. Neither population is relabeled or joined by matching printed names.

## What the graph gains

All 51,342 Lisp bodies attach to the existing effect/lowering graph through
recorded compiler/code identities in `identity:build`. Every call is retained.
Direct lexical/self calls and the 200 new local bounds have precise targets.
Named global and builtin calls retain unresolved callable-value obligations:
knowing a symbol or builtin slot is not a bound on its changing contents.
The full symbol descriptors are saved for the next binding-history join.

The adapter checks raw graph reachability, complete expression records, family
and parent identities, operator histograms, call-site order, direct callee
identities and builtin indices/entries. Compiler/code joins use materialization
events after the corresponding IR snapshot. Diagnostic names never select a
callee or join two process namespaces.

The older observer did not record assignment flags. The adapter supplies no
positive assignment hint to the reviewed bounder; actual eligibility still
requires a unique local binding, correct ownership, a use dominated by that
binding, and no write or unclassified variable use anywhere in the family.
Eight reviewed callback captures are converted to this older format without
assignment bits. Four remain bounded and four refuse, including local and
captured writes, an unknown parameter and a use outside binding scope.

U1 `compile-named-function` skips Lisp pass 2 when pass 1 has already supplied
the LFUN. The 259 such functions have retained front-end and code identities,
including the native bignum LAP routines. Their assembly is not traversed.
They remain explicitly unattached in the worklist; this is not a dead-code or
optional-feature classification. The later independent source survey's 257
unjoined output functions is a different population and is unchanged.

The additive fragment preserves every earlier graph record, seed, initializer,
disposition and trace mapping. It adds no module-membership widening. Attachment
follows existing paths and the witnessed code/compiler links; the checker bounds
full new node records, edge multiplicities and the unattached-function list.
The resulting graph has 362,505 nodes and 1,075,961 edges. Structural checks
pass; closure remains blocked. Its unresolved-edge diagnostics increase because
individual global call sites now carry explicit callable-value gaps. Those
diagnostics are **not additional Stage 0 slots**.

## Verification and remaining work

The producer checks the whole stream and graph, replays eight retained callback
probes, and rejects 22 altered IR/fragment inputs. Controls cover missing,
duplicate and surplus records, shallow IR, altered operators, wrong direct and
builtin targets, cross-process edges, fabricated global bounds, erased assembly
gaps, changed node descriptions, wrong materialization edges and false gate
credit. The standalone verifier recomputes all six deterministic outputs from
the original stream and requires byte identity. Native captures and the earlier
graph are reused; no accepted envelope or historical artifact tree is rehashed.

`NATIVE-BUILD-FLOW-R1` retains one compact packet with the derived facts, graph
fragment, checks, selected callback capture, exact input/source identities and
original development failures. One failure exposed the pass-2 bypass; the
other exposed the mistaken assumption that every observed function was already
attached to a seed. Neither failure was converted into a success record.

The subsequent [binding-version derivative](binding-versions.md) joins global
symbols to their recorded versions and consolidates the repeated per-site
obligations. It preserves the distinction between observed values and complete
candidate bounds; this packet's original graph and facts remain unchanged.
Next work through the remaining binding/body witnesses, then the 879
unbounded variable calls and 683 other computed callees, connect the assembly
worklist and boot/image generations, and qualify the target environment and
required replacements. The reviewed seed revision, complete lowering/import/
store dispositions, trace reconciliation and genuine LL15 omission mutants
still belong to the final closure. Stage 0 remains **39 accepted, eight missing
and one unreviewed of 48**; LL13-b awaits user acceptance.
