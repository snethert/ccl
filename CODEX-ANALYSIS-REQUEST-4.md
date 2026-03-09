# Codex Read-Only Analysis Request: cold-boot-init Failure After Const Pool Bloat Elimination

**Mode: READ-ONLY ANALYSIS ONLY. Do not modify any files. Do not write patches.**

**Constraint: Report only facts. Do not speculate. Trace actual code paths and report what you find. Code examples in the report are fine, but no files should be changed.**

**Scope: This is an open-ended analysis request. You are NOT restricted to answering specific questions. Read the codebase, understand the architecture, and tell us what you find — including things we haven't asked about. We want your independent assessment.**

---

## Background: What This Project Is

This is a port of Clozure Common Lisp (CCL) to WebAssembly. The architecture:

- **Kernel** (`lisp-kernel/wasm-kernel-stubs.c` → `build/wasm32/kernel/wasmcl.wasm`): C code compiled to WASM. Manages memory, GC, heap, TCR, const pools, image save/load.
- **Subprims** (`lisp-kernel/wasm32/subprims.s` → `build/wasm32/subprims/subprims.wasm`): Low-level runtime primitives (like `_SPmisc_set`, `_SPmisc_alloc_init`).
- **Compiler** (`compiler/WASM/wasm2.lisp`): Cross-compiler running on host CCL, emits WASM modules + const pool blobs.
- **Build pipeline** (`scripts/wasm/lib/make-real-image.mjs`): Node.js script that boots a WASM image, installs compiled modules, runs `cold-boot-init`, saves the root image.
- **Launch pipeline** (`scripts/wasm/lib/load-image.mjs`): Node.js script that loads the saved root image and starts Lisp.

The two-phase build:
1. **Boot phase**: Load a minimal boot image, install all compiled modules (L0 + L1), install const pools, run `cold-boot-init` to set up CLOS/packages/etc, save as `root.image`.
2. **Launch phase**: Load `root.image`, instantiate module WASM binaries, fill function table, start Lisp.

---

## What We Changed (commit 0cb898c9)

### The Problem We Solved

The const pool serializer (`wasm2-const-pool-entry` in `compiler/WASM/wasm2.lisp`) was treating class objects as opaque gvectors (tag 5), recursively deep-copying the entire CLOS class hierarchy into each pool. 1,315 pools × ~2.2 MB each = 829 MB of const pool data in modules.bin (95% of the 836 MB file). Build-time heap was 2.1 GB.

Previous workaround: purge all pools before image save (2.1 GB → 2.8 MB), reinstall on-demand at launch. This broke startup with crashes (analyzed in CODEX-ANALYSIS-REQUEST-3.md — your spill stack diagnosis was correct).

### The Fix

1. **Serializer** (`compiler/WASM/wasm2.lisp`): Added class-ref detection BEFORE the gvector fallthrough in `wasm2-const-pool-entry`. Named classes now emit tag 18 (~30 bytes) instead of tag 5 (~2.2 MB). Anonymous classes fall through to gvector as before.

2. **Kernel tag 18 handler** (`wasm-kernel-stubs.c`, `wasm_const_pool_install_inner`): When deserializing a class-ref, interns the class-name symbol and wraps it in a sentinel cons cell `(symbol . fixnum-0x434C)`. This sentinel marks pool slots that need post-install resolution.

3. **New kernel export** `wasm_const_pool_resolve_class_refs`: Walks all pool entries after cold-boot-init, finds sentinel cons cells, resolves via `(FIND-CLASS symbol NIL)`, replaces pool slot with the class object (or bare symbol on failure).

4. **Build pipeline** (`make-real-image.mjs`): Calls `wasm_const_pool_resolve_class_refs` after cold-boot-init. Removed purge. Stripped const pool byte data from modules.bin (code only).

5. **Launch pipeline** (`load-image.mjs`): Removed entire on-demand install infrastructure — scratch memory, callbacks, repair pass, pre-start GC. Pools are pre-baked.

6. **Spill stack** (`wasm-kernel-stubs.c` + `thread_manager.c`): `wasm_spill_push`/`wasm_spill_pop` now fail-fast with diagnostic dump instead of silently returning nil on NULL. Allocation fails fast on malloc failure.

7. **`wasm_const_pool_ref` slow path**: Now traps with diagnostics instead of calling host for on-demand install.

### What Worked

Build compiles. All 8,682 modules install successfully. Heap is 186 MiB (down from 2.1 GB). The class-ref serializer is working — const pool data is no longer bloating the heap.

```
[stage] compiled modules: 7558/7560 installed, 0 failed, 2 skipped (boot)
[stage] pre-cold-boot heap profile:
HEAP-PROFILE: total=195624960 (186 MiB) cons=5344093 (40 MiB)
  0xfa svec n=16282 b=151481768 (144 MiB)
  0xbf string n=7526 b=705416 (0 MiB)
  0x3a sym n=7783 b=249056 (0 MiB)
  0x2a func n=8904 b=209648 (0 MiB)
  0x82 istruct n=3648 b=172048 (0 MiB)
```

