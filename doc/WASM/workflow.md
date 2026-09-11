# Stage 0 workflow

The native census requires a qualified native build of the implementation revision. Architecture experiments may start independently. Historical Gate 0 at `4ca4df4` does not satisfy Gate 0 for v1.13. Both tracks must join before Stage 0 acceptance.

```mermaid
flowchart TD
    A[0A: Pin v1.13 baseline, evidence and inventories]
    A --> G[Gate 0: qualify native v1.13; capture R6 controls]
    G --> C[0B: evaluated compiler census and conservative closure]
    G --> T[External macOS cold-start file tracing]
    C --> J[Join operators, lowering, functions, modules and initialization]
    T --> J
    A --> P[0C: layout, logical frames, engine and ownership proofs]
    P --> I[0D: integrated GC, I/O interrupt, EH, C stack and Worker lifecycle]
    P --> B[0E: C/C4/B correctness, then baseline measurements]
    I --> B
    B --> H[H versus its own G: correctness, then measurements]
    J --> Q[0F: close census and ABI; validate complete evidence]
    H --> Q
    I --> Q
    Q --> S[Stage 0 accepted only when every required slice passes]
    S --> N[Stage 1: repeat selected contracts through generated code]
```

The initial harness is an implementation aid within 0C. It does not complete that subgate. Census distributions refine 0E's representative workloads but do not prevent earlier correctness experiments. Static unresolved edges remain visible even if no corresponding load appears in a trace. Source and target-state instrumentation is internal to the compiler; load-order observation uses an external macOS file-activity tracer, not `%fasload` hooks.
