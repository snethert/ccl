# Claude review of the execution benchmark baseline — 28 September 2026

Supplied by the user. Prose retained as supplied; the table header and layout
are repaired for Markdown. No reviewer was invoked by Codex.

---

The benchmark set is sound, its numbers reproduce from the raw samples, and it settles two questions I had left open. No defect. Accept it as the baseline record. It is still uncommitted: four modified files and the new directory.

**What I verified.** All 198 files in the evidence pack match their inventory hashes. The recorded source hashes match the working tree for every file except the code-shape inspector, which Codex changed after measurement, disclosed with both hashes, and showed produces an identical report. The three process medians per row are tight: the scalar-call row spans 98.76 to 99.12 ns. The target timer is microseconds and every sample runs at least 50 ms, so resolution is not a factor. The native disassembly shows a real call in the call loop and a real `addsd` in the typed double loop, so the native side is not cheating by inlining. The typed and untyped CAR, SVREF and double-add bodies are byte-identical in the emitted WAT, as claimed. Six corruption controls and five observer checks pass, 36 forced moving collections preserved their references, and the three ordinary READY runs are unchanged at a 26.16 s median with 7 modules and 11 instances. The harness hooks in the launcher are all behind the benchmark flag.

**What the numbers settle.**

| Loop | Native | Wasm default | Ratio | Wasm TurboFan-only | Wasm Liftoff-only |
| --- | ---: | ---: | ---: | ---: | ---: |
| inline fixnum add | 2.27 ns | 39.75 ns | 17.5× | 44.23 ns | 77.65 ns |
| scalar call | 2.51 ns | 99.00 ns | 39.4× | 113.74 ns | 255.68 ns |
| svref | 3.01 ns | 82.55 ns | 27.4× | 92.87 ns | 162.94 ns |
| typed double add | 2.54 ns | 1,725.56 ns | 680× | 1,735.41 ns | 1,858.89 ns |

- **It is not the engine tier.** Default V8 already reaches optimized code and beats forced TurboFan on calls, because adaptive tiering gets type feedback that lets it inline indirect calls. Forcing everything through the optimizer leaves the ratios at 17 to 40 times. The gap is in the emitted code.
- **It is not only the call protocol.** A loop of inline fixnum additions with no calls at all is 17.5 times slower than native. The incremental cost of adding one call is 59 ns, about 60 percent of the call row. The other 40 ns is what the body itself costs per iteration. So the per-operation protocol inside bodies, the root stores, frame reservations and validity checks the inspector counts by the dozen in a three-line loop, is as large a target as the call sequence. Direct calls attacked at most the 59 ns and, as measured, added to it.
- **Declarations do nothing.** Typed and untyped bodies are identical for CAR, SVREF and double addition, and the fixnum loop still carries the generic arithmetic fallback. The compiler has the information to specialize and discards it.
- **Floats are the outlier and the cheapest fix.** Every typed double addition leaves Wasm for the JavaScript float service, which validates the frame, stages both operands into a private memory, computes, and allocates a boxed 16-byte result. The record notes a direct Wasm scalar service exists but is not the one bound at READY. Even with that binding, the boxing remains. A declared double add should be one `f64.add` on unboxed operands. This is 680 times, in one place, with the type information already present in the source.

**Two observations, not gates.** The hand-written Wasm references (0.29 ns for an i32 loop, 0.37 ns for a call) show the engine's ceiling is at or above native for these shapes, so the headroom is real and belongs entirely to the compiler. And the rest-argument row is only 8.7 times slower because native allocates there too, which says allocation itself is not the port's weak point; the protocol around non-allocating operations is.

**What this orders, if you want my reading.** Unboxed numerics under declarations first, because the ratio is the largest and the change is local to the arithmetic emitter. Then trusting declarations for accessors, which removes the checks and root publication around CAR and SVREF. Then the call convention. Each step should rerun this set, which is exactly what the set was built for.