### What Failed

cold-boot-init throws immediately (startup-step=0):

```
cold-boot-init: fn=0x0x0412d8be entry=0x0x00001168 (idx=1114)
cold-boot-init: pending_throw=0x0x00000048 startup-step=0
cold-boot-init: threw (infra incomplete)
FAIL: wasm_run_cold_boot_init returned -6
```

`pending_throw=0x48` = TYPE-ERROR. `startup-step=0` means it failed before reaching the first `%wasm-note-startup-step` call (step 10). Entry index 1114 is the `%RUN-COLD-BOOT-INIT` function.

---

## The Chicken-and-Egg Problem

Here's what we suspect but want you to verify:

The class-ref resolution pass (`wasm_const_pool_resolve_class_refs`) runs AFTER cold-boot-init because FIND-CLASS isn't available until CLOS is initialized. But cold-boot-init code may access const pool slots that contain class-refs (sentinel cons cells `(symbol . fixnum-0x434C)`) when it expects actual class objects. Accessing a cons cell where a class is expected → TYPE-ERROR.

**But we're not sure this is the actual cause.** The same `pending_throw=0x48 startup-step=0` error was seen in earlier builds too (noted in our memory: "Adding static arrays causes startup-step=0 pending_throw=0x48 failure"). It might be unrelated to class-refs. It might be a data layout issue, a linker issue, or something else entirely.

---

## What We Want From You

1. **Trace the cold-boot-init failure path.** What exactly is `%RUN-COLD-BOOT-INIT` doing at startup-step=0 that throws TYPE-ERROR (0x48)? Read `level-0/nfasload.lisp` line 1268+ and trace the first few function calls. Which const pool entries do these functions reference? Do any of them contain class objects that would now be sentinel cons cells?

2. **Assess the sentinel cons approach.** Is wrapping class-refs in `(symbol . fixnum-0x434C)` the right approach? What happens when GC encounters these cons cells? What happens when Lisp code accesses a pool slot expecting a class and gets a cons? Is there a better interim representation?

3. **Evaluate the overall architecture.** We're trying to achieve: all work at build time, deterministic launch, reasonable artifact sizes, no RAM bloat. Read the build pipeline (`make-real-image.mjs`), the launcher (`load-image.mjs`), and the kernel const pool machinery (`wasm-kernel-stubs.c` lines 6000-7000). Tell us if the approach is sound or if there's a fundamental issue.

4. **Anything else you find.** Read the code. If you see bugs, design issues, or opportunities we haven't asked about, report them. We trust your independent judgment.

---

## Key Files to Read

| File | What's There |
|------|-------------|
| `compiler/WASM/wasm2.lisp` | Const pool serializer — look at `wasm2-const-pool-entry` (line ~4720) and `wasm2-const-pool-bytes` (line ~4900) |
| `lisp-kernel/wasm-kernel-stubs.c` | Tag 18 handler (~line 6449), `wasm_const_pool_resolve_class_refs` (~line 6760), `wasm_const_pool_ref` (~line 6848), spill push/pop (~line 2150), heap profiler (~line 584) |
| `lisp-kernel/thread_manager.c` | TCR spill stack init (~line 1881) |
| `scripts/wasm/lib/make-real-image.mjs` | Build pipeline — module install, cold-boot-init call, class-ref resolution, image save, modules.bin assembly |
| `scripts/wasm/lib/load-image.mjs` | Simplified launcher — load image, fill table, start |
| `level-0/nfasload.lisp` | `%run-cold-boot-init` (line 1268) — the function that's failing |
| `level-0/l0-misc.lisp` | Low-level Lisp infrastructure called during cold boot |
| `level-0/l0-def.lisp` | `cold-load-function-def`, bootstrap definitions |

---

## Build and Run Commands (for reference, don't run them)

```bash
# Full rebuild
scripts/wasm/rebuild-everything.sh

# Just the root image (after kernel/modules are built)
node --max-old-space-size=8192 scripts/wasm/lib/make-real-image.mjs \
  --output build/wasm32/images/root.image \
  --modules build/wasm32/modules/wasm-runtime-modules.json \
  --boot-modules build/wasm32/modules/wasm-boot-modules.json

# Launch
node scripts/wasm/lib/load-image.mjs --startup-plan build/wasm32/images/startup-plan.json
```

---

## Git Context

```
Branch: wasm-port
HEAD: 0cb898c9 wasm: eliminate const pool bloat — emit class-refs, pre-bake pools, simplify launch

Recent commits:
0cb898c9 wasm: eliminate const pool bloat — emit class-refs, pre-bake pools, simplify launch
40af098c wasm: skip invariant fcell gate (O(N) heap scan per symbol is too slow)
419a71e1 wasm: skip Lisp save path when const pools are partial
bda1d865 wasm: skip proactive const-pool install, defer to launch time
a6144e84 wasm: add post-module-install GC to compact heap before restore-lisp-pointers
d7e54001 wasm: add pre-save GC to wasm_save_image_direct
553ded6a wasm: fix function-table collision — add --table-base=256 to linker
```
