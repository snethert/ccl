# Stage 0 C/runtime boundary proof

This implements the hand-built slices **S0-LL13-c** and **S0-LL19-b**. It compiles a real freestanding C module, links imported shared memory and a per-instance table, and calls through emitted Wasm using final `try_table` exception handling. It does not implement the CCL compiler, the complete runtime, moving GC, a selected D3 ABI or native Gate 0.

Run from the repository root:

```sh
node tests/wasm/stage0/runtime-boundary/run.mjs --output /tmp/ccl-wasm-runtime-boundary
python3 doc/WASM/tools/gate.py --inventory doc/WASM/stage0/inventory.json --results /tmp/ccl-wasm-runtime-boundary/results.json
```

The output directory must be empty and outside the checkout. LLVM clang, wasm-ld, WABT wat2wasm/wasm-objdump and Node are required. `CCL_WASM_CLANG`, `CCL_WASM_LD` and `CCL_WASM_WAT2WASM` can select executable paths; they are passed as executable arguments, never evaluated as shell text. The reference is macOS with LLVM clang and LLD 21.1.8. Defaults select Homebrew `opt/llvm/bin/clang` and `opt/lld/bin/wasm-ld` explicitly on Intel or Apple Silicon; both versions are checked and executable hashes retained. Exact versions, commands, source files, input digests, objects, modules, link maps, disassembly and results are retained. Compiler/link failure and Worker timeout fail the run. The second command remains BLOCKED because these two slices do not complete the frozen Stage 0 inventory or its review requirements.

## S0-LL13-c

`binary.mjs` reads actual final module imports, signatures, exported linker globals, passive data segments and table element reservations. The ownership map includes fixture low memory, kernel static/BSS/default-stack space, and separately aligned per-Worker TLS, TCR, explicit Lisp stacks and C stacks. It rejects overlap before Worker publication. TLS setup uses actual `__tls_size`, `__tls_align`, `__tls_base` and `__wasm_init_tls`; each Worker has its own instance-private C SP global and backing stack region.

Two Workers are deliberately overlapped inside C activations with address-taken volatile local arrays. A supervisor releases them only after both are parked. The oracle checks actual frame addresses, all 64 local words, current TCR before/after the overlap and restored C SP. The second Worker is instantiated after shared `.data` and BSS sentinels have been mutated, while the first C activation remains live; both sentinels must survive. An actual address-taken C function is installed in the linker-reserved slot and invoked through both the table and C indirect call.

Negative controls cover an overlapping ownership map, active shared data initialization, aliased stack backing, an ordinary shared current-TCR global, an unresolved helper and an object-file function-signature mismatch. Mutants remain under `quarantine/`; expected failures must match the specific rejection, not merely any nonzero exit.

## S0-LL19-b

Two nested C frames publish typed root records and change root/binding/VSP/TSP/CSP checkpoints. The emitted adapter snapshots the incoming state and restores it on ordinary and exceptional paths. C epilogues are not assumed to run after a Wasm exception. No safepoint is inserted between leaving C and finishing restoration.

Twelve cases combine zero, one and six values with normal return, a handler returning supplied values, propagation of the original exit, and cleanup throwing a distinct tag. The complete ordered sequence stays in an explicitly caller-owned VSP result region; the TCR stores its descriptor. The oracle checks every value, descriptor lifetime, root/dynamic-stack restoration, C SP, observable cleanup, absence of post-exit C effects and subsequent C entry. This fixture's restart choices return or transfer outside the unwound C activation; it does not claim to resume that activation or implement all CCL restarts.

Omitting C-SP restoration, root-head restoration or the throw itself must fail the same behavioral oracle used for the correct implementation. `contract.json` and C target-compiled offset/size assertions define this fixture's layout. Its low-memory object addresses and bounded frame sizes are proof fixtures, not frozen production layout choices.

## Remaining integrated work

S0-LL20 adds actual object movement, root reload, D5 admission/lifecycle interleavings, unfinished I/O interruption, cancellation ownership and lazy installation to this foundation. The current tests exercise explicit boundary restoration and Worker ownership, not collection or arbitrary suspension. All later compiler-generated obligations remain required.

The linking assumptions follow the [WebAssembly LLVM linking conventions](https://github.com/WebAssembly/tool-conventions/blob/main/Linking.md), and the strict-link policy follows [LLD's WebAssembly documentation](https://lld.llvm.org/WebAssembly.html). The recorded binary and execution results, not those documents alone, establish this fixture's behavior.
