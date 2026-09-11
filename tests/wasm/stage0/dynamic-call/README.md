# C/C4/B dynamic-call correctness fixture

Run on the macOS reference host from the repository root:

```sh
node tests/wasm/stage0/dynamic-call/run.mjs --output /absolute/path/to/new-empty-evidence-directory
```

The runner executes the existing debugger-frame, integrated-runtime and C-boundary prerequisites afresh. It then links a new isolated C reader/allocator with the unchanged prerequisite objects and emits the same corpus for C (three argument parameters), C4 (four) and B (stack arguments). LLVM clang and wasm-ld use the existing pinned LLVM 21 toolchain; the report retains paths, versions and executable hashes. WABT and Node/V8 identities are recorded too.

Each candidate runs 53 positive cases and 27 rejection controls. The corpus covers ordered arguments 0–6 and 32, closure self/environment, direct/indirect/runtime-adapter calls, APPLY, optional/rest/keyword binding, complete multiple values, nested calls and C callbacks, moving GC, lazy installation, prebuilt redefinition, late Workers and exceptional cleanup followed by idle collection. Three 100,000-transfer chains return zero, one and six values while alternating two and 32 arguments. The C reader checks live binding/handler records on every tail iteration; stack and root high-water marks remain bounded.

The same ordinary semantic, state, metadata and collector checks reject swapped arguments, lost roots/values, bad counts, stale moved self, wrong table roles/signatures, invalid installation bytes/profiles, missing restoration/cleanup, tail-frame leaks, lost binding extent and duplicate result ownership. Controls retain actual mutated modules and their first failure. An unexpected error, deadline or surviving mutant fails the run. Host publication controls reject overlapping ranges and undersized C stacks before kernel instantiation or Worker publication. Independent raw unequal cons fixtures check C and emitted readers and mutation, including NIL reads, dotted/shared/nested/cyclic graph edges; a one-sided emitted CAR swap is rejected.

The [protocol](../../../../doc/WASM/abi/dynamic-call.v0.md) and schema define ownership. Each physical result word has one collector scanner. When the TCR owns a result region, that region's linked root record has count zero. Reusing a frame result region also clears its advertised count. Development r1 exposed duplicate scanning during collection after a return and late Worker creation; r2 exposed a stale count while reusing nested results. Both original failures are retained. The reviewed collector was not changed.

The 64-byte logical header is read independently by C static assertions and literal host offsets. Per-candidate debug metadata binds code/version/root-descriptor keys and stable fixture binding IDs to exact emitted-WAT hashes and line numbers. Policy 1 reports values unavailable while still allocating roots; it does not establish an optimized debug storage cost.

Bounds: 32 arguments, six values, 512-byte activation, 16 KiB ABI stack per Worker, up to fifteen published root records before one C-helper record, at most eight logical frames, and sixteen immutable 8 KiB inspection replies per Worker. Memory is one fixed 1 MiB shared wasm32 memory with two 4 KiB semispaces. Four ownership slots are reserved; at most three Workers are live. Argument, stack and generation capacity failures are explicit conditions. These are fixture limits. This experiment does not handle arbitrarily large cases or measure production resource costs.

Function objects are cons-based surrogates; symbols and keywords use declared fixture tokens. Module granularity is one definition per callable module plus support/runtime instances. There is no CCL compiler, production object model, browser qualification, full image restore or ABI timing/selection claim. H(G) is optional future work. New results remain NOT_REVIEWED/NOT_ACCEPTED until a different reviewer checks them and the project accepts their scopes.

The v2 report contains 18 new inventory records plus six freshly executed prerequisite records, preserving exact source, inventory, toolchain, case, control and binary artifacts. Original accepted evidence is kept separately: executing unchanged prerequisite source does not grant acceptance to the new ABI sources or newly linked kernel.
