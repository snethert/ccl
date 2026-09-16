# Stage 1 work plan — adopted 16 September 2026

Status: ADOPTED. The [inventory](inventory.json) of 31 tests is the
criterion of the [Stage 1 ledger](../evidence/current-stage1-gate-result.json)
by the user's decision of 16 September; Codex is the authorized author of
the shared-compiler changes with Claude as reviewer; the single-thread JSPI
profile is deferred. The entry condition is met: all 48 Stage 0 variants are
accepted. The [1A packet](1a.md) has three accepted records after Claude’s review and the user’s
[acceptance](acceptance-1a.json); the ledger now has five accepted records, 26 missing and
zero unreviewed records. [LL04 generated representation](representation.md)
is reviewed and accepted. The [reviewed unit](integration-1a.json) is integrated;
[LL07’s generated typed conversions](conversions.md) are reviewed, accepted and [integrated](integration-ll07.json).
The [generated B call core](b-call-core.md) now executes required-argument
direct/indirect calls and full values and is accepted and integrated.
The accepted and integrated [optional/keyword binding unit](b-bindings.md)
adds defaults, supplied-p values and keyword validation. The
accepted and integrated [rest/APPLY unit](b-rest-apply.md) supplies real cons allocation and
runtime-sized arguments, removing the 64-argument ceiling. The isolated
[runtime result-capacity proposal](b-results.md) removes the fixed 64-value
ceiling and awaits review. Next: callable objects and symbol function cells,
then the condition path, lazy adapters and tail transfers. Neither complete LL05 slot is claimed by these units.

## What Stage 1 delivers

The outline's Stage 1 exit: coordinated cross-loaded heap and code
artifacts executing through the real Wasm pass 2, vinsns, primitives and
runtime; finalized object, allocation, root and TCR contracts; the selected
B ABI confirmed through generated code; a one-Worker image loader; the
read-only file namespace; a precise single-thread collector; measured and
chosen bootstrap module granularity; and D2's materialization confirmed on
the production path. The adopted inventory has 31 tests, one variant each,
derived from the register's Stage 1 metadata, D7's scheme and the outline's
exit criteria, plus two entries proposed from Stage 0 findings.

## Subgates and order

1. **1A: R6-safe shared-compiler edit.** Backend registration, the wasm32
   arch file generated from [the layout schema](../contracts/wasm32-layout.v1.md),
   module lists, systems registrations and the cross-fasloader registration: x8632 supplies tags/NIL,
   ARM supplies the separate-code precedent, under D6's edit-site plan. S1-LL08-a proves
   R6 and R6a for every existing target after the edit; S1-LL22-b binds
   the build; S1-LL23-a makes generated diagnostics structured from the
   first emitted function. Nothing else starts before S1-LL08-a passes.
2. **1B: representation and B through generated code.** S1-LL04-a and
   S1-LL07-a repeat the Stage 0 layout and conversion fixtures through
   generated access and mutation code; S1-LL05-a and S1-LL05-b repeat the
   B corpus, stubs, adapters and tail chains, binding the accepted B decision
   directly in the generated build; S1-LL10-a fixes constant
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

## Entry decisions, all made on 16 September

- Author: Codex, for the functional shared-compiler changes as well as the
  fixtures, under the amended standing rule; Claude reviews.
- Inventory: adopted as drafted, the two proposed entries included.
- Floating-point condition policy: the ARM model, recorded in
  [the specification](../contracts/floating-point.v1.md); Stage 1 owes the
  cost measurement of the emitted checks.
- Profile: the single-thread JSPI profile is deferred to the profiles stage.
  Stage 1 runs on the full profile with one Worker.

## Obligations carried from Stage 0 by name

The [Stage 0 exit-criteria review](../stage0/exit-criteria-review.md)
carries four census enumerations into this stage under census contract
v0.2: the kernel-import join (65 imports, dispositions decided), the trap
class join (vocabulary decided, 143 native sites inventoried), the direct
foreign-call inventory (eight startup surfaces named) and the classification
of barrier-sensitive stores. Imports and foreign calls fall due in 1A and
1E, traps in 1C, and store classification before the Stage 2 multi-Worker
collector; the single-thread collector of 1D needs no barrier.

The [ARM lessons](arm-lessons.md) add six more by name: the kernel
globals block (1A), thread-local binding growth and the interrupt-level
binding (1C), stack overflow as a condition (1C), the continuable trap
classes for the lowering inventory (1C), and callback slot installation
(Stage 2). The same document revises one precedent: derive the
cross-fasloader's function handling from `xarmfasload.lisp`, not only from
x8632.

The [runtime obligations](runtime-obligations.md) carry the ARM survey into
1A ownership and addressing, binding-vector growth, interrupt masking,
recoverable stack exhaustion, trap lowering and Stage 2 callback installation.
They are implementation work, not additional claims about accepted Stage 0 evidence.

## Rules carried forward

Small commits with one deliverable each; every packet reproduced by its
verifier; adversarial review from a different model before acceptance;
R6 and R7 unweakened; hand-built Stage 0 evidence never discharging a
Stage 1 ID; no comparative timing beyond the benchmark policy.
