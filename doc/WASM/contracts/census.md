# Census and bootstrap closure contract v0.1

Status: schema and acceptance algorithm specified; the qualified native census is not yet executed. `census.schema.json` describes the exchange format. `tools/check-census.py` checks required shape, referential integrity, conservative reachability and initializer ordering; it does not prove that compiler instrumentation discovered every edge. That coverage requires S0-LL15-b/c and their omission mutants.

## Required records

- A baseline revision, profile, full instrumentation/input hashes and externally retained trace hash.
- Reviewed seeds naming the selected cold-start entrypoints, loader dependencies, compiler/read/error entrypoints and required compile/load-time effects. A seed-set revision change invalidates the old closure result.
- Nodes for every evaluated operator slot (including reserved slots), handler, vinsn, LAP/subprimitive, import, trap/store class, module, function and initializer relevant to the census. Every node has provenance, a profile disposition, implementation/replacement and acceptance-test IDs. Unsupported nodes include a reason and a test for the required condition.
- Edges with source/target identity, phase (`read`, `macroexpand`, `compile`, `load`, `run`, `callback`), observed-versus-conservative origin and complete candidate targets for indirect calls. Joins from operator/lowering records to functions/modules are explicit edges, not name-only matching.
- Initializers with prerequisites, a topological initialization rank and the completion assertion. Cycles in ordinary function dependencies are allowed. Initialization cycles require an explicit seed/phase split that produces an acyclic effect schedule; ignoring a cycle is not a disposition.

## Conservative fixed point

Start at all reviewed seeds and add every candidate target of each outgoing edge until the reachable set stops growing. Every possible target on an indirect edge is included, even if the observed run never selected it. For reflection, dynamic REQUIRE or computed names, either enumerate a sound bounded candidate set, widen to the containing supported module/package surface with justification, or leave the edge unresolved. An unresolved edge reachable from a required seed blocks closure acceptance.

Classify each reachable node as implemented, replaced or explicitly unsupported under the declared profile. A required initializer or executable bootstrap dependency cannot be discharged by `unsupported`. An unsupported operation may be reachable only as a declared error surface with an implemented condition path and test; that path is itself included in the graph. Do not mark a node optional because its implementation is scheduled in a later breadth stage.

Conservatively assumed edges retain the source evidence and reviewer rationale. The schema's `resolution` field records `complete` only when the candidate set is justified; it is not a synonym for observed. Nodes and references absent from the graph fail validation.

## External trace reconciliation

Record the exact macOS cold-start command, environment and external file-activity tracing command, and retain its raw output with a SHA-256 digest. Use a macOS tracer such as `fs_usage` or DTrace with adequate file-operation coverage and recorded permissions; a trace that cannot observe the process or loses events does not qualify. Trace availability is a census prerequisite, not a reason to change the reference platform. Filter and classify file operations with an identified parser revision. Compare native module/load order with the static projection, accounting explicitly for REQUIRE, conditional loads and trace-only files. Every observed module must map to a node reachable under the declared native scenario. Every static-but-unobserved required module remains included and receives a reason; absence from a trace never removes it.

S0-LL15-b accepts the joined instrumented graph, not source regex counts. S0-LL15-c deletes a required edge/node, conceals an unknown indirect edge, removes a loader seed and creates an invalid initializer prerequisite in separate mutants. The complete census/gate path must reject each. The tests retain independent expected dependencies so an incomplete producer and a permissive consumer cannot agree on the same omission.
