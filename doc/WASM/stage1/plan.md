# Stage 1 work plan — draft of 15 September 2026

Status: DRAFT proposed by Claude under the 15 September role switch and
refreshed after Codex's review. Nothing here is adopted. The [draft inventory](inventory.draft.json) is not the
criterion of any ledger; adopting it is a user decision recorded the way a
Stage 0 criterion change is recorded, and the functional shared-compiler
author still needs the user's authorization. Stage 0 acceptance is the entry
condition: every required Stage 0 variant accepted, which today means the
census's LL15-b and LL15-c plus the six executions awaiting Codex's review.

## What Stage 1 delivers

The outline's Stage 1 exit: coordinated cross-loaded heap and code
artifacts executing through the real Wasm pass 2, vinsns, primitives and
runtime; finalized object, allocation, root and TCR contracts; the selected
B ABI confirmed through generated code; a one-Worker image loader; the
read-only file namespace; a precise single-thread collector; measured and
chosen bootstrap module granularity; and D2's materialization confirmed on
the production path. The draft inventory has 31 tests, one variant each,
derived from the register's Stage 1 metadata, D7's scheme and the outline's
exit criteria, plus two entries proposed from Stage 0 findings.

## Subgates and order

1. **1A: R6-safe shared-compiler edit.** Backend registration, the wasm32
   arch file generated from [the layout schema](../contracts/wasm32-layout.v1.md),
   module lists, systems registrations and the cross-fasloader derived
   from the x8632 precedent, under D6's edit-site plan. S1-LL08-a proves
   R6 and R6a for every existing target after the edit; S1-LL22-b binds
   the build; S1-LL23-a makes generated diagnostics structured from the
   first emitted function. Nothing else starts before S1-LL08-a passes.
2. **1B: representation and B through generated code.** S1-LL04-a and
   S1-LL07-a repeat the Stage 0 layout and conversion fixtures through
   generated access and mutation code; S1-LL05-a and S1-LL05-b repeat the
   B corpus, stubs, adapters and tail chains; S1-LL10-a fixes constant
   pools. The [engine matrix](../stage0/engine-matrix.md) pins the
   features the emitter may use.
3. **1C: control, bindings, temporaries, closures, code identity and
   numerics.** S1-LL19-a extends the nested-exit fixture to generated
   frames and the condition path; S1-LL17-a the binding subset against
   [the TCR schema](../contracts/tcr.v1.md); S1-LL06-a temporaries under
   legal collection; S1-LL12-a closures and callable metadata; S1-LL11-a
   aliases and redefinition; S1-LL11-b the empty-registry condition that
   corrects the U1 stale-dcode defect; S1-LL16-a the numeric subset under
   the approved floating-point policy over
   [the detection rules](../contracts/floating-point.v1.md).
4. **1D: collector.** S1-LL18-a proves the precise single-thread collector
   on a small heap with complete root coverage; S1-LL18-b proves EQ hash
   tables under real movement, the plan's item 3.
5. **1E: materialization, cross-dump, loader, namespace and
   initialization.** S1-LL21-a confirms D2 on the production emitter
   against the engine pins; S1-LL21-b measures and chooses module
   granularity; S1-LL09-a, S1-LL13-a and S1-LL15-a cover symbols, generated
   installation and the census closure's initializers under the
   [initializer-binding](../stage0/initializer-binding.md) discipline;
   S1-LL14-a loads the coordinated heap and code set into a fresh instance;
   S1-NAMESPACE-a supplies the read-only namespace; S1-LOADER-a boots to
   ready.
6. **1F: gates, controls and contracts.** S1-LL01-a, S1-LL02-a, S1-LL03-a,
   S1-LL22-a and S1-LL24-a repeat the Stage 0 rejection tests through the
   real build path; S1-CONTRACTS-a finalizes the contracts against the
   generated fixtures that executed them.

## Stage 0 outputs each subgate consumes

| Stage 0 output | Consumed by |
| --- | --- |
| [Engine matrix](../stage0/engine-matrix.md) feature and JSPI pins | 1B emitter, 1E materialization; a pin change reruns dependents |
| [Layout schema and ledger](../contracts/wasm32-layout.v1.md) | 1A arch file, 1B probes, 1F contracts |
| [TCR schema](../contracts/tcr.v1.md) | 1A runtime record, 1C bindings, 1D roots |
| [Runtime-contract join](../contracts/runtime-contracts.v1.json) and the frame contract | 1C frames and EH, 1F contracts |
| [Materialization](../stage0/materialization.md) and the D2 materializer | 1E production path |
| [Nested exits](../stage0/nested-eh.md) and the boundary fixture | 1C generated EH |
| [Initializer binding](../stage0/initializer-binding.md) | 1E closure initializers and loader |
| [Kernel-import census](../contracts/kernel-imports.v1.md) | 1A runtime import inventory, 1E namespace and host services |
| [Floating-point detection and policy](../contracts/floating-point.v1.md), specified and executed over its corpus with native x86 agreement; policy decided 16 September (the ARM model) | 1C numerics; policy selected, implementation and cost measurement owed |
| Retained startup worklist and on-demand census queries (LL15-b/c under the v0.2 contract) with seeds, ranks, trap and store dispositions; unknown callees kept separate from proven bounds | 1E closure, bundle composition and module granularity; implementation questions answered by focused native scenarios, not by an exhaustive closure |
| Stale-dcode finding | 1C S1-LL11-b |

## Decisions the user owns before Stage 1 starts

- Who authors the functional shared-compiler changes; the standing rule
  requires an authorized author and a different-model reviewer.
- Adoption of this inventory, including the two proposed entries.
- (Decided 16 September: the floating-point condition policy is the ARM
  model, recorded in [the specification](../contracts/floating-point.v1.md);
  Stage 1 owes the cost measurement of the emitted checks.)
- Whether the single-thread JSPI profile is admitted for Stage 1 at all:
  Node, Chrome and Firefox 156 have JSPI on the reference Mac, Safari 26.3
  does not.

## Rules carried forward

Small commits with one deliverable each; every packet reproduced by its
verifier; adversarial review from a different model before acceptance;
R6 and R7 unweakened; hand-built Stage 0 evidence never discharging a
Stage 1 ID; no comparative timing beyond the benchmark policy.
