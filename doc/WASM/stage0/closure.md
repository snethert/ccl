# Integrated development closure — 15 September 2026

The [development command](../../../tests/wasm/native-census/closure/README.md)
turns the reviewed fragments into one working exchange graph and one set of
identity-bearing worklists. Its expected outcome is **BLOCKED, exit 2**. It is
not an executed S0-LL15-b/c result, and it changes no acceptance criterion or
inventory entry. The ledger remains 40 accepted, eight missing, zero unreviewed.

The reconstruction applies the reviewed emission, boot, wrapper, retained-build
IR, binding-version and resident-literal fragments through their original
materializers. It reproduces the historical boot and wrapper graph identities.
The resulting base has 369,586 nodes and 1,089,809 edges. Every old node, edge,
initializer and trace record remains unchanged.

Seed revision 2 is explicit. The accepted source specification is joined to its
own retained inspection: 22 named entries, the callback and builtin vectors,
three applicable toplevel methods, a union of 49 required prototypes, and the
four startup groups. The historical candidate packet keeps its original
proposed-disposition metadata; this run binds the separately accepted source
manifest and review. It does not rewrite that packet.

The inspection's object numbers are a separate `seed-v2:` namespace. The new
edges follow actual observed function literals from the required roots. Each
visited function has an unresolved body dependency. Five explicit obligations
cover execution correspondence, vector lifetime, compile/load effects, target
qualification and widening replacement. The earlier 13 roots remain separate
conservative development roots so their outstanding work cannot disappear.
This does not prove that revision 2 reaches the old graph, nor that the old
membership edges discriminate seed omissions.

The working graph has 369,706 nodes and 1,089,937 edges, all reachable under
these conservative roots. Relative to the reviewed base it adds 120 nodes and
128 edges: 109 snapshot bodies retain unresolved edges and five scope nodes
remain unimplemented. The checker reports 31,206 unresolved reachable edges
and 34,009 unimplemented reachable nodes. **Zero original obligations close.**
The larger diagnostic counts expose seed qualification work; they are not a
new count of missing Stage 0 slots.

The worklists preserve the populations that matter for closure:

| Original rich-build population | Remaining obligation |
| --- | --- |
| 5,693 called symbol cells | All lack exhaustive value bounds; 95 also lack any observed value, covering 345 call sites. |
| 5,007 original body gaps | 4,373 have resident payload witnesses, including 4,130 reported source ranges; 634 have origin classifications. Payloads remain distinct from dependency closure. |
| 1,762 computed sites | 200 immutable local bounds; 1,562 open, split into 879 variable calls and 683 computed callees. |
| 259 front-end-only functions | Native assembly bypasses remain unattached. |

The source-wide survey's target failures and the newer registry/compiler
witness remain qualification inputs with explicit limitations. No new-session
registry method or matching source name is credited to an original-build call.
Large fan-outs and evidence names containing `member` are diagnostic worklists,
not a finding that every such edge is invalid. Justified conservative bounds
remain permitted by the contract.

The existing census checker verifies structure and enumerates reachable gaps.
The integration checker independently preserves the full old graph and exact
new records, roots and metadata. Its mutations exercise omissions, inserted
cross-run edges, fabricated implementation, concealed unknown calls, changed
initializer/trace records, incorrect roots and damaged vector witnesses.
All 20 integration mutations reject at their specified check. These tests
exercise assembly consistency. They do not establish complete
instrumentation or replace LL15-c's independent omission qualification.

The retained packet is `CENSUS-DEVELOPMENT-CLOSURE-R1`, in the evidence store's
`2026-09-15-closure-r1` directory. It binds 20 direct inputs and 21 executed
source files. It retains the reports, controls, composition recipe and original
development failures; the 16,025,655-byte working graph is reproducible and not
duplicated there. The first attempt used different gzip flush behavior from
the historical writer. The second reconstructed the graph but imported a
different fixture's `controls` module after the legacy path setup. Both failed
records, tracebacks, logs and exact new-source snapshots are retained. The
corrected module has a distinct name, and the replay uses the original writer's
flush behavior. Analysis files produced before the second failure are identical
to the final retained files, with that sharing recorded explicitly.

A fresh replay reproduces all six analysis/control outputs and the optional
working graph byte for byte, again exiting 2. The final packet has 16 files
totaling 1,134,023 bytes. No historical payload scan, native execution or accepted
envelope regeneration was needed. Independent review remains pending.

The next work is to apply binding/body and call-family proofs to this graph.
The user explicitly permits another native build when it makes completion
faster. Prefer a combined compiler/body/registry capture when it removes costly
identity gaps; preserve its execution namespace, reversible observation and R6.
This replay itself needs no new native execution. Browser exclusions, including
Swink and its native clients, remain in force.
